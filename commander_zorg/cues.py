"""Deterministic midpoint-sampled force cues (no mutable scheduler)."""

from __future__ import annotations

import numpy as np


def quartic_pulse(u: float) -> float:
    """The normative C1 pulse, with zero support outside ``0 < u < 1``."""
    return 16.0 * u * u * (1.0 - u) * (1.0 - u) if 0.0 < u < 1.0 else 0.0


def cue_forces(tick: int, scene) -> np.ndarray:
    """Return the full cue force on each element for transition tick→tick+1.

    Validated scene cues and group indices are already in ascending ASCII ID
    order. Accumulation deliberately remains scalar and in that order.
    """
    if type(tick) is not int or not 0 <= tick < scene.terminal_tick:
        raise ValueError("tick: not a valid transition-start tick")
    result = np.zeros((len(scene.elements), 2), dtype=np.float64)
    for cue in scene.cues:
        u = (tick + 0.5 - cue.start_tick) / (cue.end_tick - cue.start_tick)
        envelope = quartic_pulse(u)
        force_x, force_y = cue.force_xy
        for index in scene.group_indices[cue.group]:
            result[index, 0] += envelope * force_x
            result[index, 1] += envelope * force_y
    return result
