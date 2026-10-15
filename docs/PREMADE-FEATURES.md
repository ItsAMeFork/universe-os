# Premade functies

Universe OS levert een kleine set Claude-subagents, vier commando's, een lokaal geheugen van wat werkte, en twee Brein-weergaven. Alles blijft op deze computer. Bevestigen blijft in `universe_mcp.py`, zenity (`confirm.py`) en automatisch toestaan.

Ruflo (ruvnet/ruflo, MIT) is de vergelijking. Vastgezet op **release 3.56.10**, commit `1882006a02487590c8c66a7eec8d7504f6af33c3` (opgehaald 15 oktober 2026). Plugin `ruflo-core` is daar **0.2.11**.

## Agenten

De bestanden staan in `/usr/lib/universe-os/claude/agenten/`. Een sessie werkt in `~/.local/share/universe-os/claude`. Aan-agents zijn symlinks in `.claude/agents` van die map. Uit halen verwijdert alleen onze symlink. Een echt bestand dat de gebruiker daar zelf zette blijft staan.

Op de pagina AI staat per agent een schakelaar. Standaard aan. De schakelaars zitten niet in de Claude-toegangslijst van de shell.

| Agent | Rechten | Bron |
| --- | --- | --- |
| reviewer | Read, Grep, Glob | Ruflo `plugins/ruflo-core/agents/reviewer.md`, MIT |
| tester | Read, Grep, Glob, Bash, Edit | Ruflo `plugins/ruflo-testgen/agents/tester.md`, MIT. Bash alleen voor tests |
| researcher | Read, Grep, Glob en lokaal zoeken | Ruflo `plugins/ruflo-core/agents/researcher.md`, MIT. Geen web |
| planner | Read, Grep, Glob | Eigen tekst. Geen Ruflo-bron |
| security-auditor | Read, Grep, Glob | Ruflo `plugins/ruflo-security-audit/agents/security-auditor.md`, MIT. Alleen een rapport |
| mail-assistent | mail, agenda, brein | Eigen tekst |
| opruimer | bureaublad en zoeken | Eigen tekst. Prullenbak via `bureaublad_bestand` |

Model is haiku. De aangepaste Ruflo-teksten laten weg: zwermen, `npx @claude-flow`, AgentDB, training, federatie en externe scanners.

## AI-activiteit

Het Brein heeft naast de nevel de weergave AI-activiteit. Die groepeert de bestaande tabel `acties` per taak (`taak_id`). Per taak zie je hulpmiddel, vraag, automatisch toestaan en mislukking.

Terugkijken markeert de opgeslagen rijen in volgorde. Exporteren schrijft een JSON in Downloads. Beide voeren niets opnieuw uit. Het antwoord bevat `afspelen: alleen terugkijken`.

## Wat werkte

Tabel `patronen` in `brein.db`, met FTS5. Per taaksoort: wat werkte, de les, tokens en stappen. Aan het begin van een prompt leest de hook hoogstens drie regels, samen ongeveer 180 tokens, en zet die als `additionalContext`. Dat is geheugen, geen opdracht.

Na elke taak schrijft `efficientie.py` een korte cijferregel, ook als de reflectie wordt overgeslagen. Lukt de goedkope reflectie, dan hangt `reflect.py` die zin aan de nieuwste regel van dat soort. URL's, adressen, sleutels en het woord wachtwoord gaan er niet in. De leszin gaat nog steeds door `efficientie.clean_lesson` (daar valt ook `mail` af, zodat een les niet om versturen vraagt).

## Workflows

Vier commando's, ook als skill. Geen zwerm: subagents na elkaar, in dezelfde sessie.

| Commando | Stappen |
| --- | --- |
| `/bouw` | planner, bouwen in de sessie, tester, reviewer |
| `/onderzoek` | researcher |
| `/opruimen` | opruimer |
| `/mail-ochtend` | mail-assistent |

Staat een agent uit, dan doet de hoofdsessie die stap zelf, met dezelfde rechten. Mail, wissen, installeren en het scherm gaan door de universe-hulpmiddelen.

## Taakbord

Tweede Brein-weergave. Een taak en stappen: todo, bezig, klaar, geblokkeerd. De hooks (`UserPromptSubmit`, gereedschap, subagent, `Stop`) vullen de rijen. Een geblokkeerde stap maakt de taak geblokkeerd. Overige todo-stappen blijven todo.

## Ruflo-modus

Uit, tot de gebruiker hem aanzet. Alleen dan, en alleen als `plugin.json` van ruflo-core echt in het aparte profiel staat, krijgt Claude `CLAUDE_CONFIG_DIR=~/.local/share/universe-os/claude-ruflo`. Zonder die plugin blijft de sessie bij het gewone Universe-profiel, zodat `~/.claude` niet wordt vervangen door een lege map.

Installeren opent een terminal. Het script doet een sparse checkout van alleen `plugins/ruflo-core` op de vastgezette commit, controleert naam en versie, en verwijdert elke andere pluginmap. Geen stille download.

Telemetrie, wolk en federatie staan uit (`DISABLE_TELEMETRY`, `DO_NOT_TRACK`, `RUFLO_TELEMETRY=off`, `RUFLO_CLOUD=off`, `RUFLO_FEDERATION=off`). `defaultMode: bypassPermissions` wordt geweigerd.

Elke Claude-start gaat door `universe-claude-wrap`, ook zonder Ruflo-modus. Die haalt `--dangerously-skip-permissions` en `--permission-mode bypassPermissions` weg. Headroom start die wrapper, niet `claude` zelf. Automatisch toestaan blijft de regel van Universe OS. De prullenbak bevat het woord `prullenbak`, dus automatisch toestaan laat die vraag staan.

## Vergelijking

| | Universe OS | Ruflo 3.56.10 |
| --- | --- | --- |
| Waar het draait | Alleen deze computer | Claude Code plus optionele wolk, daemon en federatie |
| Agenten | 7, kleine rechten, aan/uit | Grote catalogus, vaak sonnet, veel tools |
| Samenwerking | Subagents na elkaar | Zwerm, hive-mind, gedeelde workers |
| Geheugen | FTS5 in brein.db, klein budget | AgentDB, grafen, neurale training |
| Bevestigen | zenity en automatisch toestaan, bypass wordt gestript | Kan `--dangerously-skip-permissions` gebruiken |
| Telemetrie | Uit | Aanwezig in het project; wij zetten die uit in het aparte profiel |
| Omvang | De agentbestanden, vier commando's, twee schermen | Honderden plugins en MCP-hulpmiddelen |

Universe OS wint op de grens die voor een bureau telt: lokaal, weinig rechten, een vraag voordat er mail weggaat of iets in de prullenbak verdwijnt, en een scherm waarop je terugkijkt wat er gebeurde. Ruflo wint op schaal: meer agenten, een zwerm, een daemon en een geheugen dat over machines heen kan. Die schaal nemen we niet mee. De pagina AI zegt dat ook: Universe is de standaard, Ruflo-core mag er los bij.

## Brein-tijdlijn

Schermafbeeldingen plus tekstherkenning (tesseract, als die er is; anders alleen het beeld via grim). Uit tot de gebruiker hem aanzet. Pauze stopt meteen. Wissen haalt de beelden weg. Extra programma's kunnen op de uitsluitlijst. Wachtwoordbeheerders en bankieren staan vast uit, ook als die lijst leeg is. Na N dagen (standaard 7, hoogstens 90) verdwijnen oude beelden vanzelf. Zoeken gaat via FTS5 in `brein.db`. Het spoor in het Brein is een komeet: tijd, programma, herkende tekst. De AI krijgt deze beelden niet als hulpmiddel.

Geen Screenpipe. De licentie daarvan gebruiken we niet; dit is eigen code.

## Hé Buddy

Uit. openWakeWord 0.6.0 (Apache-2.0), whisper.cpp v1.9.5 (`d1be6fde11ac6e0407606b4e42fe72d34add8037`, model `ggml-base.bin` op revisie `5359861c739e955e79d9a303bcbc70fb988958b1`) en Piper 2023.11.14-2 (MIT) komen pas binnen als de gebruiker de terminalstart doet, in `~/.local/share/universe-os/stem`. De microfoon blijft dicht tot de schakelaar aan staat en die programma's er zijn. Met een eigen `hey_buddy.onnx` beoordeelt openWakeWord korte clips. Zonder dat bestand controleert whisper.cpp af en toe een korte opname op de woorden Hé Buddy, met pauze ertussen zodat de computer niet blijft rekenen. De zin erna gaat het paneel in; Enter blijft van de gebruiker. Er gaat geen audio naar een server.

## Ochtend-briefing

Mission Control leest wat al lokaal in het brein staat: komende agenda, belangrijke mail, diensten (afspraak met dienst, shift, ploeg of rooster) en open taken. De eerstvolgende afspraak wordt een aftelling, op het bureaublad en één keer 's ochtends bij de buddy. De schakelaar staat aan; uitzetten haalt de strook weg.

## Ghost-modus

Uit. Hoogstens een paar suggesties per dag, met minuten ertussen, en stil van 22:00 tot 07:30. Een afspraak binnen drie kwartier, een geblokkeerde stap of een doel dat op een vraag wacht. Niet nu en Nooit blijven gelden. Geen herhaling tot het zeuren wordt.

## Doelen

De gebruiker zet een doel. Daar komen stappen van op het taakbord (begrijpen, opdelen, doen, nakijken, of de regels die de gebruiker zelf schreef). Op de achtergrond staat uit. Aanzetten laat de volgende sessie één veilige stap zien; de buddy vult het paneel, de gebruiker drukt zelf op Enter. Betalen, wissen, wachtwoorden en belangrijke mail blijven todo en worden niet gestart.

## Zen en God

Blik op de pagina AI, opgeslagen als `aiBlik`. God is de standaard: het bureaublad blijft, en een hoek toont de laatste acties van de AI. Zen verbergt de taakbalk en de planeten. Overblijven de buddy en een invoerveld. De vraag gaat het paneel in; versturen doet de gebruiker met Enter.

## Wat we niet overnemen

Geen zwerm, geen hive-mind, geen daemon, geen federatie, geen cognitum, geen funnel, en niet de honderden MCP-hulpmiddelen. Geen Screenpipe. De security-auditor geeft geen exploit en geen payloads. Hé Buddy is geen aparte daemon: uit betekent dat de microfoon dicht blijft.
