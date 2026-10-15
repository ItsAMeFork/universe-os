---
description: Plan, bouw, test en review met subagents. Geen zwerm.
---

Voer /bouw uit als één sessie met subagents, na elkaar. Geen zwerm, geen gedeelde workers, geen daemon.

1. Subagent `planner`: een kort plan. Alleen lezen.
2. Bouw dat plan in deze sessie, in de thuismap. Geen sudo en geen wijziging in /usr of /etc.
3. Subagent `tester`: tests schrijven en draaien.
4. Subagent `reviewer`: alleen lezen, een kort rapport.

Elke stap die mail stuurt, iets wist, installeert of het scherm bedient, gaat door de universe-hulpmiddelen (`universe_mcp.py`). Die vragen via zenity, of volgen automatisch toestaan. Zet nooit een vlag die de toestemming overslaat. Staat een subagent uit op de pagina AI, doe die stap dan zelf met dezelfde grenzen.
