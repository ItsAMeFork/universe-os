# Universe OS gebruiken

Deze handleiding beschrijft de huidige interface in de integratiebranch. Nieuwe
wijzigingen moeten nog in de volgende ISO en op echte hardware worden getest.

## Aanmelden en afsluiten

Vul je bestaande gebruikersnaam in, kies Verder en vul je wachtwoord in. Een
juist wachtwoord opent de ruimtewereld via de imploderende planeet. Andere
gebruiker brengt je terug naar de gebruikersnaam. Foute accounts/wachtwoorden
geven geen toegang. Rechtsonder kun je zonder aanmelden afsluiten, herstarten
of slaapstand kiezen. Niet-beschikbare acties zijn grijs met uitleg. Slaapstand
is slapen in het geheugen; dit is geen sluimerstand op schijf.

Windows+A opent het bedieningspaneel met Afmelden, Vergrendelen en energieacties.
Afmelden sluit je sessie: sla werk eerst op. De planeet vormt zich terug; daarna
komt het inlogscherm. Vergrendelen houdt je programma’s open en gebruikt het
beveiligde vergrendelscherm. Ontgrendel met je eigen wachtwoord. Universe heeft
geen vast algemeen administratorwachtwoord; het installatieaccount bepaalt je
inloggegevens en beheerdersrechten.

## Navigeren

Klik een planeet, gebruik Tab/Shift+Tab en Enter, of druk 1–6. Pijltjestoetsen
kiezen een planeet. Escape of Terug naar de ruimte sluit een kamer. Binnen een
kamer blijft Tab bij de bediening; achtergrondplaneten krijgen geen focus.

| Toets | Actie |
|---|---|
| Windows | Programma’s, vensters en bestanden zoeken |
| Windows+D | Ruimtewereld tonen; nogmaals herstelt geminimaliseerde vensters |
| Windows+A | Bedieningspaneel |
| Windows+E | Bestandsbeheer |
| Windows+I | Controlecentrum |
| Windows+L | Vergrendelen |
| Alt+Tab | Wisselen tussen programma’s |
| Alt+F4 | Actief venster sluiten |
| Ctrl+Alt+T | Terminal |
| Print / Shift+Print | Schermafbeelding van scherm / gekozen gebied |

Sneltoetsen kunnen worden aangepast in Controlecentrum > Sneltoetsen.

## De zes werelden

Thuiswereld bevat je persoonlijke mappen en accountinstellingen. Applicaties
bevat geïnstalleerde programma’s, zoeken en Windows-programmabeheer.
Softwarewinkel opent de softwarebeheerder voor programma’s en updates.
Controlecentrum bevat instellingen voor netwerk, geluid, beeldschermen, taal,
energie, accounts, sneltoetsen en beveiliging. Gamehal toont geïnstalleerde games.

Communicatie toont geïnstalleerde chat/mailprogramma’s en de Chrome-tegel.
Universe OS heeft nog geen eigen chatdienst of chataccount; er wordt geen Space
Chat of Matrix-dienst automatisch gekoppeld. Je kiest zelf een dienst via een
geïnstalleerd programma of website. Een lege lijst betekent dat er nog geen
communicatieprogramma gevonden is, niet dat Universe een chataccount heeft.

Chrome wordt van Google gedownload bij de eerste start van het geïnstalleerde
systeem met internet, ook op een verbinding met datalimiet zoals gekozen door
Axel. De tegel toont wachten/downloaden/fout en wordt pas bruikbaar als het
programma beschikbaar is. Downloadstatus vernieuwen controleert de status;
dit is geen knop om een tweede installatie te starten. Zonder Chrome kun je een
al aanwezige browser vanuit Applicaties gebruiken. Chrome krijgt daarna updates
via de Google-pakketbron. De live-USB installeert Chrome niet automatisch.

## Netwerk en geluid

Het paneel en Netwerk in het Controlecentrum tonen de waarneming van
NetworkManager: wifi uit, niet verbonden, geen herkend apparaat, verbonden
zonder bevestigd internet of verbonden met internet. Een netwerk kan eerst
aanmelding op een website vereisen. Onbekende internettoegang blijft onbekend.
Geen apparaat is geen bewijs dat een specifieke driver ontbreekt; controleer
dan kabel, adapter, driver en firmware. Netwerkinstellingen zijn via het paneel
bereikbaar. Verbindingsproblemen vragen soms hardwareonderzoek door spoor A.

Geluidsuitgang toont beschikbare analoge, HDMI/DisplayPort-, USB- en
Bluetooth-uitgangen en de actieve uitgang. Kies een uitgang en Deze uitgang
gebruiken. Vernieuw de lijst na aansluiten/loskoppelen. WirePlumber beheert het
bewaren van de standaardkeuze. Een niet-actief kaartprofiel verschijnt mogelijk
pas na inschakelen bij Apparaten beheren (pavucontrol). Bluetooth eerst koppelen.
Geluid via een losse videokaart gebruikt diens HDMI/DisplayPort-uitgang; er is
geen vast videokaartmodel in de interface ingesteld.

## Updates

Nu controleren ververst de echte pakketlijst via PackageKit. De interface
onderscheidt geen updates, beschikbare updates, een oude lijst en een mislukte
controle. Een softwarevenster openen is geen bewijs dat updates geïnstalleerd
zijn. Gebruik de softwarebeheerder om beschikbare updates te installeren.
Zonder internet of met verkeerde tijd kan een controle mislukken. Een oude
melding kan van de softwarebeheerder komen; controleer de laatste geslaagde
verversing, verbinding en klok.

Debian-pakketten komen uit Debian- en Debian Security-bronnen. Chrome gebruikt
Google. Universe OS heeft nog geen eigen distributiebron voor nieuwe
interfaceversies: die zijn niet automatisch gelijk aan Debian-updates.

## Windows-programma’s

Open .exe/.msi via Windows-programma installeren of open Windows-programma’s
beheren in Applicaties. Controleer bestand en ondersteuning en bevestig zelf.
Installatie en daadwerkelijke werking zijn aparte toestanden: een afgeronde
installer bewijst niet dat het programma werkt. Wine is geen beveiligingssandbox.
Elk programma heeft een eigen omgeving. Beheer biedt starten, logboeken,
Wine-instellingen en verwijderen, met een aparte keuze voor gegevens wissen.
Niet elk Windows-programma, stuurprogramma, spel of ARM-bestand wordt ondersteund.

## Leesbaarheid en beweging

Controlecentrum > Weergave en toegankelijkheid laat tekstgrootte,
interfacegrootte en animaties aanpassen. Volledig, verminderd en uit hebben
verschillende bewegingsniveaus. De interface respecteert ook verminderde
beweging van de omgeving. Toetsenbordfocus heeft een turquoise rand.
Kamers/instellingen zijn scrollbaar. Bij grote tekst of kleine schermen blijft
scrollen nodig; 1024×768 t/m 4K moet in de VM worden gecontroleerd.
Volledige schermlezerondersteuning is nog niet bewezen.

## Problemen melden

Noteer welke knop, melding en handeling het probleem geeft en of je vanaf de
live-USB of het geïnstalleerde systeem werkt. Voeg zo mogelijk een foto toe.
Shell-/sessielogboeken staan in ~/.local/state/universe-os/. Deel geen
wachtwoorden, sleutels of persoonlijke gegevens. Bij een vastlopende shell
kunnen open programma’s blijven bestaan; herstelmodus is een aparte sessieoptie.
Bekende vertaalbeperkingen staan in NEDERLANDSE-TEKSTEN.md.
