# Chrome-beeldcorruptie op echte hardware

De screenshots bewijzen verschoven/duplicerende Chrome-beeldblokken, maar geen specifieke driver- of pakketoorzaak. Dit is een diagnosehulp, nog geen bewezen reparatie.

Start als gebruiker achtereenvolgens `universe-chrome-beeldtest auto`, `wayland`, `x11` en `software`. Sluit telkens alle testvensters. Elke proef gebruikt een apart tijdelijk profiel; het bestaande Google-profiel blijft intact. Logbestanden staan in `~/.local/state/universe-os/chrome-beeldtest-<modus>.log`; lees ze vóór delen, ze kunnen systeemdetails bevatten.

Noteer per proef: Chrome-versie, videokaart/driver, Problems Detected en Graphics Feature Status op chrome://gpu, corruptie ja/nee, typen/scrollen/video/vergroten. Vergelijk ook het echte profiel zonder het te verwijderen: verdwijnt de fout alleen met schoon profiel, onderzoek instellingen/extensies. Verdwijnt hij alleen in softwaremodus, onderzoek GPU/driverpad. Verdwijnt hij alleen op een specifiek displaypad, toets die combinatie. Geen --no-sandbox of definitieve GPU-uitschakeling zonder bewijs.

Claude: voer de vergelijking uit op de getroffen computer en kies pas daarna een launcher-/driverreparatie. VM-test alleen bewijst niet dat Axels videokaart gerepareerd is.

Bron: officiële Chromium Ozone-documentatie ondersteunt de afzonderlijke Wayland/X11-paden: https://chromium.googlesource.com/chromium/src/+/HEAD/docs/ozone_overview.md
