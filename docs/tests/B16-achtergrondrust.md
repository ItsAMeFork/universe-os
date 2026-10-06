# Achtergrondbelasting bij Chrome/installatie

Gebruiker meldt beeldproblemen en sterk vertraagd typen/installatie op zijn pc.
Nog geen diagnose van GPU, geheugen, CPU of geïnstalleerde versie beschikbaar.

🧪 De planeet-/gloedanimaties blijven voorheen achter normale programmavensters
lopen. Ze worden nu gepauzeerd zolang een niet-geminimaliseerd venster bestaat;
parallax plant dan ook geen nieuw frame. Na sluiten/minimaliseren hervat de
ruimtewereld. De afmeldanimatie wordt niet gepauzeerd. Geen Chrome-GPU-vlaggen
of beveiligingsinstellingen veranderd; geen oplossing van de beeldfout geclaimd.

Lokale test achtergrondrust.py controleert echte venster-change-methoden met
zichtbare/geminimaliseerde/gesloten vensters en meerdere achtergrondschermen.
Python/JavaScript-syntax en diffcontrole slagen.

Claude: meet CPU en invoervertraging vóór/na met Chrome en Calamares zichtbaar,
controleer herstel van animaties en Windows+D. Onderzoek echte pc met GPU/driver,
chrome://gpu, kernelmeldingen, geheugen/swap en installlog. VM-test alleen bewijst
niet dat de beeldfout op de echte videokaart opgelost is.
