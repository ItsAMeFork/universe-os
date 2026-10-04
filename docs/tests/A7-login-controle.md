# A7 — echte aanmelding (nog niet getest in de test-VM)

De GTK-greeter gebruikt LightDM/PAM voor het echte accountwachtwoord. Universe OS levert geen eigen wachtwoorddatabase of standaardwachtwoord.

Wijzigingen:
- LightDM, de GTK-greeter en de X-server zijn verplichte onderdelen; de greeter gebruikt X, de Universe-sessie Wayland.
- Handmatig een gebruikersnaam invoeren is mogelijk; gastlogin is uitgeschakeld.
- Calamares schrijft op de doelschijf een expliciete configuratie zonder automatische aanmelding en schakelt LightDM en graphical.target in.
- Het account en wachtwoord worden door de gebruiker tijdens de installatie gekozen.

Nog vereist in een aparte test-VM:
1. ISO opstarten en installeren met een nieuw account en wachtwoord.
2. Herstarten zonder ISO: de GTK-greeter moet zichtbaar zijn, zonder automatische aanmelding.
3. Een fout wachtwoord moet worden geweigerd; het juiste wachtwoord moet Universe OS starten.
4. Afmelden moet terugkeren naar de greeter; herstarten moet opnieuw om het wachtwoord vragen.
5. Controleer de herstelmodus en een tweede gebruikersaccount.

Geen van deze functionele tests is hier als geslaagd gemarkeerd. A7 blijft 🧪.

## Uitgevoerde bouwcontroles

Op 4 oktober 2026 gecontroleerd in de Debian-bouwomgeving:
- PyYAML leest de Calamares-configuratie succesvol (9 installeropdrachten).
- scripts/build-deb.sh bouwt het Debian-pakket succesvol met LightDM, GTK-greeter en xserver-xorg in Depends.
- git diff --check geeft geen whitespacefouten.

Dit zijn bouwcontroles; de aanmelding met fout en juist wachtwoord is nog niet functioneel getest.
