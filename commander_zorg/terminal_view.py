"""Small ANSI viewport backed by the unchanged Gaussian field evaluator.

The preview uses a separate, inexpensive raster. It never feeds pixels or
display timing back into simulation state or final offline rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
import shutil
import textwrap
from typing import Any

import numpy as np

from .field import evaluate_samples
from .raster import rasterize


MAX_INPUT = 160


def use_monochrome(force: bool = False, environment: Any = None) -> bool:
    """Use portable blocks unless the terminal explicitly advertises truecolor.

    Apple's Terminal commonly advertises xterm-256color without 24-bit color.
    Its default must still show geometry rather than an unsupported-color box.
    """
    environment = os.environ if environment is None else environment
    term = environment.get("TERM", "").lower()
    color = environment.get("COLORTERM", "").lower()
    advertised = color in ("truecolor", "24bit") or "direct" in term
    return force or term in ("dumb", "unknown") or not advertised


def detect_color_mode(force: bool = False, environment: Any = None) -> str:
    """Detect creator-preview color while retaining conservative legacy defaults."""
    environment = os.environ if environment is None else environment
    term = environment.get("TERM", "").lower()
    color = environment.get("COLORTERM", "").lower()
    if force or term in ("dumb", "unknown"):
        return "mono"
    if color in ("truecolor", "24bit") or "direct" in term:
        return "truecolor"
    return "256" if "256color" in term else "mono"


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


def _xterm256(pixels: np.ndarray) -> np.ndarray:
    """Choose the nearest standard xterm color cube or grayscale entry."""
    rgb = pixels.astype(np.int32)
    levels = np.array([0, 95, 135, 175, 215, 255], dtype=np.int32)
    indices = np.square(rgb[..., None] - levels).argmin(axis=-1)
    cube = 16 + 36 * indices[..., 0] + 6 * indices[..., 1] + indices[..., 2]
    cube_distance = np.square(rgb - levels[indices]).sum(axis=-1)
    grays = np.arange(8, 239, 10, dtype=np.int32)
    gray_distances = np.square(rgb[..., None, :] - grays[:, None]).sum(axis=-1)
    gray_index = gray_distances.argmin(axis=-1)
    gray_distance = np.take_along_axis(gray_distances, gray_index[..., None], axis=-1)[..., 0]
    return np.where(gray_distance < cube_distance, 232 + gray_index, cube).astype(np.uint8)


def half_blocks(pixels: np.ndarray, *, mono: bool = False,
                color_mode: str = "truecolor") -> list[str]:
    """Encode paired coverage or RGB raster rows with matching foreground/background."""
    if (not isinstance(pixels, np.ndarray) or pixels.dtype != np.uint8
            or pixels.ndim not in (2, 3) or pixels.shape[0] % 2
            or (pixels.ndim == 3 and pixels.shape[2] != 3)):
        raise ValueError("preview pixels must be an even-height uint8 gray or RGB raster")
    if color_mode not in ("truecolor", "256"):
        raise ValueError("preview color_mode must be truecolor or 256")
    if mono and pixels.ndim == 3:
        pixels = ((pixels.astype(np.int32) * [299, 587, 114]).sum(axis=2) + 500) // 1000
    elif not mono:
        rgb = np.repeat(pixels[..., None], 3, axis=2) if pixels.ndim == 2 else pixels
        colors = _xterm256(rgb) if color_mode == "256" else rgb
    rows = []
    for y in range(0, pixels.shape[0], 2):
        if mono:
            lookup = (" ", "▄", "▀", "█")
            rows.append("".join(lookup[2 * int(a >= 128) + int(b >= 128)]
                                for a, b in zip(pixels[y], pixels[y + 1], strict=True)))
        else:
            line = []
            previous = None
            for upper, lower in zip(colors[y], colors[y + 1], strict=True):
                pair = ((int(upper), int(lower)) if color_mode == "256"
                        else (tuple(map(int, upper)), tuple(map(int, lower))))
                if pair != previous:
                    a, b = pair
                    if color_mode == "256":
                        line.append(f"\x1b[38;5;{a}m\x1b[48;5;{b}m")
                    else:
                        line.append(f"\x1b[38;2;{a[0]};{a[1]};{a[2]}m"
                                    f"\x1b[48;2;{b[0]};{b[1]};{b[2]}m")
                    previous = pair
                line.append("▀")
            rows.append("".join(line) + "\x1b[0m")
    return rows


def frame_lines(runtime: Any, size: os.terminal_size, *, command: str = "",
                status: str = "Ready; type help", fps: float = 0.0,
                mono: bool = False) -> list[str]:
    """Fit the viewport and command area into the current terminal dimensions."""
    columns, rows = max(1, size.columns), max(1, size.lines)
    paragraphs = status.splitlines() or [""]
    metadata = [
        f"{'WANDER' if runtime.wander else 'DIRECTED'}  SEED {runtime.config['seed']}  "
        f"TICK {runtime.state.tick}  PREVIEW {fps:.1f} FPS",
        f"COMMAND: {command}",
    ]
    if rows < 6 or columns < 12:
        # A tiny terminal remains usable; no hidden raster is computed.
        return (["ZORG LIVE"] + metadata + [f"STATUS: {paragraphs[0]}"])[-rows:]
    wrapped = [line for paragraph in paragraphs for line in
               (textwrap.wrap(paragraph, width=max(1, columns - 8)) or [""])] or [""]
    # Keep input visible and at least one animation row even when help wraps.
    status_limit = max(1, rows - 4)
    if len(wrapped) > status_limit:
        wrapped = wrapped[:status_limit]
        wrapped[-1] = "resize for full status/help"
    status_lines = [("STATUS: " if index == 0 else "        ") + line
                    for index, line in enumerate(wrapped)]
    footer = metadata + status_lines
    body_rows = rows - 1 - len(footer)
    side = min(columns, body_rows * 2, 96)
    side -= side % 2
    preview = replace(runtime.scene, width=side, height=side, samples_per_axis=1)
    pixels = rasterize(evaluate_samples(runtime.state, preview), preview)
    # Display foreground as a light silhouette regardless of export inversion.
    if preview.invert:
        pixels = np.subtract(np.uint8(255), pixels)
    color_mode = getattr(runtime, "terminal_color_mode", "truecolor")
    monochrome = mono or color_mode == "mono"
    chromatic = getattr(runtime, "chromatic", None)
    if not monochrome and chromatic is not None and chromatic.enabled:
        # LiveScene delegates inversion to its resolved dataclass base. Color
        # receives the foreground coverage already un-inverted above.
        if preview.invert:
            preview = (replace(preview, base=replace(preview.base, invert=False))
                       if hasattr(preview, "base") else replace(preview, invert=False))
        pixels = chromatic.rgb(pixels, runtime.state, preview,
                               runtime.config["seed"], runtime.state.tick)
    image = half_blocks(pixels, mono=monochrome,
                        color_mode="256" if color_mode == "256" else "truecolor")
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
