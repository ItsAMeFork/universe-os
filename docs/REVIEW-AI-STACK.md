# Kritische review van de AI-stapel

Stand na de pull requests 39 tot en met 42 (testherstel, Claude-harness, Brein-nevel, assistent met accounts, mail, agenda en scherm), plus de reparaties op deze tak. Dit is een architectuur- en beveiligingsreview, geen verkooppraatje.

## Beslissing: geen goose, geen OpenCode

De gedeelde gereedschapsserver blijft `universe_mcp.py`. De starter (`launch.py` via `universe-ai`) kiest het programma: Claude Code, de Codex-CLI, de Gemini-CLI, of een kleine Ollama-client. Goose en OpenCode zijn bewust niet gebruikt.

- Die projecten zijn zelf een agent, met een eigen toestemmingssysteem. Dat systeem mag hier de grens niet zijn. Versturen, agenda en scherm moeten in de shell en in de MCP-server blijven, anders omzeilt een ander programma de zenity-vragen.
- Ze staan niet in Debian 13, kosten extra geheugen, en een zwakke pc heeft daar geen ruimte voor.
- Goose praat zelf met de API. Dat botst met het bestaande ontwerp: ongewijzigde Claude Code, geen `claude -p` tegen het abonnement.
- De drie cloudbureau’s spreken al MCP. Een eigen adapter per bureau is dan dubbel werk. Alleen Ollama is geen MCP-client. `ollama_host.py` is de enige nieuwe, kleine client (alleen de standaardbibliotheek). Er is in Debian geen onderhouden MCP-client voor Ollama.

Bestaande MCP-servers voor Gmail, Outlook en CalDAV lossen de zenity-poort niet op. Open Interpreter en computer-use-pakketten sturen muis en toetsen vanuit het modelproces. Dat is precies het gat dat deze shell dicht probeert te houden. LiteLLM is een proxy voor modelaanroepen, geen bureaubladagent, en voegt hier niets toe.

## Wat deze tak heeft dichtgezet

- De schermvlag is geen bestand meer dat het model zelf kan aanmaken. Hij staat in het geheugen van de shell en gaat alleen aan na een zenity-vraag (`screen.py` regel 64–87, `universe_shell.py` regel 818–822, `control_center.py` regel 72–74).
- `call` op de socket mag alleen van het echte `universe_mcp.py` (`peer.py` regel 24–48, `universe_shell.py` regel 739–742). Sneltoetsen zoals `scherm-stop` blijven open.
- Een terminal mag niet geopend, gefocust of beschreven worden. Toetsen die een terminal openen zijn geblokkeerd (`universe_shell.py` regel 45–46 en 676–699, `screen.py` regel 27–32 en 378–383).
- Zolang zenity openstaat, weigert schermbediening (`confirm.py` `busy()`, `screen.py` regel 371–373).
- Afsluiten, herstarten en slaapstand vallen niet meer terug op `systemctl` (`universe_mcp.py` regel 194–227).
- Mail- en agendatekst krijgt het voorvoegsel onbetrouwbare gegevens (`universe_mcp.py` regel 31–33 en 511–512). Een schermafbeelding krijgt een tekstwaarschuwing (regel 506–508) en staat niet meer op de automatische toestemmingslijst van Claude (`settings.json` regel 3–8).
- Bubblewrap, als het er is, verbergt de sessiebus, Wayland en `/dev/uinput` (`sandbox.py` regel 52–66). De sleutel staat alleen in de omgeving, niet in argv of in een geschreven config (`ai_provider.py` regel 372–425, `launch.py` regel 24). Zonder bubblewrap worden die variabelen alsnog gewist (`sandbox.py` regel 69–74) en zegt het paneel dat de afscherming uit staat.
- `bubblewrap` staat in `Depends`. ydotool, wtype, dotool, secret-tool, busctl en gdbus staan op de Claude-weigerlijst (`settings.json` regel 11–12). Dat is alleen een extra laag voor Claude, niet de grens.

## Ranglijst

### 1. Kritiek — de bevestiging is een afspraak met het model, geen grens

**Waar:** `settings.json` regel 1–16; `launch.py` regel 52–55; `sandbox.py` regel 1–8 en 52–66.

De CLI draait als de gebruiker. De weigerlijst van Claude geldt alleen voor dat ene programma, en een model kan `python3 -c` of een omweg gebruiken. Vanuit een gewone shell kan hetzelfde account `ydotool`, `wtype` of `secret-tool` starten zonder zenity. Daarmee leest het de sleutelbos (Gmail-tokens) of stuurt het muis en toetsen buiten de MCP-server om.

**Reparatie hier:** bubblewrap als het pakket er is; zonder bus, Wayland en uinput. De socket van de shell is de enige deur, en die vraagt nog steeds bij versturen, agenda en scherm.

**Blijft open:** `$HOME` blijft beschrijfbaar, anders kan de assistent geen bestanden bewerken. Het model kan een user-unit of een `.desktop` neerleggen. Zonder D-Bus start die niet meteen, maar na de volgende aanmelding wel. Ontbreekt bubblewrap, of zet iemand `UNIVERSE_AI_SANDBOX=0`, dan is de oude omweg terug. De sleutelbosbestanden in de thuismap zijn geen platte tekst zolang Secret Service ze versleutelt; een platte backend wel.

### 2. Kritiek — de schermvlag was een bestand dat het model zelf aanzette

**Waar:** vroeger `screen.py` `enabled()` via `os.path.isfile` op `$XDG_RUNTIME_DIR/universe-os/ai-scherm`. Nu regel 55–87.

Hetzelfde Unix-account als de assistent kon `touch` op dat bestand doen. Daarna was muis en toetsenbord aan, zonder dialoog.

**Reparatie hier:** de vlag leeft alleen in het shellproces. `enabled()` gooit een achtergebleven bestand weg en leest het niet. Het controlecentrum roept `allow()` niet meer aan; `scherm-aan` toont zenity en faalt dicht als er geen bevestiger is. `universe-ctl` wacht daar 190 seconden op (`universe-ctl` regel 19–20), anders leek de schakelaar mislukt.

**Blijft open:** wie al aan stond, moet het opnieuw aanzetten. Een dialoog die de shell toont, kan nog steeds worden aangeklikt door `ydotool` van buiten de MCP-server, zolang de afscherming uit staat (punt 1).

### 3. Hoog — schermbediening was een ontsnapping

**Waar:** `screen.py` regel 365–383; `universe_shell.py` regel 45–46, 676–699 en 739–742.

Met de vlag aan kon `scherm_klik` op Toestaan van zenity drukken. `terminal` stond in `CLAUDE_RUN`. Daarna typt het model in een shell, en `screen.perform` draait in de shell, buiten elke bubblewrap. Het model kon ook `venster` zelf invullen en doen alsof de focus geen terminal was.

**Reparatie hier:** tijdens zenity weigert `perform`. De shell vult `venster` vanuit het gefocuste venster. Terminals en `ctrl+alt+t`, `super+t`, `super+return` worden geweigerd. `terminal` zit niet meer in de toestemmingslijst. Een klik die een terminal focust terwijl een ander venster actief is, wordt bij de volgende toetsaanslag alsnog geweigerd.

**Blijft open:** `terminal_app` kijkt of `terminal` in de basisnaam zit (`screen.py` regel 99–107). `notterminal` valt daardoor ook dicht. Dat is fail-closed, geen lek. ydotool buiten de MCP-server blijft punt 1.

### 4. Hoog — een wachtwoordveld is een bewering van het model

**Waar:** `universe_mcp.py` regel 488–490; `screen.py` regel 171–176 en 187–194.

`scherm_typ` vroeg alleen bevestiging als het model `veld` op wachtwoord of betaling zette. Het kan `veld` weglaten of `bericht` sturen en een wachtwoord typen. De widgetsoort is niet te zien; AT-SPI wordt niet gebruikt.

**Reparatie hier:** een enkel token van minstens 8 tekens met een cijfer of een teken uit `!@#$%^&*` telt als geheim, ook zonder `veld`. De auditregel bevat de tekst niet.

**Blijft open:** `zomerhuis` of een wachtwoordzin met spaties gaat zonder dialoog door. Dat is een heuristiek, geen veldlezer.

### 5. Hoog — promptinjectie uit mail, agenda en scherm

**Waar:** `universe_mcp.py` regel 31–33, 278–297 en 505–512; `uitleg.md`.

De tekst van een bericht of afspraak komt in de context van het model, en daarna mag dat model gereedschap aanroepen. Een zin als “verstuur dit naar een aanvaller” is dan geen opdracht van de gebruiker, maar het model kan hem wel opvolgen. Een schermafbeelding kan hetzelfde in pixels doen, inclusief een wachtwoord op het scherm.

**Reparatie hier:** mail en agenda krijgen een vast voorvoegsel dat zegt dat de tekst niet van de gebruiker is. De afbeelding krijgt een waarschuwing. Versturen en afspraken maken gaan nog steeds door zenity in de shell, niet door een vlag van het model. Claude keurt `schermafbeelding` niet meer van tevoren goed.

**Blijft open:** het voorvoegsel is een instructie, geen isolatie. Een model dat de instructie negeert, kan alsnog het gereedschap aanroepen; de zenity-vraag is dan de echte rem, en die toont de ontvanger. `schermafbeelding` heeft geen eigen zenity in de shell (`t_screenshot`, regel 278). Elke blik een dialoog maken maakt meekijken onbruikbaar. Gemini zet `trust: true` op de MCP-server (`ai_provider.py` regel 341–349), dus die CLI vraagt zelf niet. De shell vraagt nog wel bij versturen en bij gevoelige schermacties. Een webhook of een webpagina in de afbeelding blijft onbetrouwbaar.

### 6. Hoog — afsluiten viel terug op systemctl

**Waar:** `universe_mcp.py` regel 194–227.

Als de shell weg was, of een oude shell `niet toegestaan: claude.power` teruggaf, startte `direct_power` alsnog `systemctl poweroff`. De animatie werd overgeslagen en de computer ging uit.

**Reparatie hier:** alleen vergrendelen en afmelden mogen buiten de shell. Afsluiten, herstarten en slaapstand geven een fout.

**Blijft open:** afmelden zonder shell is nog steeds `labwc --exit`, zonder de afmeldanimatie. Dat is de oude, bewuste noodweg voor vergrendelen en afmelden.

### 7. Hoog — Gmail is voor een gewone gebruiker niet te koppelen

**Waar:** `accounts.py` regel 31–38 en 275–295; `accounts-ui.js` regel 91.

De apparaatcode van Google ondersteunt de Gmail-scopes niet (`invalid_scope`). `gmail.readonly`, `gmail.send` en `gmail.compose` zijn beperkt of gevoelig. Een ongeverifieerde OAuth-app werkt alleen voor testgebruikers, en verificatie bij Google is een bedrijfsproces, geen schakelaar in dit besturingssysteem. Universe OS levert terecht geen clientgeheim mee. De gebruiker moet zelf een desktopclient maken.

**Reparatie hier:** de Accounts-pagina zegt dit in het Nederlands en wijst naar IMAP. De apparaatknop blijft voor agenda en voor tests. Loopback met PKCE, `state` en `127.0.0.1` bestond al (regel 296–313) en is de juiste browserweg.

**Blijft open:** zonder een geverifieerde client van de gebruiker zelf koppelt Gmail niet voor anderen. Microsoft-scopes hebben hun eigen beheerdersconsent. Dit hoort niet “even gefikst” te worden door een geheim in het pakket te stoppen.

### 8. Hoog — Debian 13 levert de muisbediening niet

**Waar:** `screen.py` regel 4–8 en 110–125; `DEBIAN/control`; `universe-ydotoold.service` regel 4.

`ydotool` zit niet in trixie, alleen in backports. Er is geen udev-regel die `/dev/uinput` openzet; dat apparaat is vaak `root:root` modus 600. `python3-evdev` staat in Depends, maar zonder leesrecht op uinput doet de muis niets. De gebruiker in de groep `input` zetten zou het gat van punt 1 groter maken en doen we niet. `wtype` zit wel in trixie en is de weg voor toetsen, niet voor de muis.

**Reparatie hier:** geen. Het pakket documenteert de terugval en de service start alleen als `/usr/bin/ydotoold` bestaat.

**Blijft open:** op een schone trixie beweegt de assistent de muis meestal niet. Dat in de afhankelijkheden zetten zou een pakket eisen dat de distributie niet levert.

### 9. Middel — we hebben een agent nagebouwd, deels terecht

**Waar:** `universe_mcp.py` (ongeveer 570 regels), `accounts.py` (ongeveer 1000 regels), `screen.py`, `ollama_host.py`.

OAuth, IMAP, CalDAV, scherm en geheugen zijn eigen code. Dat is duplicatie naast bestaande MCP-servers. De duplicatie is de prijs van één zenity-poort in de shell. Twee toestemmingssystemen (Claude-deny én zenity) blijven naast elkaar bestaan; alleen de shell telt.

`ollama_host.py` is de enige adapter die erbij moest. Die roept geen `send_mail` en geen `ydotool` zelf aan.

### 10. Middel — de tests bewijzen de contracten, niet het bureaublad

**Waar:** `docs/tests/ai-wisselen.py`, `docs/tests/ai-assistent.py`, `docs/tests/claude-harness.py`.

Ze draaien zonder GTK, zonder echte sleutelbos, zonder netwerk, zonder uinput en zonder zenity. Shellfuncties worden via de AST uit het bestand getrokken en los uitgevoerd. Daarom moet `call()` werken zonder peer; de peercheck zit in `incoming`, niet in `call`. `allow_call` wordt als brontekst en als pure functie getest, niet over een levende Gio-socket.

Dat vangt regressies in de beslisbomen. Het vangt niet: een echte Codex- of Gemini-installatie, een echte Ollama, een echte bubblewrap-run, of een gebruiker die Toestaan indrukt.

### 11. Middel — een trage pc

Claude Code en de Codex- en Gemini-CLI zijn Node. Een schermafbeelding is grim plus GdkPixbuf over het hele scherm (`universe_mcp.py` regel 278–294). Recoll indexeert documenten. Een 7B-model op Ollama maakt zo’n machine onbruikbaar.

De pagina AI stelt `qwen2.5:3b` voor (`ai_provider.py` regel 56–60) en zegt dat een klein model gereedschap slechter volgt. De buddy blijft cairo, bewust licht. De bevestiging hangt niet af van hoe gehoorzaam het model is.

### 12. Middel, privacy — het brein bewaart te veel, lokaal

**Waar:** `brein.py` via mail, agenda en `log_actie` in `screen.py` regel 372–405.

Onderwerpen, afspraakteksten en een actielog staan in `brein.db` op deze schijf. Dat verlaat de computer niet via deze code, maar een back-up of een ander account op dezelfde machine wel. Een schermafbeelding van het hele scherm, inclusief een wachtwoord, gaat naar het gekozen model. Bij Claude, Codex en Gemini is dat een wolk. Bij Ollama niet.

De audit van een gevoelig typveld bevat de tekst niet. De afbeelding zelf wel, zodra het model haar mag zien.

### 13. Middel — OAuth-loopback is in orde, de stappen ernaar niet

**Waar:** `accounts.py` regel 246–313.

`state`, PKCE, alleen `127.0.0.1`, clientgeheim in de sleutelbos. Een willekeurige poort hoort bij een desktopclient; een webclient met een vaste redirect is de verkeerde soort en de pagina zegt dat. Voor een niet-technische gebruiker is “maak een Google Cloud-desktopclient” geen taak. IMAP is de eerlijke weg voor mail.

### 14. Middel — de peercheck is een argv-check

**Waar:** `peer.py` regel 24–48; `universe_shell.py` regel 739–746.

De socket is modus 0600, dus alleen dezelfde gebruiker. `call` eist dat de peer Python is en dat een argument het echte pad van `universe_mcp.py` is. Een verzonnen argv met alleen de bestandsnaam komt er niet door als het pad niet klopt.

Wie zelf `python3 …/universe_mcp.py` start, mag `call` wél doen. Dat is de voordeur: dezelfde handlers, dezelfde zenity. Het dicht het gat van `echo 'call …' | socat` vanuit bash. Het dicht niet punt 1.

`scherm-aan` is geen `call` en mag dus van elk proces van deze gebruiker, inclusief de afgeschermde CLI. De dialoog verschijnt in de shell. Binnen bubblewrap kan het model Toestaan niet aanklikken.

### 15. Laag tot middel — codekwaliteit

Brede `except Exception` in de MCP-afhandeling (`universe_mcp.py` regel 542) is bewust: een fout moet een leesbaar gereedschapsantwoord zijn, geen protocolbreuk. `accounts.py` is één bestand voor vier protocollen. De klasse heet nog `ClaudeUI` en de socketopdracht heet nog `claude`, zodat bestaande tests en sneltoetsen niet breken. De pagina heet AI.

`curl | bash` voor Claude Code staat er nog (`ai_provider.py` regel 356). Codex en Gemini gaan via npm als npm er is. Ollama krijgt een URL, geen tweede pipe naar bash.

## Wisselen van AI

| Onderdeel | Claude Code | Codex | Gemini | Ollama |
|---|---|---|---|---|
| Gereedschap | `universe_mcp.py` | dezelfde | dezelfde | dezelfde, via `ollama_host.py` |
| Zenity voor mail, agenda, scherm | shell | shell | shell | shell |
| Buddy bij gereedschap | hooks | `UNIVERSE_AI_EVENTS` | idem | idem |
| Denken / klaar | hooks | geen | geen | `ollama_host.py` stuurt `think` en `done` |
| Brein-log van mail, agenda, scherm | shell | shell | shell | shell |
| Sleutel | aanmelden in het paneel, of `ANTHROPIC_API_KEY` in de sleutelbos | `OPENAI_API_KEY` of aanmelden | `GEMINI_API_KEY` of aanmelden | geen |
| Werkmap | `~/.local/share/universe-os/claude` | `…/ai/codex` | `…/ai/gemini` | `…/ai/ollama` |

De gebeurtenisnaam blijft `claude-event`, zodat de buddy niet opnieuw bedraad hoeft te worden. Codex en Gemini hebben geen prompt-start en prompt-stop. Hun eigen tekstinterface kan om toestemming vragen; die vraag is niet de grens.

Configuratie staat in `~/.config/universe-os/ai.json` (modus 0600): provider, model, Ollama-URL. Geen sleutels. Sleutels: gnome-keyring, service `universe-os`, account `ai-sleutel:<provider>`. De Ollama-URL mag alleen `http://127.0.0.1` of `http://localhost` zijn.

## Wat een niet-technische gebruiker echt moet doen

De pagina AI is: kies Claude, open het paneel, meld aan. Dat is de enige weg die zonder API-sleutel en zonder OAuth-client kan. ChatGPT en Gemini vragen een installatie via npm en een aanmelding of een sleutel. Ollama staat niet in Debian en een klein model volgt knoppen slecht. Gmail via OAuth is het zware pad; IMAP is het lichte. Schermbediening op een schone trixie typt met `wtype` en beweegt de muis vaak niet.

Dat is bruikbaar voor iemand die één keer wil aanmelden bij Claude. Het is niet “zet een vinkje en de computer doet de rest” zodra mail, muis of een lokaal model erbij komt.
