# ADR 0002 — A01/A02 evidence and noncircular publication

Accepted before evidence exporter implementation. These JSON contracts fill
v0.4 audit findings A01/A02; they do not change v0.3 numerical thresholds.

All JSON uses UTF-8, sorted keys, compact separators, one trailing newline,
finite numbers and normalized negative zero. Resolved reals are floats. Raw
input bytes are independently hashed. JSONL records are canonical JSON objects
with no blank rows. SHA-256 is integrity evidence, not a signature.

Exact trace objects:

- state: `tick, positions, velocities` (ordered Nx2 arrays).
- ACCEPT: `attempted_tick, status, source_state_hash,
  committed_state_hash, reasons` (empty reasons).
- REJECT: same except no committed hash; reasons contain code/path/element_id/
  safe string detail. Invalid candidate numbers need no hash.
- frame: `index, tick, path, mode, width, height, file_sha256, pixel_sha256,
  metrics`. Metrics: occupancy, centroid, bbox, clipping, empty, iou,
  aligned_iou, centroid_distance, field_min, field_max. Pixel hashing is
  SHA-256(`cz-gray8-v1\n` + decimal `W,H\n` + row-major bytes).

`cz-run-status-0.3`: schema_version, scene_id, state
(`running|failed|complete`), last_committed_tick, error_code.

`cz-run-manifest-0.3`: schema_version, engine_version, scene_id, config
(`raw_sha256,resolved_sha256`), element_order, policies, timeline
(`sim_hz,fps_out,frame_count,stride,terminal_tick`), expected
(`frames,states,transitions`), counts (`accepted,rejected`), artifacts
(relative path -> SHA-256), source (`digest,index_path`), environment,
verification (`closed_artifacts`), timings, warnings, creator_review
(`status,source`), contact_frames. Canonical JSON schemas live in schemas/.
Artifact paths are normalized, relative, unique, nonescaping; symlinks are
rejected. The manifest does not hash itself. Source snapshots include actual
engine files, dependency lock and scene fixtures, with a sorted hash index.
Environment includes Python, NumPy/build, Pillow, zlib, OS and architecture.

Each run owns a new destination. Publish frames atomically. Close traces,
generate contact sheet plus hashed index, then validate the prospective manifest
and closed artifacts in memory while status is running. Only after those checks
pass, finalize complete status once, hash it, and atomically publish manifest
last. Run the public verifier afterward. If public verification fails, preserve
the immutable published files and report invalid evidence. A complete status
without manifest remains incomplete. Ordinary close and rename are promised,
not power-loss durability. No candidate is committed before its decision closes.

Integrity recomputes hashes, trace links, guards, schedule, decoded image
properties and metrics; contact sheets are regenerated from indexed frames.
Replay verifies the recorded source/environment match, invokes a fresh Python
process, and compares state/decision bytes, decoded pixel hashes and PNG hashes.
Timings, destination paths and operational replay reports are not invariants.

`cz-experiment-0.3` links E0, E1, full control, cadence, replay and tests through
relative path/hash objects; it records tuning and creator review. Profile checks
recompute quantitative gates and validate linked evidence. Creator review stays
pending until explicit human input. Successful artifact export is separate from
profile acceptance and exact replay. Schemas, executable checks and corruption
tests together define the concrete evidence interchange.
