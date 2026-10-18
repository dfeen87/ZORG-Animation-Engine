"""Small explicit command grammar for cz-live-event-0.1 (no wall clock)."""
from __future__ import annotations

import math

MOTION = {"left", "right", "up", "down", "squash", "stretch", "reset", "wander_on", "wander_off"}
UI = {"help", "save", "quit"}
ENVELOPE = "quintic-target-v1"


def parse_command(text: str) -> dict:
    """Arguments are strength then transition seconds; targets persist."""
    parts = text.lower().split()
    if not parts:
        raise ValueError("empty command; type help")
    action = parts[0]
    if action in UI and len(parts) == 1:
        return {"action": action}
    if parts in (["wander","on"],["wander","off"],["reset"]):
        return {"action": "reset" if action == "reset" else "wander_"+parts[1],
                "strength":0.0,"duration_ticks":120,"scope":"all","envelope":ENVELOPE}
    if action not in MOTION-{"reset","wander_on","wander_off"} or len(parts) > 3:
        raise ValueError("unknown command or arguments; type help")
    try:
        strength = float(parts[1]) if len(parts) >= 2 else (0.5 if action in {"squash","stretch"} else 0.3)
        seconds = float(parts[2]) if len(parts) == 3 else 2.0
    except ValueError:
        raise ValueError("expected strength and transition seconds") from None
    high = 0.6 if action in {"squash","stretch"} else 0.3
    if not math.isfinite(strength) or not 0.05 <= strength <= high:
        raise ValueError(f"strength must be finite in [0.05, {high}]")
    if not math.isfinite(seconds) or not 0.5 <= seconds <= 10.0:
        raise ValueError("transition seconds must be finite in [0.5, 10]")
    return {"action": action, "strength": strength, "duration_ticks": round(seconds * 60),
            "scope": "all", "envelope": ENVELOPE}


HELP = ("left/right/up/down [strength=0.3] [seconds=2]\n"
        "squash/stretch [strength=0.5] [seconds=2]\n"
        "reset | wander on | wander off | help | save | quit")
