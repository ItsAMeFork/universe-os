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
