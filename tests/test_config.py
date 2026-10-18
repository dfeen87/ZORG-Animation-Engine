"""V01: independent schema fixtures, boundary checks and deterministic plans."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json

import numpy as np
import pytest

from commander_zorg.config import ConfigError, load_scene, resolve_scene, resolved_mapping, validate_solver


def scene_document():
    return {
        "schema_version": "cz-scene-0.3", "scene_id": "asymmetric", "seed": 17,
        "raster": {"width": 128, "height": 64, "samples_per_axis": 2, "invert": False},
        "timeline": {"sim_hz": 60, "fps_out": 30, "frame_count": 180},
        "field": {"kind": "gaussian-separable-v1", "threshold": 0.85},
        "elements": [
            {"id": "z_right", "group": "body", "home_xy": [0.3, -0.25],
             "sigma": 0.13, "weight": 0.9, "mass": 2, "spring_k": 12, "damping_c": 6},
            {"id": "a_left", "group": "head", "home_xy": [-0.2, 0.1],
             "sigma": 0.2, "weight": 1, "mass": 1, "spring_k": 14, "damping_c": 5},
        ],
        "cues": [
            {"id": "z_push", "group": "head", "start_tick": 45, "end_tick": 120,
             "envelope": "quartic-pulse-v1", "force_xy": [2, 1]},
            {"id": "a_push", "group": "body", "start_tick": 0, "end_tick": 2,
             "envelope": "quartic-pulse-v1", "force_xy": [-1, 0]},
        ],
        "limits": {"max_displacement": 0.75, "max_speed": 3, "max_total_force": 6},
    }


def put(doc, path, value):
    cursor = doc
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = value


def at(doc, path):
    cursor = doc
    for part in path:
        cursor = cursor[part]
    return cursor


def test_resolved_order_types_and_original_input_immutability():
    doc = scene_document()
    original = deepcopy(doc)
    scene = resolve_scene(doc)
    assert doc == original
    assert scene.element_order == ("a_left", "z_right")
    assert tuple(cue.id for cue in scene.cues) == ("a_push", "z_push")
    assert dict(scene.group_indices) == {"body": (1,), "head": (0,)}
    np.testing.assert_array_equal(scene.home_xy, [[-0.2, 0.1], [0.3, -0.25]])
    np.testing.assert_array_equal(scene.mass, [1.0, 2.0])
    np.testing.assert_array_equal(scene.spring_k, [14.0, 12.0])
    np.testing.assert_array_equal(scene.damping_c, [5.0, 6.0])
    resolved = resolved_mapping(scene)
    assert type(resolved["elements"][0]["mass"]) is float
    assert type(resolved["cues"][0]["force_xy"][1]) is float
    assert type(resolved["limits"]["max_speed"]) is float
    doc["elements"][1]["home_xy"][0] = 0.5
    resolved["elements"][0]["home_xy"][1] = 0.7
    assert scene.elements[0].home_xy == (-0.2, 0.1)


def test_config_definitions_and_compiled_arrays_are_immutable():
    scene = resolve_scene(scene_document())
    with pytest.raises(FrozenInstanceError):
        scene.elements[0].mass = 2.0
    with pytest.raises(FrozenInstanceError):
        scene.cues[0].force_xy = (0.0, 0.0)
    with pytest.raises(TypeError):
        scene.group_indices["head"] = (1,)
    arrays = [scene.home_xy, scene.sigma, scene.weight, scene.mass, scene.spring_k, scene.damping_c]
    for i, array in enumerate(arrays):
        assert array.dtype == np.float64
        assert array.flags.c_contiguous and array.flags.owndata
        assert not array.flags.writeable
        with pytest.raises(ValueError):
            array.flat[0] = 999
        for other in arrays[i + 1:]:
            assert not np.shares_memory(array, other)


def test_nominal_clock_and_120_hz_have_no_terminal_extra_frame():
    doc = scene_document()
    scene = resolve_scene(doc)
    assert scene.frame_ticks == tuple(range(0, 360, 2))
    assert scene.terminal_tick == 360
    assert len(scene.frame_ticks) == 180
    doc["timeline"]["sim_hz"] = 120
    for cue in doc["cues"]:
        cue["start_tick"] *= 2
        cue["end_tick"] *= 2
    finer = resolve_scene(doc)
    assert finer.frame_ticks == tuple(range(0, 720, 4))
    assert finer.terminal_tick == 720


def test_read_bytes_are_preserved_but_semantics_do_not_depend_on_array_order(tmp_path):
    doc = scene_document()
    raw = ("\n" + json.dumps(doc, indent=3) + "\n").encode()
    path = tmp_path / "scene.json"
    path.write_bytes(raw)
    scene = load_scene(path)
    assert scene.raw_bytes == raw
    doc["elements"].reverse()
    doc["cues"].reverse()
    assert resolved_mapping(scene) == resolved_mapping(resolve_scene(doc))


_OBJECT_PATHS = [(), ("raster",), ("timeline",), ("field",), ("limits",),
                 ("elements", 0), ("cues", 0)]


@pytest.mark.parametrize("path", _OBJECT_PATHS)
def test_unknown_and_missing_properties_rejected_at_every_level(path):
    doc = scene_document()
    at(doc, path)["unexpected"] = 1
    with pytest.raises(ConfigError, match="unknown"):
        resolve_scene(doc)
    doc = scene_document()
    key = next(iter(at(doc, path)))
    del at(doc, path)[key]
    with pytest.raises(ConfigError, match="missing"):
        resolve_scene(doc)


@pytest.mark.parametrize("needle,expected_path", [
    ('"seed": 17', r"\$\.seed"),
    ('"width": 128', r"\$\.raster\.width"),
    ('"sim_hz": 60', r"\$\.timeline\.sim_hz"),
    ('"threshold": 0.85', r"\$\.field\.threshold"),
    ('"max_speed": 3', r"\$\.limits\.max_speed"),
    ('"sigma": 0.13', r"\$\.elements\[0\]\.sigma"),
    ('"start_tick": 45', r"\$\.cues\[0\]\.start_tick"),
])
def test_nested_duplicate_json_keys_are_not_discarded(tmp_path, needle, expected_path):
    text = json.dumps(scene_document())
    key, value = needle.split(": ")
    text = text.replace(needle, f"{needle}, {key}: {value}", 1)
    path = tmp_path / "bad.json"
    path.write_text(text)
    with pytest.raises(ConfigError, match=expected_path):
        load_scene(path)
    assert sorted(item.name for item in tmp_path.iterdir()) == ["bad.json"]


@pytest.mark.parametrize("raw", [b"", b"{", b"{} {}", b"\xff", b"[]", b"null", b"42",
                                  b'{"x": NaN}', b'{"x": Infinity}', b'{"x": -Infinity}'])
def test_malformed_or_nonstandard_json_rejected(tmp_path, raw):
    path = tmp_path / "bad.json"
    path.write_bytes(raw)
    with pytest.raises(ConfigError, match=r"\$"):
        load_scene(path)


_NUMERIC_PATHS = [
    ("seed",), ("raster", "width"), ("raster", "height"), ("raster", "samples_per_axis"),
    ("timeline", "sim_hz"), ("timeline", "fps_out"), ("timeline", "frame_count"),
    ("field", "threshold"), ("elements", 0, "home_xy", 0),
    ("elements", 0, "sigma"), ("elements", 0, "weight"), ("elements", 0, "mass"),
    ("elements", 0, "spring_k"), ("elements", 0, "damping_c"),
    ("cues", 0, "start_tick"), ("cues", 0, "end_tick"), ("cues", 0, "force_xy", 1),
    ("limits", "max_displacement"), ("limits", "max_speed"), ("limits", "max_total_force"),
]


@pytest.mark.parametrize("path", _NUMERIC_PATHS)
@pytest.mark.parametrize("bad", [True, False, None, "1", float("nan"), float("inf"), -float("inf")])
def test_numeric_fields_never_coerce_boolean_string_null_or_nonfinite(path, bad):
    doc = scene_document()
    put(doc, path, bad)
    with pytest.raises(ConfigError, match=r"\$"):
        resolve_scene(doc)


@pytest.mark.parametrize("path", _NUMERIC_PATHS[:7] + _NUMERIC_PATHS[14:16])
def test_integer_fields_reject_real_valued_integers(path):
    doc = scene_document()
    put(doc, path, float(at(doc, path)))
    with pytest.raises(ConfigError):
        resolve_scene(doc)


@pytest.mark.parametrize("path,bad", [
    (("schema_version",), "cz-scene-0.4"), (("field", "kind"), "direct"),
    (("cues", 0, "envelope"), "sin"), (("raster", "invert"), 1),
    (("seed",), -1), (("seed",), 2**64), (("raster", "width"), 63),
    (("raster", "height"), 513), (("raster", "samples_per_axis"), 3),
    (("timeline", "sim_hz"), 90), (("timeline", "fps_out"), 60),
    (("timeline", "frame_count"), 0), (("timeline", "frame_count"), 361),
    (("field", "threshold"), 0.049), (("field", "threshold"), 5.001),
    (("elements", 0, "sigma"), 0.029), (("elements", 0, "sigma"), 0.601),
    (("elements", 0, "weight"), 0), (("elements", 0, "weight"), 2.001),
    (("elements", 0, "mass"), 0.49), (("elements", 0, "mass"), 2.01),
    (("elements", 0, "spring_k"), 4.99), (("elements", 0, "spring_k"), 100.01),
    (("elements", 0, "damping_c"), 0.99), (("elements", 0, "damping_c"), 30.01),
    (("elements", 0, "home_xy"), [1.601, 0]),
    (("elements", 0, "home_xy"), [0, -0.801]),
    (("limits", "max_displacement"), 0), (("limits", "max_displacement"), 0.751),
    (("limits", "max_speed"), 0), (("limits", "max_speed"), 3.01),
    (("limits", "max_total_force"), 0), (("limits", "max_total_force"), 6.01),
    (("cues", 0, "start_tick"), -1), (("cues", 0, "end_tick"), 361),
    (("cues", 0, "start_tick"), 120), (("cues", 0, "end_tick"), 0),
    (("cues", 0, "group"), "missing"), (("cues", 0, "force_xy"), [6, 1]),
    (("cues", 0, "force_xy"), [10**1000, 0]),
])
def test_invalid_ranges_and_unsupported_enums(path, bad):
    doc = scene_document()
    put(doc, path, bad)
    with pytest.raises(ConfigError, match=r"\$"):
        resolve_scene(doc)


@pytest.mark.parametrize("path", [("scene_id",), ("elements", 0, "id"), ("elements", 0, "group"),
                                 ("cues", 0, "id"), ("cues", 0, "group")])
@pytest.mark.parametrize("bad", ["", "A", "1a", "a-b", "a b", "é", "a\n", "a" * 33, None, 2])
def test_ascii_identifiers(path, bad):
    doc = scene_document()
    put(doc, path, bad)
    with pytest.raises(ConfigError):
        resolve_scene(doc)


@pytest.mark.parametrize("path", [("elements", 0, "home_xy"), ("cues", 0, "force_xy")])
@pytest.mark.parametrize("bad", [[], [0], [0, 1, 2], [[0], [1]], {"x": 0, "y": 1}, "0,1", (0, 1)])
def test_vectors_are_exact_json_arrays_of_two_reals(path, bad):
    doc = scene_document()
    put(doc, path, bad)
    with pytest.raises(ConfigError):
        resolve_scene(doc)


@pytest.mark.parametrize("collection", ["elements", "cues"])
def test_duplicate_ids_and_resource_caps(collection):
    doc = scene_document()
    doc[collection].append(deepcopy(doc[collection][0]))
    with pytest.raises(ConfigError, match="duplicate"):
        resolve_scene(doc)
    doc = scene_document()
    doc[collection] = [deepcopy(doc[collection][0]) for _ in range(13 if collection == "elements" else 17)]
    with pytest.raises(ConfigError, match="length"):
        resolve_scene(doc)


def test_empty_elements_rejected_but_empty_cues_valid():
    doc = scene_document()
    doc["cues"] = []
    assert resolve_scene(doc).cues == ()
    doc["elements"] = []
    with pytest.raises(ConfigError):
        resolve_scene(doc)


def test_force_sum_includes_nonoverlap_and_ignores_vector_cancellation():
    doc = scene_document()
    doc["cues"][1].update(group="head", start_tick=121, end_tick=150, force_xy=[-4, -2])
    with pytest.raises(ConfigError, match="conservative force sum"):
        resolve_scene(doc)


def test_scalar_limits_and_exact_accuracy_boundary_are_accepted():
    doc = scene_document()
    doc["seed"] = 2**64 - 1
    doc["raster"].update(width=64, height=512, samples_per_axis=1, invert=True)
    doc["field"]["threshold"] = 5
    doc["cues"] = []
    doc["elements"] = [dict(doc["elements"][0], home_xy=[0.1, -0.8], sigma=0.03,
                            weight=0.05, mass=2, spring_k=100, damping_c=30)]
    scene = resolve_scene(doc)
    assert scene.home_xy[0, 0] == 0.1
    assert scene.damping_c[0] / scene.mass[0] / scene.sim_hz == 0.25
    doc["elements"][0].update(home_xy=[-0.1, 0.8], sigma=0.6, weight=2, mass=0.5,
                               spring_k=5, damping_c=1)
    doc["field"]["threshold"] = 0.05
    assert resolve_scene(doc).threshold == 0.05


def test_accuracy_rejects_otherwise_scalar_valid_scene():
    doc = scene_document()
    doc["elements"][0].update(mass=0.5, damping_c=8)
    with pytest.raises(ConfigError, match="accuracy"):
        resolve_scene(doc)


def test_independent_stability_and_accuracy_inequality_branches():
    # A + 2D = 14/3600 + 260/60 > 4 at c=130.
    with pytest.raises(ConfigError, match="unstable"):
        validate_solver(1.0, 14.0, 130.0, 60)
    # A=0.0625, D=0.25 exactly meets both accuracy limits and remains stable.
    validate_solver(1.0, 225.0, 15.0, 60)
    with pytest.raises(ConfigError, match="accuracy"):
        validate_solver(1.0, 226.0, 15.0, 60)
    with pytest.raises(ConfigError, match="accuracy"):
        validate_solver(1.0, 225.0, 15.01, 60)


def test_real_negative_zero_is_normalized_without_mutating_raw_document():
    doc = scene_document()
    doc["elements"][0]["home_xy"] = [-0.0, 0]
    scene = resolve_scene(doc)
    assert not np.signbit(scene.home_xy[1, 0])
    assert np.signbit(doc["elements"][0]["home_xy"][0])
