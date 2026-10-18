"""Closed, hashed live recordings, separate from rendered media."""
from __future__ import annotations

from pathlib import Path

from .canonical import atomic_json, canonical_bytes, read_json, read_jsonl, sha256
from .evidence import environment_info
from .live_motion import LiveRuntime, validate_config
from .state import state_mapping


def engine_sources():
    package = Path(__file__).resolve().parent
    files = list(package.glob('*.py')) + [package.parent/name for name in ('requirements.lock','pyproject.toml')]
    return {p.relative_to(package.parent).as_posix(): sha256(p.read_bytes()) for p in sorted(files)}


class Recorder:
    def __init__(self, out: Path, config: dict):
        self.config = validate_config(config)
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=False)
        self.events_path = self.out / 'events.jsonl'
        self.events_path.touch(exist_ok=False)
        self.sources = engine_sources()
        self.environment = environment_info()
        atomic_json(self.out / 'config.json', self.config)
        atomic_json(self.out / 'session.json', {'schema_version': 'cz-live-session-0.1', 'status': 'running'})

    def record_event(self, event):
        with self.events_path.open('ab') as stream:
            stream.write(canonical_bytes(event))

    def finish(self, runtime, status='complete', reason=None, metrics=None):
        if status not in ('complete','interrupted','failed'):
            raise ValueError('invalid session finish status')
        try:
            matching = runtime.config == self.config and read_jsonl(self.events_path) == runtime.events
        except (OSError,ValueError):
            matching = False
        if not matching:
            if status != 'failed':
                raise ValueError('recording event/config mismatch')
            reason = f'{reason}; event/config recording incomplete'
        doc = {'schema_version': 'cz-live-session-0.1', 'status': status, 'reason': reason,
               'config': self.config, 'config_sha256': sha256((self.out/'config.json').read_bytes()),
               'events': 'events.jsonl', 'events_sha256': sha256(self.events_path.read_bytes()),
               'event_count': len(runtime.events), 'final_tick': runtime.state.tick,
               'duration_seconds': runtime.state.tick / self.config['sim_hz'],
               'trajectory_sha256': runtime.trajectory_sha256,
               'final_state_sha256': sha256(canonical_bytes(state_mapping(runtime.state))),
               'environment': self.environment, 'source': self.sources, 'metrics': metrics or {}}
        # Session digest binds config, events, final state, timeline and provenance.
        doc['session_sha256'] = sha256(canonical_bytes(doc))
        atomic_json(self.out / 'session.json', doc)
        return self.out / 'session.json'


def load_session(path, *, check_environment=True):
    path = Path(path)
    doc = read_json(path)
    if type(doc) is not dict or doc.get('schema_version') != 'cz-live-session-0.1':
        raise ValueError('unsupported session contract')
    if doc.get('status') not in ('complete','interrupted'):
        raise ValueError('session is incomplete or failed')
    expected = {'schema_version','status','reason','config','config_sha256','events','events_sha256',
                'event_count','final_tick','duration_seconds','trajectory_sha256','final_state_sha256',
                'environment','source','metrics','session_sha256'}
    if set(doc) != expected:
        raise ValueError('session: wrong fields')
    if sha256(canonical_bytes({k:v for k,v in doc.items() if k!='session_sha256'})) != doc['session_sha256']:
        raise ValueError('session metadata integrity mismatch')
    config = validate_config(doc['config'])
    if type(doc['final_tick']) is not int or not 0 <= doc['final_tick'] <= config['max_ticks']:
        raise ValueError('invalid final tick')
    if doc['duration_seconds'] != doc['final_tick']/60:
        raise ValueError('duration does not match tick count')
    if doc['events'] != 'events.jsonl':
        raise ValueError('invalid event artifact path')
    for name, digest in (('config.json',doc['config_sha256']), ('events.jsonl',doc['events_sha256'])):
        artifact = path.parent/name
        if artifact.is_symlink() or sha256(artifact.read_bytes()) != digest:
            raise ValueError(f'{name}: integrity mismatch')
    if read_json(path.parent/'config.json') != config:
        raise ValueError('config artifact mismatch')
    events = read_jsonl(path.parent/'events.jsonl')
    if type(doc['event_count']) is not int or doc['event_count'] != len(events):
        raise ValueError('event count mismatch')
    # Validate each event without doing every physics step yet.
    previous_tick = 0
    validator = LiveRuntime(config)
    from .state import owned_state
    for event in events:
        tick = event.get('effective_tick') if isinstance(event,dict) else None
        if type(tick) is not int or not previous_tick <= tick <= doc['final_tick']:
            raise ValueError('event tick ordering/range mismatch')
        validator.state = owned_state(tick,validator.state.positions,validator.state.velocities)
        validator.apply_event(event)
        previous_tick = tick
    if check_environment:
        if doc['environment'] != environment_info():
            raise ValueError('session environment differs; exact replay unavailable')
        if doc['source'] != engine_sources():
            raise ValueError('session source differs; exact replay unavailable')
    return doc, events


def replay_states(path):
    """Yield every tick, checking the full trajectory after terminal audit state."""
    doc,events = load_session(path)
    runtime = LiveRuntime(doc['config'])
    index = 0
    for tick in range(doc['final_tick']+1):
        while index < len(events) and events[index]['effective_tick'] == tick:
            runtime.apply_event(events[index])
            index += 1
        yield runtime.state
        if tick < doc['final_tick']:
            runtime.step()
    if runtime.trajectory_sha256 != doc['trajectory_sha256']:
        raise ValueError('numerical trajectory replay mismatch')
    if sha256(canonical_bytes(state_mapping(runtime.state))) != doc['final_state_sha256']:
        raise ValueError('final state replay mismatch')


def verify_session(path):
    doc, _ = load_session(path)
    count = sum(1 for _ in replay_states(path))
    return {'passed': True, 'states': count, 'final_tick':doc['final_tick'],
            'trajectory_sha256':doc['trajectory_sha256']}
