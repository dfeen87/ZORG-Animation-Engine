# ADR 0001 — numerical baseline and scope

Accepted for Build 0. The user authorizes changes only in the existing ZORG
repository, on `feature/build0-foundation`, with no merge or public release.
The exact supplied normative v0.3 DOCX hashes to
`3d367ddc9b0a4ec239d00889b4efd8f11a756521af8b49f79dcf8569676ab1fc`.
Its mathematical contracts take precedence over the v0.4 proposals. The user
request supersedes historical documents' research-only/local-only restrictions.
The package stays `commander_zorg`; the scene schema stays `cz-scene-0.3`.

Positive Gaussian influences are accumulated in ASCII element-ID order into
float64 zeros, then threshold is subtracted once. For each element evaluate
horizontal/vertical exponential vectors, outer product, multiply by weight,
then add. No normalization, SDF interpretation, tail truncation or GPU path.
World y is upward, raster row zero at top; world height is two and x extent
uses image aspect. The dense uniform lattice uses `(index+0.5)/s`; s=2 means
quarter/three-quarter pixel samples. Coverage uses F>=0 and round-half-up to
gray8, with inversion afterward. PNG L, compression 6, optimize false.

Tick is the sole clock. Frame zero precedes stepping. Frame j uses tick j*R;
the terminal tick is frame_count*R with no extra output frame. Midpoint quartic
cues sum in cue-ID order, independently per target element. Damping uses old
velocity; position uses new velocity. Validate stability and both accuracy
inequalities before allocation. Independent analytic and cadence checks remain
mandatory. No random motion, clamping, retries, fallback or silent tuning.

State arrays are copied, C-order float64 and read-only under ordinary engine
use. Invalid test candidates can reach the pure guard; nonfinite values cannot
be serialized as committed state. Only a successfully closed ACCEPT record
permits commitment. Rejection terminates and preserves the previous state.

Policy names adopted from v0.4 as explicit implementation decisions:
`semi-implicit-explicit-damping-v1`, `uniform-grid-gray8-v1`,
`cz-json-python-v1`; existing `gaussian-separable-v1` and
`quartic-pulse-v1` are retained. Research involving memory, AILEE, color,
camera, community and narrative systems remains documentation only.
