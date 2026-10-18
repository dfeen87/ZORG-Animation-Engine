"""Versioned fixed-tick live dynamics; Build 0 numerical contracts are unchanged.

The external bias is k * target_offset, bounded before the same semi-implicit
Euler arithmetic as Build 0. A live horizon adapter reuses its unmodified guard.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math

import numpy as np

from .canonical import canonical_bytes, strict_json
from .config import resolve_scene
from .guard import check_transition, validate_state, InvalidStateError
from .state import initial_state, owned_state, state_mapping
from .live_commands import parse_command, UI


def validate_config(config: dict) -> dict:
    config = strict_json(canonical_bytes(config))  # Detached, rejects nonfinite.
    expected = {"schema_version", "seed", "sim_hz", "fps_out", "max_ticks", "wander", "scene"}
    if type(config) is not dict or set(config) != expected:
        raise ValueError("live config: wrong fields")
    if config["schema_version"] != "cz-live-config-0.1":
        raise ValueError("unsupported live config version")
    if type(config["seed"]) is not int or not 0 <= config["seed"] <= 2**32-1:
        raise ValueError("seed must be a uint32")
    if type(config["sim_hz"]) is not int or config["sim_hz"] != 60:
        raise ValueError("live simulation requires 60 Hz")
    if type(config["fps_out"]) is not int or config["fps_out"] != 30:
        raise ValueError("live export requires 30 FPS")
    if type(config["max_ticks"]) is not int or not 2 <= config["max_ticks"] <= 216000:
        raise ValueError("max_ticks must be in [2, 216000] (up to one hour)")
    if type(config["wander"]) is not bool:
        raise ValueError("wander must be boolean")
    base = resolve_scene(config["scene"])
    if base.cues or base.sim_hz != 60:
        raise ValueError("live geometry requires 60 Hz with no finite-scene cues")
    return config


@dataclass(frozen=True)
class LiveScene:
    """Internal live guard/raster adapter, never serialized as cz-scene-0.3."""
    base: object
    terminal_tick: int
    width: int
    height: int
    samples_per_axis: int

    def __getattr__(self, name):
        return getattr(self.base, name)


class LiveNumericalError(RuntimeError):
    exit_code = 3


def smoothstep(u):
    if u <= 0:
        return 0.0
    if u >= 1:
        return 1.0
    return u*u*u*(10 + u*(-15 + 6*u))


class Blend:
    def __init__(self, value):
        self.start = self.end = np.array(value, dtype=np.float64)
        self.tick = 0
        self.duration = 1

    def at(self, tick):
        s = smoothstep((tick - self.tick) / self.duration)
        return self.start + s*(self.end-self.start)

    def set(self, target, tick, duration):
        self.start = self.at(tick).copy()
        self.end = np.array(target, dtype=np.float64)
        self.tick, self.duration = tick, duration


class LiveRuntime:
    def __init__(self, config):
        self.config = validate_config(config)
        base = resolve_scene(self.config["scene"])
        self.scene = LiveScene(base, self.config["max_ticks"], base.width, base.height, base.samples_per_axis)
        self.state = initial_state(self.scene)
        self._trace = hashlib.sha256(canonical_bytes(state_mapping(self.state)))
        self.events = []
        self.wander = self.config["wander"]
        self.translation = Blend([0., 0.])
        self.wander_mix = Blend(float(self.wander))
        self._phases = []
        for element in base.elements:
            raw = hashlib.sha256(f"live-wander-v1:{self.config['seed']}:{element.id}".encode()).digest()
            self._phases.append([int.from_bytes(raw[i:i+4], 'big') / 2**32 * math.tau for i in (0, 4)])
        self._phases = np.array(self._phases)

    def accept(self, text):
        command = parse_command(text)
        if command["action"] in UI:
            raise ValueError("UI command does not schedule motion")
        if self.state.tick >= self.scene.terminal_tick:
            raise ValueError("session reached its configured tick limit")
        event = {"schema_version": "cz-live-event-0.1", "sequence": len(self.events),
                 "effective_tick": self.state.tick, **command}
        self.apply_event(event)
        return event.copy()

    def apply_event(self, event):
        """Validate replay events via the same grammar, then apply in sequence."""
        expected = {"schema_version", "sequence", "effective_tick", "action", "strength", "duration_ticks", "scope", "envelope"}
        if type(event) is not dict or set(event) != expected:
            raise ValueError("event: wrong fields")
        if (event["schema_version"] != "cz-live-event-0.1"
                or type(event["sequence"]) is not int or event["sequence"] != len(self.events)
                or type(event["effective_tick"]) is not int or event["effective_tick"] != self.state.tick
                or not self.state.tick < self.scene.terminal_tick):
            raise ValueError("event: invalid version, sequence or effective tick")
        if (type(event["duration_ticks"]) is not int or not 30 <= event["duration_ticks"] <= 600
                or type(event["strength"]) not in (int,float)):
            raise ValueError("event: invalid parameter types")
        normalized = parse_command(f"{event['action']} {event['strength']} {event['duration_ticks']/60}")
        if any(event[k] != v for k,v in normalized.items()):
            raise ValueError("event: invalid normalized parameters")
        self.translation.set([-event["strength"], 0.], self.state.tick, event["duration_ticks"])
        self.events.append(strict_json(canonical_bytes(event)))

    def target_offsets(self, tick):
        t = tick / 60.0
        ramp = smoothstep(t/2.0)
        # Low frequency global wandering plus coherent seeded differential motion.
        phase = self._phases
        organic = np.column_stack((.025*np.sin(.71*t+phase[:,0]), .035*np.sin(.57*t+phase[:,1])))
        organic += [.055*math.sin(.43*t), .045*math.sin(.37*t)]
        return self.translation.at(tick) + ramp*self.wander_mix.at(tick)*organic

    def step(self):
        previous = self.state
        reasons = validate_state(previous, self.scene)
        if reasons:
            raise InvalidStateError(reasons)
        if previous.tick >= self.scene.terminal_tick:
            raise ValueError("session reached its configured tick limit")
        force = self.scene.spring_k[:,None]*self.target_offsets(previous.tick)
        if not np.isfinite(force).all() or np.any(np.linalg.norm(force,axis=1) > self.scene.max_total_force):
            raise LiveNumericalError(f"force limit rejected at tick {previous.tick}; state not committed")
        h = 1.0/self.config["sim_hz"]
        with np.errstate(over="ignore",invalid="ignore",divide="ignore"):
            displacement = previous.positions-self.scene.home_xy
            acceleration = (-self.scene.spring_k[:,None]*displacement
                            -self.scene.damping_c[:,None]*previous.velocities+force)/self.scene.mass[:,None]
            velocity = previous.velocities+h*acceleration
            position = previous.positions+h*velocity
        candidate = owned_state(previous.tick+1,position,velocity)
        decision = check_transition(previous,candidate,self.scene)
        if decision.status != "ACCEPT":
            raise LiveNumericalError(f"transition rejected at tick {candidate.tick}: {decision.reasons}")
        self.state = candidate
        self._trace.update(canonical_bytes(state_mapping(candidate)))
        return candidate

    @property
    def trajectory_sha256(self):
        return self._trace.hexdigest()
