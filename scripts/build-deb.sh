#!/bin/sh
# Bouwt het universe-os deb-pakket uit pakket/universe-os (draai dit in de Debian 13-bouwomgeving).
#   scripts/build-deb.sh            ->  uitvoer/universe-os_<versie>_all.deb
# Nodig: dpkg-dev, librsvg2-bin, python3-pywayland, libwayland-dev, pkgconf (voor het genereren van de Wayland-bindingen).
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

# Eigen updatebron (docs/UPDATES-VOORSTEL.md). De publieke sleutel gaat mee zodra hij bestaat; de bron zelf pas als hij
# echt online staat en getest is (scripts/apt/bron-actief), anders krijgt een ISO een onbereikbare bron mee.
# UNIVERSE_APT_URL zet hem ook aan (alleen voor tests). Kanaal stable voor iedereen; een testcomputer zet het
# testkanaal aan met een extra universe-os-test.sources (Suites: test).
if [ -f "$ROOT/scripts/apt/universe-os-updates.asc" ]; then
    install -d "$STAGE/usr/share/keyrings"
    gpg --dearmor <"$ROOT/scripts/apt/universe-os-updates.asc" >"$STAGE/usr/share/keyrings/universe-os-updates.gpg"
fi
if [ -f "$ROOT/scripts/apt/universe-os-updates.asc" ] && { [ -f "$ROOT/scripts/apt/bron-actief" ] || [ -n "${UNIVERSE_APT_URL:-}" ]; }; then
    install -d "$STAGE/etc/apt/sources.list.d"
    cat >"$STAGE/etc/apt/sources.list.d/universe-os.sources" <<SRC
# Universe OS: updates van de interface en instellingen (ondertekend; sleutel alleen geldig voor deze bron).
Types: deb
URIs: ${UNIVERSE_APT_URL:-https://itsamefork.github.io/universe-os-apt/}
Suites: stable
Components: main
Signed-By: /usr/share/keyrings/universe-os-updates.gpg
SRC
fi

# Vergrendelscherm (swaylock --image): planeetstijl met "Vergrendeld". swaylock schaalt het per scherm.
rsvg-convert -w 2560 -h 1440 "$ROOT/scripts/assets/vergrendeld.svg" -o "$STAGE/usr/share/universe-os/backgrounds/vergrendeld.png"

# Python-bindingen voor wlr-foreign-toplevel (vensteroverzicht), gegenereerd met de pywayland-scanner.
PROTO="$STAGE/usr/lib/universe-os/shell/protocols"
rm -rf "$PROTO" && mkdir -p "$PROTO"
python3 -m pywayland.scanner -i /usr/share/wayland/wayland.xml \
    "$ROOT/scripts/protocols/wlr-foreign-toplevel-management-unstable-v1.xml" -o "$PROTO" >/dev/null 2>&1
touch "$PROTO/__init__.py"
[ -f "$PROTO/wlr_foreign_toplevel_management_unstable_v1/__init__.py" ] || { echo "Genereren van de Wayland-bindingen mislukt" >&2; exit 1; }

# Elk bestand onder /etc is een conffile: eigen aanpassingen van de gebruiker worden bij een update niet stil
# overschreven (dpkg vraagt het dan). DEBIAN/conffiles hoeft dus niet met de hand bijgehouden te worden.
(cd "$STAGE" && find etc -type f | sed 's|^|/|') | sort -u | cat - "$STAGE/DEBIAN/conffiles" 2>/dev/null | sort -u >"$STAGE/DEBIAN/conffiles.nieuw"
mv "$STAGE/DEBIAN/conffiles.nieuw" "$STAGE/DEBIAN/conffiles"
while read -r f; do [ -f "$STAGE$f" ] || { echo "conffile $f bestaat niet in het pakket" >&2; exit 1; }; done <"$STAGE/DEBIAN/conffiles"

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
