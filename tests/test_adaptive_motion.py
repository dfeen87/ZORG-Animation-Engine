"""Adaptive translation admission leaves the historical engine and guards intact."""
from copy import deepcopy
from itertools import product
from pathlib import Path
import os
import numpy as np
import pytest
from commander_zorg.canonical import read_json, canonical_bytes, atomic_json, sha256
from commander_zorg.live_motion import LiveRuntime, Blend, LiveNumericalError
from commander_zorg.morph_commands import parse_command
from commander_zorg.morph_runtime import MorphRuntime
from commander_zorg.morph_targets import load_targets
from commander_zorg.morph_session import MorphRecorder, verify_session, replay_runtimes
from commander_zorg.state import state_mapping
from commander_zorg.guard import validate_state

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def runtime():
    config = read_json(ROOT/'scenes/live_lab.json')
    targets = load_targets(ROOT/'morph_targets', LiveRuntime(config).scene)
    return MorphRuntime(config, targets)


def snapshot(r):
    return canonical_bytes({'channels':r.channels(), 'events':r.events,
        'state':state_mapping(r.state), 'wander':r.wander, 'auto':r.motion_auto,
        'target':r.active_target, 'captures':r.captures, 'trace':r.trajectory_sha256})


def advance(r, ticks):
    for _ in range(ticks): r.step()


def assert_corners_safe(r):
    # Independently check every combined endpoint, including wander's full box.
    relative = r.scene.home_xy-r.scene.home_xy.mean(axis=0)
    w = .08*max(float(r.wander_mix.start),float(r.wander_mix.end))
    for shape,t,m,x,y in product((r.shape.start,r.shape.end),
            (r.translation.start,r.translation.end),(r.morph.start,r.morph.end),(-w,w),(-w,w)):
        norms = np.linalg.norm(shape+t+m*relative*[-.5,1.]+[x,y],axis=1)
        assert np.all(norms <= r.scene.max_displacement)
        assert np.all(norms*r.scene.spring_k <= r.scene.max_total_force)


@pytest.mark.parametrize('direction', ['up','down','left','right'])
def test_safe_request_unchanged(runtime, direction):
    strict = MorphRuntime(runtime.config,runtime.targets)
    runtime.accept('motion auto on')
    e = runtime.accept(direction+' .1 .5')['command']
    strict.accept(direction+' .1 .5')
    assert e['fraction']==1.
    assert e['requested']==parse_command(direction+' .1 .5')['motion']
    assert np.array_equal(runtime.translation.end,strict.translation.end)
    for _ in range(180):
        runtime.step();strict.step()
        assert np.array_equal(runtime.state.positions,strict.state.positions)
    assert runtime.trajectory_sha256==strict.trajectory_sha256


@pytest.mark.parametrize('target', ['circle','cloud','hill'])
@pytest.mark.parametrize('direction', ['up','down','left','right'])
def test_adaptation_preserves_channels_and_numerics(runtime,target,direction):
    runtime.accept('morph '+target)
    advance(runtime,17)  # Shape endpoints and wander are still active.
    runtime.accept('motion auto on')
    before = runtime.channels()
    positions = runtime.state
    e = runtime.accept(direction)['command']
    assert runtime.state is positions
    assert runtime.active_target==target and runtime.wander
    for channel in ('shape','morph','wander_mix'):
        assert runtime.channels()[channel]==before[channel]
    assert np.linalg.norm(runtime.translation.end) <= .3
    assert 0 < e['fraction'] <= 1
    assert_corners_safe(runtime)
    for _ in range(360):
        offsets = runtime.target_offsets(runtime.state.tick)
        assert np.all(np.linalg.norm(offsets*runtime.scene.spring_k[:,None],axis=1)<=runtime.scene.max_total_force)
        runtime.step()
        assert not validate_state(runtime.state,runtime.scene)
    if target=='cloud' and direction=='up':
        assert 0 < runtime.translation.end[1] < .3


def test_no_meaningful_room_is_transactional(runtime):
    runtime.accept('morph cloud');runtime.accept('motion auto on')
    runtime.accept('up')
    before = snapshot(runtime)
    with pytest.raises(ValueError,match='no meaningful safe movement'):
        runtime.accept('up')
    assert snapshot(runtime)==before


def test_strict_default_off_and_historical_events(runtime):
    runtime.accept('morph cloud')
    before=snapshot(runtime)
    with pytest.raises(ValueError,match='budget'): runtime.accept('up')
    assert snapshot(runtime)==before
    runtime.accept('motion auto on')
    # Historical events always mean the original strict request, even in auto.
    event={'schema_version':'cz-morph-event-0.1','sequence':len(runtime.events),
        'effective_tick':0,'command':parse_command('up')}
    before=snapshot(runtime)
    with pytest.raises(ValueError,match='budget'): runtime.apply_event(event)
    assert snapshot(runtime)==before
    runtime.accept('motion auto off')
    before=snapshot(runtime)
    with pytest.raises(ValueError,match='budget'):runtime.accept('up')
    assert snapshot(runtime)==before and not runtime.motion_auto
    with pytest.raises(ValueError): LiveRuntime(runtime.config).accept('motion auto on')


def test_deterministic_endpoint_supersession_and_maximality(runtime):
    other=MorphRuntime(runtime.config,runtime.targets)
    for r in (runtime,other):
        r.accept('morph cloud'); r.accept('right .05'); advance(r,45)
        r.accept('stretch .1'); r.accept('motion auto on')
    origin=runtime.translation.end.copy()
    current=runtime.translation.at(runtime.state.tick).copy()
    e=runtime.accept('up')['command']
    assert e==other.accept('up')['command']
    assert np.array_equal(runtime.translation.start,current)
    assert np.array_equal(runtime.translation.end,origin+e['fraction']*(np.array([0.,.3])-origin))
    assert 0<e['fraction']<1
    candidate=Blend([0,0]); candidate.start=current
    candidate.end=origin+(e['fraction']+2**-47)*(np.array([0.,.3])-origin)
    with pytest.raises(ValueError,match='budget'):runtime._admit(translation=candidate)
    assert_corners_safe(runtime)


@pytest.mark.parametrize('seconds',['.5','10'])
def test_duration_does_not_authorize_endpoint(runtime,seconds):
    runtime.accept('morph cloud');runtime.accept('motion auto on')
    c=runtime.accept('up .3 '+seconds)['command']
    other=MorphRuntime(runtime.config,runtime.targets)
    other.accept('morph cloud');other.accept('motion auto on')
    assert c['effective_translation']==other.accept('up .3 2')['command']['effective_translation']


@pytest.mark.parametrize('limit', ['max_total_force','max_displacement'])
def test_each_admission_limit_remains_authoritative(runtime,limit):
    c=deepcopy(runtime.config);c['wander']=False
    c['scene']['limits'][limit]=1. if limit=='max_total_force' else .1
    r=MorphRuntime(c,{'home':runtime.targets['home']})
    r.accept('motion auto on');e=r.accept('right')['command']
    assert 0<e['fraction']<1
    assert .099999999999 < r.translation.end[0] <= .1
    assert_corners_safe(r)
    if limit=='max_displacement':
        # Target admission does not replace the existing dynamic state guard.
        with pytest.raises(LiveNumericalError,match='DISPLACEMENT_LIMIT'):
            for _ in range(360):
                previous=r.state
                r.step()
        assert r.state is previous and not validate_state(r.state,r.scene)
    else:
        advance(r,360)
        assert not validate_state(r.state,r.scene)


@pytest.mark.parametrize('text',['motion auto','motion auto yes','motion gentle','up nan','up .31','up .01',
    'up .3 .1','motion auto on extra','squash .7'])
def test_invalid_commands_never_mutate(runtime,text):
    runtime.accept('morph cloud');runtime.accept('motion auto on')
    before=snapshot(runtime)
    with pytest.raises(ValueError):runtime.accept(text)
    assert snapshot(runtime)==before


@pytest.mark.parametrize('mutation',[
    lambda e:e['command'].update(fraction=.1),
    lambda e:e['command'].update(effective_translation=[0.,.3]),
    lambda e:e['command'].update(algorithm='other'),
    lambda e:e['command']['requested'].update(strength=True),
    lambda e:e['command']['requested'].update(duration_ticks=True),
    lambda e:e['command']['requested'].update(scope='head'),
    lambda e:e.update(schema_version='cz-morph-event-0.1')])
def test_tampered_decisions_never_mutate(runtime,mutation):
    runtime.accept('morph cloud');runtime.accept('motion auto on')
    other=MorphRuntime(runtime.config,runtime.targets)
    for event in runtime.events:other.apply_event(event)
    event=other.accept('up');mutation(event)
    before=snapshot(runtime)
    with pytest.raises(ValueError):runtime.apply_event(event)
    assert snapshot(runtime)==before


def test_record_replay_effective_values_and_session_version(tmp_path,runtime):
    rec=MorphRecorder(tmp_path/'take',runtime)
    for text in ('morph cloud','motion auto on','up'):
        rec.record_event(runtime.accept(text))
    advance(runtime,360)
    rec.record_event(runtime.accept('capture moved_cloud'))
    path=rec.finish(runtime)
    doc=read_json(path)
    assert doc['schema_version']=='cz-morph-session-0.2'
    assert doc['events'][2]['command']['requested']['strength']==.3
    assert verify_session(path)['exact_replay']
    replay=list(replay_runtimes(path))[-1]
    assert replay.channels()==runtime.channels() and replay.motion_auto
    assert replay.trajectory_sha256==runtime.trajectory_sha256
    # A historical container cannot be repurposed for extended events.
    doc['schema_version']='cz-morph-session-0.1'
    doc['session_sha256']=sha256(canonical_bytes({k:v for k,v in doc.items() if k!='session_sha256'}))
    atomic_json(path,doc)
    with pytest.raises(ValueError,match='historical'):verify_session(path)


def test_feedback_visible_in_terminal(runtime):
    from commander_zorg.morph_lab import _viewport
    runtime.accept('morph cloud');runtime.accept('motion auto on')
    e=runtime.accept('up');feedback=runtime.command_feedback(e)
    lines=_viewport(runtime,os.terminal_size((100,24)),status=feedback,mono=True)
    text='\n'.join(lines)
    assert 'STATUS: ADAPTIVE MOTION ACCEPTED' in text
    assert 'REQUESTED: 0.3' in text and 'APPLIED: 0.0744372057' in text
    assert 'SHAPE: CLOUD — PRESERVED' in text


def test_auto_never_repairs_invalid_simulation_state(runtime):
    runtime.accept('motion auto on');runtime.accept('right')
    runtime.translation.start=runtime.translation.end=np.array([2.,2.])
    state=runtime.state
    with pytest.raises(LiveNumericalError):runtime.step()
    assert runtime.state is state


def test_interactive_auto_feedback_and_recording(tmp_path):
    import fcntl, select, struct, subprocess, sys, termios, time
    master,slave=os.openpty();previous=termios.tcgetattr(slave)
    fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,100,0,0))
    code='''from pathlib import Path
from commander_zorg.canonical import read_json
from commander_zorg.live_motion import LiveRuntime
from commander_zorg.morph_targets import load_targets
from commander_zorg.morph_lab import run_lab
import sys
c=read_json('scenes/live_lab.json')
t=load_targets('morph_targets',LiveRuntime(c).scene)
run_lab(c,t,Path(sys.argv[1])/'take',mono=True,max_seconds=8)
'''
    def controlling_terminal():
        os.setsid();fcntl.ioctl(0,termios.TIOCSCTTY,0)
    child=subprocess.Popen([sys.executable,'-c',code,str(tmp_path)],cwd=ROOT,
        stdin=slave,stdout=slave,stderr=subprocess.PIPE,preexec_fn=controlling_terminal)
    output=b''
    def until(text):
        nonlocal output
        deadline=time.monotonic()+6
        while time.monotonic()<deadline:
            if select.select([master],[],[],.05)[0]:output+=os.read(master,65536)
            if text in output:return
            if child.poll() is not None:break
        raise AssertionError(f'missing {text!r}: {output[-1000:]!r}')
    try:
        until(b'COMMAND:')
        for command,feedback in [(b'morph cloud\r',b'MORPH accepted'),
                (b'motion auto on\r',b'MOTION AUTO ON'),
                (b'up\r',b'ADAPTIVE MOTION ACCEPTED')]:
            os.write(master,command);until(feedback)
        until(b'APPLIED: 0.0744372057')
        until('SHAPE: CLOUD — PRESERVED'.encode())
        os.write(master,b'quit\r');until(b'\x1b[?25h\x1b[?1049l')
        child.wait(timeout=6)
        assert child.returncode==0,child.stderr.read().decode()
        assert termios.tcgetattr(slave)==previous
        path=tmp_path/'take/session.json'
        assert verify_session(path)['exact_replay']
        assert read_json(path)['events'][-1]['command']['requested']['strength']==.3
    finally:
        if child.poll() is None:child.kill();child.wait()
        child.stderr.close();os.close(master);os.close(slave)


def test_effective_strength_below_historical_grammar_minimum(runtime):
    config=deepcopy(runtime.config);config['wander']=False
    config['scene']['limits']['max_total_force']=.2
    r=MorphRuntime(config,{'home':runtime.targets['home']})
    r.accept('motion auto on');event=r.accept('right')
    assert 0<r.translation.end[0]<.05
    other=MorphRuntime(config,{'home':runtime.targets['home']})
    for e in r.events:other.apply_event(e)
    assert np.array_equal(other.translation.end,r.translation.end)
    advance(r,360)
    assert not validate_state(r.state,r.scene)
    with pytest.raises(ValueError):parse_command('right '+str(event['command']['effective_translation'][0]))


@pytest.mark.parametrize('text',['stretch .6','squash .6','wander off','reset','morph hill'])
def test_auto_does_not_adapt_other_channels(runtime,text):
    strict=MorphRuntime(runtime.config,runtime.targets)
    for r in (runtime,strict):r.accept('morph cloud')
    runtime.accept('motion auto on')
    before=snapshot(runtime)
    try:
        expected=strict.accept(text)
    except ValueError:
        with pytest.raises(ValueError):runtime.accept(text)
        assert snapshot(runtime)==before
    else:
        event=runtime.accept(text)
        assert event['schema_version']=='cz-morph-event-0.1'
        assert event['command']==expected['command']
        assert runtime.channels()==strict.channels()
