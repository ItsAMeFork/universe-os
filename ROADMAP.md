# Universe OS — roadmap

Universe OS is een installeerbaar Linuxbesturingssysteem op basis van **Debian 13 (trixie), x86_64, UEFI**, met een
interactieve ruimtewereld als hoofdinterface (vormgeving en bediening uit Space Chat). Windows-programma's draaien
via **Wine**.

Deze roadmap verdeelt het werk over **twee AI-modellen** (spoor A en spoor B) die tegelijk werken. Lees eerst de
werkafspraken onderaan.

## Statuslegenda

| Teken | Betekenis |
|---|---|
| ✅ | Gebouwd **en getest** in een VM (testverslag in `docs/tests/`) |
| 🧪 | Code geschreven, **nog niet getest** |
| 🚧 | Bezig (naam van het spoor erachter) |
| ⬜ | Nog niet begonnen |
| ⛔ | Geblokkeerd (reden erbij) |

Iets staat pas op ✅ als het in de VM is gecontroleerd. "Geschreven" is niet "werkend".

---

## Huidige stand (4 oktober 2026)

| Onderdeel | Status | Waar |
|---|---|---|
| Bouw-VM Debian 13.7 in QEMU (WHPX), SSH op poort 2222 | ✅ | `vm/start-bouw-vm.ps1` |
| Centrale vormgeving en wereldindeling | 🧪 | `branding/universe.json` |
| Ruimtewereld (planeten, reizen, kamers, toetsenbord 1–6/pijlen/Esc) | 🧪 | `ui/world.*` |
| Overzicht + zoeken (Windows-toets) | 🧪 | `ui/overview.*` |
| Compact bedieningspaneel (tijd, netwerk, geluid, batterij, meldingen, aan/uit) | 🧪 | `ui/panel.*` |
| Shell met layer-shell-lagen + socket voor `universe-ctl` | 🧪 | `shell/universe_shell.py` |
| Vensterlijst / Windows+D via wlr-foreign-toplevel | 🧪 | `shell/toplevels.py` |
| Systeemfuncties (apps, bestanden, status, aan/uit) | 🧪 | `shell/backend.py` |
| labwc-configuratie + sneltoetsen uit instellingen | 🧪 | `shell/session.py`, `shortcuts.json` |
| Sessie, herstelmodus, supervisor, vergrendelen, schermafbeelding | 🧪 | `usr/bin/universe-*` |
| Accountbeheer via pkexec + polkit | 🧪 | `universe-admin-helper`, `nl.universeos.admin.policy` |
| Controlecentrum, Python-kant | 🧪 | `shell/control_center.py` |
| Wine-kern (omgeving per programma, 32/64/ARM-herkenning, logs, snelkoppelingen, verwijderen) | 🧪 | `shell/wine.py`, `usr/bin/universe-wine` |
| Beheerscherm Windows-programma's, Python-kant | 🧪 | `shell/windows_apps.py` |

Paden onder `pakket/universe-os/`: `ui/` = `usr/share/universe-os/ui/`, `shell/` = `usr/lib/universe-os/shell/`.

---

## Mijlpalen

### M1 — Eerste opstartbare versie (inloggen, ruimtewereld, bestanden, programma's)
Doel: ISO bouwt, live-sessie start in de ruimtewereld, installatie op een lege virtuele schijf, opstarten zonder ISO.

### M2 — Volledige basis
Controlecentrum compleet, accounts, taal/toetsenbord, updates, sneltoetsen, herstelroute, beveiliging.

### M3 — Windows-programma's (Wine)
.exe/.msi openen vanuit Thunar → bevestigen → installeren → starten vanuit de ruimtewereld → verwijderen.

### M4 — Oplevering
Tests op meerdere schermformaten, Nederlandse handleiding, licenties, SHA256, release op GitHub.

---

## Spoor A — Systeem, pakketten en bouw (Claude)

Eigenaar van: `live/`, `scripts/`, `vm/`, `pakket/universe-os/DEBIAN/`, `pakket/universe-os/etc/`, `docs/tests/`.

### M1
- ✅ **A1** `scripts/build-deb.sh`: bouwt `universe-os_<versie>_all.deb` met `dpkg-deb`; genereert de pywayland-bindingen
  (`python3 -m pywayland.scanner`) voor `wlr-foreign-toplevel-management-unstable-v1.xml` naar `shell/protocols/`
  (`__init__.py` meeleveren); kopieert `branding/universe.json` → `usr/share/universe-os/`.
- ✅ **A2** `DEBIAN/control` met `Depends` op: labwc, python3-gi, gir1.2-gtk-3.0, gir1.2-webkit2-4.1,
  gir1.2-gtklayershell-0.1, python3-pywayland, swaylock, swayidle, mako-notifier, wlr-randr, wlopm, grim, slurp,
  wl-clipboard, libnotify-bin, mate-polkit, xwayland, thunar, gvfs, udisks2, xfce4-terminal, zenity, fonts-noto-core.
- 🧪 **A3** `DEBIAN/postinst`: `dpkg-divert` van `/usr/share/applications/wine.desktop` (anders start .exe zonder
  bevestiging), `HOME_MODE 0700` in `/etc/login.defs`, `DIR_MODE=0700` in `/etc/adduser.conf`, ufw aanzetten
  (inkomend dicht), `update-desktop-database`.
- 🧪 **A4** Sessiebestanden: `usr/share/wayland-sessions/universe.desktop` en `universe-recovery.desktop`.
- 🧪 **A5** `live/`: live-build-config (`auto/config`): trixie, amd64, `iso-hybrid`, bootloaders `grub-efi`,
  `main contrib non-free non-free-firmware`, firmware, `--debian-installer none`. Bootparameters:
  `locales=nl_NL.UTF-8 keyboard-layouts=us keyboard-variants=intl timezone=Europe/Amsterdam`.
- 🧪 **A6** Pakketlijsten (`config/package-lists/*.list.chroot`): basis, desktop-apps (firefox-esr +
  firefox-esr-l10n-nl, mousepad, xfce4-terminal, file-roller, atril, celluloid, gnome-calculator,
  gnome-system-monitor), netwerk/geluid/bluetooth (network-manager-gnome, pipewire-audio, wireplumber, pavucontrol,
  blueman, wdisplays), software (gnome-software, packagekit, gdebi), taalpakketten, grub-efi-amd64-signed,
  shim-signed, efibootmgr, calamares, lightdm, lightdm-gtk-greeter, ufw.
- 🧪 **A7** LightDM: `user-session=universe`, gtk-greeter in Universe-kleuren, Nederlandse taal; live-account met
  automatische aanmelding **alleen in de live-sessie**.
- 🧪 **A8** Calamares (eigen config onder `includes.chroot_after_packages/etc/calamares/`): welkom, taal,
  toetsenbord (standaard us/intl, ook nl), tijdzone (voorstel Europe/Amsterdam, wijzigbaar), partitie
  (alleen "schijf wissen", expliciete bevestiging), gebruiker (sudo, geen autologin, geen rootwachtwoord), samenvatting.
  Bootloader offline (grub al in squashfs), live-pakketten verwijderen via `packages`.
- ✅ **A9** `scripts/build-iso.sh`: `lb clean && lb config && lb build`, logboek in `uitvoer/logs/`, pakketversies
  (`chroot.packages.live`) en `SHA256SUMS` naast het ISO. Verslag: `docs/tests/A9-iso-bouw.md`.
- ✅ **A10** `vm/sync-naar-vm.ps1` (project naar de bouw-VM) en `vm/haal-iso.ps1` (met SHA-256-controle).
- ✅ **A11** `vm/start-test-vm.ps1`: aparte VM, UEFI (OVMF uit QEMU), lege qcow2 van 40 GB, ISO gekoppeld of niet. Gebruik `-ZonderVenster` (het SDL-venster kan vastlopen).
- 🧪 **A12** Test M1: live opstarten, installeren, herstarten zonder ISO → `docs/tests/M1.md`. Werkt van begin tot eind, maar met twee handmatige omwegen; fixes zitten in de volgende bouw.

### M2
- ⬜ **A13** Firewall: ufw standaard inkomend geweigerd; controleren dat alleen benodigde diensten luisteren (`ss -tlnp`).
- ⬜ **A14** Herstel: GRUB-herstelmodus, sessie "Universe OS herstelmodus" op het inlogscherm testen.
- ⬜ **A15** Secure Boot met shim testen (OVMF secure-code + Microsoft-sleutels); uitkomst eerlijk vermelden.
- ⬜ **A16** Updates: officiële bronnen (trixie, trixie-updates, trixie-security) in het geïnstalleerde systeem; test bijwerken en de melding "herstart nodig".
- ⬜ **A17** Tests accounts: beheerder/standaard, sudo/polkit, `chmod 700` op persoonlijke mappen, geen toegang tot andermans bestanden.

### M3 (Wine-systeemkant)
- 🧪 **A18** Live-build hook `config/hooks/live/0100-wine32.hook.chroot`: `dpkg --add-architecture i386`,
  `apt-get update`, `apt-get install wine wine64 wine32:i386 msitools`. **Geen** `wine-binfmt` (dat zou .exe direct uitvoeren).
- ⬜ **A19** MIME: `universe-windows-installer.desktop` als standaard voor `application/x-ms-dos-executable`,
  `application/x-msdownload`, `application/vnd.microsoft.portable-executable`, `application/x-msi`, `application/x-ole-storage`
  in `/etc/xdg/mimeapps.list` (of `usr/share/applications/mimeapps.list`).
- ⬜ **A20** Tests Wine in de test-VM met 7-Zip `.exe` en `.msi` (LGPL): openen, installeren, starten vanuit de
  ruimtewereld, na herstart, verwijderen (met/zonder gegevens), andere gebruiker heeft geen toegang → `docs/tests/M3.md`.

### M4
- ⬜ **A21** Licenties: `docs/LICENTIES.md` (eigen code, Debian-pakketten, Wine), broncodeverwijzing.
- ⬜ **A22** Release: ISO + `SHA256SUMS` als GitHub Release (via `gh release create`), bouwlogboek erbij.

---

## Spoor B — Interface, shell en apps (ChatGPT)

Eigenaar van: `pakket/universe-os/usr/share/universe-os/ui/`, `pakket/universe-os/usr/lib/universe-os/shell/`,
`pakket/universe-os/usr/bin/`, `pakket/universe-os/usr/share/applications/`, `branding/`.

### M1
- ⬜ **B1** Shell starten in een echte labwc-sessie (in de live-ISO of de bouw-VM met labwc): fouten oplossen in
  `universe_shell.py`, `toplevels.py`, `webview.py`. Controleer: wereld op achtergrondlaag, paneel boven vensters,
  overzicht met toetsenbordfocus.
- ⬜ **B2** Windows-toets alleen (`Super_L` met `onRelease`), Windows+D (minimaliseren en terugzetten), Alt+Tab,
  Alt+F4 werkend in labwc 0.8.3.
- ⬜ **B3** `.desktop`-bestanden: Controlecentrum, Windows-programma's, installer (live).
- ⬜ **B4** `universe-install` (live: Calamares starten met de juiste Wayland-omgeving) en
  `universe-install-deb` (zenity + gdebi-gtk).
- ⬜ **B5** labwc-thema `usr/share/themes/Universe/openbox-3/themerc` in Universe-kleuren; `mako.conf`;
  GTK donker thema (`/etc/gtk-3.0/settings.ini`).

### M2
- ⬜ **B6** `ui/control.html` + `control.js`: alle pagina's uit `settings-index.js` (weergave/animaties/schaal,
  netwerk+wifi, geluid+microfoon, beeldschermen, bluetooth, taal+toetsenbord met **testveld voor tekens**, muis,
  datum/tijd, energie, accounts, sneltoetsen met conflictcontrole, updates, beveiliging, over).
- ⬜ **B7** Communicatie-planeet: toont geïnstalleerde chat-/mailprogramma's en meldt eerlijk dat er nog geen
  chatdienst gekoppeld is. **Geen** Space Chat en **geen** bestaande Matrix-server gebruiken of noemen: Universe OS
  staat daar los van.
- ⬜ **B8** Toegankelijkheid: zichtbare focus overal, animaties volledig/verminderd/uit, UI- en tekstschaal,
  schermformaten 1024×768 t/m 4K.
- ⬜ **B9** Nederlandse teksten nalopen; lijst van meegeleverde programma's zonder volledige Nederlandse vertaling.

### M3 (Wine-interface)
- ⬜ **B10** `ui/windows.html` + `windows.js`: bevestigingsscherm vóór uitvoeren (bestandsnaam, map, grootte,
  SHA-256, 32/64-bit, waarschuwing bij Downloads, "geen sandbox"), voortgang, lijst met status **installatie**
  (geslaagd/mislukt/geen snelkoppeling) los van status **werking** (niet getest/gestart/fout/werkt volgens gebruiker),
  starten, instellingen (omgeving, logboeken, winecfg, Wine Mono op verzoek), verwijderen met tweede bevestiging bij
  gegevens wissen.
- ⬜ **B11** `universe-windows-installer.desktop` (NoDisplay, MimeType, `Exec=universe-windows-apps --installeer %f`)
  en `universe-windows-apps.desktop`; launchers in `usr/bin/`.
- ⬜ **B12** Ruimtewereld: in het Applicaties-planeet een groep "Windows-programma's" (categorie `X-Universe-Windows`)
  en een tegel "Windows-programma's beheren"; `backend.py` uitbreiden (`windows`-vlag, hulpmiddel `windows-apps`).

### M4
- ⬜ **B13** Handleiding `docs/HANDLEIDING.md` (Nederlands): bouwen, testen in VM, USB schrijven, vormgeving en
  wereldindeling aanpassen, standaardprogramma's wijzigen.

---

## Afhankelijkheden tussen de sporen

```
A1 deb ──► A5–A9 ISO ──► A12 test M1 ──► A13–A17
B1–B5 ─────┘                   ▲
B6–B9 ─────────────────────────┘
A18–A19 (Wine systeem) + B10–B12 (Wine interface) ──► A20 test M3 ──► A21–A22 release
```

- Spoor B kan B1 testen zodra A1 een deb oplevert (installeerbaar in de bouw-VM met `labwc` + VNC/scherm).
- Spoor A heeft van spoor B alleen de bestandslijst nodig om het deb te bouwen; die staat vast in `pakket/`.

## Contract tussen interface en shell

De pagina's praten met Python via `call(cmd, args)` in `ui/api.js`. Een nieuwe opdracht toevoegen = beide kanten
aanpassen **in dezelfde commit**:

| Pagina | Python-handlers |
|---|---|
| `world`, `overview`, `panel` | `Shell.handlers()` in `universe_shell.py` |
| `control` | `handlers()` in `control_center.py` |
| `windows` | `WindowsApps.handlers()` in `windows_apps.py` |

Gebeurtenissen van Python naar pagina's: `emit(view, naam, data)` → `on(naam, fn)` in JavaScript.

---

## Werkafspraken voor de twee AI-modellen

**Wie:** spoor A = **Claude** (Claude Code, werkt ook in de bouw- en test-VM op de laptop). Spoor B = **ChatGPT**.
De eigenaar (Axel) beslist bij twijfel.

**Communiceren gaat via GitHub, op drie manieren:**
- **Roadmap:** zet je taak op 🚧 met je spoorletter vóór je begint, en op 🧪 of ✅ als je klaar bent. Push dat meteen.
- **Commitberichten** beginnen met de spoorletter en het taaknummer, bijv. `[A] A5: live-build-config` of
  `[B] B10: bevestigingsscherm Wine`. Vragen of waarschuwingen voor het andere spoor: een regel `Voor B: …` of
  `Voor A: …` in het commitbericht én een regel in de tabel Overdracht.
- **Overdracht-tabel** (onderaan): berichten, vragen en verzoeken om een bestand van het andere spoor te wijzigen.
  Wie het afhandelt, vult de kolom "Afgehandeld" in.
- Lees vóór elke sessie: `git pull`, de laatste commits (`git log --oneline -20`), deze roadmap en de Overdracht-tabel.
- Pushen mag direct naar `main` (of via een pull request), maar alleen bestanden van je eigen spoor, en altijd eerst
  `git pull --rebase` zodat je elkaars werk niet overschrijft.


1. **Eén spoor per model.** Werk alleen in de mappen van je eigen spoor. Moet je een bestand van het andere spoor
   wijzigen, schrijf het dan in "Overdracht" hieronder in plaats van het zelf te doen.
2. **Branches:** `spoor-a/<taak>` en `spoor-b/<taak>` (bijv. `spoor-a/A5-live-build`). Klein houden, één taak per
   branch, via een pull request naar `main`.
3. **Voor je begint:** `git pull`, zet de taak in deze roadmap op 🚧 met je spoor, commit dat meteen zodat het andere
   model het ziet.
4. **Klaar = getest.** Zet een taak alleen op ✅ met een testverslag in `docs/tests/` (wat, hoe, uitkomst, schermafbeelding
   of log). Anders 🧪.
5. **Niets verzinnen.** Geen nepknoppen of gesimuleerde systeemfuncties. Ontbreekt iets: meld het in de interface én hier.
6. **Geen geheimen in de repo.** Wachtwoorden, sleutels en tokens horen niet in bestanden of logs. VM-gegevens staan
   in `D:\UniverseOS-VMs\` buiten de repo.
7. **Taal:** alles wat de gebruiker ziet is Nederlands. Codecommentaar mag Engels.
8. **Regeleinden:** Linux-bestanden altijd LF (geregeld in `.gitattributes`).
9. **Bouwen gebeurt in de bouw-VM**, nooit op Windows zelf. Testen gebeurt in een aparte test-VM met een lege virtuele schijf.

## Overdracht (berichten tussen de sporen)

| Datum | Van → naar | Bericht | Afgehandeld |
|---|---|---|---|
| 2026-10-04 | — | Roadmap aangemaakt. | — |
| 2026-10-04 | A → B | Claude neemt spoor A en begint met A1 (deb-pakket). Spoor B kan beginnen met B10 (`ui/windows.html` + `ui/windows.js`): de Python-kant staat al in `shell/windows_apps.py` en `shell/wine.py` (opdrachten `wine.*`, zie `WindowsApps.handlers()`). Let op: geen Space Chat of bestaande Matrix-server gebruiken. | |
| 2026-10-04 | A → B | Claude is terug op spoor A. ISO-bouw van ChatGPT gecontroleerd: geslaagd, SHA-256 klopt (A9 ✅, `docs/tests/A9-iso-bouw.md`). Rechtenfout opgelost in `build-iso.sh`, uitvoerbare bestanden staan nu zo in git. Claude doet A10–A12 en test daarin de A7-login (PR #4) en B10 (PR #3). Nieuwe wens loginplaneet (implosie na geslaagde login, omgekeerd bij afmelden): de interface is spoor B, de systeemkant (greeter) stemmen we af. | |
| 2026-10-04 | A → B | M1 getest (`docs/tests/M1.md`): installeren, herstarten zonder ISO, login (fout wachtwoord en onbekend account geweigerd), afmelden werken. Voor B: scherm vergrendelt in de live-sessie tijdens installeren (swayidle); zoeken op "terminal" zet de instellingen boven het programma; Engelse Calamares-teksten (B9). | |
