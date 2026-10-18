"""Positive Gaussian fields with a fixed float64 operation order.

The numerical policy is ``separable-yx-weight-sum-v1``: for each control in
ascending element-ID order, multiply its vertical and horizontal exponential
vectors, multiply that outer product by its weight, then add it to the field.
Subtract the threshold once, after all controls. No tails are truncated.
"""

from __future__ import annotations

from typing import Any

import numpy as np


NUMERICAL_POLICY = "separable-yx-weight-sum-v1"


def sample_axes(scene: Any) -> tuple[np.ndarray, np.ndarray]:
    """Return horizontal samples left-to-right and vertical samples top-to-bottom.

    At two samples per axis, each pixel is sampled at its quarter and
    three-quarter positions. World height is two units and world Y points up.
    """
    width, height, samples = scene.width, scene.height, scene.samples_per_axis
    if width <= 0 or height <= 0 or samples <= 0:
        raise ValueError("image dimensions and samples_per_axis must be positive")
    step = 2.0 / height
    xs = -(width / height) + step * (
        (np.arange(width * samples, dtype=np.float64) + 0.5) / samples
    )
    ys = 1.0 - step * (
        (np.arange(height * samples, dtype=np.float64) + 0.5) / samples
    )
    return xs, ys


def evaluate_samples(state: Any, scene: Any) -> np.ndarray:
    """Evaluate the signed thresholded positive-density field at raster samples.

    Numerical state is read only. A single dense scratch array is reused for
    all element contributions, rather than retaining an element/height/width
    tensor. Scene and state element order must be the same ascending ID order.
    """
    positions = state.positions
    elements = scene.elements
    if (
        not isinstance(positions, np.ndarray)
        or positions.dtype != np.float64
        or positions.shape != (len(elements), 2)
    ):
        raise ValueError("positions must be a float64 array of shape (elements, 2)")
    if not np.isfinite(positions).all():
        raise ValueError("positions contain nonfinite values")
    ids = tuple(element.id for element in elements)
    if ids != tuple(sorted(ids)) or len(set(ids)) != len(ids):
        raise ValueError("field elements must have unique ascending IDs")
    if hasattr(state, "element_ids") and tuple(state.element_ids) != ids:
        raise ValueError("state element IDs differ from scene element IDs")
    xs, ys = sample_axes(scene)
    field = np.zeros((ys.size, xs.size), dtype=np.float64)
    scratch = np.empty_like(field)
    # Explicit ufuncs freeze arithmetic grouping and retain float64 throughout.
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        for element, position in zip(elements, positions, strict=True):
            denominator = 2.0 * element.sigma * element.sigma
            horizontal = np.exp(-np.square(xs - position[0]) / denominator)
            vertical = np.exp(-np.square(ys - position[1]) / denominator)
            np.multiply(vertical[:, None], horizontal[None, :], out=scratch)
            np.multiply(scratch, element.weight, out=scratch)
            np.add(field, scratch, out=field)
        np.subtract(field, scene.threshold, out=field)
    if not np.isfinite(field).all():
        raise ValueError("Gaussian field contains nonfinite values")
    return field
