# Menu- en animatiereview

🧪 Concrete broncodebevindingen en reparaties:
- Bestanden zoeken liep via `search` op de GTK-thread, tot 0,8 s scan per invoer.
  Overzicht gebruikt nu de bestaande worker-route `search.files` (handler toegevoegd),
  hergebruikt de programmalijst en wacht 180 ms na typen. Wissen/nieuwe invoer maakt
  oude resultaten ongeldig. Enter kan daardoor geen oude zoekresultaten openen.
- Afbreken met Escape tijdens reizen kon na de timer alsnog een kamer openen.
  Reistoken verhindert dit; configuratiewijziging herstelt ook inert/zichtbaarheid.
- Kamerlaadfouten worden getoond. Venster-sluiten is nu een echte focusbare knop,
  naast openen, zonder interactieve knop in een andere knop.
- Paneel heeft groepen, uitklapbare audio/updateopties die pas bij openen ophalen,
  directe bediening, bescherming tegen snelle open/sluit-antwoorden, behoud van
  focus/scroll en één statusverzoek tegelijk. Volumeschuif stuurt alleen de nieuwste
  waarde met maximaal één opdracht tegelijk. Ontbrekende audio schakelt dempen uit.

Lokale syntax/diffchecks en tests focus.mjs/menu-requests.mjs; geen native
WebKit/compositor- of echte-hardwaretest. Claude: snel typen/wissen/Enter,
installeren terwijl overzicht open is, Escape tijdens reizen, snelle paneltoggle,
Tab/Shift+Tab en sluiten van vensters, volumeschuif/fout, grote tekst/1024×768/4K,
updates en audio uitklappen testen. Hardwarelag/Chrome-GPU nog apart onderzoeken.
