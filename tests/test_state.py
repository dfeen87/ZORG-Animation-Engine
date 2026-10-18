"""V02/V05: state clock, array ownership and accidental alias protection."""

from dataclasses import FrozenInstanceError, fields

import numpy as np
import pytest

from commander_zorg.config import resolve_scene
from commander_zorg.state import SceneState, initial_state, owned_state, state_mapping


def small_scene():
    return resolve_scene({
        "schema_version": "cz-scene-0.3", "scene_id": "ownership", "seed": 0,
        "raster": {"width": 64, "height": 64, "samples_per_axis": 2, "invert": False},
        "timeline": {"sim_hz": 60, "fps_out": 30, "frame_count": 1},
        "field": {"kind": "gaussian-separable-v1", "threshold": 0.85},
        "elements": [{"id": "single", "group": "body", "home_xy": [-0.2, 0.3],
                      "sigma": 0.2, "weight": 1, "mass": 1, "spring_k": 14, "damping_c": 5}],
        "cues": [], "limits": {"max_displacement": 0.75, "max_speed": 3, "max_total_force": 6},
    })


def test_initial_state_has_only_tick_and_two_owned_arrays():
    scene = small_scene()
    state = initial_state(scene)
    assert tuple(field.name for field in fields(state)) == ("tick", "positions", "velocities")
    assert type(state.tick) is int and state.tick == 0
    np.testing.assert_array_equal(state.positions, [[-0.2, 0.3]])
    np.testing.assert_array_equal(state.velocities, [[0.0, 0.0]])
    assert not np.shares_memory(state.positions, scene.home_xy)
    assert not np.shares_memory(state.positions, state.velocities)


def test_copy_converts_noncontiguous_float32_into_independent_float64():
    source = np.arange(12, dtype=np.float32).reshape(3, 4)[:, ::2]
    snapshot = source.copy()
    state = owned_state(7, source, source)
    for array in (state.positions, state.velocities):
        assert array.shape == (3, 2) and array.dtype == np.float64
        assert array.flags.c_contiguous and array.flags.owndata
        assert not array.flags.writeable
        assert not np.shares_memory(array, source)
        np.testing.assert_array_equal(array, snapshot)
        with pytest.raises(ValueError):
            array[0, 0] = 100
    assert not np.shares_memory(state.positions, state.velocities)
    source[:] = -7
    np.testing.assert_array_equal(state.positions, snapshot)
    with pytest.raises(FrozenInstanceError):
        state.tick = 8


def test_each_initialization_owns_distinct_storage():
    scene = small_scene()
    one, two = initial_state(scene), initial_state(scene)
    assert not np.shares_memory(one.positions, two.positions)
    assert not np.shares_memory(one.velocities, two.velocities)
    next_state = owned_state(1, one.positions, one.velocities)
    assert not np.shares_memory(next_state.positions, one.positions)
    assert not np.shares_memory(next_state.velocities, one.velocities)


@pytest.mark.parametrize("tick", [True, False, -1, 1.0, "0", None])
def test_ownership_helper_requires_nonnegative_integer_tick(tick):
    with pytest.raises(ValueError, match="tick"):
        owned_state(tick, [[0, 0]], [[0, 0]])


@pytest.mark.parametrize("positions,velocities", [([], []), ([0, 0], [0, 0]),
    ([[0, 0, 0]], [[0, 0, 0]]), ([[0, 0]], [[0, 0], [0, 0]]), ([[[0, 0]]], [[[0, 0]]])])
def test_ownership_helper_rejects_malformed_shapes(positions, velocities):
    with pytest.raises(ValueError, match="state"):
        owned_state(0, positions, velocities)


def test_nonfinite_candidate_preserved_for_guard_but_not_committed_json():
    candidate = owned_state(1, [[float("nan"), 0]], [[0, float("inf")]])
    assert np.isnan(candidate.positions[0, 0])
    assert np.isinf(candidate.velocities[0, 1])
    with pytest.raises(ValueError, match="nonfinite"):
        state_mapping(candidate)


def test_state_mapping_is_detached_and_contains_no_hidden_configuration():
    state = owned_state(3, [[0.25, -0.125]], [[-0.5, 0.75]])
    result = state_mapping(state)
    assert result == {"tick": 3, "positions": [[0.25, -0.125]], "velocities": [[-0.5, 0.75]]}
    result["positions"][0][0] = 9
    assert state.positions[0, 0] == 0.25


def test_structural_carrier_permits_guard_negative_fixtures():
    malformed = SceneState("invalid", np.array([1], dtype=np.float32), np.array([np.nan]))
    assert malformed.tick == "invalid"
