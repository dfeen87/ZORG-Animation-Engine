"""V04 raster, V09 image failure, and PNG representation proofs."""

import io
import math
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from commander_zorg.field import evaluate_samples
from commander_zorg.raster import aligned_iou, encode_gray_png, geometry_mask, iou, measure_mask, rasterize


def scene(width=5, height=3, samples=2, invert=False):
    return SimpleNamespace(width=width, height=height, samples_per_axis=samples, invert=invert)


def test_asymmetric_coverage_threshold_equality_quantization_and_inversion():
    counts = np.array([[0, 1, 2, 3, 4], [4, 0, 3, 1, 2], [1, 4, 0, 2, 3]])
    samples = np.full((6, 10), -1.0, dtype=np.float64)
    for row in range(3):
        for column in range(5):
            for index in range(counts[row, column]):
                samples[2 * row + index // 2, 2 * column + index % 2] = 0.0
    original = samples.copy()
    expected = np.array([[0, 64, 128, 191, 255], [255, 0, 191, 64, 128], [64, 255, 0, 128, 191]], dtype=np.uint8)
    normal = rasterize(samples, scene())
    inverted = rasterize(samples, scene(invert=True))
    np.testing.assert_array_equal(normal, expected)
    np.testing.assert_array_equal(inverted, 255 - expected)
    np.testing.assert_array_equal(geometry_mask(normal, scene()), expected >= 128)
    np.testing.assert_array_equal(geometry_mask(inverted, scene(invert=True)), expected >= 128)
    np.testing.assert_array_equal(samples, original)
    assert not np.shares_memory(normal, samples)


def test_offcenter_field_produces_top_left_geometry_with_independent_oracle():
    config = scene(width=12, height=8)
    config.elements = (SimpleNamespace(id="a", sigma=0.18, weight=1.0),)
    config.threshold = 0.72
    numerical_state = SimpleNamespace(positions=np.array([[-0.75, 0.5]], dtype=np.float64))
    pixels = rasterize(evaluate_samples(numerical_state, config), config)
    expected = np.zeros((8, 12), dtype=np.uint8)
    for row in range(8):
        for column in range(12):
            occupied = 0
            for sy in (0.25, 0.75):
                for sx in (0.25, 0.75):
                    x, y = -1.5 + (column + sx) / 4, 1 - (row + sy) / 4
                    field = math.exp(-((x + 0.75) ** 2 + (y - 0.5) ** 2) / (2 * 0.18**2)) - 0.72
                    occupied += field >= 0
            expected[row, column] = math.floor(255 * occupied / 4 + 0.5)
    np.testing.assert_array_equal(pixels, expected)
    assert pixels[:4, :6].sum() > 0
    assert pixels[4:, :].sum() == 0
    assert pixels[:, 6:].sum() == 0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_field_is_rejected_before_rasterization(bad):
    samples = np.zeros((6, 10), dtype=np.float64)
    samples[2, 3] = bad
    with pytest.raises(ValueError, match="nonfinite"):
        rasterize(samples, scene())


def test_wrong_field_shape_or_dtype_is_rejected():
    with pytest.raises(ValueError, match="float64"):
        rasterize(np.zeros((3, 5), dtype=np.float64), scene())
    with pytest.raises(ValueError, match="float64"):
        rasterize(np.zeros((6, 10), dtype=np.float32), scene())


def test_metrics_world_centroid_inclusive_bbox_and_subpixel_clip_band():
    config = scene(width=12, height=10)
    pixels = np.zeros((10, 12), dtype=np.uint8)
    pixels[3:6, 3:7] = 255
    metrics = measure_mask(pixels, config)
    assert metrics["occupancy"] == 12 / 120
    assert metrics["centroid"] == pytest.approx([-0.2, 0.1])
    assert metrics["bbox"] == [3, 3, 6, 5]
    assert not metrics["clipping"]
    assert not metrics["empty"]
    assert metrics["iou"] is None
    pixels[1, 8] = 64  # Visible AA coverage clips despite being below mask threshold.
    clipped = measure_mask(pixels, config)
    assert clipped["clipping"]
    assert clipped["occupancy"] == metrics["occupancy"]
    inverted = measure_mask(255 - pixels, scene(width=12, height=10, invert=True))
    assert clipped == inverted


def test_empty_full_and_vertical_flip_diagnostics_cannot_establish_success():
    config = scene(width=12, height=10)
    empty = np.zeros((10, 12), dtype=np.uint8)
    empty_mask = empty.astype(bool)
    metrics = measure_mask(empty, config, empty_mask)
    assert metrics["empty"] and metrics["occupancy"] == 0
    assert metrics["centroid"] is metrics["bbox"] is None
    assert metrics["iou"] is metrics["aligned_iou"] is metrics["centroid_distance"] is None
    full = measure_mask(np.full((10, 12), 255, dtype=np.uint8), config)
    assert full["occupancy"] == 1 and full["clipping"]
    asymmetric = empty.copy()
    asymmetric[2:4, 3:6] = 255
    flipped = measure_mask(asymmetric[::-1].copy(), config, asymmetric >= 128)
    assert flipped["iou"] == 0
    assert flipped["centroid_distance"] > 0.01


def test_translation_aligned_iou_excludes_pure_translation_as_morphology():
    baseline = np.zeros((14, 16), dtype=bool)
    baseline[4:7, 4:8] = True
    baseline[7, 4] = True
    candidate = np.zeros_like(baseline)
    candidate[7:10, 6:10] = True
    candidate[10, 6] = True
    assert iou(candidate, baseline) < 0.5
    assert aligned_iou(candidate, baseline) == 1.0
    metrics = measure_mask(candidate.astype(np.uint8) * 255, scene(width=16, height=14), baseline)
    assert metrics["centroid_distance"] == pytest.approx(math.hypot(2, 3) * 2 / 14)
    assert metrics["aligned_iou"] == 1.0


def test_centroid_half_shift_rounds_towards_positive_infinity_and_zero_fills():
    candidate = np.zeros((6, 6), dtype=bool)
    candidate[2, 1:3] = True  # center col 1.5
    baseline = np.zeros_like(candidate)
    baseline[2, 1] = True  # shift -0.5 rounds to zero, not -1.
    assert aligned_iou(candidate, baseline) == 0.5
    # A deliberately asymmetric border fixture reveals accidental np.roll.
    candidate[:] = False
    baseline[:] = False
    candidate[2, [0, 1, 5]] = True
    baseline[2, 0] = True
    assert aligned_iou(candidate, baseline) == 0.0


def test_mask_validation_and_no_aliasing():
    pixels = np.zeros((3, 5), dtype=np.uint8)
    mask = geometry_mask(pixels, scene())
    mask[0, 0] = True
    assert pixels[0, 0] == 0
    with pytest.raises(ValueError, match="bool arrays"):
        iou(mask, pixels)
    with pytest.raises(ValueError, match="bool arrays"):
        aligned_iou(mask, np.zeros((2, 2), dtype=bool))


def test_png_mode_dimensions_decoded_pixels_and_deterministic_container():
    pixels = np.array([[0, 64, 128], [191, 255, 0]], dtype=np.uint8)
    encoded = encode_gray_png(pixels)
    assert encoded == encode_gray_png(pixels.copy())
    with Image.open(io.BytesIO(encoded)) as image:
        assert image.mode == "L"
        assert image.size == (3, 2)
        assert image.info == {}
        np.testing.assert_array_equal(np.asarray(image), pixels)
    # Inspect chunk framing independently: encoder contributes only required
    # grayscale image chunks, without timestamps, profiles or text metadata.
    chunk_types = []
    offset = 8
    while offset < len(encoded):
        length = int.from_bytes(encoded[offset : offset + 4], "big")
        chunk_types.append(encoded[offset + 4 : offset + 8])
        offset += length + 12
    assert chunk_types == [b"IHDR", b"IDAT", b"IEND"]
    with pytest.raises(ValueError, match="uint8"):
        encode_gray_png(pixels.astype(np.float64))
