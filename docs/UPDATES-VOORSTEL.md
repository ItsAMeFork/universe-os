# Voorstel: eigen updates voor Universe OS

Status (6 okt 2026): **besloten door Axel: GitHub Pages, hoofdsleutel op USB-stick, twee kanalen.** Sleutel gemaakt (vingerafdruk `771F 7DCD 1FB9 4C8D 5C4C  1B37 9D38 DB26 1B78 24AC`). **Online sinds 6 oktober 2026:** https://itsamefork.github.io/universe-os-apt/ (repo `ItsAMeFork/universe-os-apt`), versie 0.2.0 in test en stable, via HTTPS met apt getest.

## Kort

Ja, dat kan, en zonder eigen server. Universe OS krijgt een eigen **ondertekende APT-pakketbron** naast de
bronnen van Debian (beveiliging) en Google (Chrome). Updates van onze interface komen dan via precies dezelfde
weg als Debian-updates: PackageKit, GNOME Software, `apt` en onze eigen updateweergave zien ze vanzelf. Er komt
geen `git pull` en er worden geen ongetekende downloads gedaan.

## Hoe het werkt

```
bouw-VM: build-deb.sh ──► test-VM: installeren + testen ──► Axel keurt goed
   ──► ondertekenen (sleutel van Axel, niet in git) ──► publiceren op GitHub Pages
   ──► elke Universe-pc: PackageKit ziet "universe-os 0.2.0" ──► bijwerken
```

| Onderdeel | Keuze |
|---|---|
| Hosting | Een aparte GitHub-repo `universe-os-apt` met GitHub Pages (HTTPS). Gratis; ons pakket is ~1 MB, ruim binnen de limieten (1 GB opslag, ~100 GB verkeer per maand). Een eigen domeinnaam (± €10 per jaar) kan later, zodat we niet aan GitHub vastzitten. |
| Pakketbron maken | `apt-ftparchive` (apt-utils) in de bouw-VM, via `scripts/publiceer-apt.sh`. Alle versies blijven in `pool/` (terugdraaien via apt); `kanalen/test.lijst` en `kanalen/stable.lijst` bepalen wat elk kanaal ziet. (reprepro 5.3.1 in trixie bewaart maar één versie per kanaal, daarom niet gebruikt.) |
| Ondertekening | OpenPGP-sleutel (ed25519; `sqv` in Debian 13 accepteert die). **Hoofdsleutel offline** bij Axel (USB-stick of `D:\UniverseOS-VMs\keys`, nooit in git of op GitHub). Ondertekenen gebeurt met een **subsleutel die 2 jaar geldig is**. |
| Sleutel op de pc's | Pakket `universe-os-archive-keyring` zet de publieke sleutel in `/usr/share/keyrings/universe-os.gpg`. De bron staat in `/etc/apt/sources.list.d/universe-os.sources` met `Signed-By:` alleen voor onze bron; de sleutel geldt dus niet voor Debian of Google. |
| Sleutel vervangen | Ruim vóór het verlopen een nieuwe subsleutel maken en via een update van `universe-os-archive-keyring` meesturen. Een tijd lang worden beide geaccepteerd, daarna wordt met de nieuwe getekend. Bij een gelekte sleutel: intrekken en een nieuw keyring-pakket (alleen bereikbaar zolang de oude sleutel nog vertrouwd wordt, dus de hoofdsleutel goed bewaren). |
| Kanalen | `stable` (voor iedereen) en `test` (alleen voor testcomputers die het zelf aanzetten). Eerst naar `test`, na goedkeuring dezelfde versie naar `stable`. |
| Versies | Debian-versienummers: `0.1.0` → `0.2.0` (functies), `0.2.1` (reparaties). Elke versie heeft een changelog. `branding/universe.json` blijft de bron van het versienummer. |

## Compatibiliteit en migraties

- Nieuwe versies moeten instellingen van oudere versies kunnen lezen (`~/.config/universe-os/*.json`); onbekende
  velden negeren, ontbrekende aanvullen met standaardwaarden (zo werkt `config.py` nu al grotendeels).
- Systeemwijzigingen in `postinst` alleen met een versiecontrole (`dpkg --compare-versions "$2" lt 0.2.0`), zodat
  een migratie één keer draait.
- `Depends` alleen op pakketten uit Debian 13 (trixie), zodat een update nooit een andere Debian-versie vereist.
- Bestanden in `/etc` blijven conffiles: eigen aanpassingen van de gebruiker worden niet stil overschreven.

## Herstel en terugdraaien

- Oude versies blijven in de bron staan. Teruggaan: `sudo apt install universe-os=<oude versie>` (later ook als
  knop in het Controlecentrum).
- Start de interface na een update niet, dan blijft de sessie **Universe OS herstelmodus** op het inlogscherm
  beschikbaar (terminal), en het GRUB-menu met Esc.
- Volledige systeemmomentopnamen (btrfs/snapper) zijn met de huidige indeling (ext4) niet mogelijk; dat zou een
  aparte keuze in de installer zijn.

## Hoe de gebruiker het ziet

- **PackageKit / GNOME Software** lezen gewoon de APT-bronnen. Een nieuwe `universe-os` verschijnt als
  systeemupdate, net als Debian-updates.
- **Onze updateweergave** (`updates.py`, `pkcon get-updates`) telt ze automatisch mee. Spoor B kan per update
  laten zien uit welke bron die komt ("Universe OS", "Debian-beveiliging", "Google Chrome").
- Automatisch bijwerken: hetzelfde als voor Debian-updates (melding, gebruiker kiest). Geen stille herinstallatie
  van de interface terwijl je werkt; na een update van de shell volstaat opnieuw aanmelden.

## Wat er al is en wat nog gebouwd moet worden

| Er al | Nog te bouwen |
|---|---|
| `universe-os`-deb bouwen (`scripts/build-deb.sh`) | Sleutel maken (Axel, offline), keyring-pakket |
| Test-VM om te testen vóór publicatie | `scripts/publiceer-apt.sh` (reprepro + ondertekenen + naar Pages) |
| Updateweergave en PackageKit in het systeem | Repo `universe-os-apt` + GitHub Pages aanzetten |
| Versie in `branding/universe.json` | `.sources`-bestand + keyring in het ISO; changelog; versieregels |

Schatting: één tot twee werksessies voor spoor A om de bron en het ISO voor te bereiden. Kosten: €0 (GitHub
Pages), eventueel ± €10 per jaar voor een eigen domein.

## Beslissingen voor Axel

1. Akkoord met GitHub Pages als eerste hosting (of meteen een eigen domein)?
2. Waar bewaren we de offline hoofdsleutel (bijv. aparte USB-stick + kopie)?
3. Twee kanalen (`stable` + `test`) of eerst alleen `stable`?

## Stand van de uitvoering (6 oktober 2026)

Getest in de bouw-VM met een wegwerpsleutel: publiceren naar test en daarna stable; 0.1.0 en 0.1.1 blijven allebei
installeerbaar; dezelfde versie met andere inhoud wordt geweigerd; een vervalste `InRelease` wordt door apt (sqv)
geweigerd; een stable-computer ziet geen testversies; `universe-updates-helper kanaal stable|test` (polkit-actie
`nl.universeos.admin.updates`) zet het testkanaal aan en uit.

Nog te doen, in deze volgorde:
1. ✅ Repo `universe-os-apt` met GitHub Pages (tak `main`, map `/`); de bouw-VM pusht met een eigen deploy key (alleen deze repo).
2. ✅ Ondertekensubsleutel geïmporteerd in de bouw-VM (de hoofdsleutel blijft op de stick).
3. ✅ 0.2.0 gepubliceerd in test en stable; apt via HTTPS gecontroleerd (handtekening, beide kanalen, download).
4. ✅ `scripts/apt/bron-actief` aangemaakt: het volgende ISO krijgt de bron mee.
5. Nog niet getest: sleutelrotatie (oude client → nieuwe subsleutel → verlopen oude subsleutel) en het omkeren van
   migraties bij terugdraaien. Herstel na een gelekte sleutel is geen automatisch pad: dat vraagt een nieuw ISO.
