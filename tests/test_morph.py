"""Build 0.2 acceptance: geometry, independent integration, guards and evidence."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from scripts.pty_support import PtyProcess
from commander_zorg.canonical import read_json,atomic_json,canonical_bytes,sha256
from commander_zorg.live_motion import LiveRuntime,LiveNumericalError
from commander_zorg.morph_targets import load_targets,validate_target
from commander_zorg.morph_commands import parse_command
from commander_zorg.morph_runtime import MorphRuntime
from commander_zorg.morph_session import MorphRecorder,verify_session,load_session,replay_runtimes
from commander_zorg.morph_export import render_session,verify_export,pixels_for,metrics_for
from commander_zorg.state import state_mapping,owned_state
from commander_zorg.guard import validate_state

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def config():
    return read_json(ROOT/'scenes/live_lab.json')

@pytest.fixture
def targets(config):
    return load_targets(ROOT/'morph_targets',LiveRuntime(config).scene)

@pytest.fixture
def runtime(config,targets):
    return MorphRuntime(config,targets)


def advance(r,ticks):
    for _ in range(ticks): r.step()


def record(tmp_path,config,targets,status='complete',ticks=6):
    r=MorphRuntime(config,targets); rec=MorphRecorder(tmp_path/'take',r)
    rec.record_event(r.accept('wander off')); rec.record_event(r.accept('morph circle .5'))
    advance(r,ticks); rec.record_event(r.accept('capture Test_01'))
    return rec.finish(r,status=status),r


@pytest.mark.parametrize('target',['home','circle','oval','cloud','hill'])
def test_target_reproducible(config,targets,target):
    scene=LiveRuntime(config).scene
    t=validate_target(targets[target],scene)
    p=scene.home_xy+np.array(t['offsets'])
    state=owned_state(0,p,np.zeros_like(p))
    assert not validate_state(state,scene)
    pixels=pixels_for(state,scene)
    assert np.array_equal(pixels,pixels_for(state,scene))
    metrics=metrics_for(pixels,scene)
    assert not metrics['empty'] and not metrics['clipping']
    if target=='circle':
        assert np.array_equal(pixels,pixels[:,::-1])
        assert metrics['aspect_width_height']==1
    if target=='oval': assert metrics['aspect_width_height']<.6
    if target=='hill': assert metrics['aspect_width_height']>1.6
    if target=='cloud': assert metrics['upper_lobes']>=3


@pytest.mark.parametrize('mutation',[lambda t:t.update(schema_version='bad'),
    lambda t:t.update(extra=True),lambda t:t.update(basis='pixels'),
    lambda t:t.update(element_ids=list(reversed(t['element_ids']))),
    lambda t:t.update(field_sha256='0'*64),lambda t:t['offsets'][0].__setitem__(0,float('nan')),
    lambda t:t['offsets'][0].__setitem__(0,2.),lambda t:t['offsets'][0].__setitem__(0,True),
    lambda t:t.update(offsets=[[0,0]]),lambda t:t.update(id='../escape')])
def test_malformed_targets(config,targets,mutation):
    t=deepcopy(targets['circle']); mutation(t)
    with pytest.raises(ValueError): validate_target(t,LiveRuntime(config).scene)


@pytest.mark.parametrize('text',['morph','morph circle 0','morph circle nan','morph circle inf',
    'morph circle 11','morph circle 2 extra','morph ../circle','capture ../a','capture a/b',
    'capture a\\b','capture .','capture a b','capture','capture 123','capture '+('a'*65)])
def test_command_rejections(text):
    with pytest.raises(ValueError): parse_command(text)


@pytest.mark.parametrize('seconds,ticks',[('.5',30),('2',120),('10',600),('1.01',61)])
def test_duration_quantization(seconds,ticks):
    assert parse_command('morph circle '+seconds)['duration_ticks']==ticks


def test_baseline_equivalence(config,targets):
    a=LiveRuntime(config); b=MorphRuntime(config,targets)
    for text in ('right .1','stretch .2','wander off','reset'):
        a.accept(text); b.accept(text)
        for _ in range(120):
            a.step(); b.step()
            assert np.array_equal(a.state.positions,b.state.positions)
            assert np.array_equal(a.state.velocities,b.state.velocities)


def test_independent_euler_step(runtime):
    runtime.accept('morph cloud .5'); advance(runtime,10)
    p=runtime.state.positions.copy(); v=runtime.state.velocities.copy(); s=runtime.scene
    offsets=runtime.target_offsets(runtime.state.tick)
    # Independent scalar spring calculation in the accepted arithmetic grouping.
    expected_p=np.empty_like(p); expected_v=np.empty_like(v)
    for i in range(len(p)):
        for j in range(2):
            force=s.spring_k[i]*offsets[i,j]
            acceleration=(-s.spring_k[i]*(p[i,j]-s.home_xy[i,j])-s.damping_c[i]*v[i,j]+force)/s.mass[i]
            expected_v[i,j]=v[i,j]+(1/60)*acceleration
            expected_p[i,j]=p[i,j]+(1/60)*expected_v[i,j]
    runtime.step()
    assert np.array_equal(expected_p,runtime.state.positions)
    assert np.array_equal(expected_v,runtime.state.velocities)


@pytest.mark.parametrize('target',['circle','oval','cloud','hill'])
def test_completion_and_home(runtime,target):
    runtime.accept('wander off'); advance(runtime,180)
    runtime.accept(f'morph {target} .5'); advance(runtime,360)
    desired=runtime.scene.home_xy+np.array(runtime.targets[target]['offsets'])
    assert np.linalg.norm(runtime.state.positions-desired,axis=1).max()<1e-5
    assert np.array_equal(runtime.shape.at(runtime.state.tick),runtime.shape.end)
    runtime.accept('morph home .5'); advance(runtime,360)
    assert np.linalg.norm(runtime.state.positions-runtime.scene.home_xy,axis=1).max()<1e-5


def test_supersession_no_jump(runtime):
    runtime.accept('morph circle'); advance(runtime,40)
    position=runtime.state.positions.copy(); offset=runtime.target_offsets(runtime.state.tick).copy()
    runtime.accept('morph oval')
    assert np.array_equal(runtime.state.positions,position)
    assert np.array_equal(runtime.target_offsets(runtime.state.tick),offset)
    runtime.step()
    assert np.linalg.norm(runtime.state.positions-position,axis=1).max()<.02


def test_translation_and_wander_independent(runtime):
    runtime.accept('morph oval'); advance(runtime,240)
    shape=runtime.shape.end.copy()
    runtime.accept('up .05'); advance(runtime,240)
    assert np.array_equal(runtime.shape.end,shape)
    runtime.accept('morph cloud'); advance(runtime,240)
    assert np.array_equal(runtime.translation.end,[0,.05])
    runtime.accept('left .05'); advance(runtime,240)
    assert np.array_equal(runtime.shape.end,runtime.targets['cloud']['offsets'])
    assert runtime.wander


def test_rejected_command_transaction(runtime):
    runtime.accept('morph hill'); advance(runtime,180)
    before=canonical_bytes({'channels':runtime.channels(),'events':runtime.events,'state':state_mapping(runtime.state)})
    with pytest.raises(ValueError,match='budget'): runtime.accept('right .3')
    assert before==canonical_bytes({'channels':runtime.channels(),'events':runtime.events,'state':state_mapping(runtime.state)})
    with pytest.raises(ValueError,match='unsupported'): runtime.accept('morph head_base')


def test_force_rejection_never_repairs(runtime):
    runtime.shape.start=runtime.shape.end=np.ones_like(runtime.scene.home_xy)*2
    before=runtime.state
    with pytest.raises(LiveNumericalError): runtime.step()
    assert runtime.state is before


def test_capture_committed_state(runtime):
    runtime.accept('morph oval'); advance(runtime,43)
    before=state_mapping(runtime.state)
    event=runtime.accept('capture Face_attempt_01')
    c=runtime.captures[0]
    assert c['state']==before and c['tick']==43 and c['label']=='Face_attempt_01'
    assert c['id']==sha256(canonical_bytes({k:v for k,v in c.items() if k!='id'}))
    assert c['channels']==runtime.channels() and c['active_target']=='oval'
    advance(runtime,10)
    assert c['state']==before
    with pytest.raises(ValueError,match='already exists'): runtime.accept('capture Face_attempt_01')
    assert len(runtime.captures)==1


@pytest.mark.parametrize('status',['complete','interrupted'])
def test_exact_replay_and_export(tmp_path,config,targets,status):
    session,r=record(tmp_path,config,targets,status)
    assert verify_session(session)=={'passed':True,'states':7,'final_tick':6,'exact_replay':True}
    assert list(replay_runtimes(session))[-1].captures==r.captures
    result=render_session(session,tmp_path/'video',mp4=False)
    assert result['frames']==3
    assert verify_export(tmp_path/'video/manifest.json')['passed']
    with pytest.raises(FileExistsError): render_session(session,tmp_path/'video',mp4=False)
    capture=read_json(tmp_path/'video/captures/Test_01.json')
    assert capture['capture']==r.captures[0]
    png=(tmp_path/'video/captures/Test_01.png').read_bytes()
    assert sha256(png)==capture['preview_sha256']


@pytest.mark.parametrize('field',['source','trajectory_sha256','final_state_sha256','captures','events','status'])
def test_tampered_sessions_rejected(tmp_path,config,targets,field):
    path,r=record(tmp_path,config,targets)
    doc=read_json(path)
    if field=='source': doc[field]={}
    elif field in ('captures','events'): doc[field]=[]
    elif field=='status': doc[field]='failed'
    else: doc[field]='0'*64
    doc['session_sha256']=sha256(canonical_bytes({k:v for k,v in doc.items() if k!='session_sha256'}))
    atomic_json(path,doc)
    with pytest.raises(ValueError): verify_session(path)


@pytest.mark.parametrize('name',['frames/frame_000000.png','states.jsonl','captures/Test_01.json','player.html'])
def test_tampered_export_rejected(tmp_path,config,targets,name):
    path,_=record(tmp_path,config,targets)
    render_session(path,tmp_path/'video',mp4=False)
    (tmp_path/'video'/name).write_bytes(b'corrupted')
    with pytest.raises(ValueError): verify_export(tmp_path/'video/manifest.json')


def test_session_running_and_journal_mismatch(tmp_path,runtime):
    recorder=MorphRecorder(tmp_path/'take',runtime)
    with pytest.raises(ValueError): load_session(tmp_path/'take/session.json')
    runtime.accept('morph circle')
    with pytest.raises(ValueError,match='journal'): recorder.finish(runtime)


@pytest.mark.parametrize('mutation',[lambda e:e.update(schema_version='cz-live-event-0.1'),
    lambda e:e.update(sequence=True),lambda e:e.update(effective_tick=1),lambda e:e.update(extra=0),
    lambda e:e['command'].update(duration_ticks=True),lambda e:e['command'].update(duration_ticks=1),
    lambda e:e['command'].update(extra=0)])
def test_invalid_event_rejected(runtime,mutation):
    event={'schema_version':'cz-morph-event-0.1','sequence':0,'effective_tick':0,
        'command':{'action':'morph','target':'circle','duration_ticks':120}}
    mutation(event)
    with pytest.raises(ValueError): runtime.apply_event(event)
    assert not runtime.events


def test_non_tty_fails_before_recording(tmp_path,config,targets):
    from io import StringIO
    from commander_zorg.morph_lab import run_lab
    with pytest.raises(ValueError,match='interactive terminal'):
        run_lab(config,targets,tmp_path/'take',input_stream=StringIO(),output_stream=StringIO())
    assert not (tmp_path/'take').exists()


def test_components_measurement():
    from commander_zorg.morph_export import component_count
    assert component_count(np.zeros((4,4),dtype=bool))==0
    assert component_count(np.ones((4,4),dtype=bool))==1
    assert component_count(np.eye(4,dtype=bool))==4
    assert component_count(np.array([[1,0,1],[1,1,1]],dtype=bool))==1


def test_capture_reload(tmp_path,config,targets):
    from commander_zorg.morph_export import load_capture
    path,r=record(tmp_path,config,targets)
    render_session(path,tmp_path/'video',mp4=False)
    capture,state=load_capture(tmp_path/'video/captures/Test_01.json',config)
    assert capture==r.captures[0] and state_mapping(state)==capture['state']
    (tmp_path/'video/captures/Test_01.png').write_bytes(b'bad')
    with pytest.raises(ValueError): load_capture(tmp_path/'video/captures/Test_01.json',config)


def test_capture_invalid_state_rejected(runtime):
    runtime.state=owned_state(0,np.ones_like(runtime.state.positions)*2,runtime.state.velocities)
    with pytest.raises(ValueError,match='invalid committed'): runtime.accept('capture invalid')
    assert not runtime.captures and not runtime.events


def test_motion_payload_cannot_override_event(runtime):
    from commander_zorg.live_commands import parse_command
    event={'schema_version':'cz-morph-event-0.1','sequence':0,'effective_tick':0,
        'command':{'action':'motion','motion':{**parse_command('left .05'),'sequence':0}}}
    with pytest.raises(ValueError): runtime.apply_event(event)
    assert not runtime.events


@pytest.mark.parametrize('ending,expected',[(b'quit\r','complete'),(b'\x03','interrupted'),(b'save\r','complete')])
def test_real_morph_pty(tmp_path,ending,expected):
    import os,sys,select,subprocess,termios,time,fcntl,struct
    code="""from pathlib import Path
from commander_zorg.canonical import read_json,atomic_json
from commander_zorg.live_motion import LiveRuntime
from commander_zorg.morph_targets import load_targets
from commander_zorg.morph_lab import run_lab
import sys
c=read_json(Path('scenes/live_lab.json'))
t=load_targets('morph_targets',LiveRuntime(c).scene)
result=run_lab(c,t,Path(sys.argv[1])/'take',mono=True,max_seconds=5)
atomic_json(Path(sys.argv[1])/'result.json',result)
"""
    take=PtyProcess(code,(tmp_path,),cwd=ROOT,size=(100,24))
    master,slave=take.master,take.slave
    previous=take.previous
    process=take.process
    output=b''
    def until(text):
        nonlocal output
        take.wait_for(lambda data:text in data,timeout=6)
        output=take.output
    try:
        until(b'COMMAND:')
        os.write(master,b'morph circle .5\r')
        until(b'MORPH accepted at tick')
        os.write(master,b'capture My_shape\r')
        until(b'CAPTURE accepted at tick')
        os.write(master,ending)
        until(b'\x1b[?25h\x1b[?1049l')
        take.wait(timeout=6)
        output=take.output
        assert process.returncode==0,take.stderr.decode()
        assert termios.tcgetattr(slave)==previous
        assert b'\x1b[?25h\x1b[?1049l' in output
        doc=load_session(tmp_path/'take/session.json')
        assert doc['status']==expected and len(doc['events'])==2
        assert doc['captures'][0]['label']=='My_shape'
        assert verify_session(tmp_path/'take/session.json')['passed']
        result=read_json(tmp_path/'result.json')
        assert result['save_requested']==(ending==b'save\r')
    finally:
        take.close()


def test_reindexed_false_continuity_rejected(tmp_path,config,targets):
    from commander_zorg.morph_export import _artifacts
    path,_=record(tmp_path,config,targets)
    root=tmp_path/'video';render_session(path,root,mp4=False)
    measurements=read_json(root/'measurements.json');measurements['max_control_step']=0
    atomic_json(root/'measurements.json',measurements)
    manifest=read_json(root/'manifest.json');manifest['artifacts']=_artifacts(root)
    atomic_json(root/'manifest.json',manifest)
    with pytest.raises(ValueError,match='continuity'): verify_export(root/'manifest.json')
