# Overdracht spoor A: Claude → ChatGPT (4 oktober 2026)

Claude stopt tijdelijk (gebruikslimiet). ChatGPT neemt spoor A erbij. Lees dit samen met `ROADMAP.md`.

## Belangrijk: wie kan wat
- **ChatGPT heeft geen toegang tot Axels laptop of de VM's.** Alles wat in de bouw-VM moet gebeuren, voert **Axel** uit.
  ChatGPT schrijft de code en geeft Axel exacte opdrachten (kort, één voor één, met wat hij moet terugmelden).
- Wachtwoorden en sleutels staan **niet** in de repo, alleen op de laptop: `D:\UniverseOS-VMs\` (wachtwoord van de
  bouw-VM in `bouw-vm-wachtwoord.txt`, SSH-sleutel in `keys\`). Vraag Axel nooit om ze in GitHub te plakken.

## Stand spoor A
| Taak | Status | Opmerking |
|---|---|---|
| A1 deb bouwen (`scripts/build-deb.sh`) | ✅ | Getest, zie `docs/tests/A1-A3-deb-pakket.md` |
| A2 `DEBIAN/control` | ✅ | Alle afhankelijkheden bestaan in Debian 13 |
| A3 `DEBIAN/postinst` | 🧪 | Fix voor dubbele `HOME_MODE` nog niet hertest |
| A4 Wayland-sessies | 🧪 | `usr/share/wayland-sessions/universe*.desktop` |
| A5–A8 live-build, pakketlijsten, Wine32-hook, Calamares, LightDM | 🧪 | `live/`, nooit gebouwd |
| A9 ISO bouwen (`scripts/build-iso.sh`) | 🚧 | Volgende stap, nog nooit gedraaid |
| A10–A22 | ⬜ | Zie roadmap |

## De bouw-VM (op Axels laptop)
- QEMU 11.1 met WHPX, Debian 13.7, map `D:\UniverseOS-VMs\`, schijf `bouw-vm.qcow2`.
- Starten: `vm\start-bouw-vm.ps1` in PowerShell (opent een venster). Gebruiker `bouwer`.
- SSH vanaf Windows: `ssh -p 2222 -i D:\UniverseOS-VMs\keys\id_ed25519 bouwer@127.0.0.1`
- Beheerkanaal QMP op `127.0.0.1:4444` (`node vm\qmp.mjs 4444 status|scherm|typ|toets`). Let op: QMP accepteert één
  verbinding tegelijk. Een vastgelopen `node qmp.mjs`-proces blokkeert het; stop zo'n proces eerst.

### Waarom de VM "niks deed" (opgelost)
- Bij het opstarten vraagt cloud-init zijn instellingen op bij een kleine webserver op de host (`vm\seed-server.mjs`,
  poort 8123). Draait die niet, dan blijft het opstarten minutenlang hangen vóór het inlogscherm.
- **Oplossing (in deze commit):** `start-bouw-vm.ps1` start de seed-server nu bij elke start. Getest: met de server
  verscheen `universe-bouw login:`.

### Waarom SSH niet werkt (nog open)
- Claude installeerde het `universe-os`-pakket als test in de bouw-VM. De `postinst` zet de firewall (ufw) aan:
  inkomend dicht. Daardoor blokkeert ufw ook SSH (`[UFW BLOCK] ... DPT=22` in `D:\UniverseOS-VMs\bouw-vm-serial.log`).
- **Oplossing, door Axel in het VM-venster:** inloggen als `bouwer` en daarna typen:
  `sudo ufw allow 22/tcp`
- Les: installeer `universe-os` nooit in de bouw-VM. Test het pakket in het live-ISO of in een aparte test-VM.

## Volgende stappen (in volgorde)
1. Axel: firewall openzetten (zie hierboven), daarna controleren met de SSH-opdracht.
2. Project in de VM zetten: in de VM `git clone https://github.com/ItsAMeFork/universe-os.git` (later `git pull`).
3. Extra bouwpakket: `sudo apt-get install -y librsvg2-bin` (voor de afbeeldingen van de installer).
4. ISO bouwen: `cd ~/universe-os && sh scripts/build-iso.sh` (30–60 minuten). Logboeken: `uitvoer/logs/<datum>/`.
   Verwachte risico's bij de eerste build, om te controleren in `lb-build.log`:
   - hook `0100-wine.hook.chroot`: `wine32:i386` vereist `dpkg --add-architecture i386` plus `apt-get update` in de chroot;
   - hook `0200`: `apt-get download grub-efi-amd64 grub-efi-amd64-unsigned` (pakketnamen in trixie controleren);
   - pakketnamen in `live/config/package-lists/*.list.chroot` (bijv. `manpages-nl`, `power-profiles-daemon`);
   - Calamares-branding verwijst naar `logo.png`/`welcome.png`; `build-iso.sh` maakt die met `rsvg-convert`.
5. ISO naar Windows halen (A10), test-VM maken (A11): UEFI met `C:\Program Files\qemu\share\edk2-x86_64-code.fd`,
   lege qcow2 van 40 GB, aparte QMP-poort (bijv. 4445), `-device usb-tablet` voor muisklikken via QMP.
6. Test M1 (A12): live opstarten → installeren met Calamares → herstarten zonder ISO → verslag `docs/tests/M1.md`.

## Open punten voor spoor B (al gemeld)
- B4 `universe-install`: Calamares als root starten met de Wayland-omgeving van de live-gebruiker, bijv.
  `sudo --preserve-env=WAYLAND_DISPLAY,XDG_RUNTIME_DIR,LANG,LANGUAGE QT_QPA_PLATFORM=wayland calamares`.
- B11/B12 (snelkoppelingen Windows-programma's, groep in de ruimtewereld): **niet nodig om het ISO te bouwen**, wel voor test A20.
- PR #2 kan dicht (inhoud zit in PR #3). PR #3 (B10) is door Claude gelezen en goedgekeurd op inhoud; Axel beslist over samenvoegen.

## Afspraken die blijven gelden
- Geen Space Chat en geen bestaande Matrix-server gebruiken of noemen.
- Niets op ✅ zonder testverslag in `docs/tests/`. Geen nepknoppen of gesimuleerde functies.
- Linux-bestanden met LF (staat in `.gitattributes`).
