# Plan gebruikersbeheer, inloggen en vensteranimaties (Jesse t153u, 26 okt 2026)

Bron: het plan van Jesse (samenvatting buiten git: uitvoer/plan-gebruikers-0.3.md). Uitgangspunt: verbeteren, niets slopen.

## 1. Huidige architectuur (geïnspecteerd)
| Onderdeel | Nu | Bestanden |
|---|---|---|
| Displaymanager | **LightDM** (seat: greeter-session=universe-greeter, user-session=universe, pam-service=lightdm, geen gast) | `usr/share/lightdm/lightdm.conf.d/60-universe.conf` |
| Inlogscherm | Eigen LightDM-greeter in Python/GTK3 + WebKit (`gi LightDM 1`): planeet-UI in HTML/JS, authenticatie uitsluitend via liblightdm/PAM (`authenticate`, `respond`, `start_session_sync`) | `shell/greeter.py`, `ui/login.html/.js/.css`, `ui/login-power.js` |
| Sessie | labwc + `universe-session` → autostart → `universe-shell-supervisor` → `universe_shell.py`; logind-sessie per gebruiker (LightDM opent hem via PAM/pam_systemd) | `usr/bin/universe-session`, `shell/session.py` |
| Vergrendelen | `universe-lock`: animatie, dan **gtklock** (ext-session-lock-v1, PAM `gtklock`), swaylock als terugval | `usr/bin/universe-lock`, `share/universe-os/gtklock/*` |
| Uitloggen | animatie in de shell (`begin_logout`/`finish_logout`), daarna labwc afsluiten | `universe_shell.py` |
| Accounts | Instellingen → Accounts (`control_center.users()`, `ui/accounts-ui.js`); beheer via `universe-admin-helper` + polkit-actie `nl.universeos.admin` (pkexec, auth_admin); admin = groep `sudo` | `shell/control_center.py`, `lib/universe-os/universe-admin-helper`, `polkit-1/actions/nl.universeos.admin.policy` |
| Instellingen | per gebruiker in `~/.config/universe-os` | `shell/config.py` |
| Vensteranimaties | 0.2.39: labwc windowRule Iconify + portaal (flits.py), meting met grim + mintrand, vensterwacht als veiligheidsnet | `shell/flits.py`, `venstermeting.py`, `vensterwacht.py` |

## 2. Haalbaarheid
**Werkt met de bestaande stack (LightDM + logind + PAM + polkit + labwc 0.8.3):**
- *Meerdere gelijktijdige sessies / fast user switching*: LightDM ondersteunt dit standaard per VT. `dm-tool switch-to-greeter` (of D-Bus `org.freedesktop.DisplayManager.Seat.SwitchToGreeter`) start de greeter op een nieuwe VT terwijl de huidige sessie blijft draaien. Kiest men in de greeter een gebruiker die al een sessie heeft, dan schakelt LightDM na geslaagde PAM-authenticatie naar die bestaande sessie (vensters intact). Geen andere displaymanager nodig: **greetd is niet nodig** en wordt niet geïnstalleerd.
- *Echte scheiding*: elke sessie is een eigen Unix-gebruiker, eigen logind-sessie, eigen VT, eigen Wayland-socket in `/run/user/<uid>` (0700). Een andere gebruiker kan er niet bij.
- *Vergrendeld houden bij wisselen*: vóór de switch eerst `universe-lock --direct` (gtklock via ext-session-lock), zodat terugschakelen via Ctrl+Alt+F-toets ook alleen een vergrendeld scherm laat zien. labwc 0.8.3 ondersteunt ext-session-lock-v1.
- *Echt uitloggen*: `loginctl terminate-session $XDG_SESSION_ID` (eigen sessie mag zonder polkit) beëindigt alle processen van de sessie; LightDM keert terug naar de greeter. Zonder `KillUserProcesses=yes` blijven `systemd --user`-diensten even leven; dat is acceptabel (geen toegang tot de sessie), optioneel `loginctl terminate-user` als er geen andere sessie van dezelfde gebruiker is.
- *Rechten*: admin = lid van `sudo` (bestaand). Beheer via pkexec/polkit `auth_admin` (wachtwoord van een admin). Normale gebruiker: eigen wachtwoord via `passwd` (PAM), eigen naam/planeet in de eigen home.
- *Gebruikersplaneten-rij*: puur greeter-UI (HTML/JS). Gebruikerslijst komt van liblightdm (`LightDM.UserList`), die AccountsService/`/etc/passwd` leest. Niet versleepbaar = geen drag-handlers, `user-select:none`, `draggable=false`, pointer-events alleen click/tap.
- *Gebruikerswissel-animaties*: in de greeter (selecteren, inloggen) en in de shell (vergrendelen/uitloggen) – bestaande animatiecode in world.js/login.js.

**Vraagt een andere aanpak / beperkt:**
- Een animatie die *over twee sessies heen* loopt (planeet van A die naadloos in het scherm van B overgaat) kan niet: elke sessie heeft een eigen compositor/VT; de VT-wissel zelf is een harde overgang. We animeren aan beide kanten (uit- en in-animatie).
- Venster-animaties: labwc 0.8.3 geeft via foreign-toplevel geen vensterpositie/-grootte. Positie blijft komen uit grim + mintrand (betrouwbaar als het venster actief is) of uit de cache/schatting. Echt "pixelperfect vanaf frame 1" kan alleen met een compositor-patch of een labwc-versie met positie-informatie (buiten deze ronde).
- De vergrendelde sessie tonen op het vergrendelscherm (miniatuur) gebeurt bewust niet (beveiliging).

## 3. Klussen (onafhankelijk, elk een eigen branch `klus/gN` vanaf main)
1. **g1 – Gebruikersplaneten-rij op het inlogscherm** (`ui/login.*`): grote planeet blijft centraal; rij kleine planeten met naam eronder (horizontaal/licht gebogen), automatisch schalen/afbreken bij veel gebruikers (1, 2, 8, 20), niet versleepbaar, klik/tik selecteert, geselecteerde planeet komt naar voren; toetsenbordnavigatie. Test: node/harnas met 1/2/8/20 gebruikers + drag-test.
2. **g2 – PAM-loginflow in de greeter** (`shell/greeter.py`, `ui/login.js`): selectie → `authenticate(user)` → wachtwoordveld bij de geselecteerde planeet → fout = duidelijke melding, blijft op het scherm, veld leeg, geen toegang; annuleren bij wisselen van planeet; bestaande sessie van die gebruiker = terug naar die sessie (LightDM doet de switch). Nooit wachtwoord loggen. Test: python met nagebootste LightDM.
3. **g3 – Vergrendelen / Andere gebruiker / Uitloggen** (`usr/bin/universe-lock`, nieuw `usr/bin/universe-wissel`, shell-menu, gtklock-layout): 'Andere gebruiker' = eerst vergrendelen (direct) dan `dm-tool switch-to-greeter`; knop 'Andere gebruiker' in het gebruikers/startmenu en op het gtklock-scherm; 'Uitloggen' = bevestiging + animatie + `loginctl terminate-session`. Test: python/sh met nagebootste commando's.
4. **g4 – Gebruikersoverzicht en accountinstellingen** (`ui/accounts-ui.js`, `control_center.py`, `universe-admin-helper`, polkit-policy): overzicht = alleen naam + planeet; klik opent instellingen als bevoegd (admin: iedereen, normaal: alleen zichzelf); accounttype wijzigen (groep sudo) alleen admin via polkit; laatste admin kan niet worden gedegradeerd/verwijderd. Test: python.
5. **g5 – Vensteranimaties en wisselanimaties** (`flits.py`, `world.js`/`login.js` animaties): vloeiender easing per eigenschap, gloed/rand aansluitend, sluiten ook bij meerdere vensters, geen klikblokkade (input-shape leeg), CPU zuinig; animatie bij vergrendelen (eigen planeet terug naar de rij) en na inloggen (grote planeet → werkomgeving). Test: bestaande + nieuwe flits-tests.

Volgorde van mergen: g4 → g3 → g2 → g1 → g5 (g1 en g2 raken beide `login.js`: g2 eerst rebasen/oplossen).

## 4. Testplan (live, test-VM, licht en vol, gebruikers: tester (admin), anna (normaal), bram (normaal))
Punt 11 van Jesse: in/uitloggen admin en normaal, vergrendelen/ontgrendelen, A→B→A met vensters intact, eigen instellingen, normaal kan geen admin-instellingen, vensteranimaties (ook meerdere), inlogscherm met 1/2/veel gebruikers, grote planeet zichtbaar, rij eronder, uitloggen beëindigt echt (`loginctl list-sessions`), fout wachtwoord geen toegang, vergrendelde sessie afgeschermd, niet versleepbaar, bruikbaar bij veel gebruikers.

## 5. Risico en terugdraaien
Geen nieuwe displaymanager, LightDM-config blijft gelijk. Alles zit in het pakket universe-os en is met de vorige .deb terug te zetten.
