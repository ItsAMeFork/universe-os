# PERF_NOTES_R66-ASSETS

## Changes
- `scripts/assets/kern.png` (shipped as `backgrounds/kern.png`; swaybg + login/world CSS background): re-encoded with a
  uniform PNG "Sub" filter, single IDAT, zlib level 9 with Z_FILTERED.
  170687 -> 165290 bytes (-5.4 KB, -3.2%). Raw zlib streams tried: Sub 165280 (default) / 165233 (filtered) /
  Up 194876 / Avg 184138 / Paeth 198799 / None 172017 / min-sum adaptive 178812 (original was PIL-style adaptive).
  Verified: mode (RGB), size (1920x1080) and decoded pixel bytes identical to the previous file (`tobytes()` equal).
  Risk: none known; plain 8-bit RGB PNG, no ancillary chunks (none before either).

## Checked, skipped
- `scripts/assets/vergrendeld.png`, `ui/earth.png`: already at the best uniform filter; Z_FILTERED / other filters are larger.
- `scripts/assets/sterren.png`: best case (filter None) 42513 vs 42581 bytes, a 68-byte gain, not worth a commit.
- `scripts/assets/overgang.png`: not installed by build-deb.sh (generator output only), so no runtime effect; left alone.
- No palette conversion: kern/sterren/vergrendeld have >256 colours.
- `share/sounds/universe/*.wav`: plain PCM, nothing to strip losslessly (see R27).
- No zopfli/oxipng available and no new dependencies allowed.
