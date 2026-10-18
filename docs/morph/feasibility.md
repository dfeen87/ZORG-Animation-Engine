# Checkpoint A/B — expressivity study

Study completed before implementing morph commands, on main a81a93ab8c33d42b08a23329bc815b99969b9282. Baseline: 642 passed, zero failed/errors/skips; complete Build 0 experiment and exact replay passed in outputs/onboarding_build0. The original live demo also passed all gates. Reproduce the geometric study with `python scripts/study_morph.py` from the installed checkout.

[Same-scale 384×384 contact sheet](study/contact_sheet.png) and [measurements](study/measurements.json) are actual evaluations of the unchanged separable-yx-weight-sum-v1 field. No images drive the geometry. Eight sorted IDs, original weights, sigma and threshold remain fixed. Coordinates use world half-height units; targets serialize offsets relative to each original home position. Area is not conserved.

| Target | Construction | Width/height | Admission bias maximum | Assessment |
|---|---|---:|---:|---|
| home | Original positions | 0.7125 | 0 | Numerically valid; familiar baseline |
| circle | Co-locate all radial kernels | 1.000 | 2.906 | Numerically valid and visually promising |
| oval | Vertical spine with paired small kernels | 0.551 | 2.161 | Numerically valid and visually promising |
| cloud | Broad side lobes, middle peak, raised shoulders and centered lower fill | 1.798 | 4.446 | Numerically valid with three upper peaks; visually promising, creator interpretation pending |
| hill | Broad horizontal pair, shallow central crest | 1.735 | 4.205 | Numerically valid, broad/low; lower notch makes landscape interpretation ambiguous |
| head_base | Short tapered spine | 0.726 | 1.411 | Numerically valid but artistically ambiguous; excluded from recipe library |

All six are nonempty, unclipped at full resolution. Circle/oval aligned IoU is 0.651; cloud/oval 0.458; hill/cloud 0.787. Head/home IoU is 0.901, too close for a useful initial vocabulary. The circle field is analytically radial because all centers coincide; raster symmetry is exact here. No extra field parameters or elements are necessary for these candidates. Positive sums cannot subtract cavities; small kernels are swallowed by nearby large ones and sharp edges/fine interior linework are poorly supported. These are soft silhouettes, not faces, characters or scenery.

Admission checks must cover *combined* translation, squash/stretch, wander and recipe biases against the original 6-unit per-control force bound. Runtime displacement/speed guards stay active. Feasibility of isolated endpoints does not prove all interactive combinations safe. Reject commands conservatively rather than clamp state or widen bounds.

The next implementation will keep the baseline spring integrator and add a separately versioned, quintic-blended target-offset channel. Supersession continues the current target trajectory without resetting committed physics. A target label expresses authored intent. Creator approval is pending for every candidate; no classifier or learned inference is involved. The smallest next research experiment is explicit manual spacing of the hill's lower controls to reduce its notch, rather than a new representation.

The first cloud candidate had rounded shoulders but only one upper contour peak. It was rejected as insufficiently multilobed. `study/cloud_initial.png` and `measurements_initial.json` retain that attempt. A bounded explicit spacing study moved the broad kernels farther apart, raised the shoulders and moved the lower pair toward the center. The final cloud has three upper peaks after a fixed nine-column contour smoothing, one connected component, no clipping and force bias 4.446 < 6. The result is evidence of additional geometric expressivity, not proof of cloud recognizability. No field-parameter extension was needed.
