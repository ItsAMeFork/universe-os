# Test thuisplaneet als aarde met mappenbaan (10 oktober 2026)

**Systeem:** test-VM (geïnstalleerd systeem, 2 CPU's, 4 GB, geen GPU, 1920×1080), pakket 0.2.6 uit commit a40f5ef,
daarna de verbeterde `globe.js`/`world.js`/`world.css` uit deze commit rechtstreeks in `/usr/share/universe-os/ui`.
Ingelogd als `tester` via het inlogscherm, echte WebKit. Eerst ook getest in Chromium met een nagebootste shell
(1920×1080 en 1024×768).

| Test | Uitkomst |
|---|---|
| Eerste versie (aarde in één keer na `setTimeout`-ketting) | ❌ wereld pas na **186 s** zichtbaar, "Geen gereedmelding binnen 30 seconden"; zonder aarde (`world.json` met `"style":"plain"`) wel direct |
| Verbeterd: aarde pas na gereedmelding, getekend in stukjes per beeld (`requestAnimationFrame`, ~6 ms), max. 320 px | ✅ wereld binnen 5 s met gewone bol + baan, aarde na ~30 s ingetekend; twee keer herladen zonder gereedmelding-fout |
| Mappenbaan draait (Documenten, Downloads, Afbeeldingen, Muziek, Video's), voor/achter de planeet | ✅ |
| Klik op een bewegende map | ❌ eerst gemist (map verschuift ~25 px/s) → baan staat nu stil bij hover/toetsenbordfocus op een map |
| Hover op Afbeeldingen, dan klikken | ✅ baan stil, Thunar opent `/home/tester/Afbeeldingen` (~15 s in de trage VM) |
| CPU webproces (één kern, 20 s gemeten) | zonder baan ~42 %, met baan ~57 %. Eerste versie (30 stappen/s + CSS-filters): +30 %; nu 12 stappen/s zonder filters: +15 % |
| Scherm vergrendeld (na 10 min) | ✅ 0 % CPU |
| Stilstand bij verminderde animaties | ✅ (Chromium-preview) |

**Gevonden, los van deze wijziging:** met Thunar open pauzeren de wereld (zwevende planeten én baan) **niet**.
`shell.log` toont een pywayland-fout in de vensterbewaking (`toplevels.py`): `RuntimeError: Cannot find display` in
`c_to_arguments`. Daardoor komt `background-busy` waarschijnlijk nooit door. Vensteroverzicht via QMP-Windows-toets
ging niet open, dus nog niet vastgesteld of het overzicht zelf ook kapot is. Apart uitzoeken.

**Test-VM** heeft vanaf nu ontwikkeltoegang (alleen de VM, niet in pakket/ISO): SSH op 127.0.0.1:2223 met de sleutel
uit `D:\UniverseOS-VMs\keys`, sudo zonder wachtwoord, tty2 automatisch ingelogd, wachtwoord `tester`.
Niet getest: echte pc van Axel, 4K, nieuwe ISO.
