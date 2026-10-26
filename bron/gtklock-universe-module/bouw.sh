#!/bin/sh
# Bouwt uitvoer/universe-os-vergrendelknoppen_<versie>_amd64.deb (in de Debian 13-bouwomgeving; nodig: gcc, libgtk-3-dev).
set -eu
HIER=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HIER/../.." && pwd)
VERSION=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "$ROOT/branding/universe.json")
ARCH=$(dpkg --print-architecture); MA=$(dpkg-architecture -qDEB_HOST_MULTIARCH)
S=$(mktemp -d); trap 'rm -rf "$S"' EXIT
install -d "$S/DEBIAN" "$S/usr/lib/$MA/gtklock" "$S/usr/share/doc/universe-os-vergrendelknoppen"
gcc -shared -fPIC -O2 -Wall -o "$S/usr/lib/$MA/gtklock/universe-knoppen-module.so" "$HIER/universe-knoppen.c" \
    $(pkg-config --cflags --libs gtk+-3.0 gmodule-2.0)
strip --strip-unneeded "$S/usr/lib/$MA/gtklock/universe-knoppen-module.so"
printf 'Universe OS gtklock-module. GPL-3+ (patroon gtklock-powerbar-module, Jovan Lanik); gtklock-module.h: MIT.\n' \
    >"$S/usr/share/doc/universe-os-vergrendelknoppen/copyright"
cat >"$S/DEBIAN/control" <<C
Package: universe-os-vergrendelknoppen
Version: $VERSION
Architecture: $ARCH
Maintainer: Universe OS
Depends: gtklock (>= 4), gtklock (<< 5), libgtk-3-0t64
Section: x11
Priority: optional
Description: Universe OS: knoppen Andere gebruiker en Afmelden op het vergrendelscherm
C
mkdir -p "$ROOT/uitvoer"
dpkg-deb --root-owner-group --build "$S" "$ROOT/uitvoer/universe-os-vergrendelknoppen_${VERSION}_${ARCH}.deb"
