# Commander-ZORG — Proposed Code Contracts & Implementation Blueprint v0.4

**Deliverable B · 18 October 2026 · Private · PRE-CODE**

Engineering philosophy: **Design top-down. Verify bottom-up. Release with evidence.**

This is an implementation plan and a collection of **proposed, unexecuted Python illustrations**. It is not an animation engine, executable package, tested reference implementation or record of passing gates. No repository changes, commits, publication or remote writes are authorized by this document. A later authorized coding session must independently implement and verify the accepted contracts.

## 1. Authority, status and reading rules

The supplied `COMMANDER_ZORG_Architecture_and_Prototype_v0.3.docx`, SHA256 `3d367ddc9b0a4ec239d00889b4efd8f11a756521af8b49f79dcf8569676ab1fc`, controls Build 0. `v0.3 Pxxxx` locators identify its Word body paragraphs, including blank/equation paragraphs; `§n` identifies the embedded prototype specification. Table numbers identify the tables in that DOCX. The older review's F01/B02 references are historical citations, not direct verification of those originals. Equations were checked against Office Math rather than relying on a text extract that omits equation content.

Use three distinct labels:

- **Baseline requirement:** accepted v0.3 contract, retained here without silent amendment.
- **Proposed clarification:** a v0.4 implementation/evidence choice needed to make a concrete package; freeze it in an ADR before relying on it. It does not retrospectively become a v0.3 decision.
- **Future proposal:** the creator's post-v0.3 concepts and their research interfaces. These are unimplemented, unvalidated and excluded from Build 0.

**Readiness:** the numerical baseline is sufficient to begin a small local implementation. Freeze the manifest/trace/profile schemas and verification publication sequence before claiming a release-complete package. See `research/baseline-audit.md` for the full independent derivation and findings A01–A14. There is no identified need to replace the baseline integrator or expand the runtime before coding.

## 1A Full baseline findings register

These findings refine implementation planning without changing the accepted runtime. Blocking refers to the named release claim, not starting isolated numeric work.

| ID | Classification and affected gate | Source | Finding, implication and resolution |
|---|---|---|---|
| A01 | Release-blocking documentation choice; no numerical correction | §14 P0278–P0284; §15 P0297 | Required artifact contents are strong, but exact JSON structures, schema identifiers, artifact path rules and experiment-manifest references are not enumerated. Freeze `cz-run-manifest-0.3`, trace-row shapes and `cz-experiment-0.3` before implementing the verifier. Reject duplicate records, gaps, mismatched scene hashes and escaping paths. This completes evidence interoperability; it does not change the scene schema or algorithms. |
| A02 | Release-blocking verification design choice | §14 P0281, P0284 | A final manifest must be published last, but verification is also required before publication. Implement two stages: validate a prospective manifest and closed artifacts in memory; then set/finalize and hash complete status; atomically publish manifest last; finally run the public verifier. If final verification fails, report failure and retain the take as failed/incomplete evidence. Do not pretend a final manifest already exists during prepublication checks. Neither stage requires circular self-hashing. |
| A03 | Nonblocking fixture clarification | §12 P0266 | E0 requires the same threshold and “weight policy” but does not name the policy. Freeze an explicit six-preset list and keep the element weights and threshold fixed across comparable presets, with documented home/sigma changes. If differing element counts are used, define what “same weight policy” means before the gallery. Never choose a favorable subset after reporting six presets. |
| A04 | Nonblocking convergence fixture clarification | §8 P0246; §9 P0252; §12 P0267 | A 120 Hz comparison doubles cue and recovery tick boundaries. Derive all physical-time windows from the 60 Hz nominal fixture, preserving 180 output frames at 30 fps and terminal tick 720; do not double frame count. Record output-to-tick vectors separately. Compare maximum per-element Euclidean position error, not coordinatewise error or frame-to-frame displacement. |
| A05 | Nonblocking metric precision | §11 P0261–P0263; Table 7 | Occupancy uses a thresholded mask; clipping uses any nonzero non-inverted coverage. Preserve this distinction, including 64-valued antialiasing in the border check. Freeze how optional connected-component counts are computed. Centroid distances use world units and base pixel centers, not sample centers or integer bbox centers. |
| A06 | Nonblocking orchestration clarification | §5 P0223; §10 P0255–P0258; §14 P0279 | A decision is successfully closed before in-memory commit. A subsequent state-log or frame-export failure makes the run failed/incomplete even if an ACCEPT row exists. Verify trace relationships only as completion claims for complete runs; failed traces can legitimately end between writes. Do not retrofit rollback, retries or false successful completion. |
| A07 | Nonblocking defensive input handling | §4 P0114–P0117; Table 6 | Inputs can be finite but enormous before validation. Check scalar ranges before products, squares and norms. Use a robust norm such as `hypot` for conservative force checks, or reject immediately when either component already exceeds the finite force bound. Reject JSON nesting/resource abuse with a documented reasonable parser/input-size policy if needed; avoid silently adding a scene-semantic restriction. |
| A08 | Nonblocking identity boundary | §3 P0111; §11 P0264; §16 P0302 | Persistent element IDs and group membership preserve structural ownership, not mustache recognition. Keep visual review independent. Build 0 has no promised finished Commander artwork, feature detector, attachment solver or camera. An identity issue is a reason to compare representations later, not to mark the numeric guard failed. |
| A09 | Nonblocking provenance/replay distinction | §14 P0280–P0284 | Exact same-environment replay covers ordered states, decisions, decoded pixels and PNG bytes. Operational paths/timings are excluded. Dependency version strings alone do not establish equality of compiled math or encoder behavior. Record the actual environment and source digest; use a separately labeled tolerance comparison on another environment. Integrity hashes are not signatures or independent proof of correctness. |
| A10 | Nonblocking test-oracle completeness | §8 P0246; §13/Table 8 | No runtime implementation should generate its own analytic or wrong-render oracle. Derive one-step arithmetic by hand and analytic oscillator values independently; construct an asymmetric binary raster fixture without calling the field implementation. The existing v0.3 probe table is a reference to reproduce, not test output to copy into a new report. |
| A11 | Optional future diagnostic | Review P0045–P0048; §11 P0264 | Smooth field inputs do not ensure smooth level sets near critical gradients, merges or splits. Area/frame-difference/component diagnostics can explain a take; none is an unannounced topology veto. A universal consecutive IoU threshold would incorrectly reject deliberate liquid transformations. |
| A12 | Optional future numerical alternative | Review Table 1; §8 P0241–P0246 | An exact damped-spring propagator or implicit damping could alter stability/accuracy, but would replace the specified numerical policy. Keep them as later ablations only when measured 60/120 Hz accuracy or actual artistic needs justify a versioned change. More damping is not a universal cure for explicit-damping instability. |

**A13 — nonblocking (§5 P0209–P0210; §10 P0255).** “Unchanged element ordering” is an ownership/interface contract. A state with only a tick and two anonymous arrays cannot prove semantically that a buggy function did not permute rows. Keep one compiled immutable index mapping in validated configuration; derive all parameter and target arrays from it; record that order in evidence; test asymmetric per-element one-step and group-force cases. Do not claim the numeric guard can detect an arbitrary row permutation from values alone, and do not add mutable per-state IDs contrary to the specified minimal state.

### Stability-test reachability clarification

**A14 — nonblocking (§4 P0117/Table 6; §8 P0244; §13/Table 8).** With the accepted conservative accuracy envelope, `A=(h sqrt(k/m))²<=0.0625` and `D<=0.25`, so `A+2D<=0.5625<4`. Even the scalar-range extremes at 60 Hz give `A<=1/18`, `D<=1`, hence `A+2D<=2.05556<4` before the stricter envelope. Thus a fully scene-valid configuration cannot independently exercise an unstable strict-bound failure. Retain the explicit stability check for clarity and future-proof policy, but label an out-of-range `c=130` scene test as a rejection of an invalid configuration; it does not prove that the exact strict-stability branch was reached. Test the mathematical parameter-validation helper directly with suitable outside-envelope synthetic values if that branch needs independent proof. This is test-evidence precision, not a defect requiring wider accepted ranges.

## 2. Build 0 scope and immutable policies

Build 0 is one fixed-root 2D entity with persistent positive Gaussian controls, fixed-tick semi-implicit Euler springs, explicit polynomial force cues, a deterministic ACCEPT/REJECT guard, grayscale supersampling and PNG/evidence export. It tests a visual hypothesis; it does not promise finished Commander/Zorg artwork or recognized identity.

Baseline runtime includes Python, NumPy and Pillow, with pytest for development. Record exact versions and a reproducible dependency record in the actual coding environment. SciPy, PyTorch, FFmpeg, GPU frameworks, networking and upstream imports are unnecessary. An installed video encoder is optional; PNG playback must work without it (§15 P0286).

Keep the scene schema `cz-scene-0.3`. Suggested named policies are the baseline's `gaussian-separable-v1`, `quartic-pulse-v1` and explicit recorded IDs for the specified integrator/raster/canonicalization. **Proposed clarification:** name those latter IDs `semi-implicit-explicit-damping-v1`, `uniform-grid-gray8-v1` and `cz-json-python-v1`; record them as v0.4 handoff choices, not as source names already present in v0.3.

Excluded: dual-memory/TMO/PMC, emotional color, semantic keyword inference, Phase-Memory, AILEE, audio, speech, camera motion, 3D, learned geometry, per-pixel history, plugins, runtime permissions, adapters without demonstrated use, retries/clamps/fallbacks and automatic publication. New creative directions remain research proposals. The private `dfeen87/Commander-Zorg` repository must remain private and untouched during this research assignment.

## 3. Suggested source tree and dependency direction

```text
commander_zorg/
  __init__.py          # engine/schema version constants only
  config.py           # strict parse, semantic validation, canonical resolution
  state.py            # immutable-by-contract state construction/ownership
  cues.py             # stateless midpoint force evaluation
  motion.py           # candidate numerical update, no commitment
  guard.py            # numerical validity, ACCEPT/REJECT only
  field.py            # sampling lattice and separable Gaussian field
  raster.py           # coverage quantization and mask measurements
  evidence.py         # run orchestration, files, schemas, hashes, replay/profile
  cli.py              # argument handling and truthful exit status
scenes/
  e0/                 # six explicit fully specified presets
  e1_candidate.json
  e1_cue_off.json
schemas/              # proposed documentary artifact/trace/profile schemas
adrs/                 # accepted policy and clarification records
source_snapshot/      # included in evidence at run time, not this audit
tests/
  test_config.py
  test_state.py
  test_clock.py
  test_field.py
  test_raster.py
  test_motion.py
  test_cues.py
  test_guard.py
  test_profiles.py
  test_evidence.py
  test_replay.py
  test_cli.py
  fixtures/           # hand-constructed oracles and malformed evidence
```

The illustrative tree is not an instruction to create files now. There is no need for an extensible plugin framework. Nine modules follow v0.3 P0112; a small `profiles.py` or `metrics.py` is permissible later if `evidence.py` becomes hard to inspect, provided responsibilities stay explicit.

Dependencies flow from data definitions toward orchestration: `config` is independent of all engine stages; `state` imports validated configuration types; `cues`, `motion`, `guard`, `field`, `raster` use validated types and pure array operations; `evidence` invokes them and owns file I/O; `cli` invokes `config/evidence`. No numerical module imports `cli`, opens run files, consults wall clock, draws randomness, calls a network service, or derives artistic meaning from emotion words. The verifier's frame metric calculations must use the documented formula and independent wrong-render fixtures, even if it shares small pure reduction helpers with production.

## 4. File-by-file ownership and contracts

| File | Responsibilities and data ownership | Public interfaces | Dependencies and failure behavior |
|---|---|---|---|
| `config.py` | Own raw bytes and parsed JSON until validation; return immutable resolved configuration and sorted element/cue definitions; own immutable compiled parameter arrays derived from one ID mapping. Preserve raw vs resolved hashes separately. | `load_scene(Path)->ValidatedScene`; `resolve_scene(raw)->ValidatedScene`; `resolved_mapping(scene)->dict`; pure numeric/ID helpers. | Standard JSON/math/hash/path plus NumPy only for compiled float64 arrays. Reject every schema/type/range/resource/stability/target error with field path; no run directory or output on load error. Never coerce string/null/bool to number. |
| `state.py` | Own exactly tick and distinct C-order float64 position/velocity arrays. Initial arrays copy home/zero. No config mutation, hidden clock, cue cursor, RNG or previous-state link. | `initial_state(scene)->SceneState`; `owned_state(tick,positions,velocities)->SceneState`; `state_mapping(state)->dict`. | NumPy and config types. Construction verifies structural invariants; runtime invalid-candidate diagnostics may need a separate internal carrier rather than a constructor that suppresses the guard path. Never alias caller-owned writable arrays. Frozen dataclass alone is insufficient. |
| `cues.py` | Stateless evaluation of the exact midpoint envelope and stable cue-ID sums; groups map to fixed element indices. Own newly allocated force `(N,2)` output only. | `quartic_pulse(u)->float`; `cue_forces(tick,scene)->float64[N,2]`. | Config, NumPy. Require a valid transition-start tick. Return zero outside support. Force is per member, never divided by membership count. Invalid inputs are a usage/invariant error, not a cue-dependent repair. |
| `motion.py` | Propose, never commit. Compute spring acceleration using old p/v, then new v, then new p. Own distinct candidate arrays. | `propose_step(previous,scene)->CandidateState`. | `state`, `cues`, NumPy; no guard/evidence imports. Validate previous state first at orchestration boundary. Nonfinite computation is returned/reported to the guard or converted to a classified numerical failure; never silently clipped. |
| `guard.py` | Check previous/candidate dtype, shape, finite values, tick progression, displacement and speed; evaluate one immutable policy. Own a serializable decision record, not a modified state. | `validate_previous(previous,scene)->ValidationResult`; `check_transition(previous,candidate,scene)->Decision`. | Config/state, pure math/NumPy. ACCEPT or REJECT only. Give field-specific reason codes and safe strings for nonfinite diagnostics. No fallback, retry, mutation, force override or artistic score. |
| `field.py` | Derive raster-ordered x/y supersample vectors; evaluate one Gaussian at a time in fixed ID order; own one field and reusable scratch plane. | `sample_axes(scene)->(x,y)`; `evaluate_samples(state,scene)->float64[Hs,Ws]`; independent direct reference in tests only. | Config/state/NumPy. Enforce finite samples and expected shape, fail render on nonfinite field. No normalization, truncation, camera, per-entity fusion layer or distance stepping. |
| `raster.py` | Convert nonnegative-field samples into occupancy coverage and exact gray8; measure non-inverted masks, clipping, world centroids, IoU and translation-aligned morphology. Own output pixel/mask arrays and immutable metric values. | `rasterize(samples,scene)->uint8[H,W]`; `measure_mask(pixels,scene)->FrameMetrics`; `iou(a,b)->float\|None`; `aligned_iou(a,b)->float\|None`. | Config/NumPy. Reject wrong shape/nonfinite data. Empty centroid/bbox/IoU union are null with reason. Invert display only; never invert geometry semantics. No PNG file I/O is needed here. |
| `evidence.py` | Own destination lifecycle, run status, transition commit, logs, frame files, contact sheet, source/environment provenance, manifest publication, independent integrity checks, experiment profile and fresh-process replay. | `render_run(scene,new_output_directory)->RunReport`; `write_gallery(...)`; `verify_integrity(manifest_path)->VerificationReport`; `verify_replay(manifest_path,new_output_directory)->ReplayReport`; `check_profile(experiment_path)->ProfileReport`. | Calls pure modules and uses pathlib/json/hashlib/Pillow/subprocess. Refuse existing output; atomic per-file publication; fail truthfully on writes; manifest last; no resume or automatic Git mutation. A handled failure retains useful evidence and may not claim completion. |
| `cli.py` | Parse explicit commands, validate before allocation/output, call orchestration, render concise report and map typed errors to exit codes. | `main(argv=None)->int`. | Config/evidence and argparse. 0 success; 2 config/usage; 3 numeric rejection; 4 export/integrity; 5 replay mismatch; dedicated profile command 6 for failed E1 automated gates. Do not turn a failed metric profile into an export failure or hide it behind a render-success message. |

**Proposed type contract:** use frozen dataclasses/tuples for semantic definitions; compiled parameter arrays have `(N,2)` homes and `(N,)` scalar parameters, fixed ID order and write-protected owned storage. `SceneState` contains only `tick:int`, `positions:float64[N,2]`, `velocities:float64[N,2]` (§5 P0209–P0210). `CandidateState` may be the same structural type at a distinct lifecycle stage. Decision metadata is outside state. Do not add a state `emotion`, camera, memory or linked history field.

The guard cannot infer the semantic identity of anonymous array rows from values alone. One immutable ID-to-index plan, asymmetric per-element tests, stable compiled arrays and recorded order establish that contract. Do not claim the guard detects every arbitrary permutation.

## 5. Strict scene schema and validation

Every key shown in the source's complete scene is required, including an explicitly empty cue array when no cues exist. Unknown keys are errors at every nesting level. IDs match ASCII `[a-z][a-z0-9_]{0,31}`; element and cue uniqueness are separate namespaces; group names follow the same grammar. Sort elements and cues by ascending ASCII ID. Do not sort based on JSON input order, a locale or hash-table behavior (§4 P0114–P0118).

| Field | Baseline range/type |
|---|---|
| `schema_version` | Exact string `cz-scene-0.3` |
| `scene_id` | Valid ID |
| `seed` | Integer 0…18446744073709551615; provenance only; no random runtime draws |
| `raster.width`, `raster.height` | Integers 64…512 |
| `raster.samples_per_axis` | Integer 1 or 2; E0/E1 evidence uses 2 |
| `raster.invert` | Boolean, never numeric |
| `timeline.sim_hz` | Integer 60 or 120 |
| `timeline.fps_out` | Integer 30 and divisor of sim_hz |
| `timeline.frame_count` | Integer 1…360; E1 180 |
| `field.kind` | Exact string `gaussian-separable-v1` |
| `field.threshold` | Real 0.05…5.0 |
| `elements` | Array length 1…12; delivered scenes use 5…12 |
| element `id`, `group` | Valid ID; unique element IDs |
| `home_xy` | Two finite reals; `abs(x)<=0.8*(W/H)`, `abs(y)<=0.8` |
| `sigma` | Real 0.03…0.60 world units |
| `weight` | Real 0.05…2.0; no zero/negative weights |
| `mass` | Real 0.5…2.0 |
| `spring_k` | Real 5.0…100.0 |
| `damping_c` | Real 1.0…30.0 |
| `cues` | Array length 0…16; unique cue IDs |
| cue `id`, `group` | Valid ID; group targets at least one element |
| cue `start_tick`, `end_tick` | Integers `0<=start<end<=frame_count*(sim_hz/fps_out)` |
| cue `envelope` | Exact string `quartic-pulse-v1` |
| cue `force_xy` | Two finite reals; physical artistic force units |
| `limits.max_displacement` | Real `0 < value <=0.75` |
| `limits.max_speed` | Real `0 < value <=3.0` |
| `limits.max_total_force` | Real `0 < value <=6.0` |

Additional checks for every element are `h*sqrt(k/m)<=0.25`, `h*c/m<=0.25`, `h²*k/m+2*h*c/m<4`. Conservatively sum the Euclidean norms of **all** cues targeting an element, including nonoverlapping cues, and require that sum not exceed `max_total_force`. Do not replace it with vector cancellation or a peak-time optimizer. Check scalar ranges before large products/norms. Use robust `hypot` and reject huge force components before creating arrays. The stability restrictions can reject values individually within the scalar table; that is intentional (§4 P0117).

Integers supplied for real fields are accepted, converted to float64 and canonically represented as JSON floats. Strings, nulls, booleans and nonfinite values are not accepted as real numbers. No YAML, expression evaluation, environment substitution, schema migration or execution of values is supported.

### Proposed, unexecuted strict parsing illustration

```python
import json
import math
import re
from pathlib import Path

class ConfigError(ValueError):
    pass

ID = re.compile(r"[a-z][a-z0-9_]{0,31}\Z", re.ASCII)

def reject_constant(token):
    raise ConfigError(f"$: unsupported JSON constant {token}")

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(f"$: duplicate object key {key!r}")
        result[key] = value
    return result

def exact_keys(value, expected, path):
    if type(value) is not dict:
        raise ConfigError(f"{path}: expected object")
    missing, extra = set(expected) - value.keys(), value.keys() - set(expected)
    if missing or extra:
        raise ConfigError(f"{path}: missing={sorted(missing)}, unknown={sorted(extra)}")

def real_number(value, path, lo, hi, *, open_lo=False):
    if type(value) not in (int, float):  # bool is deliberately excluded
        raise ConfigError(f"{path}: expected a finite real number")
    try:
        value = float(value)
    except (ValueError, OverflowError):
        raise ConfigError(f"{path}: real value outside finite range") from None
    if not math.isfinite(value):
        raise ConfigError(f"{path}: expected finite value")
    if (value <= lo if open_lo else value < lo) or value > hi:
        raise ConfigError(f"{path}: outside accepted range")
    return 0.0 if value == 0.0 else value

def integer(value, path, lo, hi):
    if type(value) is not int or not lo <= value <= hi:
        raise ConfigError(f"{path}: expected integer in [{lo}, {hi}]")
    return value

def identifier(value, path):
    if type(value) is not str or ID.fullmatch(value) is None:
        raise ConfigError(f"{path}: malformed ASCII ID")
    return value

def read_document(path: Path):
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
        doc = json.loads(text, object_pairs_hook=unique_object,
                         parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ConfigError(f"$: invalid JSON ({type(exc).__name__})") from None
    exact_keys(doc, {"schema_version", "scene_id", "seed", "raster",
                     "timeline", "field", "elements", "cues", "limits"}, "$")
    return raw, doc  # next: validate EVERY nested object/range/target before output

def validate_solver(mass, stiffness, damping, sim_hz, path):
    h = 1.0 / sim_hz
    A, D = h*h*stiffness/mass, h*damping/mass
    if not (A > 0.0 and D > 0.0 and A + 2.0*D < 4.0):
        raise ConfigError(f"{path}: unstable numerical parameters")
    if h*math.sqrt(stiffness/mass) > 0.25 or D > 0.25:
        raise ConfigError(f"{path}: outside accuracy envelope")
```

This block illustrates essential checks; it is **not a complete loader**. The full implementation must call exact-key/range/vector/type checks for every nested object, enforce allowed enumerations, uniqueness, physical home extents, cue targets/support, force sums and resource bounds, then produce sorted immutable resolved objects. Duplicate-key detection above identifies the duplicate key but not its full nested path; a complete loader should improve that diagnostic without weakening rejection. Do not claim this fragment passes V01.

## 6. State, clock and ownership

Source interfaces are retained (§5 P0211–P0223):

```text
# Proposed interface pseudocode
load_scene(path: Path) -> ValidatedScene
initial_state(scene: ValidatedScene) -> SceneState
cue_forces(tick: int, scene: ValidatedScene) -> Float64Array
propose_step(previous: SceneState, scene: ValidatedScene) -> CandidateState
check_transition(previous, candidate, scene) -> Decision
evaluate_samples(state, scene) -> Float64Array
rasterize(samples, scene) -> Gray8Array
measure_mask(pixels, scene) -> FrameMetrics
render_run(scene, new_output_directory: Path) -> RunReport
verify_integrity(manifest_path: Path) -> VerificationReport
verify_replay(manifest_path: Path, new_output_directory: Path) -> ReplayReport
```

Use integer `R=sim_hz//fps_out` after divisibility validation. `frame_ticks=tuple(j*R for j in range(frame_count))`; terminal tick is `frame_count*R`. Render tick 0 before any update. Integrate through terminal tick but do not output an extra frame. Record every committed state including zero, and one decision per attempted transition. For nominal E1: 180 frames, 360 ACCEPT decisions and 361 states; ticks 0,2,…,358 label images, tick 360 is the terminal audit state. A 120 Hz cadence take has terminal tick 720 and output ticks 0,4,…,716; double all cue/recovery boundaries, preserve 180 frames. Never accumulate floating seconds or let export speed set simulation time (§9 P0251–P0253).

### Proposed, unexecuted ownership illustration

```python
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class SceneState:
    tick: int
    positions: np.ndarray
    velocities: np.ndarray

def owned_state(tick, positions, velocities):
    # Pure ownership helper; runtime structural/finite checks remain explicit.
    p = np.array(positions, dtype=np.float64, order="C", copy=True)
    v = np.array(velocities, dtype=np.float64, order="C", copy=True)
    p.flags.writeable = False
    v.flags.writeable = False
    return SceneState(tick, p, v)

def initial_state(scene):
    return owned_state(0, scene.home_xy,
                       np.zeros((len(scene.elements), 2), dtype=np.float64))
```

The constructor is illustrative, not a universal validator. Test dtype, shapes, integer tick, finite values, C-contiguity, input immutability, no sharing with scene/caller arrays and no position/velocity sharing. Read-only flags alone do not establish deep immutability against deliberate low-level tampering. The architecture assumes ordinary engine code obeys ownership; tests detect accidental mutation/aliasing.

## 7. Cues, motion and numeric guard

For transition n→n+1, evaluate at n+1/2. For a cue on `[start,end]`, `u=(n+0.5-start)/(end-start)` and `e(u)=16u²(1-u)²` for `0<u<1`, zero otherwise. This has peak 1 at 1/2, zero endpoint values and first derivatives, and no plateau. It is C1 at support boundaries; do not claim arbitrary-order smoothness. Sum cues in ID order, applying the complete force to each group member (§9 P0248–P0250).

### Proposed, unexecuted cue and motion illustration

```python
def quartic_pulse(u):
    return 16.0*u*u*(1.0-u)*(1.0-u) if 0.0 < u < 1.0 else 0.0

def cue_forces(tick, scene):
    if type(tick) is not int or not 0 <= tick < scene.terminal_tick:
        raise ValueError("tick: not a valid transition-start tick")
    out = np.zeros((len(scene.elements), 2), dtype=np.float64)
    for cue in scene.cues:  # validated ascending ASCII cue ID order
        u = (tick + 0.5 - cue.start_tick) / (cue.end_tick - cue.start_tick)
        e = quartic_pulse(u)
        fx, fy = cue.force_xy
        for i in scene.group_indices[cue.group]:  # ascending element-ID order
            out[i, 0] += e * fx
            out[i, 1] += e * fy
    return out

def propose_step(previous, scene):
    # Orchestrator must validate previous BEFORE entering this function.
    h = 1.0 / scene.sim_hz
    z = previous.positions - scene.home_xy
    force = cue_forces(previous.tick, scene)
    acceleration = (-scene.spring_k[:, None]*z
                    -scene.damping_c[:, None]*previous.velocities
                    +force) / scene.mass[:, None]
    velocity_next = previous.velocities + h*acceleration
    position_next = previous.positions + h*velocity_next
    return owned_state(previous.tick + 1, position_next, velocity_next)
```

The order is normative: previous velocity in damping, updated velocity in position (§8 P0240–P0241). No implicit damping denominator, alternative integrator or explicit-position Euler substitution. Candidate allocation does not imply acceptance. A robust implementation classifies nonfinite arithmetic as numerical failure and does not let an exception produce false completion.

For an unforced coordinate, `A=h²k/m`, `D=hc/m`,

```text
[z_next]   [1-A,   h(1-D)] [z]
[v_next] = [-A/h,  1-D  ] [v]
```

Trace is `2-A-D`, determinant `1-D`. The unit-disk conditions reduce to `A>0`, `D>0`, `A+2D<4`, exactly the source (§8 P0242–P0244). Defaults `m=1,k=14,c=5` have damping ratio about 0.668 and expected overshoot. More damping can destabilize this explicit-damping discretization. Stability does not prove field visibility, forced bounds, physical realism or artistic quality.

For the default underdamped analytic oracle define `beta=c/(2m)`, `omega=sqrt(k/m-beta²)`:

\[
z(t)=e^{-\beta t}\left[z_0\cos(\omega t)+\frac{v_0+\beta z_0}{\omega}\sin(\omega t)\right].
\]

Generate oracle values independently from this expression and its derivative. Do not call `propose_step` to manufacture expected states. The required 60 Hz two-second case uses `z0=0.2,v0=0` and max position error `<=0.01`; 120 Hz error must be smaller. Forced common-time E1 comparison also requires max Euclidean position discrepancy `<=0.01`; report velocity discrepancy separately (§8 P0246).

**Guard decision contract:** previous and candidate must have valid dtype/shape/finite values, candidate tick exactly previous+1, consistent immutable index plan, displacement from each immutable home `<=max_displacement`, speed `<=max_speed`. The previous state must be valid before proposal. ACCEPT does not edit anything. REJECT preserves previous state and aborts; it records attempted tick, source-state hash and stable reason codes with component paths. Nonfinite details use `"nan"`, `"+inf"`, `"-inf"`, never JSON nonfinite literals. No hash of invalid numeric candidate values is mandatory (§10 P0255–P0258).

**Proposed reason codes:** `BAD_TICK`, `BAD_SHAPE`, `BAD_DTYPE`, `NONFINITE_POSITION`, `NONFINITE_VELOCITY`, `DISPLACEMENT_LIMIT`, `SPEED_LIMIT`, `INVALID_PREVIOUS`, `FIELD_NONFINITE`, `EXPORT_FAILURE`. Keep numerical REJECT codes distinct from render/export failures. A decision record must be successfully closed before committing candidate in memory. If any later log/export write fails, mark the run failed where possible; no complete manifest. Interrupted traces may end between writes and remain incomplete rather than being repaired retroactively.

## 8. Gaussian field, sampling and grayscale raster

Use positive inside:

\[
F(x,y)=\sum_i q_i\exp[-((x-p_{i,x})^2+(y-p_{i,y})^2)/(2\sigma_i^2)]-\tau.
\]

One Gaussian with `q>tau` has zero-contour radius `sigma*sqrt(2*ln(q/tau))`; center field is `q-tau`. A field amplitude is not distance. No field normalization, density-derived sphere tracing, adaptive samples, Gaussian-tail truncation, endpoint-inclusive grid or camera transform belongs in Build 0 (§6–§7 P0225–P0237).

### Proposed, unexecuted coordinate and field illustration

```python
def sample_axes(scene):
    W, H, s = scene.width, scene.height, scene.samples_per_axis
    aspect = W / H
    x = -aspect + (2.0 / H) * ((np.arange(W*s, dtype=np.float64) + 0.5) / s)
    y = 1.0 - (2.0 / H) * ((np.arange(H*s, dtype=np.float64) + 0.5) / s)
    return x, y

def evaluate_samples(state, scene):
    x, y = sample_axes(scene)
    values = np.zeros((len(y), len(x)), dtype=np.float64, order="C")
    scratch = np.empty_like(values)
    for i, element in enumerate(scene.elements):  # ascending ID order
        px, py = state.positions[i]
        gx = np.exp(-0.5 * ((x - px) / element.sigma)**2)
        gy = np.exp(-0.5 * ((y - py) / element.sigma)**2)
        np.multiply.outer(gy, gx, out=scratch)
        scratch *= element.weight
        values += scratch
    values -= scene.threshold  # subtract once, after fixed-order sum
    if not np.isfinite(values).all():
        raise FloatingPointError("FIELD_NONFINITE")
    return values
```

This path has one accumulation plane and one scratch plane. Its direct reference must be independently written in tests from the full 2D expression and agree within absolute `1e-12` at selected samples. Algebraic equivalence does not require bitwise equality between direct and separable operation orders. The code above chooses where the weight multiplication occurs; freeze this operation order as part of the numerical policy and use it consistently during replay.

### Proposed, unexecuted raster illustration

```python
def rasterize(samples, scene):
    H, W, s = scene.height, scene.width, scene.samples_per_axis
    if samples.shape != (H*s, W*s) or samples.dtype != np.float64:
        raise ValueError("field: invalid shape/dtype")
    if not np.isfinite(samples).all():
        raise FloatingPointError("FIELD_NONFINITE")
    inside = samples >= 0.0
    counts = inside.reshape(H, s, W, s).sum(axis=(1, 3), dtype=np.int64)
    pixels = np.floor(255.0 * counts / (s*s) + 0.5).astype(np.uint8)
    return 255 - pixels if scene.invert else pixels

def geometry_mask(pixels, scene):
    un_inverted = 255 - pixels if scene.invert else pixels
    return un_inverted >= 128
```

At s=2, permitted coverage values are 0,64,128,191,255 before display inversion. Metrics use non-inverted threshold `>=128`. Clipping instead checks **any value >0** in the outer two rows/columns; do not discard 64-valued edge coverage. Export grayscale mode `L`, fixed PNG compression 6, optimization false and no timestamps/text/color profile (§7 P0236–P0237).

**Metric contracts:** area fraction is count/(H*W); world centroid uses base-pixel centers `x=-a+2(j+0.5)/H`, `y=1-2(r+0.5)/H`; inclusive bbox is `[xmin,ymin,xmax,ymax]` in integer raster coordinates. Empty masks have null centroid/bbox and an explicit diagnostic. IoU is intersection/union; zero union returns null and fails the relevant gate (§11 P0261).

For morphology, calculate centroid in raster row/column coordinates, derive baseline minus candidate shift, round each component with `floor(value+0.5)`, translate with zero-fill and no wrap, then calculate aligned IoU. This allows half-pixel residual alignment error per axis and is an inexpensive translation rejection diagnostic, not recognition. A translated-only asymmetric fixture must fail the morphology gate even if raw frame differences are large. Added component/critical-gradient diagnostics remain descriptive and do not veto intended topology changes (§11 P0263–P0264).

## 9. Deterministic artifacts, canonicalization and publication

Baseline required successful-run artifacts (§14 P0277–P0284):

```text
NEW_RUN/
  scene.input.json
  scene.resolved.json
  frames/frame_000000.png ... frame_000179.png   # nominal E1
  contact_sheet.png
  states.jsonl
  decisions.jsonl
  frames.jsonl
  run_status.json
  manifest.json                                # publish LAST
```

A gallery has its own static manifest and all six resolved preset scenes/images. The separate experiment manifest links E0, nominal E1, the complete cue-off control, replay, profile results, test records and implementation report. An incomplete gallery or compact unit-test control cannot substitute for release evidence (§14 P0278).

Refuse an already existing destination, even an empty directory. Validate configuration and resources first, then create the new destination and `running` status. Atomic writes use temporary files and same-filesystem rename. No overwrite/resume mode is supported. On a handled failure, record `failed`, an error code and last committed tick where possible; killed/interrupted `running` runs remain incomplete. Files already exported are useful diagnostics, not completed evidence.

Canonical JSON uses UTF-8, sorted object keys, separators `,` and `:`, no nonfinite numbers and exactly one trailing newline. Normalized real fields serialize as JSON floats, element/cue arrays in resolved ID order, negative floating zero as positive zero. Raw hash is over original input bytes, not reserialized input. Cross-language canonicalization is not promised; record the actual Python environment (§14 P0280).

### Proposed, unexecuted canonical and PNG illustration

```python
import hashlib
import io
import json
import math
import os
from PIL import Image

def normalize_json(value):
    # This illustration accepts only deliberate evidence values.
    if isinstance(value, np.ndarray):
        return normalize_json(value.tolist())
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("nonfinite JSON number")
        return 0.0 if number == 0.0 else number
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (tuple, list)):
        return [normalize_json(item) for item in value]
    if type(value) is dict and all(type(k) is str for k in value):
        return {key: normalize_json(item) for key, item in value.items()}
    raise TypeError("unsupported evidence value")

def canonical_bytes(value):
    text = json.dumps(normalize_json(value), sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return (text + "\n").encode("utf-8")

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def state_mapping(state):
    return {"tick": state.tick,
            "positions": state.positions.tolist(),
            "velocities": state.velocities.tolist()}

def pixel_hash(gray):
    if gray.dtype != np.uint8 or gray.ndim != 2:
        raise ValueError("gray8 image required")
    H, W = gray.shape
    prefix = b"cz-gray8-v1\n" + f"{W},{H}\n".encode("ascii")
    return sha256(prefix + np.ascontiguousarray(gray).tobytes(order="C"))

def encode_gray_png(gray):
    image = Image.fromarray(gray)
    if image.mode != "L":
        raise ValueError("PNG must be grayscale L")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=6, optimize=False)
    return buffer.getvalue()

def write_new_file_atomically(destination, data):
    # Caller owns a fresh run directory; no competing writer is supported.
    temporary = destination.with_name(destination.name + ".tmp")
    if destination.exists():
        raise FileExistsError(destination)
    with temporary.open("xb") as stream:
        stream.write(data)
    os.replace(temporary, destination)
```

The block is an illustration of canonical content and same-directory publication. It is not a completed concurrency-resistant file service or crash-proof storage system. The accepted baseline claims atomic rename and ordinary successful close, not power-loss durability (§10 P0256). The resolved mapping must already have normalized semantic integer/real fields correctly; canonicalization does not infer a schema from arbitrary dictionaries. PNG bytes and decoded-pixel bytes have distinct hashes. No engine metadata chunks are supplied.

### Proposed artifact/trace schema clarifications

Freeze exact documentary JSON schemas before implementation of the verifier. Suggested schemas below supplement the baseline's listed contents; they are **v0.4 proposals**.

- `cz-state-row-0.3`: `{tick, positions, velocities}` with positions/velocities N by 2 real arrays in manifest element order. Tick zero exists once; complete nominal E1 rows are 0…360. Each line is one canonical JSON object, no recursive history.
- `cz-decision-row-0.3`: `{attempted_tick, status, source_state_hash, committed_state_hash, reasons}`. For ACCEPT, reasons is empty and committed hash matches state at attempted tick. For REJECT, omit committed hash and include reason objects with code/path/element ID/safe scalar details. No wall-clock timing or path belongs in replay-invariant rows.
- `cz-frame-row-0.3`: `{index,tick,path,mode,width,height,file_sha256,pixel_sha256,metrics}`. Relative canonical frame paths are unique; index/tick correspondence must match the rational timeline. Metrics include occupancy, null-or-world centroid, null-or-inclusive bbox, clipping, baseline and aligned IoU, centroid distance, field extrema and empty diagnostics. Keep raw numeric field planes out of evidence.
- `cz-run-status-0.3`: state `running|failed|complete`; run/schema identifiers; error code and last committed tick where relevant. Complete status is finalized once before manifest hashing and never mutated afterward.
- `cz-run-manifest-0.3`: baseline schema/engine versions; raw/resolved hashes; element order; policy IDs; artifact path/hash list; expected frames/transitions/states and timeline; accepted/rejected totals; exact environment/source digest; integrity outcomes; timings/warnings; creator review `pending|accepted|rejected` with explicit source if provided. It does not hash itself, and hashes are not a signature.
- `cz-experiment-0.3`: exact E0/E1/control/replay/test/report paths and hashes; 60/120 Hz study references; automated gate outcomes; evidence sufficiency; creator review; tuning/change record. Distinguish “render/export succeeded,” “integrity passed,” “profile passed,” “exact replay demonstrated” and “creator accepted.”

Adopt strict path rules: run-relative normalized paths, no absolute paths, no `..`, no duplicate references or symlinks escaping the run root. A verifier follows a known schema rather than executing or importing arbitrary evidence content. Reject unexpected numbered frames as well as missing ones. The output directory itself and operational metadata are excluded from deterministic comparisons.

### Proposed, unexecuted run orchestration pseudocode

```text
load and validate scene entirely; derive nominal profile and resource bounds
refuse existing destination; create new run directory; write running status
save exact raw input and canonical resolved scene; snapshot actual source
construct state 0; validate it; write state 0
render frame 0 and its record
for n in 0 .. terminal_tick-1:
    validate previous committed state
    candidate = propose_step(previous, scene)
    decision = check_transition(previous, candidate, scene)
    write and successfully close decision row
    if REJECT:
        write failed status where possible; abort with exit 3; NO manifest
    commit candidate in memory; write corresponding state row
    if committed tick is an output tick:
        evaluate finite field; rasterize; atomically write PNG
        decode/verify required properties; record hashes and metrics
close all logs; build required contact sheet; collect source/env/timing evidence
construct prospective manifest and validate all closed artifacts and trace links
finalize complete run_status once; hash it; finish prospective artifact list
atomically publish manifest LAST
run public integrity verification; report genuine outcome and separate profile
```

The public verifier can take an in-memory prospective manifest during prepublication checking; its external command takes the published path. This removes circular dependence on a manifest that has not yet been written. If final verification detects corruption, the run is invalid regardless of a `complete` string. Retain the diagnostics and report failure; do not quietly rewrite hashed status/manifest to manufacture success.

## 10. Integrity verification, replay and truthful claims

Integrity checks recompute rather than merely read stored “passed” flags. They verify:

1. Strict manifest/trace schemas and exact required artifacts; finalized status and a valid final manifest are both present.
2. Every artifact file hash and raw/resolved configuration hash; source content index and dependency record are available.
3. Unique complete frame indices, expected filenames, no extra numbered files, decoded mode L and dimensions, file hash and domain-separated decoded-pixel hash.
4. Record counts, exact integer timeline, state ticks and decision relationships: source hash refers to n, ACCEPT committed hash refers to n+1; correct counts and no rejected transition in a complete nominal E1.
5. Finite values and bounds in states; no array shape/order mismatch; recomputed masks, occupancy, bbox, centroid, clipping, baseline IoU and aligned IoU agree with records under the documented comparison policy.
6. Contact-sheet required source indices, labels and measured minimum-aligned-IoU selection. **Proposed clarification:** save `contact_sheet.index.json` as an additional hashed artifact listing index→cell/label references, because a contact-sheet PNG alone cannot reliably prove which source frames were assembled. It supplements, rather than replaces, the required PNG.
7. Expected experiment-level E0/E1/control/replay/test links and profile results. Creator-review text is never inferred from image hashes or a model score.

A hostile or accidentally corrupt manifest can consistently lie about its own metrics, so recomputation and independent fixtures matter. An internally consistent manifest still cannot prove an artistic claim, establish author's identity or guarantee complete host process history.

### Proposed, unexecuted frame-verification fragment

```python
def verify_frame(frame_row, run_root, scene):
    # resolve_checked_relative_path enforces the adopted artifact path rules.
    path = resolve_checked_relative_path(run_root, frame_row["path"])
    payload = path.read_bytes()
    if sha256(payload) != frame_row["file_sha256"]:
        raise IntegrityError("PNG_FILE_HASH")
    with Image.open(io.BytesIO(payload)) as image:
        image.load()  # detect truncation/decoder failure
        if image.format != "PNG" or image.mode != "L":
            raise IntegrityError("PNG_MODE_OR_FORMAT")
        if image.size != (scene.width, scene.height):
            raise IntegrityError("PNG_DIMENSIONS")
        pixels = np.array(image, dtype=np.uint8, copy=True)
    if pixel_hash(pixels) != frame_row["pixel_sha256"]:
        raise IntegrityError("PIXEL_HASH")
    measured = measure_mask(pixels, scene)
    compare_metric_record(measured, frame_row["metrics"])
    return pixels, measured
```

The fragment is deliberately incomplete: `IntegrityError`, path policy, strict schema checks, timeline/trace/source verification, baseline/alignment calculations and record comparison remain required. It illustrates independent decode/hash/metric checks, not a tested verifier. A complete verifier must not compare only byte hashes or trust Pillow's open-without-load as evidence that the whole image is decodable.

**Fresh-process replay:** start a separate engine process with the recorded resolved scene and exact approved source/environment into a new destination, from tick zero. Compare ordered state rows, decision rows, decoded pixel hashes and PNG file hashes. Compare canonical semantic trace objects or exact canonical trace bytes; exclude timing, path and OS scheduling metadata. Record both commands, exit statuses and compared digests. A same-environment claim is earned only by this completed replay. Cross-environment/backend comparisons use a separately labeled tolerance study and cannot pass the exact-replay claim (§14 P0283–P0284).

A seed-only change must change the resolved configuration hash but not trajectories/pixels because Build 0 uses no random draws. A perturbation to an active cue must change the configuration hash and relevant motion/output. Run both metamorphic checks. No committed Git revision is required: snapshot exactly executed engine files, dependency lock and fixtures with a sorted path/hash index, including uncommitted content where present; do not initialize Git merely to acquire a revision (§14 P0282).

## 11. E0 and E1 acceptance profiles — retained in full

**E0 (§12 P0266):** six explicit static presets, five–twelve elements each, the same threshold and documented weight policy, with home/sigma changes recorded. Save every resolved scene and one image per preset; export a labeled sheet. At least four decoded outputs differ. Every preset selected as usable has finite field, occupancy in `[0.03,0.65]` and no nonzero coverage in the outer two-pixel band. Exploratory failures remain labeled. Creator selection stays pending unless supplied. **Proposed clarification:** freeze the preset list and fixed weight/threshold comparison policy before generation; do not retrospectively omit failures.

**E1 (§12 P0267; Table 7):** baseline or provisional E0 selection, 384×384, s=2, 180 frames, 30 fps, 60 Hz. Cue-off control has exactly the same resolved scene except empty cues and distinct scene ID, and produces its own complete 180-frame evidence package. Compact test controls do not replace it.

| Gate | Exact nominal requirement | Implementation caution |
|---|---|---|
| Schedule | 180 frames at ticks 0,2,…,358; 360 accepted transitions through terminal tick 360 | Render initial state first; terminal audit is not frame 180 |
| Validity | No rejected step, nonfinite sample, hidden state edit or export failure | Do not call a frozen/retimed run successful |
| Visibility | Every output occupancy 0.03…0.65; no foreground in outer two pixels | Clipping uses any coverage `>0`, not only binary mask |
| Excitation | At least one targeted element reaches displacement `>=0.05` world units | Check disturbance before allowing recovery claims |
| Morphology | At least one disturbed output frame has aligned IoU `<=0.90` against baseline | Translation alone cannot pass |
| Temporal variation | At least ten distinct decoded E1 frame hashes | Hash decoded pixels as specified; container metadata cannot supply variation |
| Cue-off invariance | Every cue-off position/velocity array bit-identical to its initial array while ticks advance; every decoded control frame equals initial frame | State-row hashes differ because tick changes; compare arrays themselves |
| Numeric recovery | At EVERY tick 330…360 inclusive: max per-element position error `<=0.01` AND max speed `<=0.02` | No endpoint-only or monotonic-error shortcut |
| Image recovery | EVERY rendered recovery-window frame has baseline IoU `>=0.98` AND world centroid displacement `<=0.01` | Frames 165…179 are in the output tail; terminal tick 360 is numeric-only |
| Replay | Fresh-process states, decisions, decoded pixel hashes AND PNG file hashes identical in recorded environment | Operational metadata excluded; different environment is a distinct comparison |
| Creator judgment | Explicitly report pending, accepted or rejected | Pending is not an automated profile failure; automation cannot substitute for human judgment |

**Proposed clarification:** define “disturbed output frame” for morphology before measurement as an output after first cue activation and before the start of the nominal recovery window; save the full aligned-IoU series. Source P0269 does not define a special narrower window. Do not select a window after seeing results. A conservative alternative is report both all-post-activation and cue-support minima and let the creator inspect them; changing the contractual gate requires a documented decision.

The contact sheet contains frames **0,23,38,50,60,90,120,165,179**, plus the measured minimum-aligned-IoU frame if different. Labels show index and derived time. Preserve the full sequence; sparse stills cannot reveal every flicker. Provide exact local playback instructions or a self-contained local HTML player using exported frames, without creating a new engine GUI or requiring an encoder. Playback timing is a viewer convenience, not the authoritative schedule (§12 P0270).

Thresholds are prototype acceptance choices, not proofs of fluidity, humor or recognized identity. If a take misses a gate, retain/report it, tune with recorded reasons or record a versioned design change and fresh evidence. Do not lower tolerances after inspecting outcomes while claiming the same profile. After the small gallery and two documented tuning passes, if no form is promising, compare circles/capsules or a constrained warp before adding research layers (§12 P0269–P0271).

## 12. Independent test architecture — V01 through V12

These tests are mandatory v0.3 requirements, not optional smoke checks (Table 8; §13 P0273–P0275). Keep unit fixtures small, but run the complete release E1/control/replay. Record command, exact environment, exit code, pass/fail summary and retained artifacts. A unit test cannot universally prove no external process mutated a repository; scope/nonmutation is process evidence.

| Test | Suggested files and independent oracle | Must detect |
|---|---|---|
| **V01 Strict configuration** | `test_config.py`: malformed literal JSON fixtures, nested duplicate keys, exact boundary values, calculated unstable/accuracy cases; execute CLI in temporary directory | Duplicate keys/IDs; unknown keys/schema; bool numerics; NaN/Infinity; vector shapes; unsupported values/groups/ticks/ranges/resources; unstable parameters; output creation before load success |
| **V02 Scheduler** | `test_clock.py`: independently enumerated short schedule plus nominal vectors, exact first-render callback assertion | Step-before-frame-zero, accumulated time, missing terminal audit, wrong record counts, nondividing cadence, cue sampled at endpoint rather than midpoint |
| **V03 Field** | `test_field.py`: analytic single Gaussian center/off-center/radius; independent direct exponential expression on selected points | Wrong sign/sigma factor; transposed axes; broken symmetry/translation; nonfinite values; direct/separable difference above absolute `1e-12`; reordered accumulation policy |
| **V04 Raster** | `test_raster.py`: hand-built asymmetric supersample Boolean pattern converted to signed field values independent of Gaussian path | Row direction; quarter/three-quarter coordinates; threshold equality; quantization values; L/dimensions; inversion relation; off-by-one shapes |
| **V05 Motion** | `test_motion.py`, `test_state.py`: hand-calculated nonzero asymmetric one-step; analytic underdamped default solution; separate 60/120 Hz study | Wrong integrator/damping velocity, per-element mass mix-up, rest drift, aliasing/input mutation, analytic/cadence errors above gate, copied previous state |
| **V06 Cue** | `test_cues.py`: exact zero/end/midpoint values and independent overlapping cue sums with at least two group members of different mass | Wrong support/sample, wrong pulse scale, total-group force division, unsorted addition, invalid group targeting |
| **V07 Rejection** | `test_guard.py`, `test_evidence.py`: injected candidate NaN, bad tick, over-speed, over-displacement, decision-write failure | Mutation/commit after REJECT, rejected run marked complete, unsafe JSON nonfinites, false next-state output, hidden clamp/retry |
| **V08 E1 recovery** | `test_profiles.py`: full excited/morphing take, deliberately static solver and copied-final-pose fake | A recovered-but-never-disturbed take, endpoint-only checks, velocity ignored, copied baseline masquerading as recovery |
| **V09 Bad renders** | `test_profiles.py`, fixtures: empty/full, translated-only, static, vertically flipped, missing-frame cases with specific expected failures | Empty IoU treated as 1; static hashes passing variation; translated shape passing morph; flipped coordinate fixture; gaps/count mismatch |
| **V10 Artifact failure** | `test_evidence.py`, `test_cli.py`: existing dirs; deterministic write failures; interrupted status; missing/truncated/wrong-mode PNG; wrong contact-sheet source refs | Overwrite, incomplete success, hashes without decoding, stale artifact substitution, bad contact sheet |
| **V11 Replay** | `test_replay.py`: two fresh engine processes; separate active-cue perturbation and provenance-only seed perturbation | Hidden state/RNG/order; scene hash omission; outputs unaffected by active cue; seed changing pixels; false cross-environment equality claim |
| **V12 Evidence claims** | `test_evidence.py`, `test_profiles.py`: mutate files/metrics/status/trace links, recalculate only some hashes, unset creator review | Verifier trusting stored pass flags; missing expected records; failure accepted as complete; automated artistic acceptance |

Specific arithmetic fixture proposal for V05: use two elements with distinct masses/k/c and nonzero p-home/v and cue vectors, calculate one step by hand with the required operation order, and verify every coordinate. The analytic default fixture is a different proof: it measures accumulated discretization error rather than only agreement with a copied update equation.

For V04, preserve the specified `floor(255*coverage+0.5)` recipe. With only s=1 or s=2, round-to-even happens to produce the same permitted coverage values; a test must not pretend these cases distinguish the two recipes. Likewise a synthetic threshold example must use an actually available gray level or explicitly identify itself as a general metric-unit fixture, because 127 is not emitted by the nominal raster. Test exact specified comparisons, but do not invent a visible defect where permitted inputs produce identical output.

For strict-stability test claims, note that the accepted accuracy envelope already implies `A+2D<=0.5625<4`; the narrower scene ranges cannot produce an otherwise valid unstable scene. An invalid `c=130` fixture proves rejection of invalid input, but may hit the scalar range check first. Test the pure mathematical stability helper independently if proving that specific inequality branch matters; do not widen accepted scene ranges for test reachability.

For V09 the flipped fixture must be asymmetric and checked against an independent expected orientation; occupancy alone is invariant under a vertical flip. Each deliberately wrong fixture has a named expected failed gate, rather than expecting every metric to reject every possible bad image. Derive shifted shapes with zero-fill and enough margin that cropping cannot create an unrelated apparent morph.

## 13. Performance contracts and controlled development sequence

Preflight dimensions, samples, frame count and influence count before allocating arrays. At the nominal eight-influence workload, one sampled plane is 768×768 float64 = 4,718,592 bytes; one field plus one scratch plane = 9,437,184 bytes before masks, encoders and interpreter overhead. There are 849,346,560 influence-sample contributions and 2,211,840 separable exponentials over 180 frames. These are derived counts, not measured resident memory or run time. Never materialize an N×H×W component tensor, cache all fields or retain every full frame to create a sheet (§15 P0287).

Each state is only `4N` float64 values plus tick; NumPy raw array payload is `32N` bytes, excluding object/log overhead. Stream state/decision/frame records as the run proceeds. Storing every state in the required audit trace is different from adding a historical-memory controller. Use thumbnail selection or reopen exported PNGs for the contact sheet.

Measure actual field evaluation, raster reduction, PNG encoding/writing, log writing, end-to-end wall time and peak resident memory where obtainable; document measurement method/hardware and overhead. The source's 30-second nominal E1 iteration target is a usability aspiration. Report it as met/missed from measurement; correctness does not fail because the target is missed (§15 P0288). Profile before vectorized rewrites, compiled kernels or GPU work; changing reduction/operation order can change replay policy.

| Stage | Smallest deliverable | Exit condition before proceeding |
|---|---|---|
| 0 — freeze handoff | New local project, short plan; ADRs for positive-inside, integer ticks, explicit-damping integrator, reject/abort, supersampling, separability, canonicalization and artifact schemas | Scope/private/nonmutation constraints recorded; exact documentary choices agreed by the later authorized implementer |
| 1 — data and clock | Strict scene loader, immutable compiled definitions/state, sample axes and tick vectors | V01 plus ownership/clock portions of V02/V05 pass; load errors create no output |
| 2 — static field | Analytic field oracle, separable path, raster/metrics | V03/V04 and relevant V09 pass; six-preset E0 gallery produced before motion |
| 3 — dynamics | Pure pulse/force, candidate integrator, numeric guard and transition log | V05/V06/V07 pass; default analytic error and forced 60/120 Hz convergence gate recorded |
| 4 — first takes | E1 nominal and complete cue-off control, all metrics and contact sheet/playback | E1 gates reported independently of export completion; V08/V09 pass; failed takes retained |
| 5 — integrity | Complete file lifecycle, schema/trace/hash/source verification, failure injection | V10/V12 pass; real source snapshot/dependency/environment evidence present |
| 6 — replay and close | Fresh-process exact replay, V11 metamorphic checks, experiment manifest/report | Required tests and profile/replay gates passed or honestly incomplete; creator review explicit; stop after E0/E1 |

This order refines v0.3 P0290–P0296 without importing upstream systems. Artifact logging must be added as the corresponding runtime stages appear; “integrity stage” does not mean generate an unaudited take and reconstruct a fictitious trace later. Implement source snapshots and raw/resolved saving early enough that each recorded take is genuinely reproducible.

Suggested CLI contracts (§15 P0297):

```text
commander-zorg validate scene.json
commander-zorg gallery preset_directory --out NEW_GALLERY
commander-zorg render scene.json --out NEW_RUN
commander-zorg verify NEW_RUN/manifest.json --integrity
commander-zorg verify NEW_RUN/manifest.json --replay --out NEW_REPLAY
commander-zorg check-profile experiment_manifest.json
```

Executable naming may differ if exact commands are documented. Exit code 0 on `render` means artifact generation and integrity passed, **not** an automatic E1 artistic or profile pass. Dedicated profile failure is 6; pending creator review is not an automated failure. Report profile failures clearly even if the render command exited 0. General exit codes are 2 config/usage, 3 numerical rejection, 4 export/integrity, 5 replay mismatch. Do not print “Build 0 complete” merely because one render command succeeded.

## 14. Deferred post-v0.3 architecture — research interfaces only

All components below are **future proposals**, unimplemented and outside the accepted Build 0 runtime. Their role here is to prevent later coupling, not to justify placeholder files/classes now. Separate authorization, versioned state/schema additions and ablation evidence precede construction.

| Future concern | Simplest proposed ownership/interface | Validation boundary |
|---|---|---|
| Shared expression plan | `expression_plan.py`: immutable, tick-addressed scripted cues with independent geometry/motion/color channels and explicit precedence | No renderer needs to know the semantic meaning of “suspicion”; scripted artistic intent overrides keyword proposals; known script look-ahead is anticipation, not inferred prediction |
| Temporal Memory Observer | `observe(previous_memory, compact_observation, delta_t)->new_memory`; EMA/finite buffer outside `SceneState` until a versioned extension | Bounded dimension/units, sample schedule, startup/reset/termination, no full-frame history; observation-only B must leave A trajectories unchanged unless a separately named history-conditioned control is enabled |
| Predictive Motion Conditioner | `condition_target(base_control, state, memory, known_cues, horizon)->bounded_delta`; initially prefer small target/force adjustment over direct vertex/state mutation | Smooth bounded correction, rollback/reset rules, feedback stability, deterministic replay, matched A/B/C trials and measured benefit versus a simple cue envelope |
| Phase diagnostics adapter | `qualify(signal_window, reference)->quality`; `diagnose(...)->normalized_features\|unavailable`; observer first, optional controller later | Exact original definition and attribution retained; causal phase, sufficient amplitude, sampling/latency/window/reset/wrap specified; no unbounded injection; evidence against EMA/delay/known phase |
| Indexed palette | `palette.py` loads a versioned JSON registry and resolves persistent color IDs; a small `expression_color.py` builds region/intensity targets | Explicit scripted ID/override wins; palette associations are authored fiction, not universal emotion facts; RGB/color space/intensity limits and applicability validated |
| Temporal and spatial color | `color_control.py` computes scalar envelopes/history persistence; `color_render.py` applies linear-light/perceptual interpolation, alpha and independent region masks | Color does not alter physical geometry; zero intensity returns exact monochrome baseline; retained faint color can outlast motion; independent tests for gamut/alpha/mask/temporal limits |
| Visual safety | Offline `visual_safety.py`: analyze final decoded frame sequences plus reduced-effects policy; report intervals/metrics/review needs | Screen-area/time/luminance/red/pattern assumptions and standard revisions explicit; warnings supplement engineering; pass never guarantees universal seizure prevention |
| Character features | Persistent `FeatureId`, entity ownership, local attachment frames and optional dedicated feature/cutout render channels | Mustache remains attached, recognizable and ordered under deformation; explicit scene directive is required for intended identity change; structural IDs alone are insufficient |
| Feature-focused camera | `camera_plan.py` accepts time-stamped feature snapshots, authored weights and composition constraints; output 2D frame transform, bounded zoom and validity state | Distinguish world/local/screen coordinates; stable IDs/visibility, scale limits, smooth target changes, no clipped identity feature, no feedback from camera into shape; genuine 3D needs depth representation and remains deferred |
| Governance | Future AILEE adapter consumes compact candidate decisions and produces explicit whole-state proposal plus provenance | Pinned exact API/license, same prerecorded candidate-stream ablation, full revalidation of every mediated state; hard numeric validity remains mandatory |

An illustrative **proposed interface sketch, not runtime code**, for later camera work is:

```python
@dataclass(frozen=True)
class FeatureSnapshot:
    feature_id: str
    entity_id: str
    world_xy: tuple[float, float]
    visibility: float
    priority: float
    # Bounds/local attachment frame would require an explicit future schema.

# Research-only signatures:
# observe(compact_state, memory, observation_tick) -> MemoryState
# predict(compact_state, memory, horizon_seconds) -> ForecastWithQuality
# color_targets(script_cues, palette, authored_overrides) -> RegionColorTargets
# frame_camera(features, previous_camera, authored_plan) -> Camera2DProposal
```

These added records do not belong in Build 0 `SceneState`. If a future camera follows the mustache, it should derive the landmark from its authored attachment frame and visible geometry, then smooth the view target under zoom/acceleration limits. A weighted focus switch must not teleport framing merely because an emotional color becomes brighter. Historical state can damp framing or retain focus priority; color can supply an authored narrative cue. Neither requires changing geometry. Occlusion/visibility uncertainty should produce a documented framing fallback, not invented 3D information. A 2D crop/translate/scale cannot reveal the reverse side of the mustache; actual perspective change needs depth or a new representation.

**Future evidence gates:** first finish baseline and creator review; then improve representation if needed and test attached identity features and scripted local color separately. Compare compact observation and one bounded conditioning rule against ordinary state/cue retuning, followed by optional short-horizon prediction. Study 2D feature cameras after landmarks are reliable. Phase-Memory and governance remain behind source reconciliation, qualified signals and demonstrated incremental value. These research studies can proceed independently when their inputs are ready. Safety-aware export design must precede public animated releases even if research color/memory is deferred. The larger research report supplies equations, alternative models, source limitations and study plans; none is an automatic approval to implement.

## 15. Copy-ready implementation directive — Build 0 only

The following directive is intended for a **separately authorized future coding session**. It is the final handoff, not authorization for source work during the v0.4 research assignment.

> **Implement Commander-ZORG Build 0 under the supplied v0.3 Architecture and Prototype Specification.** The authoritative supplied DOCX has SHA256 `3d367ddc9b0a4ec239d00889b4efd8f11a756521af8b49f79dcf8569676ab1fc`. Use v0.4's code-contract blueprint as an implementation plan and documentary clarification register; preserve v0.3 when they conflict unless an explicit recorded correction is approved. Do not treat illustrative unexecuted snippets as a tested engine.
>
> Work in a new local project directory. Preserve the privacy of `dfeen87/Commander-Zorg`. No GitHub writes, commits, pushes, repository visibility changes, publication or external messages follow from this directive; any future remote operation requires separate authorization. Do not modify upstream research repositories.
>
> Build only one fixed-root 2D positive-Gaussian entity, a fixed integer-tick clock, the specified semi-implicit Euler integrator with old-velocity damping and new-velocity position, exact quartic midpoint force cues, numeric ACCEPT/REJECT, grayscale spatial supersampling, PNG output, metrics and evidence. Use Python, NumPy and Pillow with pytest, recording exact dependencies/environment. Do not add memory/TMO/PMC, emotional colors, Phase-Memory, AILEE, advanced shaders, cameras, 3D, audio, semantic emotion inference, random runtime motion, retries, clamps or fallback policies.
>
> Start with `config.py`, `state.py`, `cues.py`, `motion.py`, `guard.py`, `field.py`, `raster.py`, `evidence.py` and `cli.py`. Record ADRs for sign, coordinates, integer timeline, numerical operation order, integrator/stability, reject/abort, supersampling, canonicalization and artifact/profile schemas. Use one immutable sorted element/cue plan. Scene state contains only tick, C-order float64 positions and velocities with independent owned arrays. Validate all configuration before creating an output directory.
>
> Preserve strict `cz-scene-0.3`: reject unknown/duplicate keys, invalid IDs/duplicates, bool-as-number, nonfinite values, wrong vectors/groups/enums/ticks/ranges/resources. Normalize semantic real fields to float64 and sort IDs. Enforce all scalar ranges, `h sqrt(k/m)<=0.25`, `hc/m<=0.25`, and `h²k/m+2hc/m<4`, with positive stiffness/damping. Conservatively sum norms of every cue targeting an element, including nonoverlapping cues, against the per-element force bound. The seed is provenance only.
>
> Use world y in [-1,1], world x in [-W/H,W/H], positive y upward and raster row zero at the top. Sample quarter/three-quarter pixel positions for s=2 on `(H*s,W*s)`. Evaluate fixed-ID separable Gaussians into one float64 field plus scratch and subtract threshold once. Check finite samples. Occupancy is `F>=0`, gray8 is `floor(255*coverage+0.5)`, and inversion is display-only after quantization. Export mode-L PNG at compression 6 with optimization disabled and no engine metadata. Do not use this field as distance or normalize it dynamically.
>
> Implement static components first and pass independent V01/V02/ownership/V03/V04 checks. Produce six explicit E0 presets with 5–12 controls, documented common weight/threshold policy, resolved scenes, six images and a labeled sheet; at least four decoded images differ. Selected usable baselines have finite fields, occupancy [0.03,0.65] and no nonzero coverage in the outer two pixels. Keep exploratory failures labeled and creator selection pending until supplied.
>
> Add the exact cue/motion/guard pipeline. Cues sample transition n→n+1 at n+0.5 with `16u²(1-u)²` inside support; sum in cue-ID order and apply full vector independently to every group member. Validate previous state before proposal. ACCEPT commits only after its decision record has been successfully written. REJECT records attempted tick/source hash/reasons, preserves committed state and aborts nonzero. Never clamp, retry, reset, advance a frozen pose, replace a bad state with baseline or publish a complete manifest after rejection. Nonfinite diagnostics must be valid JSON strings.
>
> Pass V05/V06/V07 using independent arithmetic, analytic and failure fixtures. For default `m=1,k=14,c=5`, displacement 0.2 and zero velocity over two seconds, max 60 Hz position error against the independently evaluated continuous spring solution is <=0.01 and smaller at 120 Hz. In the forced nominal 60/120 Hz comparison, double cue/recovery tick boundaries, preserve physical timing and output cadence, and require max per-element Euclidean position discrepancy <=0.01; report velocity differences separately.
>
> Render nominal E1 at 384×384, s=2, 180 frames/30 fps and 60 Hz. Render initial tick 0 first, output ticks 0,2,…,358, and integrate through terminal tick 360 without exporting an extra frame: 360 accepted decisions and 361 states. Render the full 180-frame cue-off control with only cues emptied and scene ID changed. Save both configurations and complete independent artifacts.
>
> Calculate all E1 gates: no rejection/nonfinite/hidden edit/export failure; per-frame occupancy [0.03,0.65] and no coverage in outer two pixels; targeted peak displacement >=0.05; at least one disturbed frame aligned IoU <=0.90; at least ten distinct decoded E1 frames; bit-identical cue-off arrays and identical decoded control frames; every simulation tick 330–360 has max displacement <=0.01 and max speed <=0.02; every rendered recovery frame has baseline IoU >=0.98 and world-centroid displacement <=0.01. Empty masks/empty IoU unions fail relevant gates. Aligned IoU uses nearest-integer centroid alignment with zero-fill, never wrap. Keep creator review pending/accepted/rejected separate from numeric/image metrics.
>
> Save required `scene.input.json`, `scene.resolved.json`, numbered PNG frames, `contact_sheet.png`, `states.jsonl`, `decisions.jsonl`, `frames.jsonl`, `run_status.json` and final `manifest.json`; a separate gallery manifest and experiment manifest link E0/E1/control/replay/tests/report. Contact sheet frames are 0,23,38,50,60,90,120,165,179 and the measured minimum-aligned-IoU frame if different, with index/derived-time labels. Provide exact full-sequence playback instructions without requiring an optional encoder. Preserve failed takes and all tuning reasons.
>
> Refuse existing output destinations. Use temporary files and same-filesystem atomic rename, running/failed/finalized status, and publish complete manifest last after closed-artifact checks. Hash original raw bytes separately from normalized resolved JSON. Canonical JSON is UTF-8, sorted keys, compact separators, normalized negative zero, finite numeric values and one trailing newline. State hashes follow that recipe. Pixel hashes use `b"cz-gray8-v1\n" + ASCII("W,H\n") + row-major gray8 bytes`; also hash PNG files. Record actual executed source content, dependency lock, fixtures and environment; a Git commit alone is insufficient and no Git initialization is required.
>
> Complete V08–V12: genuinely excited/morphing recovery; empty/full/static/translated/flipped/missing fixtures; overwrite/write/interruption/truncated/wrong-mode/contact-sheet failures; recomputed integrity/trace/profile checks; two fresh processes for exact state/decision/pixel/PNG replay; active-cue and provenance-only-seed perturbation checks. Do not claim v0.3's old probe results as newly executed evidence. Every required test record has exact command, exit code and output summary.
>
> Report render/integrity/profile/replay/creator outcomes separately. CLI statuses are 0 success, 2 config/usage, 3 numeric rejection, 4 export/integrity, 5 replay mismatch, and 6 for dedicated profile failure. Render success alone does not mean E1 passed. Creator-review pending is not an automated failure. Measure field/raster/export/log/end-to-end time and memory where available; report the 30-second nominal usability target honestly without claiming hardware specifications prove it. Do not retain all fields/frames or allocate an influence-by-image tensor.
>
> Release gates are all required independent tests, complete E0 and E1/control evidence, numeric/image profile pass, integrity pass and demonstrated fresh-process exact replay under the recorded environment. State creator-review status explicitly; do not invent artistic acceptance. After the small gallery and two documented tuning passes, if no form is visually promising, compare circles/capsules or a constrained warp before adding layers. End with a factual Build 0 complete/incomplete record, passed/failed gates, evidence paths/hashes, exact commands/exits, creator status, measured timings, limitations, deferred systems and the smallest next experiment. **Stop after E0/E1; no integration, remote write or publication is implied.**
