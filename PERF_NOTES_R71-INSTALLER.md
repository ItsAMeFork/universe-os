# PERF_NOTES_R71-INSTALLER

Area: live/ (Calamares modules, live-build config), scripts/ build scripts, universe-updates-run.

## Changed
- `scripts/build-deb.sh`: the pre-build JavaScript syntax check ran `node --check` once per ui/*.js file, sequentially
  (27 files, ~80 ms node start-up each). It now runs them in parallel with `xargs -P $(nproc)`.
  - Measured (8 cores): 2.17 s -> 0.40 s for the check.
  - Same check, same message (`Syntaxfout in <file>`); a failing file makes xargs exit 123, which aborts the script via
    `set -e` (verified with a deliberately broken file). Build-time only; the .deb is unchanged.
  - Risk: very low. Needs `xargs -0/-P` (GNU findutils, present on the Debian 13 build environment).

## Looked at, deliberately not changed
- `universe-updates-run`: every apt-get step (update, simulate, download, upgrade) is needed for the status/counting
  behaviour; nothing can be dropped or merged without changing behaviour. Python overhead is negligible next to apt.
- Calamares modules/sequence: unpackfs/initramfs/packages dominate install time; changing squashfs compression,
  initramfs scope or sequence would alter the image or behaviour, and cannot be verified here (no live-build/VM).
- `live/config/apt/apt.conf` (e.g. `Acquire::Languages "none"`) would drop Translation indices from the ISO: visible
  difference, skipped.
- Hooks 0100/0200: the `apt-get update` / `apt-get download` calls are required after `dpkg --add-architecture` and for
  the offline GRUB packages.
- Duplicate `py_compile` in build-deb.sh costs ~0.06 s; kept as a fail-fast check.

Not tested: a full `build-deb.sh` run (needs pywayland scanner/dpkg-dev) and any ISO build.
