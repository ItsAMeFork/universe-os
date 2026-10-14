# Verplichte updates: interface voor systeemtaak

Opdracht Axel: B maakt installerenknop en verwijdert testkanaalkeuze; A maakt installatie en dagelijks controleren bij aanmelden automatisch. Geen automatische reboot gevraagd.

- `updates.install` start dezelfde idempotente taak als de automatische logincontrole en geeft een statusobject terug. Niet alleen een softwarevenster openen. Handler in Controlecentrum én shell; niet blokkeren op GTK-thread.
- `updates.status` / `updates.refresh` / `updates.install`: `{state,count,checkedAt,rebootRequired,message,error}`. State: checking/downloading/installing/waiting/current/available/stale/error.
- Statuspolling iedere 5 seconden zolang kaart zichtbaar is. Knoppen uit tijdens actieve taak. Geen succesmelding vóór echt resultaat.
- A: stable-only bronbeleid; bestaande testbron migreren zonder downgrade; ondertekende Debian/Google/Universe-bronnen. Offline en pakketlocks herproberen. Per-systeem dagelijkse controle bij aanmelden, niet per open UI/venster. Beschikbare updates automatisch installeren, zonder afhankelijkheid van zichtbare kaart.

Lokale UI-test: `node docs/tests/updates-install-ui.cjs`. Echte systeemhandler ontbreekt nog in deze B-PR: onbekende opdracht levert zichtbare fout. Niet als werkende automatische installatie publiceren vóór A-integratie/native test.

Native tests: 4 gevonden updates→echte installatie→0; automatisch bij login zonder open Controlecentrum; gewone gebruiker; offline/weer online; PackageKit/APT-lock; twee gebruikers/kaarten zonder dubbele transactie; systeemupdate en rebootmelding; testkanaal niet zichtbaar en testbron weg.
