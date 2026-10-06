#!/bin/sh
# Zet een gebouwd universe-os-pakket in de eigen updatebron (draai dit in de bouw-VM; zie docs/UPDATES-VOORSTEL.md).
#   sh scripts/publiceer-apt.sh test               nieuwste uitvoer/universe-os_*.deb naar het testkanaal
#   sh scripts/publiceer-apt.sh stable [VERSIE]    een versie die al in test staat door naar stable (standaard: de nieuwste)
#   ... --push                                     daarna ook echt publiceren (git push naar GitHub Pages)
# Zonder --push wordt alleen lokaal in ~/universe-os-apt bijgewerkt, zodat je eerst kunt kijken.
#
# Opbouw (apt-ftparchive, geen database): alle versies blijven in pool/, zodat terugdraaien via apt altijd kan
# (apt install universe-os=<oude versie>). kanalen/<kanaal>.lijst bepaalt welke versies een kanaal ziet.
# Ondertekenen met de ondertekensubsleutel in de gpg-sleutelbos van de bouw-VM; gpg vraagt de wachtwoordzin.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
REPO=${UNIVERSE_APT_REPO:-$HOME/universe-os-apt}
KANAAL=${1:-}
shift || true
VERSIE=
PUSH=
for a in "$@"; do case "$a" in --push) PUSH=1 ;; *) VERSIE=$a ;; esac; done
FPR=$(cat "$ROOT/scripts/apt/vingerafdruk" 2>/dev/null || true)
[ -n "$FPR" ] || { echo "Nog geen updatesleutel (scripts/apt/vingerafdruk ontbreekt)." >&2; exit 1; }
case "$KANAAL" in test|stable) ;; *) echo "Kanaal moet test of stable zijn." >&2; exit 2 ;; esac
command -v apt-ftparchive >/dev/null || { echo "apt-ftparchive ontbreekt: sudo apt-get install apt-utils" >&2; exit 1; }
[ -d "$REPO/.git" ] || { echo "$REPO is geen git-checkout van de updatebron (universe-os-apt)." >&2; exit 1; }
POOL=pool/main/u/universe-os
mkdir -p "$REPO/$POOL" "$REPO/kanalen"
touch "$REPO/kanalen/test.lijst" "$REPO/kanalen/stable.lijst"

if [ "$KANAAL" = test ]; then
    DEB=$(ls -1t "$ROOT"/uitvoer/universe-os_*_all.deb 2>/dev/null | head -1)
    [ -n "$DEB" ] || { echo "Geen pakket in uitvoer/. Eerst: sh scripts/build-deb.sh" >&2; exit 1; }
    NAAM=$(basename "$DEB")
    if [ -e "$REPO/$POOL/$NAAM" ] && ! cmp -s "$DEB" "$REPO/$POOL/$NAAM"; then
        echo "$NAAM staat al in de bron met een andere inhoud. Verhoog het versienummer (branding/universe.json)." >&2
        exit 1
    fi
    cp "$DEB" "$REPO/$POOL/$NAAM"
else
    if [ -z "$VERSIE" ]; then
        VERSIE=$(sed -n 's/^universe-os_\(.*\)_all\.deb$/\1/p' "$REPO/kanalen/test.lijst" | sort -V | tail -1)
    fi
    NAAM="universe-os_${VERSIE}_all.deb"
    grep -qx "$NAAM" "$REPO/kanalen/test.lijst" || { echo "Versie '$VERSIE' staat (nog) niet in test." >&2; exit 1; }
fi
grep -qx "$NAAM" "$REPO/kanalen/$KANAAL.lijst" || echo "$NAAM" >>"$REPO/kanalen/$KANAAL.lijst"

# Indexen en ondertekende Release per kanaal opnieuw maken.
for k in test stable; do
    T=$(mktemp -d)
    mkdir -p "$T/$POOL"
    while read -r f; do [ -n "$f" ] && ln -s "$REPO/$POOL/$f" "$T/$POOL/$f"; done <"$REPO/kanalen/$k.lijst"
    B="$REPO/dists/$k/main/binary-amd64"
    mkdir -p "$B"
    (cd "$T" && apt-ftparchive packages pool) >"$B/Packages"
    gzip -9nc "$B/Packages" >"$B/Packages.gz"
    rm -rf "$T"
    rm -f "$REPO/dists/$k/Release" "$REPO/dists/$k/InRelease" "$REPO/dists/$k/Release.gpg"
    apt-ftparchive -o APT::FTPArchive::Release::Origin="Universe OS" -o APT::FTPArchive::Release::Label="Universe OS" \
        -o APT::FTPArchive::Release::Suite="$k" -o APT::FTPArchive::Release::Codename="$k" \
        -o APT::FTPArchive::Release::Architectures=amd64 -o APT::FTPArchive::Release::Components=main \
        release "$REPO/dists/$k" >"$REPO/dists/$k/Release.tmp"
    mv "$REPO/dists/$k/Release.tmp" "$REPO/dists/$k/Release"
    gpg --batch --yes -u "$FPR" --clearsign -o "$REPO/dists/$k/InRelease" "$REPO/dists/$k/Release"
    gpg --batch --yes -u "$FPR" -abs -o "$REPO/dists/$k/Release.gpg" "$REPO/dists/$k/Release"
done
cp "$ROOT/scripts/apt/universe-os-updates.asc" "$REPO/universe-os-updates.asc"
touch "$REPO/.nojekyll"
echo "test:   $(tr '\n' ' ' <"$REPO/kanalen/test.lijst")"
echo "stable: $(tr '\n' ' ' <"$REPO/kanalen/stable.lijst")"

cd "$REPO"
git add -- pool dists kanalen universe-os-updates.asc .nojekyll
if git diff --cached --quiet; then
    echo "Geen wijzigingen."
else
    git commit -q -m "universe-os: $NAAM naar $KANAAL"
fi
if [ -n "$PUSH" ]; then
    echo "Publiceren naar $(git remote get-url origin) (tak $(git rev-parse --abbrev-ref HEAD))"
    git push -q origin HEAD
    echo "Gepubliceerd."
else
    echo "Lokaal bijgewerkt in $REPO. Publiceren: opnieuw met --push."
fi
