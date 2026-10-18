"""Exercise transport backpressure and failure cleanup independently of ZORG."""
import os
from pathlib import Path
import signal
import subprocess

import pytest

from scripts.pty_support import PtyProcess

ROOT = Path(__file__).resolve().parents[1]


def test_pty_child_owns_controlling_terminal():
    take = PtyProcess('import os; print(os.tcgetpgrp(0) == os.getpgrp())', cwd=ROOT)
    try:
        assert take.wait(timeout=3) == 0
        assert b'True' in take.output
    finally:
        take.close()


def test_pty_wait_drains_terminal_and_stderr_beyond_pipe_capacity():
    code = "import os\nfor _ in range(64):\n os.write(1,b'x'*8192)\n os.write(2,b'e'*8192)\n"
    take = PtyProcess(code, cwd=ROOT)
    try:
        assert take.wait(timeout=3) == 0
        assert take.output == b'x' * (64 * 8192)
        assert take.stderr == b'e' * (64 * 8192)
    finally:
        take.close()


def test_pty_early_exit_keeps_traceback_and_closes_descriptors():
    take = PtyProcess("raise RuntimeError('specific child failure')", cwd=ROOT)
    master, slave = take.master, take.slave
    try:
        with pytest.raises(AssertionError, match='specific child failure'):
            take.wait_for(lambda output: b'never emitted' in output, timeout=3)
        assert take.process.returncode == 1
    finally:
        take.close()
    for fd in (master, slave):
        with pytest.raises(OSError):
            os.fstat(fd)


def test_pty_timeout_then_cleanup_kills_term_resistant_child():
    code = "import signal,time\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\nprint('READY')\ntime.sleep(60)"
    take = PtyProcess(code, cwd=ROOT)
    take.wait_for(lambda output: b'READY' in output, timeout=3)
    with pytest.raises(subprocess.TimeoutExpired):
        take.wait(timeout=.05)
    take.close()
    assert take.process.returncode == -signal.SIGKILL
    assert take.process.stderr.closed
    assert take.master is take.slave is None
