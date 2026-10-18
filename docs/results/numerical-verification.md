# Numerical verification report

All baseline acceptance thresholds below are unchanged. Results belong to
`outputs/build0_take_01`; engineering acceptance is separate from creator review.

| Check | Measured | Required | Outcome |
| --- | --- | --- | --- |
| Output schedule | 180 frames, ticks 0,2,…,358 | exact | pass |
| Committed schedule | 361 states, 360 ACCEPT transitions, terminal tick360 | exact | pass |
| Invalid accepted states/rejections/nonfinite fields | 0 | 0 | pass |
| E1 occupancy range | 0.159206814236–0.162333170573 | 0.03–0.65 every frame | pass |
| Clipped output frames | 0 | 0, including antialiasing in outer two pixels | pass |
| Target excitation | 0.131869962308 world units | >=0.05 | pass |
| Minimum centroid-aligned IoU | 0.883546414675 | <=0.90 during disturbance | pass |
| Distinct decoded E1 frames | 101 | >=10 | pass |
| Max anchor error, ticks330–360 | 1.12620118389e-05 | <=0.01 all31 states | pass |
| Max speed, ticks330–360 | 3.41496263922e-05 | <=0.02 all31 states | pass |
| Minimum recovery-frame IoU | 1.0 | >=0.98 all15 rendered tail frames | pass |
| Maximum recovery centroid shift | 0.0 | <=0.01 | pass |
| Cue-off control | 180 identical decoded frames; state arrays invariant | exact complete control | pass |
| 60Hz analytic max position error | 0.00467983205245 | <=0.01 over2s | pass |
| 120Hz analytic max position error | 0.00232797478582 | smaller than60Hz | pass |
| Forced60/120 position discrepancy | 0.00196843635307 | <=0.01 common-time Euclidean maximum | pass |
| Forced60/120 velocity discrepancy | 0.0036049835572 world units/s | separately report; no invented threshold | reported |
| Independent scalar reference discrepancies | position0.0, velocity0.0 | <=1e-12 | pass |
| Fresh-process state/decision/pixel/PNG comparison | exact | exact recorded environment | pass |

The unforced oracle uses the closed-form damped-spring solution, independently
of the update implementation. Forced references use separate scalar loops and
explicit formulas. The profile verifier recomputes the cadence study rather
than trusting stored pass flags. Cue-off rest tests also compare raw array
bytes, covering signed-zero/bit invariance before canonical serialization.

## Executed test families

| Family | Independent coverage | Outcome |
| --- | --- | --- |
| V01 | Strict JSON duplicate keys/IDs, ranges, enums, resources, force and solver limits | pass |
| V02 | Integer frame/terminal clock, zero before update and midpoint scheduling | pass |
| V03 | Analytic Gaussian center/radius/sign and independently direct sum | pass |
| V04 | Asymmetric orientation/sample lattice, exact quantization/inversion/PNG | pass |
| V05 | Hand arithmetic, analytic spring, convergence, ownership and alias rejection | pass |
| V06 | Pulse support/peak/endpoints, overlap, per-element force, sorted order | pass |
| V07 | NaN/tick/shape/dtype/speed/displacement rejection and unchanged source state | pass |
| V08 | Full-tail recovery and synthetic frozen/final-only failure counterexamples | pass |
| V09 | Empty/full/static/translated/flipped/missing-image gate failures | pass |
| V10 | Existing output, failed write/interrupt, missing/truncated/wrong-mode PNG, sheet links | pass |
| V11 | Two fresh processes, replay, cue perturbation and seed-only invariance | pass |
| V12 | Rehashed metric/trajectory/source corruption, canonical traces, linked JUnit/report verification | pass |

The suite executed 456 passing cases with zero failures, errors
or skips. Tests overlap families intentionally; file counts below are not
independent family totals. `tests/test_experiments.py` additionally checks
forged cadence results, stale hashes and truthful JUnit totals.

| Pytest module | Cases | Result |
| --- | --- | --- |
| `tests.test_config` | 289 | passed |
| `tests.test_evidence` | 42 | passed |
| `tests.test_experiments` | 19 | passed |
| `tests.test_field` | 9 | passed |
| `tests.test_guard` | 12 | passed |
| `tests.test_motion` | 19 | passed |
| `tests.test_profiles` | 29 | passed |
| `tests.test_raster` | 12 | passed |
| `tests.test_replay` | 8 | passed |
| `tests.test_state` | 17 | passed |

Source and experiment hashes, exact commands, test-output text and JUnit XML
are retained in the final evidence and linked by its experiment manifest.
No integrity checksum is treated as mathematical correctness or artistic approval.
Creator review and native macOS acceptance remain pending.
