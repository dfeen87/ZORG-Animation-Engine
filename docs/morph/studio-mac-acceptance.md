# Native MacBook acceptance — pending execution

Linux PTY emulation and hosted macOS are separate evidence from this native
Terminal.app/iTerm2 review. Record OS version, terminal app/version, shell,
window size, TERM/COLORTERM, Python executable, imported module path, dependency
versions, FFmpeg/ffprobe versions, tested commit and logs. Never paste secrets.

```sh
git fetch origin
git switch feature/chromatic-motion-studio
git pull --ff-only
brew install python@3.12 ffmpeg
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m pip check
python -c 'import sys,commander_zorg; print(sys.executable); print(commander_zorg.__file__)'
python -m pytest -q --junitxml=outputs/mac-pytest.xml
commander-zorg morph-lab --record outputs/mac_creator_01
```

Use a new take directory. Enter `color on`, `palette auto`, `motion auto on`,
`motion normal`, `speed normal`, `wander off`, `morph oval .5`. Wait three
seconds; observe restrained teal pixels. Enter `morph cloud 2`; confirm a smooth
blue transition without flash, flicker or silhouette changes. Allow settling,
then `up`. Choose `motion bold`, enter `up` again, then repeat after settling.
Expect one larger/adapted endpoint followed by an honest limit with no new
executed event. `down .05` explicitly moves toward an interior absolute target.
Try `motion gentle` and `speed slow`; explicit numeric arguments still override.

Enter `palette cloud`, then `morph circle 2` to check persistent override;
`palette auto` resumes shape colors. Interrupt a morph with another morph and
look for continuous color. Direction/shape/wander combinations may truthfully
hit admission limits; slower speed does not authorize unsafe deformation.

Test Terminal.app's normal xterm-256color environment without forcing
COLORTERM. Confirm coherent quantized blue rather than gray. Test iTerm2 with
its actual advertised truecolor settings. Record these independently. Repeat a
fresh take with `--mono`, confirming familiar light blocks. Resize to narrow
and tiny windows, then restore width; input and status must stay usable, no
scrolling ANSI garbage, half-block foreground/background correct.

Capture with `capture Mac_cloud`, then `save`. Confirm echo, cursor and normal
screen restored. Inspect the RGB PNG capture, `export/player.html`, MP4 if
encoded, and run:

```sh
commander-zorg verify-morph-session outputs/mac_creator_01/session.json
commander-zorg verify-morph-export outputs/mac_creator_01/export/manifest.json
commander-zorg render-morph-session outputs/mac_creator_01/session.json --out outputs/mac_gray_01 --grayscale --no-mp4
python scripts/demo_chromatic_cloud.py --out outputs/mac_cloud_demo_01
```

In fresh takes, test `quit`, Ctrl+C, save, and an invalid command. Terminal
settings must restore after every exit. Review all Pytest outcomes/JUnit;
a green exit alone does not prove zero skips. Use `scripts/ci.py run` with its
passive outcome report and `audit-tests` for strict inventory acceptance.
Preserve a failure's traceback/session; never increase timeouts to hide a hang.

Creator decision still required: approve or revise the actual blue cloud's
silhouette, palette coherence, visible pixel texture, pacing and movement.
These artistic judgments are not asserted by numerical test success.
