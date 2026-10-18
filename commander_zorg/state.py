"""Owned numerical state, with no independent mutable animation clock."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import ValidatedScene


@dataclass(frozen=True, eq=False)
class SceneState:
    """A structural state carrier; the numerical guard validates candidates.

    Direct construction intentionally permits malformed test candidates. Normal
    engine code uses :func:`owned_state` to establish shape and array ownership.
    """

    tick: int
    positions: np.ndarray
    velocities: np.ndarray


CandidateState = SceneState


def owned_state(tick: int, positions, velocities) -> SceneState:
    """Copy two N-by-2 arrays into independent, readonly float64 C storage.

    Nonfinite candidate values are preserved for explicit REJECT diagnostics;
    this ownership helper does not repair or adjudicate numerical states.
    """
    if type(tick) is not int or tick < 0:
        raise ValueError("state.tick: expected nonnegative integer")
    p = np.array(positions, dtype=np.float64, order="C", copy=True)
    v = np.array(velocities, dtype=np.float64, order="C", copy=True)
    if p.ndim != 2 or p.shape[1] != 2 or p.shape[0] == 0:
        raise ValueError("state.positions: expected nonempty N-by-2 array")
    if v.shape != p.shape:
        raise ValueError("state.velocities: expected shape matching positions")
    p.flags.writeable = False
    v.flags.writeable = False
    return SceneState(tick, p, v)


def initial_state(scene: ValidatedScene) -> SceneState:
    return owned_state(0, scene.home_xy, np.zeros((len(scene.elements), 2), dtype=np.float64))


def state_mapping(state: SceneState) -> dict:
    """Return a detached finite JSON representation of a committed state."""
    if not (np.isfinite(state.positions).all() and np.isfinite(state.velocities).all()):
        raise ValueError("state: nonfinite candidates cannot be serialized as committed states")
    return {"tick": state.tick, "positions": state.positions.tolist(),
            "velocities": state.velocities.tolist()}
