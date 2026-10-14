# Test zwart scherm, vangnet en vensteroverzicht (8 oktober 2026)

**Systeem:** test-VM, ISO 0.2.3 geïnstalleerd met Calamares (lege schijf), daarna pakket 0.2.5 (commit 9eadb98 + PR #33)
erover geïnstalleerd met `apt-get install ./universe-os_0.2.5_all.deb`, ingelogd via het inlogscherm als nieuwe gebruiker.

| Test | Uitkomst |
|---|---|
| 0.2.3: installeren, herstarten zonder ISO, inloggen | ✅ ruimtewereld binnen 10 s (zwart scherm niet na te bootsen) |
| 0.2.5: inloggen | ✅ ruimtewereld na 4,4 s (later 1,9 s), geen valse foutmelding |
| Vensteroverzicht (Windows-toets) met een open venster | ✅ "Geopende programma's (1)"; vóór 0.2.5 in elke versie kapot (`No module named pywayland._ffi`, oorzaak: `python3-cffi-backend` ontbrak) |
| world.js kapot gemaakt met de fout uit 0.2.0, shell herstart | ✅ melding "De ruimtewereld kon niet laden" + Opnieuw proberen/Afmelden; paneel en vensters blijven werken |
| Logboek bij die fout | ✅ `world.js:13: CONSOLE JS ERROR SyntaxError: Unexpected token ')'` en `UI world: …` in `shell.log` |
| world.js hersteld, shell herstart | ✅ ruimtewereld terug |

Niet getest op Axels echte pc (andere GPU); daar blijft een eventuele fout nu zichtbaar en staat de oorzaak in
`~/.local/state/universe-os/shell.log`.
