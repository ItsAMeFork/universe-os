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

## Eigen indeling: alles verplaatsbaar en optioneel (10 oktober, zelfde test-VM)

Wens van Axel: "alles moet net zo als een normaal bureaublad: zelf toevoegen, slepen, verplaatsen; alles optioneel".
Per gebruiker in `~/.config/universe-os/layout.json` (gecontroleerd in `config.py`), wijzigingen gaan naar wereld en dock.

| Test (echte WebKit tenzij anders vermeld) | Uitkomst |
|---|---|
| Planeet slepen (Gamehal naar rechtsonder) | ✅ staat er, opgeslagen (x 88,54 / y 59,26), blijft staan na shellherstart |
| Klik zonder slepen | ✅ opent de planeet zoals altijd |
| Rechtsklik op de lege ruimte | ✅ Programma/Map/Bestand toevoegen, Mappenbaan verbergen, Indeling herstellen |
| Programma toevoegen | ✅ kiezer met alle programma's; item met echt pictogram op de plek van de rechtsklik, melding boven het dock |
| Rechtsklik op dockknop → Uit het dock halen | ✅ menu boven het dock (laag groeit tijdelijk), dock krimpt en centreert, opgeslagen |
| Planeet verbergen / terugzetten, map of bestand toevoegen, item slepen en verwijderen, dock herschikken | ✅ in Chromium-preview; in de VM nog niet allemaal apart nagelopen |
| Controle van de opslag | ✅ onveilige naam (`../x`), relatief pad en `app:evil;rm` geweigerd, dubbele dockknop één keer, coördinaten begrensd |

Gevonden en opgelost tijdens het testen:
- Slepen werkte niet in WebKit: het begon een tekstselectie en hield de muis daarvoor vast → de wereld is niet meer
  selecteerbaar (`user-select:none`, geen beeldsleep); bewegingen worden op de hele pagina gevolgd (pointer capture
  houdt in WebKitGTK de muis niet vast).
- `vm/qmp.mjs klik` drukte op de oude muispositie (bewegen en drukken in één keer) → eerst bewegen, dan drukken.
  Nieuw: `beweeg` en `sleep`.

Niet getest: toetsenbord (Menu-toets/Shift+F10, Alt+pijlen) in de VM, zoom/tekstgrootte, twee schermen, leeg dock
(verdwijnt dan), map/bestand-kiezer (zenity) in de VM.

## Bureaublad zoals Windows met de ruimte als achtergrond (10 oktober, zelfde test-VM, echte WebKit)

Wens van Axel: "de ruimte net als een normaal bureaublad, de planeten als achtergrond (soort 3D), normale
bureaubladpictogrammen en een menu zoals Windows, in de stijl van de foto's".

| Test | Uitkomst |
|---|---|
| Achtergrond | ✅ aarde (480 px intern) met oranje baan, planeten op verschillende diepten, nevel; niet aanklikbaar |
| Pictogrammen | ✅ raster linksboven met echte themapictogrammen: Persoonlijke map, Prullenbak, inhoud van `~/Bureaublad` (Notities.txt, Projecten), eigen snelkoppeling (Software) |
| Dubbelklik op Notities.txt | ✅ opent in Mousepad |
| Rechtsklik op het bureaublad | ✅ Nieuwe map, Programma op het bureaublad, Snelkoppeling naar map/bestand, Pictogrammen schikken, Op de taakbalk zetten, Bureaubladmap openen, Persoonlijke instellingen |
| Startmenu (`universe-ctl start`, = Windows-toets) | ✅ zoekveld, Vastgemaakt (10 echte programma's), Alle apps, Snel naar, account, Instellingen, aan/uit |
| Zoeken "reken" + Enter | ✅ Rekenmachine start; open venster verschijnt rechts in de taakbalk |
| Controle van de opslag | ✅ foute posities, onbekende verborgen pictogrammen, `rm -rf` in Start en dubbele items geweigerd |

Gevonden en opgelost: startmenu onzichtbaar (`100vh` = hoogte van de smalle laag → hoogte uit `screen.height`);
`present()` op de laag maakte het groeien ongedaan (weggehaald). Sneltoetsen: Windows = startmenu,
Windows+Tab = taakweergave (geldt na opnieuw aanmelden, nog niet in de VM getest).

Niet getest in de VM: pictogram slepen naar een rastervak, naam wijzigen (F2), naar prullenbak (Delete), Nieuwe map,
aan/uit-menu, pictogrammen vastmaken/losmaken in Start, de Windows-toets zelf, 1024×768/4K, zoom.

### Vervolg bureaublad (10 oktober, test-VM)

| Test | Uitkomst |
|---|---|
| Pictogram slepen (Projecten) | ✅ klikt vast in vak [4,5], opgeslagen |
| F2 → "Werk" | ✅ map hernoemd op schijf, plek behouden |
| Hernoemen en daarna Delete | ✅ naar de prullenbak (`~/.local/share/Trash`), prullenbakpictogram wordt "vol" |
| Rechtsklik → Nieuwe map → "Vakantie" | ✅ op de plek van de rechtsklik ([6,3]), naam meteen in te typen |
| Startmenu: aan/uit-knop | ✅ Vergrendelen, Afmelden, Opnieuw opstarten, Afsluiten (niet uitgevoerd) |
| Klik op het bureaublad sluit Start | ✅ |
| Startmenu na shellstart | ✅ direct (wordt 5 s na het bureaublad op de achtergrond geladen) |
| CPU in rust | wereld ~28 % van één kern (oud ~42 %), taakbalk/start 0 % |

Gevonden en opgelost:
- Naamveld van een nieuwe map verdween: de mapbewaking ververste het bureaublad tijdens het typen → geen verversing
  zolang een naam wordt getypt; na hernoemen blijft het pictogram geselecteerd (Delete werkt meteen).
- `Gio.DesktopAppInfo.new` gooit in deze PyGObject `TypeError` bij een onbekend id → vensterlijst brak bij
  gnome-calculator. Nu overal via `backend.desktop_app()` (ook Chrome-status, starten, snelkoppelingen).
- Startmenu in de groeiende taakbalklaag werd soms niet mee vergroot → eigen laag met vaste grootte (`start.html`).

Windows-toets (na het opnieuw genereren van rc.xml + labwc --reconfigure): ✅ opent en sluit het startmenu.
Nog open: wereldpagina laadde één keer pas na 42 s (VM druk, 488 MB geheugen voor de wereld);
1024×768/4K.
