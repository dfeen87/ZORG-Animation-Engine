"""Independent V03 numerical geometry and V04 coordinate fixtures."""

import math
from types import SimpleNamespace

import numpy as np
import pytest

from commander_zorg.field import evaluate_samples, sample_axes


def scene(*, width=9, height=9, samples=1, elements=None, threshold=0.72):
    if elements is None:
        elements = (SimpleNamespace(id="a", sigma=0.3, weight=1.0),)
    return SimpleNamespace(
        width=width,
        height=height,
        samples_per_axis=samples,
        elements=elements,
        threshold=threshold,
    )


def state(positions):
    return SimpleNamespace(positions=np.array(positions, dtype=np.float64))


def test_sample_axes_use_world_aspect_positive_y_and_quarter_offsets():
    xs, ys = sample_axes(scene(width=3, height=2, samples=2))
    np.testing.assert_array_equal(xs, [-1.25, -0.75, -0.25, 0.25, 0.75, 1.25])
    np.testing.assert_array_equal(ys, [0.75, 0.25, -0.25, -0.75])
    assert xs.dtype == ys.dtype == np.float64


def test_single_gaussian_center_off_center_radius_sign_and_symmetry():
    sigma = 0.3
    # Sample column 6 is radius 4/9 world units from center column 4.
    radius = 4 / 9
    weight = 0.72 * math.exp(radius * radius / (2 * sigma * sigma))
    config = scene(elements=(SimpleNamespace(id="a", sigma=sigma, weight=weight),))
    result = evaluate_samples(state([[0, 0]]), config)
    assert result[4, 4] == pytest.approx(weight - 0.72, abs=1e-15)
    assert result[4, 6] == pytest.approx(0.0, abs=1e-14)
    assert result[4, 5] > 0
    assert result[4, 7] < 0
    expected_off_center = weight * math.exp(-((2 / 9) ** 2 + (4 / 9) ** 2) / (2 * sigma**2)) - 0.72
    assert result[2, 5] == pytest.approx(expected_off_center, abs=1e-14)
    np.testing.assert_allclose(result, result[::-1, :], atol=1e-14, rtol=0)
    np.testing.assert_allclose(result, result[:, ::-1], atol=1e-14, rtol=0)


def test_separable_policy_agrees_with_independent_scalar_direct_equation():
    elements = (
        SimpleNamespace(id="asymmetric-a", sigma=0.12, weight=0.8),
        SimpleNamespace(id="asymmetric-b", sigma=0.37, weight=1.1),
        SimpleNamespace(id="asymmetric-c", sigma=0.21, weight=0.4),
    )
    config = scene(width=11, height=7, samples=2, elements=elements)
    positions = [[-0.62, 0.51], [0.21, -0.15], [0.88, 0.63]]
    numerical_state = state(positions)
    before = numerical_state.positions.copy()
    result = evaluate_samples(numerical_state, config)
    # Coordinates and direct exponentials are constructed independently, with
    # two-dimensional squared radius rather than the production separable path.
    expected = np.empty((14, 22), dtype=np.float64)
    for row in range(14):
        for column in range(22):
            x = -11 / 7 + (column / 2 + 0.25) * 2 / 7
            y = 1 - (row / 2 + 0.25) * 2 / 7
            value = 0.0
            for element, (px, py) in zip(elements, positions):
                value += element.weight * math.exp(-((x - px) ** 2 + (y - py) ** 2) / (2 * element.sigma**2))
            expected[row, column] = value - 0.72
    np.testing.assert_allclose(result, expected, rtol=0, atol=1e-12)
    np.testing.assert_array_equal(numerical_state.positions, before)
    assert not np.shares_memory(result, numerical_state.positions)
    assert np.isfinite(result).all()


def test_translation_moves_density_by_one_pixel_without_normalization():
    config = scene(width=10, height=10)
    baseline = evaluate_samples(state([[0, 0]]), config)
    translated = evaluate_samples(state([[0.2, 0]]), config)
    np.testing.assert_allclose(translated[:, 1:], baseline[:, :-1], rtol=0, atol=1e-14)


@pytest.mark.parametrize("positions", [[[float("nan"), 0]], [[0, float("inf")]]])
def test_nonfinite_positions_are_rejected(positions):
    with pytest.raises(ValueError, match="nonfinite"):
        evaluate_samples(state(positions), scene())


def test_nonfinite_computed_field_is_rejected():
    config = scene(elements=(SimpleNamespace(id="a", sigma=0.3, weight=float("inf")),))
    with pytest.raises(ValueError, match="field contains nonfinite"):
        evaluate_samples(state([[0, 0]]), config)


def test_wrong_state_dtype_shape_and_element_mapping_are_rejected():
    with pytest.raises(ValueError, match="float64"):
        evaluate_samples(SimpleNamespace(positions=np.zeros((1, 2), dtype=np.float32)), scene())
    with pytest.raises(ValueError, match="float64"):
        evaluate_samples(state([[0, 0], [0, 0]]), scene())
    numerical_state = state([[0, 0]])
    numerical_state.element_ids = ("wrong",)
    with pytest.raises(ValueError, match="IDs differ"):
        evaluate_samples(numerical_state, scene())


def test_nonascending_element_ids_are_rejected_instead_of_reordered():
    elements = (
        SimpleNamespace(id="b", sigma=0.3, weight=1),
        SimpleNamespace(id="a", sigma=0.3, weight=1),
    )
    with pytest.raises(ValueError, match="ascending IDs"):
        evaluate_samples(state([[0, 0], [0, 0]]), scene(elements=elements))
