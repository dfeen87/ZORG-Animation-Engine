"""V05/V06: independent arithmetic, analytic motion, cadence and cue proofs."""

from copy import deepcopy
import math

import numpy as np
import pytest

from commander_zorg.config import resolve_scene, resolved_mapping
from commander_zorg.cues import cue_forces, quartic_pulse
from commander_zorg.guard import check_transition
from commander_zorg.motion import propose_step
from commander_zorg.state import initial_state, owned_state


def _document():
    return {
        "schema_version": "cz-scene-0.3", "scene_id": "motion_fixture", "seed": 0,
        "raster": {"width": 64, "height": 64, "samples_per_axis": 2, "invert": False},
        "timeline": {"sim_hz": 60, "fps_out": 30, "frame_count": 180},
        "field": {"kind": "gaussian-separable-v1", "threshold": 0.85},
        "elements": [
            {"id": "a", "group": "left", "home_xy": [0.1, -0.2], "sigma": 0.2,
             "weight": 1, "mass": 1, "spring_k": 14, "damping_c": 5},
            {"id": "b", "group": "right", "home_xy": [-0.3, 0.25], "sigma": 0.1,
             "weight": 0.8, "mass": 2, "spring_k": 20, "damping_c": 4},
        ],
        "cues": [],
        "limits": {"max_displacement": 0.75, "max_speed": 3, "max_total_force": 6},
    }


def _cue(cue_id, group, force, start=0, end=1):
    return {"id": cue_id, "group": group, "force_xy": list(force),
            "start_tick": start, "end_tick": end, "envelope": "quartic-pulse-v1"}


def test_v05_asymmetric_hand_calculated_step_and_owned_inputs():
    document = _document()
    document["cues"] = [_cue("a", "left", [0.6, -0.3]), _cue("b", "right", [-0.4, 0.8])]
    scene = resolve_scene(document)
    previous = owned_state(0, [[0.22, -0.28], [-0.36, 0.4]], [[0.3, -0.15], [-0.2, 0.1]])
    p_before, v_before = previous.positions.copy(), previous.velocities.copy()
    scene_before = resolved_mapping(scene)
    candidate = propose_step(previous, scene)
    # Exact rational arithmetic, calculated separately from the implementation:
    # acceleration rows (-129/50,157/100) and (4/5,-13/10).
    expected_v = np.array([[257 / 1000, -743 / 6000], [-14 / 75, 47 / 600]])
    expected_p = np.array([[13457 / 60000, -101543 / 360000], [-817 / 2250, 14447 / 36000]])
    np.testing.assert_allclose(candidate.velocities, expected_v, rtol=0, atol=6e-17)
    np.testing.assert_allclose(candidate.positions, expected_p, rtol=0, atol=6e-17)
    assert candidate.tick == 1
    assert check_transition(previous, candidate, scene).status == "ACCEPT"
    np.testing.assert_array_equal(previous.positions, p_before)
    np.testing.assert_array_equal(previous.velocities, v_before)
    assert resolved_mapping(scene) == scene_before
    for out in (candidate.positions, candidate.velocities):
        assert out.dtype == np.float64 and out.flags.c_contiguous
        assert not np.shares_memory(out, previous.positions)
        assert not np.shares_memory(out, previous.velocities)
        assert not np.shares_memory(out, scene.home_xy)
    assert not np.shares_memory(candidate.positions, candidate.velocities)


def test_v05_rest_invariance_through_terminal_tick():
    scene = resolve_scene(_document())
    state = initial_state(scene)
    initial_positions = state.positions.tobytes()
    initial_velocities = state.velocities.tobytes()
    for tick in range(scene.terminal_tick):
        candidate = propose_step(state, scene)
        assert check_transition(state, candidate, scene).status == "ACCEPT"
        assert candidate.tick == tick + 1
        np.testing.assert_array_equal(candidate.positions, scene.home_xy)
        np.testing.assert_array_equal(candidate.velocities, np.zeros((2, 2)))
        assert candidate.positions.tobytes() == initial_positions
        assert candidate.velocities.tobytes() == initial_velocities
        state = candidate


def test_v05_analytic_default_spring_60_and_120_hz(record_property):
    errors = {}
    for hz in (60, 120):
        document = _document()
        document["timeline"]["sim_hz"] = hz
        document["elements"] = document["elements"][:1]
        document["elements"][0]["home_xy"] = [0, 0]
        scene = resolve_scene(document)
        state = owned_state(0, [[0.2, 0]], [[0, 0]])
        largest = 0.0
        # Independent continuous damped-spring solution, m=1 k=14 c=5.
        beta = 2.5
        omega = math.sqrt(14 - beta * beta)
        for tick in range(2 * hz + 1):
            t = tick / hz
            expected = math.exp(-beta * t) * (0.2 * math.cos(omega * t)
                                             + (0.5 / omega) * math.sin(omega * t))
            largest = max(largest, abs(state.positions[0, 0] - expected))
            if tick < 2 * hz:
                candidate = propose_step(state, scene)
                assert check_transition(state, candidate, scene).status == "ACCEPT"
                state = candidate
        errors[hz] = largest
        record_property(f"max_position_error_{hz}_hz", largest)
    assert errors[60] <= 0.01
    assert errors[120] < errors[60]


def test_v05_forced_common_time_cadence_gate(record_property):
    # The default E1 driven coordinates have these exact m/k/c, cue and timing.
    # Extra independent rest elements do not alter these uncoupled coordinates.
    common = {}
    for hz in (60, 120):
        document = _document()
        document["timeline"]["sim_hz"] = hz
        document["elements"] = document["elements"][:1]
        document["elements"][0]["home_xy"] = [0, 0]
        factor = hz // 60
        document["cues"] = [_cue("surprise", "left", [2, 1], 45 * factor, 120 * factor)]
        scene = resolve_scene(document)
        state = initial_state(scene)
        samples = []
        for tick in range(scene.terminal_tick + 1):
            if tick % (hz // 30) == 0:
                samples.append((state.positions.copy(), state.velocities.copy()))
            if tick < scene.terminal_tick:
                candidate = propose_step(state, scene)
                assert check_transition(state, candidate, scene).status == "ACCEPT"
                state = candidate
        common[hz] = samples
    position_difference = max(float(np.linalg.norm(a[0] - b[0], axis=1).max())
                              for a, b in zip(common[60], common[120], strict=True))
    velocity_difference = max(float(np.linalg.norm(a[1] - b[1], axis=1).max())
                              for a, b in zip(common[60], common[120], strict=True))
    record_property("forced_max_position_difference", position_difference)
    record_property("forced_max_velocity_difference", velocity_difference)
    assert position_difference <= 0.01


@pytest.mark.parametrize("u,expected", [(-1, 0), (0, 0), (0.25, 0.5625),
                                       (0.5, 1), (0.75, 0.5625), (1, 0), (2, 0)])
def test_v06_quartic_support_and_peak(u, expected):
    assert quartic_pulse(u) == expected


def test_v06_endpoint_first_derivatives_vanish():
    epsilon = 1e-7
    assert abs(quartic_pulse(epsilon) / epsilon) < 2e-6
    assert abs(quartic_pulse(1 - epsilon) / epsilon) < 2e-6


def test_v06_midpoint_overlap_full_force_and_different_masses():
    document = _document()
    for element in document["elements"]:
        element["group"] = "shared"
    document["cues"] = [_cue("b", "shared", [0.4, -0.8], 0, 2),
                        _cue("a", "shared", [0.6, 0.3], 0, 1)]
    original = deepcopy(document)
    scene = resolve_scene(document)
    assert [cue.id for cue in scene.cues] == ["a", "b"]
    force = cue_forces(0, scene)
    # Midpoint envelopes are 1 and 9/16; neither force is shared/divided.
    np.testing.assert_allclose(force, [[0.825, -0.15], [0.825, -0.15]], rtol=0, atol=6e-17)
    assert force.dtype == np.float64
    candidate = propose_step(initial_state(scene), scene)
    np.testing.assert_allclose(candidate.velocities, [[11 / 800, -1 / 400],
                                                    [11 / 1600, -1 / 800]],
                               rtol=0, atol=3e-18)
    np.testing.assert_array_equal(cue_forces(2, scene), np.zeros((2, 2)))
    assert document == original


def test_v06_sorted_cue_addition_has_observable_float_order():
    document = _document()
    document["cues"] = [_cue("c", "left", [-1, 0]), _cue("b", "left", [2**-53, 0]),
                        _cue("a", "left", [1, 0])]
    scene = resolve_scene(document)
    # In a,b,c order (1 + 2**-53) rounds to 1 before adding -1.
    assert cue_forces(0, scene)[0, 0] == 0.0


@pytest.mark.parametrize("tick", [-1, True, 1.0, 360, None])
def test_v06_invalid_transition_tick(tick):
    with pytest.raises(ValueError, match="tick"):
        cue_forces(tick, resolve_scene(_document()))
