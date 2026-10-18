"""Position-only morph extension; reuses the unmodified live step and guards."""
from copy import deepcopy
from itertools import product
import numpy as np
from .canonical import canonical_bytes, sha256, strict_json
from .live_motion import LiveRuntime, Blend
from .live_commands import UI
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

    def target_offsets(self,tick):
        return super().target_offsets(tick)+self.shape.at(tick)

    def channels(self):
        return {k:blend_mapping(getattr(self,k)) for k in ('shape','translation','morph','wander_mix')}

    def _admit(self):
        # Each quintic blend is a convex combination of its endpoints. Test all
        # independent corners, plus an analytic box enclosing seeded wander.
        # This proves a bound for future target forces, not only this tick.
        relative = self.scene.home_xy-self.scene.home_xy.mean(axis=0)
        wander = .08*max(float(self.wander_mix.start),float(self.wander_mix.end))
        for shape,translation,morph,sx,sy in product(
            (self.shape.start,self.shape.end),(self.translation.start,self.translation.end),
            (self.morph.start,self.morph.end),(-1,1),(-1,1)):
            offset = shape+translation+morph*relative*np.array([-.5,1.])+wander*np.array([sx,sy])
            norms = np.linalg.norm(offset,axis=1)
            if np.any(norms*self.scene.spring_k > self.scene.max_total_force) or np.any(norms > self.scene.max_displacement):
                raise ValueError('combined motion exceeds conservative force/displacement admission budget; reduce motion or turn wander off')

    def accept(self,text):
        command = parse_command(text)
        event = {'schema_version':'cz-morph-event-0.1','sequence':len(self.events),
                 'effective_tick':self.state.tick,'command':command}
        self.apply_event(event)
        return deepcopy(event)

    def apply_event(self,event):
        event = strict_json(canonical_bytes(event))
        if (type(event) is not dict or set(event)!={'schema_version','sequence','effective_tick','command'}
            or event['schema_version']!='cz-morph-event-0.1'
            or type(event['sequence']) is not int or event['sequence']!=len(self.events)
            or type(event['effective_tick']) is not int or event['effective_tick']!=self.state.tick
            or self.state.tick>=self.scene.terminal_tick):
            raise ValueError('invalid morph event version/sequence/tick/fields')
        command = event['command']
        if type(command) is not dict:
            raise ValueError('invalid command')
        action = command.get('action')
        if action=='morph':
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
        previous = {k:deepcopy(getattr(self,k)) for k in ('shape','translation','morph','wander_mix','wander','active_target')}
        count = len(self.events)
        try:
            if action=='morph':
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
