# Schakelaars en animatiekosten — 14 oktober

Vanaf main 92e9511, op expliciete opdracht Axel beide problemen onderzocht.

## Bevestigd in headless Chrome met echte stylesheets

`animation-layout.cjs` (Playwright, CHROME_BIN aanpasbaar) reconstrueert oud en nieuw:

| Meting | Voor | Na |
| --- | --- | --- |
| Schakelaar | 0 × 17 CSS px | 76 × 42 CSS px |
| Schakelaarbaan | 4 px | 76 px |
| CSS-overgang op `.sp-obj` | transform 150 ms | geen |

De inline span negeerde breedte/hoogte; display:inline-block en display:flex op het label werken ook buiten Controlecentrum. Klik op checkbox en 400px breed viewport slagen. Planeten zijn buttons en erfden de generieke transform-overgang, ondanks framegestuurde JS-projectie. Dit voegde visuele achterstand toe, geen gemeten FPS-cijfer.

Vervolgmeting: dezelfde browser verplaatst een planeet 12 frames met 15px per frame. Gemiddelde afwijking van de gevraagde positie vóór de fix 54,1 CSS px; erna 0. Dit bevestigt de CSS-achterstand in Chrome; native WebKit-frametijd blijft apart te meten. Op de host waren bouw- en test-VM op dat moment uit; Claude is gevraagd om een vrij testmoment.

## Kosten van schermvullende canvassen

Hemel en login-effecten tekenden tot DPR2, ook bij software-rendering. Nieuwe grens: software maximaal Full-HD-pixels; hardware maximaal 4K-pixels. CSS-geometrie, teksten en planeettexturen behouden hun eigen resolutie. Alleen effecten kunnen bij grote schermen zachter zijn.

`node docs/tests/canvas-budget.cjs`: Full HD DPR2 software 8.294.400→2.073.600 pixels; 4K DPR2 software 33.177.600→2.073.600. Full HD DPR1 blijft gelijk. Dit meet pixelwerk, niet totale frametijd.

Directe animatierenders annuleren bovendien een eventueel al ingeplande inputrender; eerder kon render() de handle wissen zonder de callback te annuleren, met extra renders als gevolg.

## Nog nodig

Native WebKit: 1920×1080 met gfx=soft, FPS/framecadans bij zoom/slepen, login/lock/logout en paneelschakelaars met Tab/Spatie; reduced/off. Vergelijk Full HD DPR1 (winst vooral overgang/extra renders) en HiDPI (ook pixelbudget). Controleer visuele effecten; geen hogere FPS claimen vóór meting. Geen nieuwe build/versie/publicatie door B.
