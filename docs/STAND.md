# Stand van Universe OS (9 oktober 2026, Claude spoor A)

Werkbranch: `spoor-a/A23-echte-computer` (main loopt achter; PR #11 was de laatste samenvoeging naar main).

## Klaar en getest
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
