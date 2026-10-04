#!/bin/sh
# Bouwt het universe-os deb-pakket uit pakket/universe-os (draai dit in de Debian 13-bouwomgeving).
#   scripts/build-deb.sh            ->  uitvoer/universe-os_<versie>_all.deb
# Nodig: dpkg-dev, python3-pywayland, libwayland-dev, pkgconf (voor het genereren van de Wayland-bindingen).
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT="$ROOT/uitvoer"
VERSION=$(python3 -c "import json;print(json.load(open('$ROOT/branding/universe.json'))['version'])")
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$OUT"

echo "Universe OS-pakket $VERSION bouwen"
cp -a "$ROOT/pakket/universe-os/." "$STAGE/"
find "$STAGE" -name '__pycache__' -prune -exec rm -rf {} +

# Centrale vormgeving en versie.
install -Dm644 "$ROOT/branding/universe.json" "$STAGE/usr/share/universe-os/universe.json"
echo "$VERSION" >"$STAGE/usr/share/universe-os/version"

# Python-bindingen voor wlr-foreign-toplevel (vensteroverzicht), gegenereerd met de pywayland-scanner.
PROTO="$STAGE/usr/lib/universe-os/shell/protocols"
rm -rf "$PROTO" && mkdir -p "$PROTO"
python3 -m pywayland.scanner -i /usr/share/wayland/wayland.xml \
    "$ROOT/scripts/protocols/wlr-foreign-toplevel-management-unstable-v1.xml" -o "$PROTO" >/dev/null 2>&1
touch "$PROTO/__init__.py"
[ -f "$PROTO/wlr_foreign_toplevel_management_unstable_v1/__init__.py" ] || { echo "Genereren van de Wayland-bindingen mislukt" >&2; exit 1; }

# Rechten: alles van root, programma's uitvoerbaar, de rest leesbaar.
find "$STAGE" -type d -exec chmod 0755 {} +
find "$STAGE" -type f -exec chmod 0644 {} +
for f in "$STAGE"/usr/bin/* "$STAGE"/usr/lib/universe-os/universe-* "$STAGE"/DEBIAN/postinst "$STAGE"/DEBIAN/postrm \
         "$STAGE"/DEBIAN/preinst "$STAGE"/DEBIAN/prerm; do
    [ -f "$f" ] && chmod 0755 "$f"
done
sed -i "s/@VERSION@/$VERSION/" "$STAGE/DEBIAN/control"
# Installed-Size in KiB (zonder DEBIAN/).
SIZE=$(du -sk --exclude=DEBIAN "$STAGE" | cut -f1)
sed -i "/^Version:/a Installed-Size: $SIZE" "$STAGE/DEBIAN/control"

# Syntaxcontrole vóór het inpakken: kapotte Python of shellscripts komen niet in het pakket.
python3 -m py_compile "$STAGE"/usr/lib/universe-os/shell/*.py
for f in "$STAGE"/usr/bin/* "$STAGE"/usr/lib/universe-os/universe-*; do
    case "$(head -c 40 "$f")" in
        '#!/bin/sh'*) sh -n "$f" ;;
        '#!/usr/bin/python3'*) python3 -m py_compile "$f" ;;
    esac
done
find "$STAGE" -name '__pycache__' -prune -exec rm -rf {} +

DEB="$OUT/universe-os_${VERSION}_all.deb"
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "$DEB" >/dev/null
echo "Klaar: $DEB"
dpkg-deb -I "$DEB" | sed -n '/Package:/,/Description:/p'
