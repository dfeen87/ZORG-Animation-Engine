# Build 0.2 implementation evidence

Implemented on `feature/semantic-morphing-build02` from main `a81a93ab8c33d42b08a23329bc815b99969b9282`. Creator artistic approval and native MacBook acceptance remain pending. This is explicit mathematical construction and curation; no machine learning or external AI services are used.

## Demonstrated behavior

The eight-element positive Gaussian representation produces distinct circle, vertical oval and three-peaked cloud candidates using position changes alone. Home and a broad low hill are also available. The head-like study is numerically valid but too similar to home and is excluded. No weights, sigma, threshold, element count, baseline scene, historical test or original field arithmetic changed.

`morph-lab` accepts bounded named transitions and historical motion commands through independent channels. Supersession preserves committed positions/velocities and current target positions. Conservative combined force admission can reject large directional movements with wide shapes; `.05` directions were demonstrated with wander and morphing. The unchanged spring integrator checks every committed tick. Target blend completion and physical settling are separate.

`capture LABEL` saves exact committed mathematical state and active channels with seed/config/source provenance and content ID. Export generates previews from those recorded states. Case-preserving labels, duplicate protection and path restrictions are enforced. The loader verifies capture contents and reconstructs numerical state; session replay reconstructs the entire channel history. Automatic promotion is deferred because translation/wander must be reviewed explicitly.

## Executed checks

Baseline before changes: **642 passed**, zero failed/errors/skips; complete E0/E1/control/cadence/integrity/exact replay/profile gates passed. The original live demo passed its full geometry/integrity check.

Final suite: **716 passed**, zero failed/errors/skips: the 642 historical tests ran unchanged and 74 new tests cover recipe rejection, identity correspondence, independent scalar Euler verification, deterministic transitions, home recovery, supersession, translation/wander coexistence, admission rollback, force rejection without repair, captures/reload, provenance tampering, exact replay, PNG-state correspondence, corrupted and reindexed evidence, interrupted recordings and real PTY quit/save/Ctrl+C restoration.

The complete Build 0 runner was executed after the extension, including all tests, six E0 candidates, 180-frame E1 and cue-off control, independent cadence study, fresh-process replay and complete profile verification. See [tests](results/tests/test_report.json) and the saved Build 0 result summaries. No historical test was weakened.

All four new JSON Schema documents passed Draft 2020-12 structural validation; actual final evidence validated: five targets, 12 events, six captures and one closed session. Runtime checks additionally enforce relational, finite-number, force, provenance and chronology constraints.

An initial added PTY test failed because its child lacked a controlling terminal. The harness was corrected to establish terminal ownership and drain output while waiting for restoration. The final PTY tests pass. No engine behavior was weakened to address that failure.

## Morph demonstration

The 20-second sequence uses the same runtime and event handling as interactive commands:

- 0–3 seconds: autonomous original form.
- At 3 seconds: fade wander off and morph to circle.
- At 6 seconds: morph to oval.
- At 9 seconds: morph to cloud.
- At 13 seconds: morph to hill.
- At 16 seconds: morph home, ending at 20 seconds.

Each target blend lasts 0.5 seconds, followed by physical settling. All 1,200 fixed-tick transitions execute; export has **1,201 states and 600 full-resolution 384×384 PNG frames at 30 FPS**. Six tick-stamped captures and 12 ordered events are preserved in the [self-contained recording](results/demo_session.json). Exact same-environment numerical replay, every PNG against reconstructed mathematical state, capture previews, artifact integrity and geometry gates passed. MP4/H.264 encoding succeeded.

Watch the [complete film](results/morph-demo.mp4), inspect the [labeled contact sheet](results/demo-contact-sheet.png), and read the [full measured report](results/demo_check.json). Complete PNG/HTML/state/capture evidence is retained in `outputs/morph_build02_final/video`; regenerate with the documented commands to obtain another complete take. Reports and preview film are committed; the full regenerable raster sequence stays in ignored outputs.

| Check | Measured result |
|---|---:|
| Empty / clipped / disconnected frames | 0 / 0 / 0 |
| Circle width/height | 1.000 |
| Oval width/height | 0.551 |
| Cloud upper contour peaks | 3 |
| Hill width/height | 1.735 |
| Largest endpoint control error | 0.000794 world units |
| Return-home control error | 0.0000436 world units |
| Maximum per-tick control step | 0.010107 world units |
| Maximum per-frame centroid step | 0.008161 world units |
| Circle/oval aligned IoU | 0.650 |
| Cloud/hill aligned IoU | 0.787 |

Endpoint tolerance is two 384-pixel world pixels (~0.01042), chosen to ensure close geometric recovery. Circle aspect tolerance is 4%; oval <0.65, hill >1.6; cloud has at least three upper peaks after a fixed nine-column moving average. Pairwise aligned IoU below 0.90 excludes near-identical shapes. These tests establish geometric distinctions, not semantic recognition or artistic approval.

The initial cloud candidate failed the contour distinction check. Its evidence is retained in the study directory; manual spacing and centered lower controls produced the accepted candidate without changing the representation.

## Performance and limits

A 100×30 Linux pseudo-terminal ran 424 ticks over 7.083 wall seconds, displaying 104 previews at **14.68 FPS**. Oval, upward motion, cloud, leftward motion and two captures were accepted; terminal settings and alternate screen were restored; 425 states replayed exactly. See [PTY evidence](results/pty_acceptance.json). This is a measured machine-specific result, not native macOS acceptance or a universal FPS promise.

The target-offset microbenchmark measured approximately 19.94 µs per historical live evaluation and 27.82 µs with the new shape channel (median of three 20,000-call runs). The added cost is ~7.88 µs against a 16,667 µs simulation tick budget. This excludes raster evaluation and command admission; see [method and values](results/target_performance.json). Offline timings and source/environment details are in the complete local export manifest.

All five accepted recipes retain the same control identities and static field parameters. No new topology is required for these forms. Positive-only kernels cannot carve holes by subtraction and struggle with corners, fine linework and internal facial features. The circle and oval are visually promising; cloud is visibly multilobed and promising, with human interpretation pending; hill's broad low profile is useful geometrically but its lower notch makes landscape interpretation ambiguous. `head_base` remains excluded. No convincing face, full landscape, physical realism, mathematical novelty or universal real-time guarantee is claimed.

The smallest next mathematical experiment is manual redistribution of hill's lower pair to reduce its notch while keeping current field arithmetic and limits. Any extra elements, signed influences or parameter variation requires another versioned study. Reviewed capture promotion can follow after defining how motion channels are removed; it is not automatic knowledge acquisition.

Historical recordings remain subject to their original source-provenance checks. Changed source correctly prevents exact verification of old recordings from this checkout. The baseline validation was performed before any modifications, and fresh baseline experiments were regenerated after implementation.
