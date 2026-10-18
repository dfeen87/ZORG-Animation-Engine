"""Strict, deterministic compilation of the accepted ``cz-scene-0.3`` schema.

No output directories or application state are created by this module. JSON
objects are parsed without discarding duplicate keys, including nested ones.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping

import numpy as np


class ConfigError(ValueError):
    """A scene is outside the versioned configuration contract."""


_ID = re.compile(r"[a-z][a-z0-9_]{0,31}\Z", re.ASCII)


@dataclass(frozen=True)
class Element:
    id: str
    group: str
    home_xy: tuple[float, float]
    sigma: float
    weight: float
    mass: float
    spring_k: float
    damping_c: float


@dataclass(frozen=True)
class Cue:
    id: str
    group: str
    start_tick: int
    end_tick: int
    envelope: str
    force_xy: tuple[float, float]


@dataclass(frozen=True, eq=False)
class ValidatedScene:
    scene_id: str
    seed: int
    width: int
    height: int
    samples_per_axis: int
    invert: bool
    sim_hz: int
    fps_out: int
    frame_count: int
    threshold: float
    max_displacement: float
    max_speed: float
    max_total_force: float
    elements: tuple[Element, ...]
    cues: tuple[Cue, ...]
    home_xy: np.ndarray
    sigma: np.ndarray
    weight: np.ndarray
    mass: np.ndarray
    spring_k: np.ndarray
    damping_c: np.ndarray
    group_indices: Mapping[str, tuple[int, ...]]
    element_order: tuple[str, ...]
    frame_ticks: tuple[int, ...]
    terminal_tick: int
    raw_bytes: bytes


class _ObjectPairs(list):
    """Distinguish parsed JSON objects from arrays until paths are known."""


@dataclass(frozen=True)
class _NonfiniteConstant:
    token: str


def _unpack_json(value, path: str):
    if isinstance(value, _NonfiniteConstant):
        raise ConfigError(f"{path}: unsupported JSON constant {value.token}")
    if isinstance(value, _ObjectPairs):
        result = {}
        for key, item in value:
            child = f"{path}.{key}"
            if key in result:
                raise ConfigError(f"{child}: duplicate object key")
            result[key] = _unpack_json(item, child)
        return result
    if isinstance(value, list):
        return [_unpack_json(item, f"{path}[{i}]") for i, item in enumerate(value)]
    return value


def _read_document(raw: bytes) -> dict:
    try:
        parsed = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_ObjectPairs,
            parse_constant=_NonfiniteConstant,
        )
        return _unpack_json(parsed, "$")
    except ConfigError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ConfigError(f"$: invalid UTF-8 JSON ({type(exc).__name__})") from None


def _exact_keys(value, expected: set[str], path: str) -> None:
    if type(value) is not dict:
        raise ConfigError(f"{path}: expected object")
    if any(type(key) is not str for key in value):
        raise ConfigError(f"{path}: object keys must be strings")
    missing = expected - value.keys()
    extra = value.keys() - expected
    if missing or extra:
        raise ConfigError(f"{path}: missing={sorted(missing)}, unknown={sorted(extra)}")


def _integer(value, path: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ConfigError(f"{path}: expected integer in [{low}, {high}]")
    return value


def _real(value, path: str, low=-math.inf, high=math.inf, *, open_low=False) -> float:
    if type(value) not in (int, float):
        raise ConfigError(f"{path}: expected finite real number")
    try:
        real = float(value)
    except (OverflowError, ValueError):
        raise ConfigError(f"{path}: real value outside finite range") from None
    if not math.isfinite(real):
        raise ConfigError(f"{path}: expected finite real number")
    if (real <= low if open_low else real < low) or real > high:
        raise ConfigError(f"{path}: outside accepted range")
    return 0.0 if real == 0.0 else real


def _identifier(value, path: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ConfigError(f"{path}: malformed ASCII ID")
    return value


def _enum(value, expected, path: str):
    if type(value) is not type(expected) or value != expected:
        raise ConfigError(f"{path}: expected {expected!r}")
    return value


def _array(value, path: str, low: int, high: int) -> list:
    if type(value) is not list or not low <= len(value) <= high:
        raise ConfigError(f"{path}: expected array of length {low} through {high}")
    return value


def _vector(value, path: str) -> tuple[float, float]:
    _array(value, path, 2, 2)
    return (_real(value[0], f"{path}[0]"), _real(value[1], f"{path}[1]"))


def validate_solver(mass, stiffness, damping, sim_hz, path: str = "$") -> None:
    """Check the exact Euler stability inequality and accuracy envelope.

    This helper also accepts out-of-schema positive parameters so the stability
    inequality can be tested independently of the narrower scene scalar ranges.
    """
    m = _real(mass, f"{path}.mass", 0.0, open_low=True)
    k = _real(stiffness, f"{path}.spring_k", 0.0, open_low=True)
    c = _real(damping, f"{path}.damping_c", 0.0, open_low=True)
    hz = _real(sim_hz, f"{path}.sim_hz", 0.0, open_low=True)
    h = 1.0 / hz
    a = h * h * k / m
    d = h * c / m
    if not (a > 0.0 and d > 0.0 and a + 2.0 * d < 4.0):
        raise ConfigError(f"{path}: unstable numerical parameters")
    if h * math.sqrt(k / m) > 0.25 or d > 0.25:
        raise ConfigError(f"{path}: outside accuracy envelope")


def _readonly(values) -> np.ndarray:
    result = np.array(values, dtype=np.float64, order="C", copy=True)
    result.flags.writeable = False
    return result


def load_scene(path: str | Path) -> ValidatedScene:
    """Read and fully validate UTF-8 JSON, retaining its exact source bytes."""
    raw = Path(path).read_bytes()
    return resolve_scene(_read_document(raw), raw_bytes=raw)


def resolve_scene(doc: dict, raw_bytes: bytes | None = None) -> ValidatedScene:
    """Validate a JSON mapping without mutating it and compile owned arrays."""
    _exact_keys(doc, {"schema_version", "scene_id", "seed", "raster", "timeline",
                      "field", "elements", "cues", "limits"}, "$")
    _enum(doc["schema_version"], "cz-scene-0.3", "$.schema_version")
    scene_id = _identifier(doc["scene_id"], "$.scene_id")
    seed = _integer(doc["seed"], "$.seed", 0, 2**64 - 1)

    raster = doc["raster"]
    _exact_keys(raster, {"width", "height", "samples_per_axis", "invert"}, "$.raster")
    width = _integer(raster["width"], "$.raster.width", 64, 512)
    height = _integer(raster["height"], "$.raster.height", 64, 512)
    samples = _integer(raster["samples_per_axis"], "$.raster.samples_per_axis", 1, 2)
    if type(raster["invert"]) is not bool:
        raise ConfigError("$.raster.invert: expected boolean")

    timeline = doc["timeline"]
    _exact_keys(timeline, {"sim_hz", "fps_out", "frame_count"}, "$.timeline")
    sim_hz = _integer(timeline["sim_hz"], "$.timeline.sim_hz", 60, 120)
    if sim_hz not in (60, 120):
        raise ConfigError("$.timeline.sim_hz: expected 60 or 120")
    fps_out = _integer(timeline["fps_out"], "$.timeline.fps_out", 30, 30)
    if sim_hz % fps_out:
        raise ConfigError("$.timeline.fps_out: must divide simulation frequency")
    frame_count = _integer(timeline["frame_count"], "$.timeline.frame_count", 1, 360)
    ratio = sim_hz // fps_out
    terminal_tick = frame_count * ratio

    field = doc["field"]
    _exact_keys(field, {"kind", "threshold"}, "$.field")
    _enum(field["kind"], "gaussian-separable-v1", "$.field.kind")
    threshold = _real(field["threshold"], "$.field.threshold", 0.05, 5.0)

    limits = doc["limits"]
    _exact_keys(limits, {"max_displacement", "max_speed", "max_total_force"}, "$.limits")
    max_displacement = _real(limits["max_displacement"], "$.limits.max_displacement", 0.0, 0.75, open_low=True)
    max_speed = _real(limits["max_speed"], "$.limits.max_speed", 0.0, 3.0, open_low=True)
    max_total_force = _real(limits["max_total_force"], "$.limits.max_total_force", 0.0, 6.0, open_low=True)

    elements = []
    seen = set()
    for i, item in enumerate(_array(doc["elements"], "$.elements", 1, 12)):
        path = f"$.elements[{i}]"
        _exact_keys(item, {"id", "group", "home_xy", "sigma", "weight", "mass", "spring_k", "damping_c"}, path)
        identifier = _identifier(item["id"], f"{path}.id")
        if identifier in seen:
            raise ConfigError(f"{path}.id: duplicate element ID {identifier!r}")
        seen.add(identifier)
        group = _identifier(item["group"], f"{path}.group")
        home = _vector(item["home_xy"], f"{path}.home_xy")
        if abs(home[0]) > 0.8 * (width / height):
            raise ConfigError(f"{path}.home_xy[0]: outside 80 percent viewport half-extent")
        if abs(home[1]) > 0.8:
            raise ConfigError(f"{path}.home_xy[1]: outside 80 percent viewport half-extent")
        sigma = _real(item["sigma"], f"{path}.sigma", 0.03, 0.60)
        weight = _real(item["weight"], f"{path}.weight", 0.05, 2.0)
        mass = _real(item["mass"], f"{path}.mass", 0.5, 2.0)
        spring_k = _real(item["spring_k"], f"{path}.spring_k", 5.0, 100.0)
        damping_c = _real(item["damping_c"], f"{path}.damping_c", 1.0, 30.0)
        validate_solver(mass, spring_k, damping_c, sim_hz, path)
        elements.append(Element(identifier, group, home, sigma, weight, mass, spring_k, damping_c))
    elements = tuple(sorted(elements, key=lambda item: item.id))
    groups = {group: tuple(i for i, element in enumerate(elements) if element.group == group)
              for group in sorted({element.group for element in elements})}

    cues = []
    seen = set()
    for i, item in enumerate(_array(doc["cues"], "$.cues", 0, 16)):
        path = f"$.cues[{i}]"
        _exact_keys(item, {"id", "group", "start_tick", "end_tick", "envelope", "force_xy"}, path)
        identifier = _identifier(item["id"], f"{path}.id")
        if identifier in seen:
            raise ConfigError(f"{path}.id: duplicate cue ID {identifier!r}")
        seen.add(identifier)
        group = _identifier(item["group"], f"{path}.group")
        if group not in groups:
            raise ConfigError(f"{path}.group: target group has no elements")
        start = _integer(item["start_tick"], f"{path}.start_tick", 0, terminal_tick)
        end = _integer(item["end_tick"], f"{path}.end_tick", 0, terminal_tick)
        if start >= end:
            raise ConfigError(f"{path}.end_tick: require start_tick < end_tick")
        envelope = _enum(item["envelope"], "quartic-pulse-v1", f"{path}.envelope")
        force = _vector(item["force_xy"], f"{path}.force_xy")
        if abs(force[0]) > max_total_force or abs(force[1]) > max_total_force:
            raise ConfigError(f"{path}.force_xy: exceeds conservative force bound")
        if math.hypot(*force) > max_total_force:
            raise ConfigError(f"{path}.force_xy: exceeds conservative force bound")
        cues.append(Cue(identifier, group, start, end, envelope, force))
    cues = tuple(sorted(cues, key=lambda item: item.id))
    for group in groups:
        total = sum(math.hypot(*cue.force_xy) for cue in cues if cue.group == group)
        if total > max_total_force:
            raise ConfigError(f"$.cues: conservative force sum for group {group!r} exceeds limits.max_total_force")

    if raw_bytes is None:
        raw_bytes = json.dumps(doc, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    elif type(raw_bytes) is not bytes:
        raise ConfigError("$: raw_bytes must be bytes")
    return ValidatedScene(
        scene_id, seed, width, height, samples, raster["invert"], sim_hz, fps_out,
        frame_count, threshold, max_displacement, max_speed, max_total_force,
        elements, cues, _readonly([item.home_xy for item in elements]),
        _readonly([item.sigma for item in elements]),
        _readonly([item.weight for item in elements]),
        _readonly([item.mass for item in elements]),
        _readonly([item.spring_k for item in elements]),
        _readonly([item.damping_c for item in elements]),
        MappingProxyType(groups), tuple(item.id for item in elements),
        tuple(i * ratio for i in range(frame_count)), terminal_tick, raw_bytes,
    )


def resolved_mapping(scene: ValidatedScene) -> dict:
    """Return a detached JSON-compatible, sorted semantic configuration."""
    return {
        "schema_version": "cz-scene-0.3",
        "scene_id": scene.scene_id,
        "seed": scene.seed,
        "raster": {"width": scene.width, "height": scene.height,
                   "samples_per_axis": scene.samples_per_axis, "invert": scene.invert},
        "timeline": {"sim_hz": scene.sim_hz, "fps_out": scene.fps_out,
                     "frame_count": scene.frame_count},
        "field": {"kind": "gaussian-separable-v1", "threshold": scene.threshold},
        "elements": [{"id": item.id, "group": item.group, "home_xy": list(item.home_xy),
                      "sigma": item.sigma, "weight": item.weight, "mass": item.mass,
                      "spring_k": item.spring_k, "damping_c": item.damping_c}
                     for item in scene.elements],
        "cues": [{"id": item.id, "group": item.group, "start_tick": item.start_tick,
                  "end_tick": item.end_tick, "envelope": item.envelope,
                  "force_xy": list(item.force_xy)} for item in scene.cues],
        "limits": {"max_displacement": scene.max_displacement,
                   "max_speed": scene.max_speed, "max_total_force": scene.max_total_force},
    }
