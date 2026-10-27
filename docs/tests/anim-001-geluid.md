# Test UOS-ANIM-001 deel 4: geluid van de update-inslag (a4, Claude)

**Datum:** 27 oktober 2026
**Omgeving:** box (Linux), headless Google Chrome via playwright-core (rendert met `OfflineAudioContext`), Python 3 + numpy
(geen scipy). Niet getest op echte hardware of in een sessie met PipeWire.

## Wat er is

- `usr/share/sounds/universe/update-inslag.wav`: 48 kHz, stereo, 16 bit, 18,60 s. Gemaakt met
  `scripts/assets/maak-update-inslag.html` (de synthese uit het goedgekeurde voorbeeld, vaste toevalszaden, de
  meteorietzoef is het bestaande `meteoor.wav` vertraagd tot 4,7 s).
- `universe-geluid update-inslag` speelt hem af. Hij staat op de lijst met toegestane namen en krijgt dezelfde behandeling
  als de andere geluiden: `pw-play --volume=0.8`, stil als "Systeemgeluiden" uit staat (`"sounds": false`). Dempen van de
  uitgang (sink mute) geldt vanzelf, omdat pw-play via de standaarduitgang speelt.

## Cue-sheet (T in s, 0 = vertrek van de update-planeet)

| T | Wie speelt | Geluid |
|---|---|---|
| 0–4,7 | `update-inslag.wav` | meteoor.wav (vertraagd, links→midden) + aanzwellende ruis 160→2200 Hz |
| 4,7 | `update-inslag.wav` | inslag: bas 125→32 Hz, donder, heldere tik, rommelend puin |
| 4,95–13,4 | `update-inslag.wav` | 15 korte brokjes + 11 rotsgeluiden, zacht rommelende kern (5,2–15) |
| 5,1 / 8,9 | `update-inslag.wav` | lage rotsdonder links / rechts |
| 6, 7 … 15 | **shell** (`aftellen.wav`, 10×) | aftellen (niet in de wav) |
| 12,5 | `update-inslag.wav` | donder vóór het aanzuigen |
| 13–14,1 | `update-inslag.wav` | zes planeten worden aangezogen (panning volgt de spiraal), elk met zachte lage plof |
| 14,7 | `update-inslag.wav` | aanloop scheur |
| 15 | `update-inslag.wav` | korst barst: bas, donder, scheuren in lagen, spanningstoon 47 Hz |
| 15,75–17,8 | `update-inslag.wav` | aanzuigen naar binnen ('pull'), sluit af met bas op 17,65 |
| 16 | **shell** (`lancering.wav`) | lancering (niet in de wav) |
| 17,9 | **shell** (`afsluiten.wav`) | afsluitgeluid (niet in de wav), zie hieronder |
| 18,1–18,6 | `update-inslag.wav` | stilte (laatste 50 ms uitgefade) |

Gemeten (rms per 100 ms) staan de pieken van de wav precies op 4,7 (−11,7 dBFS), 12,5, 13,2–14,0 (aanzuigen), 15,0
(−12,5 dBFS) en 17,6. Na 14,1 s is het stil tot de breuk op 15 s; na 18,1 s volledig stil.

## Afsluitgeluid zit niet in de bestaande update-route

In `universe_shell.py` roept `begin_launch` na het aftellen `begin_logout('reboot', sound='lancering')` aan.
`begin_logout` speelt `backend.sound(sound or (… 'afsluiten'))`, dus met `sound='lancering'` wordt **afsluiten
overgeslagen**. Het voorbeeld speelt afsluiten extra op 17,9 s (`play('afsluiten',intro+11.9,.65)`). Dat moet de
shell (deel a5) dus apart afspelen. Het zit bewust niet in deze wav: daar staan alleen de effecten.

## Controles

| Controle | Hoe | Uitkomst |
|---|---|---|
| Opnieuw renderen | `/tmp/pw/render.mjs` (kopie naar deze worktree) | ✅ gelijk aan de gecommitte wav op 1 LSB na (afronding; rms van verschil −134 dBFS). Twee renders achter elkaar: idem. |
| Oversturing in het bestand | piek, aantal samples ≥ 32766 | ✅ piek −3,0 dBFS (begrenzer in het html), 0 geclipte samples |
| Klikken | 2e afgeleide t.o.v. lokale rms (5 ms) | ✅ hoogste verhouding 0,95 (een klik geeft ≫ 5); begin en eind exact 0; DC-offset −0,0001 |
| Geen aftellen/lancering/afsluiten erin | genormaliseerde kruiscorrelatie met de projectbestanden | ✅ aftellen ≤ 0,26 op T=6…15; lancering max 0,21; afsluiten max 0,06. Eén uitschieter 0,69 op 17,87 s is de uitstervende bastoon (track −47 dBFS daar), geen tik. In de code worden die bestanden ook niet geladen. |
| Samen afgespeeld | som zoals in productie: wav×0,8 + aftellen×0,8 (6…15) + lancering×0,8 (16) + afsluiten×1,0 (17,9) | ✅ inslag −4,9, breuk+laatste tik −4,5, lancering+aanzuigen −5,3 dBFS; hoogste piek −1,0 dBFS is afsluiten zelf |
| `universe-geluid update-inslag` | `sh -n`; met nep-`pw-play` en instellingenbestand | ✅ speelt met `--volume=0.8`; niets bij `"sounds": false`; onbekende naam doet niets |

### Niveaus (dBFS)

| Bestand | Duur | Piek | Rms | Luidste 400 ms |
|---|---|---|---|---|
| aftellen.wav | 0,70 s | −8,4 | −23,0 | −20,6 |
| lancering.wav | 3,20 s | −4,0 | −15,1 | −9,5 |
| afsluiten.wav | 5,80 s | −1,0 | −13,9 | −9,8 |
| meteoor.wav | 2,20 s | −6,0 | −21,7 | −15,0 |
| update-inslag.wav | 18,60 s | −3,0 | −24,2 | −12,3 |

Niveaukeuze: het html rekent terug naar de verhouding uit het voorbeeld (aftellen op 0,65 × master 0,72, effecten op
master 0,72; versterking 1/(0,65·0,72) = 2,14). De begrenzer op −3 dBFS zet die op 1,49 (−3,1 dB). Daardoor klinken de
effecten ten opzichte van de tik iets zachter dan in het voorbeeld. Zonder die begrenzing zou de wav zelf clippen, en
samen met de laatste tik en de lancering zou er nog minder ruimte zijn. Daarom zijn de niveaus **niet aangepast**. De
luidste 400 ms van de inslag (−12,3) zit net onder lancering/afsluiten (−9,5/−9,8): duidelijk hoorbaar, niet harder dan
de projectgeluiden.

Let op voor de shell (niet in mijn bestanden): in het voorbeeld speelt lancering op 0,4 en aftellen/afsluiten op 0,65.
universe-geluid speelt alles op 0,8 (afsluiten 1,0). Lancering klinkt in productie dus relatief ~4 dB harder dan in het
voorbeeld. De som blijft onder 0 dBFS (zie boven).

## Nog te testen

- Echt afspelen in een Universe OS-sessie (PipeWire): synchroon met de animatie, dempen tijdens het afspelen.
- Bij afbreken van de scene (fout, of herstart afgebroken) moet de shell het geluid stoppen, bv.
  `pkill -u $(id -u) -f sounds/universe/update-inslag.wav`. Dat hoort bij de wiring (a5).
