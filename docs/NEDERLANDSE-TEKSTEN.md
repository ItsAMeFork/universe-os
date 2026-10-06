# Nederlandse teksten — B9

Broncodecontrole 2026-10-06: eigen schermen world/login/panel/overview/windows/
control en gedeelde audio/update-status gebruiken Nederlandse labels, uitleg en
fouten. Password:/Username: worden na trim vertaald. Programma- en apparaatnamen
blijven hun echte naam houden. Systeemfouten bij beheer, schaling en energie
beginnen nu met Nederlandse uitleg; de technische melding blijft beschikbaar.

Dit is een broncodecontrole, geen volledige visuele vertalingstest. Status 🧪.
Claude: doorloop installatie, login/fout/afmelden, alle kamers en instellingstegels
met nl_NL.UTF-8 en maak een lijst van resterende Engelse zichtbare teksten.

| Onderdeel | Bekende of nog te controleren beperking |
|---|---|
| Calamares | M1 meldt Engelse knoppen/teksten uit de meegeleverde upstream-vertaling; zie docs/tests/M1.md en PR #8. Eigen branding is Nederlands. |
| Wine / Windows-installers | Tekst wordt door Wine of het Windows-programma geleverd; Universe kan die niet algemeen vertalen. |
| Firefox / Chrome | Gebruik de Nederlandse taalvoorkeur; taalpakketten en de taal van websites zijn apart. De echte browsernaam blijft behouden. |
| GNOME Software / pavucontrol / Blueman / Thunar / terminal | Gebruik systeembibliotheken en vertaalcatalogi; volledige dekking moet in de nieuwe ISO worden gecontroleerd. |
| Hardware / tijdzones / logboeken | Productnamen, identifiers en technische logregels kunnen Engels blijven. |

Onvolledige upstream-vertalingen worden als beperking gemeld en niet vervangen
door een verzonnen succesmelding. Een programma dat een eigen taal kiest, kan
afwijken van de ingestelde Universe-sessietaal.
