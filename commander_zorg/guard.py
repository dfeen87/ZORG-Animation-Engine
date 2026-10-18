"""Pure deterministic validation; invalid candidates are never repaired."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class Decision:
    status: str
    attempted_tick: int
    reasons: tuple[dict, ...]


class InvalidStateError(ValueError):
    """A previous state cannot be used to propose an auditable transition."""

    def __init__(self, reasons):
        self.reasons = tuple(reasons)
        super().__init__("invalid previous state: " + "; ".join(
            f"{item['path']}: {item['code']} ({item['detail']})"
            for item in self.reasons))


def _safe_number(value) -> str:
    value = float(value)
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "+inf" if value > 0 else "-inf"
    return repr(value)


def validate_state(state, scene) -> list[dict]:
    """Describe structural, finite, and configured bound failures in order.

    Element identity is the immutable scene index plan: a state carries no
    alternative IDs or mutable ordering. Diagnostics contain JSON-safe strings.
    """
    failures = []

    def fail(code, path, detail, element_id=None):
        failures.append({"code": code, "path": path,
                         "element_id": element_id, "detail": detail})

    tick = state.tick
    if type(tick) is not int or not 0 <= tick <= scene.terminal_tick:
        fail("BAD_TICK", "tick", "expected integer in simulation tick range")
    expected_shape = (len(scene.elements), 2)
    valid_arrays = {}
    for name, code in (("positions", "NONFINITE_POSITION"),
                       ("velocities", "NONFINITE_VELOCITY")):
        values = getattr(state, name)
        if not isinstance(values, np.ndarray):
            fail("BAD_SHAPE", name, "expected numpy array")
            continue
        if values.shape != expected_shape:
            fail("BAD_SHAPE", name, f"expected shape {expected_shape}; got {values.shape}")
        if values.dtype != np.dtype(np.float64):
            fail("BAD_DTYPE", name, f"expected float64; got {values.dtype}")
        if not values.flags.c_contiguous:
            fail("BAD_LAYOUT", name, "expected C-contiguous array")
        if values.shape != expected_shape or values.dtype != np.dtype(np.float64):
            continue
        finite = np.isfinite(values)
        for row, component in np.argwhere(~finite):
            element_id = scene.elements[int(row)].id
            fail(code, f"{name}[{int(row)}][{int(component)}]",
                 _safe_number(values[row, component]), element_id)
        if finite.all():
            valid_arrays[name] = values
    if "positions" in valid_arrays:
        displacement = valid_arrays["positions"] - scene.home_xy
        with np.errstate(over="ignore", invalid="ignore"):
            norms = np.hypot(displacement[:, 0], displacement[:, 1])
        for row in np.flatnonzero(norms > scene.max_displacement):
            fail("DISPLACEMENT_LIMIT", f"positions[{int(row)}]",
                 f"norm {_safe_number(norms[row])} exceeds {_safe_number(scene.max_displacement)}",
                 scene.elements[int(row)].id)
    if "velocities" in valid_arrays:
        values = valid_arrays["velocities"]
        with np.errstate(over="ignore", invalid="ignore"):
            norms = np.hypot(values[:, 0], values[:, 1])
        for row in np.flatnonzero(norms > scene.max_speed):
            fail("SPEED_LIMIT", f"velocities[{int(row)}]",
                 f"norm {_safe_number(norms[row])} exceeds {_safe_number(scene.max_speed)}",
                 scene.elements[int(row)].id)
    return failures


def check_transition(previous, candidate, scene) -> Decision:
    """Return ACCEPT/REJECT without committing or modifying either state."""
    previous_failures = validate_state(previous, scene)
    failures = []
    if previous_failures:
        failures.append({"code": "INVALID_PREVIOUS", "path": "previous",
                         "element_id": None, "detail": "source state is invalid"})
        failures.extend({**reason, "path": "previous." + reason["path"]}
                        for reason in previous_failures)
    failures.extend(validate_state(candidate, scene))
    if (type(previous.tick) is int and type(candidate.tick) is int
            and candidate.tick != previous.tick + 1):
        failures.append({"code": "BAD_TICK", "path": "tick", "element_id": None,
                         "detail": f"expected next tick {previous.tick + 1}; got {candidate.tick}"})
    attempted_tick = (previous.tick + 1 if type(previous.tick) is int
                      else candidate.tick if type(candidate.tick) is int else 0)
    return Decision("REJECT" if failures else "ACCEPT", attempted_tick, tuple(failures))
