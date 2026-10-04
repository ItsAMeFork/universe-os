# Test A1–A3: deb-pakket `universe-os` (spoor A, Claude)

**Datum:** 4 oktober 2026
**Omgeving:** bouw-VM Debian 13.7 (trixie) amd64 in QEMU 11.1 met WHPX op Windows 11 (Intel i5-10210U, 15,4 GB RAM).

## Uitgevoerd

| Stap | Opdracht | Uitkomst |
|---|---|---|
| Pakket bouwen | `sh scripts/build-deb.sh` | ✅ `uitvoer/universe-os_0.1.0_all.deb`, Installed-Size 524 KiB. Python-syntaxcontrole en `sh -n` geslaagd; Wayland-bindingen gegenereerd. |
| Installeren met afhankelijkheden | `apt-get install --no-install-recommends ./uitvoer/universe-os_0.1.0_all.deb` | ✅ apt-afsluitcode 0; alle afhankelijkheden in `Depends` bestaan in Debian 13. |
| Wine-omleiding | `dpkg-divert --list` | ✅ `wine.desktop` omgeleid naar `/usr/share/universe-os/diverted/`. |
| Privé persoonlijke mappen | `grep HOME_MODE /etc/login.defs`, `grep DIR_MODE /etc/adduser.conf`, `ls -ld /home/bouwer` | ✅ `0700`, `drwx------`. Fout gevonden: `HOME_MODE` stond twee keer in `login.defs`. Opgelost in `postinst`. De oplossing is nog niet opnieuw getest. |
| Firewall | `grep ENABLED /etc/ufw/ufw.conf` | ✅ `ENABLED=yes`, inkomend geweigerd. Bijwerking: dit blokkeerde ook SSH naar de bouw-VM (zie hieronder). |
| Rooktest sessie zonder scherm | labwc headless + `universe-ctl ping` | ✅ Shell gestart, socket aanwezig, antwoord `ok`. Vensterlijst en Windows+D zijn niet getest, omdat de SSH-verbinding wegviel door de firewall. |

## Lessen

- **Installeer `universe-os` niet in de bouw-VM**: de firewall blokkeert dan SSH. Testen van het pakket hoort in een
  wegwerp-VM of in het live-ISO. De bouw-VM heeft nu een QMP-beheerkanaal (`vm/qmp.mjs`, poort 4444) om zoiets te herstellen.

## Nog te testen

- Opnieuw installeren na de `HOME_MODE`-fix (moet precies één regel opleveren).
- Vensterlijst, Windows+D en overzicht in een sessie met een venster (overgedragen aan B1 van spoor B, in het live-ISO).
