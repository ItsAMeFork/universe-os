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
| Everything Claude Code | affaan-m/ECC | `b92f181b3b74` | MIT | aan | `tdd-workflow`, `security-review`, `verification-loop` | `claude plugin install ecc@ecc` zou de hooks meenemen (scripts uit de repo bij elke tool). Regels kopieert die plugin niet; die blijven ook uit. De andere honderden vaardigheden ook, anders wordt elke sessie duurder |
| Impeccable | pbakaus/impeccable | `2f98774f86bc` | Apache-2.0 | aan | de markdown-vaardigheid | de design-hook, die een programma uit de repo draait na een UI-wijziging |
| Design taste | Leonxlnx/taste-skill | `a60a36dc2bb3` | MIT | aan | `skills/taste-skill/SKILL.md` | de experimentele v2 en de scripts |
| Bestanden in de thuismap | `@modelcontextprotocol/server-filesystem@1.0.0` | servers `bbb701e7ac1e` | MIT (het project noemt een licentiewissel) | aan | argument is alleen de thuismap | andere schijven |
| Chrome DevTools | `chrome-devtools-mcp@1.10.1` | `bdc7e243a8d3` | Apache-2.0 | uit | geen sleutel nodig | een browser die het model kan sturen; binnen bubblewrap meestal zonder Wayland |
| Context7 | `@upstash/context7-mcp@4.4.1` | `2dcbb295e4a2` | MIT | uit | een sleutel is niet verplicht | elke documentvraag gaat naar context7.com |

De vaardigheden komen in `~/.claude/skills`, `~/.codex/skills` en `~/.gemini/skills`, als snelkoppeling naar `~/.local/share/universe-os/ai/plugins`. Ollama laadt die mappen niet zelf; de uitleg noemt alleen de namen. Codex, Gemini en Claude krijgen de MCP-regels in hun eigen config, naast `universe`. De Ollama-host praat alleen met `universe_mcp.py`.

Paden met `..`, `hooks` of `rules` worden geweigerd. Er wordt geen hookbestand uit die repo's in de instellingen gezet.
