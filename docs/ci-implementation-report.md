# Strict CI foundation — implementation report

Base: latest verified main `cc9d5635149ddbef2190c67e36f0e165083a920c` (README capability PR #5 merged). Branch: `engineering/strict-ci-foundation`. No earlier workflow directory existed. The installed package is `commander_zorg`/`commander-zorg`, requires Python `>=3.12,<3.13`, and uses `requirements.lock` and pytest. Independent collection confirmed **716 tests**.

## Files and implementation

| File | Purpose |
| --- | --- |
| `.github/workflows/ci.yml` | Required PR/main/manual test matrix: Ubuntu 24.04 and macOS 15, Python 3.12 |
| `.github/workflows/deep-validation.yml` | Manual Linux-only full Build 0, semantic morph and original live verification |
| `scripts/ci.py` | Standard-library child exit-code/log recorder, passive pytest inventory plugin, strict outcome audit, summaries and compact report selection |
| `docs/ci.md` | Running CI, reading evidence, macOS triage, security, retention and optional required-check setup |
| `docs/ci-implementation-report.md` | This report, preservation and actual validation scope |
| `README.md` | Additive links to workflows and CI instructions |

The helper is needed to distinguish actual selected/executed tests and stage exit codes from incomplete execution. It does not implement numerical checks, alter assertions, mask pytest status or replace the repository's existing verification scripts. Test selection is the complete existing default suite. A separate audit rejects unexpected reduction below the 716-test baseline, deselection, skips/xfail/xpass, unexecuted test bodies and discrepancies with JUnit. No Python dependency was added.

## Locally executed validation

Platform actually executed: Linux x86-64, Python **3.12.14**. This is the managed development machine, not a GitHub Ubuntu runner or native Mac.

- A fresh Python 3.12 venv installed every locked dependency, installed the package with `--no-deps --no-build-isolation -e .`, and passed `python -m pip check`.
- The fast CI command ran the complete suite: **716 collected, 716 selected, 716 test bodies executed, 716 passed; zero failed, errors, skipped or deselected**. JUnit independently recorded 716 passing cases. Two existing `record_property`/xunit2 warnings remained visible; they were not hidden or treated as test failures.
- All seven requested `commander-zorg SUBCOMMAND --help` checks passed. Both E1 and control scene validations passed. No noninteractive invocation of the interactive labs was attempted.
- The full `scripts/run_build0.py` run repeated all 716 tests, rendered all six E0 candidates and E1/control, and passed cadence, integrity, fresh-process replay and complete profile gates.
- `morph-demo --no-mp4` and the existing checker passed with **600 frames, 1,201 states and six captures**.
- `live-demo --no-mp4` and the existing checker passed with **450 frames and 901 states**, including integrity and trajectory checks.
- Compact mathematical evidence collection passed: **369,356 bytes**, with no generated frames, traces, videos or source snapshots selected. Fast and deep stage summaries both reported every required local stage passed with exit status 0.
- All ten locked packages downloaded successfully as compatible wheels for macOS 15 arm64 and x86-64. NumPy's wheels target macOS 14+; Pillow wheels target macOS 11+ arm64 / 10.13+ x86-64. This checks distribution availability, not native installation, execution or numerical compatibility.
- Both YAML files parsed and passed `actionlint 1.7.7`. The temporary linter binary was downloaded from the authoritative upstream release and verified against its published SHA-256 manifest. It is not installed by the workflow or added as an application dependency.
- Pins were resolved against upstream Git tags: checkout v6.0.2, setup-python v6.2.0, upload-artifact v6.0.0. The workflows use full immutable commit SHAs.
- Temporary failure fixtures verified exact propagation of child exit 7 and complete log capture; stale-stage refusal; separate pass/fail/setup-error/teardown-error/skip/xfail/xpass classification; reduced-inventory rejection; independent JUnit rejection of forged all-pass totals; missing-stage failure; and compact-artifact exclusion of frames/source/traces. These intentional fixture failures are distinct from the passing application suite. The temporary fixtures did not change repository tests.

Representative commands actually executed from the checkout (using the relevant Python 3.12 venv):

```sh
python -m pytest --collect-only -q
python scripts/ci.py run --pytest-report pytest-outcomes.json pytest -- python -m pytest -q --junitxml=ci-results/pytest.xml
python scripts/ci.py run test-audit -- python scripts/ci.py audit-tests --junit ci-results/pytest.xml
python scripts/ci.py smoke
python scripts/ci.py summary fast
```

Deep commands used `ZORG_CI_RESULTS=outputs/ci-foundation-deep-results` and a fresh `outputs/ci-foundation-deep/` take:

```sh
python scripts/ci.py run --pytest-report pytest-outcomes.json build0 -- python scripts/run_build0.py --out outputs/ci-foundation-deep/build0
python scripts/ci.py run morph-demo -- commander-zorg morph-demo --out outputs/ci-foundation-deep/morph --no-mp4
python scripts/ci.py run morph-check -- python scripts/check_morph_demo.py outputs/ci-foundation-deep/morph/video/manifest.json --report outputs/ci-foundation-deep/morph/check_report.json
python scripts/ci.py run live-demo -- commander-zorg live-demo --out outputs/ci-foundation-deep/live --no-mp4
python scripts/ci.py run live-check -- python scripts/check_live_demo.py outputs/ci-foundation-deep/live/video/manifest.json --report outputs/ci-foundation-deep/live/check_report.json
python scripts/ci.py run test-audit -- python scripts/ci.py audit-tests --junit outputs/ci-foundation-deep/build0/tests/junit.xml
python scripts/ci.py run compact-reports -- python scripts/ci.py compact outputs/ci-foundation-deep
python scripts/ci.py summary deep
```

Local generated reports remain outside tracked source in `outputs/`; no frame sequences or new mathematical evidence files are committed. Local testing exercised the CI working tree based on the main SHA above. GitHub execution must independently establish acceptance for the submitted PR SHA and runner environments.

## Preservation and security review

The change is restricted to the six files listed above. The following diff must remain empty:

```sh
git diff cc9d5635149ddbef2190c67e36f0e165083a920c -- commander_zorg tests scenes morph_targets schemas requirements.lock pyproject.toml docs/results docs/live/results docs/morph/results
```

Existing verification scripts are unchanged; only `scripts/ci.py` is added. There are no modifications to field arithmetic, spring integration, state structures, force limits, morph recipes, scene definitions, renderer, terminal behavior, source-provenance contracts or historical test assertions. CI runs the existing gates without weakening them.

Both workflows restrict `GITHUB_TOKEN` to `contents: read`, disable checkout credential persistence and use only SHA-pinned GitHub-owned actions. No write credentials, new secrets, external reporting, public artifact hosting, deployment, Docker, administrative changes, workflow commits/pushes or automatic merge is introduced. PR testing uses `pull_request`, not `pull_request_target`. Reports stay in authenticated private GitHub Actions artifacts for seven days. Fast and deep concurrency groups include the workflow identity; matrix fail-fast is false, jobs have 15/30-minute limits, and full CLI demo rendering is manual only. Deep report selection has a 20 MiB limit and records disabled MP4 separately from required mathematical verification.

## GitHub execution and remaining acceptance

At initial API inspection, GitHub's REST and GraphQL requests were rejected with `Forbidden`; Git read access worked. Local YAML validation and local passing tests do not establish hosted Linux/macOS CI acceptance. The final PR/run status is recorded below after the submission attempt.

No macOS traceback has been supplied or observed locally. Repeated `F`/`E` progress letters do not identify a cause. If the hosted macOS matrix fails, use its exact failed/errored IDs, phase details, JUnit tracebacks and environment metadata to prepare a separate compatibility fix. Do not skip platform tests or change numerical tolerances. Native MacBook Terminal.app/iTerm2 acceptance remains a distinct outstanding check even after any hosted macOS pass.

Branch protection/rulesets are not changed or claimed active. After real successful hosted runs, an administrator can require `Tests (ubuntu-24.04, Python 3.12)` and `Tests (macos-15, Python 3.12)`. Deep validation stays manual initially. GitHub may require the new dispatch workflow to be present on the default branch before it can run; no merge is authorized to work around that limitation.
