# Build 0 scene decisions

Authority is the SHA-256-verified v0.3 specification. The original JSON at
paragraphs P0120–P0206 is transcribed into `scenes/e1.json` without numerical
changes. E1 remains a provisional mathematical candidate; no creator selection
or recognizable-character claim is recorded. The initial experiment uses this
exact seed before any tuning is considered.

The eight controls use the source masses 1, stiffnesses 14 and damping 5. The
`surprise` cue applies force `[2, 1]` independently to the two head controls,
at midpoint samples of transitions 45 through 119. Its endpoints remain ticks
45 and 120. `scenes/control.json` differs only in scene ID and its empty cue
array. The required 180-frame control is a separate complete run.

The six E0 inputs are explicit JSON files, with eight controls each. All retain
the seed's weights, threshold 0.85, dynamics, limits, raster policy and provenance
seed. Each uses one output frame and no cues. Geometry changes below list every
change relative to the E1 seed; unlisted positions and sigmas remain unchanged.
Coordinates and sigma are in world units. These are exploratory shapes, not
final character artwork.

| Preset | Home-position changes | Sigma changes |
| --- | --- | --- |
| `e0_01_seed` | None | None |
| `e0_02_wide` | accents `(-.34,.28)`, `(.34,.28)`; bases `(-.20,-.46)`, `(.20,-.46)` | None |
| `e0_03_tall` | head_00 `(0,.38)`, head_01 `(.08,.59)`, core_00 `(0,-.30)`; bases `(-.13,-.56)`, `(.13,-.56)` | None |
| `e0_04_asymmetric` | head_00 `(-.10,.30)`, head_01 `(-.03,.50)`; accents `(-.33,.34)`, `(.19,.20)` | None |
| `e0_05_compact` | head_00 `(0,.23)`, head_01 `(.06,.38)`, core_00 `(0,-.19)`; bases `(-.13,-.37)`, `(.13,-.37)` | core_00 `.27`, core_01 `.26`, head_00 `.22` |
| `e0_06_forked` | accents `(-.30,.42)`, `(.30,.42)`; head_00 `(0,.27)`, head_01 `(.08,.44)`; bases `(-.20,-.47)`, `(.20,-.47)` | accents `.12` each, head_00 `.18` |

The gallery retains all six results and labels visibility failures. A usable
baseline must have finite field extrema, occupancy in `[.03,.65]`, and no
nonzero antialiased foreground in the outer two-pixel band. At least four
candidate decoded images must differ. The seed is the provisional E1 baseline
only if its own measured gates pass. Creator artistic review remains pending.

No E1 tuning has been authorized by an undocumented parameter change. A future
take must record its input differences and reason, preserve the previous take,
and rerun the unchanged numerical and image gates. Never edit thresholds to
turn a failing result into a passing one.
