"""Real POSIX pseudo-terminal checks, without claiming native macOS acceptance."""

from __future__ import annotations

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

from commander_zorg.live import run_live, terminal_session
from commander_zorg.live_motion import LiveRuntime
from commander_zorg.session import verify_session
from commander_zorg.terminal_view import CommandInput, draw_frame, frame_lines, half_blocks


ROOT = Path(__file__).resolve().parents[1]


def _config():
    return json.loads((ROOT / "scenes/live_lab.json").read_text())


class PtyTake:
    """Keep the slave open so settings can be compared after child exit."""

    def __init__(self, directory, *, size=(80, 24), fail=False):
        self.master, self.slave = os.openpty()
        fcntl.ioctl(self.slave, termios.TIOCSWINSZ,
                    struct.pack("HHHH", size[1], size[0], 0, 0))
        self.previous = termios.tcgetattr(self.slave)
        self.directory = directory
        self.output = b""
        code = (
            "import json,sys\nfrom pathlib import Path\n"
            "from commander_zorg.live import run_live\n"
            "from commander_zorg.live_motion import LiveRuntime\n"
            "config=json.loads(Path('scenes/live_lab.json').read_text())\n"
        )
        if fail:
            code += (
                "original=LiveRuntime.step\n"
                "def step(self):\n"
                " if self.state.tick >= 3: raise RuntimeError('injected transition failure')\n"
                " return original(self)\n"
                "LiveRuntime.step=step\n"
            )
        code += (
            "result=run_live(config,Path(sys.argv[1])/'take',mono=True,max_seconds=8)\n"
            "(Path(sys.argv[1])/'result.json').write_text(json.dumps(result))\n"
        )

        def controlling_terminal():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)

        self.process = subprocess.Popen(
            [sys.executable, "-c", code, str(directory)], cwd=ROOT,
            stdin=self.slave, stdout=self.slave, stderr=subprocess.PIPE,
            preexec_fn=controlling_terminal,
        )

    def wait_for(self, predicate, *, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            readable, _, _ = select.select([self.master], [], [], 0.05)
            if readable:
                self.output += os.read(self.master, 65536)
            if predicate(self.output):
                return
            if self.process.poll() is not None:
                break
        raise AssertionError(f"PTY condition missing; child={self.process.poll()}, tail={self.output[-500:]!r}")

    def tick(self, minimum):
        self.wait_for(lambda output: any(int(n) >= minimum for n in re.findall(rb"TICK (\d+)", output)))

    def send(self, value):
        os.write(self.master, value)

    def finish(self, *, expected_code=0):
        self.process.wait(timeout=5)
        while select.select([self.master], [], [], 0)[0]:
            self.output += os.read(self.master, 65536)
        stderr = self.process.stderr.read().decode()
        assert self.process.returncode == expected_code, stderr
        assert termios.tcgetattr(self.slave) == self.previous
        assert b"\x1b[?25h\x1b[?1049l" in self.output
        assert b"\n" not in self.output  # fixed rows, no scrolling log
        return json.loads((self.directory / "take/session.json").read_text())

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=3)
        self.process.stderr.close()
        os.close(self.master)
        os.close(self.slave)


@pytest.fixture
def pty_take(tmp_path):
    takes = []

    def create(**kwargs):
        directory = tmp_path / str(len(takes))
        directory.mkdir()
        take = PtyTake(directory, **kwargs)
        takes.append(take)
        return take

    yield create
    for take in takes:
        take.close()


def test_live_foundation_real_pty_left_tick_log_and_exact_replay(pty_take):
    take = pty_take()
    take.tick(30)
    take.send(b"l")
    take.wait_for(lambda data: b"COMMAND: l" in data)
    take.send(b"eft\r")
    take.wait_for(lambda data: b"LEFT accepted at tick" in data)
    accepted = int(re.search(rb"LEFT accepted at tick (\d+)", take.output)[1])
    take.tick(accepted + 130)
    take.send(b"quit\r")
    doc = take.finish()
    events = [json.loads(line) for line in (take.directory / "take/events.jsonl").read_text().splitlines()]
    assert events[0]["action"] == "left"
    assert events[0]["effective_tick"] == accepted >= 30
    assert doc["metrics"]["preview_frames"] > 15
    assert doc["metrics"]["achieved_preview_fps"] > 8
    assert "█".encode() in take.output or "▀".encode() in take.output
    assert verify_session(take.directory / "take/session.json")["passed"]

    # Compare against the exact same tick-driven autonomous trajectory.
    autonomous, directed = LiveRuntime(doc["config"]), LiveRuntime(doc["config"])
    before = autonomous.state.positions.copy()
    for tick in range(doc["final_tick"]):
        if tick == accepted:
            directed.apply_event(events[0])
        autonomous.step()
        directed.step()
    assert np.linalg.norm(autonomous.state.positions - before) > 0.01
    assert np.mean(directed.state.positions[:, 0] - autonomous.state.positions[:, 0]) < -0.15


@pytest.mark.parametrize("ending,reason,status", [
    (b"quit\r", "quit", "complete"),
    (b"save\r", "save", "complete"),
    (b"\x03", "ctrl_c", "interrupted"),
    (b"\x04", "eof", "complete"),
])
def test_live_pty_clean_exit_modes(pty_take, ending, reason, status):
    take = pty_take(size=(18, 6))
    take.wait_for(lambda data: b"COMMAND:" in data)
    take.send(ending)
    doc = take.finish()
    assert (doc["reason"], doc["status"]) == (reason, status)


def test_live_pty_invalid_command_continues_and_resize(pty_take):
    take = pty_take(size=(30, 9))
    take.wait_for(lambda data: b"COMMAND:" in data)
    take.send(b"left nan\r")
    take.wait_for(lambda data: b"STATUS: direction strength" in data)
    fcntl.ioctl(take.slave, termios.TIOCSWINSZ, struct.pack("HHHH", 3, 8, 0, 0))
    # A resized tiny terminal keeps its command row and can still exit.
    take.wait_for(lambda data: b"\x1b[3;1H\x1b[2KSTATUS:" in data)
    take.send(b"quit\r")
    doc = take.finish()
    assert doc["event_count"] == 0
    assert doc["status"] == "complete"


def test_live_pty_transition_failure_restores_and_records_failure(pty_take):
    take = pty_take(fail=True)
    take.wait_for(lambda data: b"COMMAND:" in data)
    doc = take.finish(expected_code=1)
    assert doc["status"] == "failed"
    assert doc["final_tick"] == 3
    assert "injected transition failure" in doc["reason"]


def test_noninteractive_live_rejected_before_record_creation(tmp_path):
    with pytest.raises(ValueError, match="live-demo"):
        run_live(_config(), tmp_path / "take", input_stream=io.StringIO(), output_stream=io.StringIO())
    assert not (tmp_path / "take").exists()


def test_terminal_context_restores_on_output_error():
    master, slave = os.openpty()
    before = termios.tcgetattr(slave)

    class BrokenOutput:
        def write(self, text):
            raise BrokenPipeError("terminal gone")

    try:
        with os.fdopen(os.dup(slave), "r") as stream:
            with pytest.raises(BrokenPipeError), terminal_session(stream, BrokenOutput()):
                pass
        assert termios.tcgetattr(slave) == before
    finally:
        os.close(master)
        os.close(slave)


def test_input_editor_rejects_overflow_escapes_and_preserves_partial_line():
    editor = CommandInput()
    assert editor.feed(b"le") == []
    assert editor.text == "le"
    assert editor.feed(b"\x1b[Aft\x7fT\r\n")[0].text == "lefT"
    assert editor.feed(b"x" * 161 + b"\r")[0].kind == "invalid"
    assert editor.text == ""
    assert editor.feed(b"\x03")[0].kind == "interrupt"


def test_preview_uses_field_and_fits_without_newlines():
    runtime = LiveRuntime(_config())
    pixels = np.array([[0, 255, 0, 255], [0, 0, 255, 255]], dtype=np.uint8)
    assert half_blocks(pixels, mono=True) == [" ▀▄█"]
    assert "38;2;" in half_blocks(pixels)[0]
    with pytest.raises(ValueError):
        half_blocks(pixels.astype(float))
    for columns, rows in ((1, 1), (8, 3), (20, 6), (80, 24), (200, 60)):
        size = os.terminal_size((columns, rows))
        lines = frame_lines(runtime, size, command="left", mono=True)
        assert len(lines) <= rows
        output = io.StringIO()
        draw_frame(output, lines, size)
        assert "\n" not in output.getvalue()
        assert f"\x1b[{rows};1H" in output.getvalue()
