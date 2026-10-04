#!/bin/sh
# Bouwt het Universe OS live-ISO (draai dit in de Debian 13-bouwomgeving; vraagt sudo voor live-build).
#   scripts/build-iso.sh   ->  uitvoer/universe-os-<versie>-amd64.iso + .sha256 + logs/
# Nodig: live-build, librsvg2-bin, dpkg-dev, python3-pywayland, libwayland-dev, pkgconf. Duurt 20-60 minuten.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT="$ROOT/uitvoer"
LIVE="$ROOT/live"
VERSION=$(python3 -c "import json;print(json.load(open('$ROOT/branding/universe.json'))['version'])")
STAMP=$(date +%Y%m%d-%H%M)
LOGS="$OUT/logs/$STAMP"
mkdir -p "$OUT" "$LOGS"

echo "== 1/4 Universe OS-pakket bouwen"
sh "$ROOT/scripts/build-deb.sh" | tee "$LOGS/build-deb.log"
mkdir -p "$LIVE/config/packages.chroot"
rm -f "$LIVE"/config/packages.chroot/universe-os_*.deb
cp "$OUT/universe-os_${VERSION}_all.deb" "$LIVE/config/packages.chroot/"

echo "== 2/4 Afbeeldingen voor de installer"
B="$LIVE/config/includes.chroot_after_packages/etc/calamares/branding/universe"
rsvg-convert -w 128 -h 128 "$ROOT/scripts/assets/logo.svg" -o "$B/logo.png"
rsvg-convert -w 960 -h 540 "$ROOT/pakket/universe-os/usr/share/universe-os/backgrounds/ruimte.svg" -o "$B/welcome.png"
chmod +x "$LIVE"/auto/* "$LIVE"/config/hooks/live/*.hook.chroot

echo "== 3/4 live-build (dit duurt lang)"
cd "$LIVE"
sudo lb clean --purge >/dev/null 2>&1 || true
lb config >"$LOGS/lb-config.log" 2>&1
sudo lb build 2>&1 | tee "$LOGS/lb-build.log" | grep -E '^(P:|E:|W:)|Error|error:' || true

echo "== 4/4 Resultaat"
ISO=$(ls -1t "$LIVE"/*.iso 2>/dev/null | head -1 || true)
if [ -z "$ISO" ]; then
    echo "Het ISO is NIET gebouwd. Zie $LOGS/lb-build.log" >&2
    tail -30 "$LOGS/lb-build.log" >&2
    exit 1
fi
NAME="universe-os-${VERSION}-amd64.iso"
sudo mv "$ISO" "$OUT/$NAME"
sudo chown "$(id -u):$(id -g)" "$OUT/$NAME"
cp "$LIVE/chroot.packages.live" "$LOGS/pakketversies.txt" 2>/dev/null || true
cp "$LIVE"/config/package-lists/*.list.chroot "$LOGS/" 2>/dev/null || true
(cd "$OUT" && sha256sum "$NAME" >"$NAME.sha256")
echo "Klaar: $OUT/$NAME ($(du -h "$OUT/$NAME" | cut -f1))"
cat "$OUT/$NAME.sha256"
echo "Logboeken en pakketversies: $LOGS"
