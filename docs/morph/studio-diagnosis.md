# Checkpoint A — adaptive motion diagnosis

Baseline: PR #7 merge `a0da2378d705449d54eaeb3e73fbf402e873d385`.
The experiment imported `/workspace/ZORG/commander_zorg/morph_runtime.py`
from the repository under CPython 3.12.14, NumPy 2.3.5 and Pillow 12.3.0 on
Linux x86_64. No runtime source, target, limit or historical test was changed
during collection. The parent baseline suite separately passed 765 tests with
zero failures or skips. These results establish a Linux source baseline;
native Mac acceptance and the creator's installed environment remain separate.

The [machine matrix](studio-evidence/baseline-motion-matrix.json) retains parsed
commands, mode, shape and transition phase, requested/effective targets, prior
endpoint, independent conservative-budget diagnostics, rejection source,
mutation flags, numerical validity and replay outcomes. Detailed sessions and
all per-element corner budgets are retained in `work/checkpoint-a/`.

## Mandatory matrix results

All ten scenarios completed as eleven recorded runs (the final scenario uses
two identical numerical starting states). All **8,066 replayed states** were
valid, and every run reproduced its full final runtime snapshot exactly.
All command rejections left state, channels, events, captures, mode, shape
identity and trajectory hash unchanged. No simulation-step rejection occurred.

| Scenario | Observed result |
| --- | --- |
| Home → adaptive → up | Accepts absolute `[0, 0.3]`. A settled repeat also reports acceptance although its target does not change. |
| Cloud → adaptive → up | Accepts reduced `[0, 0.07443720568516347]`. |
| Cloud → up again after settling | First request adapts; second rejects at `_adaptive_command` because remaining endpoint progress is below `1e-6`. |
| Oval → cloud → up with overlap | At cloud phase `17/120`, adapts to the same `0.07443720568516347` Y endpoint. |
| Cloud + wander on → up | Adapts to Y `0.07443720568516347`. |
| Cloud + wander off, settled → up | Unexpectedly retains the same Y ceiling; completed wander blend's old start is still budgeted. |
| Cloud → up → left → up | Up adapts; both later requests reject because no meaningful feasible progress lies on their specified old-to-requested endpoint segments. |
| Rapid changes every seven ticks | Mixed accepted/reduced/rejected decisions, no state jumps or invalid commits; a changed direction can retain a component on the previous axis. |
| Up → cloud in adaptive mode | Home up succeeds; cloud rejects at strict `_admit`, with the original technical budget message. |
| Strict versus adaptive, identical starts | Matching state/channel digests: strict up rejects at `_admit`; adaptive up accepts reduced Y `0.07443720568516347`. |

The maximum measured displacement across the matrix was `0.5492608314`, speed
`0.3883420743`, and external bias-force magnitude `5.4993287283`, versus
unchanged limits `0.75`, `3.0`, and `6.0`. These are trajectory observations,
not replacement admission thresholds or guarantees for custom configurations.

## Confirmed implementation defects

**Expired channel starts remain in conservative admission.** `_admit` always
uses both stored shape, translation and squash/stretch endpoints and the
maximum of both wander endpoints. It never discards a start after its blend
has completed. The elapsed blend actually evaluates solely to its end, so
the old start can needlessly restrict all future requests. Five supplementary
recorded probes reproduced exact replay for another 5,285 valid states:

| Settled setup | Adaptive up Y |
| --- | ---: |
| Cloud; wander off once | `0.07443720568516347` |
| Cloud; wander off twice | `0.233537470649755` |
| Cloud; morph home once | `0.07443720568516347` |
| Cloud; morph home twice | `0.3` |

At the first wander-off result, the current wander value is already exactly
zero. At the first home result, the current shape offsets are already exactly
zero. Reissuing the same completed command refreshes its stored start and
unlocks otherwise lost capacity. This is a confirmed cause of inconsistent
creator experience and of the unhelpful advice to turn already-disabled wander
off. Correct this only for a newly versioned creator runtime; historical events
must retain their original admission and exact replay meaning.

**The full-feasible branch can report success with no target movement.**
`_adaptive_command` checks the meaningful endpoint change only after full
endpoint admission fails. A settled home `up`, followed by the same `up`,
is accepted with `fraction=1`, unchanged endpoint `[0, 0.3]`, a new event and
refreshed translation bookkeeping. A no-wander probe isolates this from organic
motion. An unfinished identical target can appropriately say that its existing
transition is continuing; a settled unchanged target must not claim new motion.

## Intended constraints and feedback limitations

Historical directional commands request **absolute local deformation targets**.
They neither accumulate relative movement nor initiate continuous travel.
Repeated cloud up at a saturated endpoint is therefore a valid rejection.
The 48-step bisection is deterministic, and independent analytic quadratic
corner calculations agree with its feasible segment bounds. Duration does not
authorize an unsafe endpoint. A straight segment from a saturated endpoint
toward another absolute target may have no feasible positive-length portion;
this does not prove that every possible safe alternative path is impossible.

Shape, squash/stretch and wander changes remain strict even when directional
auto mode is enabled. The reproduced up-then-cloud failure comes from this
strict path, not failed bisection. Shape deformation, directional offsets and
wander all consume the same local force/displacement enclosure. Unfinished
transitions can legitimately require both still-reachable endpoints. Reports
should identify the rejected operation, active channels and true limitation.

Admission constrains future target offsets and external bias forces. It does
not replace the separate `LiveRuntime.step` force check, `check_transition`, or
state speed/displacement validation. The existing custom-limit regression
demonstrates spring overshoot can reject after equilibrium admission while
preserving the last valid state. Nothing here supports increasing limits,
relabelling invalid state, or silently repairing a rejected step.

Every test runtime starts strict, and the recorded mode switch is explicit.
These probes use the checked-out source directly, so stale installation is not
the cause of the reproduced behavior. They do not establish what version was
installed on the creator's Mac. Native diagnostics should record executable,
module file, package/source version, config and actual active mode.

## World-travel decision gate

The current additive translation is a local spring-target deformation bias.
The matrix establishes a real cloud saturation limit, and rigid world travel
could move that cloud without spending its internal deformation budget. It
would, however, require explicit versioned transform events, independent bounds
and timing, material-local color coordinates, camera/framing rules, clipping
validation, terminal mapping, export and replay integrity. Existing full-frame
exports reject clipped silhouettes. The matrix does not establish that these
contracts can all be introduced safely in a narrow motion repair.

**Defer world travel to a separate engineering pass.** Repair expired-corner
admission and truthful feedback first; preserve absolute historical semantics.
Do not advertise travel as available in the current product. A later pass
should add explicitly named rigid translation operations and render from
`world_transform(local_state)` while leaving all local dynamics guards intact.

## Reproduction

`scripts/diagnose_morph_motion.py` is explicitly **baseline-only**. Its embedded
engine-source inventory refuses a newer runtime instead of relabelling current
behavior as PR #7 evidence. Copy this script into an unchanged checkout of the
baseline commit, install `requirements.lock`, and run:

```sh
python scripts/diagnose_morph_motion.py --out work/motion-baseline-new
```

Use a new output directory. The script records the mandatory matrix plus four
expired-corner probes, invokes source-bound session verification and compares
the full replayed runtime snapshot. The original execution scripts and the
separate no-wander no-op probe remain under `work/checkpoint-a/`. Once engine
sources change, original baseline sessions correctly refuse verification in
the newer source environment; use their recorded original source environment
to replay them.
