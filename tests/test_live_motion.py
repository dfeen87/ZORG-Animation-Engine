"""Live commands exercise the guarded geometry, including simultaneous extremes."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from commander_zorg.canonical import read_json
from commander_zorg.field import evaluate_samples
from commander_zorg.guard import InvalidStateError
from commander_zorg.live_commands import ENVELOPE, parse_command
from commander_zorg.live_motion import LiveNumericalError, LiveRuntime
from commander_zorg.raster import measure_mask, rasterize
from commander_zorg.state import owned_state


@pytest.fixture
def config():
    return read_json(Path(__file__).parents[1] / "scenes/live_lab.json")


def _metrics(runtime):
    # Resolution changes affect only this raster adapter, never the simulation.
    view = replace(runtime.scene, width=96, height=96, samples_per_axis=2)
    pixels = rasterize(evaluate_samples(runtime.state, view), view)
    return measure_mask(pixels, view)


def _advance(runtime, count):
    for _ in range(count):
        runtime.step()


@pytest.mark.parametrize("text,action", [
    ("left", "left"), ("RIGHT", "right"), (" up ", "up"), ("down", "down"),
    ("squash", "squash"), ("stretch", "stretch"), ("reset", "reset"),
    ("wander on", "wander_on"), ("wander off", "wander_off"),
    ("help", "help"), ("save", "save"), ("quit", "quit"),
])
def test_supported_command_grammar(text, action):
    assert parse_command(text)["action"] == action


@pytest.mark.parametrize("text,strength,ticks", [
    ("left .05 .5", .05, 30), ("right .3 10", .3, 600),
    ("up .2 .75", .2, 45), ("stretch .6 .5", .6, 30),
    ("squash .05 10", .05, 600),
])
def test_optional_arguments_are_strength_then_seconds(text, strength, ticks):
    command = parse_command(text)
    assert command["strength"] == strength
    assert command["duration_ticks"] == ticks
    assert command["scope"] == "all"
    assert command["envelope"] == ENVELOPE


@pytest.mark.parametrize("text", [
    "", "north", "left .3001", "stretch .6001", "squash .049", "right -inf",
    "up nan", "down 1e999", "stretch .5 .49", "squash .5 10.01",
    "right two 2", "left .2 nan", "help extra", "reset .3", "wander maybe",
    "wander on 2", "wander_on", "left .2 2 trailing",
])
def test_malformed_commands_do_not_change_runtime(config, text):
    runtime = LiveRuntime(config)
    before = runtime.state
    targets = runtime.target_offsets(60).copy()
    with pytest.raises(ValueError):
        runtime.accept(text)
    assert runtime.state is before
    assert runtime.events == []
    np.testing.assert_array_equal(runtime.target_offsets(60), targets)


@pytest.mark.parametrize("action,axis,sign", [
    ("left", 0, -1), ("right", 0, 1), ("up", 1, 1), ("down", 1, -1),
])
@pytest.mark.parametrize("wander", [False, True])
def test_direction_has_signed_field_centroid_response(config, action, axis, sign, wander):
    config["wander"] = wander
    reference, directed = LiveRuntime(config), LiveRuntime(config)
    _advance(reference, 120)
    _advance(directed, 120)
    event = directed.accept(f"{action} .3 .5")
    assert event["effective_tick"] == 120
    _advance(reference, 240)
    _advance(directed, 240)
    neutral, moved = _metrics(reference), _metrics(directed)
    assert sign * (moved["centroid"][axis] - neutral["centroid"][axis]) > .25
    assert abs(moved["centroid"][1-axis] - neutral["centroid"][1-axis]) < .03
    assert not moved["empty"] and not moved["clipping"]


@pytest.mark.parametrize("action", ["squash", "stretch"])
def test_morphology_changes_height_and_width_without_translation(config, action):
    config["wander"] = False
    neutral, morphed = LiveRuntime(config), LiveRuntime(config)
    morphed.accept(f"{action} .6 .5")
    _advance(neutral, 300)
    _advance(morphed, 300)
    base, changed = _metrics(neutral), _metrics(morphed)
    bx0, by0, bx1, by1 = base["bbox"]
    cx0, cy0, cx1, cy1 = changed["bbox"]
    height_ratio = (cy1-cy0+1) / (by1-by0+1)
    width_ratio = (cx1-cx0+1) / (bx1-bx0+1)
    if action == "stretch":
        assert height_ratio > 1.25
        assert width_ratio < .98
    else:
        assert height_ratio < .85
        assert width_ratio > 1.1
    assert np.linalg.norm(np.subtract(changed["centroid"], base["centroid"])) < .06
    assert not changed["empty"] and not changed["clipping"]


def test_same_tick_precedence_and_independent_morph_channel(config):
    config["wander"] = False
    superseded, reference = LiveRuntime(config), LiveRuntime(config)
    commands = ("left .3 .5", "right .3 .5", "stretch .6 .5")
    events = [superseded.accept(command) for command in commands]
    reference.accept("right .3 .5")
    reference.accept("stretch .6 .5")
    assert [event["sequence"] for event in events] == [0, 1, 2]
    assert [event["effective_tick"] for event in events] == [0, 0, 0]
    for _ in range(300):
        superseded.step()
        reference.step()
    np.testing.assert_array_equal(superseded.state.positions, reference.state.positions)
    assert superseded.trajectory_sha256 == reference.trajectory_sha256
    image = _metrics(superseded)
    assert image["centroid"][0] > .25
    assert image["bbox"][3]-image["bbox"][1] > 50
    assert len(superseded.events) == 3


def test_superseding_midtransition_is_continuous_and_bounded(config):
    runtime = LiveRuntime(config)
    runtime.accept("right .3 .5")
    _advance(runtime, 15)
    before = runtime.target_offsets(runtime.state.tick).copy()
    state = runtime.state
    runtime.accept("left .3 .5")
    np.testing.assert_array_equal(runtime.target_offsets(runtime.state.tick), before)
    assert runtime.state is state
    for tick in range(1200):
        if tick % 7 == 0:
            runtime.accept("right .3 .5" if tick % 2 else "left .3 .5")
            runtime.accept("squash .6 .5" if tick % 2 else "stretch .6 .5")
        prior = runtime.state
        runtime.step()
        assert np.max(np.linalg.norm(runtime.state.positions-prior.positions, axis=1)) < .02
    assert np.max(np.linalg.norm(runtime.state.positions-runtime.scene.home_xy, axis=1)) < .75


def test_reset_recovers_home_and_wander_toggle_is_smooth(config):
    runtime = LiveRuntime(config)
    runtime.accept("right .3 .5")
    runtime.accept("stretch .6 .5")
    _advance(runtime, 240)
    before = runtime.target_offsets(runtime.state.tick).copy()
    runtime.accept("wander off")
    np.testing.assert_array_equal(runtime.target_offsets(runtime.state.tick), before)
    _advance(runtime, 150)
    disabled = runtime.target_offsets(runtime.state.tick).copy()
    _advance(runtime, 60)
    np.testing.assert_array_equal(runtime.target_offsets(runtime.state.tick), disabled)
    runtime.accept("wander on")
    _advance(runtime, 150)
    assert not np.array_equal(runtime.target_offsets(runtime.state.tick), disabled)
    before = runtime.target_offsets(runtime.state.tick).copy()
    runtime.accept("reset")
    np.testing.assert_array_equal(runtime.target_offsets(runtime.state.tick), before)
    _advance(runtime, 600)
    np.testing.assert_allclose(runtime.state.positions, runtime.scene.home_xy, atol=1e-6, rtol=0)
    assert not runtime.wander
    np.testing.assert_array_equal(runtime.target_offsets(runtime.state.tick), np.zeros_like(before))


@pytest.mark.parametrize("seed", [0, 1, 172026])
@pytest.mark.parametrize("direction", ["left", "right", "up", "down"])
@pytest.mark.parametrize("morph", ["squash", "stretch"])
def test_all_combined_extremes_remain_guarded_for_twenty_seconds(config, seed, direction, morph):
    config["seed"] = seed
    runtime = LiveRuntime(config)
    runtime.accept(f"{direction} .3 .5")
    runtime.accept(f"{morph} .6 .5")
    for tick in range(1200):
        force = runtime.scene.spring_k[:, None] * runtime.target_offsets(runtime.state.tick)
        assert np.isfinite(force).all()
        assert np.max(np.linalg.norm(force, axis=1)) <= runtime.scene.max_total_force
        runtime.step()  # Each transition invokes the unchanged Build 0 guard.
        assert not runtime.state.positions.flags.writeable
        assert np.max(np.linalg.norm(runtime.state.velocities, axis=1)) <= runtime.scene.max_speed
        assert np.max(np.linalg.norm(runtime.state.positions-runtime.scene.home_xy, axis=1)) <= runtime.scene.max_displacement
        if tick % 120 == 119:
            image = _metrics(runtime)
            assert not image["empty"]
            if image["clipping"]:
                # The guard's two-pixel edge band is wider in world units on a
                # coarse preview. Confirm clipping at the real export raster.
                exported = rasterize(evaluate_samples(runtime.state, runtime.scene), runtime.scene)
                assert not measure_mask(exported, runtime.scene)["clipping"]


def test_seeded_motion_is_exact_and_seed_changes_geometry(config):
    first, twin = LiveRuntime(config), LiveRuntime(config)
    other = LiveRuntime({**config, "seed": config["seed"] + 1})
    for tick in range(600):
        if tick == 120:
            for runtime in (first, twin, other):
                runtime.accept("stretch .5 .5")
        first.step()
        twin.step()
        other.step()
    assert first.trajectory_sha256 == twin.trajectory_sha256
    np.testing.assert_array_equal(first.state.positions, twin.state.positions)
    assert first.trajectory_sha256 != other.trajectory_sha256
    assert not np.array_equal(first.state.positions, other.state.positions)


@pytest.mark.parametrize("limit", ["max_displacement", "max_speed"])
def test_state_bound_rejection_keeps_last_committed_state(config, limit):
    config["wander"] = False
    config["scene"]["limits"][limit] = 1e-6
    runtime = LiveRuntime(config)
    runtime.accept("right .3 .5")
    for _ in range(100):
        before, digest = runtime.state, runtime.trajectory_sha256
        try:
            runtime.step()
        except LiveNumericalError:
            assert runtime.state is before
            assert runtime.trajectory_sha256 == digest
            break
    else:
        pytest.fail(f"{limit} did not reject a violating transition")


def test_invalid_previous_state_rejects_without_repair(config):
    runtime = LiveRuntime(config)
    positions = runtime.state.positions.copy()
    positions[0, 0] = np.nan
    runtime.state = owned_state(0, positions, runtime.state.velocities)
    before = runtime.state
    with pytest.raises(InvalidStateError, match="NONFINITE_POSITION"):
        runtime.step()
    assert runtime.state is before
    assert np.isnan(runtime.state.positions[0, 0])


@pytest.mark.parametrize("field,value", [
    ("sequence", True), ("sequence", -1), ("effective_tick", True),
    ("effective_tick", 1), ("duration_ticks", True), ("duration_ticks", 29),
    ("duration_ticks", 601), ("duration_ticks", 10**1000), ("strength", True),
    ("strength", float("nan")), ("strength", float("inf")), ("strength", .31),
    ("scope", "head"), ("envelope", "instant"), ("action", "north"),
    ("schema_version", "unknown"),
])
def test_replay_event_rejection_is_atomic(config, field, value):
    source = LiveRuntime(config)
    event = source.accept("left .3 .5")
    event[field] = value
    runtime = LiveRuntime(config)
    state, target = runtime.state, runtime.target_offsets(60).copy()
    with pytest.raises(ValueError):
        runtime.apply_event(event)
    assert runtime.state is state
    assert runtime.events == []
    np.testing.assert_array_equal(runtime.target_offsets(60), target)


def test_horizon_is_separate_from_finite_scene_and_cannot_advance(config):
    config["max_ticks"] = 2
    runtime = LiveRuntime(config)
    _advance(runtime, 2)
    assert runtime.scene.base.terminal_tick == 2
    with pytest.raises(ValueError, match="tick limit"):
        runtime.step()
    with pytest.raises(ValueError, match="tick limit"):
        runtime.accept("left")

