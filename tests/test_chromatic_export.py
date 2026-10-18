"""Independent coverage and RGB replay contracts for opt-in studio exports."""
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from commander_zorg.canonical import atomic_json,canonical_bytes,read_json,read_jsonl,sha256
from commander_zorg.chromatic import ALGORITHM,ChromaticState,encode_rgb_png
from commander_zorg.live_motion import LiveRuntime
from commander_zorg.morph_export import _artifacts,load_capture,pixels_for,render_session,verify_export
from commander_zorg.morph_session import MorphRecorder,replay_runtimes
from commander_zorg.morph_targets import load_targets
from commander_zorg.raster import encode_gray_png
from commander_zorg.studio_runtime import StudioRuntime

ROOT=Path(__file__).resolve().parents[1]


def record(tmp_path,enabled=True,turn_off=False,ticks=6):
    config=read_json(ROOT/'scenes/live_lab.json')
    targets=load_targets(ROOT/'morph_targets',LiveRuntime(config).scene)
    runtime=StudioRuntime(config,targets)
    recorder=MorphRecorder(tmp_path/'take',runtime)
    for command in ('wander off','capture Before'):
        recorder.record_event(runtime.accept(command))
    if enabled:
        recorder.record_event(runtime.accept('color on'))
    recorder.record_event(runtime.accept('morph cloud .5'))
    for _ in range(ticks):
        runtime.step()
    recorder.record_event(runtime.accept('capture After'))
    if turn_off:
        recorder.record_event(runtime.accept('color off'))
    return recorder.finish(runtime),runtime


def rehash(root):
    manifest=read_json(root/'manifest.json')
    manifest['artifacts']=_artifacts(root)
    atomic_json(root/'manifest.json',manifest)


def test_rgb_export_reproduces_pixels_and_keeps_independent_coverage(tmp_path):
    session,_=record(tmp_path)
    root=tmp_path/'rgb'
    render_session(session,root,mp4=False)
    manifest=read_json(root/'manifest.json')
    assert manifest['schema_version']=='cz-morph-export-0.3'
    assert manifest['presentation']=={'mode':'rgb','algorithm':ALGORITHM,'seed':172026}
    rows=read_jsonl(root/'frames.jsonl')
    for runtime in replay_runtimes(session):
        tick=runtime.state.tick
        if tick>=6 or tick%2:
            continue
        coverage=pixels_for(runtime.state,runtime.scene)
        rgb=runtime.chromatic.rgb(coverage,runtime.state,runtime.scene,runtime.config['seed'],tick)
        row=rows[tick//2]
        assert row['coverage_sha256']==sha256(coverage.tobytes())
        assert row['pixels_sha256']==sha256(rgb.tobytes())
        assert row['chromatic']==runtime.chromatic.mapping()
        assert (root/row['path']).read_bytes()==encode_rgb_png(rgb)
        with Image.open(root/row['path']) as image:
            assert image.mode=='RGB'
    assert verify_export(root/'manifest.json')=={'passed':True,'frames':3,'states':7,'captures':2,'exact_replay':True}


@pytest.mark.parametrize('enabled,color,mode,version',[
    (True,False,'L','cz-morph-export-0.1'),
    (False,None,'L','cz-morph-export-0.1'),
    (False,True,'RGB','cz-morph-export-0.3'),
])
def test_gray_and_rgb_modes_are_independent(tmp_path,enabled,color,mode,version):
    session,_=record(tmp_path,enabled=enabled)
    root=tmp_path/'video'
    render_session(session,root,mp4=False,color=color)
    assert read_json(root/'manifest.json')['schema_version']==version
    first=next(replay_runtimes(session))
    gray=pixels_for(first.state,first.scene)
    with Image.open(root/'frames/frame_000000.png') as image:
        assert image.mode==mode
        if mode=='L':
            assert (root/'frames/frame_000000.png').read_bytes()==encode_gray_png(gray)
        else:
            assert np.array_equal(np.asarray(image),np.repeat(gray[:,:,None],3,axis=2))
    assert verify_export(root/'manifest.json')['passed']


def test_recorded_color_on_still_selects_rgb_when_final_state_is_off(tmp_path):
    session,runtime=record(tmp_path,turn_off=True)
    assert not runtime.chromatic.enabled
    root=tmp_path/'video'
    render_session(session,root,mp4=False)
    assert read_json(root/'manifest.json')['schema_version']=='cz-morph-export-0.3'
    assert verify_export(root/'manifest.json')['passed']


def test_rgb_capture_restores_its_original_color_snapshot(tmp_path):
    session,runtime=record(tmp_path,turn_off=True)
    root=tmp_path/'video'
    render_session(session,root,mp4=False)
    for expected in runtime.captures:
        path=root/'captures'/f"{expected['label']}.json"
        capture,state=load_capture(path,runtime.config)
        assert capture==expected
        snapshot=ChromaticState.from_mapping(capture['chromatic'])
        coverage=pixels_for(state,runtime.scene)
        rgb=snapshot.rgb(coverage,state,runtime.scene,capture['seed'],capture['tick'])
        assert path.with_suffix('.png').read_bytes()==encode_rgb_png(rgb)
        if capture['label']=='Before':
            assert np.array_equal(rgb,np.repeat(coverage[:,:,None],3,axis=2))


def test_rehashed_rgb_png_tampering_is_rejected_by_exact_replay(tmp_path):
    session,_=record(tmp_path)
    root=tmp_path/'video'
    render_session(session,root,mp4=False)
    path=root/'frames/frame_000000.png'
    with Image.open(path) as image:
        altered=np.array(image)
    altered[0,0]=[1,2,3]
    encoded=encode_rgb_png(altered)
    path.write_bytes(encoded)
    frames=read_jsonl(root/'frames.jsonl')
    frames[0].update(sha256=sha256(encoded),pixels_sha256=sha256(altered.tobytes()))
    (root/'frames.jsonl').write_bytes(b''.join(canonical_bytes(row) for row in frames))
    rehash(root)
    with pytest.raises(ValueError,match='mathematical replay'):
        verify_export(root/'manifest.json')


@pytest.mark.parametrize('target',['state','frame','capture','algorithm','seed','sheet'])
def test_rehashed_color_metadata_tampering_is_rejected(tmp_path,target):
    session,_=record(tmp_path)
    root=tmp_path/'video'
    render_session(session,root,mp4=False)
    if target in ('state','frame'):
        path=root/('states.jsonl' if target=='state' else 'frames.jsonl')
        rows=read_jsonl(path)
        rows[0]['chromatic']['enabled']=not rows[0]['chromatic']['enabled']
        path.write_bytes(b''.join(canonical_bytes(row) for row in rows))
    elif target=='capture':
        path=root/'captures/Before.json'
        doc=read_json(path)
        doc['presentation']['algorithm']='unknown-color-v99'
        atomic_json(path,doc)
    elif target=='sheet':
        path=root/'contact_sheet.png'
        with Image.open(path) as image:
            altered=np.array(image)
        altered[0,0]=[1,2,3]
        path.write_bytes(encode_rgb_png(altered))
    else:
        path=root/'manifest.json'
        doc=read_json(path)
        doc['presentation'][target]='unknown-color-v99' if target=='algorithm' else 0
        atomic_json(path,doc)
    rehash(root)
    with pytest.raises(ValueError):
        verify_export(root/'manifest.json')


def test_rgb_capture_rejects_incompatible_algorithm_before_loading(tmp_path):
    session,runtime=record(tmp_path)
    root=tmp_path/'video'
    render_session(session,root,mp4=False)
    path=root/'captures/After.json'
    doc=read_json(path)
    doc['presentation']['algorithm']='unknown-color-v99'
    atomic_json(path,doc)
    with pytest.raises(ValueError,match='presentation'):
        load_capture(path,runtime.config)


def test_zero_duration_rgb_take_retains_verified_capture_and_contact_sheet(tmp_path):
    session,_=record(tmp_path,ticks=0)
    root=tmp_path/'video'
    result=render_session(session,root,mp4=False)
    assert result['frames']==0
    with Image.open(root/'contact_sheet.png') as image:
        assert image.mode=='RGB' and image.width==384
    assert verify_export(root/'manifest.json')=={'passed':True,'frames':0,'states':1,'captures':2,'exact_replay':True}


@pytest.mark.parametrize('malformed',['missing_command','bad_command','bad_operation'])
def test_invalid_color_selection_event_is_rejected_before_creating_output(tmp_path,malformed):
    session,_=record(tmp_path)
    doc=read_json(session)
    if malformed=='missing_command':
        del doc['events'][0]['command']
    elif malformed=='bad_command':
        doc['events'][0]['command']=None
    else:
        doc['events'][0]['command']['operation']=None
    doc['session_sha256']=sha256(canonical_bytes({k:v for k,v in doc.items() if k!='session_sha256'}))
    atomic_json(session,doc)
    with pytest.raises(ValueError,match='command|operation'):
        render_session(session,tmp_path/'video',mp4=False)
    assert not (tmp_path/'video').exists()
