# UOS-ANIM-001 — plan en contracten (5 agents)

Spec: `uitvoer/UOS-ANIM-001-opdracht-grok.md` (niet gecommit). Referentie: `uitvoer/UOS-ANIM-001-goedgekeurd.html`,
leesbare versie zonder base64: `/workspace/anim001/stripped.html` (regelnummers hieronder verwijzen daarnaar).

Tijdlijn (T in s, 0 = vertrek update-planeet): 0–4.7 meteorietvlucht, 4.7 inslag, 6 aftelling start (t=T-6),
15 korst barst (explosie, laatste seconde), 16 nul ('Opnieuw opstarten…'), 16–17.9 implosie naar gloeiende kern.
De shell blijft baas: herstart op de bestaande deadline via begin_logout('reboot') → finish_logout → backend.power.

**Lichte modus (gfx=licht/soft) = EXACT dezelfde animatie** (zelfde meteoriet, scheuren, brokstukken, explosie,
implosie, timing, geluid). Alleen minder pixels (canvasScale-budget) mag; geen elementen weglaten, geen minder deeltjes.
Minder beweging (motionAllowed false): alleen statische aarde+planeten, ring, tekst; geen vlucht/zoom/flitsen/fragmenten.

## Contracten (ES-modules in pakket/universe-os/usr/share/universe-os/ui/)
- `aarde-breuk.js` (a1): `buildFracture(earthImg, pxRadius) -> F` eenmalig: onregelmatig breuknetwerk met gedeelde
  randen (polylines per rand, door beide platen gedeeld; geen regelmatig raster/driehoeken zichtbaar), per plaat
  centroid px,py (eenheid r=1), release-tijd, Path2D, gecachte sprite (aardetextuur) + verschroeide sprite.
  `drawCracking(g,F,x,y,r,age)` (age=T-4.7>0: kern, intacte platen met verschroeiing, groeiende scheuren, krater, gloed),
  `drawDebris(g,F,x,y,r,T)` (losse platen; zelfde formule als drawCrustDebris r120-132, doorlopend na T=15 incl.
  collapse), `disposeFracture(F)`. Geen canvas-creatie per frame, geen indexOf in de lus.
- `explosie-update.js` (a3): `buildBurst(seed)->B` (vonken eenmalig), `drawBurst(g,B,cx,cy,R,age,W,H)` (r65-113 zonder
  de 18x18-cellen; kern lost op in gloed, schokgolven, vonken, flits), `drawClose(g,ex,ey,er,k,w,h)` (r246-247).
- `meteoriet.js` (a2): `startUpdateScene({host,seconds=10,runup=6,reduced,planets,scale}) -> {stop()}`; één rAF-lus,
  tijd uit performance.now; sterren, planeten rond aarde (config.world.planets, globe()/earth.png), meteoriet (de
  update-planeet zelf, geen kopie), inslag, aanzuigen (r200-245), roept a1/a3 aan. Tekst/cijfers als DOM (alleen bij
  wijziging bijwerken, aria-live), geen kop 'UNIVERSE OS / UPDATE GEÏNSTALLEERD'. Bij nul 'Opnieuw opstarten…'.
  stop() ruimt rAF, canvas en sprites op; dubbel starten = no-op.
- Geluid (a4): `usr/share/sounds/universe/update-inslag.wav` (al gerenderd, scripts/assets/maak-update-inslag.html)
  bevat alle effecten op T=0..18.6. universe-geluid kent 'update-inslag'. Shell speelt: update-inslag op T=0, aftellen
  op T=6..15, lancering op 16, afsluiten op 17.9.
- Wiring (a5): universe_shell.py (begin_launch 16 s voor deadline met runup 6, guard tegen dubbel, geen herstart bij
  fout, afsluitgeluid, finish_logout-wachttijd), world.js (launch-countdown → startUpdateScene; logout-begin laat
  de scene doorlopen), world.css.
