"""V08/V09: profile gates tested independently from a successful renderer.

These synthetic trace/metric tables isolate acceptance inequalities; they are
not advertised as physically valid engine runs or release evidence. Real-run
integrity and numerical integration are verified by their separate families.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from commander_zorg.config import load_scene, resolved_mapping
from commander_zorg.experiments import profile_metrics
from commander_zorg.raster import measure_mask


@pytest.fixture
def profile_fixture():
    scene = resolved_mapping(load_scene(Path(__file__).parents[1] / "scenes" / "e1.json"))
    home = [item["home_xy"][:] for item in scene["elements"]]
    zero = [[0.0, 0.0] for _ in home]
    target = next(i for i, item in enumerate(scene["elements"]) if item["group"] == scene["cues"][0]["group"])
    states = []
    for tick in range(361):
        p = copy.deepcopy(home)
        if 80 <= tick <= 100:
            p[target][0] += .1
        states.append({"tick": tick, "positions": p, "velocities": copy.deepcopy(zero)})
    frames = []
    for index in range(180):
        disturbed = 40 <= index <= 50
        frames.append({"index": index, "tick": index * 2,
                       "pixel_sha256": hashlib.sha256(f"fixture {index}".encode()).hexdigest(),
                       "metrics": {"occupancy": .2, "clipping": False, "empty": False,
                                   "field_min": -.85, "field_max": 2.0,
                                   "aligned_iou": .8 if disturbed else 1.0,
                                   "iou": .75 if disturbed else 1.0,
                                   "centroid_distance": .02 if disturbed else 0.0}})
    control_scene = copy.deepcopy(scene)
    control_scene.update(scene_id="synthetic_control", cues=[])
    control_states = [{"tick": tick, "positions": copy.deepcopy(home), "velocities": copy.deepcopy(zero)}
                      for tick in range(361)]
    control_frames = copy.deepcopy(frames)
    for frame in control_frames:
        frame["pixel_sha256"] = frames[0]["pixel_sha256"]
    return scene, states, frames, control_scene, control_states, control_frames


def _check(fixture):
    return profile_metrics(*fixture)


def test_independent_profile_fixture_exercises_all_required_gates(profile_fixture):
    report = _check(profile_fixture)
    assert report["passed"] is True
    assert set(report["gates"]) == {
        "nominal_settings", "state_schedule", "frame_schedule", "finite_states", "state_bounds",
        "excitation", "numeric_recovery", "visibility", "finite_fields", "morphology",
        "temporal_variation", "image_recovery", "control_configuration", "control_schedule",
        "control_state_invariance", "control_frame_invariance"}
    assert report["gates"]["numeric_recovery"]["measured"] == {
        "position_max": 0.0, "speed_max": 0.0, "first_tick": 330, "last_tick": 360}


@pytest.mark.parametrize("tick,quantity", [(330, "positions"), (359, "positions"),
                                            (330, "velocities"), (359, "velocities")])
def test_recovery_checks_entire_tail_and_both_quantities(profile_fixture, tick, quantity):
    states = profile_fixture[1]
    states[tick][quantity][0][0] += .010001 if quantity == "positions" else .020001
    # The terminal state stays perfect: final-only recovery would falsely pass.
    report = _check(profile_fixture)
    assert report["gates"]["numeric_recovery"]["passed"] is False
    assert report["passed"] is False


@pytest.mark.parametrize("index,metric,value", [(165, "iou", .979999), (179, "iou", .979999),
                                                (165, "centroid_distance", .010001),
                                                (179, "centroid_distance", .010001)])
def test_image_recovery_checks_all_required_output_tail_frames(profile_fixture, index, metric, value):
    profile_fixture[2][index]["metrics"][metric] = value
    report = _check(profile_fixture)
    assert report["gates"]["image_recovery"]["passed"] is False


def test_frozen_solver_and_static_images_cannot_pass_recovery_alone(profile_fixture):
    _, states, frames, _, control_states, control_frames = profile_fixture
    for index, state in enumerate(states):
        state["positions"] = copy.deepcopy(control_states[index]["positions"])
        state["velocities"] = copy.deepcopy(control_states[index]["velocities"])
    for frame in frames:
        frame["pixel_sha256"] = control_frames[0]["pixel_sha256"]
        frame["metrics"].update(aligned_iou=1.0, iou=1.0, centroid_distance=0.0)
    report = _check(profile_fixture)
    assert report["gates"]["numeric_recovery"]["passed"] is True
    for name in ("excitation", "morphology", "temporal_variation"):
        assert report["gates"][name]["passed"] is False
    assert report["passed"] is False


def test_translation_without_deformation_fails_morphology(profile_fixture):
    for frame in profile_fixture[2]:
        frame["metrics"]["aligned_iou"] = 1.0
    report = _check(profile_fixture)
    assert report["gates"]["excitation"]["passed"] is True
    assert report["gates"]["temporal_variation"]["passed"] is True
    assert report["gates"]["morphology"]["passed"] is False


@pytest.mark.parametrize("case", ["empty", "full", "clipped", "missing", "nonfinite", "missing_field"])
def test_bad_renders_fail_their_intended_profile_checks(profile_fixture, case):
    frames = profile_fixture[2]
    gate = "visibility"
    if case == "empty":
        frames[50]["metrics"].update(occupancy=0.0, empty=True, iou=None, aligned_iou=None)
    elif case == "full":
        frames[50]["metrics"].update(occupancy=1.0, clipping=True)
    elif case == "clipped":
        frames[50]["metrics"]["clipping"] = True
    elif case == "missing":
        frames.pop(50)
        gate = "frame_schedule"
    elif case == "nonfinite":
        frames[50]["metrics"]["field_max"] = float("inf")
        gate = "finite_fields"
    else:
        del frames[50]["metrics"]["field_min"]
        gate = "finite_fields"
    report = _check(profile_fixture)
    assert report["gates"][gate]["passed"] is False
    assert report["passed"] is False


def test_flipped_asymmetric_recovery_image_fails_similarity(profile_fixture):
    # An asymmetric upper-world shape cannot be mistaken for its lower-world
    # mirror by a perfect final-state claim or an image's unchanged dimensions.
    scene = load_scene(Path(__file__).parents[1] / "scenes" / "e1.json")
    pixels = np.zeros((384, 384), dtype=np.uint8)
    pixels[70:160, 120:260] = 255
    pixels[145:205, 200:225] = 255
    flipped = pixels[::-1, :].copy()
    metrics = measure_mask(flipped, scene, pixels >= 128)
    assert metrics["centroid_distance"] > .01
    assert metrics["iou"] < .98
    profile_fixture[2][165]["metrics"].update(metrics)
    assert _check(profile_fixture)["gates"]["image_recovery"]["passed"] is False


@pytest.mark.parametrize("what", ["position", "velocity", "pixel", "parameter", "short"])
def test_cue_off_control_is_a_complete_invariant_experiment(profile_fixture, what):
    control_scene, states, frames = profile_fixture[3:]
    if what == "position":
        states[80]["positions"][0][1] += 1e-9
        name = "control_state_invariance"
    elif what == "velocity":
        states[80]["velocities"][0][1] = 1e-9
        name = "control_state_invariance"
    elif what == "pixel":
        frames[80]["pixel_sha256"] = "f" * 64
        name = "control_frame_invariance"
    elif what == "parameter":
        control_scene["seed"] += 1
        name = "control_configuration"
    else:
        del frames[5:]
        del states[10:]
        name = "control_schedule"
    report = _check(profile_fixture)
    assert report["gates"][name]["passed"] is False
    assert report["passed"] is False


@pytest.mark.parametrize("table,field,gate", [
    (1, "tick", "state_schedule"), (2, "index", "frame_schedule"),
    (4, "tick", "control_schedule"), (5, "index", "control_schedule"),
])
def test_boolean_zero_cannot_alias_a_schedule_integer(profile_fixture, table, field, gate):
    profile_fixture[table][0][field] = False
    assert _check(profile_fixture)["gates"][gate]["passed"] is False


@pytest.mark.parametrize("metric,gate", [("field_min", "finite_fields"), ("iou", "image_recovery")])
def test_boolean_values_are_not_numerical_profile_measurements(profile_fixture, metric, gate):
    profile_fixture[2][165]["metrics"][metric] = True
    assert _check(profile_fixture)["gates"][gate]["passed"] is False
