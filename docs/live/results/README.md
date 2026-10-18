# Build 0.1 execution evidence

The full suite passed **642 tests**: 456 unchanged Build 0 regressions and 186
new live tests, with no failures or skips. The complete Build 0 runner also
passed all E0/E1/control, cadence, integrity, replay and profile gates under the
new source snapshot. Its original scenes and numerical modules are unchanged.

The [15-second MP4](live-demo.mp4) is H.264, `yuv420p`, 384×384 and 30 FPS.
FFprobe counted 450 frames and FFmpeg decoded the entire file without errors.
The [contact sheet](demo-contact-sheet.png) samples the take; review the full
video for motion. Creator artistic approval is pending.

[Demo checks](demo_check.json) validate all 450 exported frames against their
saved mathematical states and bind the 901-state trace to the session. The
recording replays exactly in a separate process. Measurements include:

| Measurement | Result |
| --- | --- |
| Autonomous distinct pixel frames, first two seconds | 52 |
| Distinct pixel frames, complete take | 426 |
| Rightward centroid change | +0.3294 world units |
| Leftward centroid change | −0.6405 world units |
| Stretch aspect ratio relative to preceding pose | 1.4349× |
| Squash aspect ratio relative to preceding pose | 0.5059× |
| Largest control movement in one 60 Hz tick | 0.01130 world units |
| Largest image-centroid movement in one output frame | 0.02221 world units |
| Final maximum control distance from home | 0.00002688 world units |
| Empty or clipped frames | 0 |

A separate actual Linux pseudo-terminal take accepted `left` and `stretch`
while displaying live Gaussian geometry, then finished with `save`. It
recorded 420 ticks over seven simulation seconds, displayed 104 previews at
**14.84 FPS**, restored the cursor and complete termios settings, produced no
scrolling log, and replayed all 421 states exactly. Its PNG/HTML/MP4 export also
completed. See [PTY acceptance](pty_acceptance.json). Automated PTY tests cover
partial input, visible autonomous evolution and signed image displacement,
help, invalid input, resize, tiny dimensions, quit, save, Ctrl+C, EOF,
recording failures, numerical failures and finalization interruption.

Native macOS acceptance was **not run**. Follow the
[MacBook procedure](../README.md#macbook-acceptance-procedure) to test the actual terminal.
Cross-platform bitwise replay is not claimed.

[Validation summary](validation.json) hashes this compact evidence bundle and
records the exact engine-source hashes. The retained full evidence lives in
ignored `outputs/live_demo_02`, `outputs/live_pty_acceptance_01`, and
`outputs/build0_regression_live_01` in the prepared workspace. Those complete
frame/source snapshots are not included in Git. Regenerate new takes with:

```sh
python -m pytest -q
commander-zorg live-demo --out outputs/my_live_demo
python scripts/check_live_demo.py outputs/my_live_demo/video/manifest.json --report outputs/my_live_demo/demo_check.json
python scripts/run_build0.py --out outputs/my_build0_regression
```

Keep each recording with its matching source and environment. Adding the live
extension changes source provenance, so pre-extension Build 0 evidence remains
integrity-verifiable but exact replay against changed current source correctly
refuses the mismatch. The fresh Build 0 regression take above demonstrates
replay under this extension's source snapshot.
