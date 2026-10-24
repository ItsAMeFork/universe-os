# Sneltoetsen in Universe OS (0.2.30)

Zoals in Windows. Systeemtoetsen staan in `pakket/universe-os/usr/share/universe-os/shortcuts.json`
(labwc `rc.xml` wordt daaruit gemaakt; aanpassen kan in het Controlecentrum). Win = de Windows-toets.

## Systeem (labwc)
| Toets | Wat |
|---|---|
| Win | Startmenu |
| Win+Tab | Taakweergave (open programma's en zoeken) |
| Win+R, Win+S | Uitvoeren / zoeken |
| Win+D, Win+M | Bureaublad tonen (nogmaals: vensters terug) |
| Win+E | Bestandsbeheer |
| Win+I | Controlecentrum (instellingen) |
| Win+F1 | Dit sneltoetsenoverzicht (op de pagina Sneltoetsen in het Controlecentrum) |
| Win+A | Bedieningspaneel |
| Win+C | AI (paneel) |
| Win+Escape | AI stoppen (scherm en automatisch toestaan) |
| Win+L | Vergrendelen |
| Win+V | Klembordgeschiedenis (laatste 25 teksten) |
| Win+. | Emoji kiezen (gaat op het klembord, plakken met Ctrl+V) |
| Win+pijltjes | Vensters links/rechts/kwart, maximaliseren, minimaliseren |
| Win+Shift+S, Shift+PrtSc | Schermafbeelding van een gebied |
| PrtSc | Schermafbeelding van het hele scherm |
| Alt+Tab, Alt+Shift+Tab | Wisselen tussen programma's |
| Alt+F4 | Venster sluiten |
| Ctrl+Shift+Esc | Taakbeheer (systeemmonitor) |
| Ctrl+Alt+Del | Menu: vergrendelen, afmelden, taakbeheer |
| Ctrl+Alt+T | Terminal |

## In programma's en in de Universe-pagina's
Ctrl+C kopiëren, Ctrl+X knippen, Ctrl+V plakken, Ctrl+A alles selecteren, Ctrl+Z ongedaan maken: werken in alle
GTK-programma's, invoervelden van de desktop (WebKit) en Chrome; labwc onderschept ze niet.
Ctrl+S/F/P/N/W/T (opslaan, zoeken, afdrukken, nieuw, tab sluiten, nieuwe tab) doen wat het programma ervoor heeft
(browser, teksteditor, bestandsbeheer). In bestandsbeheer (Thunar): F2 hernoemen, Del naar prullenbak,
Shift+Del definitief verwijderen.

## Niet zoals Windows
- Terminal: Ctrl+V plakt (nieuw), maar kopiëren is Ctrl+Shift+C, want Ctrl+C stopt daar een programma.
- Ctrl+Y (opnieuw) werkt alleen in programma's die het kennen; GTK gebruikt meestal Ctrl+Shift+Z.
- Klembordgeschiedenis bewaart alleen tekst, niet afbeeldingen.
