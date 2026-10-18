"""Presentation determinism, material stability and untouched grayscale output."""
from copy import deepcopy
from dataclasses import replace
import io
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

from commander_zorg.canonical import canonical_bytes, read_json, sha256
from commander_zorg.chromatic import ALGORITHM, ChromaticState, PALETTES, encode_rgb_png, material_coordinates
from commander_zorg.live_motion import LiveRuntime
from commander_zorg.morph_export import pixels_for
from commander_zorg.raster import encode_gray_png, geometry_mask
from commander_zorg.state import owned_state, state_mapping

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def runtime():
    return LiveRuntime(read_json(ROOT / 'scenes/live_lab.json'))


def enabled(target='cloud', tick=120):
    color = ChromaticState()
    color.enabled = True
    color.on_morph(target, 0, 120)
    return color


def test_repeated_seeded_frames_and_pngs_are_identical(runtime):
    gray = pixels_for(runtime.state, runtime.scene)
    color = enabled()
    a = color.rgb(gray, runtime.state, runtime.scene, 1, 120)
    b = color.rgb(gray, runtime.state, runtime.scene, 1, 120)
    assert np.array_equal(a, b)
    assert encode_rgb_png(a) == encode_rgb_png(b)
    assert np.unique(a[gray == 255], axis=0).shape[0] > 10


def test_seed_changes_only_coherent_color(runtime):
    gray = pixels_for(runtime.state, runtime.scene)
    color = enabled()
    a = color.rgb(gray, runtime.state, runtime.scene, 1, 120)
    b = color.rgb(gray, runtime.state, runtime.scene, 2**32 - 1, 120)
    assert not np.array_equal(a, b)
    assert np.max(np.abs(a.astype(int) - b.astype(int))) < 45
    assert np.array_equal(a[gray == 0], b[gray == 0])


def test_color_has_no_wall_clock_or_tick_noise_after_transition(runtime, monkeypatch):
    import time
    monkeypatch.setattr(time, 'time', lambda: (_ for _ in ()).throw(AssertionError('wall clock')))
    monkeypatch.setattr(time, 'monotonic', lambda: (_ for _ in ()).throw(AssertionError('wall clock')))
    gray = pixels_for(runtime.state, runtime.scene)
    color = enabled()
    assert np.array_equal(color.rgb(gray, runtime.state, runtime.scene, 1, 120),
        color.rgb(gray, runtime.state, runtime.scene, 1, 99999))


@pytest.mark.parametrize('start,end', [('home','cloud'), ('oval','cloud'), ('cloud','circle'), ('cloud','home')])
def test_palette_transition_endpoints_and_replay(start, end):
    a, b = enabled(start), enabled(start)
    for color in (a, b):
        color.on_morph(end, 120, 120)
    expected = PALETTES['neutral' if end == 'home' else end]
    assert np.array_equal(a.palette.at(120), PALETTES['neutral' if start == 'home' else start])
    assert np.array_equal(a.palette.at(240), expected)
    assert a.mapping() == b.mapping()
    midpoint = a.palette.at(180)
    assert np.array_equal(midpoint, b.palette.at(180))
    assert np.all(midpoint >= np.minimum(a.palette.start, a.palette.end))
    assert np.all(midpoint <= np.maximum(a.palette.start, a.palette.end))


def test_interruption_starts_from_actual_visible_palette(runtime):
    color = enabled('oval')
    color.on_morph('cloud', 120, 120)
    gray = pixels_for(runtime.state, runtime.scene)
    before = color.rgb(gray, runtime.state, runtime.scene, 1, 170)
    palette = color.palette.at(170).copy()
    color.on_morph('circle', 170, 60)
    assert np.array_equal(color.palette.start, palette)
    assert np.array_equal(before, color.rgb(gray, runtime.state, runtime.scene, 1, 170))
    assert np.array_equal(color.palette.at(230), PALETTES['circle'])


def test_cloud_endpoint_is_coherent_sky_blue(runtime):
    gray = pixels_for(runtime.state, runtime.scene)
    rgb = enabled().rgb(gray, runtime.state, runtime.scene, 172026, 120)
    inside = rgb[gray == 255].astype(int)
    assert np.all(inside[:, 2] > inside[:, 0] + 40)
    assert np.all(inside[:, 1] > inside[:, 0] + 20)
    assert 100 < inside[:, 0].mean() < 180
    assert 170 < inside[:, 1].mean() < 230
    assert inside[:, 2].mean() > 220


def test_material_coordinates_and_texture_follow_rigid_translation():
    home = np.array([[-.125, 0.], [.125, 0.]], dtype=np.float64)
    elements = [SimpleNamespace(sigma=.25, weight=1.), SimpleNamespace(sigma=.25, weight=1.)]
    scene = SimpleNamespace(width=64, height=64, home_xy=home, elements=elements, invert=False)
    state = owned_state(0, home, np.zeros_like(home))
    shift = 4
    translated = owned_state(0, home + [.125, 0.], np.zeros_like(home))
    ax, ay = material_coordinates(state, scene)
    bx, by = material_coordinates(translated, scene)
    np.testing.assert_allclose(ax[:, :-shift], bx[:, shift:], rtol=0, atol=3e-16)
    np.testing.assert_allclose(ay[:, :-shift], by[:, shift:], rtol=0, atol=3e-16)
    gray = np.full((64, 64), 255, dtype=np.uint8)
    color = enabled()
    a, b = color.rgb(gray, state, scene, 20, 120), color.rgb(gray, translated, scene, 20, 120)
    assert np.array_equal(a[:, :-shift], b[:, shift:])


def test_subpixel_translation_changes_texture_continuously(runtime):
    scene = replace(runtime.scene, width=64, height=64)
    state = runtime.state
    shifted = owned_state(0, state.positions + [1e-7, 0.], state.velocities)
    gray = np.full((64, 64), 255, dtype=np.uint8)
    color = enabled()
    a, b = color.rgb(gray, state, scene, 20, 120), color.rgb(gray, shifted, scene, 20, 120)
    assert np.max(np.abs(a.astype(int) - b.astype(int))) <= 1


@pytest.mark.parametrize('invert', [False, True])
def test_antialias_alpha_and_inversion_are_preserved(runtime, invert):
    scene = replace(runtime.scene, base=replace(runtime.scene.base, invert=invert))
    gray = pixels_for(runtime.state, scene)
    color = enabled()
    alpha = 255 - gray if invert else gray
    solid = np.full_like(gray, 0 if invert else 255)
    foreground = color.rgb(solid, runtime.state, scene, 1, 120).astype(float)
    rgb = color.rgb(gray, runtime.state, scene, 1, 120)
    background = 255. if invert else 0.
    expected = np.floor(background + alpha[..., None] / 255. * (foreground - background) + .5).astype(np.uint8)
    # The solid foreground is already rounded, so compositing can differ by one
    # output unit from a single final rounding of the original floating color.
    assert np.max(np.abs(rgb.astype(int) - expected.astype(int))) <= 1
    assert np.all(rgb[alpha == 0] == background)
    assert np.array_equal(gray, pixels_for(runtime.state, scene))
    assert np.array_equal(geometry_mask(gray, scene), alpha >= 128)


def test_color_never_changes_numerical_or_grayscale_state(runtime):
    scene, state = runtime.scene, runtime.state
    gray = pixels_for(state, scene)
    png = encode_gray_png(gray)
    before = canonical_bytes(state_mapping(state))
    color = enabled()
    color.rgb(gray, state, scene, 172026, 120)
    assert before == canonical_bytes(state_mapping(state))
    assert png == encode_gray_png(pixels_for(state, scene))
    assert sha256(gray.tobytes()) == sha256(pixels_for(state, scene).tobytes())
    # Baseline initial live_lab pixels and mode-L PNG, measured before color
    # source was introduced under pinned NumPy/Pillow dependencies.
    assert sha256(gray.tobytes()) == '611a22c167ca6f32a957d6a2c4ef22bcbb106d4cc2a33e0d9cf171f149e4d3a1'
    # Decoded grayscale is cross-platform stable; PNG container compression is
    # platform-specific under the pinned Pillow build. Both known baseline
    # encoders remain byte-pinned on their own platform rather than weakening
    # same-environment PNG reproducibility or altering legacy export bytes.
    assert np.array_equal(np.asarray(Image.open(io.BytesIO(png))), gray)
    expected = ('8bc10abdd0a88f90673464dbba892f6ab5abf0c48859f9232a14820a5eb69a0c'
                if sys.platform == 'darwin'
                else '1a2ab19277d7028eed12995dab423423137e2d557a813ac5a8b2001305af3181')
    assert sha256(png) == expected


def test_disabled_returns_identical_gray_channels(runtime):
    gray = pixels_for(runtime.state, runtime.scene)
    rgb = ChromaticState().rgb(gray, runtime.state, runtime.scene, 1, 0)
    assert all(np.array_equal(rgb[:, :, channel], gray) for channel in range(3))
    assert Image.open(io.BytesIO(encode_rgb_png(rgb))).mode == 'RGB'


def test_override_survives_morph_and_auto_resumes():
    color = enabled('oval')
    color.set_palette('circle', 'oval', 120, 60)
    mapping = color.mapping()
    color.on_morph('cloud', 180, 120)
    assert color.mapping() == mapping
    color.set_palette('auto', 'cloud', 180, 120)
    assert color.mode == 'auto' and color.override is None
    assert np.array_equal(color.palette.at(300), PALETTES['cloud'])
    color.on_reset('home', 300, 120)
    assert np.array_equal(color.palette.at(420), PALETTES['neutral'])
    color.on_morph('custom_shape', 420, 120)
    assert color.palette_name == 'neutral'


def test_mapping_round_trip_preserves_interruption(runtime):
    color = enabled('oval')
    color.on_morph('cloud', 120, 120)
    color.on_morph('circle', 175, 60)
    restored = ChromaticState.from_mapping(color.mapping())
    assert restored.mapping() == color.mapping()
    gray = pixels_for(runtime.state, runtime.scene)
    assert np.array_equal(restored.rgb(gray, runtime.state, runtime.scene, 1, 190),
        color.rgb(gray, runtime.state, runtime.scene, 1, 190))


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(algorithm='unknown'), lambda d: d.update(extra=1),
    lambda d: d.update(enabled=1), lambda d: d.update(mode='custom'),
    lambda d: d.update(override='cloud'), lambda d: d.update(palette=[]),
    lambda d: d['palette'].update(name='unknown'),
    lambda d: d['palette'].update(tick=True), lambda d: d['palette'].update(duration_ticks=0),
    lambda d: d['palette'].update(duration_ticks=601), lambda d: d['palette'].update(start=[]),
    lambda d: d['palette']['start'][0].__setitem__(0, float('nan')),
    lambda d: d['palette']['start'][0].__setitem__(0, -1),
    lambda d: d['palette']['start'][0].__setitem__(0, True),
    lambda d: d['palette']['start'][0].__setitem__(0, 10**1000),
    lambda d: d['palette']['start'][0].__setitem__(0, float('inf')),
    lambda d: d.update(mode=[]), lambda d: d.update(algorithm={}),
    lambda d: d['palette'].update(name=[]), lambda d: d['palette'].update(start=[[0,0,0]]),
    lambda d: d['palette']['end'][0].__setitem__(0, 200),
])
def test_corrupt_palette_data_rejected(mutation):
    mapping = enabled().mapping()
    mutation(mapping)
    with pytest.raises(ValueError):
        ChromaticState.from_mapping(mapping)


@pytest.mark.parametrize('mapping', [None, [], '', True, 1])
def test_invalid_color_mapping_containers_rejected(mapping):
    with pytest.raises(ValueError): ChromaticState.from_mapping(mapping)


@pytest.mark.parametrize('seed', [-1, 2**32, True, 1., float('nan')])
def test_invalid_color_seeds_rejected(runtime, seed):
    gray = pixels_for(runtime.state, runtime.scene)
    with pytest.raises(ValueError):
        enabled().rgb(gray, runtime.state, runtime.scene, seed, 120)


@pytest.mark.parametrize('name', ['custom', 'home', '', None, []])
def test_invalid_palette_command_is_transactional(name):
    color = enabled()
    before = deepcopy(color.mapping())
    with pytest.raises(ValueError): color.set_palette(name, 'cloud', 120)
    assert before == color.mapping()


@pytest.mark.parametrize('pixels', [np.zeros((2, 2), dtype=np.uint8), np.zeros((2, 2, 4), dtype=np.uint8), np.zeros((2, 2, 3))])
def test_invalid_rgb_encoder_input_rejected(pixels):
    with pytest.raises(ValueError): encode_rgb_png(pixels)
