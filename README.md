# ZORG

ZORG is a small, local mathematical animation engine. Commander-ZORG is the
original fictional production that motivates the technology. This repository
began as **Commander-Zorg**; its existing history and MIT software license,
including Don Michael Feeney Jr.'s attribution, are preserved.

Build 0 evaluates positive Gaussian influence fields, renders deterministic
grayscale silhouettes, and animates independent damped springs with a prescribed
quartic force pulse. It exports inspectable state, decision, frame, source and
integrity evidence. It has no editor, network service, AI system, memory layer,
GPU dependency or production character pipeline. Artistic approval is separate
from numerical acceptance and remains pending unless the creator supplies it.

The internal Python package remains `commander_zorg` and the scene schema remains
`cz-scene-0.3`. The numerical authority is the verified v0.3 specification;
[architecture decisions](docs/adr) and [scene decisions](docs/scene-decisions.md)
record implementation choices. Implementation reports state which complete
experiments and evidence gates actually passed.

The verified take passed **456 tests**, all six E0 candidates, full E1 and
cue-off sequences, numerical/image gates, integrity and fresh-process replay.
See the [implementation report](docs/results/implementation-report.md),
[numerical results](docs/results/numerical-verification.md),
[E0 gallery](docs/results/e0-gallery.png) and
[E1 contact sheet](docs/results/e1-contact-sheet.png).
Creator review is pending. The implementation branch is pushed to
`dfeen87/ZORG`; GitHub API networking still blocks metadata verification and
automated PR creation. [Create the PR on GitHub](https://github.com/dfeen87/ZORG/pull/new/feature/build0-foundation).

## Install on a MacBook or Linux machine

Python **3.12** is the supported baseline. The implementation environment is
Linux on x86-64 with Python 3.12; exact interpreter, NumPy, Pillow, pytest and
zlib versions are recorded in run manifests and `requirements.lock`. Native
macOS acceptance has not been demonstrated. A MacBook should use the same
Python minor release, install the locked dependencies, run the tests, and
regenerate evidence locally. Exact PNG replay is demonstrated only within the
recorded environment, not promised across operating systems or compiled builds.

Clone the existing private repository using your existing GitHub access:

```sh
git clone https://github.com/dfeen87/ZORG.git
cd ZORG
git checkout feature/build0-foundation
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
```

The engine uses Python, NumPy and Pillow; pytest is the test dependency. No
FFmpeg, SciPy, browser framework or external development service is required.
The commands below also work as `python -m commander_zorg.cli ...` after
installation or from the checkout root.

## Test and regenerate experiments

Reproduce the complete experiment, including test reports, E0, full E1 and
control, numerical cadence comparisons, integrity checks, fresh-process replay
and the final linked profile report:

```sh
python scripts/run_build0.py --out outputs/build0_take_01
```

The runner preserves complete evidence in the new output directory and records
all measured gates. It refuses an existing destination. To execute the same
operations individually:

```sh
python -m pytest -q
commander-zorg validate scenes/e1.json
commander-zorg gallery scenes/e0 --out outputs/e0_take_01
commander-zorg render scenes/e1.json --out outputs/e1_take_01
commander-zorg render scenes/control.json --out outputs/control_take_01
commander-zorg cadence scenes/e1.json --out outputs/cadence_take_01.json
commander-zorg verify outputs/e1_take_01/manifest.json --integrity
commander-zorg verify outputs/control_take_01/manifest.json --integrity
commander-zorg verify outputs/e1_take_01/manifest.json --replay --out outputs/replay_take_01
```

Every destination must be new. Use a new take name for another run; existing
takes are refused. Rendering success does not imply all Build 0 profile gates
passed. The complete E1 and control each contain 180 PNG frames at ticks
`0,2,...,358`, 361 state rows through terminal audit tick 360, and 360 accepted
transition rows. Frame zero is rendered before stepping. Renderers stream one
field at a time, and numerical rejection preserves the last committed state
and terminates the run without clamping or repair.

Each run contains:

```text
scene.input.json       scene.resolved.json
frames/                contact_sheet.png
states.jsonl           decisions.jsonl          frames.jsonl
run_status.json        manifest.json            source/
```

The gallery contains six complete child static runs and its labeled contact
sheet. State and decision traces use canonical JSON. The engine records raw
input and resolved semantic hashes separately, exact executed source hashes,
environment versions, decoded-pixel hashes and PNG file hashes. The final
manifest is published atomically after checking all closed artifacts. Failed
or interrupted runs are retained and cannot verify as complete.

A release experiment manifest links the E0 gallery, E1, full cue-off control,
cadence study, fresh-process replay report and executed test report using
relative paths plus SHA-256 hashes. Its schema is `cz-experiment-0.3` (see
[schemas](schemas)). Once this manifest and its linked evidence exist:

```sh
commander-zorg check-profile outputs/experiment_manifest.json --report outputs/profile_report.json
```

This command verifies linked integrity before checking numerical and image
acceptance. It recomputes the cadence study with independent scalar and analytic
references, verifies test-output and JUnit hashes, and checks actual JUnit
testcase totals rather than trusting report pass flags. Tests and report values must come from actual executions. It checks
all recovery states at ticks 330–360, every recovery output frame, excitation,
centroid-aligned morphology, visibility, ten distinct decoded frames, control
invariance, independent 60/120 Hz comparisons and exact replay. It never
substitutes creator artistic judgment. Exit codes are 0 success, 2 configuration
or usage failure, 3 numerical rejection, 4 integrity/export failure, 5 replay
failure, and 6 experiment/profile failure.

## View the outputs

Open `player.html` from an exported run in your local browser for complete
30-FPS sequence playback, or open `contact_sheet.png` in your image viewer. The E1 sheet includes frames
0, 23, 38, 50, 60, 90, 120, 165 and 179, plus the minimum aligned-IoU frame
when different. Review the complete frame sequence for flicker; sparse stills
do not establish fluid motion. `frames/frame_000000.png` through
`frame_000179.png` are ordered at exactly 30 FPS for six seconds.

If FFmpeg is already installed locally, an optional viewing copy can be made:

```sh
ffmpeg -framerate 30 -i outputs/e1_take_01/frames/frame_%06d.png -c:v libx264 -pix_fmt yuv420p outputs/e1_preview.mp4
```

The PNG sequence and its recorded timestamps remain the required evidence.
No optional encoder is needed to inspect each full-resolution output image.
Ask during creator review whether the form feels fluid, an identifiable accent
survives, the disturbance reads clearly, and recovery feels intentional.

## Limits and next steps

Build 0 is an experiment in mathematical geometry, motion and verification.
It does not establish final character recognition, humor, mathematical novelty,
physical realism or a real-time performance guarantee. The proposed thirty-second
render target must be judged from measured runs. Generated outputs are ignored
by Git; preserve complete evidence separately and regenerate it with the same
scene and environment.

The next engineering experiment should follow the measured failing gate, if
any. A later creative tuning take must explicitly record scene changes and
retain its predecessors. Temporal history, predictive motion, colors,
cinematography, authoring tools and a community platform remain deferred.
The software's MIT license does not automatically confer rights to original
character artwork, scripts, fictional settings or third-party assets.

## Live Morph Lab — Build 0.1

The [Live Morph Lab guide](docs/live/README.md) documents the interactive ANSI
terminal viewport, reproducible autonomous motion, directional and shape
commands, tick-stamped recordings, offline replay, and PNG/HTML/optional MP4
export. It includes a noninteractive 15-second demo and a native MacBook
acceptance checklist. Build 0's finite experiments and numerical contracts
remain separate.

```sh
commander-zorg live --scene scenes/live_lab.json --record outputs/live_take_01
commander-zorg live-demo --out outputs/live_demo_01
```

The live viewport displays a Gaussian-field silhouette that wanders and changes
shape continuously. Type commands and press Return while it animates. Physics
runs at a fixed 60 Hz; the terminal preview targets 15 FPS. Accepted motion
commands are recorded with their effective simulation ticks for exact replay
with the same source and supported environment.

### New capabilities — Build 0.2

The Live Morph Lab now has a dedicated `morph-lab` mode for directing the
mathematical form itself:

- Smoothly morph between named `home`, `circle`, `oval`, `cloud`, and `hill`
  targets with `morph NAME`, or choose a transition duration with
  `morph NAME 2.0`.
- Combine named shape changes with directional movement, autonomous wander,
  and squash/stretch, within the existing numerical safety limits.
- Redirect an ongoing morph toward another target, or return the shape to
  `home`, while the animation continues.
- Preserve the current mathematical state with `capture LABEL`, including
  control positions, velocities, field parameters, motion targets, and the
  simulation tick; generate its preview PNG during export.
- Record and replay morph commands and captures, then export the animation
  as full-resolution PNG frames, a standalone HTML player, and optional MP4.
- Generate a complete 20-second morph demonstration with `morph-demo`.

```sh
commander-zorg morph-lab --record outputs/my_morph_take --mono
```

Inside this mode, try `morph circle`, `morph oval 2.0`, `up 0.05`,
`capture My_shape`, and `save`. Shape names express artistic intent;
creator approval remains pending. See the [Semantic Morph Lab guide](docs/morph/README.md)
for the complete workflow.

### Start an interactive take

From the repository root, using the Python 3.12 environment installed above:

```sh
source .venv/bin/activate
commander-zorg live --scene scenes/live_lab.json --seed 172026 --record outputs/my_live_take
```

Use a new recording directory for every take. The viewport needs an interactive
ANSI-compatible terminal; `--mono` forces monochrome rendering. Native macOS
terminal acceptance still needs the local checks in the guide.

### Commands to type inside the viewport

| Command | What it does |
| --- | --- |
| `left`, `right`, `up`, `down` | Smoothly move toward a directional offset from the home pose. |
| `squash` | Compress the shape vertically and widen its control layout. |
| `stretch` | Elongate the shape vertically and narrow its control layout. |
| `reset` | Smoothly return toward home and turn wander off. |
| `wander on`, `wander off` | Fade autonomous motion in or out. |
| `help` | Show the available commands while animation continues. |
| `save` | Finish the recording and export its animation. |
| `quit` | Exit cleanly and keep the recording for later export. |

Directional and shape commands accept **strength, then transition seconds**:

```text
right 0.3 2.0
stretch 0.5 1.5
left
squash
reset
save
```

Direction strength defaults to `0.3` world units and accepts `0.05`–`0.30`.
Shape strength defaults to `0.5` and accepts `0.05`–`0.60`. Transition duration
defaults to two seconds and accepts `0.5`–`10` seconds. Targets persist until
replaced: directions share one translation channel, squash/stretch share one
shape channel, and both can coexist with wander. Invalid commands are rejected
without stopping the animation. Ctrl+C restores the terminal and retains the
captured recording as interrupted.

### Replay, export and watch

Typing `save` exports into the recording's `export/` directory. Alternatively,
verify and export a saved recording explicitly:

```sh
commander-zorg verify-session outputs/my_live_take/session.json
commander-zorg render-session outputs/my_live_take/session.json --out outputs/my_live_video
commander-zorg verify-live-export outputs/my_live_video/manifest.json
```

The supplied scene exports a complete 384×384 PNG sequence at 30 FPS, a local
HTML player, session/event records and a manifest with source and artifact
hashes. When FFmpeg with H.264 support is available, it also creates
`animation.mp4`; otherwise the HTML player remains available. On a MacBook:

```sh
open outputs/my_live_video/player.html
# When MP4 encoding succeeded:
open outputs/my_live_video/animation.mp4
```

For a complete noninteractive demonstration using the same runtime:

```sh
commander-zorg live-demo --seed 172026 --out outputs/my_live_demo
open outputs/my_live_demo/video/player.html
```

The 15-second demo shows autonomous motion, rightward movement, stretch,
leftward movement, squash and recovery. See the
[saved demo video](docs/live/results/live-demo.mp4) and
[execution evidence](docs/live/results/README.md): 642 tests passed, including
all 456 unchanged Build 0 regressions, and the complete Build 0 experiment gates
passed again. Exact replay across different operating systems or library builds
is not claimed; record and verify a new take on the destination machine.

## Semantic Morph Lab — Build 0.2

The separately versioned [Semantic Morph Lab](docs/morph/README.md) adds explicit
mathematical recipes for home, circle, oval, cloud and hill, bounded morphing,
independent translation, creator-labeled state captures, and deterministic
replay/export. Eight original Gaussian controls and field parameters are
preserved. Artistic target approval remains pending; `head_base` is excluded
as insufficiently distinct. See the [feasibility study](docs/morph/feasibility.md)
and [implementation evidence](docs/morph/implementation-report.md).

```sh
commander-zorg morph-lab --record outputs/morph_take_01 --mono
# Inside the terminal: morph circle; morph oval; up .05; capture My_shape; save
commander-zorg morph-demo --out outputs/morph_demo_01
python scripts/check_morph_demo.py outputs/morph_demo_01/video/manifest.json --report outputs/morph_demo_01/check_report.json
```

Use a new take directory each time. Wide forms plus strong motion can exceed
the unchanged force budget; rejected commands preserve the current state.
