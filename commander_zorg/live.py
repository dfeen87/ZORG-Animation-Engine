"""Fixed-tick live runtime with bounded terminal input and durable recording."""

from __future__ import annotations

from contextlib import contextmanager
import math
import os
from pathlib import Path
import select
import sys
import termios
import time
import tty
from typing import Any

from .live_commands import HELP, parse_command
from .live_motion import LiveRuntime
from .session import Recorder
from .terminal_view import CommandInput, draw_frame, frame_lines, terminal_size, use_monochrome


@contextmanager
def terminal_session(input_stream: Any, output_stream: Any):
    """Own terminal settings only inside this context, including failure paths."""
    fd = input_stream.fileno()
    previous = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd, termios.TCSANOW)
        output_stream.write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H")
        output_stream.flush()
        yield
    finally:
        # Restore input first: an unavailable output device must not strand raw
        # input settings. Best-effort ANSI cleanup also covers broken pipes.
        try:
            termios.tcsetattr(fd, termios.TCSANOW, previous)
        finally:
            try:
                output_stream.write("\x1b[0m\x1b[?25h\x1b[?1049l")
                output_stream.flush()
            except (OSError, ValueError):
                pass


def run_live(config: dict, record: Path, *, mono: bool = False,
             preview_fps: float = 15.0, max_seconds: float | None = None,
             input_stream: Any = None, output_stream: Any = None,
             runtime_factory=LiveRuntime, recorder_factory=None,
             command_parser=parse_command, help_text=HELP, viewport=frame_lines) -> dict:
    """Run a live take; display frames may be dropped, simulation ticks never are.

    ``save`` returns ``save_requested=True`` for the CLI's offline exporter.
    A non-TTY call fails before creating a recording; use live-demo instead.
    Each command is accepted before the next transition at its saved tick.
    """
    input_stream = sys.stdin if input_stream is None else input_stream
    output_stream = sys.stdout if output_stream is None else output_stream
    if not input_stream.isatty() or not output_stream.isatty():
        raise ValueError("live requires an interactive terminal; use live-demo for noninteractive animation")
    if not math.isfinite(preview_fps) or not 1.0 <= preview_fps <= 30.0:
        raise ValueError("preview_fps must be finite and between 1 and 30")
    if max_seconds is not None and (not math.isfinite(max_seconds) or max_seconds <= 0):
        raise ValueError("max_seconds must be finite and positive")

    runtime = runtime_factory(config)
    recorder = (Recorder(Path(record), runtime.config) if recorder_factory is None
                else recorder_factory(Path(record), runtime))
    editor = CommandInput()
    monochrome = use_monochrome(mono)
    sim_hz = runtime.scene.sim_hz
    tick_limit = runtime.scene.terminal_tick
    if max_seconds is not None:
        bounded_seconds = min(max_seconds, tick_limit / sim_hz)
        tick_limit = min(tick_limit, math.ceil(bounded_seconds * sim_hz))
    status_text = "Moving autonomously; type help"
    recording_status, reason = "complete", "quit"
    save_requested = False
    frame_count = 0
    render_seconds = 0.0
    started = time.monotonic()
    failure = None
    try:
        with terminal_session(input_stream, output_stream):
            started = time.monotonic()
            next_tick, next_preview = started + 1.0 / sim_hz, started
            running = True
            while running:
                now = time.monotonic()
                timeout = max(0.0, min(next_tick - now, next_preview - now, 0.05))
                readable, _, _ = select.select([input_stream.fileno()], [], [], timeout)
                if readable:
                    data = os.read(input_stream.fileno(), 4096)
                    if not data:
                        reason, running = "eof", False
                    for event in editor.feed(data):
                        if event.kind in ("interrupt", "eof"):
                            reason = "ctrl_c" if event.kind == "interrupt" else "eof"
                            recording_status = "interrupted" if event.kind == "interrupt" else "complete"
                            running = False
                            break
                        if event.kind == "invalid":
                            status_text = event.text
                            continue
                        try:
                            command = command_parser(event.text)
                            action = command["action"]
                            if action == "help":
                                status_text = help_text
                            elif action in ("save", "quit"):
                                reason, running = action, False
                                save_requested = action == "save"
                                break
                            else:
                                accepted = runtime.accept(event.text)
                                status_text = f"{action.upper()} accepted at tick {runtime.state.tick}"
                        except ValueError as exc:
                            status_text = str(exc)
                            continue
                        if action not in ("help", "save", "quit"):
                            # A recording failure is fatal: never acknowledge a
                            # command whose event was not durably captured.
                            recorder.record_event(accepted)
                if not running:
                    break

                # Bound work per pass to keep keyboard polling responsive under
                # load. Backlog remains due, and every transition is executed.
                now = time.monotonic()
                for _ in range(8):
                    if now < next_tick:
                        break
                    if tick_limit is not None and runtime.state.tick >= tick_limit:
                        reason, running = "duration_limit", False
                        break
                    runtime.step()
                    next_tick += 1.0 / sim_hz
                if tick_limit is not None and runtime.state.tick >= tick_limit:
                    reason, running = "duration_limit", False
                if not running:
                    break

                now = time.monotonic()
                if now >= next_preview:
                    render_started = time.monotonic()
                    elapsed = max(now - started, 1e-9)
                    size = terminal_size(output_stream)
                    lines = viewport(runtime, size, command=editor.text,
                                        status=status_text, fps=frame_count / elapsed,
                                        mono=monochrome)
                    draw_frame(output_stream, lines, size)
                    render_seconds += time.monotonic() - render_started
                    frame_count += 1
                    next_preview = time.monotonic() + 1.0 / preview_fps
    except KeyboardInterrupt:
        recording_status, reason = "interrupted", "ctrl_c"
    except Exception as exc:
        recording_status, reason = "failed", f"{type(exc).__name__}: {exc}"
        failure = exc

    elapsed = max(time.monotonic() - started, 1e-9)
    metrics = {
        "preview_frames": frame_count,
        "achieved_preview_fps": frame_count / elapsed,
        "render_seconds": render_seconds,
        "elapsed_seconds": elapsed,
        "final_tick": runtime.state.tick,
    }
    try:
        session = recorder.finish(runtime, status=recording_status, reason=reason, metrics=metrics)
    except KeyboardInterrupt:
        # Input settings have already been restored before recording is closed.
        # One interrupted close gets a single retry with a truthful status.
        if recording_status != "failed":
            recording_status, reason = "interrupted", "ctrl_c_during_finish"
        save_requested = False
        session = recorder.finish(runtime, status=recording_status, reason=reason, metrics=metrics)
    except (OSError, ValueError) as exc:
        # An interrupt or failed write may leave a partially recorded event.
        # Such a take is diagnostic evidence, never a replayable success.
        recording_status, reason = 'failed', f'finalization: {type(exc).__name__}: {exc}'
        save_requested = False
        failure = failure or exc
        session = recorder.finish(runtime,status='failed',reason=reason,metrics=metrics)
    if failure is not None:
        raise RuntimeError(f"Live recording failed; diagnostic session saved at {session}: {reason}") from failure
    return {"session": str(session), "status": recording_status, "reason": reason,
            "save_requested": save_requested, "metrics": metrics}
