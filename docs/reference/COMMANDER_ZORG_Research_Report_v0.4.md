# Predictive Animation Phase Memory and Emotional Color Research Report

Version 0.4 | 18 October 2026 | Deliverable C | Private research

## Reading guide

Sections 1 to 10 cover temporal models, experiments, identity and cinematography. Sections 11 to 15 audit AILEE and the coauthored Phase-Memory sources. Sections 16 to 23 cover color, safety and the other upstream systems. Sections 24 and 25 complete the color code examples and research decisions. All external references were accessed on 18 October 2026.

## 1 Research decision and evidence status

The proposed Temporal Memory Observer (TMO) and Predictive Motion Conditioner (PMC) have a credible mathematical path to testing, but neither has demonstrated an artistic benefit. Start with the existing spring state, then an observation-only exponential average, then a small explicitly bounded control experiment. Scripted anticipation is a different information condition from extrapolation of past motion. Indexed emotional color can be tested independently, using an immutable palette, explicit script selections, a temporal intensity controller and localized linear-light compositing. The camera addendum belongs to a separate future study of persistent landmarks and framing.

All new subsystems in this report are research proposals outside Build 0. No animation engine, memory controller, color renderer or procedural camera was implemented for this audit. Documentary code blocks are proposed implementation sketches, not executed or validated implementations. Algebra and workload arithmetic are derived here; source inspections are identified by pinned revision; inherited v0.3 scalar probes are not new v0.4 measurements. No improvement in fluidity, humor, storytelling, performance or safety has been measured.

The authoritative supplied source is `COMMANDER_ZORG_Architecture_and_Prototype_v0.3.docx`, SHA256 `3d367ddc9b0a4ec239d00889b4efd8f11a756521af8b49f79dcf8569676ab1fc`. Body paragraph locators include blank paragraphs. Tables and Office Math were read separately because ordinary paragraph text omits equations. v0.1 and v0.2 remain higher historical sources for their respective roles; statements about them here are inherited through v0.3 unless independently identified. The current assignment Section 0 and cinematography addendum introduce the new research. They do not authorize Build 0 expansion.

## 2 Distinguish four kinds of temporal information

Ordinary state consists of positions and velocities. In the specified Markov spring model, current state and future external force determine subsequent state. Different earlier histories that arrive at the same state have the same future under the same force. An added memory can create a new expressive behavior, but it does not recover missing deterministic spring physics.

Historical observation compresses previous measurements. It can estimate recent intensity or recovery and establish a character response that depends on more than the current pose. Prediction estimates motion unavailable at the current tick, with forecast errors. Script anticipation consumes future events explicitly available in the saved script; it is lookahead with known information, rather than evidence that a history model can predict surprises.

Phase diagnostics compare qualified oscillatory signals against a declared reference. They are neither ordinary pose state nor a generic name for smoothing. A nonoscillatory single surprise pulse does not automatically possess a scientifically useful instantaneous phase. A numerical phase value from a transform is insufficient without amplitude, signal quality, causality and reference qualification.

## 3 Shared expressive state with independent channels

Propose an immutable `ExpressionCue` record carrying character ID, script cue ID, exact tick boundaries, authored intensity, optional color ID, priority, target region IDs, anticipation permission and source provenance. A resolver creates separate typed controls for geometry, motion and color. A future camera consumes a separate cinematic directive and optional expression annotation. The field evaluator receives numeric geometry only and never interprets words such as suspicion or COMMANDER.

Channel controllers own their own state and time constants. Motion can be at rest while a color intensity decays slowly. Color can be deliberately absent during agitation. A scripted discovery may illuminate a localized feature while its geometry stays fixed. The common cue does not require one oscillator, one damping coefficient or one shared memory scalar to drive everything.

Pure future interfaces, to be designed after Build 0, are:

```text
# Proposed interface pseudocode
# Proposed interfaces only; not engine code and not executed.
resolve_expression(script_cues, tick, character_profile) -> ExpressionControls
observe(committed_motion, previous_observer, observer_config) -> ObservationState
predict(motion, observation, allowed_future_cues, model) -> Prediction
condition_motion(base_control, prediction, policy) -> MotionControl
resolve_color(expression, palette, previous_color, policy) -> ColorControl
resolve_features(committed_geometry, feature_definitions) -> FeatureObservations
compose_camera(features, cinematic_cues, previous_camera, policy) -> CameraState
```

Use plain dataclasses and arrays when these experiments are authorized. There is no present need for a plugin framework. Each channel can be disabled. Disabling a channel must produce its baseline without stale caches or hidden state. Do not add empty implementation classes to Build 0.

## 4 Temporal Memory Observer

### 4.1 Compact measured features

Let control i have root-local displacement z_i, velocity v_i and model acceleration a_i. Define positive authored scales d*, v*, a*. Candidate bounded observations include displacement norm divided by d*, speed divided by v*, acceleration norm divided by a*, and an explicit script intensity. Use a bounded mapping such as r/(1+r) for nonnegative normalized r; record the mapping and scales. Boundedness does not make a scale meaningful: use measured baseline distributions to select them before a confirmatory comparison.

Signed per-axis velocity averages can cancel opposite movements. Retain a separate nonnegative speed or energy-like channel when activity matters. A physical mechanical energy is E = sum_i (m_i ||v_i||² + k_i ||z_i||²)/2 for independent springs; it is a useful numeric diagnostic, not an emotion score. Root translation must be separated before future locomotion experiments. Current Build 0 has a fixed root.

The model acceleration is available from current state and force. Finite differencing velocities amplifies noise and should be a separately labeled measurement if used. Use committed states only; a rejected candidate must not contaminate retained history. The observer operates on float64 compact state, never on stored full-resolution images.

### 4.2 Time-consistent exponential history

For sample interval Δ and memory time constant τ > 0, use the following proposed exact update for a held observation x_k:

$$\beta=\exp(-\Delta/\tau),\qquad m_{k+1}=\beta m_k+(1-\beta)x_k.$$

This derives from the first-order filter dm/dt = (x−m)/τ with x constant over the interval. For x and m in [0,1], the update is a convex combination and remains in [0,1]. It gives a time parameter in seconds rather than a frame-dependent arbitrary coefficient. NIST describes ordinary exponentially decreasing weights and the significance of initialization; the continuous-time coefficient here is our filter derivation, not a new NIST animation result. [NIST single exponential smoothing](https://www.itl.nist.gov/div898/handbook/pmc/section4/pmc431.htm).

For variable sample intervals, use the actual integer-tick elapsed time. This preserves decay for a held signal; changing sample rate still changes the approximation to a varying input. There is no claim that 15 Hz and 120 Hz observation are identical. Avoid computing `1-exp(-x)` by cancellation for tiny x; a later implementation can use `-expm1(-x)`.

Initialize to a declared neutral m_0=0 for an at-rest scene or to the first observation for warm starts. These choices have different startup transients. No silent prehistory is allowed. A reset is an explicit logged event tied to a scene boundary, cut or creator directive; retain cross-scene history only with deliberate narrative permission.

After the observation becomes zero, m decays by exp(−t/τ). It never reaches exact zero mathematically. Define a finite stopping policy: once below ε and without authorized future activity, set exactly zero and record that deterministic policy. Required waiting time satisfies t ≥ τ ln(m_initial/ε), for m_initial > ε. A color persistence tail should not silently postpone a mandatory motion recovery gate.

### 4.3 Finite windows and compression

A rectangular average over K observations is m_k = (1/K) sum_{j=0}^{K−1} x_{k−j}. Maintain a ring buffer and running sum for O(d) update and O(Kd) storage for d features. At startup either divide by the actual count or include neutral padding; choose one. Running sums accumulate rounding error, so a deterministic periodic re-sum may be specified. A finite window gives exact finite forgetting, but introduces a sharp change when an old event leaves the window and latency near (K−1)Δ/2 for slowly changing signals.

Weighted finite windows allow a smoother exit, at O(Kd) work unless a recursive structure is derived. A two-state exponential cascade can smooth derivatives with O(d) state, but increases lag. A maximum, quantile or variance carries different information and requires its own validation. Do not retain many correlated features simply because they are cheap.

Compression choices include character-level aggregate channels, a few semantic region channels, or per-control channels. Begin with two to four scalars per character. Aggregation loses which feature moved; per-region observation is justified only when that distinction affects a testable artistic requirement. Quantization can save storage later but may cause threshold chatter. Float64 at this scale is simpler.

### 4.4 Sampling and cost

Sample at integer tick divisors, initially every tick for compact signals or every two to four ticks for a low-frequency observer. At 60 Hz these latter rates are 30 and 15 Hz. These are experimental choices, not guarantees against aliasing. Downsample only after appropriate filtering when higher-frequency components are present. The observation sampling rate must exceed twice the highest retained signal frequency, and practical filters need transition bandwidth. The spring natural frequency sqrt(14)/2π ≈ 0.596 Hz does not bound frequencies introduced by cue changes, geometry, sampling or faults.

For twelve controls with two-axis position, velocity and acceleration, six channels per control give d=72. A two-second 30 Hz window uses 60×72×8 = 34,560 bytes of float64 samples, excluding object overhead; an EMA stores 576 bytes for 72 channels. Two aggregate scalars use 16 bytes. Computing these is O(N), compared with O(NWHs²) field accumulation. These arithmetic counts establish plausible scale, not negligible measured latency or real-time performance.

## 5 Predictive Motion Conditioner

### 5.1 Predictors and their information sets

The simplest forecast is constant velocity, p_hat(t+H)=p(t)+Hv(t). Constant acceleration adds H²a(t)/2, assuming acceleration stays approximately constant. Both can fail at force onset, cue reversal, near recovery or with a noisy derivative. A normalized prediction residual should be measured at realized future time, not claimed from an apparently smooth forecast.

For this known spring, model rollout using the same state and explicitly authorized future cue schedule is a stronger baseline. Over an integer horizon L, repeatedly apply an independent forecast transition to a scratch state without committing it. Its cost is O(LN), not O(LNWH). It predicts the same model rather than learning a character. If it uses the same erroneous implementation as the renderer, self-consistency is not independent correctness; retain analytic tests and a separate validation oracle.

Use three declared modes: `history_only` receives past and present observations and assumes a documented future force; `known_script` may read saved future cues within a fixed horizon; `none` has no predictive correction. A withheld surprise event is not allowed to leak through a precomputed feature array. An offline full-clip diagnostic may be useful for editing, but it cannot be reported as causal runtime prediction.

### 5.2 Where to apply a correction

Rank options by complexity and interpretability:

1. Authored anticipation cues without PMC. They offer exact artistic control and add no inference model.
2. Modify a bounded future expression target or a predeclared cue gain in a separate experimental schema. The geometry integrator remains unchanged.
3. Add a separately capped force correction, with new load/runtime force accounting and stability analysis.
4. Alter stiffness, damping, sigma, weight or direct positions. These change recovery, topology or state continuity and complicate attribution. Defer unless the simpler options fail.

For a future target-based controller, a proposed offset is δr_n = δ_max tanh(K e_pred,n), applied componentwise with a documented norm cap afterward, where e_pred is a scaled forecast feature error. The correction must have explicit units. A smoother controller state can follow it:

$$c_{n+1}=\rho c_n+(1-\rho)\,\delta r_n,\qquad \rho=\exp(-h/\tau_c).$$

Then r_n = r_authored,n + g_n c_n, with g_n a smooth permission envelope. This is a proposed change for a future target controller; Build 0 retains its original force cues. A smootherstep g(u)=6u⁵−15u⁴+10u³ has zero first and second derivatives at its endpoints. Multiplying by a smooth envelope cannot repair an already discontinuous c or conflicting target selection automatically.

Use radial saturation to cap vector magnitude rather than applying unrelated axis caps and assuming the Euclidean limit is obeyed. Bound correction size, rate and horizon; log desired and realized correction. Runtime finite arithmetic and limits remain hard guards. No predicted target may overwrite committed geometry or bypass the numeric guard.

### 5.3 Closed-loop stability is an additional problem

The v0.3 unforced update for one coordinate has state matrix

$$M=\begin{bmatrix}1-A&h(1-D)\\-A/h&1-D\end{bmatrix},\quad A=h^2k/m,\quad D=hc/m.$$

Its trace is 2−A−D and determinant is 1−D. The Schur conditions reduce to A>0, D>0, A+2D<4. Those conditions certify this uncoupled linear recurrence only. A new memory/PMC feedback path creates an augmented matrix involving z, v, observer state and correction state, with possible sample delays. Reusing the original scalar bound would be unjustified.

A proposed linear local experiment writes X_{n+1}=M_aug X_n+B u_n and verifies every eigenvalue magnitude strictly below one with margin across the declared parameter grid. For a delayed observer, include all delay states. Use induced-norm or a discrete Lyapunov analysis for robustness where possible. A spectral-radius test at one operating point is not a proof for every nonlinear saturation regime, switching event or cadence.

A bounded external correction to a stable linear spring gives bounded state under the usual finite-dimensional fixed-system assumptions. It does not establish convergence to home: a nonzero sustained correction can leave a steady offset. If it is fed back from the state, its boundedness alone still does not prove asymptotic stability or good recovery. To recover to the original home, expire authorization, drive correction to zero, and verify the tail at every required sample. Gating based on thresholds can chatter; add declared hysteresis or continuous blending and test boundary cases.

The least risky first PMC study is feedforward anticipation of known script cues with a strict small horizon and no closed-loop adaptation. A history-conditioned controller should follow only if the observer shows information beyond current pose and velocity. Test forecast error independently from expressive benefit: an accurate forecast can make the character feel mechanical, and a deliberately stylized anticipation can be useful without being a better predictor.

### 5.4 Character signatures and parameters

An authored character profile can specify τ_memory, correction gain, horizon, recovery delay, cue intensity range and color persistence. A cautious Commander might retain a slow color tail while the motion settles quickly; Zorg might have a faster authored anticipation. These are provisional character designs, not psychological facts or learned personalities.

Parameter identification should use a small predeclared family of profiles and held-out scripts. Do not tune each candidate on every evaluation clip and then claim general improvement. Ordinary m, k and c already alter motion signature. Compare those cheaper adjustments and authored cue timing before attributing recognition to an observer or predictor. Recognition requires actual creator/viewer assessment, not merely different numeric coefficients.

## 6 Determinism and failure policy for future memory experiments

Record observer sample cadence and phase, initial memory, every added state, coefficient policy, forecast horizon and permitted script view. Use integer tick schedules and stable character/feature ID order. Snapshot observer and correction state in research traces. A replay must recompute updates from initial state and compare the added state, not merely the rendered image.

Update order should be explicit: resolve script at tick n, read observer committed through n, forecast from committed motion, derive bounded control for transition n→n+1, propose and guard motion, commit only after successful audit write, then update observer from the committed state according to its schedule. This one-transition causal convention prevents an algebraic loop. Record if observation instead occurs before stepping; do not switch order silently.

On invalid prediction, either abort the named experimental take or disable PMC under a separately versioned policy whose intervention is recorded. Do not silently count a fallback-heavy run as an unqualified C result. On a rejected motion candidate, preserve all previously committed channel states and terminate unless an independently authorized fault policy says otherwise. Memory reset, scene cut and late cue edits are explicit trace events. Build 0 keeps REJECT and abort and has no such extra state.

## 7 Controlled experiment plan

### 7.1 Motion experiments A through D

Use a fixed set of resolved geometries, including broad fused silhouettes, thin feature candidates and near-critical merge cases. Use isolated pulses, overlapping cues, long stillness, abrupt script surprises, repeated motifs and direction reversals. Keep dimensions, timestep, output schedule, integrator and force ceilings matched. Archive exact script and configuration hashes before inspection. Sweep a small parameter grid on development clips; freeze settings before held-out evaluation.

| Condition | Information and intervention | Required control |
| --- | --- | --- |
| A | v0.3 motion, no added observer or prediction | Authoritative baseline |
| B0 | TMO records history but cannot affect controls | Must reproduce A trajectories and pixels exactly |
| B1 | Bounded history modulates one declared cue parameter | Extra comparison to separate observation from intervention |
| C | Same history plus one bounded PMC rule | Match B1 controller and information except predictor |
| C script | Known-script anticipation | Separate from historical forecasting; include authored anticipation baseline |
| D | Qualified Phase-Memory features added to C | Only after source discrepancy and phase admissibility gates pass |

An observation-only B cannot improve fluidity because it does not affect output. Its purpose is to prove noninterference and feature quality. If B is intended to change motion, its control mapping must be named B1 rather than obscured as observation. Include a parameter-matched simpler smoothing controller, and spring/cue retuning baseline, to avoid crediting extra damping to sophisticated memory.

Numerical metrics: validity/rejections, max displacement and speed, RMS and peak acceleration, finite-difference jerk with a fixed differentiation convention, settling time, overshoot, energy-like residual, forecast error by horizon, intervention magnitude, and cadence sensitivity. Compute trajectory quantities at simulation rate; output-rate differences are a separate visual sampling diagnostic. A lower jerk can result from attenuating the entire performance, so compare excitation amplitude and narrative timing as constraints.

Image metrics: occupancy/clipping, aligned IoU, pixel difference distribution, change-region area and persistence, feature visibility where defined. No single frame-difference threshold proves fluidity. Compare unannotated full clips, standardized contact sheets and optional numeric overlays. Match playback speed, pixel scale and exposure. Randomize condition labels and viewing order; keep the creator's preferred artistic mapping available but do not treat one person's preference as a population result.

Proposed pilot: six geometries × four scripts × A/B0/B1/C, with two cadences for a selected stress subset. This is a workload plan, not an already executed trial or a statistical power calculation. Ask the creator to rate readability, intentional recovery, feature survival and preference; optionally use independent viewers with a predeclared rubric. Report paired differences, all clips, uncertainty and disagreements rather than only the best example.

Advance TMO only if B0 is exactly noninterfering, features are stable enough to interpret, and B1 gives repeatable creator-preferred behavior on held-out scenes beyond simple cue/spring retuning. Advance PMC only if correction limits and recovery hold, the forecast or anticipation produces a useful repeatable visual difference, and benefit exceeds its tuning/latency burden. Suggested screening goals such as a 10% reduction in a selected continuity metric or a 10% render-overhead budget are project choices to preregister after baseline measurement, not established scientific thresholds.

Reject or redesign if the benefit disappears after matching amplitude, only works on tuned clips, reduces expressiveness, introduces lag/oscillation, worsens recovery, leaks future information, fails exact replay, or needs exceptions for most scripts. Observation can remain a diagnostic even when control intervention is rejected. Phase-informed D must beat the strongest simpler B/C comparison using the same causal latency and input budget.

### 7.2 Separate color study

Hold geometry, motion and camera fixed. Compare monochrome, authored color envelopes, history-conditioned color persistence and separately permitted script-anticipatory color. Add a history-only forecasting variant only if it predicts an unavailable future quantity. Begin with a neutral palette and the creator's provisional amber/violet/cyan/blue/gold mappings; these are artistic conventions for this story, not universal emotional associations.

Measure intensity overshoot, rate and second differences, luminance/chromaticity trajectories, changed area, return-to-baseline time, palette ID consistency, mask leakage, gamut handling, safety-screen findings, replay and compute overhead. Color difference measures need a declared space and viewing assumptions. A visually smooth transition is not necessarily low luminance contrast; a constant-luminance hue transition can still require saturated-red analysis.

Creator questions should test whether color clarifies the intended beat, remains selective, distracts from expression, reveals a discovery too early, and preserves the monochrome identity. Include clips where motion settles before color; evaluate whether the longer tail is meaningful. Reject automatic inference when it contradicts authored meaning or overcolors neutral scenes. Numerical smoothness and storytelling preference remain separate outcomes.

## 8 Persistent features and the Commander mustache

Feature identity requires more than a stable control ID. Assign a persistent feature ID such as `commander.mustache.main` with owning character, local attachment transform, geometric support, renderer region, visibility and authored identity constraints. Its appearance should be reviewed across expressions and transformations. The requirement is preservation by default with an explicit scene directive for authorized change; it is not a universal ban on surreal transformation.

Possible representations, in increasing construction burden, are a separate composited 2D feature layer, a dedicated local field channel, an attached curve/capsule group, or a skeleton/mesh region with constrained deformation. A black mustache on a black silhouette needs an intentional contrast/cutout strategy; geometry alone does not guarantee visibility. A material or shading mask may preserve its contrast without changing its physical boundary. Color selections must respect identity-critical exclusion masks unless expressly overridden.

For an attached feature, write p_world = T_root T_head p_local in homogeneous 2D coordinates. A local deformation may act before this attachment transform. Use two reliable landmarks or an authored head frame for orientation; if a head collapses or landmarks coincide, do not divide by a zero length or infer a stable rotation. Report frame validity and apply an explicit hold/cut/review policy.

A smooth inverse warp preserves topology only if it stays one-to-one with a nonsingular Jacobian over the relevant region. A positive local Jacobian determinant alone does not establish global injectivity. Independent feature deformation constraints can cap length, area and aspect ratios, but recognition must still be judged visually. Field merging can obscure a feature even when its own geometry survives. Test overlap, crop, layer order, contrast, attachment error, symmetry and sampled feature silhouette across the permitted envelope.

## 9 Feature anchored procedural cinematography

### 9.1 Research scope and external precedent

Use persistent mathematical landmarks as camera focal targets while leaving the source geometry unchanged. Unity Cinemachine provides a relevant design precedent for local target offsets, screen position, dead zones and damping; its documentation explicitly warns that lookahead can amplify noisy animation. Target groups also assign weights and radii. These are architectural examples, not evidence that Unity or AeroCam is needed here. [Unity Position Composer](https://docs.unity3d.com/Packages/com.unity.cinemachine@3.1/manual/CinemachinePositionComposer.html), [Unity Target Group](https://docs.unity3d.com/Packages/com.unity.cinemachine@3.1/manual/CinemachineTargetGroup.html).

First study 2D translation and positive zoom. For world point p, camera center c, positive zoom s and optional screen offset o, use p_screen = s(p−c)+o in an explicitly declared coordinate system. Derive the raster transform separately so y-up and row-down are not confused. Zoom is magnification or crop, not a new viewing angle. Rotating a flat image also does not reveal the hidden side of a mustache. Genuine perspective changes require depth, surfaces, occlusion and projection assumptions, beyond Build 0 and beyond a simple 2D framing experiment.

### 9.2 Feature registry and focal priority

Propose `FeatureDefinition(id, owner, attachment, local_bounds, identity_priority)` and per-tick `FeatureObservation(id, world_center, world_bounds, visible_fraction, frame_valid)`. Cinematic directives specify active targets, authored priority, desired composition, shot timing, allowed anticipation and zoom limits. Stable IDs persist across regenerated geometry; invalid or intentionally transformed features are reported explicitly rather than reassigned to an unrelated nearby blob.

A weighted focal center is c* = sum_j w_j p_j / sum_j w_j for valid active targets with w_j≥0. If the total weight is zero, use the authored default shot. Weight changes need a smooth envelope and tie rule; do not let tiny color fluctuations repeatedly change the active target. A high priority mustache can influence framing without requiring every shot to center on it. The creator can override all automatic focal selection.

Weighted means do not guarantee that all target extents fit. For a target group, derive required scale from the union of target bounding boxes and safe composition margins, then apply positive minimum/maximum zoom. If no allowed camera fits every high-priority target, report a composition conflict and choose an authored shot policy. Do not shrink or distort the characters to make the camera constraint pass.

For a simple screen-center framing case, with the camera centered on the target union's bounding-box center, target union width Bx and height By, and symmetric available screen extents Ux, Uy, the maximum fitting magnification is min(Ux/Bx, Uy/By). A weighted focal center can differ from that box center; then check directional distances to every target extent against each side's composition margin. Guard zero extents and use the same world-to-screen convention on both axes. This fit equation describes geometry at one instant; camera smoothing can still temporarily crop a moving target. Enforce and test a separate allowed crop budget rather than claiming the target-center controller guarantees visibility.

### 9.3 Interpolation and memory

Use authored shot transitions first. A future smoothed center can use c_next = exp(−h/τ_cam)c + (1−exp(−h/τ_cam))c*. Interpolate log zoom ℓ=log(s) to keep scale positive, with declared limits on pan speed, acceleration and zoom rate. A first-order filter of a discontinuous target can produce a velocity discontinuity at the switch; use a finite smootherstep trajectory with controlled endpoints or a separately validated second-order controller when continuity of camera derivatives matters.

Dead zones prevent constant micro-corrections but can introduce discontinuities when crossing their boundary. Test boundary behavior and add a smooth soft region if necessary. Hysteresis and minimum shot dwell time reduce rapid target switching. Known future script cues can schedule a reveal or pre-position the camera; motion extrapolation should be limited and disabled on invalid/noisy landmarks. There is no reason to make the camera follow every spring oscillation.

Historical activity can sustain a feature priority briefly after a gesture. It must not create a self-reinforcing loop in which zoom enlarges a feature, image-based salience rises, and the camera zooms further. Prefer semantic/local geometric feature measurements independent of the camera. Likewise, a color cue may nominate a feature for a scripted reveal, but luminance alone must not override cinematic intent. Log every automatic focal change and its source.

Keep camera and color permissions independent. An amber accent can linger while the camera returns to a wider shot; a gold discovery can motivate an authored close-up without changing the field. A camera must not alter material masks or physical control positions to manufacture its target. Final sequence safety analysis must occur after camera transforms, since zoom and pan can enlarge high-contrast patterns and changed areas.

### 9.4 Future modules and validation

Start with `features.py` for local attachments/observations and `camera.py` for shot resolution and 2D transforms. Keep renderer projection application separate from landmark extraction. Only separate `composition.py` after the policy becomes complex enough to justify it. Proposed interfaces are `observe_features(geometry, definitions)`, `resolve_shot(cues, observations, history)`, `step_camera(previous, target, policy)` and `project(points, camera, viewport)`.

Required tests: local-to-world transform oracle, viewport mapping, zoom positivity, fitting target extents with margins, deterministic ties, missing/occluded targets, attachment degeneracy, static-shot rest invariance, bounds on pan/zoom derivatives, no mutation of geometry, exact replay, scene cuts/reset, and mismatched aspect ratios. Stress high-speed mustache motion, competing features, partial off-screen targets, abrupt color changes, and full feature disappearance.

Compare a static camera, authored keyframes, smoothed landmark follow, and optional lookahead with identical geometry and color. Measure landmark screen error, visible fraction, crop duration, shot switches, camera velocity/acceleration/jerk, zoom rate and computation. Creator review must assess narrative emphasis, reveal timing and whether camera motion obscures rather than supports performance. Reject lookahead or history if it adds jitter, spoilers, latency or needless zoom. This system remains deferred until stable features and a useful baseline animation exist.

## 10 Prioritized research gates

First complete the monochrome E0/E1 evidence package. If shapes are weak, compare simpler shape representations before adding temporal systems. Next test identity features with a local attachment representation and scripted localized color independently. An observation-only TMO can be instrumented after a baseline exists; it need not delay either experiment. Then test one bounded control intervention with the strongest simpler comparison. Keep phase adapters behind qualification and paper/code reconciliation, and AILEE behind a demonstrated governance problem. Add 2D cinematic framing once landmarks have dependable validity/visibility. Defer 3D perspective, learned prediction, complex shader frameworks and per-pixel history.

The following source-audit and color/safety sections provide the verified upstream details, indexed palette design, shader equations and publication checks. They do not change the staged decision above.


## 11. Decisions for the consolidated v0.4 package

1. Preserve v0.3 Build 0 unchanged: neither upstream is a required runtime dependency. The v0.3 numeric guard, abort-on-rejection behavior, deterministic scene state, and evidence format remain authoritative.
2. AILEE contains a real, inspected scalar trust pipeline, bounded fallback behavior, structured audit results, optional replay helpers, and a separate hash-chained ledger. It does not provide an animation state validator or a scientifically calibrated measure of artistic quality. Its substitution-on-rejection behavior conflicts with Build 0 reject-and-abort semantics. Study a compact-state observer adapter only after an animation-specific defect justifies it.
3. The coauthored Phase-Memory paper defines genuine phase-based diagnostics, including a finite memory horizon and normalized diagnostic score. The pinned executable source differs materially from the final paper: its U3 accumulates from a start index without expiration, its U2 uses centered differentiation at interior samples, and its score function does not itself apply frozen normalization scales. These discrepancies were already anticipated in v0.3 P0061; source inspection now verifies them. Resolve them before direct reuse, without silently modifying the coauthored definitions.
4. The Phase-Memory validation notebook is an illustrative synthetic-data notebook with empty saved outputs and stale API calls. It does not independently reproduce the real-EEG performance stated in the README. The final paper also explicitly reports a synthetic benchmark in which the full operator had no positive lead time and did not outperform simpler baselines. None of this supplies evidence of animation benefit.
5. The most defensible future Phase-Memory experiment begins with controller-known phase in a deliberately oscillatory fixture, then compares ordinary state, simple bounded history, and phase diagnostics under matched inputs. Do not derive phase indiscriminately from settling motion, emotional intensity, or monochrome-to-color envelopes.

## 12. Source access, pins, and scope

Authenticated connected GitHub repository discovery, default-branch metadata, recursive trees, individual pinned file reads, and workflow-run metadata were available. All remote operations were GET/read operations. The accessible repository listing identified `dfeen87/Commander-Zorg` as **private**; no visibility change or remote mutation occurred. No Commander-Zorg source was needed for these upstream conclusions.

| System | Default branch and inspected commit | Commit date (UTC) | Inspection depth |
|---|---|---|---|
| AILEE Trust Layer | `main`, `de238cd4a9edd53f978bc33a02f77f891887f263` | 2026-10-09 | Core Python pipeline; selected fallback tests and smoke tests; architecture and fallback report; ledger implementation; optional replay/serialization helpers; light-transition and memory domain scope; packaging, license, citation, and CI definition |
| Phase-Memory Operator | `main`, `33ba9edc481cf0b63c24abba8dd82b440c5ce411` | 2026-04-29 | Final paper; all four core Python modules; bug-fix tests; calibration protocol; synthetic notebook; dependency record; license, citation, replay notes, and CI definition |

The pins represent the default-branch heads observed during this audit, not a claim that every released tag, branch, language runtime, domain adapter, or dependency has been exhaustively audited. Source records are in `upstream-primary-sources.json` alongside this report.

Primary commit references: [AILEE pinned revision](https://github.com/dfeen87/AILEE-Trust-Layer/commit/de238cd4a9edd53f978bc33a02f77f891887f263); [Phase-Memory pinned revision](https://github.com/dfeen87/Phase-Memory-Operator/commit/33ba9edc481cf0b63c24abba8dd82b440c5ce411).

## 13. AILEE: verified implementation and relevant mathematics

### 13.1 Exact inspected public interface

The Python package release metadata identifies version 10.0.2; the single pipeline file retains an older internal v7.0.0 descriptive banner. Pin the repository commit and inspected path rather than treating that banner as the package version. `setup.py` declares Python >=3.9 and no mandatory third-party dependency for the core pipeline.

The inspected API is `AileeTrustPipeline(AileeConfig(...))`, followed by `process(raw_value, raw_confidence=None, peer_values=None, timestamp=None, context=None) -> DecisionResult`. The input and output are scalar numeric values. Per-instance mutable state consists of timestamp/value history, last accepted good value, and last result. `DecisionResult` reports value, safety status, grace status, consensus status, fallback flag, confidence score, reasons, and metadata. A frozen dataclass does not make its nested lists/dictionaries immutable.

Sources: [package metadata](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/setup.py#L5-L25); [result/config definitions](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/ailee_trust_pipeline_v1.py#L57-L173); [pipeline public entry point](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/ailee_trust_pipeline_v1.py#L292-L357).

### 13.2 Routing and numeric boundaries

The inspected pipeline validates numeric inputs before mutation. A hard-envelope violation chooses a fallback scalar and commits that result with an outright-rejected status. For in-envelope input, it computes a confidence score, may route a borderline result through GRACE, may check peer consensus, and either retains the raw scalar or selects fallback. A valid returned fallback enters the trusted history; it does not become the last accepted good value. A failure that cannot establish a finite admissible result raises before committing the new result.

AILEE's core status vocabulary is `ACCEPTED`, `BORDERLINE`, `OUTRIGHT_REJECTED`; grace and consensus each have PASS/FAIL/SKIPPED. Insufficient peers produce consensus SKIPPED, and certain accepted branches intentionally retain the scalar with that status. Thus “returned value,” “consensus achieved,” and “authorized animation state” are different propositions.

Sources: [hard-envelope route](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/ailee_trust_pipeline_v1.py#L339-L357); [consensus](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/ailee_trust_pipeline_v1.py#L677-L703); [commit policy](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/ailee_trust_pipeline_v1.py#L818-L827).

### 13.3 Confidence, trend, and forecasting are domain assumptions

The inspected score combines recent-history inverse variance, peer agreement, and plausibility relative to history. For sufficient history, the stability component is `1/(1+variance)`. Optional supplied confidence contributes 15% after clipping to [0,1]. GRACE needs at least two available checks and at least two passing checks among trend, forecast proximity, and peer agreement. Its forecast is the last history value plus the mean recent increment.

Engineering implications (this audit's interpretation):

- `1 + variance` needs an explicit dimensionless feature scale before use with positions, speeds, forces, or color intensities. Otherwise changing units changes confidence.
- Trend “velocity” and “acceleration” are first and second **sample differences**, not time-normalized derivatives. Timestamps are recorded but not used in these equations. A future adapter must fix the observation cadence and declare feature units, or derive separately labeled rate-aware features.
- A deliberately expressive movement can be statistically unusual without being invalid. A confidence score is not an artistic correctness probability.
- Peer values require independently meaningful sources. Creating several copies of the same predicted animation value does not establish independent consensus.
- The startup history and default thresholds must be tested explicitly; high external confidence alone does not override the internally combined score.

Sources: [confidence computation](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/ailee_trust_pipeline_v1.py#L496-L549); [GRACE, per-sample trend and forecast](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/ailee_trust_pipeline_v1.py#L572-L668); [cold-start smoke fixture](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/tests/test_pipeline_smoke.py#L9-L16).

### 13.4 Fallback hardening and remaining limits

Version 10.0.2 implements a single fallback boundary: select a finite candidate, apply fallback clamps, then apply authoritative hard bounds. Disjoint intervals are rejected; stable midpoint/median and mean fallback paths address intermediate overflow. Final construction and commit recheck finiteness and bounds. The targeted tests cover disjoint configurations, mutated bounds, fallback routes, extreme finite histories, invalid numeric evidence, and atomic failure.

The upstream fallback report states 108 focused tests and a full Python run of 670 passed/1 skipped; these are **upstream reported results**, not locally rerun results. GitHub workflow metadata returned two completed successful CI runs at the pinned HEAD. The workflow definition includes Python tests on 3.9/3.10/3.11 and additional native, packaging, Rust, TypeScript, and C++ jobs. This audit inspected the definition and overall run metadata, not every job log. Cross-runtime semantic equivalence is not established here. Earlier-layer extreme arithmetic can still raise; the upstream report explicitly records this limitation.

Sources: [fallback implementation](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/ailee_trust_pipeline_v1.py#L709-L757); [regression tests](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/tests/test_fallback_integrity.py); [upstream verification and limits](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/docs/FALLBACK_INTEGRITY_V10_0_2.md#L61-L107); [observed successful CI run](https://github.com/dfeen87/AILEE-Trust-Layer/actions/runs/38003676880); [workflow definition](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/.github/workflows/ci.yml).

### 13.5 Provenance and deterministic replay boundaries

The separate `governance_v1` ledger computes SHA-256 over compact sorted JSON entry fields and checks previous/current hashes. The writer generates a UUID-derived entry ID and current UTC creation time. Its generic serializer allows fallback representations of unfamiliar objects and does not specify the v0.3 canonical JSON newline/nonfinite/negative-zero rules. These ledger entries are not byte-identical replay artifacts by default. Hash chaining detects inconsistency relative to the chain being checked; it does not by itself authenticate an author or prevent wholesale replacement of an unanchored chain.

The core `process` defaults to wall-clock time if no timestamp is supplied. Optional replay helpers exist, but an animation adapter must use tick-derived time, persist complete initial/updated adapter state, pin configuration, exclude operational wall clocks from deterministic comparisons, and retain v0.3 evidence as the authority. Do not replace the Build 0 manifest recipe with AILEE's general ledger serializer.

Sources: [ledger serialization/hash](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/governance_v1/ledger/ledger.py#L23-L69); [ledger writer IDs/times](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/governance_v1/ledger/ledger.py#L277-L380); [optional replay helper](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/optional/ailee_replay.py).

### 13.6 Domain-name traps and licensing evidence

The inspected AILEE Memory Domain governs RAM/heap/swap/process-memory actions. It is not TMO or expressive character memory. The Light Transition Domain governs light-carried communications, signal integrity, freshness, BER/SNR, and propagation constraints. It is not emotional color blending or a photosensitivity validator. Domain names alone are insufficient evidence for reuse.

Sources: [Memory Domain scope](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/domains/memory/MEMORY.md#L1-L38); [Light Transition scope](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/ailee/domains/light_transition/LIGHT_TRANSITION.md#L1-L23).

The root LICENSE, core pipeline, ledger, packaging, and citation metadata identify MIT and Don Michael Feeney Jr. The root notice requires preserving its copyright/permission notice with copies or substantial portions. One inspected smoke-test header instead identifies PolyForm Noncommercial 1.0.0. This is a verified notice discrepancy, not a legal resolution: obtain a file-specific clarification before copying that test. Do not infer that all files in every historical revision share one notice. Scholarly citation and software-license compliance are separate obligations. No source was incorporated into the engine in this assignment.

Sources: [AILEE LICENSE](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/LICENSE); [citation metadata](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/CITATION.cff); [conflicting test header](https://github.com/dfeen87/AILEE-Trust-Layer/blob/de238cd4a9edd53f978bc33a02f77f891887f263/tests/test_pipeline_smoke.py#L1).

### 13.7 Recommended AILEE experiment, after Build 0

Start with observation-only evaluation of normalized compact features from a saved candidate stream: max displacement, max speed, feature-attachment error, or another predeclared measurable signal. No per-pixel trust pipelines. Compare (i) recorded observations only, (ii) deterministic hard rejection, and (iii) an AILEE observer/adapter. Hold candidate order and inputs identical across arms and serialize each independent pipeline's history. Measure invalid-transition detection, false intervention on intentional expression, retained expressive range, CPU time, memory, startup behavior, and replay.

Any later mediation requires a complete proposed animation state, explicit policy, and independent revalidation of every invariant; coordinatewise scalar fallback cannot be assumed to preserve attachment, topology, or coupled position/velocity consistency. A closed-loop mediator is a separate experiment from prerecorded-stream observation. Reject full integration if the ordinary numeric guard catches the same faults with less complexity, if intervention suppresses creator-approved behavior, or if the adapter's confidence cannot be given a defensible interpretation. This is the E3 seam already described by v0.3 P0064–P0066/P0301, not authorization to implement it now.

## 14. Krüger–Feeney Phase-Memory: definitions that must be preserved

### 14.1 Attribution and mathematical object

The repository paper and CITATION.cff identify **Marcel Krüger and Don Feeney (2026)**. The work is a supervisory diagnostic representation of phase deviation, phase drift, and finite accumulated phase history. It is not ordinary animation state, a generic historical average, TMO, PMC, a controller, a Lyapunov proof, or a demonstrated animation system.

For an admissible oscillatory signal `s(t)`, the paper uses an analytic signal `z=s+iH[s]`, phase `theta=arg(z)`, and a declared reference `theta_ref`. Its final definitions are:

\[
U_1(t)=\operatorname{wrap}(\theta(t)-\theta_{ref}(t)),\qquad
U_2(t)=\dot\theta(t)-\dot\theta_{ref}(t),
\]
\[
U_3(t)=\int_{t-T_m}^{t}w(\tau)U_1(\tau)\,d\tau,\quad
T_m>0,\quad 0\leq w\leq1,
\]
\[
J(t)=a\bigl(U_1/\sigma_\theta\bigr)^2+
b\bigl(U_2/\sigma_\omega\bigr)^2+
c\bigl(U_3/\sigma_m\bigr)^2,\quad a,b,c\geq0.
\]

The paper freezes the memory horizon, scale parameters, weights, reference policy, and alert thresholds after calibration. It gives backward first differences for discrete U2 and a finite rectangular sum for discrete U3. An alert adds an above-threshold dwell requirement. The score is a diagnostic departure measure; its name does not establish closed-loop stability.

Sources: [paper definitions, Eqs. 2–11](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/paper/deterministic-phase.md#L58-L130); [coauthor citation record](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/CITATION.cff).

### 14.2 Mathematical limits relevant to animation

With principal wrapping to [-pi,pi) and w in [0,1], finite-horizon memory satisfies `abs(U3)<=pi*Tm` (or `pi*M*dt` for the declared discrete sum). This is a derived bound, not an empirical quality result. U1 has angular units, U2 angle/time, and U3 angle*time; frozen dimensional scales are necessary before a dimensionless combined score or controller input is claimed.

A signed history integral can cancel alternating deviations. Crossing the phase branch cut can introduce a large signed jump despite a small circular change. U2 should use the declared unwrapped phase convention, not naïvely differentiate a wrapped sawtooth. Near-zero analytic amplitude, a constant signal, a transient pulse, or a mixture with no meaningful single phase can make phase interpretation unreliable. A scalar amplitude-statistic gate alone does not establish narrowband oscillatory content.

If phase is already known from a periodic motion controller, use it directly and log that provenance. An externally measured oscillatory signal needs a declared estimator, reference alignment, frequency range, sampling cadence, anti-aliasing, quality gate, latency, startup, reset, and dropout behavior. Nyquist alone does not establish adequate phase accuracy. Choose a sampling rate from a declared error/latency study; do not label ordinary 10 Hz snapshots sufficient for every phase signal.

These are mathematical/engineering inferences from the definitions and the paper's explicit admissibility limitations, not new claims by the coauthors. Sources: [paper phase qualification](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/paper/deterministic-phase.md#L58-L66); [paper limits](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/paper/deterministic-phase.md#L414-L424).

### 14.3 Verified source discrepancies and integration blockers

These are blockers for **direct Phase-Memory reuse**, not blockers for Build 0.

| ID | Static observation at pinned revision | Consequence / required resolution |
|---|---|---|
| PM-01 | Final paper Eq. 5/8 uses finite horizon Tm; `compute_U3` uses cumulative trapezoidal integration from `t0_idx`, with no expiration or decay | Select and document the intended scholarly definition; reconcile via a separately authorized upstream correction or a clearly named independent adapter; do not represent cumulative history as verified finite memory |
| PM-02 | Paper discrete U2 uses backward differences; source `compute_U2` calls `np.gradient` | Interior values use a following sample; cannot be treated as zero-latency causal online features |
| PM-03 | `analytic_signal` calls SciPy full-array FFT Hilbert; optional amplitude gate uses the median of the full supplied amplitude array | Whole-clip results and quality normalization can depend on future samples; acceptable for labeled offline diagnostics, not unqualified online predictive conditioning |
| PM-04 | `compute_triadic_state` reduces all intervals to their mean for U2, whereas U3 uses individual intervals | Require uniform ticks or explicitly support/test irregular timestamps; reject nonfinite, mismatched, nonmonotone data before use |
| PM-05 | Score function computes raw weighted squares; normalization helper estimates scales from whichever arrays are passed | Caller must reuse calibration-only scales; no normalization refit on validation/test clips; expose exact applied scales in the adapter record |
| PM-06 | Parameter dataclass checks negativity but not finiteness; its freeze flag may itself be assigned false | Do not treat it as strict immutable configuration; validate independently and store a locked resolved record |
| PM-07 | Quality heuristic uses mean amplitude / amplitude standard deviation; a nonzero DC signal can satisfy this heuristic | Qualify actual oscillatory content separately; do not equate this advisory statistic with measured physical SNR |
| PM-08 | Final paper's sample-count dwell equation and source/test dwell conventions require reconciliation at boundary counts | Define seconds covered by samples, first eligible alert tick, inclusivity, and noninteger-duration rounding with exact fixtures |

Source locations: [U1/U2/U3 and aggregate API](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/src/triadic_operator.py#L37-L166); [phase estimator/quality heuristic](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/src/phase_extraction.py#L42-L201); [parameters, raw score, normalization](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/src/stability_functional.py#L19-L86); [warning implementation](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/src/warning_logic.py#L61-L82); [dwell fixture](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/src/test_bug_fixes.py#L168-L185).

The interpretation of centered differences is supported by [NumPy's gradient documentation](https://numpy.org/doc/stable/reference/generated/numpy.gradient.html). The transform method is confirmed by [SciPy's Hilbert documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.hilbert.html). Neither API promises causal streaming output. Those current documentation pages are methodological references, not pinned dependency versions for the upstream code.

### 14.4 What the available validation evidence does and does not establish

The README reports real-EEG ROC-AUC 0.87, median lead time 15.3 s, and false-alarm rate 0.10/s. Those numbers are upstream assertions in this audit. The final paper cites a separate Medinformatics article by Krüger, Feeney, and Wende, DOI `10.47852/bonviewMEDIN62029043`; an attempted direct DOI retrieval was inaccessible, so that article's dataset, analysis, and reported results were not independently examined here. No transfer to animation is implied.

The pinned notebook explicitly calls its generated EEG-like data synthetic and its metrics illustrative. Its code cells have no saved outputs. Static inspection finds imports/calls for `calibrate_weights` and singular `compute_lead_time` that do not match the inspected source's `calibrate_weights_grid` and plural `compute_lead_times`; its false-alarm calls also omit a required exclusion-window argument. Thus the notebook is not a verified working reproduction of even that demonstration at this pin. It applies `filtfilt` and global signal normalization before splitting, which creates a future-information boundary incompatible with claims of a causal online detector; a future study must define preprocessing separately for that claim. These findings come from source inspection, not an attempted notebook execution.

The final paper's illustrative delayed-bistable benchmark reports no positive lead time for any tested method; full-operator ROC-AUC 0.153 versus 0.209 for amplitude threshold and 0.487 for drift only, with two full-operator false alarms. The paper explicitly declines to claim superiority in that configuration. Treat these as paper-reported outcomes, not audit-run measurements. They strengthen the requirement for simple ablations and a predeclared rejection criterion.

Sources: [README performance assertions](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/README.md#L124-L136); [synthetic notebook](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/validation/eeg_replay.ipynb); [paper-reported synthetic results](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/paper/deterministic-phase.md#L274-L282); [paper's external article citation](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/paper/deterministic-phase.md#L312-L320).

The repository has standalone bug-fix tests, but its pinned CI installs dependencies and compiles sources only. GitHub reported a successful run at the pinned HEAD; this does not establish behavioral-test execution or scientific validation. Sources: [CI definition](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/.github/workflows/ci.yml); [observed successful run](https://github.com/dfeen87/Phase-Memory-Operator/actions/runs/25135335020); [bug-fix script](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/src/test_bug_fixes.py).

### 14.5 Proposed independent diagnostic adapter

This is a future research design, unimplemented and unvalidated. Suggested boundary:

`PhaseObservation(tick, phase_rad, reference_phase_rad, amplitude_quality, valid)` → `PhaseDiagnostics(tick, U1_rad, U2_rad_per_s, U3_rad_times_s, normalized_channels, J, quality, latency_ticks, reason_codes)`.

The interface must identify whether phase was controller-known or estimated and which mathematical/source variant it follows. A finite-window implementation needs only compact phase samples/weights and a rolling sum per feature, O(M) storage and O(1) update for a fixed rectangular window, rather than images. Keep the paper's finite sum and wrap definition explicit. Include initialization coverage, expiration, reset, malformed samples, dropped samples, and numerical rolling-sum drift in tests. A periodically recomputed sum can bound floating accumulation error, but its cadence is part of the deterministic policy.

Use the diagnostic for logging first. If a later controller trial is justified, map only qualified normalized outputs to bounded controls, for example `d=tanh(J/J_scale)` for nonnegative J, followed by an independently parameterized low-pass envelope and rate limit. This mapping is a new adapter, not the original operator. Preserve hard motion/color/feature constraints after mapping. Unknown/invalid phase must yield an explicit unavailable status with zero influence under the named policy, never a fabricated phase estimate. A sustained color cue with no oscillation has no inherent phase; use ordinary scripted intensity/history instead.

### 14.6 Evidence required for adoption

Before a Phase-Memory-informed Experiment D:

1. Reconcile paper/source U3, U2, scaling, dwell, and calibration-policy differences at a pinned revision or a distinctly named adapter. Obtain author review where scholarly definitions are being clarified.
2. Verify known-phase synthetic fixtures: constant offset, frequency slip, wrapping, bounded finite history, a low-amplitude dropout, irregular-tick rejection, startup/reset, and causality. A causality test holds all samples through n fixed while changing later samples and checks outputs through n, allowing only declared estimator latency.
3. Use locked calibration scales and held-out scenes. Compare ordinary spring state, scalar EWMA, finite delay history, and phase features with the same allowed future script information. Include matched x/v/current-cue states reached through different histories.
4. Demonstrate incremental diagnostic value or creator-approved visual improvement with no unacceptable stability, recovery, aliasing, latency, identity, or visual-safety regression. Measure overhead and deterministic replay separately from visual preference.
5. Reject adoption if simple history predicts/conditions equally well, the selected animation signals lack admissible phase, quality gates disable it most of the time, or gains vanish on held-out clips. Improved J behavior alone is not an animation-quality result.

The source calibration protocol requires frozen parameters after calibration, whereas the final paper also discusses selection among fixed configurations in validation. A new study must state its selection rule before accessing the holdout and must not silently mix the two protocols. Sources: [calibration protocol](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/calibration/calibration_protocol.md); [paper split policy](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/paper/deterministic-phase.md#L134-L149).

### 14.7 Dependencies and separate licensing/attribution duties

The reference implementation uses NumPy and SciPy; optional/validation facilities additionally list scikit-learn, PyYAML, Jupyter/ipykernel, and matplotlib. The dependency file specifies ranges, not an exact reproducible lock. These dependencies are unnecessary for Build 0. A known-phase diagnostic could avoid Hilbert/SciPy, but that would be a separately verified adapter implementation, not proof that the existing code has no SciPy dependency.

The pinned LICENSE identifies MIT, copyright 2026 Don Michael Feeney Jr., requiring preservation of its copyright/permission notice with copied substantial portions. Scholarly attribution remains **Krüger and Feeney**, even though the software notice names one copyright holder. Cite the coauthored paper, exact code revision, any separate validation paper actually used, and the adapter's own departures. Do not relabel an EWMA or a new predictor as the Krüger–Feeney operator.

Sources: [dependencies](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/reproducibility/requirements.txt); [license](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/LICENSE); [citation](https://github.com/dfeen87/Phase-Memory-Operator/blob/33ba9edc481cf0b63c24abba8dd82b440c5ce411/CITATION.cff).

## 15. Integration priority and unresolved questions

| Priority | Next action | Release boundary |
|---|---|---|
| 0 | Complete v0.3 E0/E1 with the local numeric guard and original evidence requirements | Build 0 only; no upstream imports |
| 1 | If identity fails, study attached feature geometry before specialized memory | New explicitly authorized character experiment |
| 2 | Compare simple compact TMO observation and script-driven anticipation with ordinary dynamics | Separate history/prediction experiment |
| 3 | Reconcile Phase-Memory definitions and repair reproducibility evidence in a separately authorized research effort; begin with offline diagnostics | No effect on Build 0 coding readiness |
| 4 | Study AILEE observation on fixed candidate streams only after a measurable validation gap appears | Separate E3 authorization |
| 5 | Permit bounded Phase-Memory-informed or AILEE-mediated control only after ablations, causality checks, complete-state revalidation, and creator review support it | New release gates and full evidence |

Unresolved, explicitly unverified: external real-EEG result reproduction; behavior of every AILEE runtime/domain; file-specific resolution of the AILEE smoke-test notice conflict; intended upstream resolution of paper/source differences; animation-specific phase observables; useful parameter ranges; artistic benefits; practical runtime cost. These gaps justify deferral and targeted experiments, not expansion of Build 0 or claims that either upstream is unsuitable for all purposes.


## 16. Decision and scope

The simplest useful future color experiment is an immutable indexed palette, explicit script color directives, one bounded scalar envelope per active character-region, and a pure numerical compositor. Begin with scripted color alone. Historical persistence and anticipation are optional controls evaluated separately after that baseline is satisfactory. Color should be an independently switchable presentation channel; geometry receives no emotional labels and motion receives no palette data.

Section 0's amber/agitation, violet/suspicion, cyan/curiosity, blue/reflection, and gold/discovery are project-specific proposed artistic mappings. They are neither universal psychological facts nor accepted v0.3 decisions. An experiment must determine whether viewers understand and prefer these choices. A faint color after motion settles is possible precisely because the color envelope has its own release duration.

The separate cinematography addendum also originates after v0.3. This contribution supplies color/camera interaction constraints; the main architecture report should contain the feature-frame/camera specification. No camera transform, color palette, temporal observer, or safety analyzer belongs in the v0.3 Build 0 runtime.

## 17. Future module plan and ownership

| Proposed file | Owns and exposes | Inputs and dependencies | Failure behavior and tests |
|---|---|---|---|
| `palettes/emotion_colors.json` | Authored color IDs and versioned metadata | No executable behavior; validated before rendering | Unknown fields, duplicate IDs, nonfinite/out-of-range values, invalid regions, bad permissions reject before a render |
| `color_index.py` | Immutable palette records; `load_palette`, `lookup_color` | JSON, schema validator, stable character/feature catalog | Unknown ID is a compile error for explicit cues; keyword proposals may be discarded with a diagnostic; test version/ID/reference validation |
| `expression_color.py` | Directive precedence; `resolve_color`; pure `envelope_at_tick`; `ColorControl` snapshots | Parsed script directives, palette entries, tick and optional bounded observations | Conflicting equal-priority explicit directives reject unless stable resolution is declared; validate continuity, endpoints and exact return to baseline |
| `shader_color.py` | `compose_tint` and attachment-local region masks | Linear RGB arrays, coverage/masks, numeric `ColorControl`; no emotion names | Shape mismatch, NaN or invalid premultiplication reject; test transfer conversion, mask confinement, feature protection and transparent edges |
| `visual_safety.py` | Offline final-sequence screening/reporting | Decoded export, timestamps, display/profile assumptions and pinned rule version | Missing/unsupported profile or undecodable frame produces **inconclusive**, never pass; unit fixtures plus independent analyzer comparison required |

Initially keep temporal envelope functions inside `expression_color.py`. A separate `temporal_color.py` becomes justified if stateful history, multiple controllers or substantial color tests make the smaller module hard to review. Do not introduce six independent micro-modules solely because six names were suggested. The safety analyzer remains separate because it observes the complete export and must detect effects created by geometry, camera and editing as well as color.

Suggested future interfaces (proposed, unexecuted):

```text
# Proposed interface pseudocode
load_palette(document: Mapping, feature_catalog: FeatureCatalog) -> Palette
lookup_color(palette: Palette, color_id: str) -> PaletteEntry
resolve_color(cue: ColorCue, palette: Palette, policy: ColorPolicy) -> ResolvedColor
envelope_at_tick(tick: int, timing: ColorTiming) -> float
color_control(tick: int, cue: ResolvedColor, memory: ColorMemory | None) -> ColorControl
region_mask(region: RegionSpec, frame: FeatureFrame, coverage: Array) -> Array
compose_tint(base_linear: Array, tint_linear: tuple, amount: Array) -> Array
analyze_sequence(export: ExportDescriptor, rules: SafetyRules) -> SafetyReport
```

Snapshots should contain only stable color ID, linear RGB target, bounded intensity, region ID, protected feature IDs, active interval and provenance. The renderer must not infer emotions, parse script prose, change positions, or write history. Use actual simulation ticks rather than the wall clock. The manifest pins the palette bytes/hash, schema version, directive compiler version, export profile, reduced-effects preset and all controller parameters.

## 18. Versioned palette and directive design

The following is a **proposed configuration example**, not a finalized schema or evidence of accepted color values. Numeric choices are artistic starting points requiring rendered review; they are not medical safety limits.

```json
{
  "schema_version": "1.0.0",
  "palette_id": "zorg-emotional-accents",
  "palette_revision": "0.1.0-research",
  "encoding": "srgb",
  "baseline": "monochrome",
  "entries": [
    {
      "id": "CZ-C001",
      "name": "Restrained amber",
      "srgb_hex": "#D3A14A",
      "emotion_tags": ["agitation"],
      "keyword_proposals": ["agitated"],
      "characters": ["zorg"],
      "scenes": ["*"],
      "region_id": "zorg.face.accent",
      "shader_channel": "fill_tint",
      "intensity_min": 0.0,
      "intensity_max": 0.25,
      "timing": {"attack_s": 0.8, "release_s": 1.2, "curve": "quintic"},
      "history": {"permitted": false, "half_life_s": 0.5, "max_weight": 0.15},
      "anticipation": {"permitted": false, "max_lead_s": 0.3},
      "safety_policy_id": "cz-sdr-conservative-research-v1",
      "protected_features": []
    }
  ]
}
```

Use alphanumeric IDs as strings, including numerical-looking IDs, so leading zeros survive parsing and external script references remain stable. IDs are unique and never recycled. Human names can change and need not be unique. Semantically different colors receive new IDs; changing an existing color value requires a new palette revision and does not alter earlier exports. A complete JSON Schema should disallow unknown fields, require supported schema major version, constrain six hex digits, finite numeric ranges and enum values, and declare which migrations preserve meaning. JSON itself does not prohibit duplicate object keys: reject duplicates during loading before normal dictionary construction. Duplicate entry IDs are a separate error.

Cross-field validation must require `0 <= min <= max <= 1`, nonzero attack/release when smooth transitions are requested, positive history half-life, nonnegative lead time, valid target character/scene/region, explicit default policy and consistent feature ownership. Minimum intensity is zero for the ordinary inactive case; a nonzero active minimum cannot prevent terminal recovery. RGB/hex is the source encoding; convert once to a declared internal linear-light space. Do not silently interpret sRGB bytes as linear intensity.

Directive example (proposed syntax):

```text
COLOR id=CZ-C001 character=zorg region=zorg.face.accent
      start_tick=240 hold_ticks=120 attack_ticks=48 release_ticks=72
      intensity=0.18 anticipation=false history=false
COLOR mode=monochrome character=commander start_tick=0 end_tick=720
```

Precedence: a global monochrome/reduced-effects selection constrains the entire render; an explicit monochrome directive suppresses automatic proposals; an explicit scripted ID wins over character defaults; a curated character/expression mapping may supply a default only when enabled; keyword matching merely proposes a draft cue for creator acceptance. The word `COMMANDER` carries no automatic color meaning. Metadata tags are searchable authoring aids. They do not become hidden runtime behavior.

Safety policy validation applies to the resolved directive even if it was explicit. If the desired cue violates the selected policy, reject with a reviewable diagnostic or produce an explicitly selected reduced-effects alternative; do not silently change artistic intent. Each diagnostic records requested and effective parameters and the reason. For initial experiments, allow one active tint per region. Resolve different regions independently. Reject ambiguous overlapping directives rather than adding intensities that may exceed bounds; a later documented stable priority/ID rule may support intentional overlap.

## 19. Color mathematics and contracts

For SDR sRGB input `c` in `[0,1]`, decode to linear light:

\[
L(c)=\begin{cases}c/12.92,&c\le0.04045\\((c+0.055)/1.055)^{2.4},&c>0.04045.\end{cases}
\]

Encode `l` back using `12.92*l` at `l <= 0.0031308`, otherwise `1.055*l^(1/2.4)-0.055`. Interpolate or composite in the space explicitly selected for that operation, then encode once at output. CSS Color 4 distinguishes encoded sRGB, linear-light sRGB, Oklab and interpolation behavior; it is a primary technical reference, not an emotional mapping source. [CSS Color 4, predefined sRGB spaces and sample conversion code](https://www.w3.org/TR/css-color-4/#predefined-sRGB).

The most economical first compositor is a convex tint on an opaque monochrome baseline `B`:

\[
a(x,t)=\operatorname{clip}(I(t)M(x,t)P(x,t),0,1),\quad
C_{lin}(x,t)=(1-a)B_{lin}(x,t)+aT_{lin}.
\]

`M` is a local region mask and `P` excludes protected features. All values remain within the componentwise convex hull of the two in-gamut inputs. This is a tint amount, not a geometry deformation or necessarily physical illumination. It can change luminance and therefore must be assessed on the final sequence. Hard monochrome black and white have little chromatic freedom at identical luminance; a visible accent necessarily changes some appearance unless midgray shading already provides room. Do not promise luminance invariance from arbitrary tinting.

For a genuine transparent overlay, keep alpha coverage distinct from chromatic intensity and use premultiplied channels. Source-over composition is `c_out = c_src + (1-alpha_src)*c_dst`, with `alpha_out = alpha_src + (1-alpha_src)*alpha_dst`. Recover unassociated RGB only if `alpha_out > 0`; choose a declared zero RGB at zero alpha. Premultiplication prevents transparent-edge color contamination during filtering, but does not itself establish the light/color space. [W3C Compositing and Blending Level 1, simple alpha compositing](https://www.w3.org/TR/compositing-1/#simplealphacompositing).

Oklab is a credible comparison when transitions between accents look uneven in linear RGB. Its `L,a,b` axes approximately separate lightness and chromatic components, and its author provides forward/inverse transforms and discusses perceptual limitations. It is not a guarantee of identical appearance across viewers or displays. Treat Oklab as interpolation space and linear RGB as the compositing space; explicitly gamut-map before final composition. In OkLCh, hue is undefined at zero chroma, and hue path choices must be specified, particularly when returning to monochrome. Cartesian Oklab interpolation avoids that hue singularity. [B. Ottosson, *A perceptual color space for image processing*](https://bottosson.github.io/posts/oklab/).

Recommended progression: one fixed sRGB accent with linear-light tinting; compare the resulting transitions visually; add Oklab only if the controlled study demonstrates a benefit. Out-of-gamut clipping is deterministic but may change hue/lightness; count and report it. A more elaborate gamut mapper adds cost and policy decisions and should have reference vectors. Do not introduce HDR during the first color investigation.

### 19.1 Bounded temporal envelope

For `q=clip(u,0,1)`, use the independently derived quintic `S(q)=6q^5-15q^4+10q^3`. It has zero first and second derivatives at the endpoints. A nonoverlapping attack/hold/release envelope is

\[
I(t)=I_{max} S((t-t_a)/T_a)\,[1-S((t-t_r)/T_r)],\quad t_r\ge t_a+T_a.
\]

Outside the active interval return exactly zero, not an asymptotic residual. This produces bounded continuous values with continuous first/second derivatives for the planned endpoints. Discrete sampling and quantization still require rendered checks; continuity of a scalar does not prove visual smoothness. When changing a cue while a transition is active, either reject the overlap in the first implementation or use a bounded Hermite segment matching the current value and slope. Restarting an envelope at zero creates a discontinuity.

The following **proposed illustrative Python** is unexecuted. It assumes schema/domain checks have already succeeded; it is neither a production module nor independently tested reference code.

```python
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class ColorCue:
    mode: str                  # "auto", "indexed", "monochrome"
    color_id: str | None
    accepted_proposal_id: str | None = None

def lookup_color(palette, color_id):
    try:
        return palette.by_id[color_id]
    except KeyError:
        raise ValueError(f"unknown explicit color ID: {color_id}") from None

def resolve_color(cue, palette, color_enabled):
    if not color_enabled or cue.mode == "monochrome":
        return None
    if cue.mode == "indexed":
        return lookup_color(palette, cue.color_id)
    # Keyword inference alone never enters this path: acceptance is explicit.
    return (lookup_color(palette, cue.accepted_proposal_id)
            if cue.accepted_proposal_id is not None else None)

def smooth5(u):
    q = min(1.0, max(0.0, u))
    return q*q*q * (10.0 + q*(-15.0 + 6.0*q))

def envelope(tick, start, attack, release_start, release, peak):
    # Validated integer tick inputs; attack, release > 0;
    # release_start >= start + attack; 0 <= peak <= palette maximum.
    if tick <= start or tick >= release_start + release:
        return 0.0
    return peak * smooth5((tick-start)/attack) * (
        1.0-smooth5((tick-release_start)/release))

def srgb_decode(c):
    return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4

def srgb_encode(l):
    return 12.92*l if l <= 0.0031308 else 1.055*l**(1/2.4)-0.055

def tint_opaque_pixel(base_linear, tint_linear, intensity, mask):
    # Each tuple is validated finite linear RGB in [0,1]; mask in [0,1].
    a = intensity * mask
    return tuple((1.0-a)*b + a*c for b,c in zip(base_linear,tint_linear))

def history_step(previous, observation, elapsed_s, half_life_s):
    # Observation is a scalar intensity, not a rendered image.
    retain = math.exp(-math.log(2.0)*elapsed_s/half_life_s)
    return retain*previous + (1.0-retain)*observation
```

### 19.2 Local regions, history and anticipation

For a feature-local elliptical mask, transform the pixel/world point by the inverse attachment frame: `u = A_feature^-1 (x - p_feature)`, with valid invertible scale/rotation. With `r=sqrt((u_x/r_x)^2+(u_y/r_y)^2)`, let `M=1-S((r-r_inner)/(r_outer-r_inner))`, where `0<=r_inner<r_outer`; clamp by character coverage. This gives a soft localized mask attached to the character as it moves. Coverage describes geometry; the mask describes where color is allowed. A topology-changing field needs persistent feature metadata because inferring a landmark from the brightest pixel or current Gaussian maximum can jump across frames.

Protect the mustache by an explicit protected-feature mask or dedicated layer. `M_effective = M_region * (1-M_mustache)` when that feature is protected. Character/scene directives may deliberately authorize a special treatment, which must be explicit and logged. Palette lookup must not remove a feature, change its attachment or change opacity of its identity contour by accident.

Historical color persistence can be a single bounded EWMA per region:

\[
m_{n+1}=e^{-\ln2\,\Delta/H}m_n+(1-e^{-\ln2\,\Delta/H})I_n,
\quad I^*=(1-\eta)I_n+\eta m_n,
\quad 0\le\eta\le\eta_{max}\le1.
\]

This is a convex combination and stays bounded when inputs are bounded. `H` is a half-life measured in seconds; the observer uses the elapsed sample interval, not a fixed per-frame multiplier. It adds lag and may blur intentionally sharp narrative transitions. It is ordinary history, not Phase-Memory. On a scene cut, seek, character removal or explicit reset, reinitialize deterministically. At the authored release deadline, force the inactive target to zero and apply a specified finite terminal segment; an EWMA alone never reaches exact zero in real arithmetic. Store the scalar plus last sample tick; replay/seek must reconstruct it from a checkpoint with history and palette versions.

An anticipatory scripted cue is a known event, not an inferred prediction. If the script explicitly permits a lead `L>0` and event onset is `t_e`, a proposed anticipation ramp is `I_pre(t)=I_lead S((t-(t_e-L))/L)` before `t_e`, then a joined main envelope begins from `I_lead`. Default lead is zero, especially for discoveries where early gold would reveal the plot. If cue permission is false, future information must have no effect on present output. Historical extrapolation, by contrast, estimates future intensity from past observations and requires prediction-error validation. The first color experiment needs neither form of prediction.

Color may consume a normalized expressive scalar shared with motion, but it must have a separate mapping, limit, half-life and termination rule. Never reuse raw acceleration, unbounded phase drift or a camera velocity directly as alpha. Avoid closed-loop color-to-motion-to-color feedback in the initial research architecture.

## 20. Visual safety: standards and their exact scope

**Normative web target:** WCAG 2.2 SC 2.3.1 (Level A) permits no more than three flashes in any one-second period **or** flashing below its general/red thresholds. The general definition uses paired opposing relative-luminance changes of at least `0.10`, with darker state below `0.80`. Its area alternative is no more than `0.006 sr` within any 10-degree visual field, described as 25% of that field. This is not 25% of the entire exported frame. A flash is two opposing transitions, not each changed frame. WCAG also provides a fine balanced-pattern exception with elements smaller than 0.1 degree. [WCAG 2.2, SC 2.3.1 and glossary](https://www.w3.org/TR/WCAG22/#three-flashes-or-below-threshold).

**Current explanatory red definition:** the WCAG Understanding document describes a working definition involving `R/(R+G+B)>=0.8` in at least one state and a greater-than-`0.2` difference in CIE 1976 UCS `u',v'` chromaticity. RGB is linearized and converted to XYZ. Handle black/zero denominators explicitly. The page advises testing full-screen presentation, loop boundaries and the highest-dynamic-range version. Its reference 341×256 viewport is tied to stated viewing assumptions; it is not a universal 87,296-pixel hazardous-area threshold. [W3C Understanding SC 2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html).

**Stricter web target:** WCAG SC 2.3.2 (Level AAA) does not allow more than three flashes in any one-second period, regardless of size or brightness. It reduces risk and does not eliminate risk for every viewer. [W3C Understanding SC 2.3.2](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes.html). G19 notes that seven alternating transitions represent 3.5 flashes, not three complete flashes that can be rounded down; its procedure also checks starting/ending light-dark state when three flashes occur. Test rolling one-second intervals, not calendar-aligned buckets. [W3C Technique G19](https://www.w3.org/WAI/WCAG22/Techniques/general/G19).

**Broadcast reference:** ITU-R BT.1702-3 (November 2023), Annex 1, gives a different display-luminance framework: opposing changes of at least `20 cd/m²` below a darker-state `160 cd/m²`, with HDR contrast treatment above that level, and separate saturated-red concern. Its informative pattern guidance flags more than five light-dark stripe pairs occupying over 40% of displayed area when stationary, or over 25% when changing direction/oscillating/flashing/reversing contrast, with specified luminance conditions. Clearly flowing one-direction patterns have a stated exception. These broadcast percentages must not replace WCAG's visual-angle test. The Recommendation discusses risks from repeated sequences and limits of risk elimination. [ITU-R BT.1702-3, Annex 1 and informative Attachment 1](https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1702-3-202311-I!!PDF-E.pdf).

ISO 9241-391:2016 covers requirements, analysis and compliance tests for reducing photosensitive seizures from electronic-display imagery. Its public catalog says the edition is current and notes revision activity. The full paid standard was not obtained in this audit, so no clause-level ISO conformance claim is made. [ISO public catalog](https://www.iso.org/standard/56350.html). Distribution-specific requirements must be checked before actual publication; the above references are engineering inputs, not a finding that every planned distribution is governed by the same rule.

### 20.1 Proposed conservative authoring policy

These are project proposals, not standard thresholds or clinical safety advice:

1. Avoid intentional flashes and repeated contrast reversal. Do not use saturated red for rapid transitions. Slow ramps and small restrained accents are preferable starting materials.
2. Use a configurable minimum transition duration, such as an initial 0.5-second experimental floor, plus limits on intensity/slew. Record that this is a tunable conservative heuristic, not a validated seizure-prevention threshold.
3. Permit sustained low accents and expressive local changes; reject unreviewed strobe effects. Bound cumulative overlays and allow only one effective controller per region initially.
4. Preserve monochrome as a selectable artistic baseline, while recognizing that black-white motion, zooming stripes, scene cuts and fine raster aliasing can still create provocative sequences. Grayscale output alone does not establish safety.
5. Defer HDR. A future HDR path needs actual transfer functions, mastering/display assumptions, display-luminance analysis and independent validation; an SDR relative-luminance proxy cannot certify HDR.

A `max_dI/dt` bound helps constrain one controller. It does not constrain final screen luminance when masks move, camera zoom enlarges regions, geometry reverses coverage or several cues overlap. Temporal smoothing alone cannot replace export analysis. The safety controller should report compromises rather than silently modify script semantics.

### 20.2 Proposed frame-sequence validation architecture

`visual_safety.py` is a future screening and reporting tool until independently validated against trusted fixtures/analyzers. Do not label its output “certified safe.” A complete implementation is outside this pre-code assignment.

1. Decode the **final encoded distribution copy**, preserving presentation timestamps, durations, frame order, color primaries/transfer/matrix and range metadata. Also analyze the uncompressed master to locate whether encoding introduced problems. Include opening/closing graphics, subtitles, cuts, fades, camera transformations and the last-to-first boundary of looping assets. Validate each resolution/frame-rate/profile variant.
2. Convert SDR samples correctly to linear RGB/relative luminance `Y=0.2126R+0.7152G+0.0722B`. Analyze spatially local signals/areas. Whole-frame mean brightness can hide equally large brightening and darkening regions; a single maximum frame difference can overflag harmless motion.
3. Track local peaks, troughs and opposing transitions over rolling one-second windows. Include half-flashes and boundary cases. Aggregate concurrently flashing regions according to the selected standard and documented display geometry. Do not treat adjacent-frame differences alone as complete flashes.
4. Analyze saturated-red transitions separately, using a pinned rule definition. Do not substitute RGB Euclidean distance or an obsolete red-only proxy while claiming current WCAG testing. Retain black/zero-chromaticity edge cases and color conversion vectors in the test suite.
5. Screen high-contrast repetitive patterns, rotations, oscillations, zoom aliasing and broad-field motion separately. A future FFT/spatial-frequency score can flag candidates for creator review; it is not by itself a standard-compliant pattern detector. Require a report identifying the actual bands, stripe counts, area, contrast and temporal behavior examined.
6. Export timestamps, rule IDs, region heat maps, transition traces, affected-area plots, profile assumptions, severity and analysis uncertainty. The automated result is `pass-under-declared-checks`, `fail`, or `inconclusive`. Attach analyzer/version/hash, input hash and creator review record.
7. Fail the publication gate on a standards failure or inconclusive required check. Modify/rerender/reanalyze; compare with an established independent flash-and-pattern analyzer before episodes are released. Expert accessibility review is needed when the artistic material approaches thresholds or the analyzer disagrees with another tool.

W3C G15 explicitly favors modifying or withholding material that violates flash thresholds; warnings may be missed or not understood, so they cannot serve as the correction. [W3C Technique G15](https://www.w3.org/WAI/WCAG22/Techniques/general/G15). An internal validator needs both false-positive and false-negative fixtures, known expected classifications, fractional/variable timestamp cases, antialiasing/compression cases and comparisons to an independent analyzer. No successful automated result guarantees seizure prevention.

### 20.3 Reduced effects and warning proposal

Proposed reduced-effects preset: no deliberate flashing; lower accent chroma/intensity; slower envelope and recovery; no color anticipation; no optional residual oscillation; restrained camera movement/zoom; reduced high-contrast repetitive patterns. Keep narrative landmarks recognizable and supply equivalent script/caption meaning so color is not the only cue. Analyze this variant separately. A web player can honor the user's reduced-motion preference, but a prerecorded movie needs an actual alternate render or an explicitly selected playback version. [Media Queries Level 5, `prefers-reduced-motion` (Working Draft)](https://www.w3.org/TR/mediaqueries-5/#prefers-reduced-motion).

Proposed copy, to be tailored to the episode and only mention an alternate version when it exists:

> Photosensitivity notice: This episode contains high-contrast animation and changing light and color effects that may affect some viewers. A reduced-effects version is available. Choose the version that is appropriate for you.

If the episode actually contains flashing, say “flashing imagery” plainly. Present a stable readable opening card before animation and repeat the notice near playback controls; provide an accessible spoken notice where suitable. Avoid animated warning text. Do not call the reduced-effects version safe for everyone. The creative intent to show a warning does not authorize releasing a failed sequence. Ofcom's television code separately requires precautions and provides warning provisions in particular editorially justified cases; it is a jurisdiction-specific broadcast rule, not a generic warning exemption. [Ofcom Broadcasting Code, rule 2.12](https://www.ofcom.org.uk/tv-radio-and-on-demand/broadcast-standards/section-two-harm-offence).

## 21. Controlled future color study

Hold geometry, motion trajectories, framing, cues, duration, output sampling, masks, audio/script and export profile constant. Color controllers should operate on a fixed recorded state trace in the first study so feedback cannot change the matched motion. Evaluate scripted anticipation and history-based prediction separately.

| Condition | Color behavior | Principal question |
|---|---|---|
| C0 | Original monochrome | Baseline identity, clarity and creator preference |
| C1 | Explicit indexed scripted colors with bounded envelopes | Does selective color improve recognition of intended narrative beats without undermining monochrome identity? |
| C2 | C1 plus bounded scalar history/persistence | Does persistence improve continuity or merely add lag, unwanted residue and ambiguity? |
| C3a | C1 plus authorized known-script anticipation | Is a lead useful without revealing a narrative event too early? |
| C3b | C1 plus historical extrapolation, if later justified | Does measured prediction accuracy justify added control compared with simply lengthening the envelope? |
| C4 (optional) | Qualified phase diagnostic adapter | Does valid phase information add information beyond the same history and energy features? |

Include a strong simpler competitor: retuned C1 with longer release or a one-pole smoothing filter. Equalize peak intensity, colored-area budget and total accent exposure when the research question permits; otherwise report their differences as confounds. Keep C0 black-white even though it cannot match chromatic energy. Counterbalance presentation order, hide technical condition names, use paired clips and contact sheets, collect creator choices/reasons and, if useful, external viewer ratings. Do not recruit photosensitive participants for provocative validation footage.

Separate numerical metrics from artistic judgments: control continuity, maximum/rms first and second time derivatives of intensity, interframe Oklab distance, luminance-change distributions, fraction/area of colored pixels, return-to-monochrome time, gamut excursions, safety flags, identical replay hashes, process time and peak memory. Pixel color differences also reflect movement; use stable feature-local samples and controller traces to isolate color behavior. A low frame difference can reward lifeless desaturation and does not prove storytelling quality.

Pre-register provisional acceptance criteria before seeing comparisons: zero invalid states and permission violations; exact replay in the declared environment; no new required safety failures; recovery by the agreed deadline; bounded cost within an agreed budget; and a repeatable creator preference or task-specific comprehension benefit over both C1 and its simpler retuned competitor. Choose numerical margins after the first C1 measurement, record them before comparing C2/C3, and avoid inventing universal perceptual thresholds. Reject or defer history/prediction if benefit is absent, inconsistent, explained by extra accent time, or outweighed by lag, plot leakage, tuning difficulty, safety burden or computation.

## 22. Read-only upstream audit at pinned revisions

All revision pins below were obtained from the repository's `main` branch through GitHub read tools. Pinned implementation, tests, package/build configuration and license files were inspected. No upstream tests, firmware, shader, plugin or animation was run in this assignment. A source test demonstrates intended coverage, not a passing test result or product readiness.

### 22.1 AeroCam

**Pin:** `dfeen87/AeroCam` at `75208489a7c9bea2efec5107d1f0f0614110eb9d` (repository version 4.1.0). [Pinned tree](https://github.com/dfeen87/AeroCam/tree/75208489a7c9bea2efec5107d1f0f0614110eb9d).

Verified relevant implementation:

- `src/quaternion.cpp`: axis-angle and angular-velocity construction, normalization, multiplication, rotation and shortest-sign SLERP with a near-coincident normalized linear branch. SLERP assumes suitable unit-quaternion inputs; the function does not explicitly validate finite inputs, bound `t`, normalize both input arguments or clamp the dot before `acos`. `tests/test_quaternion.cpp` inspected here tests identity and a 90-degree rotation, not the difficult SLERP cases. Possible future reuse is a mathematical reference for a separately authorized 3D camera adapter, after tests for identity, antipodal equivalence, near coincidence, nonunit/nonfinite inputs and interpolation endpoints. Build 0 is 2D and needs none of this. [Quaternion implementation](https://github.com/dfeen87/AeroCam/blob/75208489a7c9bea2efec5107d1f0f0614110eb9d/src/quaternion.cpp), [inspected quaternion tests](https://github.com/dfeen87/AeroCam/blob/75208489a7c9bea2efec5107d1f0f0614110eb9d/tests/test_quaternion.cpp).
- `src/motion_deblur.cpp`: relative quaternion warp `H=K R K^-1`, directional Gaussian point-spread kernel generation and Gaussian gain. This is camera/video math, not character fluid geometry or a demonstrated restoration pipeline. Require positive focal lengths, valid normalized orientations, positive sigma and legal kernel dimensions before adaptation. The homography models a rotational camera/image relation; it does not reconstruct missing depth or turn a 2D character into 3D. [Motion/deblur source](https://github.com/dfeen87/AeroCam/blob/75208489a7c9bea2efec5107d1f0f0614110eb9d/src/motion_deblur.cpp).
- `src/aerocam_stabilizer.cpp`: the class named `ExtendedKalmanFilter` initializes `P/Q/R`, but the inspected update uses fixed gain `0.5` and does not perform covariance evolution/update there. `predict` uses the supplied acceleration directly as world acceleration; `update` converts accelerometer readings to acceleration, then reuses that vector as measured velocity. These observed unit/frame limitations prevent treating the naming/README as evidence of a complete physically valid EKF. The Gaussian command `-e exp(-||e||²/(2 sigma²))` is present; its magnitude decreases toward zero at very large errors and is not an unconditional recovery/stability theorem. Do not port it as a replacement for Build 0's spring. [Stabilizer source, especially lines 89–105 and 123–178](https://github.com/dfeen87/AeroCam/blob/75208489a7c9bea2efec5107d1f0f0614110eb9d/src/aerocam_stabilizer.cpp).
- `snap/ts/src/MotionMoodEngine.ts`: velocity/spin/stability thresholds select static named presets, saturation/contrast, 4×4 grading matrices and suggestion text. This is genuine preset-selection code. No temporal indexed emotional envelope, script override, localized character mask or photosensitivity validator is present in that inspected file. It is therefore a comparison for what the new color system must specify, not proof that Section 0 is already implemented. [MotionMoodEngine](https://github.com/dfeen87/AeroCam/blob/75208489a7c9bea2efec5107d1f0f0614110eb9d/snap/ts/src/MotionMoodEngine.ts).

`CMakeLists.txt` contains an embedded path and an `AEROCAM_TESTS` native C++20 library/test path; tests include quaternion, EKF, IMU driver and Snap components. Embedded code has MCU/HAL dependencies, while wholesale import would introduce C++/toolchain, TypeScript/Snap and application-domain overhead. Inspect exact files before any isolated reuse. MIT license names Don Michael Feeney Jr.; copied/substantially adapted software must retain the copyright and permission notice. Scholarly/project attribution is separate from that notice. The README's broad real-time, plugin, deblur and platform claims were not independently measured. [CMake](https://github.com/dfeen87/AeroCam/blob/75208489a7c9bea2efec5107d1f0f0614110eb9d/CMakeLists.txt), [license](https://github.com/dfeen87/AeroCam/blob/75208489a7c9bea2efec5107d1f0f0614110eb9d/LICENSE).

**Integration recommendation:** no Build 0 import. Future camera/motion research may study the narrow quaternion/homography/math pieces with explicit unit/frame adapters. Do not conflate the README's AI-Lex energy equation with AILEE Trust Layer governance or infer a shared validated animation runtime from the name.

### 22.2 SPECS Optical Compensation Layer

**Pin:** `dfeen87/SPECS-Optical-Compensation-Layer` at `6af955bb09fceb9dbad3bec448667d788a131efc` (2.0.0). [Pinned tree](https://github.com/dfeen87/SPECS-Optical-Compensation-Layer/tree/6af955bb09fceb9dbad3bec448667d788a131efc).

`distortion_model.py` validates finite native-compatible coefficients, positive `fx/fy`, matrix/translation shapes and uint64 timestamp; builds `K[R|t]` and a flattened row-major 4×4 interchange matrix; exports through a temporary file followed by replacement; and applies sensor eye-offset updates without mutating the base mapping. It uses the Python standard library. This supplies useful examples for explicit coordinate/serialization and reject-before-export boundaries, not a required animation dependency. Shape/finiteness checks on `R` are not proof that it is an orthonormal rotation. [Calibration source](https://github.com/dfeen87/SPECS-Optical-Compensation-Layer/blob/6af955bb09fceb9dbad3bec448667d788a131efc/distortion_model.py).

`shaders/corrective.frag` maps UV coordinates to centered lens space, computes Brown–Conrady radial/tangential terms, guards radial denominator with `max(...,1e-6)`, applies a single inverse-style mapping and samples the input texture. This is a spatial correction shader, not emotional color interpolation. The single correction step is an approximation to inversion; it does not prove a global inverse for arbitrary distortion coefficients, and denominator clamping does not guarantee a fold-free map. Texture border handling remains a host responsibility. [Corrective fragment shader](https://github.com/dfeen87/SPECS-Optical-Compensation-Layer/blob/6af955bb09fceb9dbad3bec448667d788a131efc/shaders/corrective.frag).

The public `GraphicsApi`/pipeline interfaces and native source separate graphics calls, loading, shader lifecycle and callbacks. `tests/test_distortion_model.py` inspects projection coefficients, sensor update, atomic export behavior, invalid timestamps/numerics/shapes and preservation after invalid export. `tests/test_bridge.cpp` uses fake graphics to test JSON boundaries, shader resource cleanup, call order and fail-before-draw validation. Those tests do not constitute rendered GPU output comparisons or a performance benchmark. [Python tests](https://github.com/dfeen87/SPECS-Optical-Compensation-Layer/blob/6af955bb09fceb9dbad3bec448667d788a131efc/tests/test_distortion_model.py), [native fake-graphics tests](https://github.com/dfeen87/SPECS-Optical-Compensation-Layer/blob/6af955bb09fceb9dbad3bec448667d788a131efc/tests/test_bridge.cpp).

Dependencies are Python 3.10+ for calibration, C++17/CMake 3.16+ for native code and host-provided OpenGL/GLSL 3.30 support for actual rendering. The project deliberately supplies no device/window/OpenGL-loader application. MIT license is Don Michael Feeney Jr.; `CITATION.cff` names Don Michael Feeney and version 2.0.0. Preserve the applicable notice on copied/adapted software and cite scholarly work appropriately. [README requirements](https://github.com/dfeen87/SPECS-Optical-Compensation-Layer/blob/6af955bb09fceb9dbad3bec448667d788a131efc/README.md), [CMake](https://github.com/dfeen87/SPECS-Optical-Compensation-Layer/blob/6af955bb09fceb9dbad3bec448667d788a131efc/CMakeLists.txt), [license](https://github.com/dfeen87/SPECS-Optical-Compensation-Layer/blob/6af955bb09fceb9dbad3bec448667d788a131efc/LICENSE), [citation](https://github.com/dfeen87/SPECS-Optical-Compensation-Layer/blob/6af955bb09fceb9dbad3bec448667d788a131efc/CITATION.cff).

**Integration recommendation:** conceptual influence only for Build 0. A future color compositor should remain a small independent numeric stage. Optical-warp experiments are separately authorized future work and require adapters for world-to-mask/UV conventions, row/column matrix convention, out-of-bounds samples and landmark visibility. An optical transform that distorts the Commander's mustache may be artistically unacceptable even if numerically finite.

### 22.3 Letter-Depth Encoding in UFO

**Discovery:** no separate repository named Letter-Depth Encoding was found in the accessible owner listing/search. Actual implementation, tests and a paper text extraction were found in `dfeen87/UFO`, so the source is available rather than wholly unverified.

**Pin:** `dfeen87/UFO` at `da4eb5f4a96b29bb0e34a8ac2a89dc695764cd2d`, package `radial_membrane_ai` version 5.0.0. [Pinned LDE directory](https://github.com/dfeen87/UFO/tree/da4eb5f4a96b29bb0e34a8ac2a89dc695764cd2d/radial_membrane_ai/lde).

`lde/models.py` defines symbol/config/state/boundary records. `lde/pipeline.py` computes activation by symbol frequency, spread, boundary participation, repetition pressure, local gap tension, stiffness and directed adjacency coherence. Depth is a weighted combination of descriptive terms. It samples a polar boundary using `r(theta)=r0+sum_l depth_l max(0,cos(distance(theta,theta_l)))`, then calculates first and second radial finite differences. The field named `curvature_map` in this path is `r''` approximated by a second difference, not the full curvature of a polar plane curve. The half-wave-clamped cosine basis also has derivative kinks at its support boundary; do not infer global smoothness from a smooth-looking plot. [LDE pipeline, especially lines 80–175 and 210–247](https://github.com/dfeen87/UFO/blob/da4eb5f4a96b29bb0e34a8ac2a89dc695764cd2d/radial_membrane_ai/lde/pipeline.py).

The same file explicitly states that geometry alone is insufficient for lossless text reconstruction and requires retained ordering/casing/insertion metadata. This supports a useful architectural analogy: persistent character identity must live in explicit feature metadata instead of being inferred solely from the deformed field. It is not a theorem that LDE preserves the Commander's visual identity, nor a semantic emotion detector. Its `phase` is an assigned symbol angle, which must not be conflated with temporal analytic-signal phase or the Krüger–Feeney Phase-Memory Operator. [LDE reconstruct, lines 310–338](https://github.com/dfeen87/UFO/blob/da4eb5f4a96b29bb0e34a8ac2a89dc695764cd2d/radial_membrane_ai/lde/pipeline.py), [models](https://github.com/dfeen87/UFO/blob/da4eb5f4a96b29bb0e34a8ac2a89dc695764cd2d/radial_membrane_ai/lde/models.py).

Inspected tests check ordinary encoding, expected array sizes, absent symbols, gap edge cases, empty/punctuation inputs and a Unicode reconstruction mismatch. A specific documentation discrepancy is material: the traceability document's broad Unicode round-trip claim must not be generalized to this LDE entry point. `lde_encode` lines 40–47 lowercases recognized symbols and retains a casing bit; the Kelvin sign `K` therefore becomes `k` and reconstructs as `K`, causing the deliberate full-mode verification rejection asserted by `test_reconstruction_failure_verification`. This is source-level evidence of a restricted domain and fail-closed behavior, not a universally lossless API. The document's “implemented and tested” labels are upstream claims; this audit did not execute those tests. A primary paper PDF is indexed in `docs/papers`, and its checked-in text extraction was inspected; PDF layout/equation fidelity and publication/peer-review status were not independently certified. [LDE tests](https://github.com/dfeen87/UFO/blob/da4eb5f4a96b29bb0e34a8ac2a89dc695764cd2d/radial_membrane_ai/tests/test_lde_pipeline.py), [traceability](https://github.com/dfeen87/UFO/blob/da4eb5f4a96b29bb0e34a8ac2a89dc695764cd2d/docs/PAPER_IMPLEMENTATION_TRACEABILITY.md), [paper text extraction](https://github.com/dfeen87/UFO/blob/da4eb5f4a96b29bb0e34a8ac2a89dc695764cd2d/research/lde-analysis/lde_paper_text.txt).

The direct `LDEConfig.validate` and `LDEBoundaryGeometry.validate` methods inspected here use sign/shape checks without comprehensive explicit finiteness/type checks. In particular, a sign comparison does not reject NaN. Do not treat these methods as Commander-ZORG's numerical admission guard; an adapter would need its own strict finite/domain validation and atomic rejection contract. This is a source-inspection finding, not an executed adversarial test result. [LDE validation methods](https://github.com/dfeen87/UFO/blob/da4eb5f4a96b29bb0e34a8ac2a89dc695764cd2d/radial_membrane_ai/lde/models.py).

The narrow pipeline imports NumPy and local records/exceptions. Whole-package dependencies include Python 3.11+, NumPy, SciPy, SymPy, NetworkX, Pydantic, typing-extensions and Matplotlib; importing the full simulation for a small animation adapter would add unjustified complexity. The root MIT license names Don Michael Feeney Jr.; retain the software notice on substantial reuse and independently check the publication's attribution/license if adapting paper material. No software license automatically establishes rights for every third-party paper or asset in a repository. [Package declaration](https://github.com/dfeen87/UFO/blob/da4eb5f4a96b29bb0e34a8ac2a89dc695764cd2d/pyproject.toml), [license](https://github.com/dfeen87/UFO/blob/da4eb5f4a96b29bb0e34a8ac2a89dc695764cd2d/LICENSE).

**Integration recommendation:** no Build 0 import. After feature/identity design exists, investigate a small explicit symbolic-to-expression adapter with independently normalized outputs and tests; compare against directly scripted scalars. Defer any automatic text-to-emotion-to-color mapping unless it demonstrates benefit over creator-authored cues and respects overrides.

## 23. Priority recommendations for the consolidated roadmap

1. Implement and verify the existing v0.3 monochrome Build 0 only, following the separate baseline audit and its proposed clarifications. Maintain repository privacy; this assignment authorizes no upstream write.
2. Establish persistent feature identities/local frames and mustache protection before expressive deformation or feature-target cameras are attempted. Geometric validity and recognizable identity are separate acceptance tests.
3. Study independent scalar historical observation and target conditioning on recorded low-dimensional motion; do not import AeroCam's control loop or LDE's semantic metaphors as validated motion physics.
4. Run scripted local-color C1 with an indexed palette, quintic envelopes and linear-light compositor. Compare to monochrome before authorizing memory-conditioned colors or perceptual interpolation dependencies.
5. Build an independently validated export-time safety workflow before released episodes. Include geometry/camera/editing effects, warnings and a separately analyzed reduced-effects version. Keep formal standards checks distinct from conservative authoring heuristics.
6. Permit history/anticipation only if matched experiments beat simpler envelopes; separately research qualified Phase-Memory features with the original scholarly attribution and exact operator definitions.
7. Investigate 2D feature-focused framing/zoom with explicit cinematic directives and bounded camera controls. Color salience and recent feature history may propose focal priorities, but explicit focus wins and the camera never moves geometry to satisfy composition. Reanalyze the final framed export because zoom changes hazardous area and high-contrast pattern scale. Genuine 3D viewpoint changes, optical correction, GPU frameworks and wholesale upstream integrations remain deferred.

All numerical improvements, real-time throughput, GPU gains, stronger narrative comprehension and better animation quality remain unmeasured hypotheses for Commander-ZORG.


## 24 Additional proposed color code contracts

The following illustrative Python fills out mask selection, history conditioning, permitted scripted anticipation and exact monochrome restoration. It is proposed, unexecuted code with preconditions, not a production implementation. These examples operate independently of the geometry solver. A real future implementation must validate types, finite inputs, shape/ownership, palette permissions and all cross-field timing relations before rendering.

```python
import numpy as np

def feature_region_mask(points_world, origin, local_to_world,
                        radii, inner, outer, coverage, protected):
    # points_world is [...,2]; local_to_world is a validated invertible 2x2
    # attachment transform. radii are positive; 0 <= inner < outer.
    # coverage and protected are matching arrays in [0,1].
    local = np.linalg.solve(
        local_to_world,
        (points_world-origin).reshape(-1, 2).T
    ).T.reshape(points_world.shape)
    r = np.sqrt(np.sum((local / radii)**2, axis=-1))
    q = np.clip((r-inner)/(outer-inner), 0.0, 1.0)
    smooth = q*q*q*(10.0 + q*(-15.0 + 6.0*q))
    return (1.0-smooth) * coverage * (1.0-protected)

def conditioned_intensity(script_value, memory_value, history_weight,
                          history_permitted, tick, fade_start, fade_ticks):
    # fade_start is at or after the scripted support. fade_ticks > 0.
    # The planned finite fade gates persistence without a hard cutoff jump.
    eta = history_weight if history_permitted else 0.0
    raw = (1.0-eta)*script_value + eta*memory_value
    if tick >= fade_start + fade_ticks:
        return 0.0
    if tick <= fade_start:
        return raw
    q = (tick-fade_start)/fade_ticks
    return raw * (1.0-smooth5(q))

def authored_color_intensity(tick, event_tick, attack_ticks, hold_ticks,
                            release_ticks, peak, requested_lead_ticks,
                            cue_allows_lead, palette_allows_lead,
                            max_lead_ticks):
    # All quantities validated; attack/release positive, peak within entry cap.
    # Explicit future-script permissions are required on BOTH cue and palette.
    allowed = cue_allows_lead and palette_allows_lead
    lead = requested_lead_ticks if allowed else 0
    if lead > max_lead_ticks:
        raise ValueError("requested anticipation exceeds permitted horizon")
    if lead:
        # Pre-event attack reaches peak at the event. It is script lookahead.
        start, attack = event_tick-lead, lead
        release_start = event_tick+hold_ticks
    else:
        start, attack = event_tick, attack_ticks
        release_start = event_tick+attack_ticks+hold_ticks
    return envelope(tick, start, attack, release_start, release_ticks, peak)

def composite_region(base_linear_rgb, tint_linear_rgb, intensity, region_mask):
    # Arrays validated; intensity and mask bounded in [0,1].
    if intensity == 0.0:
        return base_linear_rgb.copy()  # exact baseline, owned output
    amount = (intensity*region_mask)[..., None]
    return (1.0-amount)*base_linear_rgb + amount*tint_linear_rgb
```

Here `smooth5` and `envelope` are the proposed functions in the earlier color section. `protected` is a geometric feature mask with matching coordinates, not an emotional label. Select it through persistent region/feature IDs and attachment definitions. Do not use a camera-dependent brightest-pixel tracker for the mustache. The palette and cue resolver should reject cross-character feature references unless a deliberate cross-character effect has its own valid contract.

The explicit false-permission path has zero lead and must produce exactly the same current output when unavailable future cues change. This example deliberately replaces the ordinary attack with a pre-event attack, reaching peak at the event. It changes accent exposure and post-event timing relative to the no-lead case; match or report those differences in the comparison. Memory permission false sets its influence to zero. The terminal fade reaches exact zero on a declared tick, but sampled memory updates can still step between samples; this does not prove whole-path derivative continuity. Interpolation or an additional independently tested envelope is needed if that continuity is required. The compositor returns an owned copy of the original linear baseline at zero intensity; the same output conversion then restores identical monochrome pixels. If multiple regions are later enabled, their aggregate mixture/ordering needs an additional bounded composition policy and tests.

Required future tests include protected mask leakage, singular attachment rejection, mask edge continuity, invalid color ID, ambiguous overlap, override precedence, permissions, zero/history initialization, final-zero deadline, future-information noninterference, transfer-function reference vectors, linear-light mixture endpoints, transparent premultiplied edge fixtures and exact replay. Syntax or algebra alone cannot validate these code sketches.

## 25 Consolidated research decisions

Build 0 can proceed without new runtime features, after evidence-schema decisions are recorded. Compact TMO and short-horizon PMC are credible experiments, not demonstrated animation improvements. Indexed scripted color is the simplest useful future color system; history and anticipation remain optional. Genuine Phase-Memory needs the coauthored definitions, source reconciliation and qualified causal signals before an independent adapter is justified. Identity features should have explicit local geometry/render ownership. Feature-focused cinematography should begin with 2D framing and should never modify geometry to satisfy composition. Episode release requires final-sequence safety validation, reduced effects and creator review with an honest warning; no automated test guarantees universal safety.

Prioritize E0/E1, creator review and representation quality. Then study attached features and scripted color separately, compact observation and bounded conditioning, followed by 2D camera composition. Defer Phase-Memory and AILEE control integrations until a measurable need and stronger evidence exist. Keep 3D perspective, per-pixel memory, learned predictors, GPU claims and publication outside the present assignment.
