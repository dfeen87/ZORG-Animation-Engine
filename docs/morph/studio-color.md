# Chromatic presentation contract 0.3

The original Gaussian evaluator, antialiased coverage raster, target recipes,
spring dynamics and numerical guards are unchanged. `ChromaticState` colors
that computed coverage after geometry. Color never enters the physics state.
Color is off initially; `color on` opts into preview and saved RGB animation.
`color off` restores familiar grayscale presentation. If a take ever enabled
color, its default export is RGB, including grayscale intervals. Use
`render-morph-session ... --grayscale` for independent original mode-L frames;
`--color` explicitly selects recorded RGB presentation for 0.3 sessions.

`palette auto` follows shape identity. Named `palette neutral/circle/oval/cloud/hill`
overrides persist across morphs; `palette auto` restores shape following.
There is no custom editor in this pass. Unknown mathematical target identities
use neutral under auto. Palette selection changes presentation only.

| Shape | Shadow RGB | Middle RGB | Highlight RGB |
| --- | --- | --- | --- |
| Home / neutral | 167,176,187 | 216,222,230 | 248,250,253 |
| Circle | 167,101,36 | 232,174,66 | 255,232,158 |
| Oval | 79,129,149 | 147,183,198 | 219,233,241 |
| Cloud | 73,145,208 | 126,197,240 | 218,241,255 |
| Hill | 48,103,68 | 105,164,104 | 195,223,158 |

Algorithm `material-gaussian-palette-v1` computes pixel-center material coordinates
by subtracting the influence-weighted displacement of the existing mathematical
controls from their homes. Under rigid motion, this translates with the object;
under deformation it is a smooth approximation, not a globally invertible map.
Fixed uint32 hashes with the recorded config seed generate two smooth lattice
textures at 9 and 43 cycles per world unit. A restrained material-local vertical
shade combines them. There is no animated random source, redraw counter or
wall-clock dependency. Smooth deformation can stretch the grain naturally.

Shadow/middle/highlight anchors interpolate directly in sRGB using the existing
quintic `6u^5-15u^4+10u^3`. Auto follows the exact morph start tick/duration.
Interrupting a morph samples the visible current anchors and starts from that
value. Geometry retains spring response, so the palette reaches its target on
the target-envelope timeline while the physical shape may continue settling.
Palette overrides use the active speed preset. Color-off intervals continue
tracking palettes so later enabling color reflects recorded shape history.

RGB foreground composites with original antialiased coverage over black, or
white for inverted scenes. Inversion is interpreted as background/coverage,
never as channelwise RGB inversion. Terminal preview un-inverts to the existing
bright-on-dark silhouette. `COLORTERM=truecolor/24bit` or direct-color TERM uses
24-bit ANSI; xterm-256color uses nearest standard color cube/grayscale entries,
including separate half-block foreground/background. Explicit `--mono` wins.
Unknown/dumb terminals retain portable blocks. Detection is advertisement-based;
actual Terminal.app/iTerm2 appearance still needs native creator review.

Creator 0.3 sessions store normalized color/palette events and use deterministic
initial settings. Captures include the complete chromatic blend, algorithm and
recomputed content ID. RGB exports have their own `cz-morph-export-0.3` manifest
and presentation seed/version, per-tick palette snapshots, RGB pixel/file hashes
and separate unchanged coverage hashes/geometry metrics. Verification regenerates
every frame and capture and validates metadata, contact sheet, player, source,
environment and chronology. Hashing altered frames and rehashing the manifest
cannot replace exact replay. Legacy grayscale export retains its 0.1 contract;
it never claims to verify RGB data. Mixed manually injected legacy captures in
an RGB studio take are explicitly unsupported; new creator commands always
produce chromatic snapshots.

The complete PNG sequence and local HTML player are authoritative color media.
Optional MP4 is encoded as H.264/yuv420p when FFmpeg/libx264 is available; lossy
MP4 is integrity-indexed but is not claimed pixel-identical to PNG. Source and
environment provenance remain strict, including for historical recordings.
