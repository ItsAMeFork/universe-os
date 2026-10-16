# PERF_NOTES_R104-ASSETS

## Changes
- `scripts/assets/overgang.png` (generator output of `maak-vergrendeld.html`, not shipped by `build-deb.sh`):
  re-encoded as one IDAT (was 10 fragmented IDAT chunks) with a uniform PNG None filter, zlib level 9.
  - Size: 38963 -> 32142 bytes (-6821, -17.5%).
  - Pixels: verified identical to HEAD with PIL (RGB, 2560x1440, `ImageChops.difference` bbox empty).
  - Risk: none at runtime (not installed). Only repo size changes.

## Checked, no change made
- `share/sounds/universe/*.wav` (17 files, ~7 MB): every file is `fmt ` + `data` only, RIFF size matches
  file length, no slack or trailing bytes. Nothing to strip losslessly. Converting to FLAC/Opus would change
  format and references, so skipped (same as R4/R27/R51).
- Byte-identical duplicates: none (md5 across all non-.git files over 1 KB).
- Sounds: all 17 are referenced (`universe-geluid` and the shell). None is dead.
- PNGs: `vergrendeld.png`, `kern.png`, `sterren.png`, `earth.png` already done in R4/R27/R51/R66
  (single IDAT, uniform filter). Not repeated.
- HTML: all under 4 KB. The only image loads are CSS backgrounds (`kern.png`) that must be present at
  first paint (login/world). Lazy loading would change timing, so not done.
  `earth.png` stays eager on purpose (see `globe.js`).
- Lazy-loading sounds: they are played on demand, so a deferred load would add latency at first play.
  That is a perceptible change, so skipped.

## Measurements
| file | before | after |
|---|---|---|
| scripts/assets/overgang.png | 38963 B | 32142 B |

Filter comparison for overgang.png (single IDAT, zlib 9): None 32085 (+ header), Sub 38370, Up 47302,
Average 45465, Paeth 41902. None is the smallest; PIL `optimize=True` gave 39628 (larger).

## Commits
- `perf(assets): losslessly recompress overgang.png` (repo size only)
