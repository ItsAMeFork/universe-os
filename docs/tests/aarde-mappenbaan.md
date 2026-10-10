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

**Gevonden en opgelost (vensterbewaking):** met een venster open pauzeerde de wereld niet. Oorzaak in `toplevels.py`:
de Wayland-registry was een lokale variabele en werd na `start()` opgeruimd; pywayland vindt de verbinding voor elk
nieuw venster via die registry, dus vensters die na het starten van de shell openden gaven `RuntimeError: Cannot find
display` en kwamen nooit in de vensterlijst (overzicht, `background-busy`). Nu bewaard als `self.registry`.

| Test na de fix (shell herstart, daarna Thunar geopend) | Uitkomst |
|---|---|
| Wereld pauzeert met open venster | ✅ webproces 0 % CPU over 20 s, twee schermafbeeldingen identiek, venster zichtbaar (niet vergrendeld) |
| Venster sluiten | ✅ wereld beweegt weer (77 % CPU) |
| Nieuwe "Cannot find display" in `shell.log` | ✅ geen |
| Vensteroverzicht (Windows-toets) | niet getest (toets via QMP kwam niet door) |

**Test-VM** heeft vanaf nu ontwikkeltoegang (alleen de VM, niet in pakket/ISO): SSH op 127.0.0.1:2223 met de sleutel
uit `D:\UniverseOS-VMs\keys`, sudo zonder wachtwoord, tty2 automatisch ingelogd, wachtwoord `tester`.
Niet getest: echte pc van Axel, 4K, nieuwe ISO.

## Dock (10 oktober, zelfde test-VM)

Nieuwe shell-laag `dock` (TOP-laag onderaan, eigen ruimte via exclusive zone), pagina `ui/dock.html` + `ui/dock.js`.

| Test | Uitkomst |
|---|---|
| Na shellstart | ✅ dock op maat (6 knoppen) met echte pictogrammen: Ruimtewereld, Bestanden, Chrome (standaardbrowser), Terminal, Softwarewinkel, Controlecentrum; hint-tekst van de wereld staat erboven |
| Klik Bestanden | ✅ Thunar opent, oranje balkje onder Bestanden (actief), tooltip "Bestanden" |
| Klik Ruimtewereld | ✅ alle vensters geminimaliseerd, wereld zichtbaar, stip onder Bestanden blijft (open) |
| Klik Bestanden opnieuw | ✅ zelfde venster terug (geen tweede Thunar) |
| Venster maximaliseren | ✅ venster stopt boven het dock |

Niet getest: andere open programma's rechts van de scheidingslijn, Internet zonder standaardbrowser, tekstgrootte/zoom
anders dan 100 %, 1024×768 en 4K, twee schermen (het dock staat alleen op het hoofdscherm).
Bestaand, niet door het dock: het paneel bovenaan ligt over de titelbalk van een gemaximaliseerd venster.
