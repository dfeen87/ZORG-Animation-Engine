"""Position-only morph extension; reuses the unmodified live step and guards."""
from copy import deepcopy
from itertools import product
import numpy as np
from .canonical import canonical_bytes, sha256, strict_json
from .live_motion import LiveRuntime, Blend
from .live_commands import UI, parse_command as parse_live
from .morph_commands import parse_command
from .morph_targets import validate_target
from .state import state_mapping
from .guard import validate_state


def blend_mapping(blend):
    return {'start':blend.start.tolist(),'end':blend.end.tolist(),
            'tick':blend.tick,'duration_ticks':blend.duration}


class MorphRuntime(LiveRuntime):
    def __init__(self, config, targets):
        super().__init__(config)
        if type(targets) is not dict or not targets:
            raise ValueError('target library required')
        self.targets = {k:validate_target(v,self.scene) for k,v in targets.items()}
        if any(k != v['id'] for k,v in self.targets.items()) or 'home' not in self.targets:
            raise ValueError('target library ID mismatch or missing home')
        self.shape = Blend(np.zeros_like(self.scene.home_xy))
        self.active_target = 'home'
        self.captures = []
        self.motion_auto = False

    def target_offsets(self,tick):
        return super().target_offsets(tick)+self.shape.at(tick)

    def channels(self):
        return {k:blend_mapping(getattr(self,k)) for k in ('shape','translation','morph','wander_mix')}

    def _admit(self, translation=None):
        translation = self.translation if translation is None else translation
        # Each quintic blend is a convex combination of its endpoints. Test all
        # independent corners, plus an analytic box enclosing seeded wander.
        # This proves a bound for future target forces, not only this tick.
        relative = self.scene.home_xy-self.scene.home_xy.mean(axis=0)
        wander = .08*max(float(self.wander_mix.start),float(self.wander_mix.end))
        for shape,offset_translation,morph,sx,sy in product(
            (self.shape.start,self.shape.end),(translation.start,translation.end),
            (self.morph.start,self.morph.end),(-1,1),(-1,1)):
            offset = shape+offset_translation+morph*relative*np.array([-.5,1.])+wander*np.array([sx,sy])
            norms = np.linalg.norm(offset,axis=1)
            if np.any(norms*self.scene.spring_k > self.scene.max_total_force) or np.any(norms > self.scene.max_displacement):
                raise ValueError('combined motion exceeds conservative force/displacement admission budget; reduce motion or turn wander off')

    def _adaptive_command(self, motion):
        """Pure admission search: 48 bisections, meaningful endpoint delta >=1e-6.

        The requested endpoint is affine in alpha. Every corner constraint is
        a norm of an affine function, hence convex; alpha=0 reuses the admitted
        endpoint and the new blend start lies inside its old endpoint segment.
        Feasibility on [0,1] is consequently an interval containing zero.
        Only translation changes. Duration cannot repair an unsafe endpoint.
        """
        action = motion['action']
        directions = {'left':[-1.,0.], 'right':[1.,0.],
                      'up':[0.,1.], 'down':[0.,-1.]}
        requested = np.array(directions[action])*motion['strength']
        origin = self.translation.end.copy()

        def candidate(alpha):
            blend = deepcopy(self.translation)
            target = requested if alpha == 1. else origin+alpha*(requested-origin)
            blend.set(target,self.state.tick,motion['duration_ticks'])
            self._admit(translation=blend)
            return blend

        try:
            selected = candidate(1.)
            fraction = 1.
        except ValueError:
            # Never attempt recovery of an inadmissible current channel state.
            selected = candidate(0.)
            low,high = 0.,1.
            for _ in range(48):
                middle = (low+high)/2
                try:
                    trial = candidate(middle)
                except ValueError:
                    high = middle
                else:
                    low,selected = middle,trial
            fraction = low
            if np.linalg.norm(selected.end-origin) < 1e-6:
                raise ValueError('no meaningful safe movement within admission budget')
        return {'action':'adaptive_motion','requested':deepcopy(motion),
                'effective_translation':selected.end.tolist(),
                'fraction':fraction,'algorithm':'translation-bisection-v1'}

    def accept(self,text):
        command = parse_command(text)
        version = 'cz-morph-event-0.1'
        if command['action']=='motion_auto':
            version = 'cz-morph-event-0.2'
        elif (command['action']=='motion' and self.motion_auto
              and command['motion']['action'] in ('left','right','up','down')):
            command = self._adaptive_command(command['motion'])
            version = 'cz-morph-event-0.2'
        event = {'schema_version':version,'sequence':len(self.events),
                 'effective_tick':self.state.tick,'command':command}
        self.apply_event(event)
        return deepcopy(event)

    def command_feedback(self,event):
        command = event['command']
        if command['action']=='motion_auto':
            return 'MOTION AUTO '+('ON' if command['enabled'] else 'OFF')
        if command['action']!='adaptive_motion':
            return f"{command['action'].upper()} accepted at tick {self.state.tick}"
        motion = command['requested']
        x,y = command['effective_translation']
        applied = {'left':-x,'right':x,'up':y,'down':-y}[motion['action']]
        status = 'ADAPTIVE MOTION ACCEPTED' if command['fraction']<1 else 'MOTION ACCEPTED'
        return (f"{status}\nCOMMAND: {motion['action']}\n"
                f"REQUESTED: {motion['strength']:.9g}\nAPPLIED: {applied:.9g}\n"
                f"TARGET XY: ({x:.9g}, {y:.9g})\n"
                f"SHAPE: {self.active_target.upper()} — PRESERVED")

    def apply_event(self,event):
        event = strict_json(canonical_bytes(event))
        if (type(event) is not dict or set(event)!={'schema_version','sequence','effective_tick','command'}
            or event['schema_version'] not in ('cz-morph-event-0.1','cz-morph-event-0.2')
            or type(event['sequence']) is not int or event['sequence']!=len(self.events)
            or type(event['effective_tick']) is not int or event['effective_tick']!=self.state.tick
            or self.state.tick>=self.scene.terminal_tick):
            raise ValueError('invalid morph event version/sequence/tick/fields')
        command = event['command']
        if type(command) is not dict:
            raise ValueError('invalid command')
        action = command.get('action')
        extended = event['schema_version']=='cz-morph-event-0.2'
        if extended:
            if action=='motion_auto':
                if set(command)!={'action','enabled'} or type(command['enabled']) is not bool:
                    raise ValueError('invalid motion auto command')
                normalized = command
            elif action=='adaptive_motion':
                if not self.motion_auto or set(command)!={'action','requested','effective_translation','fraction','algorithm'}:
                    raise ValueError('invalid adaptive motion command or mode')
                motion = command['requested']
                if type(motion) is not dict or motion.get('action') not in ('left','right','up','down'):
                    raise ValueError('invalid adaptive direction')
                if type(motion.get('duration_ticks')) is not int or type(motion.get('strength')) not in (int,float):
                    raise ValueError('invalid adaptive parameter types')
                requested = parse_live(f"{motion['action']} {motion['strength']} {motion['duration_ticks']/60}")
                if canonical_bytes(requested)!=canonical_bytes(motion):
                    raise ValueError('noncanonical adaptive request')
                normalized = self._adaptive_command(requested)
            else:
                raise ValueError('unknown extended morph event action')
        elif action=='morph':
            if set(command)!={'action','target','duration_ticks'} or type(command['duration_ticks']) is not int:
                raise ValueError('invalid morph command')
            normalized = parse_command(f"morph {command['target']} {command['duration_ticks']/60}")
        elif action=='capture':
            if set(command)!={'action','label'}:
                raise ValueError('invalid capture command')
            normalized = parse_command(f"capture {command['label']}")
        elif action=='motion':
            if (set(command)!={'action','motion'} or type(command['motion']) is not dict
                or set(command['motion'])!={'action','strength','duration_ticks','scope','envelope'}):
                raise ValueError('invalid motion command')
            normalized = command  # original LiveRuntime validates its exact normalized grammar below
            if command['motion'].get('action') in UI:
                raise ValueError('UI command cannot be recorded as motion')
        else:
            raise ValueError('unknown morph event action')
        if canonical_bytes(command)!=canonical_bytes(normalized):
            raise ValueError('noncanonical morph command')
        previous = {k:deepcopy(getattr(self,k)) for k in ('shape','translation','morph','wander_mix','wander','active_target','motion_auto')}
        count = len(self.events)
        try:
            if action=='motion_auto':
                self.motion_auto = command['enabled']
            elif action=='adaptive_motion':
                self.translation.set(command['effective_translation'],self.state.tick,
                                     command['requested']['duration_ticks'])
                self._admit()
            elif action=='morph':
                if command['target'] not in self.targets:
                    raise ValueError(f"unsupported target: {command['target']}")
                self.shape.set(self.targets[command['target']]['offsets'],self.state.tick,command['duration_ticks'])
                self.active_target = command['target']
                self._admit()
            elif action=='motion':
                old = {'schema_version':'cz-live-event-0.1','sequence':count,'effective_tick':self.state.tick,**command['motion']}
                LiveRuntime.apply_event(self,old)
                self.events.pop()
                if command['motion']['action']=='reset':
                    self.shape.set(np.zeros_like(self.scene.home_xy),self.state.tick,command['motion']['duration_ticks'])
                    self.active_target='home'
                self._admit()
            else:
                if validate_state(self.state,self.scene):
                    raise ValueError('cannot capture invalid committed state')
                if any(c['label']==command['label'] for c in self.captures):
                    raise ValueError('capture label already exists in this take')
                from .session import engine_sources
                snapshot = {'schema_version':'cz-morph-capture-0.1','label':command['label'],
                    'tick':self.state.tick,'active_target':self.active_target,
                    'state':state_mapping(self.state),'channels':self.channels(),
                    'seed':self.config['seed'],'config_sha256':sha256(canonical_bytes(self.config)),
                    'source_sha256':sha256(canonical_bytes(engine_sources())),
                    'field':{'threshold':self.scene.threshold,'elements':[
                        {'id':e.id,'sigma':e.sigma,'weight':e.weight} for e in self.scene.elements]},
                    'validation':'passed'}
                snapshot['id']=sha256(canonical_bytes(snapshot))
                self.captures.append(snapshot)
            self.events.append(event)
        except BaseException:
            for k,v in previous.items():
                setattr(self,k,v)
            del self.events[count:]
            raise
