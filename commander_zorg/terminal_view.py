"""Small ANSI viewport backed by the unchanged Gaussian field evaluator.

The preview uses a separate, inexpensive raster. It never feeds pixels or
display timing back into simulation state or final offline rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
import shutil
from typing import Any

import numpy as np

from .field import evaluate_samples
from .raster import rasterize


MAX_INPUT = 160


@dataclass(frozen=True)
class InputEvent:
    kind: str
    text: str = ""


class CommandInput:
    """Bounded ASCII line editing without terminal echo or control injection."""

    def __init__(self) -> None:
        self.text = ""
        self.overflow = False
        self._escape = 0
        self._last_cr = False

    def feed(self, data: bytes) -> list[InputEvent]:
        events = []
        for value in data:
            if value in (3, 4):
                events.append(InputEvent("interrupt" if value == 3 else "eof"))
                continue
            if self._escape:
                if self._escape == 1 and value in (ord("["), ord("O")):
                    self._escape = 2
                elif 0x40 <= value <= 0x7E:
                    self._escape = 0
                continue
            if value == 27:
                self._escape = 1
                continue
            if value in (10, 13):
                if value == 10 and self._last_cr:
                    self._last_cr = False
                    continue
                self._last_cr = value == 13
                if self.overflow:
                    events.append(InputEvent("invalid", "Command exceeds 160 characters"))
                elif self.text.strip():
                    events.append(InputEvent("command", self.text))
                self.text = ""
                self.overflow = False
                continue
            self._last_cr = False
            if value in (8, 127):
                self.text = self.text[:-1]
            elif 32 <= value <= 126:
                if len(self.text) < MAX_INPUT:
                    self.text += chr(value)
                else:
                    self.overflow = True
        return events


def terminal_size(stream: Any) -> os.terminal_size:
    try:
        return os.get_terminal_size(stream.fileno())
    except (OSError, ValueError, AttributeError):
        return shutil.get_terminal_size((80, 24))


def half_blocks(pixels: np.ndarray, *, mono: bool = False) -> list[str]:
    """Encode pairs of genuine raster rows as terminal cells."""
    if pixels.dtype != np.uint8 or pixels.ndim != 2 or pixels.shape[0] % 2:
        raise ValueError("preview pixels must be an even-height uint8 raster")
    rows = []
    for y in range(0, pixels.shape[0], 2):
        if mono:
            lookup = (" ", "▄", "▀", "█")
            rows.append("".join(lookup[2 * int(a >= 128) + int(b >= 128)]
                                for a, b in zip(pixels[y], pixels[y + 1], strict=True)))
        else:
            line = []
            previous = None
            for upper, lower in zip(pixels[y], pixels[y + 1], strict=True):
                pair = (int(upper), int(lower))
                if pair != previous:
                    a, b = pair
                    line.append(f"\x1b[38;2;{a};{a};{a}m\x1b[48;2;{b};{b};{b}m")
                    previous = pair
                line.append("▀")
            rows.append("".join(line) + "\x1b[0m")
    return rows


def frame_lines(runtime: Any, size: os.terminal_size, *, command: str = "",
                status: str = "Ready; type help", fps: float = 0.0,
                mono: bool = False) -> list[str]:
    """Fit the viewport and command area into the current terminal dimensions."""
    columns, rows = max(1, size.columns), max(1, size.lines)
    footer = [
        f"{'WANDER' if runtime.wander else 'DIRECTED'}  SEED {runtime.config['seed']}  "
        f"TICK {runtime.state.tick}  PREVIEW {fps:.1f} FPS",
        f"COMMAND: {command}",
        f"STATUS: {status}",
    ]
    if rows < 6 or columns < 12:
        # A tiny terminal remains usable; no hidden raster is computed.
        return (["ZORG LIVE"] + footer)[-rows:]
    body_rows = rows - 4
    side = min(columns, body_rows * 2, 96)
    side -= side % 2
    preview = replace(runtime.scene, width=side, height=side, samples_per_axis=1)
    pixels = rasterize(evaluate_samples(runtime.state, preview), preview)
    # Display foreground as a light silhouette regardless of export inversion.
    if preview.invert:
        pixels = np.subtract(np.uint8(255), pixels)
    image = half_blocks(pixels, mono=mono)
    padding = " " * ((columns - side) // 2)
    image = [padding + line for line in image]
    image += [""] * (body_rows - len(image))
    return ["ZORG LIVE — MATHEMATICAL MORPH LAB"[:columns]] + image + footer


def draw_frame(stream: Any, lines: list[str], size: os.terminal_size) -> None:
    """Overwrite fixed screen rows without emitting scrolling newlines.

    Colored raster rows already obey the column bound. Plain text is sliced
    before insertion, so arbitrary status text cannot wrap into the viewport.
    """
    columns, rows = max(1, size.columns), max(1, size.lines)
    parts = ["\x1b[0m"]
    for index in range(rows):
        line = lines[index] if index < len(lines) else ""
        if "\x1b[" not in line:
            line = line[:columns]
        parts.append(f"\x1b[{index + 1};1H\x1b[2K{line}")
    parts.append("\x1b[0m")
    stream.write("".join(parts))
    stream.flush()
