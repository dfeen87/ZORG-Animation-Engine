# Executed Build 0.2 evidence

Final commands, from the Python 3.12 editable installation:

```sh
python scripts/run_build0.py --out outputs/build02_final_regression
commander-zorg morph-demo --out outputs/morph_build02_final
python scripts/check_morph_demo.py outputs/morph_build02_final/video/manifest.json --report outputs/morph_build02_final/check_report.json
commander-zorg verify-morph-session outputs/morph_pty_final/session.json
```

The first command passed all 716 tests and all complete Build 0 experiment gates. The demo checker passed all geometric and replay gates over 600 frames, 1,201 states and six captures. `morph-demo.mp4` and `demo-contact-sheet.png` are copies of actual exports. `demo_session.json` is a self-contained morph recording, not a substitute for frame evidence. Use `commander-zorg render-morph-session docs/morph/results/demo_session.json --out outputs/NEW_EXPORT` to regenerate the complete PNG sequence, HTML player and state/capture evidence with the same source and supported environment.

`demo_check.json`, `build0_profile_report.json`, `build0_status.json`, `tests/`, `pty_acceptance.json` and `target_performance.json` retain executed measurements. The full local takes remain in ignored `outputs/`. Creator artistic review and native MacBook acceptance are pending; neither is implied by numerical passes. See the implementation report for tolerance rationale and limitations.
