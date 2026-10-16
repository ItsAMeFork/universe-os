# PERF_NOTES_R51-ASSETS

## Changes
- `scripts/assets/vergrendeld.png` (lock-screen background, shipped as `backgrounds/vergrendeld.png`, missed by earlier passes
  because they only looked under `ui/`): re-encoded with a uniform PNG "Sub" filter, single IDAT, zlib level 9.
  1063032 -> 849956 bytes (-213 KB, -20.0%). Raw zlib streams tried: Sub 849899 / Up 1079865 / Avg 975275 /
  None 1249388 / min-sum-abs adaptive mix 954705 (the original used PIL-style adaptive filters, 1059867 of IDAT).
  Verified: mode (RGB), size (2560x1440) and decoded pixel bytes identical to the previous file (`tobytes()` equal).
  Risk: none known; plain 8-bit RGB PNG, no ancillary chunks (none before either). Decode cost is the same or lower
  (Sub is a cheap unfilter).

## Checked, skipped
- `ui/earth.png`: already Sub-optimised in R27; no palette/bit-depth reduction possible (80862 colours, real alpha 0..255).
- `share/sounds/universe/*.wav`: plain PCM, nothing to strip losslessly (see R27); a codec change would alter references.
- No oxipng/zopflipng/zopfli available on this box and no new dependencies allowed, so no deflate-level gains beyond zlib 9.
- HTML/JS/CSS: all small; no safe invisible lazy-loading candidates (earth.png is intentionally eager).
- `docs/` screenshots left alone (docs is off-limits).
