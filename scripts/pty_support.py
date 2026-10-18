"""Bounded POSIX PTY test transport; never restores settings for the child."""
from __future__ import annotations

import errno
import fcntl
import os
from pathlib import Path
import select
import signal
import struct
import subprocess
import sys
import termios
import time


def terminal_settings_equal(expected, actual):
    """Compare real tty settings, ignoring Darwin's transient PENDIN flag.

    PENDIN requests a pending-input retype after canonical-mode restoration.
    macOS may set it during tcsetattr; it is not a persistent user setting.
    Every other input/output/control/local flag, speed and control byte must match.
    """
    if len(expected) != 7 or len(actual) != 7:
        return False
    before, after = list(expected), list(actual)
    if sys.platform == 'darwin':
        pending = getattr(termios, 'PENDIN', 0x20000000)
        before[3] &= ~pending
        after[3] &= ~pending
    return before == after


class PtyProcess:
    """Keep the slave for restoration assertions and drain both child streams."""

    def __init__(self, code, args=(), *, cwd, size=(80, 24)):
        self.master = self.slave = None
        self.process = None
        self.output = b''
        self.stderr = b''
        self._readers = {}
        self._closed = False
        try:
            self.master, self.slave = os.openpty()
            fcntl.ioctl(self.slave, termios.TIOCSWINSZ,
                        struct.pack('HHHH', size[1], size[0], 0, 0))
            self.previous = termios.tcgetattr(self.slave)
            # setsid is performed by Popen's C implementation. The new Python
            # process claims its terminal before importing any application code.
            # No Python preexec_fn runs in a fork of a NumPy-loaded parent.
            self.process = subprocess.Popen(
                [sys.executable, '-u', str(Path(__file__).resolve()),
                 '--child', code, *map(str, args)], cwd=cwd,
                stdin=self.slave, stdout=self.slave, stderr=subprocess.PIPE,
                start_new_session=True,
            )
            os.set_blocking(self.master, False)
            os.set_blocking(self.process.stderr.fileno(), False)
            self._readers = {self.master: 'output', self.process.stderr.fileno(): 'stderr'}
        except BaseException:
            self.close()
            raise

    def _pump(self, timeout):
        if not self._readers:
            # wait() still polls a child that has closed both output streams.
            if timeout:
                time.sleep(timeout)
            return False
        readable, _, _ = select.select(list(self._readers), [], [], timeout)
        for fd in readable:
            try:
                block = os.read(fd, 65536)
            except BlockingIOError:
                continue
            except OSError as error:
                if error.errno != errno.EIO or fd != self.master:
                    raise
                block = b''  # Linux PTY hangup; BSD PTYs may return EOF.
            if block:
                name = self._readers[fd]
                setattr(self, name, getattr(self, name) + block)
            else:
                self._readers.pop(fd, None)
        return bool(readable)

    def wait_for(self, predicate, *, timeout=5):
        deadline = time.monotonic() + timeout
        while True:
            if predicate(self.output):
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self._pump(min(.05, remaining))
            if self.process.poll() is not None:
                # A final readable block may contain the expected marker.
                while time.monotonic() < deadline and self._pump(0):
                    pass
                if predicate(self.output):
                    return
                break
        raise AssertionError(
            f'PTY condition missing; child={self.process.poll()}, '
            f'tail={self.output[-1000:]!r}, stderr={self.stderr[-4000:]!r}')

    def send(self, value):
        # Test commands are shorter than the terminal input buffer.
        written = os.write(self.master, value)
        if written != len(value):
            raise OSError('incomplete PTY command write')

    def wait(self, *, timeout):
        deadline = time.monotonic() + timeout
        while self.process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(self.process.args, timeout,
                                                output=self.output, stderr=self.stderr)
            self._pump(min(.05, remaining))
        while time.monotonic() < deadline and self._pump(0):
            pass
        return self.process.returncode

    def close(self, *, timeout=3):
        """Bound TERM/KILL/reap together, including a failed test's cleanup."""
        if self._closed:
            return
        self._closed = True
        deadline = time.monotonic() + timeout
        try:
            if self.process is not None:
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                if self.process.poll() is None:
                    try:
                        self.wait(timeout=min(.25, max(0, deadline - time.monotonic())))
                    except subprocess.TimeoutExpired:
                        pass
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                if self.process.poll() is None:
                    self.wait(timeout=max(0, deadline - time.monotonic()))
        finally:
            self._readers.clear()
            if self.process is not None and self.process.stderr is not None:
                self.process.stderr.close()
            for name in ('master', 'slave'):
                fd = getattr(self, name)
                if fd is not None:
                    os.close(fd)
                    setattr(self, name, None)


def _child():
    if len(sys.argv) < 3 or sys.argv[1] != '--child':
        raise SystemExit('test helper requires --child CODE [ARG ...]')
    code = sys.argv[2]
    sys.argv = ['-c', *sys.argv[3:]]
    fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    # Validate before the child exits. Darwin may revoke a PTY slave when its
    # controlling process exits; inspecting the slave afterward can raise ENOTTY.
    baseline = termios.tcgetattr(0)
    try:
        exec(compile(code, '<pty-child>', 'exec'), {'__name__': '__main__'})
    finally:
        restored = termios.tcgetattr(0)
        if not terminal_settings_equal(baseline, restored):
            raise AssertionError('PTY child did not restore its own terminal settings')


if __name__ == '__main__':
    _child()
