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
from commander_zorg.state import state_mapping

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
    return canonical_bytes({'state': state_mapping(r.state),
                            'channels': r.channels(), 'events': r.events,
                            'captures': r.captures, 'active_target': r.active_target,
                            'wander': r.wander, 'motion_preset': r.motion_preset,
                            'speed_preset': r.speed_preset,
                            'chromatic': r.chromatic.mapping(),
                            'trace': r.trajectory_sha256, 'auto': r.motion_auto,
                            'future_admission': r._future_admission})


@pytest.mark.parametrize('channel,elapsed', [('wander', 60), ('shape', 30)])
def test_partial_transition_matches_independent_vertical_capacity(studio, channel, elapsed):
    studio.accept('morph cloud'); advance(studio, 360)
    studio.accept('wander off' if channel == 'wander' else 'morph home 2')
    advance(studio, elapsed)
    studio.accept('motion auto on')

    # Solve each circular constraint analytically for a pure upward endpoint:
    # y <= sqrt(cap**2 - (shape_x + wander_x)**2) - shape_y - wander_y.
    # This uses no production admission method or bisection. Current->end
    # shape corners enclose the remaining monotone quintic transition.
    tick = studio.state.tick
    current_shape = studio.shape.at(tick).copy()
    wander = .08 * max(float(studio.wander_mix.at(tick)), float(studio.wander_mix.end))
    caps = np.minimum(studio.scene.max_displacement,
                      studio.scene.max_total_force / studio.scene.spring_k)
    upper_bounds = [.3]
    for shape in (current_shape, studio.shape.end):
        for sx in (-1, 1):
            for sy in (-1, 1):
                radicand = caps**2 - (shape[:, 0] + sx*wander)**2
                assert np.all(radicand > 0)
                upper_bounds.extend((np.sqrt(radicand) - shape[:, 1] - sy*wander).tolist())
    expected = min(upper_bounds)
    # A partially finished transition releases some capacity, not all of it.
    assert .074437205685 < expected < .233537470650
    prior_channels = studio.channels()
    previous_state = studio.state
    studio.accept('up')
    assert studio.state is previous_state
    assert studio.translation.end[0] == 0.
    assert studio.translation.end[1] == pytest.approx(expected, abs=2e-14)
    assert all(studio.channels()[name] == prior_channels[name]
               for name in ('shape', 'morph', 'wander_mix'))

    # Validate actual future forces and committed states through completion.
    # Admission does not substitute for the existing dynamic guard.
    for _ in range(360):
        force = studio.scene.spring_k[:, None] * studio.target_offsets(studio.state.tick)
        assert np.max(np.linalg.norm(force, axis=1)) <= studio.scene.max_total_force
        studio.step()
        assert not validate_state(studio.state, studio.scene)

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
@pytest.mark.parametrize('settled_ticks', [0, 360])
def test_safe_repeated_absolute_target_is_not_false_success(studio, auto, settled_ticks):
    if auto: studio.accept('motion auto on')
    studio.accept('up')
    advance(studio, settled_ticks)
    before = snapshot(studio)
    with pytest.raises(ValueError, match='TARGET ALREADY SET'):
        studio.accept('up')
    assert snapshot(studio) == before


@pytest.mark.parametrize('command,reason', [
    ('up .3', 'LIMIT REACHED'),
    ('capture Existing', 'already exists'),
    ('morph unknown_shape', 'unsupported target'),
])
def test_rejection_preserves_populated_creator_snapshot(studio, command, reason):
    for text in ('color on', 'palette cloud', 'motion gentle', 'speed fast',
                 'morph cloud .5', 'motion auto on', 'up .3 .5'):
        studio.accept(text)
    advance(studio, 360)
    studio.accept('capture Existing')
    before = snapshot(studio)
    with pytest.raises(ValueError, match=reason):
        studio.accept(command)
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
