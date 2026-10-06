#!/bin/sh
# Maakt de sleutel waarmee Universe OS-updates worden ondertekend. Draai dit ZELF (Axel), één keer, op Windows in
# Git Bash, met de sleutel-USB-stick erin (NIET de stick voor het ISO: die wordt bij het schrijven gewist):
#   sh scripts/maak-updatesleutel.sh E          (E = stationsletter van de USB-stick)
# gpg vraagt twee keer om een wachtwoordzin. Kies een lange en bewaar die apart (niet op de stick).
# Resultaat op de stick, map universe-os-updatesleutel\:
#   gnupg\                  hoofdsleutel (geheim, blijft ALLEEN op de stick)
#   intrekking.asc          om de sleutel ongeldig te maken als hij ooit lekt
#   ondertekensleutel.asc   alleen de ondertekensubsleutel (2 jaar geldig) voor de bouw-VM
# In het project: scripts/apt/universe-os-updates.asc (publiek, mag in git).
set -eu
[ $# -eq 1 ] || { echo "Gebruik: sh scripts/maak-updatesleutel.sh <stationsletter van de USB-stick>" >&2; exit 2; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
STICK="/$(echo "$1" | tr 'A-Z' 'a-z' | tr -d ':')"
[ -d "$STICK" ] || { echo "Station $1 niet gevonden." >&2; exit 1; }
DIR="$STICK/universe-os-updatesleutel"
[ -e "$DIR" ] && { echo "$DIR bestaat al; er wordt niets overschreven." >&2; exit 1; }
mkdir -p "$DIR/gnupg"
chmod 700 "$DIR/gnupg"
export GNUPGHOME="$DIR/gnupg"
# Zonder venster: UNIVERSE_SLEUTEL_WACHTWOORDBESTAND=<bestand met de wachtwoordzin> (komt niet in de procesregel).
PW=${UNIVERSE_SLEUTEL_WACHTWOORDBESTAND:-}
G="gpg --batch"
[ -n "$PW" ] && G="gpg --batch --pinentry-mode loopback --passphrase-file $PW"

# Hoofdsleutel: alleen certificeren (subsleutels maken/verlengen), 10 jaar. Ondertekenen: subsleutel, 2 jaar.
$G --quick-generate-key "Universe OS updates" ed25519 cert 10y
FPR=$(gpg --list-keys --with-colons "Universe OS updates" | awk -F: '/^fpr/{print $10; exit}')
$G --quick-add-key "$FPR" ed25519 sign 2y

gpg --armor --export "$FPR" >"$ROOT/scripts/apt/universe-os-updates.asc"
$G --armor --export-secret-subkeys "$(gpg --list-keys --with-colons "$FPR" | awk -F: '/^fpr/{n++} n==2&&/^fpr/{print $10"!"; exit}')" >"$DIR/ondertekensleutel.asc"
# gpg maakt zelf een intrekkingscertificaat; vóór gebruik de dubbele punt aan het begin van de sleutelregel weghalen.
cp "$GNUPGHOME/openpgp-revocs.d/$FPR.rev" "$DIR/intrekking.asc"
echo "$FPR" >"$ROOT/scripts/apt/vingerafdruk"

echo
echo "Klaar. Vingerafdruk: $FPR"
echo "Op de stick: $DIR"
echo "Publieke sleutel in het project: scripts/apt/universe-os-updates.asc (commit die)."
echo "Maak nu een kopie van de map $DIR op een tweede stick en berg beide op."
