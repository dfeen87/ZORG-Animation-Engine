"""Self-contained morph sessions with strict provenance and exact tick replay."""
from copy import deepcopy
from pathlib import Path
from .canonical import atomic_json, canonical_bytes, read_json, sha256, strict_json
from .evidence import environment_info
from .session import engine_sources
from .morph_runtime import MorphRuntime
from .state import state_mapping

SESSION_KEYS = {'schema_version','status','reason','config','targets','events','captures',
    'final_tick','trajectory_sha256','final_state_sha256','source','environment','metrics','session_sha256'}


class MorphRecorder:
    def __init__(self,out,runtime):
        self.out=Path(out)
        self.out.mkdir(parents=True,exist_ok=False)
        self.config=deepcopy(runtime.config)
        self.targets=deepcopy(runtime.targets)
        self.source=engine_sources()
        self.environment=environment_info()
        self.journal=self.out/'events.jsonl'
        self.journal.touch(exist_ok=False)
        atomic_json(self.out/'session.json',{'schema_version':'cz-morph-session-0.1','status':'running'})

    def record_event(self,event):
        with self.journal.open('ab') as stream:
            stream.write(canonical_bytes(event))
            stream.flush()

    def finish(self,runtime,status='complete',reason=None,metrics=None):
        if status not in ('complete','interrupted','failed'):
            raise ValueError('invalid recording status')
        matching = (runtime.config==self.config and runtime.targets==self.targets
            and self.journal.read_bytes()==b''.join(canonical_bytes(e) for e in runtime.events)
            and self.source==engine_sources() and self.environment==environment_info())
        if not matching and status!='failed':
            raise ValueError('recording journal/config/source/environment mismatch')
        version = getattr(runtime, 'session_version', None) or (
            'cz-morph-session-0.2' if any(e['schema_version']=='cz-morph-event-0.2' for e in runtime.events)
            else 'cz-morph-session-0.1')
        doc={'schema_version':version,'status':status,'reason':reason,
            'config':self.config,'targets':self.targets,'events':runtime.events,'captures':runtime.captures,
            'final_tick':runtime.state.tick,'trajectory_sha256':runtime.trajectory_sha256,
            'final_state_sha256':sha256(canonical_bytes(state_mapping(runtime.state))),
            'source':self.source,'environment':self.environment,'metrics':metrics or {}}
        doc['session_sha256']=sha256(canonical_bytes(doc))
        atomic_json(self.out/'session.json',doc)
        return self.out/'session.json'


def load_session(path):
    path=Path(path)
    if path.is_symlink():
        raise ValueError('symlink session refused')
    doc=read_json(path)
    if (type(doc) is not dict or set(doc)!=SESSION_KEYS or doc['schema_version'] not in ('cz-morph-session-0.1','cz-morph-session-0.2','cz-morph-session-0.3')
        or doc['status'] not in ('complete','interrupted')):
        raise ValueError('unsupported, failed or incomplete morph session')
    if sha256(canonical_bytes({k:v for k,v in doc.items() if k!='session_sha256'}))!=doc['session_sha256']:
        raise ValueError('session metadata integrity mismatch')
    if doc['source']!=engine_sources() or doc['environment']!=environment_info():
        raise ValueError('source/environment differs; exact morph replay unavailable')
    runtime=runtime_for(doc)
    if type(doc['final_tick']) is not int or not 0<=doc['final_tick']<=runtime.scene.terminal_tick:
        raise ValueError('invalid final tick')
    if type(doc['events']) is not list or type(doc['captures']) is not list:
        raise ValueError('invalid events/captures')
    previous=0
    for sequence,event in enumerate(doc['events']):
        if type(event) is not dict or type(event.get('effective_tick')) is not int:
            raise ValueError('invalid event')
        if doc['schema_version']=='cz-morph-session-0.1' and event.get('schema_version')!='cz-morph-event-0.1':
            raise ValueError('extended event in historical morph session')
        if doc['schema_version']=='cz-morph-session-0.2' and event.get('schema_version') not in ('cz-morph-event-0.1','cz-morph-event-0.2'):
            raise ValueError('creator event in historical morph session')
        tick=event['effective_tick']
        if not previous<=tick<=doc['final_tick'] or event.get('sequence')!=sequence:
            raise ValueError('event chronology mismatch')
        previous=tick
    return doc


def runtime_for(doc):
    if doc['schema_version']=='cz-morph-session-0.3':
        from .studio_runtime import StudioRuntime
        return StudioRuntime(doc['config'],doc['targets'])
    return MorphRuntime(doc['config'],doc['targets'])


def replay_runtimes(path):
    doc=load_session(path)
    runtime=runtime_for(doc)
    index=0
    for tick in range(doc['final_tick']+1):
        while index<len(doc['events']) and doc['events'][index]['effective_tick']==tick:
            runtime.apply_event(doc['events'][index]); index+=1
        yield runtime
        if tick<doc['final_tick']:
            runtime.step()
    if (runtime.trajectory_sha256!=doc['trajectory_sha256'] or
        sha256(canonical_bytes(state_mapping(runtime.state)))!=doc['final_state_sha256'] or
        canonical_bytes(runtime.captures)!=canonical_bytes(doc['captures'])):
        raise ValueError('trajectory/final state/capture replay mismatch')


def verify_session(path):
    count=sum(1 for _ in replay_runtimes(path))
    return {'passed':True,'states':count,'final_tick':count-1,'exact_replay':True}
