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

## Veiligheid
Claude Code vraagt zelf toestemming. Wij geven alleen alleen-lezen-hulpmiddelen vooraf vrij (lijsten, zoeken,
status, brein lezen). Openen, instellingen wijzigen, vensters sluiten en het brein beschrijven vragen toestemming.

## Fasen
1. **Deze stap:** starter, MCP-server met hulpmiddelen en brein (notities en voorkeuren), hooks, socketopdrachten,
   paneel met terminal, eenvoudig tijdelijk personage. Testen in de VM.
2. Tweede brein uitbreiden: bestandsindex (elk half uur, laagste prioriteit) en tijdlijn van 30 dagen.
3. **Vervolgproject:** het echte personage in Disney-stijl, als vooraf gerenderde animaties (geen live 3D), dat zonder
   andere aanpassingen het tijdelijke figuurtje vervangt.

## Open punten
- Of Claude Code in een eigen paneel tonen mag bij verspreiden: Axel vraagt dat eventueel na bij Anthropic.
- labwc geeft geen vensterposities door: bij vensters loopt het personage naar het pictogram in de taakbalk.
