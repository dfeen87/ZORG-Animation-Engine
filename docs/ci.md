# Continuous integration

[Fast CI workflow](../.github/workflows/ci.yml) · [Manual deep verification](../.github/workflows/deep-validation.yml) · [Implementation evidence](ci-implementation-report.md)

## Required cross-platform gate

`ZORG CI` runs for pull requests targeting `main`, pushes to `main`, and manual dispatches. Both explicit runner images use Python 3.12:

- `Tests (ubuntu-24.04, Python 3.12)`
- `Tests (macos-15, Python 3.12)`

Checkout uses the exact event SHA. For a pull request, this is GitHub's synthetic merge commit, so the tests cover the proposed change integrated with its base. Diagnostics record both event and checkout SHAs and fail if they differ. Matrix fail-fast is disabled: a Linux failure does not cancel macOS or vice versa. Each job has a 15-minute timeout. Superseded runs of this workflow for the same pull request/ref are canceled; the concurrency group includes the workflow name.

Install the full `requirements.lock`, then install the package without dependency resolution or isolated build dependency upgrades:

```sh
python -m pip install --disable-pip-version-check -r requirements.lock
python -m pip install --disable-pip-version-check --no-deps --no-build-isolation -e .
python -m pip check
python -m pytest -q --junitxml=ci-results/pytest.xml
```

CI executes that pytest command through `scripts/ci.py` with a passive reporting plugin. The plugin observes collection and setup/call/teardown outcomes; it does not change test selection, assertions, markers, skips, exit codes or engine behavior. Third-party plugin auto-discovery is disabled to keep the locked environment reproducible; pytest's built-in functionality and the explicit passive reporter remain enabled. No terminal, morph, mathematical, replay or evidence tests are excluded. No `-x` is used.

The observed baseline is **716 tests** on main `cc9d5635149ddbef2190c67e36f0e165083a920c`. `BASELINE_TESTS` is a minimum, not a limit on growth. The test audit rejects a count below 716, deselection, collection errors/skips, missing test bodies, nonzero pytest exit status, and any failed, errored, skipped, xfailed or xpassed outcome. JUnit must independently confirm the same passing inventory. A legitimate future reduction requires explicit review and an updated documented baseline; adding tests requires no baseline adjustment. A count alone cannot prove unchanged assertions, so code review still matters.

The helper records both collected and selected counts, the exact count of executed call phases, and per-test outcomes and phase details. Setup errors are reported as errors even though that test body never ran; teardown errors remain errors even when the body passed. They are not counted as additional tests just because JUnit emits a second row. Collection failures retain their identifiers and traceback. A step that did not start is reported as `not_executed`, never passed.

Safe CLI smoke checks call `--help` for `validate`, `live`, `live-demo`, `morph-lab`, `morph-demo`, `render-morph-session` and `verify-morph-session`, then actually validate `scenes/e1.json` and `scenes/control.json`. They do not launch interactive apps. The existing pytest PTY tests exercise terminal behavior in genuine pseudo-terminals.

## Diagnostics and failure behavior

Each job uploads `ci-results/` to this private repository's Actions artifact storage for **7 days**, on success or failure. Artifacts and job summaries contain:

- OS, architecture, Python, installed distribution versions, optional FFmpeg availability and commit SHA.
- Every stage's child command, exact exit status, elapsed time and outcome; complete merged stdout/stderr logs.
- JUnit XML, selected/collected/executed counts, per-phase outcomes and failing/errored test IDs.
- A summary identifying missing or unfinished mandatory stages.

See the step log and JUnit for full tracebacks, not only pytest's progress letters. CLI checks and test audits can run after pytest fails to collect independent diagnostics; the original failed step remains failed. No `continue-on-error`, ignored shell failure or success reclassification is used. A zero-test run, unexpected skip, expected failure or missing required result cannot make the gate green. Diagnostic and artifact upload failures also fail the job. Job cancellation or a hard timeout can prevent the final upload; GitHub's failed/canceled job and live logs remain authoritative in that case.

## Investigating macOS failures

A macOS failure is a failing cross-platform gate even when Linux passes. Compare failed test IDs and setup/teardown tracebacks with Linux, then inspect the recorded Python/dependency versions, architecture and OS. Possible investigation areas include PTY control, process lifecycle, filesystem assumptions and compiled-library differences; none is a confirmed cause merely because the platform is macOS.

Reproduce the exact failing command using Python 3.12 and the lockfile on the affected Mac. Preserve JUnit and logs before making a separate, focused compatibility fix. Do not disable platform tests, add skip/xfail markers, change numerical tolerances or bypass source-provenance checks to obtain green CI. Regenerate evidence within each environment; cross-platform bitwise image identity is not asserted by this workflow. A hosted macOS test pass would still leave native Terminal.app/iTerm2 creator acceptance to the existing manual procedure.

## Manual mathematical verification

`ZORG Deep Validation` is **workflow_dispatch only**, initially on `ubuntu-24.04` with Python 3.12 and a 30-minute timeout. It is not required on every PR or push. Once the workflow is on the default branch, use Actions → ZORG Deep Validation → Run workflow and select the intended ref, or:

```sh
gh workflow run deep-validation.yml --ref main
```

GitHub may require a dispatch workflow to exist on the default branch before it can be launched; its absence there is not a reason to add automatic render triggers to this PR.

The workflow uses a fresh `outputs/ci-RUN_ID-RUN_ATTEMPT/` take and executes:

```sh
python scripts/run_build0.py --out "$ZORG_CI_TAKE/build0"
commander-zorg morph-demo --out "$ZORG_CI_TAKE/morph" --no-mp4
python scripts/check_morph_demo.py "$ZORG_CI_TAKE/morph/video/manifest.json" --report "$ZORG_CI_TAKE/morph/check_report.json"
commander-zorg live-demo --out "$ZORG_CI_TAKE/live" --no-mp4
python scripts/check_live_demo.py "$ZORG_CI_TAKE/live/video/manifest.json" --report "$ZORG_CI_TAKE/live/check_report.json"
```

The Build 0 runner executes the complete suite, all E0 candidates, E1 and control sequences, cadence study, integrity, fresh-process replay and profile gates. Its pytest subprocess is observed by the same passive inventory reporter. Morph and live checkers recompute genuine mathematical/image/replay evidence; output-directory existence is not a pass. Every stage retains its own exit code, and independent demos can still run after a failed Build 0 stage. Missing evidence causes verification failure.

MP4 encoding is explicitly disabled for this gate. That is recorded separately from test outcomes; unavailable FFmpeg is optional and never substitutes for PNG/HTML or mathematical acceptance. No existing geometry, numerical or replay gate is reduced for speed.

Only compact reports, JUnit/logs, statuses, manifests and timing files are uploaded. Frames, state/event traces, captured images, source snapshots, PNGs, HTML media bundles and videos are excluded from uploaded deep artifacts. Compact mathematical reports have a 20 MiB aggregate limit; exceeding it fails the collection step rather than silently dropping reports. Generated frames stay in the ephemeral runner filesystem and are never committed.

## Security and maintenance

Both workflows use `permissions: contents: read`, disable persisted checkout credentials, and use only GitHub-owned checkout, Python setup and artifact upload actions pinned to full commit SHAs with release labels. Updating a pin requires checking the corresponding upstream tag and reviewing release notes. No write token, deployment secret, external reporting service, telemetry integration, Docker, downloaded installer script, automatic merge or repository push is introduced. Artifacts stay in GitHub's authenticated private repository storage; do not publish them through public hosting.

No cache or new Python dependency is needed. Action dependencies are SHA-pinned; runner images and Python's 3.12 patch release remain GitHub-maintained, and diagnostics expose their actual versions. For local workflow linting, use a trusted `actionlint` release; it is a maintainer validation tool, not an extra application dependency.

## Optional protection of main

After observing successful runs, a repository administrator can manually require these exact job check names for `main`:

- `Tests (ubuntu-24.04, Python 3.12)`
- `Tests (macos-15, Python 3.12)`

Select checks as emitted by the installed workflow, require an up-to-date branch if appropriate, and retain review policy. This implementation does **not** create or change rulesets, branch protection or administrative settings. Protection must not be claimed active without GitHub confirmation. Leave deep validation as a manual research/release gate initially.
