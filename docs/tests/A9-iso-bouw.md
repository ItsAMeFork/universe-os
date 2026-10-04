# Test A9: ISO bouwen met `scripts/build-iso.sh` (spoor A)

**Datum:** 4 oktober 2026
**Omgeving:** bouw-VM Debian 13.7 (trixie) amd64, live-build `1:20250505+deb13u1`.
**Bouwkopie:** `~/universe-os-chatgpt` in de bouw-VM, commit `d37a3fd` = `main` (`a8dd844`) + B10 (PR #3) + A7-login (PR #4).
Bouw gestart door ChatGPT via Axel; gecontroleerd door Claude.

## Uitkomst

| Controle | Uitkomst |
|---|---|
| `lb build` | ✅ `P: Build completed successfully` (logboek `uitvoer/logs/20261004-1342/lb-build.log`, start 13:42, klaar 14:22) |
| ISO | ✅ `universe-os-0.1.0-amd64.iso`, 1.939.922.944 bytes |
| SHA-256 | ✅ `1e596280eac08ef6e2178d07e74e6b38b11cda75f42a0339bf295fd39ba6aed4`, `sha256sum -c` geeft `OK` |
| Pakketversies | ✅ 1232 pakketten in `pakketversies.txt` |

Belangrijkste pakketten in het ISO: linux-image-amd64 6.12.111-1, labwc 0.8.3-1, lightdm 1.32.0-6+b2,
lightdm-gtk-greeter 2.0.9-1, xserver-xorg-core 21.1.16-1.3+deb13u4, calamares 3.3.14-1, wine en wine32:i386
10.0~repack-6, grub-efi-amd64-signed 1+2.12+9+deb13u2, shim-signed 1.51~1+deb13u1, universe-os 0.1.0.

Meldingen in het logboek die geen fout zijn: `Failed to open connection to "system" message bus` (geen D-Bus in de
chroot) en het blok dat live-build zelf markeert met "can be ignored".

## Gevonden en opgelost

- **Rechtenfout** (`uitvoer/logs/geintegreerde-bouw-rechtenfout*.log`): de `chmod +x` in `build-iso.sh` raakte ook de
  hooks die `lb config` als symlink naar systeembestanden aanmaakt (`0010-disable-kexec-tools.hook.chroot` enz.):
  `Operation not permitted`, en door `set -e` stopte de bouw. Opgelost: `build-iso.sh` maakt alleen eigen bestanden
  uitvoerbaar, en `live/auto/*`, de eigen hooks en `scripts/*.sh` staan nu als uitvoerbaar (100755) in git.

## Niet getest

- Deze bouw is gedraaid vóór de rechtenfix uit deze commit (in de bouwkopie zijn de rechten met de hand gezet).
  De volgende bouw vanaf `main` controleert de fix.
- Opstarten, installeren en inloggen: dat is A12.
