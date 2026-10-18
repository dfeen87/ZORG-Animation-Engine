"""Opt-in deterministic color applied after the unchanged coverage raster.

``material-gaussian-palette-v1`` pulls pixel centers back toward control home
positions using normalized Gaussian influence weights. A rigid translation of
every control therefore translates the material coordinates exactly in real
arithmetic. Two smooth, seeded lattice textures remain fixed in those local
coordinates; they never use redraw count, a random generator, or wall time.

RGB anchors interpolate directly in sRGB with the same quintic timing as
geometry. Coverage composites against black, or white for inverted scenes.
This presentation stage neither modifies coverage nor writes numerical state.
"""
from __future__ import annotations

import io
from typing import Any

import numpy as np
from PIL import Image

from .live_motion import Blend


ALGORITHM = 'material-gaussian-palette-v1'
DEFAULT_DURATION_TICKS = 120
# Restrained shadow, middle, and highlight colors. Entries are immutable tuples.
PALETTES = {
    'neutral': ((167, 176, 187), (216, 222, 230), (248, 250, 253)),
    'circle': ((167, 101, 36), (232, 174, 66), (255, 232, 158)),
    'oval': ((79, 129, 149), (147, 183, 198), (219, 233, 241)),
    'cloud': ((73, 145, 208), (126, 197, 240), (218, 241, 255)),
    'hill': ((48, 103, 68), (105, 164, 104), (195, 223, 158)),
}


def _timing(tick: int, duration: int) -> None:
    if type(tick) is not int or tick < 0:
        raise ValueError('color tick must be a nonnegative integer')
    if type(duration) is not int or not 1 <= duration <= 600:
        raise ValueError('color duration_ticks must be in [1, 600]')


def _target_palette(target: str) -> str:
    if type(target) is not str:
        raise ValueError('color target must be text')
    return target if target in PALETTES else 'neutral'


def _rgb_anchors(values: Any) -> np.ndarray:
    if (type(values) is not list or len(values) != 3
            or any(type(row) is not list or len(row) != 3 for row in values)
            or any(type(value) not in (int, float) for row in values for value in row)):
        raise ValueError('palette anchors must be three RGB triples')
    # Reject enormous JSON integers before float64 conversion can overflow.
    if any(value < 0 or value > 255 for row in values for value in row):
        raise ValueError('palette RGB values must be finite and in [0, 255]')
    result = np.array(values, dtype=np.float64)
    if not np.isfinite(result).all() or np.any(result < 0) or np.any(result > 255):
        raise ValueError('palette RGB values must be finite and in [0, 255]')
    return result


def _lattice_hash(x: np.ndarray, y: np.ndarray, seed: int) -> np.ndarray:
    """Defined uint32 mixing; operations intentionally wrap modulo 2**32."""
    a = x.astype(np.int64).astype(np.uint32) * np.uint32(0x1F123BB5)
    b = y.astype(np.int64).astype(np.uint32) * np.uint32(0x5F356495)
    value = a ^ b ^ np.uint32(seed)
    value ^= value >> np.uint32(16)
    value *= np.uint32(0x7FEB352D)
    value ^= value >> np.uint32(15)
    value *= np.uint32(0x846CA68B)
    value ^= value >> np.uint32(16)
    return value.astype(np.float64) / 4294967295.0


def _noise(x: np.ndarray, y: np.ndarray, seed: int, scale: float) -> np.ndarray:
    x, y = x * scale, y * scale
    ix, iy = np.floor(x), np.floor(y)
    tx, ty = x - ix, y - iy
    # Cubic interpolation gives a continuous texture and continuous first slope.
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a, b = _lattice_hash(ix, iy, seed), _lattice_hash(ix + 1, iy, seed)
    c, d = _lattice_hash(ix, iy + 1, seed), _lattice_hash(ix + 1, iy + 1, seed)
    return (a + tx * (b - a)) + ty * ((c + tx * (d - c)) - (a + tx * (b - a)))


def material_coordinates(state: Any, scene: Any) -> tuple[np.ndarray, np.ndarray]:
    """Return Gaussian-weighted inverse-displacement pixel-center coordinates.

    This is a smooth material approximation during deformation, not a claim of
    a globally invertible geometry map. It is rigid-translation invariant.
    """
    positions = state.positions
    if (not isinstance(positions, np.ndarray) or positions.dtype != np.float64
            or positions.shape != scene.home_xy.shape or not np.isfinite(positions).all()):
        raise ValueError('color requires finite float64 control positions')
    step = 2.0 / scene.height
    xs = -(scene.width / scene.height) + step * (np.arange(scene.width) + .5)
    ys = 1.0 - step * (np.arange(scene.height) + .5)
    x, y = np.broadcast_arrays(xs[None, :], ys[:, None])
    density = np.zeros_like(x)
    offset_x = np.zeros_like(x)
    offset_y = np.zeros_like(x)
    for element, position, home in zip(scene.elements, positions, scene.home_xy, strict=True):
        denominator = 2.0 * element.sigma * element.sigma
        horizontal = np.exp(-np.square(xs - position[0]) / denominator)
        vertical = np.exp(-np.square(ys - position[1]) / denominator)
        influence = np.multiply(vertical[:, None], horizontal[None, :]) * element.weight
        density += influence
        offset_x += influence * (position[0] - home[0])
        offset_y += influence * (position[1] - home[1])
    # All visible Gaussian coverage has positive density. Zero underflow occurs
    # only in distant background; assigning zero displacement there is harmless.
    np.divide(offset_x, density, out=offset_x, where=density > 0)
    np.divide(offset_y, density, out=offset_y, where=density > 0)
    return x - offset_x, y - offset_y


class ChromaticState:
    """Presentation-only creator settings and a supersedable palette blend."""

    def __init__(self) -> None:
        self.enabled = False
        self.mode = 'auto'
        self.override = None
        self.palette_name = 'neutral'
        self.palette = Blend(PALETTES['neutral'])

    def set_palette(self, name: str, target: str, tick: int,
                    duration: int = DEFAULT_DURATION_TICKS) -> None:
        _timing(tick, duration)
        if type(name) is not str or (name != 'auto' and name not in PALETTES):
            raise ValueError('palette must be auto, neutral, circle, oval, cloud, or hill')
        selected = _target_palette(target) if name == 'auto' else name
        self.mode = 'auto' if name == 'auto' else 'override'
        self.override = None if name == 'auto' else name
        self.palette_name = selected
        self.palette.set(PALETTES[self.palette_name], tick, duration)

    def on_morph(self, target: str, tick: int, duration: int) -> None:
        _timing(tick, duration)
        name = _target_palette(target)
        if self.mode == 'auto':
            self.palette_name = name
            self.palette.set(PALETTES[name], tick, duration)

    def on_reset(self, target: str, tick: int, duration: int) -> None:
        self.on_morph(target, tick, duration)

    def mapping(self) -> dict:
        return {'algorithm': ALGORITHM, 'enabled': self.enabled, 'mode': self.mode,
            'override': self.override, 'palette': {'name': self.palette_name,
                'start': self.palette.start.tolist(), 'end': self.palette.end.tolist(),
                'tick': self.palette.tick, 'duration_ticks': self.palette.duration}}

    @classmethod
    def from_mapping(cls, mapping: dict) -> ChromaticState:
        expected = {'algorithm', 'enabled', 'mode', 'override', 'palette'}
        if (type(mapping) is not dict or set(mapping) != expected
                or mapping['algorithm'] != ALGORITHM or type(mapping['enabled']) is not bool
                or mapping['mode'] not in ('auto', 'override')):
            raise ValueError('invalid chromatic state')
        override = mapping['override']
        if ((mapping['mode'] == 'auto' and override is not None)
                or (mapping['mode'] == 'override' and (type(override) is not str or override not in PALETTES))):
            raise ValueError('invalid palette override')
        palette = mapping['palette']
        if (type(palette) is not dict or set(palette) != {'name', 'start', 'end', 'tick', 'duration_ticks'}
                or type(palette['name']) is not str or palette['name'] not in PALETTES
                or (override is not None and palette['name'] != override)):
            raise ValueError('invalid palette metadata')
        _timing(palette['tick'], palette['duration_ticks'])
        start, end = _rgb_anchors(palette['start']), _rgb_anchors(palette['end'])
        if not np.array_equal(end, PALETTES[palette['name']]):
            raise ValueError('palette endpoint differs from named algorithm palette')
        result = cls()
        result.enabled, result.mode, result.override = mapping['enabled'], mapping['mode'], override
        result.palette_name = palette['name']
        result.palette.start, result.palette.end = start, end
        result.palette.tick, result.palette.duration = palette['tick'], palette['duration_ticks']
        return result

    def rgb(self, coverage: np.ndarray, state: Any, scene: Any, seed: int, tick: int) -> np.ndarray:
        """Color a grayscale raster without changing its foreground coverage."""
        if (not isinstance(coverage, np.ndarray) or coverage.dtype != np.uint8
                or coverage.shape != (scene.height, scene.width)):
            raise ValueError('color coverage must match the configured uint8 raster')
        if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
            raise ValueError('color seed must be a uint32')
        if type(tick) is not int or tick < 0:
            raise ValueError('color tick must be a nonnegative integer')
        if not self.enabled:
            return np.repeat(coverage[:, :, None], 3, axis=2)
        x, y = material_coordinates(state, scene)
        shade = np.clip(.5 + .35 * y + .18 * (_noise(x, y, seed, 9.) - .5)
            + .10 * (_noise(x, y, seed ^ 0xA511E9B3, 43.) - .5), 0., 1.)
        anchors = self.palette.at(tick)
        lower = anchors[0] + np.minimum(2 * shade, 1)[..., None] * (anchors[1] - anchors[0])
        upper = anchors[1] + np.maximum(2 * shade - 1, 0)[..., None] * (anchors[2] - anchors[1])
        foreground = np.where((shade <= .5)[..., None], lower, upper)
        alpha = (255 - coverage if scene.invert else coverage).astype(np.float64) / 255.
        background = 255. if scene.invert else 0.
        pixels = background + alpha[..., None] * (foreground - background)
        return np.floor(pixels + .5).astype(np.uint8)


def encode_rgb_png(pixels: np.ndarray) -> bytes:
    """Encode only mode-RGB pixels using the legacy PNG compression settings."""
    if not isinstance(pixels, np.ndarray) or pixels.dtype != np.uint8 or pixels.ndim != 3 or pixels.shape[2] != 3:
        raise ValueError('RGB pixels must be a three-channel uint8 raster')
    output = io.BytesIO()
    Image.fromarray(pixels).save(output, format='PNG', compress_level=6, optimize=False)
    return output.getvalue()
