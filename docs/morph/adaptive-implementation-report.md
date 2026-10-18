# Adaptive motion implementation report

Baseline: GitHub `main` at `23d087a19c5f09cad5ad5f61f69e939b0f103c61`
(October 18, 2026). The supplied checkout was behind; the current baseline was
inspected and synchronized through the GitHub connector because the executor's
configured Git proxy was unavailable. No CI workflow changes are part of this PR.

## Result

Directional commands in Morph Lab can now opt into conservative adaptive
admission with `motion auto on`; `motion auto off` restores strict behavior.
Default configurations remain strict. A safe requested endpoint is unchanged;
an unsafe endpoint triggers deterministic bounded bisection using the existing
combined force/displacement calculation. Only the translation channel changes.
The original numerical step, force guards, state guards, target definitions,
limits and Build 0/0.1 command grammar remain unchanged.

The [technical guide](adaptive-motion.md) documents the convexity argument,
48-iteration precision, meaningful-motion threshold, supersession behavior,
versioned event/session extension and MacBook acceptance steps. Presets were
left deferred because they are optional and would add another control surface.

## Measured demonstration

The [self-contained take](adaptive-evidence/session.json) records cloud with
wander active, requests `up` at tick 180 and finishes at tick 540. Feedback:

```text
STATUS: ADAPTIVE MOTION ACCEPTED
COMMAND: up
REQUESTED: 0.3
APPLIED: 0.0744372057
TARGET XY: (0, 0.0744372057)
SHAPE: CLOUD — PRESERVED
```

The full stored effective Y value is `0.07443720568516347`, selected fraction
`0.24812401895054492`. Shape, squash/stretch and wander channels were checked
unchanged at admission. All 541 states and 270 full-resolution frames passed
same-environment exact replay and export verification. Maximum observed force
was `5.166551852528211` against limit `6.0`; maximum observed displacement was
`0.5011789177188345` against limit `0.75`. These are measured trajectory maxima,
not substituted admission thresholds. See the [machine report](adaptive-evidence/report.json),
[before image](adaptive-evidence/before.png) and [after image](adaptive-evidence/after.png).
The full PNG/HTML sequence can be regenerated with the documented demo command;
MP4 was explicitly disabled for this demo.

## Verification

The complete unchanged historical inventory contains 716 tests. The new file
adds 49 regressions: unchanged safe motion, reduced unsafe motion, saturated
rejection, preserved identity/channels, strict defaults/toggles, deterministic
selection and maximality bracket, active-transition supersession, duration
independence, both numerical limits, effective values below the old grammar's
minimum, nonmutating invalid/tampered requests, effective replay, version
separation, actual PTY feedback/recording and unchanged non-directional behavior.
Existing tests and numerical thresholds were not modified.

The final complete suite passed **765 tests**, with **0 failures, 0 skips**
and two existing JUnit warnings in 30.64 seconds.
The [inventory audit](adaptive-evidence/test-audit-report.json),
[JUnit XML](adaptive-evidence/pytest.xml) and [full output](adaptive-evidence/pytest.log)
are retained alongside this report. The Linux PTY path was exercised by both old and new tests. Native macOS
and GitHub-hosted CI outcomes must be assessed separately; no MacBook pass is
claimed from this environment. Existing optional FFmpeg coverage and all PTY
tests remain enabled. Warnings from existing `record_property` tests under
JUnit xunit2 are reported as warnings, not hidden or converted into failures.

A custom tightly bounded displacement fixture also demonstrates that the
unchanged dynamic guard can reject spring overshoot after target admission;
the last valid committed state remains intact. Adaptive target feasibility
never suppresses a later force/state rejection. This preserves the existing
safety contract and is documented as a limit of target admission.

Intermediate new-test failures revealed incorrect test assumptions about
stretch feasibility and equilibrium displacement versus dynamic overshoot.
Those new tests were corrected to check strict-channel equivalence and actual
guard rejection respectively. No existing tests or safety limits were changed.

Creator artistic approval and native MacBook acceptance remain pending. The
pull request is intended for review against `main`; no merge is performed.
