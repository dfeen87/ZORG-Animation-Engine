# CI and platform evidence

Development Linux: the complete suite executed **932 tests, 932 passed, zero
failed/skipped/deselected**. Passive per-phase outcomes independently match all
932 JUnit cases; the strict inventory audit passes with a preserved minimum of
765. Two pre-existing `record_property`/xunit2 warnings remain. Locked dependency
check passes. The real libx264 smoke encode/ffprobe reports H.264, yuv420p, 30 FPS,
three ordered frames. Relevant evidence is in `studio-evidence/`.

PR #7 and its main merge have a confirmed hosted Ubuntu failure: FFmpeg absent,
764 tests passed and one MP4 test skipped; the inventory audit correctly failed.
Do not weaken the zero-skip rule. Both workflows now install FFmpeg/ffprobe and
require an actual libx264 smoke encode/probe. Local application PNG/HTML fallback
remains available when optional encoding is absent; CI coverage requires it.

Historical hosted macOS runs also failed/hung before adaptive motion. Their
15-minute cancellation prevented final tracebacks/JUnit. The exact native cause
was not proven by the available old logs. Progress-to-test mapping suggests PTY
failures, but that is an inference. A cancelled job is not a pass.

Confirmed harness hazards have been repaired: wait-before-drain can deadlock
when terminal or stderr buffers fill, cleanup could skip descriptor close after
timeout, and Python `preexec_fn` could hang before exec in a scientific-library
parent. A shared helper uses `start_new_session`, a fresh interpreter terminal
bootstrap, concurrent PTY/stderr drainage, and bounded TERM/KILL/reap cleanup.
Stress tests prove flooding and TERM-resistant cleanup behavior. No wait limit
or workflow timeout was increased. AST comparison preserves every original
assertion expression in the three modified historical test modules.

CI now saves each test start and each phase failure/traceback immediately, so a
later hang cannot erase its cause. `faulthandler_timeout=30` emits diagnostic
stacks without changing test outcomes or imposing a pass/fail timeout. Passive
hook tests demonstrate that traceback evidence survives a deliberately hung
later fixture. The deep workflow additionally requires the exact chromatic demo.
Both YAML files and all 19 shell blocks parse; action SHAs and read-only job
permissions remain pinned. Full actionlint was unavailable.

Hosted Ubuntu/macOS results for this feature are recorded separately when run.
Native MacBook Terminal.app/iTerm2 visual and cleanup acceptance remains pending
until the creator executes the supplied guide. Linux PTY emulation, a source
inspection or a cancelled macOS job must never be substituted for it.
