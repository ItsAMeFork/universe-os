# Claude in Universe OS (ontwerp, 11 oktober 2026)

Wens van Axel: "Claude direct in het besturingssysteem, met hulpmiddelen om alles te bedienen wat je ziet, mooie
overgangen zonder lag, en een 3D-personage dat over het scherm beweegt." Afgesproken in het cmd-gesprek (deel 1
goedgekeurd, deel 2 voorgelegd) en in de projectdraad verder uitgewerkt.

## Uitgangspunten
- **Het personage is het lichaam van Claude Code.** De gebruiker praat met de echte, ongewijzigde Claude Code in een
  paneel. Ons personage stuurt zelf nooit vragen naar Claude (geen `claude -p` op het abonnement van de gebruiker; dat
  verbieden de voorwaarden van Anthropic). Het personage reageert alleen op wat Claude Code doet (hooks).
- **Alleen met Claude Code.** Is `claude` niet geïnstalleerd, dan is er geen personage en geen paneel; het
  Controlecentrum toont dan "Claude Code installeren" (het officiële installatieprogramma van Anthropic). Universe OS
  levert Claude Code niet zelf mee.
- **Standaard Haiku:** `claude --model haiku --continue`. Met `/model` kiest de gebruiker zelf een ander model.
- **Niets draait voordat je het gebruikt.** Geen dienst op de achtergrond; de shell start alles pas bij Windows+C.

## Onderdelen
| Onderdeel | Bestand | Taak |
|---|---|---|
| Starter | `usr/bin/universe-claude` | controleert of `claude` er is, start Claude Code met Haiku, onze MCP-server, hooks en uitleg |
| OS-hulpmiddelen | `usr/lib/universe-os/claude/universe_mcp.py` | MCP-server (stdio, alleen standaardbibliotheek) met hulpmiddelen voor programma's, vensters, ruimtewereld, bestanden, instellingen, schermafbeelding en het tweede brein |
| Tweede brein | zelfde map, `brein.py` | één SQLite-database met FTS5 in `~/.local/share/universe-os/brein.db`: voorkeuren en notities (later: bestandsindex en tijdlijn) |
| Hooks | `usr/lib/universe-os/claude/universe-claude-hook` | Claude Code meldt elke stap; het script stuurt `claude-event <soort>` via `universe-ctl` naar de shell |
| Claude-paneel | shell, laag `claude` | glaspaneel rechts met een echte terminal (VTE) waarin Claude Code draait; Windows+C of klik op het personage |
| Personage | shell, laag `buddy` (`ui/buddy.*`) | klein doorzichtig venster dat meebeweegt en animaties speelt op de seintjes |

## Verbinding met de shell
De MCP-server en de hooks praten met de draaiende shell via de bestaande socket (`universe-ctl`):
- `call <naam> <json>` voert een vrijgegeven paginahandler uit (zoals `apps.launch`, `volume.set`, `windows.list`)
  en geeft JSON terug. Alleen een vaste lijst is toegestaan; afmelden, uitschakelen en installeren horen daar niet bij.
- `claude-event <soort> [json]` geeft een seintje aan het personage (luisteren, denken, hulpmiddel, toestemming, klaar).
- `claude` opent of sluit het Claude-paneel (Windows+C).

## Vooruitdenken (zonder AI)
Het personage stelt zelf dingen voor in een tekstballon met knoppen die het meteen regelen (`shell/buddy_hints.py`):
afgeronde download (openen, map tonen, .deb installeren), USB-stick (openen), batterij onder 15 % (scherm donkerder) en
gewoontes uit de tijdlijn ("Je opent rond deze tijd vaak Firefox"). Elke ballon heeft ook "Vraag Claude" (zet een
vraag klaar in het paneel; de gebruiker verstuurt met Enter), "Niet nu" (rest van de dag) en "Nooit". Antwoorden staan
in het brein (tabel hints). Het personage stuurt zelf nooit iets naar Claude.

## Tweede brein
- Herinneringen, tijdlijn (30 dagen, programma's en bestanden die via Universe geopend worden) en antwoorden op
  suggesties: SQLite in `~/.local/share/universe-os/brein.db`.
- De planeet Brein toont die herinneringen als een nevel (sterren, sterrenbeelden via gedeelde woorden in FTS5,
  komeetspoor). Controlecentrum → Beveiliging laat zien wat er staat, exporteert JSON en kan alles vergeten.
- Inhoud van je bestanden: **Recoll** (Debian-pakket, Xapian, offline), aanbevolen pakket. Index van de eigen mappen,
  elk half uur bijgewerkt op laagste prioriteit (niet op een bijna lege batterij). Zonder Recoll: zoeken op bestandsnaam.
- Onderzocht en afgevallen: mem0/OpenMemory en Khoj (te zwaar, LLM nodig), basic-memory (Python 3.12, AGPL), de
  MCP-memory-referentieserver (niets extra), localsearch (zwaarder dan Recoll).

## Hooks en personage
| Claude Code (hook) | Personage |
|---|---|
| UserPromptSubmit | luistert, daarna denkt het |
| PreToolUse | gaat aan het werk; bij een Universe-hulpmiddel loopt het naar die plek (planeet of taakbalk) |
| PostToolUse | klaar met die stap, weer denken |
| Notification (toestemming nodig) | steekt een hand op; het paneel komt naar voren |
| Stop | blij gebaar, terug naar zijn plekje |

## Zonder lag
- Personage = klein venster (geen laag over het hele scherm); bewegen = de marge van dat venster verschuiven.
- Het personage staat stil als er een programma op de voorgrond staat (zelfde regel als de ruimtewereld).
- Claude Code stopt 10 minuten nadat het paneel dicht is.
- Animaties volgen de instelling "animaties" en remmen zichzelf af op trage computers, zoals bij inloggen.

## Persoonlijke assistent (mail, agenda, scherm)

De gebruiker koppelt accounts één keer in Controlecentrum → Accounts. Claude Code
gebruikt daarna dezelfde sessie, via de MCP-hulpmiddelen van `universe_mcp.py`.
Die praten alleen met de shell (`universe-ctl call`), op een vaste lijst.

| Hulpmiddel | Wat het doet | Toestemming |
|---|---|---|
| `mail_search`, `mail_read`, `mail_draft` | zoeken, lezen, concept | concept schrijft, verstuurt niet |
| `mail_send` | versturen | kort antwoord naar een bekend adres mag mee als automatisch toestaan aan staat; belangrijke mail blijft een vraag |
| `calendar_list` | komende afspraken | lezen |
| `calendar_create` | afspraak zetten | altijd een venster met titel, begin, einde en plek |
| `scherm_muis`, `scherm_klik`, `scherm_typ`, `scherm_toets`, `scherm_scroll`, `scherm_focus` | scherm overnemen | alleen als "AI mag scherm bedienen" aan staat voor deze aanmelding |

`scherm.toestaan` staat niet op de lijst die Claude mag aanroepen. De schakelaar zit
in het Controlecentrum. Super+Escape (`universe-ctl scherm-stop`) zet hem uit.

Gmail en Outlook gaan via Claude in Chrome (`claude --chrome` en de officiële extensie). De gebruiker logt in in zijn eigen Chrome. Er is geen OAuth-client. IMAP en OAuth blijven een extra weg.

Invoer op labwc: `wtype` voor toetsen (protocol van de compositor), `python3-evdev`
via `/dev/uinput` voor muis en scroll. `ydotool` heeft voorrang als `ydotoold` draait;
dat pakket zit in Debian 13 alleen in backports, daarom is het geen harde afhankelijkheid.
`xdotool` wordt niet gebruikt.

Geheimen: `python3-keyring` naar gnome-keyring. `brein.db` bewaart de naam, het adres,
de rechten, een korte mail- en agendasamenvatting, en het actielogboek
(goedgekeurd, geweigerd, uitgevoerd, mislukt). Geen wachtwoord, geen token.
Een wachtwoord dat Claude in een veld typt komt ook niet in dat logboek; het veld
moet als `wachtwoord` of `betaling` worden aangegeven, en dan komt er eerst een vraag.

De Brein-nevel tekent mail, agenda en acties als extra sterren (blauw, geel, roze)
en toont ze in de lijst, filterbaar. Dat blijft op deze computer.

## Veiligheid
Claude Code vraagt zelf toestemming. Wij geven alleen alleen-lezen-hulpmiddelen vooraf vrij (lijsten, zoeken,
status, brein lezen). Openen, instellingen wijzigen, vensters sluiten en het brein beschrijven vragen toestemming.
Versturen, afspraken maken, en gevoelige schermacties (wissen, betalen, wachtwoordveld) hebben daarbovenop een
eigen venster in de shell. Zonder antwoord "Toestaan" gebeurt de actie niet, ook niet als het hulpmiddel
rechtstreeks wordt aangeroepen.

De toestemming van Claude Code zelf is geen grens. Die geldt alleen voor dat ene programma, en een terminalopdracht
loopt eromheen. De grens zit in de shell en in `universe_mcp.py`: `call` op de socket alleen vanaf dat bestand,
schermtoestemming alleen in het geheugen van de shell na een venster, geen invoer naar een terminal, en bubblewrap
zodat het programma de sleutelbos en `/dev/uinput` niet zelf pakt. Zie `docs/REVIEW-AI-STACK.md`.

## Wisselen van AI
Controlecentrum → AI kiest het programma in het paneel: Claude Code (standaard), Codex (ChatGPT), Gemini of Ollama.
Alle vier gebruiken dezelfde `universe_mcp.py`. Ollama spreekt zelf geen MCP; `ollama_host.py` is alleen de client
ernaartoe. OpenCode (MIT) en Goose (Apache-2.0) zijn optioneel, niet de standaard. Hun eigen toestemmingssysteem is niet de grens; de vragen op het scherm blijven van de shell. Zet hun computer-besturing niet aan.
Hooks van Claude Code blijven voor luisteren, denken, toestemming en klaar. Bij de andere programma's stuurt de
MCP-server de seintjes voor hulpmiddelen (`UNIVERSE_AI_EVENTS`); luisteren en klaar komen bij Ollama uit de host.
Codex en Gemini hebben dat begin- en eindseintje niet. Sleutels staan in de sleutelbos (`ai-sleutel:<programma>`),
niet in `ai.json`.

## Lessen en plugins
Na een taak schrijft de shell het tokengebruik in `brein.db` (tabel `efficientie`). Een korte les (soort `les`) komt er alleen als die goedkoper is dan de taak en het weekbudget nog ruimte heeft. Dat gaat via de goedkoopste API van het gekozen programma, nooit via `claude -p`. Zonder API-sleutel slaat Claude, Codex en Gemini de les over; het gebruik blijft wel bewaard. Ollama kan lokaal reflecteren. De pagina AI toont een trend en een schakelaar. Lessen zijn sterren in het brein, te filteren, te bewerken en te verwijderen.

Plugins zijn een vastgezette, bekeken set. Hooks en regelpakketten van derden gaan niet aan. Chrome DevTools en Context7 staan uit tot de gebruiker ze aanzet, omdat de een een browser bestuurt en de ander vragen naar context7.com stuurt. Frontend design (officieel, Apache-2.0) staat aan als vaardigheid. Everything Claude Code 2.2.3 installeer je met de marketplace-opdracht; regels worden daarna niet aangezet. Headroom (tokens besparen, baken uit) staat uit. De schakelaar Tokens besparen (Headroom) staat groot op de pagina AI en ook in het paneel, met de stand Uit of Aan. Minder tokens en goedkoper; de AI kan af en toe een detail missen. OmniRoute (lokale router op poort 20128) staat uit.

Een Claude-sessie kan naar OmniRoute of naar LiteLLM (`http://127.0.0.1:4000`) wijzen via `ANTHROPIC_BASE_URL`. Terug naar Claude haalt dat adres weg. OpenClaude wordt niet gebruikt: het is een ongeautoriseerde afgeleide en stuurt standaard via een betaalde gateway, met zoeken via Exa. Een andere agent, als je die wilt, is OpenCode (MIT) of Goose (Apache-2.0). Van Headroom en OmniRoute comprimeert er hoogstens één, en gratis aanbieders via OmniRoute kunnen je vragen lezen. Zie `docs/AI-PLUGINS-EN-LESSEN.md`.

Automatisch toestaan staat uit. De schakelaar staat op de pagina AI en in het bedieningspaneel, met een duur van 30 minuten, 1 uur, 2 uur of tot je het uitzet. Daarna gaat hij zelf uit. Gewone bevestigingen (programma openen, bestanden, concepten, agenda lezen) gaan dan door. Betalen, wissen, versturen, wachtwoorden en systeemwijzigingen worden niet uitgevoerd; ze wachten in het brein onder Acties. Waar het kan, staat er Ongedaan maken. Super+Escape zet de stand direct uit. Zolang hij aan staat, is er een balk op het scherm.

## Fasen
1. **Deze stap:** starter, MCP-server met hulpmiddelen en brein (notities en voorkeuren), hooks, socketopdrachten,
   paneel met terminal, eenvoudig tijdelijk personage. Testen in de VM.
2. Gedaan: bestandsindex (Recoll), tijdlijn, suggesties met tekstballon, Disney-principes in de bewegingen.
3. **Vervolgproject:** ("Claude motion" bestaat niet als tool; Remotion/animation-studio maken alleen video's) het echte personage in Disney-stijl, als vooraf gerenderde animaties (geen live 3D), dat zonder
   andere aanpassingen het tijdelijke figuurtje vervangt.

## Open punten
- Of Claude Code in een eigen paneel tonen mag bij verspreiden: Axel vraagt dat eventueel na bij Anthropic.
- labwc geeft geen vensterposities door: bij vensters loopt het personage naar het pictogram in de taakbalk.
