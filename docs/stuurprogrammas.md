# Stuurprogramma's (vanaf 0.2.23)

Doel: het ISO werkt op zo veel mogelijk pc's, zoals Ubuntu, Pop!_OS en Mint. Lijst:
`live/config/package-lists/stuurprogrammas.list.chroot`. Firmware (wifi, bluetooth, geluid, grafisch) kwam al mee via
`--firmware-chroot`.

## Grafisch
- **Intel, AMD, virtuele machines:** Mesa (OpenGL, Vulkan, VA-API, VDPAU), alle Xorg-stuurprogramma's,
  `intel-media-va-driver-non-free` en `i965-va-driver`. Laden zoals altijd vanzelf.
- **NVIDIA:** het eigen stuurprogramma 550 (`nvidia-driver`, `nvidia-kernel-dkms`, `nvidia-vulkan-icd`) met
  `linux-headers-amd64`. De module wordt tijdens de bouw door DKMS gemaakt (hook `0300-stuurprogrammas`; de bouw stopt
  als hij ontbreekt). Een geïnstalleerd systeem maakt hem opnieuw na een kernelupdate.

### Wie kiest nvidia of nouveau
`/etc/modprobe.d/universe-gpu.conf` houdt nouveau en nvidia tegen bij het automatisch laden (ook in de initramfs).
Het NVIDIA-pakket zelf zou nouveau op elke pc blokkeren; dat bestand haalt de hook weg.
`universe-gpu.service` (vóór het inlogscherm) kijkt dan per pc:

| Situatie | Keuze |
|---|---|
| Geen NVIDIA-kaart | niets, niets verandert |
| Kaart die nvidia 550 kent (Maxwell/GTX 750 en nieuwer; PCI-id in de module) | `nvidia` (met `modeset=1`) |
| Oudere kaart (bijv. GT 210, GTX 600-reeks met Kepler) | `nouveau` |
| nvidia laadt niet (Secure Boot, zie hieronder) | terug naar `nouveau` |
| Opstartoptie `universe.gpu=nvidia` / `nouveau` / `veilig` | die keuze |

Uitkomst: `/run/universe-os/gpu.json` en `journalctl -u universe-gpu`. `grafisch.py` onthoudt zijn beeldproef per
stuurprogramma, dus na een wissel nouveau → nvidia test hij één keer opnieuw.

### Opstartmenu (live-ISO, UEFI en BIOS)
- **Universe OS** (standaard): automatisch, zoals hierboven. (De stock-entry "Live system" en de fail-safe-entry zijn weggehaald.)
- **NVIDIA-stuurprogramma:** `universe.gpu=nvidia`, ook als de kaart niet in de lijst staat.
- **Veilige grafische modus:** `universe.gpu=veilig universe.gfx=safe`: geen GPU-stuurprogramma, het beeld van de
  firmware (simpledrm) en tekenen door de processor. Werkt ook met Wayland (labwc).
- **nomodeset (noodgeval):** ook simpledrm uit. labwc heeft dan geen beeldscherm; alleen voor als niets anders werkt.
Op een geïnstalleerd systeem: in GRUB met `e` dezelfde opties toevoegen.

### Secure Boot
Het ISO start met Secure Boot (shim en kernel zijn door Debian ondertekend), en nouveau is ook ondertekend. De
NVIDIA-module van DKMS is **niet** ondertekend met een sleutel die de pc vertrouwt; met Secure Boot aan weigert de
kernel hem. Dan valt universe-gpu terug op nouveau (staat in `gpu.json`). Wie nvidia wil met Secure Boot: na de
installatie een eigen sleutel inschrijven (`sudo mokutil --import /var/lib/dkms/mok.pub`, herstarten, MOK
bevestigen), of Secure Boot uitzetten. De DKMS-sleutel van de bouw wordt uit het ISO gehaald (een openbare privésleutel
zou iedereen modules laten ondertekenen); een geïnstalleerd systeem maakt een eigen sleutel bij de volgende DKMS-bouw.

## Verder
- Video: GStreamer good/bad/ugly/libav en VA-API.
- Printen: CUPS met printers zonder stuurprogramma (IPP Everywhere, AirPrint, `ipp-usb`), Gutenprint, HP (hpcups),
  Brother (brlaser), Samsung/Xerox (splix), foo2zjs; `system-config-printer`.
- Scannen: `sane-airscan` en Simple Scan.
- Tekentabletten: `xserver-xorg-input-wacom`. Firmware-updates: `fwupd`. Thunderbolt: `bolt`.
- Windows-schijven en USB-sticks: `ntfs-3g`, `exfatprogs`.
- Niet toegevoegd: `broadcom-sta-dkms`. Dat blokkeert b43/bcma/brcmsmac op elke pc, ook waar die wel werken.
  De open Broadcom-firmware (`firmware-brcm80211`, b43) zit er al in.
