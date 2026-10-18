"""Pure semi-implicit Euler candidates; acceptance belongs to the guard."""

from __future__ import annotations

import numpy as np

from .cues import cue_forces
from .guard import InvalidStateError, validate_state
from .state import owned_state


def propose_step(previous, scene):
    """Own a new candidate using previous-velocity damping and updated position.

    Arithmetic nonfinites remain in the candidate for the guard to reject with
    component diagnostics. No clamp, repair, fallback, or state commit occurs.
    """
    reasons = validate_state(previous, scene)
    if reasons:
        raise InvalidStateError(reasons)
    if previous.tick == scene.terminal_tick:
        raise InvalidStateError([{
            "code": "BAD_TICK", "path": "tick", "element_id": None,
            "detail": "terminal state has no following transition",
        }])
    h = 1.0 / scene.sim_hz
    force = cue_forces(previous.tick, scene)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        displacement = previous.positions - scene.home_xy
        acceleration = (-scene.spring_k[:, None] * displacement
                        - scene.damping_c[:, None] * previous.velocities
                        + force) / scene.mass[:, None]
        velocity_next = previous.velocities + h * acceleration
        position_next = previous.positions + h * velocity_next
    return owned_state(previous.tick + 1, position_next, velocity_next)
