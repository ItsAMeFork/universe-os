# Test planeet-inlogscherm `universe-greeter` (PR #7, spoor B; getest door spoor A)

**Datum:** 4 oktober 2026. **Systeem:** geïnstalleerd vanuit ISO `230a70c5…`, test-VM 1280×800, account `tester`.
In `/etc/lightdm/lightdm.conf` met de hand `greeter-session=universe-greeter` gezet (zie M1.md: Calamares overschreef het).
Schermafbeeldingen in `docs/tests/greeter/`.

| Test | Uitkomst |
|---|---|
| Greeter start onder LightDM zonder vensterbeheerder, vult het scherm, focus zichtbaar | ✅ `greeter-1-start.png` |
| Fout wachtwoord | ✅ geweigerd, "Aanmelden mislukt. Controleer je account en wachtwoord.", geen overgang — `greeter-2-fout.png` |
| Onbekend account | ✅ geweigerd met dezelfde melding — `greeter-6-onbekend.png` |
| Juist wachtwoord | ✅ formulier verdwijnt, planeet implodeert, daarna de ruimtewereld — `greeter-5-implosie.png` |
| Afmelden | ✅ terug naar het planeet-inlogscherm (omgekeerde animatie nog niet gebouwd) |
| **"Andere gebruiker" tijdens de wachtwoordvraag** | ❌ "Annuleren is nog niet bevestigd"; daarna geeft elke poging "De aanmelding wordt al gecontroleerd" en is de knop weg. **Niemand kan meer inloggen** tot LightDM herstart — `greeter-3-annuleren.png`, `greeter-4-vast.png` |

**Kleinere punten:**
- Het veld "Wachtwoord" is zichtbaar vóór de gebruikersnaam is verstuurd (het `hidden`-attribuut wordt door CSS overschreven).
- De PAM-vraag verschijnt als Engels "Password:"; tijdens de vraag staat er al "Aanmelding controleren…".

**Conclusie:** de kern werkt (echte PAM-controle, weigeren zonder overgang, implosie alleen na succes). Door de
blokkerende fout bij "Andere gebruiker" blijft de GTK-greeter de standaard tot dat is opgelost.

## Hertest na commit `7550feb` (4 oktober 2026, 19:15)

`greeter.py`, `login.js` en `login.css` uit `7550feb` in hetzelfde geïnstalleerde systeem gezet, LightDM herstart.

| Test | Uitkomst |
|---|---|
| Wachtwoordveld verborgen tot de gebruikersnaam is verstuurd | ✅ `greeter-7-zonder-wachtwoordveld.png` |
| Geen "Aanmelding controleren…" tijdens de wachtwoordvraag | ✅ |
| "Andere gebruiker" tijdens de wachtwoordvraag | ✅ terug naar de gebruikersnaam — `greeter-8-andere-gebruiker.png` |
| Daarna ander account (`bestaatniet`), opnieuw "Andere gebruiker", dan `tester` + juist wachtwoord | ✅ geen blokkade, ruimtewereld opent — `greeter-9-na-wisselen.png`, `greeter-10-ingelogd-na-wisselen.png` |
| PAM-vraag in het Nederlands | ❌ nog "Password:" (waarschijnlijk stuurt PAM `"Password: "` met spatie; de opzoektabel vergelijkt exact) |

**Conclusie:** de blokkerende fout is opgelost. De greeter kan de standaard worden; alleen de vertaling van de PAM-vraag
is nog open (niet blokkerend). Omgekeerde animatie bij afmelden is nog niet gebouwd.

## Derde ronde: vers geïnstalleerd systeem (4 oktober 2026, 21:10)

**ISO:** SHA-256 `50420d62779a90492a7553dc4db2ab2e3b18f7ac53defd50d9ed38eb0757e3b7`, testkopie `0606bdb` =
`spoor-a/A9-iso-bouw` + PR #3, #4 (met `greeter-session=universe-greeter`), #6, #7 (t/m `d7c254f`), #8. Geen handwerk.

| Test | Uitkomst |
|---|---|
| Installeren zonder omwegen | ✅ (derde keer op rij) |
| Na herstart zonder ISO verschijnt vanzelf het planeet-inlogscherm | ✅ `greeter-11-standaard-na-installatie.png` |
| Wachtwoordvraag in het Nederlands ("Wachtwoord") | ✅ `greeter-12-wachtwoord-nl.png` |
| Fout wachtwoord geweigerd, "Andere gebruiker" blijft zichtbaar | ✅ `greeter-13-fout.png` |
| Juist wachtwoord → ruimtewereld | ✅ `greeter-14-ingelogd.png` |

**Conclusie:** A7 ✅. Het planeet-inlogscherm werkt als standaard. Nog open: B14 (omgekeerde overgang bij afmelden).

## Bouwomgeving

Tijdens twee bouwpogingen (19:28, 20:00) blokkeerde ufw in de **bouw-VM** zelf SSH en downloads (`[UFW BLOCK]`, ook
voor antwoorden van poort 80). Gevolgen: `postinst` raakt in een chroot de draaiende firewall niet meer aan (`e6bfc5d`),
en ufw staat in de bouw-VM uit (een bouwmachine die alleen via 127.0.0.1 bereikbaar is). Universe OS zelf houdt ufw aan.
