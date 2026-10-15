# Oplossingen voor de AI-stapel

Stand na de pull requests 39 tot en met 42, plus deze tak. Dit is geen lijst van deuren die dicht blijven. Elk punt hieronder heeft een werkende weg.

De gedeelde gereedschapsserver blijft `universe_mcp.py`. De starter kiest het programma. OpenClaude wordt niet gebruikt: het is een ongeautoriseerde afgeleide en stuurt standaard via een betaalde gateway, met zoeken via Exa. Een andere agent, als je die wilt, is OpenCode (MIT) of Goose (Apache-2.0). Hun eigen toestemming is niet de grens.

## Gmail en Outlook: log in in Chrome

De apparaatcode van Google ondersteunt de Gmail-scopes niet, en een ongeverifieerde OAuth-app werkt alleen voor testgebruikers. Dat is geen reden om mail onmogelijk te maken.

**Werkende weg:** Google Chrome en de officiële extensie Claude in Chrome (`https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn`). De knop op de Internet-planeet is de voorkeursroute; dezelfde knop staat op Controlecentrum → AI. Die vraagt eerst toestemming, ook als automatisch toestaan aan staat, installeert Chrome uit de officiële apt-bron `https://dl.google.com/linux/chrome/deb/` en opent die winkelpagina. De gebruiker logt in in zijn eigen browser. Een klik op de Internet-planeet opent nog steeds de gekozen standaardbrowser. Claude Code start met `--chrome` zodra Chrome er is (`ai_provider.py`, `chrome_agent.py`). De verbinding is er als Chrome, de extensie en het native-hostbestand `com.anthropic.claude_code_browser_extension.json` er alle drie zijn.

Lezen, sorteren, concepten, onderzoek en formulieren gaan door. De Accounts-pagina zegt dat ook: log gewoon in in Chrome. IMAP en OAuth blijven staan als extra weg voor een eigen server, niet als de enige weg.

## Versturen blijft agentisch, belangrijke mail niet

Automatisch toestaan staat uit tot de gebruiker het aanzet, met een duur. Daarna mag een kort antwoord naar een adres dat al eens is goedgekeurd weg, zonder venster. De volledige tekst komt in het brein onder Acties.

Dit blijft een vraag, ook als automatisch toestaan aan staat:

- een nieuwe ontvanger
- een woord of domein van de lijst op de pagina AI (standaard onder meer bank, overheid, verzekering, werkgever, verhuurder, geld, contract, juridisch, gezondheid, baan, wachtwoord)
- een bijlage
- meer dan drie ontvangers
- een bericht dat het model zelf als belangrijk markeert
- betalen, wissen en een wachtwoord

De lijst is te bewerken (`auto.regels`). De extensie vraagt zelf ook voor gevoelige acties. Een klik op Versturen in de browser mag pas nadat `mail_send` zojuist is goedgekeurd; de hook schrijft browserstappen onder Acties en houdt de rest tegen (`universe-claude-hook`, `chrome_agent.judge_browser`).

## Muis op Debian

Websites hebben geen `/dev/uinput` nodig. Claude in Chrome bedient de aangemelde browser.

Voor de rest van het bureaublad is `wtype` de weg voor toetsen; dat zit in Debian 13. De muis kan via `ydotool` uit trixie-backports, met een udev-regel die de gebruiker zelf aanzet. Het script staat in `screen.desktop_mouse_script` en wordt niet vanzelf gedraaid:

```
deb http://deb.debian.org/debian trixie-backports main
apt-get install -y -t trixie-backports ydotoold
KERNEL=="uinput", GROUP="input", MODE="0660"
usermod -aG input "$USER"
```

Daarna opnieuw aanmelden. De groep `input` is een bewuste keuze van de gebruiker, geen standaard van het pakket.

## Een klein lokaal model

Ollama met `qwen2.5:3b` blijft de weg als er niets de computer mag verlaten. Voor werk dat een sterker model nodig heeft, wijst een Claude-sessie naar OmniRoute (`http://127.0.0.1:20128`) of LiteLLM (`http://127.0.0.1:4000`) via `ANTHROPIC_BASE_URL`. De knop Terug naar Claude haalt dat adres weg. OmniRoute blijft uit tot de gebruiker zelf een aanbieder toevoegt. Gratis aanbieders kunnen de vragen lezen; dat staat op de pagina. Gemini en Ollama gaan niet via die router.

## Wat de grens is

De shell vraagt, of de mailpoort beslist. De weigerlijst van Claude is een extra laag, niet de grens. Bubblewrap, als het er is, verbergt de sessiebus, Wayland en `/dev/uinput`, zodat het programma niet zelf de sleutelbos of de muis pakt. Bij `--chrome` blijven `/tmp` en de echte runtime-map zichtbaar, anders kan de extensie de sessie niet bereiken. De bus en uinput blijven dicht.

De schermvlag leeft in het geheugen van de shell. Super+Escape zet schermbediening en automatisch toestaan uit. Een terminal kan de bevestiging niet omzeilen. Afsluiten gaat niet via een stille `systemctl` als de shell weg is.

`$HOME` blijft beschrijfbaar, anders kan de assistent geen bestanden bewerken. Ontbreekt bubblewrap, of zet iemand `UNIVERSE_AI_SANDBOX=0`, dan is die afscherming weg. De tests zijn headless contracten: ze bewijzen de beslissingen, niet een levende Chrome-sessie.
