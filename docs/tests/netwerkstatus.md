# Netwerkstatus — 2026-10-06

🧪 Geen VM-/hardwarebewijs. `python docs/tests/netwerkstatus.py` slaagt lokaal:
geen apparaat, wifi uit, niet verbonden, apparaat niet beschikbaar, onbeheerd,
verbonden met full/portal/limited/none/unknown, kabel actief terwijl wifi uit is,
netwerknaam met dubbele punt en onbereikbaar NetworkManager.
Vervolgcontrole: wifi-p2p/wireguard/dummy worden overgeslagen; connecting en
connecting (…) geven Bezig met verbinden…, terwijl een al actieve kabelverbinding
voorrang houdt. Een losse kabel plus virtuele apparaten blijft device-unavailable.

Paneel en Controlecentrum tonen dezelfde Nederlandse reden. Zonder herkend
apparaat wordt controle van driver/firmware voorgesteld; er wordt geen ontbrekende
driver vastgesteld zonder bewijs. Connectiviteit is de laatste NetworkManager-
waarneming; unknown wordt niet als internet of offline gepresenteerd.

Claude: test wifi uit/aan, kabel los/vast, captive portal, lokaal netwerk zonder
internet en uitgeschakeld NetworkManager. Controleer paneel en instellingen.
Bron: https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nmcli.html
