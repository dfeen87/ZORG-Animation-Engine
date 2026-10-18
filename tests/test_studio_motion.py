"""Future-only creator admission and immutable historical semantics."""
from copy import deepcopy
from pathlib import Path
import numpy as np
import pytest
from commander_zorg.canonical import read_json, canonical_bytes
from commander_zorg.live_motion import LiveRuntime
from commander_zorg.morph_targets import load_targets
from commander_zorg.morph_runtime import MorphRuntime
from commander_zorg.studio_runtime import StudioRuntime
from commander_zorg.morph_session import MorphRecorder, verify_session
from commander_zorg.guard import validate_state

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def studio():
    config = read_json(ROOT/'scenes/live_lab.json')
    return StudioRuntime(config, load_targets(ROOT/'morph_targets', LiveRuntime(config).scene))

def advance(r, count=240):
    for _ in range(count):
        r.step()
        assert not validate_state(r.state, r.scene)

def snapshot(r):
    return canonical_bytes({'channels': r.channels(), 'events': r.events,
                            'trace': r.trajectory_sha256, 'auto': r.motion_auto})

def test_settled_wander_releases_budget_once(studio):
    for c in ('morph cloud', 'wander off', 'motion auto on'):
        studio.accept(c)
    advance(studio)
    studio.accept('up')
    assert studio.translation.end[1] == pytest.approx(.233537470650, abs=1e-11)
    advance(studio, 360)

def test_settled_return_home_releases_past_shape(studio):
    studio.accept('morph cloud'); advance(studio)
    studio.accept('morph home'); advance(studio)
    studio.accept('motion auto on'); studio.accept('up')
    assert np.array_equal(studio.translation.end, [0., .3])
    advance(studio)

@pytest.mark.parametrize('auto', [False, True])
def test_safe_repeated_absolute_target_is_not_false_success(studio, auto):
    if auto: studio.accept('motion auto on')
    studio.accept('up')
    before = snapshot(studio)
    with pytest.raises(ValueError, match='TARGET ALREADY SET'):
        studio.accept('up')
    assert snapshot(studio) == before

def test_saturated_rejection_is_transactional_and_direction_change_works(studio):
    studio.accept('morph cloud'); studio.accept('motion auto on'); studio.accept('up')
    before = snapshot(studio)
    with pytest.raises(ValueError, match='LIMIT REACHED'): studio.accept('up')
    assert snapshot(studio) == before
    # A tangent change can itself have no feasible segment at a boundary;
    # moving back toward the interior is a meaningful safe alternative.
    studio.accept('down .05'); advance(studio)
    studio.accept('up')
    advance(studio)

def test_historical_events_keep_stale_corner_semantics(studio):
    old = MorphRuntime(studio.config, studio.targets)
    for command in ('morph cloud', 'wander off'):
        studio.apply_event(old.accept(command))
    advance(studio); advance(old)
    for command in ('motion auto on', 'up'):
        studio.apply_event(old.accept(command))
    assert studio.channels() == old.channels()
    assert studio.translation.end[1] == pytest.approx(.074437205685)

def test_studio_recording_replays_and_rejects_forged_algorithm(studio, tmp_path):
    rec = MorphRecorder(tmp_path/'take', studio)
    for command in ('morph cloud', 'wander off', 'motion auto on'):
        rec.record_event(studio.accept(command))
    advance(studio)
    rec.record_event(studio.accept('up'))
    advance(studio)
    path = rec.finish(studio)
    assert read_json(path)['schema_version'] == 'cz-morph-session-0.3'
    assert verify_session(path)['exact_replay']
    bad = deepcopy(studio.events[0]); bad['sequence'] = len(studio.events)
    bad['effective_tick'] = studio.state.tick
    bad['command']['admission'] = 'unsafe'
    before = snapshot(studio)
    with pytest.raises(ValueError): studio.apply_event(bad)
    assert snapshot(studio) == before
