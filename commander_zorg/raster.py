"""Coverage rasterization, geometric image measurements, and grayscale PNGs."""

from __future__ import annotations

import io
import math
from typing import Any

import numpy as np
from PIL import Image


def rasterize(samples: np.ndarray, scene: Any) -> np.ndarray:
    """Threshold samples, average coverage, round halves up, then invert."""
    height, width, count = scene.height, scene.width, scene.samples_per_axis
    if (
        not isinstance(samples, np.ndarray)
        or samples.dtype != np.float64
        or samples.shape != (height * count, width * count)
    ):
        raise ValueError("field must have the configured float64 sample shape")
    if not np.isfinite(samples).all():
        raise ValueError("cannot rasterize nonfinite field samples")
    occupied = samples.reshape(height, count, width, count) >= 0.0
    covered = np.count_nonzero(occupied, axis=(1, 3))
    coverage = covered / (count * count)
    pixels = np.floor(255.0 * coverage + 0.5).astype(np.uint8)
    if scene.invert:
        pixels = np.subtract(np.uint8(255), pixels)
    return pixels


def _gray_pixels(pixels: np.ndarray, scene: Any | None = None) -> None:
    if not isinstance(pixels, np.ndarray) or pixels.dtype != np.uint8 or pixels.ndim != 2:
        raise ValueError("pixels must be a two-dimensional uint8 array")
    if scene is not None and pixels.shape != (scene.height, scene.width):
        raise ValueError("pixels differ from the configured image dimensions")


def _noninverted(pixels: np.ndarray, scene: Any) -> np.ndarray:
    _gray_pixels(pixels, scene)
    return np.subtract(np.uint8(255), pixels) if scene.invert else pixels


def geometry_mask(pixels: np.ndarray, scene: Any) -> np.ndarray:
    """Return independent noninverted foreground coverage >= 128."""
    return _noninverted(pixels, scene) >= np.uint8(128)


def _mask_pair(a: np.ndarray, b: np.ndarray) -> None:
    if (
        not isinstance(a, np.ndarray)
        or not isinstance(b, np.ndarray)
        or a.dtype != np.bool_
        or b.dtype != np.bool_
        or a.ndim != 2
        or a.shape != b.shape
    ):
        raise ValueError("masks must be equally shaped two-dimensional bool arrays")


def iou(a: np.ndarray, b: np.ndarray) -> float | None:
    """Intersection over union; two empty masks have undefined similarity."""
    _mask_pair(a, b)
    union = int(np.count_nonzero(a | b))
    if union == 0:
        return None
    return int(np.count_nonzero(a & b)) / union


def _raster_centroid(mask: np.ndarray) -> tuple[float, float] | None:
    rows, columns = np.nonzero(mask)
    if rows.size == 0:
        return None
    return float(columns.mean()), float(rows.mean())


def aligned_iou(candidate: np.ndarray, baseline: np.ndarray) -> float | None:
    """Align candidate to baseline by integer centroid translation without wrap.

    Each shift uses floor(value + 0.5), including for negative half-integers.
    Empty operands cannot establish morphological similarity and return None.
    """
    _mask_pair(candidate, baseline)
    source_center = _raster_centroid(candidate)
    target_center = _raster_centroid(baseline)
    if source_center is None or target_center is None:
        return None
    dx = math.floor(target_center[0] - source_center[0] + 0.5)
    dy = math.floor(target_center[1] - source_center[1] + 0.5)
    height, width = candidate.shape
    translated = np.zeros_like(candidate)
    source_x0, source_x1 = max(0, -dx), min(width, width - dx)
    source_y0, source_y1 = max(0, -dy), min(height, height - dy)
    if source_x0 < source_x1 and source_y0 < source_y1:
        translated[
            source_y0 + dy : source_y1 + dy,
            source_x0 + dx : source_x1 + dx,
        ] = candidate[source_y0:source_y1, source_x0:source_x1]
    return iou(translated, baseline)


def measure_mask(
    pixels: np.ndarray, scene: Any, baseline: np.ndarray | None = None
) -> dict[str, Any]:
    """Measure noninverted geometry in world and inclusive raster coordinates.

    Clipping includes every nonzero antialiasing pixel in the outer two rows
    or columns; geometry and occupancy use the >=128 binary mask instead.
    The optional baseline is a noninverted boolean mask, not grayscale pixels.
    """
    noninverted = _noninverted(pixels, scene)
    mask = noninverted >= np.uint8(128)
    if baseline is not None:
        _mask_pair(mask, baseline)
    rows, columns = np.nonzero(mask)
    centroid = None
    bbox = None
    if rows.size:
        step = 2.0 / scene.height
        centroid = [
            -(scene.width / scene.height) + step * (float(columns.mean()) + 0.5),
            1.0 - step * (float(rows.mean()) + 0.5),
        ]
        bbox = [int(columns.min()), int(rows.min()), int(columns.max()), int(rows.max())]
    clipping = bool(
        np.any(noninverted[:2, :])
        or np.any(noninverted[-2:, :])
        or np.any(noninverted[:, :2])
        or np.any(noninverted[:, -2:])
    )
    baseline_iou = None
    morphology_iou = None
    centroid_distance = None
    if baseline is not None:
        baseline_iou = iou(mask, baseline)
        morphology_iou = aligned_iou(mask, baseline)
        center = _raster_centroid(mask)
        baseline_center = _raster_centroid(baseline)
        if center is not None and baseline_center is not None:
            centroid_distance = (2.0 / scene.height) * math.hypot(
                center[0] - baseline_center[0], center[1] - baseline_center[1]
            )
    return {
        "occupancy": int(rows.size) / mask.size,
        "centroid": centroid,
        "bbox": bbox,
        "clipping": clipping,
        "empty": bool(rows.size == 0),
        "iou": baseline_iou,
        "aligned_iou": morphology_iou,
        "centroid_distance": centroid_distance,
    }


def encode_gray_png(pixels: np.ndarray) -> bytes:
    """Encode only mode-L pixels, with fixed compression and no metadata."""
    _gray_pixels(pixels)
    output = io.BytesIO()
    Image.fromarray(pixels).save(output, format="PNG", compress_level=6, optimize=False)
    return output.getvalue()
