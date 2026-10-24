// Leesbaar overzicht van de sneltoetsen, getoond op de pagina Sneltoetsen van het Controlecentrum (alleen weergave).
// Bron van waarheid voor de toetsen zelf is shortcuts.json; deze lijst is de uitleg in gewone woorden. Houd beide gelijk.
export const OVERZICHT=[
 {titel:'Systeem',regels:[
  ['Win','Startmenu'],
  ['Win+Tab','Taakweergave (open programma\'s en zoeken)'],
  ['Win+R, Win+S','Uitvoeren / zoeken'],
  ['Win+D, Win+M','Bureaublad tonen (nogmaals: vensters terug)'],
  ['Win+E','Bestandsbeheer'],
  ['Win+I','Controlecentrum (instellingen)'],
  ['Win+A','Bedieningspaneel'],
  ['Win+L','Vergrendelen'],
  ['Win+V','Klembordgeschiedenis (laatste 25 teksten)'],
  ['Win+.','Emoji kiezen (gaat op het klembord, plakken met Ctrl+V)'],
  ['Win+C','AI (paneel)'],
  ['Win+Escape','AI stoppen (scherm en automatisch toestaan)'],
  ['Win+F1','Dit sneltoetsenoverzicht'],
  ['Win+pijltjes','Vensters links/rechts/kwart, maximaliseren, minimaliseren'],
  ['Win+Shift+S, Shift+PrtSc','Schermafbeelding van een gebied'],
  ['PrtSc','Schermafbeelding van het hele scherm'],
  ['Alt+Tab, Alt+Shift+Tab','Wisselen tussen programma\'s'],
  ['Alt+F4','Venster sluiten'],
  ['Ctrl+Shift+Esc','Taakbeheer (systeemmonitor)'],
  ['Ctrl+Alt+Del','Menu: vergrendelen, afmelden, taakbeheer'],
  ['Ctrl+Alt+T','Terminal']]},
 {titel:'In programma\'s en in de Universe-pagina\'s',regels:[
  ['Ctrl+C, Ctrl+X, Ctrl+V','Kopiëren, knippen, plakken'],
  ['Ctrl+A, Ctrl+Z','Alles selecteren, ongedaan maken'],
  ['Ctrl+S, Ctrl+F, Ctrl+P','Opslaan, zoeken, afdrukken (wat het programma ervoor heeft)'],
  ['Ctrl+N, Ctrl+W, Ctrl+T','Nieuw, tab sluiten, nieuwe tab'],
  ['F2','In bestandsbeheer: hernoemen'],
  ['Del, Shift+Del','In bestandsbeheer: naar de prullenbak, of definitief verwijderen']]},
 {titel:'Niet zoals Windows',regels:[
  ['Ctrl+V in de terminal','Plakt (nieuw); kopiëren gaat met Ctrl+Shift+C, want Ctrl+C stopt daar een programma'],
  ['Ctrl+Y','Opnieuw: werkt alleen in programma\'s die het kennen; GTK gebruikt meestal Ctrl+Shift+Z'],
  ['Klembordgeschiedenis','Bewaart alleen tekst, geen afbeeldingen']]}
];
