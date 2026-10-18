"""Creator colors retain actual raster geometry and bounded terminal output."""
from __future__ import annotations

from dataclasses import replace
import fcntl
import io
import json
import os
from pathlib import Path
import re
import select
import struct
import subprocess
import sys
import termios
import time

import numpy as np
import pytest

from commander_zorg.canonical import canonical_bytes, read_json
from scripts.pty_support import terminal_settings_equal
from commander_zorg.chromatic import ChromaticState
from commander_zorg.live_motion import LiveRuntime
from commander_zorg.morph_targets import load_targets
from commander_zorg.state import state_mapping
from commander_zorg.studio_runtime import StudioRuntime
from commander_zorg.terminal_view import (
    detect_color_mode, draw_frame, frame_lines, half_blocks, use_monochrome,
)


ROOT = Path(__file__).resolve().parents[1]
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


@pytest.fixture
def runtime():
    config = read_json(ROOT / "scenes/live_lab.json")
    result = StudioRuntime(config, load_targets(ROOT / "morph_targets", LiveRuntime(config).scene))
    # A presentation state can also be attached before the creator CLI adapter.
    if not hasattr(result, "chromatic"):
        result.chromatic = ChromaticState()
    result.chromatic.enabled = True
    result.chromatic.set_palette("cloud", "home", 0, 1)
    result.step()
    return result


@pytest.mark.parametrize("environment,expected", [
    ({}, "mono"),
    ({"TERM": "xterm-256color"}, "256"),
    ({"TERM": "xterm-256color", "COLORTERM": "truecolor"}, "truecolor"),
    ({"COLORTERM": "24bit"}, "truecolor"),
    ({"TERM": "xterm-direct"}, "truecolor"),
    ({"TERM": "dumb", "COLORTERM": "truecolor"}, "mono"),
    ({"TERM": "unknown", "COLORTERM": "truecolor"}, "mono"),
])
def test_creator_color_detection_preserves_legacy_detection(environment, expected):
    assert detect_color_mode(environment=environment) == expected
    assert detect_color_mode(True, environment=environment) == "mono"
    assert use_monochrome(environment={"TERM": "xterm-256color"})


def test_rgb_half_blocks_encode_both_rows_and_nearest_standard_256_colors():
    pixels = np.array([
        [[255, 0, 0], [128, 128, 128], [90, 100, 130]],
        [[0, 0, 255], [255, 255, 255], [0, 0, 0]],
    ], dtype=np.uint8)
    truecolor = half_blocks(pixels)[0]
    assert truecolor == (
        "\x1b[38;2;255;0;0m\x1b[48;2;0;0;255m▀"
        "\x1b[38;2;128;128;128m\x1b[48;2;255;255;255m▀"
        "\x1b[38;2;90;100;130m\x1b[48;2;0;0;0m▀\x1b[0m"
    )
    assert half_blocks(pixels, color_mode="256")[0] == (
        "\x1b[38;5;196m\x1b[48;5;21m▀"
        "\x1b[38;5;244m\x1b[48;5;231m▀"
        "\x1b[38;5;60m\x1b[48;5;16m▀\x1b[0m"
    )
    assert ANSI.sub("", truecolor) == "▀▀▀"
    with pytest.raises(ValueError):
        half_blocks(pixels[:, :, :2])
    with pytest.raises(ValueError):
        half_blocks(pixels, color_mode="16")


def test_legacy_grayscale_half_block_bytes_are_unchanged():
    pixels = np.array([[0, 100, 128, 255], [255, 128, 100, 0]], dtype=np.uint8)
    expected = "".join(
        f"\x1b[38;2;{int(a)};{int(a)};{int(a)}m"
        f"\x1b[48;2;{int(b)};{int(b)};{int(b)}m▀"
        for a, b in zip(pixels[0], pixels[1], strict=True)
    ) + "\x1b[0m"
    assert half_blocks(pixels) == [expected]
    assert half_blocks(pixels, mono=True) == ["▄▄▀▀"]


@pytest.mark.parametrize("color_mode,marker", [("truecolor", "38;2;"), ("256", "38;5;")])
def test_color_preview_respects_noninverted_scene_adapter_without_mutation(runtime, color_mode, marker):
    runtime.terminal_color_mode = color_mode
    size = os.terminal_size((80, 24))
    before = canonical_bytes({"state": state_mapping(runtime.state),
                              "events": runtime.events, "color": runtime.chromatic.mapping()})
    original = frame_lines(runtime, size)
    assert any(marker in line for line in original)
    assert "48;" in "".join(original)
    inverted = replace(runtime.scene, base=replace(runtime.scene.base, invert=True))
    runtime.scene = inverted
    assert frame_lines(runtime, size) == original
    assert runtime.scene is inverted and runtime.scene.invert
    assert canonical_bytes({"state": state_mapping(runtime.state),
                            "events": runtime.events, "color": runtime.chromatic.mapping()}) == before


@pytest.mark.parametrize("columns,rows", [(1, 1), (8, 3), (12, 6), (20, 8), (80, 24), (140, 40)])
@pytest.mark.parametrize("mode", ["truecolor", "256", "mono"])
def test_chromatic_resize_status_bounds_and_explicit_mono_geometry(runtime, columns, rows, mode):
    runtime.terminal_color_mode = mode
    size = os.terminal_size((columns, rows))
    settings = dict(command="palette auto", status="COLOR ON | PALETTE AUTO | " * 20)
    lines = frame_lines(runtime, size, **settings)
    output = io.StringIO()
    draw_frame(output, lines, size)
    encoded = output.getvalue()
    assert "\n" not in encoded
    screen_rows = re.split(r"\x1b\[\d+;1H\x1b\[2K", encoded)[1:]
    assert len(screen_rows) == rows
    assert all(len(ANSI.sub("", line)) <= columns for line in screen_rows)
    colored_mono = frame_lines(runtime, size, mono=True, **settings)
    runtime.chromatic.enabled = False
    assert frame_lines(runtime, size, mono=True, **settings) == colored_mono
    assert not any("38;" in line or "48;" in line for line in colored_mono)


@pytest.mark.parametrize("mode", ["truecolor", "256", "mono"])
def test_creator_real_pty_color_modes_resize_and_restore(tmp_path, mode):
    master, slave = os.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    previous = termios.tcgetattr(slave)
    code = (
        "import json,sys,termios\nfrom pathlib import Path\n"
        "from scripts.pty_support import terminal_settings_equal\n"
        "tty_before=termios.tcgetattr(0)\n"
        "from commander_zorg.canonical import read_json\n"
        "from commander_zorg.live_motion import LiveRuntime\n"
        "from commander_zorg.morph_targets import load_targets\n"
        "from commander_zorg.morph_lab import run_lab\n"
        "config=read_json(Path('scenes/live_lab.json'))\n"
        "targets=load_targets(Path('morph_targets'),LiveRuntime(config).scene)\n"
        "result=run_lab(config,targets,Path(sys.argv[1])/'take',"
        "mono=(sys.argv[2]=='mono'),max_seconds=1.2)\n"
        "assert terminal_settings_equal(tty_before,termios.tcgetattr(0)), 'child tty not restored'\n"
        "(Path(sys.argv[1])/'result.json').write_text(json.dumps(result))\n"
    )
    environment = dict(os.environ, TERM="xterm-256color", COLORTERM="")
    if mode == "truecolor":
        environment["COLORTERM"] = "truecolor"
    process = subprocess.Popen(
        [sys.executable, "-c", code, str(tmp_path), mode], cwd=ROOT,
        stdin=slave, stdout=slave, stderr=subprocess.PIPE, env=environment,
    )
    output = b""
    sent = resized = False
    deadline = time.monotonic() + 6
    try:
        # Drain while the child runs: RGB output can exceed a PTY buffer.
        while time.monotonic() < deadline:
            if select.select([master], [], [], .05)[0]:
                output += os.read(master, 65536)
            if not sent and b"COMMAND:" in output:
                os.write(master, b"speed fast\rcolor on\rpalette cloud\r")
                sent = True
            if mode == "truecolor":
                ready = any(r != g or g != b for r, g, b in re.findall(
                    rb"\x1b\[38;2;(\d+);(\d+);(\d+)m", output))
            elif mode == "256":
                ready = any(17 <= int(n) <= 230 and int(n) not in (59, 102, 145, 188)
                            for n in re.findall(rb"\x1b\[38;5;(\d+)m", output))
            else:
                ready = b"PALETTE CLOUD" in output
            # Observe the actual selected color mode before shrinking its raster.
            if sent and not resized and ready:
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 3, 8, 0, 0))
                resized = True
            if process.poll() is not None:
                while select.select([master], [], [], 0)[0]:
                    output += os.read(master, 65536)
                break
        assert process.poll() is not None, "creator preview failed to terminate while output was drained"
        assert process.returncode == 0, process.stderr.read().decode()
        assert sent and resized
        assert b"\x1b[3;1H\x1b[2KSTATUS:" in output
        # The child checks the complete tty state before its PTY is hung up.
        assert b"\x1b[?25h\x1b[?1049l" in output
        assert b"\n" not in output
        result = json.loads((tmp_path / "result.json").read_text())
        assert result["status"] == "complete"
        assert result["metrics"]["preview_frames"] > 1
        if mode == "truecolor":
            matches = re.findall(rb"\x1b\[38;2;(\d+);(\d+);(\d+)m", output)
            assert any(r != g or g != b for r, g, b in matches)
            assert b"\x1b[48;2;" in output
        elif mode == "256":
            matches = [int(n) for n in re.findall(rb"\x1b\[38;5;(\d+)m", output)]
            assert any(17 <= n <= 230 and n not in (59, 102, 145, 188) for n in matches)
            assert b"\x1b[48;5;" in output
            assert b"\x1b[38;2;" not in output
        else:
            assert b"\x1b[38;" not in output and b"\x1b[48;" not in output
            assert any(glyph.encode() in output for glyph in "▀▄█")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)
        process.stderr.close()
        os.close(master)
        os.close(slave)


def test_studio_header_exposes_color_and_palette_at_standard_width(runtime):
    from commander_zorg.morph_lab import _viewport
    runtime.terminal_color_mode = '256'
    runtime.chromatic.enabled = True
    runtime.chromatic.set_palette('cloud', runtime.active_target, runtime.state.tick, 120)
    for columns in (80, 100):
        lines = _viewport(runtime, os.terminal_size((columns, 24)))
        assert len(lines[0]) <= columns
        assert 'COLOR ON CLOUD' in lines[0]
        assert 'AUTO' in lines[0]
        assert 'MOTION' in lines[0]
        assert 'SPEED' in lines[0]
    for columns in (8, 24, 40, 60):
        lines = _viewport(runtime, os.terminal_size((columns, 24)))
        assert len(lines[0]) <= columns
        if columns >= len('COLOR ON CLOUD'):
            assert 'COLOR ON CLOUD' in lines[0]
