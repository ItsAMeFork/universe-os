#!/bin/sh
# Draait alle tests in docs/tests (*.py, *.cjs, *.mjs) vanuit de repo-root, elk met een limiet van 300 s.
#   docs/tests/alle-tests.sh          alle tests
#   docs/tests/alle-tests.sh --snel   ai-assistent-preview.py overslaan (headless browser)
# Logs per test komen in een tijdelijke map (blijft staan, het pad wordt getoond).
# Exitcode 0 als alles slaagt, 1 als er een test faalt, 2 bij een onbekende optie.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
TESTS="$ROOT/docs/tests"
TIJDLIMIET=300
SNEL=0

for arg in "$@"; do
    case "$arg" in
        --snel) SNEL=1 ;;
        -h|--help) sed -n '2,5p' "$0"; exit 0 ;;
        *) echo "Onbekende optie: $arg" >&2; echo "Gebruik: $0 [--snel]" >&2; exit 2 ;;
    esac
done

LOGMAP=$(mktemp -d "${TMPDIR:-/tmp}/universe-tests.XXXXXX")
echo "Tests draaien vanuit $ROOT"
echo "Logs: $LOGMAP"
echo

OK=0
FOUT=0
OVERGESLAGEN=0
FOUTEN=""

for pad in "$TESTS"/*.py "$TESTS"/*.cjs "$TESTS"/*.mjs; do
    [ -f "$pad" ] || continue
    naam=$(basename "$pad")

    if [ "$SNEL" = 1 ] && [ "$naam" = "ai-assistent-preview.py" ]; then
        echo "OVERGESLAGEN  $naam (--snel)"
        OVERGESLAGEN=$((OVERGESLAGEN + 1))
        continue
    fi

    case "$naam" in
        *.py) interpreter=python3 ;;
        *) interpreter=node ;;
    esac
    if ! command -v "$interpreter" >/dev/null 2>&1; then
        echo "FOUT          $naam ($interpreter ontbreekt)"
        FOUT=$((FOUT + 1))
        FOUTEN="$FOUTEN $naam"
        continue
    fi

    log="$LOGMAP/${naam}.log"
    start=$(date +%s)
    # Vanuit de repo-root, zoals de tests bedoeld zijn; de exitcode van timeout (124) betekent een time-out.
    (cd "$ROOT" && timeout "$TIJDLIMIET" "$interpreter" "$pad") >"$log" 2>&1
    code=$?
    duur=$(( $(date +%s) - start ))

    if [ "$code" = 0 ]; then
        echo "OK            $naam (${duur} s)"
        OK=$((OK + 1))
    else
        if [ "$code" = 124 ]; then
            reden="time-out na ${TIJDLIMIET} s"
        else
            reden="exitcode $code"
        fi
        echo "FOUT          $naam ($reden, log: $log)"
        FOUT=$((FOUT + 1))
        FOUTEN="$FOUTEN $naam"
    fi
done

echo
echo "Samenvatting: $OK OK, $FOUT FOUT, $OVERGESLAGEN overgeslagen"
if [ "$FOUT" -gt 0 ]; then
    echo "Gefaald:$FOUTEN"
    echo "Logs staan in $LOGMAP"
    exit 1
fi
if [ "$OK" = 0 ]; then
    echo "Geen tests gevonden in $TESTS" >&2
    exit 1
fi
exit 0
