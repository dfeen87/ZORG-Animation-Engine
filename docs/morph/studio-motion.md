# Creator motion contract 0.3

`morph-lab` uses `StudioRuntime`; the historical `MorphRuntime`, demo, event
0.1/0.2 semantics and numerical step remain unchanged. Creator events wrap
normalized operations with `future-corners-v1`. Replay applies that version's
admission explicitly; legacy events always use their original algorithm.

At the command tick, each channel's future quintic trajectory lies between its
current evaluated value and its endpoint. Enumerating these independent convex
corners, plus wander's unchanged analytic box, conservatively bounds every
future offset. Expired starts are unreachable and no longer reserve budget.
Force, displacement, speed, integration and target limits are unchanged.
Bisection remains 48 iterations on the segment from the previous translation
endpoint to the requested absolute endpoint. Meaningful endpoint delta must be
at least 1e-6; identical targets never acknowledge new movement in contract 0.3.

Directions set absolute **local deformation** targets. They do not accumulate
steps or initiate continuous world travel. Direction changes can preserve a
component of the prior endpoint when adapted. A tangent direction from a
saturated boundary can have no feasible positive segment; resetting/reducing
deformation is an explicit creator choice. No hidden shape or wander changes
are made. World translation is deferred as documented in the diagnosis.

| Command | Normalized intention |
| --- | --- |
| `motion gentle` | Direction strength 0.10 |
| `motion normal` | Direction strength 0.20 |
| `motion bold` | Direction strength 0.30 |
| `speed slow` | Transition 240 ticks / 4 seconds |
| `speed normal` | Transition 120 ticks / 2 seconds |
| `speed fast` | Transition 60 ticks / 1 second |
| `motion auto on/off` | Adapt directions / strict admission |

Settings persist until explicitly changed and are recorded as validated numeric
0.3 events. Directions, squash/stretch and morphs use the selected speed when
seconds are omitted. Explicit numeric strength/seconds override defaults for
that command. Wander/reset retain their historical two-second envelope.
Intensity controls amount; speed controls timing. Slower duration cannot admit
an unsafe endpoint. Bold is the initial intensity to preserve omitted-argument
0.30 behavior; normal speed preserves two seconds. Strict remains the initial
mode because old creator scripts can depend on explicit opt-in. The header
shows settings. `motion auto off` provides explicit research mode.

Morph, wander and squash/stretch still require strict admission, with explanatory
feedback. Auto affects directional commands only. Rejections do not record an
executed event or alter state. Independent dynamic guards can still reject a
later step under custom configurations, preserving the last valid state.

Historical sessions remain source/environment-bound, as before: use their
original checkout for exact replay. New source must not claim to verify an old
source inventory. The baseline source archive and rollback branch preserve that
path; the baseline-only diagnosis script checks its original inventory.
