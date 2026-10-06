# Nieuwe programma’s als planeten

🧪 Vanaf de eerste registratie van deze functie wordt per account een baseline
van bestaande zichtbare .desktop-programma’s bewaard. Nieuw geregistreerde
programma’s worden startbare planeten op het bureaublad, ook Wine-snelkoppelingen.
Bestaande vooraf geïnstalleerde programma’s blijven in Applicaties; er worden
niet ineens tientallen systeemhulpmiddelen op het bureaublad toegevoegd.
Gio.AppInfoMonitor signaleert installatie/verwijdering, met 300 ms bundeling.
Verwijderde programma’s verdwijnen; opgeslagen planeten blijven na herlogin.

De zes werelden blijven bestaan. Extra planeten staan in een horizontaal
scrollbare strook; hun canvas is klein en heeft geen continue animatie. Kamers
verbergen de strook en maken hem inert. Klik/Tab/Enter start via apps.launch.

Lokale reconciliatietests, JS/Python-syntax en diffcontrole. Native Gio-monitor,
installeren/verwijderen/Chrome/Wine, meerdere schermen, herlogin en 1024×768/4K
moeten door Claude worden getest. PR is afhankelijk van menu-review #27.
