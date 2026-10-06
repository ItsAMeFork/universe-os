#!/bin/sh
# Zet een gebouwd universe-os-pakket in de eigen updatebron (draai dit in de bouw-VM; zie docs/UPDATES-VOORSTEL.md).
#   sh scripts/publiceer-apt.sh test                 nieuwste uitvoer/universe-os_*.deb naar het testkanaal
#   sh scripts/publiceer-apt.sh stable               dezelfde versie uit test door naar stable (voor iedereen)
#   ... --push                                       daarna ook echt publiceren (git push naar GitHub Pages)
# Zonder --push wordt alleen lokaal in ~/universe-os-apt bijgewerkt, zodat je eerst kunt kijken.
# Ondertekenen gebeurt met de ondertekensubsleutel in de gpg-sleutelbos van de bouw-VM; gpg vraagt de wachtwoordzin.
# Dat is bewust: zonder Axel (wachtwoordzin) geen update. Draai het dus vanuit een eigen terminal (ssh -t).
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
REPO=${UNIVERSE_APT_REPO:-$HOME/universe-os-apt}
KANAAL=${1:-}
PUSH=${2:-}
FPR=$(cat "$ROOT/scripts/apt/vingerafdruk" 2>/dev/null || true)
[ -n "$FPR" ] || { echo "Nog geen updatesleutel (scripts/apt/vingerafdruk ontbreekt). Zie scripts/maak-updatesleutel.sh." >&2; exit 1; }
case "$KANAAL" in test|stable) ;; *) echo "Kanaal moet test of stable zijn." >&2; exit 2 ;; esac
command -v reprepro >/dev/null || { echo "reprepro ontbreekt: sudo apt-get install reprepro" >&2; exit 1; }
[ -d "$REPO/.git" ] || { echo "$REPO is geen git-checkout van de updatebron (universe-os-apt)." >&2; exit 1; }

mkdir -p "$REPO/conf"
sed "s/VINGERAFDRUK/$FPR/" "$ROOT/scripts/apt/distributions" >"$REPO/conf/distributions"
printf 'basedir %s\n' "$REPO" >"$REPO/conf/options"

if [ "$KANAAL" = test ]; then
    DEB=$(ls -1t "$ROOT"/uitvoer/universe-os_*_all.deb 2>/dev/null | head -1)
    [ -n "$DEB" ] || { echo "Geen pakket in uitvoer/. Eerst: sh scripts/build-deb.sh" >&2; exit 1; }
    reprepro -b "$REPO" includedeb test "$DEB"
else
    reprepro -b "$REPO" copy stable test universe-os
fi
# Publieke sleutel naast de bron, voor wie hem handmatig wil controleren.
cp "$ROOT/scripts/apt/universe-os-updates.asc" "$REPO/universe-os-updates.asc"
touch "$REPO/.nojekyll"
reprepro -b "$REPO" list "$KANAAL"

cd "$REPO"
git add -A
git commit -q -m "universe-os naar $KANAAL: $(reprepro -b "$REPO" list "$KANAAL" | awk '/universe-os /{print $3; exit}')" || true
if [ "$PUSH" = --push ]; then
    git push -q
    echo "Gepubliceerd naar $KANAAL."
else
    echo "Lokaal bijgewerkt in $REPO. Publiceren: opnieuw met --push."
fi
