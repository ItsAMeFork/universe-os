# Lessen en plugins

Dit hoort bij de AI-pagina in het Controlecentrum. De bevestiging voor mail, agenda en scherm blijft in de shell, voor elk programma hetzelfde.

## Leren van een taak

Na een afgeronde taak komt er een rij in `brein.db`, tabel `efficientie`: programma, model, tokens in en uit, of dat een schatting is, aantal stappen, duur en een korte titel. De titel wordt leeg gemaakt als er een sleutel in lijkt te staan.

Waar de cijfers vandaan komen:

- Claude Code: het `usage`-veld in de hook of in het transcript (`--output-format json` heeft dezelfde velden). Geen `claude -p`. Dat zou het abonnement aanspreken en hoort niet bij dit ontwerp.
- Codex en Gemini: hun usage-object als het er is, anders een schatting uit de lengte van de tekst (`tekens / 4`), gemarkeerd als schatting.
- Ollama: `prompt_eval_count` en `eval_count` uit het antwoord. Ontbreken die, dan ook een schatting.

Een les (soort `les` in het brein) wordt alleen gevraagd als leren aanstaat, de taak minstens ongeveer 2000 tokens of 3 stappen was, de reflectie (ruim 400 tokens gereserveerd) kleiner is dan de taak, en de reflecties van de laatste zeven dagen onder 2500 tokens blijven. Het verzoek is één zin, hoogstens 180 uitvoertokens, zonder gereedschap. Het goedkoopste model van het actieve programma:

- Claude: `claude-haiku-4-5`, alleen met een API-sleutel in de sleutelbos
- Codex: `gpt-4.1-mini`, alleen met een API-sleutel
- Gemini: `gemini-2.5-flash`, alleen met een API-sleutel
- Ollama: `qwen2.5:3b` op deze computer

Zonder sleutel slaat Claude, Codex en Gemini de les over. Het gebruik blijft bewaard. Een les met een link, een adres of het woord versturen wordt niet opgeslagen. Een bijna gelijke les wordt niet nog eens toegevoegd.

Aan het begin van een sessie gaan hoogstens vier lessen mee, samen rond de 300 tokens, ontdubbeld. Staat leren uit, dan niet. De schakelaar staat op de pagina AI. De trend daar toont de laatste taken. In de Brein-nevel is een les een eigen ster en een filter in de lijst. Bewerken en verwijderen gaat met dezelfde knoppen als andere herinneringen.

Codex en Gemini hebben geen eigen stop-hook. Hun gebruik wordt bewaard zodra een transcript of usage-object binnenkomt; de Ollama-host en de Claude-hook doen dat zelf. Een sessie die geen van beide schrijft, telt niet mee.

## Plugins

Alles staat vast op een commit of een pakketversie (oktober 2026). Installeren haalt alleen die bestanden. Lukt het netwerk niet, dan blijft de status `later` en probeert de volgende start of de knop Plugins ophalen het opnieuw. Elke plugin is apart uit te zetten. Uitzetten haalt de snelkoppeling weg, niet meteen het bestand.

| Plugin | Bron | Vastgezet | Licentie | Staat | Wat wel | Wat niet |
|---|---|---|---|---|---|---|
| Superpowers | obra/superpowers | `bb92a7774141` | MIT | aan | de vaardigheden (`SKILL.md`) | de SessionStart-hook, die de hele tekst in elke sessie plakt |
| Everything Claude Code 2.2.3 | affaan-m/everything-claude-code | `c05b2d6614f6` | MIT | aan (drie vaardigheden) | `tdd-workflow`, `security-review`, `verification-loop` uit die tag | De knop Installeren voert `claude plugin marketplace add affaan-m/everything-claude-code` en daarna `claude plugin install ecc@ecc` uit, en verwijdert daarna `~/.claude/rules/ecc`. Regels worden niet gekopieerd en niet automatisch aangezet. De hooks uit de repo schrijven we niet in `settings.json`. Het officiële installatiecommando kan zelf hooks van de plugin aanzetten; dat is een rest van dat commando, niet iets dat Universe OS in de instellingen zet. De andere honderden vaardigheden gaan niet mee, anders wordt elke sessie duurder |
| Frontend design | anthropics/claude-code | `b0b7bed98203` | Apache-2.0 (de pluginmap; `SKILL.md` verwijst naar `LICENSE.txt`, dat bestand staat niet in de map) | aan | alleen `plugins/frontend-design/skills/frontend-design/SKILL.md` | geen extra hook. Installeren in een terminal: `claude plugin install frontend-design@anthropic-plugin-directory` |
| Headroom 0.40.0 | headroomlabs-ai/headroom | `855390d6110e` | Apache-2.0 | uit | `uv tool install "headroom-ai[all]==0.40.0"`. De wrapper `universe-ai-headroom` zet `HEADROOM_BEACON=off` en `DO_NOT_TRACK=1` en start `headroom wrap --code-memory none claude` | Het anonieme baken staat bij Headroom zelf aan; daarom altijd de wrapper, nooit `headroom` los. `--code-memory none` haalt Serena niet binnen via uvx. De grote schakelaar Tokens besparen (Headroom) staat uit, bovenaan de pagina AI en direct in het paneel. De stand (Uit of Aan) staat erbij. Minder tokens en goedkoper; de AI kan af en toe een detail missen. Alleen Claude. Niet tegelijk met de compressie van OmniRoute |
| OmniRoute 3.8.51 | diegosouzapw/OmniRoute | `c1e30b767697` | MIT | uit | `npm i -g omniroute@3.8.51`. Lokale gateway op `http://127.0.0.1:20128` | Blijft uit tot je zelf aanbieders toevoegt (een naam, geen adres). Gratis aanbieders kunnen je vragen lezen. De router stuurt alleen Claude (`ANTHROPIC_BASE_URL`) en Codex (`OPENAI_BASE_URL` op `/v1`) erheen. Gemini en Ollama blijven buiten de gateway. Compressie van OmniRoute staat alleen aan als Tokens besparen uit staat |
| Impeccable | pbakaus/impeccable | `2f98774f86bc` | Apache-2.0 | aan | de markdown-vaardigheid | de design-hook, die een programma uit de repo draait na een UI-wijziging |
| Design taste | Leonxlnx/taste-skill | `a60a36dc2bb3` | MIT | aan | `skills/taste-skill/SKILL.md` | de experimentele v2 en de scripts |
| Bestanden in de thuismap | `@modelcontextprotocol/server-filesystem@1.0.0` | servers `bbb701e7ac1e` | MIT (het project noemt een licentiewissel) | aan | argument is alleen de thuismap | andere schijven |
| Chrome DevTools | `chrome-devtools-mcp@1.10.1` | `bdc7e243a8d3` | Apache-2.0 | uit | geen sleutel nodig | een browser die het model kan sturen; binnen bubblewrap meestal zonder Wayland |
| Context7 | `@upstash/context7-mcp@4.4.1` | `2dcbb295e4a2` | MIT | uit | een sleutel is niet verplicht | elke documentvraag gaat naar context7.com |

De vaardigheden komen in `~/.claude/skills`, `~/.codex/skills` en `~/.gemini/skills`, als snelkoppeling naar `~/.local/share/universe-os/ai/plugins`. Ollama laadt die mappen niet zelf; de uitleg noemt alleen de namen. Codex, Gemini en Claude krijgen de MCP-regels in hun eigen config, naast `universe`. De Ollama-host praat alleen met `universe_mcp.py`.

Headroom en OmniRoute zijn programma's, geen markdown. Ze worden niet op de achtergrond gedownload. De knop Installeren opent een terminal met het vastgezette commando. Eén compressor tegelijk: `compressie` in `ai.json` is `geen` (standaard), `headroom` of `omniroute`. Zet je de ene aan, dan gaat de andere uit. Staat de router aan zonder OmniRoute-compressie, dan gaat `OMNIROUTE_COMPRESSION=off` mee, omdat OmniRoute anders zelf ook comprimeert.

Een sessie van Claude blijft bij Claude tot je OmniRoute of LiteLLM kiest. Dat zet alleen voor die sessie `ANTHROPIC_BASE_URL` op `http://127.0.0.1:20128` of op het LiteLLM-adres (`http://127.0.0.1:4000`, alleen deze computer). Terug naar Claude haalt het adres weg. OpenClaude staat niet in Universe OS. Een andere agent is OpenCode (MIT) of Goose (Apache-2.0), niet een afgeleide van Claude Code.

Automatisch toestaan staat uit. Kies 30 minuten, 1 uur, 2 uur of tot je het uitzet. Gewone vragen gaan dan zonder venster door en komen in Acties te staan. Een kort antwoord naar een bekend adres mag dan ook weg; de volledige tekst staat onder Acties. Belangrijke mail (de lijst met domeinen en woorden op de pagina AI, een nieuwe ontvanger, een bijlage, meer dan drie ontvangers, of iets dat het model als belangrijk markeert), betalen, wissen en wachtwoorden blijven in de wachtrij. Super+Escape zet de stand uit.

Claude in Chrome is de voorkeursroute voor de browser, en de weg naar Gmail en Outlook. De knop op de Internet-planeet en de knop op de pagina AI installeren Chrome uit de officiële apt-bron van Google, na een vraag, en openen de extensie. Een sessie van Claude start met `--chrome` zodra Chrome er is. Versturen, betalen, wissen, wachtwoorden en belangrijke mail blijven een vraag, ook als automatisch toestaan aan staat.

Paden met `..`, `hooks` of `rules` worden geweigerd. Er wordt geen hookbestand uit die repo's in de instellingen gezet. Het installatieprogramma weigert een `cp` en weigert een pad met `rules/`, behalve het verwijderen van `~/.claude/rules/ecc`.
