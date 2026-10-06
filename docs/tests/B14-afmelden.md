# B14 afmelden — 2026-10-06

🧪 Planeet vormt zich boven alle vensters op alle schermen, daarna gewone
labwc-afmelding en LightDM-login. Verminderde/uitgeschakelde animatie slaat de
beweging over. Afmelden wacht maximaal 1,8 seconde op het UI-antwoord; een
startfout herstelt de ruimtewereld en toont de fout. Niet-opgeslagen werk wordt
nog steeds vooraf in het paneel gemeld.

Lokale controle: docs/tests/afmelden.py test de echte Python-methoden met
gesimuleerde GTK/backend: dubbele verzoeken, timer, één exit en fout-herstel.
Python/JS-syntax en diffcontrole slagen.

Claude: test na echt inloggen met open vensters, meerdere schermen, alle
animatieniveaus en opnieuw inloggen. Onderbreek de JS-callback en controleer de
timeout. Visuele aansluiting op greeter en werkelijke sessiebeëindiging moeten
nog in de VM bewezen worden.
