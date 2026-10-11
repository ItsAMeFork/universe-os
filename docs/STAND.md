# Stand van Universe OS (10 oktober 2026, Claude spoor A)

Werkbranch: `spoor-a/A23-echte-computer` (main loopt achter; PR #11 was de laatste samenvoeging naar main).

## 11 oktober: Claude in Universe OS, fase 1 (ontwerp: `docs/CLAUDE-IN-UNIVERSE.md`)
| Wat | Waar | Test |
|---|---|---|
| Claude-paneel (Windows+C of klik op personage): echte terminal met de ongewijzigde Claude Code, Haiku, `--continue` | `shell/claude_ui.py`, `bin/universe-claude` | VM met nep-`claude` (`~/.local/bin/claude` van tester) |
| Tijdelijk personage (planeetje met ring, Cairo, geen WebKit): denken, werken, toestemming, blij; loopt naar taakbalk/wereld/paneel | `shell/claude_ui.py` (Buddy), instelling `buddy` | VM: alle seintjes via de hook gezien |
| OS-hulpmiddelen + tweede brein (SQLite FTS5) als MCP-server | `lib/universe-os/claude/universe_mcp.py`, `brein.py` | VM: JSON-RPC, alle soorten aanroepen |
| Hooks -> `universe-ctl claude-event`; `universe-ctl call` met vaste toegestane lijst | `claude/universe-claude-hook`, `universe_shell.py` (CLAUDE_CALLS) | VM |
Nog niet getest: met de echte Claude Code (moet in de VM geïnstalleerd en ingelogd worden), typen in het paneel,
installatieknop in het Controlecentrum (nog niet gebouwd). Pakket niet opnieuw gebouwd: VM heeft losse bestanden.

## Later op 10 oktober: inloggen, afmelden en vergrendelen met animaties (t/m 78b70dd)
| Wat | Waar | Test |
|---|---|---|
| Inlog- en vergrendelscherm: de aarde in de ruimte (zelfde camera als het 3D-bureaublad) | `ui/login.*`, `ui/space.js`, `scripts/assets/vergrendeld.png` (gemaakt met `maak-vergrendeld.html`) | VM (vergrendelplaatje, inlogscherm) |
| Aarde als kant-en-klaar plaatje | `ui/earth.png` (720 px, earthNow) | VM |
| Inlogscherm: planeet vormt zich; bij inloggen opladen + ontploffen | `ui/explode.js` | preview; **Axel test in de VM** |
| Bureaublad: na inloggen/ontgrendelen spiralen planeten uit de aarde; afmelden/vergrendelen het omgekeerde | `ui/world.js` (animateWorld, intro.claim) | preview; **Axel test in de VM** |
| Vergrendelen met animatie: `universe-lock` -> `universe-ctl lock`, shell bewaakt swaylock en speelt uitloop; slaapstand `--direct` | `bin/universe-lock`, `universe-idle`, `universe_shell.py` | nog niet in VM gezien |
Axel vond de eerste versie van de animaties "niet goed genoeg"; deze versie is veel rijker, zijn oordeel volgt nog.
Open: zwart moment tussen ontploffing en bureaublad (sessiestart), animaties op echte pc bekijken, pakket opnieuw bouwen
(VM heeft losse bestanden over pakket 0.2.6 heen), alleen Full HD testen (4K liet de VM vastlopen).

## Nieuw op 10 oktober: bureaublad zoals Windows (concept van Axel)
Concept: foto's in `C:\Users\Axel Van Lienen\Downloads\foto`. Wens: "een normaal bureaublad, de planeten als
achtergrond (3D), pictogrammen en een menu zoals Windows, in de stijl van de foto's; alles optioneel".
| Wat | Waar | Test |
|---|---|---|
| **3D-bureaublad** (later die avond, vervangt achtergrond + pictogrammenraster): elk programma een planeet, aarde = Persoonlijke map, mappen/bestanden in een baan; wiel = zoom, slepen = schuiven, rechts slepen = draaien, object slepen = verplaatsen; 0 % CPU in rust | `ui/world.js`, `layout.json` (space) | VM |
| Bureaubladpictogrammen: Persoonlijke map, Prullenbak, `~/Bureaublad`, snelkoppelingen; slepen in raster, F2, Delete, Nieuwe map, rechtsklikmenu's | `ui/world.js`, `backend.desktop_*` | VM |
| Taakbalk (eigen lijst, verslepen, open vensters) | `ui/dock.*`, laag `dock` | VM |
| Startmenu (zoeken, vastgemaakt, alle apps, aan/uit), Windows-toets; Windows+Tab = taakweergave | `ui/start.*`, laag `start`, `shortcuts.json` | VM |
| Indeling per gebruiker | `~/.config/universe-os/layout.json` (`config.layout`) | VM |
| Fix vensterbewaking (registry bewaren) en veilige `desktop_app()` | `toplevels.py`, `backend.py` | VM |
Testverslag: `docs/tests/aarde-mappenbaan.md`. Pakket 0.2.6 uit commit 837c3f4 gebouwd en in de test-VM geïnstalleerd
(versienummer niet verhoogd; publiceren alleen als Axel het zegt).
Test-VM: ontwikkeltoegang (SSH 127.0.0.1:2223, sudo zonder wachtwoord), gebruiker `tester` / wachtwoord `tester`.
Nog open: wereldpagina soms traag in de VM (één keer 42 s), 1024×768/4K, twee schermen, ruimtestation/sterrenstelsel uit
het concept (eventueel als achtergrond of onderdelen van het startmenu).

## Klaar en getest (tot 9 oktober)
| Wat | Versie | Test |
|---|---|---|
| Zwart scherm 0.2.0 (één `)` te veel in world.js) | 0.2.1 | VM |
| Vangnet: melding "De ruimtewereld kon niet laden" + Opnieuw proberen/Afmelden, fouten in `shell.log` (PR #33 B, wachttijd 30 s) | 0.2.5 | VM, echte WebKit: `docs/tests/zwart-scherm-0.2.5.md` |
| Vensteroverzicht werkte nooit: `python3-cffi-backend` ontbrak | 0.2.5 | VM |
| Internet-planeet met browserkeuze, geen programmabalk (PR #31 B) | 0.2.2 | VM |
| Installer: vinkje automatisch aanmelden verborgen (`branding/universe/stylesheet.qss`) | ISO 0.2.5+ | nog niet in een ISO bekeken |
| Verplichte updates: `universe-updates.service` (timer, inloggen, knop), polkit zonder wachtwoord, alleen stable (PR #35 B = knop) | 0.2.6 | VM: `docs/tests/verplichte-updates-0.2.6.md` |
| `build-deb.sh` controleert Python + JS (node staat in de bouw-VM) | — | — |
| `vm/sync-naar-vm.ps1` maakt mappen eerst leeg (verwijderde bestanden bleven in de VM) | — | — |

## Bestanden en plekken
- ISO's: `D:\UniverseOS-VMs\iso\` — nieuwste **universe-os-0.2.6-amd64.iso** (SHA-256 `87026f3c…acdc150`), nog niet door Axel getest.
- Updatebron: https://itsamefork.github.io/universe-os-apt/ — online **0.2.4** (stable + test). 0.2.5/0.2.6 **niet** gepubliceerd.
- Publiceren: snelkoppeling "Universe OS update publiceren" (`vm\publiceer-update.ps1`), wachtwoordzin uit `F:\sleutel universe os\wachtwoordzin.txt`.
- Updatesleutel (nieuw, 7 okt): `19FAEFC86A1F7E25C78408AA0189D5914EAE81F2`, map `F:\sleutel universe os` (ook kopiëren naar tweede stick). Computers met de oude sleutel (0.2.0 en ouder) krijgen geen updates.
- Test-VM: geïnstalleerd systeem, gebruiker `tester` (testwachtwoord alleen voor de VM).

## Afspraken
- ISO bouwen alleen als Axel het zegt of ChatGPT op GitHub "ja" geeft.
- ChatGPT (spoor B) volgt issue #1 en de commits; berichten daar plaatsen. Taken voor B: issue #32.
- Publiceren alleen als Axel het zegt.

## Open
1. Axel test ISO 0.2.6 op de echte pc (live, installeren, inloggen, Windows-toets, Controlecentrum > Updates).
2. 0.2.6 publiceren als update (na akkoord Axel); daarna een echte universe-os-update via de bron testen.
3. Oorzaak van het oorspronkelijke zwarte scherm op de echte pc: niet nagebootst; bij een fout nu melding + `shell.log`.
4. Chrome-beeldcorruptie: PR #34 (B) is een diagnosetool, nog niet samengevoegd; hardwaregegevens van Axel nodig.
5. PR #28 en #30 kunnen dicht (vervangen).
