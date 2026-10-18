# ZORG Build 0.2 — explicit semantic morphing

One positive Gaussian medium, eight stable element identities, creator-authored recipes. No learning, external services, inference or raster replacement. Target names describe artistic intent; creator approval is pending.

Read the [feasibility study](feasibility.md), [architecture decision](architecture.md), [implementation report](implementation-report.md), and [same-scale targets](study/contact_sheet.png).

## Install and run

Use the existing checkout. Cloud tasks are already isolated; do not create a worktree unless requested. Python 3.12 is required.

```sh
cd /workspace/ZORG
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-build-isolation --no-deps -e .
python -m pytest -q
commander-zorg morph-lab --scene scenes/live_lab.json --targets morph_targets --seed 172026 --record outputs/my_morph_take --mono
```

Inside the ANSI terminal:

```text
morph circle
capture My_circle_01
morph oval 2.0
up 0.05
morph cloud 4.0
left 0.05
capture Cloud_attempt_01
morph home
save
```

`morph NAME [seconds]` accepts 0.5–10 seconds (default 2), rounded to nearest 60 Hz tick, half up. This is the target blend duration; the physical spring continues settling afterward. A command never teleports or resets committed physics. `capture LABEL` records the current committed geometry, velocities, tick, active target and motion channels; it does not claim that a transition has settled. Labels preserve case and must start with an ASCII letter, followed by letters/digits/underscores, at most 64 characters. Labels must be unique within a take.

The original directions, squash/stretch, wander, reset, help, save and quit remain available. Translation and named shape use separate channels. Squash/stretch remains a separate home-relative offset channel. `reset` returns all channels to home and turns wander off; `morph home` changes only the named-shape channel, retaining translation and wander. For exact original geometry use reset and allow settling. Ctrl+C retains an interrupted recording and restores the terminal.

The original force budget is finite. For example, `up` with default strength 0.3 can be rejected when a circle already places the lower controls far from their original homes. Use strengths such as 0.05, reduce the shape excursion, or turn wander off and let its blend complete. Rejection preserves the prior channels, event sequence and committed state; no clipping or silent force scaling is used. Some combinations remain impossible under the original bounds.

## Replay and export

```sh
commander-zorg verify-morph-session outputs/my_morph_take/session.json
commander-zorg render-morph-session outputs/my_morph_take/session.json --out outputs/my_morph_video
commander-zorg verify-morph-export outputs/my_morph_video/manifest.json
commander-zorg morph-demo --out outputs/morph_demo_01
python scripts/check_morph_demo.py outputs/morph_demo_01/video/manifest.json --report outputs/morph_demo_01/check_report.json
python scripts/run_build0.py --out outputs/build0_regression_01
```

All output directories/reports must be new. PNGs and the standalone `player.html` are authoritative viewing outputs. FFmpeg/H.264 MP4 encoding is optional (`--no-mp4` skips it). Open the exported player from a local file browser. Preview pixels never feed simulation or offline rendering.

A session embeds the exact config, recipe library, tick-ordered events and captures, with source/environment and trajectory hashes. `events.jsonl` is a live journal; the closed, hashed `session.json` is self-contained. A process killed before finalization leaves a running marker and diagnostic journal, not a completed session. No automatic crash recovery is claimed. Failed sessions are not replayable successes. Interrupted closed sessions are verifiable prefixes.

Export preserves all numerical states, channels, target labels, complete 30 FPS frames, per-frame geometry, captures with mathematical JSON and PNG hashes, a contact sheet, player, optional MP4, status and an artifact index. `load_capture(path, config)` validates and reconstructs the committed numerical state and verifies its PNG. Captures are intentionally not promoted automatically into recipes. Importing active channel continuation from a standalone capture is not a CLI feature; replay its parent session to reproduce the entire motion history.

Exact replay requires the same source and recorded environment. Old Build 0/0.1 schema semantics and verification remain unchanged; their source-sensitive replay honestly rejects a changed engine checkout. Keep the original source/snapshot to verify historical takes, or regenerate new evidence. Hashes establish integrity, not authorship signatures.

## MacBook terminal acceptance

Native macOS has not been tested here. On Python 3.12, install the locked dependencies as above, run the full suite, then generate a fresh local morph demo. Open its player, inspect the full film, and run the demo checker. Same-environment replay is the claim; cross-platform bitwise PNG identity is not promised.

In Terminal.app and/or iTerm2:

1. Start `morph-lab --mono` in a normal ANSI terminal. Confirm the silhouette animates and the tick counter advances.
2. Enter the sequence above, waiting for each form to settle; confirm the cloud's upper contour has three lobes and movement remains independent of shape.
3. Capture during a transition and again after settling, using distinct case-preserving labels. Verify the captured previews correspond to those exact ticks.
4. Try an unknown target, unsafe label, duplicate capture and over-budget motion. Confirm clear rejection and continued animation.
5. Resize both very small and large; use backspace, help, save, quit and Ctrl+C in separate takes. Confirm terminal echo, cursor and alternate screen are restored in every exit mode.
6. Verify and export the saved and interrupted takes. Confirm 384×384 PNGs and 30 FPS timestamps, player scrubbing and optional MP4. Check measured preview FPS rather than assuming a guaranteed rate.

Creator checklist: Are circle and oval visibly distinct? Does cloud read as a cloud rather than a decorative blob? Is hill useful despite its lower notch? Are transitions fluid in the complete film? Does home feel restored? Which captures deserve intentional future promotion? Record approval/rejection separately from automated geometry gates.

## Optional adaptive directional motion

Use `motion auto on` to select the strongest feasible translation along the
bounded segment toward a requested direction; `motion auto off` restores strict
admission. Strict mode remains the default. See [adaptive motion](adaptive-motion.md)
for the algorithm, versioned recording contract, measured demo and MacBook checks.
