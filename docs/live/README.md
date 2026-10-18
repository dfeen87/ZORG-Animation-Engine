# ZORG Live Morph Lab — Build 0.1

Live Morph Lab is a local terminal animation application built on ZORG's
Gaussian field evaluator. A seeded, moving silhouette responds to a small
command grammar. Captured actions have simulation ticks, so the same take can
be replayed and rendered offline at full resolution.

Build 0 remains a separate finite experiment. Its `cz-scene-0.3` contract,
accepted E0/E1 scenes, field equation, integration arithmetic, raster
quantization and acceptance thresholds are unchanged. The new live geometry
uses its own spring configuration (`spring_k: 10`); it does not retune E0/E1.

## Install and run

Use Python **3.12** and the existing virtual environment from Build 0. From the
repository root:

```sh
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
python -m pytest -q
commander-zorg live --scene scenes/live_lab.json --seed 172026 --record outputs/live_take_01
```

Every recording and export destination must be new. Keep each take rather than
overwriting animation evidence. No additional Python dependencies, hosted
services or specialist terminal graphics protocols are required. FFmpeg is an
optional local media encoder.

Run `live` in an ANSI-compatible interactive terminal, including macOS Terminal.
It requires TTY input and output. In a pipe, CI job or other noninteractive
environment, it exits with an actionable error before creating a take; run the
demo instead:

```sh
commander-zorg live-demo --scene scenes/live_lab.json --seed 172026 --out outputs/live_demo_01
```

This produces a 15-second recording in `outputs/live_demo_01/record` and its
rendered video artifacts in `outputs/live_demo_01/video`. The demo uses the same
command parser, motion runtime, recorder and exporter as live mode.

## Commands

Type a command and press Return while the animation continues. Commands are
case-insensitive and accept ordinary spaces. The optional argument order is
**strength, then transition seconds**; do not include units in the input.

| Command | Meaning | Default strength | Allowed strength |
| --- | --- | --- | --- |
| `left [strength] [seconds]` | Target a negative world-x offset | `0.3` | `0.05`–`0.30` world units |
| `right [strength] [seconds]` | Target a positive world-x offset | `0.3` | `0.05`–`0.30` world units |
| `up [strength] [seconds]` | Target a positive world-y offset | `0.3` | `0.05`–`0.30` world units |
| `down [strength] [seconds]` | Target a negative world-y offset | `0.3` | `0.05`–`0.30` world units |
| `squash [strength] [seconds]` | Compress the control layout vertically, widen horizontally | `0.5` | `0.05`–`0.60` |
| `stretch [strength] [seconds]` | Elongate the control layout vertically, narrow horizontally | `0.5` | `0.05`–`0.60` |
| `wander on` | Fade autonomous motion in over two seconds | — | No arguments |
| `wander off` | Fade autonomous motion out over two seconds | — | No arguments |
| `reset` | Recover translation and morphology toward home; fade wander out | — | No arguments |
| `help` | Show the command reference in the status area | — | No arguments |
| `save` | Finish the take and export it after leaving the viewport | — | No arguments |
| `quit` | Finish the take and retain its session for later export | — | No arguments |

Motion transitions default to **2 seconds** and accept `0.5`–`10` seconds.
They are rounded to the nearest simulation tick at 60 Hz. For example:

```text
right 0.25 1.5
stretch 0.55 2
left
reset
wander on
save
```

These are persistent targets, rather than impulses or timed holds. A directional
command selects one absolute translation vector relative to home. `left` after
`up` transitions toward `[-strength, 0]`; it does not accumulate another offset.
A new directional command replaces the translation target. A new squash or
stretch replaces the morphology target. The two channels coexist, and wander
continues independently until disabled. `reset` returns both channels toward
zero and disables wander; use `wander on` to resume it.

Transitions use a quintic target envelope with zero first and second derivatives
at both ends. Superseding a transition starts from its current target value;
the spring state retains its current positions and velocities. For commands
accepted on the same tick, recorded sequence order applies and the last command
in each affected channel determines that channel's new target. Forces do not
accumulate without bound. Morphology strength scales the Gaussian-control
layout around its home centroid; it is not a promise of the same percentage
change in the rendered silhouette's height.

Unknown commands, extra arguments, nonfinite values and out-of-range strengths
or durations are rejected in the status line without terminating the animation
or entering the action log. Input supports ASCII text and Backspace, with a
160-character limit. Arrow-key escape sequences are ignored; this is a small
line editor without history or shell completion.

## Preview and shutdown

Physics advances at a fixed **60 Hz**. Wall-clock time paces the live loop but
never supplies the procedural motion's time coordinate. Slow displays can skip
preview frames while every simulation transition is still executed; sustained
overload can make the simulated timeline lag wall time.

The preview targets **15 FPS**, using a square Gaussian raster sized to the
terminal and capped at 96 pixels per side, one sample per pixel. Unicode
half-blocks encode two raster rows per terminal row. ANSI foreground and
background truecolor supply grayscale when the terminal advertises support;
otherwise the application selects monochrome half-blocks. `--mono` always
forces monochrome.
The exporter independently evaluates the full scene resolution and supersampling.
Terminal preview pixels never become export inputs.

```sh
commander-zorg live --scene scenes/live_lab.json --record outputs/live_take_02 --mono --preview-fps 12
```

The viewport fits the current terminal size; very small terminals retain a
compact status/input area instead of rendering an unusable image. Rendering
overwrites fixed screen positions without scrolling. Input remains available
while motion runs. The session records measured preview frames, achieved FPS,
render time and wall time in `session.json`, rather than claiming a universal
performance guarantee.

`quit`, `save`, Ctrl+C and EOF leave the alternate screen and restore terminal
settings and cursor visibility. Ctrl+C saves an `interrupted` session, which can
be verified and exported through its last committed tick. Terminal or numerical
errors retain a diagnostic `failed` session and restore the terminal; failed or
still-running recordings cannot be replayed as completed evidence. As with any
terminal application, an uncatchable process kill or loss of power cannot run
cleanup; use the shell's `reset` utility if the terminal is left in an unusual
state.

The provided configuration limits a take to one hour (`216000` ticks).
`--max-seconds` can stop a short smoke test sooner. A duration limit preserves
the session; use `render-session` for an export unless the take ended with
`save`. `--no-mp4` on `live`, `live-demo` or `render-session` skips the optional
encoder while retaining PNG frames and the HTML player.

## Record, replay and watch

A live take is independent of its media:

```text
live_take_01/
  config.json
  events.jsonl
  session.json
  export/            # created when the creator types save
```

`config.json` contains the versioned initial configuration, including the full
geometry and seed. `events.jsonl` contains only accepted mathematical actions;
`help`, `save`, invalid input and `quit` are UI actions, not motion events.
`session.json` binds the artifacts, executed source hashes, environment versions,
final state and full numerical trajectory. It records actual duration as
`final_tick / 60`, not the time spent watching the screen.

```sh
commander-zorg verify-session outputs/live_take_01/session.json
commander-zorg render-session outputs/live_take_01/session.json --out outputs/live_video_01
commander-zorg verify-live-export outputs/live_video_01/manifest.json
```

The exporter produces ordered full-resolution PNGs at **30 FPS**, an always
available standalone `player.html`, a manifest with integrity hashes and, when
a usable FFmpeg with H.264 support is installed, `animation.mp4` encoded with
`yuv420p`. The supplied scene exports at **384 × 384**, with two samples per
axis. The HTML player reads the local PNG sequence directly; open it as a file
without a web server. Keep its `frames` directory beside it. Encoder absence or
failure is reported honestly and does not discard valid frames or the player.
An interrupted or failed render retains its status/artifacts and does not
publish a successful manifest. Each output path is exclusive, so retries use a
new destination.

The 15-second demo contains **450 frames**, named `frame_000000.png` through
`frame_000449.png`, at ticks `0, 2, ..., 898`. Its state trace contains ticks
`0` through `900`, including the final audit state, which is not rendered.
For an odd-length take the last 30-FPS frame spans the remaining simulation
tick; the manifest separately reports captured duration and media duration.
Exports also retain `record/`, `source/files/`, `states.jsonl`, `frames.jsonl`
and `export_status.json` alongside the player, media and manifest.

On a MacBook:

```sh
open outputs/live_video_01/player.html
# If the encoder succeeded:
open outputs/live_video_01/animation.mp4
```

The demonstration schedules `right 0.3 1.2` at tick 120 (2 s),
`stretch 0.55 1.2` at 240 (4 s), `left 0.3 1.2` at 360 (6 s),
`squash 0.55 1.2` at 480 (8 s), and `reset` at 600 (10 s).
It ends at tick 900 (15 s), allowing five seconds for recovery and stabilization.
The initial two seconds contain autonomous motion alone.

Replay requires the recorded source files and environment fingerprint to match.
Verification steps every captured tick and compares the trajectory and final
state hashes; frame integrity alone does not establish numerical replay.
The guarantee covers identical initial conditions, seed, events and supported
environment. A Linux take is not promised to reproduce bit-for-bit on macOS or
another NumPy/interpreter build. Generate and verify a new take locally on that
machine; changing or bypassing provenance checks is not a cross-platform proof.
Archive the commit and environment with any recording you intend to preserve.

## Live contracts and numerical safety

The documentary JSON Schema 2020-12 files are:

| Record | Version | Schema |
| --- | --- | --- |
| Initial configuration | `cz-live-config-0.1` | [`live-config.schema.json`](../../schemas/live-config.schema.json) |
| Each action event | `cz-live-event-0.1` | [`live-event.schema.json`](../../schemas/live-event.schema.json) |
| Session summary | `cz-live-session-0.1` | [`live-session.schema.json`](../../schemas/live-session.schema.json) |

The configuration embeds an ordinary `cz-scene-0.3` geometry with no finite
cues. Its separate live fields require `sim_hz: 60`, `fps_out: 30`, a uint32
seed, a boolean initial `wander`, and `max_ticks` from 2 through 216000.
The embedded finite timeline is not extended or reinterpreted as Build 0
evidence. An internal adapter supplies the live horizon for guard checks.

An event has exactly these fields:

```json
{
  "schema_version": "cz-live-event-0.1",
  "sequence": 0,
  "effective_tick": 120,
  "action": "left",
  "strength": 0.3,
  "duration_ticks": 120,
  "scope": "all",
  "envelope": "quintic-target-v1"
}
```

`effective_tick` is the committed simulation tick before the affected
transition. Sequence starts at zero and is contiguous. Tick order is
nondecreasing; multiple events may share a tick. Events effective at the final
recorded tick can be retained even when the take ends before another step.
Direction/morphology transition durations are 30–600 ticks. `reset`,
`wander_on` and `wander_off` use strength zero and exactly 120 ticks. All
controls currently have `scope: "all"`.

The autonomous target combines low-frequency sinusoids and per-element phases
derived deterministically from the seed and element IDs. Its influence fades
in smoothly during the first two seconds. It does not draw independent random
values each frame. Directional and differential morphology offsets share the
same spring state as that target.

The versioned live extension applies the bounded force bias
`spring_k * target_offset` to the spring/damping acceleration, using the same
semi-implicit Euler arithmetic as Build 0. Existing state ownership and
`check_transition` validation gate every candidate before commit. Force,
displacement, speed, identity and finite-value checks remain in force.
Rejected candidates are not clamped, repaired or substituted; the recording
fails at its last valid state. A custom live configuration must still satisfy
the scene loader and runtime limits; a command's valid syntax alone cannot
guarantee its safety with arbitrarily changed geometry or spring constants.

Schemas describe structure. The strict loaders and replay verifier additionally
enforce duplicate-key rejection, finite numbers, integer token requirements,
event sequencing, tick ranges, normalized command parameters, provenance,
artifact hashes and numerical trajectory equality. A schema match alone does
not establish any of those relationships or creator artistic acceptance.

## MacBook acceptance procedure

Automated Linux pseudo-terminal checks establish controlled input, rendering
and cleanup behavior in that environment. They do not establish native macOS
Terminal acceptance. Perform this local check in a real terminal:

1. Fetch the feature branch and activate the existing Python 3.12 environment:

   ```sh
   git fetch origin feature/live-morph-lab
   git switch feature/live-morph-lab
   git pull --ff-only origin feature/live-morph-lab
   source .venv/bin/activate
   python -m pip install -r requirements.lock
   python -m pip install --no-deps -e .
   python -m pytest -q
   ```

2. Launch a new take:

   ```sh
   commander-zorg live --scene scenes/live_lab.json --seed 172026 --record outputs/mac_live_take_01
   ```

3. Watch for several seconds without commands. Confirm continuous autonomous
   movement, changing contours and a stable input area. Note the displayed FPS.
4. Type `left`, then `right`, waiting about three seconds after each. Confirm
   signed motion and a tick-stamped acceptance message for each action.
5. Type `stretch`, then `squash`, again allowing about three seconds each.
   Confirm genuine height/width changes rather than whole-body translation.
6. Type `reset` and wait about five seconds. Confirm smooth recovery. Type
   `wander on` to resume autonomous motion, then `save` to finish and export.
7. Verify the saved take and export, then watch the actual media:

   ```sh
   commander-zorg verify-session outputs/mac_live_take_01/session.json
   commander-zorg verify-live-export outputs/mac_live_take_01/export/manifest.json
   open outputs/mac_live_take_01/export/player.html
   # When animation.mp4 was produced:
   open outputs/mac_live_take_01/export/animation.mp4
   ```

8. For a separate offline export, choose a new path:

   ```sh
   commander-zorg render-session outputs/mac_live_take_01/session.json --out outputs/mac_live_video_01
   open outputs/mac_live_video_01/player.html
   ```

9. Run another take, submit a malformed command, resize the terminal and press
   Ctrl+C. Confirm the prompt and cursor return, ordinary typing works, the
   session says `interrupted`, and `verify-session` accepts its captured prefix.
   Use another new take to check `quit` without automatic export.

Record the terminal version, macOS version, Python version, achieved FPS and
observations alongside the resulting session. Watch the full exported sequence
for smooth motion, visibility, clipping and response timing. Creator judgment
about the animation remains separate from automated numerical validation.
