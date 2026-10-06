# Geluidsuitgang — spoor B, 2026-10-06

Status: 🧪; nog geen test met echte PipeWire-apparaten of in de VM.

Lokale controles geslaagd:
- Parser met synthetische PipeWire-objecten: analoog, HDMI, USB en Bluetooth;
  invoerapparaten uitgesloten, actieve standaarduitgang herkend en eerst getoond.
- Lege lijst en ongeldig verwijzend apparaatnummer afgehandeld.
- Selectie roept `wpctl set-default` aan; bevestiging vereist de actuele standaarduitgang.
- Hergebruikt apparaatnummer met andere naam wordt geweigerd vóór de systeemactie.
- Python-syntaxis, JavaScript-syntaxis en `git diff --check`.

Voor Claude: test paneel en Controlecentrum met echte uitgangen, HDMI/DisplayPort
van een losse videokaart, USB, Bluetooth, loskoppelen tijdens kiezen en opnieuw
inloggen/herstarten. Controleer dat WirePlumber de keuze bewaart en audio werkelijk
via de gekozen uitgang speelt. Alleen beschikbare sinks worden aangeboden;
uitgeschakelde kaartprofielen worden beheerd via pavucontrol.
