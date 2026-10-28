# UOS-ANIM-001 in de echte desktop van de test-VM (28 okt, Claude)

Na ChatGPT's reparaties en mijn review (commit 996d69c). Getest in de **echte Universe-sessie** (labwc + shell + WebKit),
niet in een los harnas: 1920x1080, virtio-vga zonder 3D, 2 vCPU, 4 GB. De shell zelf startte de scène vanuit een
geschreven updatestatus (`restartRequired` + `installedAt`, zoals `universe-updates-run` die schrijft), na de echte
120 s. Geluid opgenomen van de monitor van de geluidskaart van de VM (`pw-record`, stream.capture.sink). Beelden met
`grim` (halve grootte). Bewijs: `uitvoer/vm-test/anim-001-claude/` (niet in git).

| Test | Uitkomst |
|---|---|
| Normaal, geslaagde update | Scène 16 s, cijfers midden op de aarde, implosie, echte herstart (journal: `reboot.target`, `systemd-shutdown: Syncing`). Geluid: inslageffect, tik per seconde, afsluitgeluid. |
| Afmelden tijdens de aanloop (T≈3 s, via de assistent: tool `energie`, actie `afmelden`) | Afgemeld, **geen** herstart, effect stopt direct (stilte in de opname, geen `pw-play update-inslag` meer). |
| Mislukte update (`restartRequired` false) | Geen melding, geen scène, geen herstart. |
| Systeemgeluiden uit tijdens de scène (T≈5 s) | Effect stopt binnen 0,5 s; daarna ook geen tikken en geen afsluitgeluid; scène en herstart lopen door. |
| Lichte modus (`/etc/universe-os/grafisch-licht`) | Dezelfde elementen op dezelfde plekken als normaal (zie `normaal-vs-licht.png`), echte herstart. |
| Minder beweging (`animations: reduced`) | Stilstaande aarde + planeten, ring, cijfers, tekst; geen vlucht, flits of brokstukken (plan-afspraak r12). Herstart. |

Beeldsnelheid (tijdelijke meetregel in de VM-kopie van meteoriet.js, daarna weer verwijderd):

| Modus | beelden | tekentijd gem. | tussen beelden p50 / p95 / max |
|---|---|---|---|
| normaal | 50 | 14 ms | 317 / 788 / 1394 ms |
| licht | 101 | 5 ms | 149 / 346 / 785 ms |
| minder beweging | 96 | 1 ms | 145 / 367 / 739 ms |

Het JavaScript is niet de rem (tekentijd 1-14 ms); de tijd gaat naar WebKit/compositing zonder 3D in de VM
(virtio-vga zonder virgl, 2 vCPU). ChatGPT's harnasmeting via SSH (p95 313 ms, max 2440 ms, geen toegang tot
`/dev/dri/renderD128`) had bovendien geen zitplaats-ACL op de render node. Vloeiendheid is in deze VM niet te
beoordelen: dat moet op echte hardware (pc beneden / Jesse).

Gerepareerd in 996d69c t.o.v. ChatGPT's stand:
- `world.css` zette `translate:-50% -50%` bovenop `transform:translate(-50%,-50%)` uit meteoriet.js: cijfers en
  onderschriften in world.html dubbel verschoven, en andere lettermaten dan world-lite. Nu één bron (meteoriet.js).
- `universe-geluid --wacht`: `timeout` maakte een eigen procesgroep, waardoor `killpg` de speler miste en het
  effect na afbreken doorspeelde. Nu `timeout --foreground`.
- `world-lite.js` laadt meteoriet.js pas bij de aftelling (een kapotte scènemodule mag de noodbureaublad niet slopen).

Niet live getest: een tweede scherm dat tijdens de scène bijkomt (`sync_launch`; alleen de unittest), world-lite in
de echte sessie (alleen `anim-001-lite.cjs`), een echte update via de updatebron.

QEMU-pauze bij elke herstart: de gast sluit volledig af (tot `systemd-shutdown`), daarna gaat QEMU (WHPX) op
`paused` en stopt na `cont` binnen 7 ms opnieuw, zonder I/O-fout. Ligt aan QEMU/WHPX bij de reset, niet aan
Universe OS. Werkwijze: QMP `quit` en de VM opnieuw starten.
