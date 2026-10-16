# PERF_NOTES R67-WORLDJS (world.js, third pass)

## Change
1. `drawBoom()` (login explosion, 240 sparks per frame, about 1.2 s): `Math.cos/sin(s.a)` per spark is precomputed
   in `SPARKS` (`ca`, `sa`), the two spark colour strings (`alpha()` + template) and the `d0` easing factor are
   computed once per frame instead of once per spark. Same inputs and same operation order.
   - Output: bit-identical. 20,000 random frames (t, centre, size, light/full mode): every strokeStyle, lineWidth,
     moveTo and lineTo compared, 0 differences.
   - Measured (node, mock canvas that records calls, 20k frames of 240 sparks): old 5.6-6.0 s, new 3.8-3.9 s (about 1/3 less).
     Per frame this removes 960 trig calls and 240 string builds.

## Looked at, skipped
- `project()`/`shownAt()` result objects, star loop, rings, planet DOM writes: already handled in R8/R22 or API change for tiny gain.
- Grouping sparks by colour: changes paint order of overlapping strokes, not identical output.
- `drawSky()` own cos/sin (4 per frame): negligible.

## Risk
Very low. Only runs during the login animation. Not tested in a live WebKit session (node + syntax check only).
