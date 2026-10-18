# Build 0 JSON contracts

These JSON Schema 2020-12 documents describe the concrete Build 0 interchange
records adopted in ADR 0002. They are reviewable contract artifacts. They do not
introduce a plugin system, a network schema service, or a runtime dependency on
`jsonschema`. References resolve to adjacent files in this directory. The
`$schema` URL identifies the standard dialect; the engine does not fetch it.

| Artifact | Documentary schema |
| --- | --- |
| Raw or resolved scene | `scene.schema.json` |
| Published run `manifest.json` | `run-manifest.schema.json` |
| Per-scene `run_status.json` | `run-status.schema.json` |
| Each `states.jsonl` row | `state-row.schema.json` |
| Each `decisions.jsonl` row | `decision-row.schema.json` |
| Each `frames.jsonl` row | `frame-row.schema.json` |
| `contact_sheet.index.json` | `contact-index.schema.json` |
| `source/index.json` | `source-index.schema.json` |
| Experiment manifest | `experiment.schema.json` |
| Fresh-process replay report | `replay.schema.json` |
| E0 gallery manifest | `gallery.schema.json` |
| E0 gallery `run_status.json` | `gallery-status.schema.json` |
| Independent cadence report | `cadence.schema.json` |
| Executed test report | `tests.schema.json` |
| Successful integrity result | `integrity.schema.json` |
| Final experiment profile result | `profile.schema.json` |

`common.schema.json` holds shared definitions. Every record object declares its
exact keys and rejects additional properties. Path/hash dictionaries use
constrained property names and values; they are intentionally indexed maps.
The gallery status has only its actual `state` field; its enclosing artifact
selects that schema. JSONL trace rows also carry no `schema_version`. Their
filenames and enclosing versioned run manifest select the row schema. Adding a
version field to those rows would change the adopted trace contract.

Scene validation and evidence verification in the engine enforce the executable
contracts. JSON Schema alone cannot prove all requirements. The strict JSON
parser rejects duplicate keys, nonstandard nonfinite literals and booleans used
as numbers. The scene loader additionally distinguishes integer tokens from
real tokens in integer fields, checks unique IDs, group membership, cue support,
aspect-dependent home bounds, solver conditions and conservative cue-force
sums. Standard JSON Schema `integer` means a mathematically integral value and
does not capture that token distinction. Resolved real fields and state arrays
use canonical float representations; canonical byte checks enforce them.

The verifier checks exact schedules, sorted element identity, corresponding
array lengths, finite numerical values, committed-state bounds, transition
arithmetic, state-hash links, frame regeneration, decoded and PNG hashes,
contact-sheet content, source snapshots, path containment and symlinks. A
schema match does not establish those relationships, exact replay, mathematical
correctness, experiment acceptance or creator approval.

`run-manifest.schema.json` describes the final published manifest. Before
publication, the internal prospective object deliberately has no finalized
wall/RSS timing fields or complete-status hash. That temporary object is not a
published artifact. The engine validates closed artifacts, finalizes status,
hashes it and atomically publishes the final manifest last, then verifies the
published result.

Creator review remains exactly `{"status":"pending","source":null}` in the
current implementation. No schema field implies an imported artistic opinion.
Tuning records are explicit strings describing configuration changes; their
presence does not authorize unrecorded numerical-policy changes.
