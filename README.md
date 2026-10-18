<h1 align="center">ZORG</h1>

<p align="center">
  <strong>MATHEMATICS WITH A CAST OF CHARACTERS.</strong><br>
  <em>A deterministic animation laboratory, built for a story that hasn't reached the screen yet.</em>
</p>

<p align="center">
  <a href="https://github.com/dfeen87/ZORG/actions/workflows/ci.yml"><img alt="ZORG CI" src="https://github.com/dfeen87/ZORG/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <img alt="Python 3.12" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&amp;logoColor=white">
  <img alt="Creator Studio Build 0.3" src="https://img.shields.io/badge/Creator%20Studio-Build%200.3-7457C5">
  <img alt="Local first" src="https://img.shields.io/badge/Local--first-no%20cloud%20required-0D9488">
  <a href="LICENSE"><img alt="MIT licensed software" src="https://img.shields.io/badge/Code%20license-MIT-22A06B"></a>
</p>

<p align="center">
  <a href="#-launch-the-creator-studio">Launch the studio</a> ·
  <a href="#-watch-the-math-change-shape">See the pixels</a> ·
  <a href="#-why-zorg-exists">The story</a> ·
  <a href="#-verified-engineering">Verification</a> ·
  <a href="#-whats-next">What's next</a>
</p>

---

> **“COMMANDER!!! THE HUMAN GAVE US COLORS!!!”**
>
> **“That's very nice, Zorg. Please don't spill them on my newspaper.”**

## 🎬 Why ZORG exists

**Commander–ZORG** is an original fictional project about two aliens in a spaceship. **ZORG** is the mathematical animation engine being developed to bring that world to life.

The premise is delightfully straightforward: **create the characters through mathematics, then give the artist the tools to direct their performances.**

This is not a text-to-video service, a generative-AI model, or a finished movie studio. It is an evolving, **local Python research engine** with real, tested foundations for geometry, motion, live interaction, shape transformations, and procedural color.

**The guiding idea:**

> We are not creating a show to demonstrate an animation engine.  
> We are creating an animation engine to bring our show to life.

## 🌈 Watch the math change shape

<p align="center">
  <img src="docs/morph/studio-evidence/cloud-demo/contact_sheet.png" alt="Verified ZORG Build 0.3 contact sheet showing the oval-to-cloud chromatic animation" width="860">
</p>

| An oval | A changing form | A sky-blue cloud |
| :---: | :---: | :---: |
| <img src="docs/morph/studio-evidence/cloud-demo/starting_oval.png" alt="ZORG starting oval" width="235"> | <img src="docs/morph/studio-evidence/cloud-demo/transition_50.png" alt="ZORG halfway through its blue cloud transition" width="235"> | <img src="docs/morph/studio-evidence/cloud-demo/sky_blue_cloud.png" alt="ZORG procedural sky-blue cloud" width="235"> |

These are **actual committed Build 0.3 demonstration frames**, not concept art. The source-backed demo recorded **841 simulation states, 420 RGB frames, and five captures**. Its exact replay and export checks passed in the recorded development environment. See the [demonstration and evidence](docs/morph/studio-demo.md).

The shapes and their colors are mathematical. The clouds have *not* been approved as final character artwork; creator visual review is still part of the process.

## 🚀 Launch the Creator Studio

**Requirements:** Python **3.12**, a Mac or Linux terminal, and access to this private repository. FFmpeg is optional for local MP4 exports; PNG and HTML playback do not require it.

```bash
git clone https://github.com/dfeen87/ZORG.git
cd ZORG
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .

# A fresh recording destination is required for every take.
commander-zorg morph-lab --record outputs/first_zorg_take
```

In the live terminal, enter these **one at a time**, pressing Return after each:

```text
color on
palette auto
motion auto on
motion gentle
speed slow
wander off
morph oval .5
morph cloud 2
up
capture SkyBlueCloud
save
```

**What happens?** ZORG uses a named mathematical shape recipe, transitions toward its sky-blue cloud palette, attempts a conservatively safe directional move, and records the take. The terminal previews the animation while the simulation runs on its own fixed tick schedule.

If a requested movement exceeds a numerical limit, the engine can reduce a supported directional command or reject it honestly. **It never relaxes the physics guards to make an animation “look successful.”**

On **Terminal.app**, an `xterm-256color` environment uses quantized ANSI color; terminals advertising truecolor use 24-bit color. Add `--mono` to the launch command for portable monochrome blocks. Actual creator visual acceptance on a physical MacBook remains a separate check.

### 🎛️ The creative controls

| What you want | What to type |
| --- | --- |
| Change mathematical shape | `morph circle`, `morph oval`, `morph cloud 2`, `morph hill`, `morph home` |
| Choose movement intensity | `motion gentle`, `motion normal`, `motion bold` |
| Choose transition pacing | `speed slow`, `speed normal`, `speed fast` |
| Negotiate safe direction movement | `motion auto on` (or `motion auto off` for strict mode) |
| Direct a movement target | `up`, `down`, `left`, `right` |
| Change visual presentation | `color on`, `color off`, `palette auto`, `palette cloud` |
| Control autonomous movement | `wander on`, `wander off` |
| Save a mathematical snapshot | `capture MyShape` |
| Get live command help | `help` |
| End a take | `save` or `quit` |

Named shape targets are **`home`, `circle`, `oval`, `cloud`, and `hill`**. Palette overrides also support `neutral`, `circle`, `oval`, `cloud`, and `hill`.

**Important motion distinction:** `up` and the other directions currently request **absolute local deformation targets**, **not** endless world-space travel. Repeating a saturated target can correctly report `LIMIT REACHED`. Independent movement through a spaceship is planned research, not an existing command.

Read the [motion semantics](docs/morph/studio-motion.md), [chromatic design](docs/morph/studio-color.md), and [native Mac acceptance guide](docs/morph/studio-mac-acceptance.md).

## 🎞️ Replay it. Export it. Verify it.

A recorded take contains tick-indexed instructions, state/capture evidence, configuration and integrity information. With the same recorded source and supported environment, it can be replayed and independently checked.

```bash
# After saving the take above:
commander-zorg verify-morph-session outputs/first_zorg_take/session.json
commander-zorg verify-morph-export outputs/first_zorg_take/export/manifest.json

# Or generate a fresh, fully scripted color demonstration:
python scripts/demo_chromatic_cloud.py --out outputs/chromatic_showcase_01
commander-zorg verify-morph-session outputs/chromatic_showcase_01/record/session.json
commander-zorg verify-morph-export outputs/chromatic_showcase_01/video/manifest.json
```

Open `outputs/first_zorg_take/export/player.html` locally to watch the animation, or inspect the PNG sequence frame by frame. FFmpeg with H.264/libx264 support also enables a convenient MP4.

The **grayscale geometry remains the mathematical baseline**. Seeded, material-local texture and shape-aware palette transitions are applied *after* grayscale coverage is computed, without changing the physics. Exports have their own versioned manifests; historical session contracts retain their original meanings.

**Integrity matters:** exact source/environment replay, numerical trajectories, decoded pixels and image artifacts have distinct verification responsibilities. Byte-identical PNG encoding is not promised across different platform/library builds.

## ⚙️ What's inside the engine?

| Layer | What it does |
| --- | --- |
| **Mathematical medium** | Evaluates superposed positive Gaussian influence fields and rasterizes antialiased silhouettes. |
| **Motion & safety** | Uses bounded spring dynamics, fixed simulation ticks, explicit target blends and conservative force/displacement admission. |
| **Creator controls** | Accepts named morphs, directional commands, motion/speed presets, wander, and state captures. |
| **Chromatic presentation** | Adds seeded material-local RGB texture, named palettes, and continuous color transitions without altering numerical state. |
| **Evidence & replay** | Records versioned events, captures, source/environment provenance, frame hashes, verification reports, and export manifests. |

There is **no machine learning, online API, runtime cloud dependency, GPU requirement, or sprite-based character replacement** in this pipeline.

<details>
<summary><strong>🧪 Go deeper: the original Build 0 experiment</strong></summary>

Build 0 established the field, numerical solver, grayscale renderer, integrity checks and the E0/E1 experiment system. The later studios extend that foundation rather than replacing it.

```bash
python scripts/run_build0.py --out outputs/build0_research_01
commander-zorg validate scenes/e1.json
commander-zorg render scenes/e1.json --out outputs/e1_research_01
commander-zorg verify outputs/e1_research_01/manifest.json --integrity
```

Destinations must not already exist. Rendering a valid scene does not, by itself, constitute passing every experiment/profile gate.

Explore the [implementation report](docs/results/implementation-report.md), [numerical verification](docs/results/numerical-verification.md), [E0 gallery](docs/results/e0-gallery.png), [E1 frames](docs/results/e1-contact-sheet.png), [architecture decisions](docs/adr), and [schemas](schemas/README.md).

</details>

## ✅ Verified engineering

**Build 0.3 hardening:** the [PR #9 hosted CI run](https://github.com/dfeen87/ZORG/actions/runs/39161093651) recorded **934 passing tests on Ubuntu 24.04** and **934 passing tests on macOS 15**, using Python 3.12. Both strict test-inventory audits passed with no failed, skipped, or deselected tests. Two existing Pytest warnings remained on each platform.

Those counts describe a **specific verified commit**, not a promise about future builds. The badge at the top reports the current `main` workflow status.

- [Fast cross-platform CI](.github/workflows/ci.yml) — pytest, dependency/media checks, test inventory auditing and diagnostics.
- [Manual deep validation](.github/workflows/deep-validation.yml) — broader Build 0, live, morph and chromatic evidence reproduction.
- [CI guidance](docs/ci.md) — platform scope, artifacts and failure reporting.
- [Creator Studio CI report](docs/morph/studio-ci.md) — development evidence and limitations.

**Platform CI passing ≠ finished artistic acceptance.** Terminal.app/iTerm2 color appearance, timing, texture and the final shapes still need creator review on the target hardware. The manual deep workflow is independent of the passing PR #9 fast-CI run.

## 🗺️ From mathematical potato to movie

| Milestone | Status | Focus |
| --- | --- | --- |
| **Build 0** | Implemented | Mathematical fields, springs, grayscale evidence and replay |
| **Build 0.1** | Implemented | Live terminal interaction, recording and export |
| **Build 0.2** | Implemented | Named mathematical morphs and persistent captures |
| **Build 0.3** | Implemented; artistic review pending | Creator presets, corrected admission, deterministic RGB |
| **Next research** | **Not implemented** | Object identity, local vs. world movement, multiple actors, scene/camera context |
| **Longer horizon** | **Research concept** | Radial spatial strings, symbolic cinematic direction, Commander and Zorg performing in a spaceship |

The forthcoming **radial spatial-context / Letter-Depth Encoding** investigation is a *hypothesis to examine*, not an engine feature or proven translation from prose to cinema.

## 📚 Explore the laboratory

| Area | Start here |
| --- | --- |
| Creator motion & adaptive behavior | [Motion contract](docs/morph/studio-motion.md) · [Diagnosis](docs/morph/studio-diagnosis.md) |
| Procedural color | [Chromatic architecture](docs/morph/studio-color.md) · [Demo walkthrough](docs/morph/studio-demo.md) |
| Original live animation | [Live Lab guide](docs/live/README.md) · [Saved demo](docs/live/results/live-demo.mp4) |
| Named semantic shapes | [Morph Lab guide](docs/morph/README.md) · [Morph demo](docs/morph/results/morph-demo.mp4) |
| Mathematical foundations | [Build 0 results](docs/results/implementation-report.md) · [Architecture](docs/morph/architecture.md) |
| Verification and contracts | [CI](docs/ci.md) · [JSON schemas](schemas/README.md) |

## 📜 License & creative ownership

Code in this repository is distributed under the [MIT License](LICENSE), with the original software attribution preserved. **The MIT software license does not automatically grant rights to the original Commander–ZORG characters, scripts, story bible, fictional setting, or third-party creative assets.**

This is a personal, evolving research and creative project. The code is real; the finished film is still ahead of us.

---

<p align="center">
  <strong>LET MATHEMATICS DISCOVER THE CHARACTERS.</strong><br>
  <em>Let cinematic intention reveal their personalities.</em><br><br>
  <strong>Design top-down. Verify bottom-up. Release with evidence.</strong>
</p>
