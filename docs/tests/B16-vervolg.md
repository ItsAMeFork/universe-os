# B16 vervolg: opstart — 2026-10-06

🧪 Het doel ≤ 3 seconden vanaf geslaagde authenticatie is nog niet bewezen.

Aanpassingen: shell direct starten in labwc-autostart; omgevingspublicatie en
gebruikersmappen blokkeren dit niet meer. Scherminstellingen en hulpprogramma's
blijven starten. Overzicht-WebView pas maken bij eerste gebruik. Native WebKit-
achtergrond donker vóór laden van HTML/CSS. Na twee frames met de gebouwde
ruimtewereld schrijft `world.ready` een monotone tijdmeting in shell.log.

Lokale Python/JavaScript-syntax en diffcontrole; geen tijdwinst geclaimd.

Claude: meet vijf koude logins op dezelfde hardware op 1920×1080, vanaf juiste
wachtwoordbevestiging tot bruikbare planeten. Noteer totale duur en shell.log
(`ruimtewereld zichtbaar`), ook live-start. Controleer eerste beeld op wit,
Windows/Windows+A, schermschaling en meerdere schermen. Meet daarna FPS met
UNIVERSE_DEBUG_FPS=1, animaties full/reduced/off. Als doel niet gehaald wordt,
gebruik sessie- en shell-log om resterende login/compositor/WebKit-tijd te scheiden.
