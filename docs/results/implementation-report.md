# Build 0 implementation report

The mathematical foundation and all automated evidence gates passed. Repository
delivery remains incomplete because GitHub API networking prevents required
canonical-name/privacy verification and pull-request creation. Source is
committed locally on `feature/build0-foundation`; no merge or public release
occurred. The implementation source commit is `01984b2` (based on
`0090e6322ce63621acb25ce05e26ac6a53bb68bb`). Creator review is pending.

## Completion record

| Claim | Actual outcome |
| --- | --- |
| Source files created | Passed: all nine requested modules, package metadata, canonicalization and experiments |
| Tests | 456 passed; 0 failed; 0 errors; 0 skipped; V01–V12 executed |
| E0 | Six explicit eight-control presets; six distinct decoded images; all six visibility gates passed |
| E1 and independent control | Both complete: 180 PNGs, 360 ACCEPT transitions, 361 states through tick 360 |
| Numerical/image acceptance | All unchanged v0.3 gates passed; no scene tuning needed |
| Artifact integrity | E0 child runs, E1, control and replay all passed |
| Fresh-process exact replay | State/decision trace bytes, decoded pixels and PNG bytes identical |
| Creator review | Pending; silhouettes have no claimed character recognition or artistic approval |

The numerical package uses Python/NumPy/Pillow and pytest for development.
config/state own strict sorted definitions and copied float64 arrays; cues/motion/
guard implement midpoint pulse, the prescribed Euler update and rejection;
field/raster evaluate the positive Gaussian sum and spatial coverage;
evidence/experiments/CLI orchestrate closed artifacts and independent gates.
[ADRs](../adr/) resolve A01/A02, operation order, exact trace/profile schemas and
manifest-last publication. No deferred system was implemented or modified.

## Reproduction and evidence

The actual complete command, from the checkout root, was:

```sh
python scripts/run_build0.py --out outputs/build0_take_01
```

It exited 0. Use a **new** output name when repeating. The runner executes tests
with JUnit output, then E0, E1, the complete control, independent cadence and
analytic references, fresh-process replay and cross-file profile verification.
Exact subprocess test arguments and raw output are retained in
`outputs/build0_take_01/tests/`. [README](../../README.md) contains MacBook venv,
installation, individual CLI, viewing and verification instructions. Open each
run's `player.html` locally for full-sequence playback; space pauses and arrow
keys step. The PNG timestamps remain authoritative.

Complete output is `outputs/build0_take_01/` (ignored by Git). Delivery includes
a separate evidence archive and source patch/package. Small contact sheets in
this directory are derived review aids; their full-source artifacts remain in
the evidence. The earlier `outputs/e1_baseline_probe` is retained as a successful
pre-final source probe, not substituted for final evidence or exact-source replay.
No candidate was discarded and no E1 scene parameter was changed.

| Evidence relative to final output | SHA-256 |
| --- | --- |
| `experiment_manifest.json` | `d47dc50371da90ec27270ea836e0fc3114cde0e80a755ae08a35e755ebdcba54` |
| `profile_report.json` | `872c733b30f7fab82c6180bc7e9bb60f37ccc9c0be654b3c52379b5514866e0f` |
| `e0/manifest.json` | `a1e435073ae2ccc2b1ae71836ac5ee9139fec0b86a56553d775c398ad336b6e8` |
| `e1/manifest.json` | `914a0c44aea392cca268ec762b53de4991a9a1e79f02ee49a8b32572185ad8e5` |
| `control/manifest.json` | `508e9d048d29fccd296852bbab3af3c60d18e4add9ad8f1ecf0efa83462e4da7` |
| `replay/replay_report.json` | `a390c5e33b0725534d1800c39657dfb54b3ae1a9ea2c53d85b843a3525fcb2dd` |
| `tests/test_report.json` | `588e8caf27a6dd79aa541a246e06f697f0b6dd9d5a430a5c5ec57c988f01ecea` |

Executed source/lock/fixture/test/runner content digest:
`7d5db3e56947f09d75416106f0155f6a12e30bde58a39ed0724d0bd57fa47890`. Full per-file snapshots and dependency versions
are included in each run, independently of Git revision. Git document-only
follow-up commits do not change that executed-source digest.

## Actual environment and performance

Linux x86_64;
Python 3.12.14, NumPy 2.3.5,
Pillow 12.3.0, pytest 9.0.2,
Python zlib 1.3.2,
Pillow zlib 1.3.1. No native macOS execution
occurred. Exact replay across operating systems or compiled math builds is not
claimed. The cloud machine reported five CPUs; numerical rendering is streamed
without an influence-by-image tensor or retained full-frame history.

The full experiment runner took 94.272s.
Measured around the actual API calls, including public integrity verification:
E0 1.012s; E1 14.499s;
control 14.370s; replay 24.234s.
The proposed 30s E1 iteration target was met on this machine.
The E1 manifest reports field evaluation 2.690s,
raster/metrics 1.802s, PNG export
0.333s, decision/frame log writes
0.044s, and peak process RSS
60284 KiB (Linux getrusage lifetime high-water).
Its wall field ends at manifest publication; `operation_timings.json` also
includes the subsequent public verification. Performance is measured evidence,
not a real-time or 4K claim.

## Repository delivery limitation and next step

Native Git reads and a branch-push **dry run** succeeded through the platform
proxy. That dry run changed no remote refs. REST/GraphQL requests to
`api.github.com` were refused by the enforced proxy policy before authentication.
Both unauthenticated repository-name pages returned 404; that is consistent
with private access but does not establish canonical identity/visibility metadata.
The required checks therefore remain unverified. The implementation branch has
not been pushed and no PR exists; this preserves the user's private-destination
requirement while metadata access is unavailable.

An additive `api.github.com` allowance plus tested install/start instructions
were saved in the environment draft. Review/save and publish that environment
configuration, then verify `full_name`, `private`, `default_branch` and remote HEAD
before pushing this existing branch and creating the private PR. Do not merge.
No new token is inferred to be necessary from this network failure.

Build 0 mathematical automated acceptance: **passed**. Overall repository
handoff: **incomplete pending GitHub metadata/PR access**. Creator review: **pending**.
The smallest next creative experiment is review of the full sequence and one
recorded geometry/force tuning take if requested. Memory, color, camera,
authoring and community systems remain deferred.
