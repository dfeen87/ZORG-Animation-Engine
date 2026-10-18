from copy import deepcopy
import pytest
import numpy as np
from test_studio_motion import studio, advance
from commander_zorg.studio_commands import parse_command, MOTION_PRESETS, SPEED_PRESETS
from commander_zorg.studio_runtime import StudioRuntime
from commander_zorg.morph_session import MorphRecorder, verify_session, replay_runtimes
from commander_zorg.canonical import canonical_bytes


@pytest.mark.parametrize('name,value', list(MOTION_PRESETS.items()))
@pytest.mark.parametrize('speed,ticks', list(SPEED_PRESETS.items()))
def test_presets_equal_explicit_normalized_commands(studio, name, value, speed, ticks):
    other = StudioRuntime(studio.config, studio.targets)
    studio.accept('motion '+name); studio.accept('speed '+speed)
    a = studio.accept('up')['command']['operation']
    b = other.accept(f'up {value} {ticks/60}')['command']['operation']
    assert a == b
    advance(studio, 300); advance(other, 300)
    assert np.array_equal(studio.state.positions, other.state.positions)
    assert studio.trajectory_sha256 == other.trajectory_sha256


def test_preset_persistence_explicit_override_and_replay(studio, tmp_path):
    rec = MorphRecorder(tmp_path/'take', studio)
    for c in ('motion gentle', 'speed slow', 'up', 'left .2 .5', 'morph oval'):
        rec.record_event(studio.accept(c)); advance(studio, 30)
    assert studio.motion_preset == 'gentle' and studio.speed_preset == 'slow'
    assert studio.events[-1]['command']['operation']['duration_ticks'] == 240
    assert studio.events[-2]['command']['operation']['motion']['duration_ticks'] == 30
    path = rec.finish(studio)
    assert verify_session(path)['exact_replay']
    replay = list(replay_runtimes(path))[-1]
    assert replay.creator_status() == studio.creator_status()


@pytest.mark.parametrize('text', ['motion enormous', 'motion gentle extra', 'speed instant',
                                  'speed fast extra', 'up nan', 'up .31', 'morph cloud inf'])
def test_invalid_creator_inputs_are_atomic(studio, text):
    before = canonical_bytes(studio.events)
    with pytest.raises(ValueError): studio.accept(text)
    assert canonical_bytes(studio.events) == before


def test_tampered_preset_is_atomic(studio):
    other = StudioRuntime(studio.config, studio.targets)
    event = other.accept('motion gentle'); event['command']['strength'] = .3
    with pytest.raises(ValueError): studio.apply_event(event)
    assert studio.motion_preset == 'bold' and not studio.events


def test_speed_changes_timing_not_admission(studio):
    endpoints = []
    for name in SPEED_PRESETS:
        r = StudioRuntime(studio.config, studio.targets)
        for c in ('morph cloud', 'motion auto on', 'speed '+name, 'up'): r.accept(c)
        endpoints.append(r.translation.end.tolist())
    assert endpoints[0] == endpoints[1] == endpoints[2]
