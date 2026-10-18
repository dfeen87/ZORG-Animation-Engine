"""V07: invalid candidates reject without altering the committed source state."""

import json

import numpy as np
import pytest

from commander_zorg.config import resolve_scene
from commander_zorg.guard import InvalidStateError, check_transition, validate_state
from commander_zorg.motion import propose_step
from commander_zorg.state import SceneState, initial_state, owned_state


def _scene():
    return resolve_scene({
        "schema_version": "cz-scene-0.3", "scene_id": "guard_fixture", "seed": 0,
        "raster": {"width": 64, "height": 64, "samples_per_axis": 2, "invert": False},
        "timeline": {"sim_hz": 60, "fps_out": 30, "frame_count": 180},
        "field": {"kind": "gaussian-separable-v1", "threshold": 0.85},
        "elements": [{"id": "asymmetric", "group": "head", "home_xy": [0.1, -0.2],
                      "sigma": 0.2, "weight": 1, "mass": 1, "spring_k": 14, "damping_c": 5}],
        "cues": [], "limits": {"max_displacement": 0.75, "max_speed": 3, "max_total_force": 6},
    })


@pytest.mark.parametrize("fault,code", [
    ("nan_position", "NONFINITE_POSITION"), ("infinite_velocity", "NONFINITE_VELOCITY"),
    ("bad_tick", "BAD_TICK"), ("bool_tick", "BAD_TICK"),
    ("speed", "SPEED_LIMIT"), ("displacement", "DISPLACEMENT_LIMIT"),
    ("shape", "BAD_SHAPE"), ("dtype", "BAD_DTYPE"), ("layout", "BAD_LAYOUT"),
])
def test_v07_reject_malformed_candidate_without_mutation(fault, code):
    scene = _scene()
    previous = initial_state(scene)
    p_before, v_before = previous.positions.copy(), previous.velocities.copy()
    positions, velocities = previous.positions.copy(), previous.velocities.copy()
    tick = 1
    if fault == "nan_position":
        positions[0, 1] = np.nan
    elif fault == "infinite_velocity":
        velocities[0, 0] = -np.inf
    elif fault == "bad_tick":
        tick = 2
    elif fault == "bool_tick":
        tick = True
    elif fault == "speed":
        velocities[0] = [2.2, 2.2]
    elif fault == "displacement":
        positions[0] += [0.6, 0.6]
    elif fault == "shape":
        positions = np.zeros((2, 2), dtype=np.float64)
    elif fault == "dtype":
        velocities = velocities.astype(np.float32)
    elif fault == "layout":
        storage = np.zeros((1, 4), dtype=np.float64)
        storage[:, ::2] = positions
        positions = storage[:, ::2]
    candidate = SceneState(tick, positions, velocities)
    decision = check_transition(previous, candidate, scene)
    assert decision.status == "REJECT"
    assert decision.attempted_tick == 1
    assert code in {reason["code"] for reason in decision.reasons}
    # Diagnostics must be serializable with strict JSON, including invalid floats.
    json.dumps({"status": decision.status, "reasons": decision.reasons}, allow_nan=False)
    np.testing.assert_array_equal(previous.positions, p_before)
    np.testing.assert_array_equal(previous.velocities, v_before)
    assert previous.tick == 0
    if fault in ("nan_position", "infinite_velocity"):
        reason = next(reason for reason in decision.reasons if reason["code"] == code)
        assert reason["element_id"] == "asymmetric"
        assert reason["detail"] == ("nan" if fault == "nan_position" else "-inf")


def test_v07_valid_bounds_are_inclusive_and_guard_does_not_repair():
    scene = _scene()
    previous = initial_state(scene)
    positions = previous.positions.copy()
    positions[0, 0] += 0.75
    candidate = owned_state(1, positions, [[0, 3]])
    p_before, v_before = candidate.positions.copy(), candidate.velocities.copy()
    assert check_transition(previous, candidate, scene).status == "ACCEPT"
    np.testing.assert_array_equal(candidate.positions, p_before)
    np.testing.assert_array_equal(candidate.velocities, v_before)


def test_v07_invalid_previous_is_checked_before_force_or_proposal():
    scene = _scene()
    previous = owned_state(0, [[np.nan, 0]], [[0, 0]])
    with pytest.raises(InvalidStateError, match="NONFINITE_POSITION"):
        propose_step(previous, scene)
    candidate = owned_state(1, scene.home_xy, [[0, 0]])
    decision = check_transition(previous, candidate, scene)
    assert decision.status == "REJECT"
    assert decision.reasons[0]["code"] == "INVALID_PREVIOUS"
    assert decision.reasons[1]["path"] == "previous.positions[0][0]"
    assert np.isnan(previous.positions[0, 0])


def test_v07_terminal_state_is_valid_but_cannot_advance():
    scene = _scene()
    terminal = owned_state(scene.terminal_tick, scene.home_xy, [[0, 0]])
    assert validate_state(terminal, scene) == []
    with pytest.raises(InvalidStateError, match="terminal"):
        propose_step(terminal, scene)
    candidate = owned_state(scene.terminal_tick + 1, scene.home_xy, [[0, 0]])
    assert check_transition(terminal, candidate, scene).status == "REJECT"
