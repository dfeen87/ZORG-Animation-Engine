from copy import deepcopy
import numpy as np
import pytest
from test_studio_motion import studio, advance
from commander_zorg.studio_runtime import StudioRuntime
from commander_zorg.morph_session import MorphRecorder, verify_session, replay_runtimes
from commander_zorg.canonical import canonical_bytes, sha256
from commander_zorg.morph_export import pixels_for


def snapshot(r):
    return canonical_bytes({'events': r.events, 'channels': r.channels(),
                            'color': r.chromatic.mapping(), 'captures': r.captures,
                            'trace': r.trajectory_sha256})


def test_color_and_palette_do_not_change_physics_or_gray(studio):
    other = StudioRuntime(studio.config, studio.targets)
    studio.accept('color on'); studio.accept('palette cloud')
    for c in ('morph oval', 'motion auto on', 'up .05'):
        studio.accept(c); other.accept(c)
    for _ in range(240):
        studio.step(); other.step()
    assert studio.trajectory_sha256 == other.trajectory_sha256
    assert np.array_equal(pixels_for(studio.state, studio.scene), pixels_for(other.state, other.scene))
    assert studio.chromatic.palette_name == 'cloud'
    studio.accept('palette auto')
    assert studio.chromatic.palette_name == 'oval'


@pytest.mark.parametrize('targets', [('home','cloud'),('oval','cloud'),('cloud','circle'),('cloud','home')])
def test_shape_palette_and_interruption_are_continuous(studio, targets):
    studio.accept('color on'); studio.accept('morph '+targets[0]); advance(studio)
    studio.accept('morph '+targets[1]+' 2'); advance(studio, 31)
    before = studio.chromatic.palette.at(studio.state.tick).copy()
    studio.accept('morph hill .5')
    assert np.array_equal(studio.chromatic.palette.at(studio.state.tick), before)
    assert studio.chromatic.palette_name == 'hill'
    advance(studio)


def test_color_settings_record_replay_capture_and_tamper(studio, tmp_path):
    rec = MorphRecorder(tmp_path/'take', studio)
    for c in ('color on', 'palette auto', 'morph cloud', 'motion auto on', 'up'):
        rec.record_event(studio.accept(c)); advance(studio, 10)
    rec.record_event(studio.accept('capture Blue'))
    capture = studio.captures[-1]
    assert capture['schema_version'] == 'cz-morph-capture-0.3'
    assert capture['id'] == sha256(canonical_bytes({k:v for k,v in capture.items() if k != 'id'}))
    path = rec.finish(studio)
    assert verify_session(path)['exact_replay']
    assert list(replay_runtimes(path))[-1].chromatic.mapping() == studio.chromatic.mapping()


@pytest.mark.parametrize('command', [
    {'action':'color','enabled':1}, {'action':'color','enabled':True,'extra':False},
    {'action':'palette','name':'cloud','duration_ticks':True},
    {'action':'palette','name':'cloud','duration_ticks':60},
    {'action':'palette','name':'custom','duration_ticks':120},
    {'action':'creator','admission':'future-corners-v1','operation':{'action':'motion','motion':None}},
    {'action':'creator','admission':'future-corners-v1','operation':{'action':'motion','motion':{'action':[]}}},
    {'action':'creator','admission':'future-corners-v1','operation':{'action':'morph','target':'cloud','duration_ticks':10**400}},
])
def test_malformed_events_are_atomic(studio, command):
    event = {'schema_version':'cz-morph-event-0.3','sequence':0,'effective_tick':0,'command':command}
    before = snapshot(studio)
    with pytest.raises(ValueError): studio.apply_event(event)
    assert snapshot(studio) == before


@pytest.mark.parametrize('text', ['color','color yes','color on extra','palette custom','palette cloud .5'])
def test_invalid_color_grammar(studio, text):
    before = snapshot(studio)
    with pytest.raises(ValueError): studio.accept(text)
    assert snapshot(studio) == before
