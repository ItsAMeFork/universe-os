# Stand van Universe OS (10 oktober 2026, Claude spoor A)

Werkbranch: `spoor-a/A23-echte-computer` (main loopt achter; PR #11 was de laatste samenvoeging naar main).

## 28 oktober: versie 0.3.5 (geen flits van het oude slotscherm; animatie loopt af; GEPUBLICEERD 28 okt ~22:00, apt test + stable, apt-commits 81c5362 + edd390c, broncommit 962a637, deb sha256 a28646b6…; geen ISO)
- Getest 28 okt ~21:50 in de test-VM (0.3.4 via de echte updater + 0.3.5-bestanden): grim-film binnen de sessie na
  Windows+L: bureaublad -> lichtstrepen -> aarde gaat op in de kern -> slot; geen oude kaart. universe-lock wacht nu op
  lock.ready van de wereld (max 6 s, socketcommando lock-klaar) i.p.v. vaste 2,3 s (Axel: "laat de animatie aflopen").
  Ontgrendelen via het inlogscherm OK. Ctrl+Alt+F-terugweg (kaart na 8 s) niet opnieuw getest.
Axel: bij Windows+L verscheen heel kort het oude gtklock-scherm (kaart + klok) voor het inlogscherm. Nu toont gtklock
(blijft de beveiliging) met `gtklock/stil.css` alleen kern.png; kaart pas na 8 s als nooduitweg (wissel mislukt of
Ctrl+Alt+F terug); geen -H. Vergrendelanimatie eindigt nu in de kern ({core:true}, zoals afmelden), ontgrendelen komt
eruit (zoals inloggen). NOG TE DOEN: live test in de VM (Windows+L, elke ~0,3 s een QMP-schermafbeelding: de kaart mag
nergens verschijnen; Ctrl+Alt+F8 -> kaart na 8 s; ontgrendelen), daarna mergen naar main en publiceren.
Test-VM: SSH viel 28 okt ~21:15 weg na een netwerkstoring (updater: "geen internet"); in de VM werkten netwerk en sshd,
op de host kwam niets binnen; na herstart van QEMU kort weer, daarna opnieuw weg. Console tty2 (Ctrl+Alt+F2) werkt.

## 28 oktober: versie 0.3.4 (eigen profielfoto op je planeet; inlog-/vergrendelscherm blijft aan; GEPUBLICEERD 28 okt ~20:55, apt test + stable, apt-commits e7bca7d + 11dd36a, broncommit 2d7b533, deb sha256 0a091a87…; geen ISO)
Bevat ook 0.3.3 (hieronder), die niet apart is gepubliceerd.
- Profielfoto (ontwerp `docs/superpowers/specs/2026-10-28-profielfoto-design.md`): Controlecentrum > Gebruikers >
  eigen account > Profielfoto. Elk formaat dat GdkPixbuf leest (JPG, PNG, GIF, BMP, TIFF, WebP, HEIC/HEIF/AVIF),
  EXIF-draaiing, voorbeeld max 1024 px; midden automatisch rond uitgesneden, verschuiven (slepen of pijltjes) en zoomen
  (schuifbalk, muiswiel, +/-). Opslaan als PNG 512x512 via AccountsService SetIconFile (eigen account, geen
  beheerder). `greeter.py` geeft de foto als data-URL (alleen PNG/JPEG/GIF/WebP, max 2 MB) aan de planeet.
  Nieuwe afhankelijkheden: accountsservice, webp-pixbuf-loader, heif-gdk-pixbuf, libheif-plugin-libde265 (iPhone-HEVC).
- Inlog-/vergrendelscherm (X-server) zette na 10 min het beeld uit; nu standaard altijd aan. Beheerder: Controlecentrum
  > Energie > "Inlog- en vergrendelscherm", 0 = nooit, max 120 min (`/etc/universe-os/inlogscherm.json`, via
  `universe-admin-helper set-greeter-screen-off`, alleen beheerders). `greeter.py` past het bij elke start toe (xset).
- Live in de test-VM: iPhone-HEIC gekozen, met toetsenbord ingezoomd en verschoven, opgeslagen (geen wachtwoordvraag,
  icons/tester 512x512 PNG), op de planeet in het vergrendelde inlogscherm (gloed + stipje blijven), verwijderd.
  xset op het inlogscherm: 0 -> screensaver 0 + "DPMS is Disabled"; 30 -> "Off: 1800, DPMS is Enabled".
  Helper: standaardgebruiker geweigerd (126), 121 geweigerd. Tests: profielfoto-034.py, profielfoto-ui.mjs,
  inlogscherm-scherm.py (Linux OK). Screenshots `uitvoer/vm-test/0.3.4-*.png`.
- Niet live getest: slepen met de muis (QMP-muis werkt niet in de VM; rekenwerk wel getest), opslaan van de
  beheerdersinstelling via het venster (pkexec-vraag; helper zelf wel getest).

## 28 oktober: versie 0.3.3 (vergrendelen = inlogscherm, klok op de aarde, groene gloed; niet apart gepubliceerd, zit in 0.3.4; geen ISO)
Axel: vergrendelen (Windows+L, menu, inactiviteit, slaapstand, assistent) toont hetzelfde inlogscherm als bij het
opstarten i.p.v. het oude gtklock-scherm; aarde in het inlogscherm iets uitgezoomd; klok en datum op de aarde;
vergrendeld: alleen de vergrendelde account(s) tot 'Andere gebruiker', ingelogde/vergrendelde planeten groene gloed.
- `universe-lock`: na het slot (gtklock blijft de beveiliging) start universe-wissel het inlogscherm; terug met één
  wachtwoord (LightDM -> logind Unlock -> universe-ontgrendel-wacht). Mislukt de wissel: gewoon het slotscherm.
  `universe-wissel` geeft `UNIVERSE_LOCK_ZONDER_INLOGSCHERM` mee (niet dubbel wisselen).
- `space.js loginEarthPx()`: één maat (min(64vw, 62vh, 520 px), was 650) voor inlogscherm en afmeld-/vergrendelanimatie.
- `klok.js`: tijd + Nederlandse datum, controleert elke seconde (klopt na slaapstand). Test `docs/tests/klok.mjs`.
- Live in de test-VM (0.3.2 via de echte updatebron + deze bestanden): Windows+L -> inlogscherm met alleen tester
  (gloed, stipje, veld) + 'Andere gebruiker' -> alle planeten; goed wachtwoord -> zelfde sessie, venster nog open;
  fout -> melding; Ctrl+Alt+F8 naar de sessie -> slot staat er (geen open bureaublad). Linux-tests:
  wisselen-afmelden (14), ontgrendelen-030, sneltoetsen, vergrendelscherm, vergrendel-invoer OK.
  Screenshots `uitvoer/vm-test/0.3.3-*.png`.
- Niet live getest: slaapstand (QEMU/WHPX pauzeert bij wekken, net als bij herstart); `inlog-planeten.mjs` bijgewerkt
  maar niet gedraaid (geen Playwright op deze pc).
- Eerder vandaag bevestigd: de test-VM haalde 0.3.2 zelf van de updatebron, toonde de scène en herstartte.

## 28 oktober: versie 0.3.2 (UOS-ANIM-001: update-scène vóór de verplichte herstart; GEPUBLICEERD 28 okt 19:10, apt test + stable, apt-commits eed6dbd + 34a617d, broncommit a645bdd; geen ISO)
Na een geïnstalleerde update: de laatste 16 s vóór de herstart vliegt de update-planeet in de aarde (6 s aanloop),
dan 10 s aftellen terwijl de korst breekt, bij 0 implodeert alles in de kern en volgt de herstart. Zelfde scène in
normaal, lichte modus en world-lite; minder beweging = stilstaand met ring en cijfers. Gebouwd door 5 agents (Grok-
opdracht, klus/a1..a5), ChatGPT repareerde geluid/afbreken, Claude de dubbele CSS-verschuiving, de procesgroep van
`timeout` en het lazy laden in world-lite. Echt getest in de desktop van de test-VM: `docs/tests/anim-001-vm.md`
(normaal, licht, minder beweging, afmelden tijdens aanloop, geluid uit, mislukte update; echte herstarts).
Beperking: in de VM ~3-7 beelden/s (geen 3D); vloeiendheid op echte hardware nog beoordelen.
- Deb: universe-os_0.3.2_all.deb (5b9d6671…); universe-os-vergrendelknoppen blijft 0.3.1 (alleen Recommends, geen versie).
- Online gecontroleerd 28 okt: Packages van test en stable tonen universe-os 0.3.2; pool-.deb HTTP 200, hash klopt.

## 27 oktober: versie 0.3.1 (inlogscherm zonder kaart: inloggen via de kleine gebruikersplaneten; GEPUBLICEERD 27 okt 09:57, apt test + stable, beide pakketten, apt-commits d9ca7b5 + 1dd7240, broncommit a48cab2; geen ISO)
Jesse (t155u): alleen het inlogscherm. De rechthoekige kaart ('Universe OS', 'Jouw toegang tot het universum', gebruikersnaam, wachtwoord, Inloggen, Andere gebruiker) is weg; de grote planeet, ruimte en de rest zijn ongewijzigd.
- `ui/login.html/.js/.css`: klik/tik (of pijltjes + Enter) op een kleine planeet: die licht vloeiend op en direct eronder (boven als het knoppenpaneel in de weg zit) verschijnt een klein wachtwoordveld (#kluis) met pijltje; Enter of pijltje logt in, Escape sluit. Fout wachtwoord: rode melding in dat veld, veld leeg en meteen weer klaar. 1 gebruiker: meteen gekozen.
- Vergrendelde sessie(s) (liblightdm `logged_in`, greeter.py geeft `ingelogd` per gebruiker door): alleen die planeet/planeten met een markeringsstipje en linksonder de kleine knop 'Andere gebruiker'; die toont het overzicht met alle planeten. Zonder vergrendelde sessie geen knop. Terugkeren = één wachtwoord, dezelfde sessie; afmelden beëindigt de sessie echt.
- Planeten niet versleepbaar (ongewijzigd), focusring rond de planeet in plaats van een rechthoek. Rijhoogte nu t.o.v. de grote planeet (`PLANEET_VRIJ`) in plaats van de kaart.
- Suite: 62 OK, 0 FOUT. Tests: `docs/tests/inlog-planeten.mjs` (26 controles, Chromium en `ENG=webkit`), `ontgrendelen-030.py` uitgebreid. Live in de test-VM (12, 2 en 1 gebruiker via testfilter; vol en licht via /etc/universe-os/grafisch-licht): goed/fout wachtwoord, terugkeren naar vergrendelde anna, 'Andere gebruiker' zichtbaar/onzichtbaar, overzicht, afmelden, sleeptest. Screenshots: `uitvoer/vm-test/0.3.1-*.png`; `0.3.1-grote-planeet-voor-na.png`: rand van de grote planeet pixel-gelijk, buiten het oude kaartvlak max. 2/255 verschil.
- Debs (a48cab2): universe-os_0.3.1_all.deb (56c4dabc…), universe-os-vergrendelknoppen_0.3.1_amd64.deb (f1d1f12e…).
- Online gecontroleerd 27 okt 09:58: Packages van test en stable tonen beide pakketten in 0.3.1; beide pool-.debs HTTP 200, hashes kloppen.

## 26 oktober: versie 0.3.0 (gtklock-vergrendelscherm met eigen knoppenmodule, gtklock in het Nederlands, robuuste 'Andere gebruiker'; GEPUBLICEERD 26 okt 08:25, apt test + stable, apt-commits 6a2cc54 + 24795e8, broncommit 4bdecf0; geen ISO)
- Twee pakketten: `universe-os_0.3.0_all.deb` (sha256 36e846f5…) en `universe-os-vergrendelknoppen_0.3.0_amd64.deb` (sha256 80f2885c…).
- `scripts/publiceer-apt.sh` (f123875): neemt bijbehorende pakketten van dezelfde versie (`universe-os-*_VERSIE_*.deb`) mee naar test en stable.
- Online gecontroleerd 26 okt 08:26: Packages van test en stable tonen universe-os 0.3.0 en universe-os-vergrendelknoppen 0.3.0 (amd64); beide pool-.debs HTTP 200, hashes kloppen.

## 26 oktober: versie 0.2.39 (eerst het portaal, dan het venster; GEPUBLICEERD 26 okt 09:25, apt test + stable, apt-commits 78c2474 + b58b4fc, broncommit 2bda01d; geen ISO)
- Jesse t146u: venster vanuit de onderbalk verscheen zonder animatie. Nu verbergt labwc elk nieuw venster bij het mappen (windowRule Iconify, plaatsing midden); de shell speelt het portaal en zet het venster onder de nog dichte kaart terug. Geen labwc-patch nodig.
- Veiligheidsnet vensterwacht.py (gestart door universe-shell-supervisor): zonder shell-hartslag (4 s) geen verbergregel en verborgen vensters worden getoond.
- Live getest licht + vol: onderbalk, sluiten, venster dat een app zelf opent, menu; planeet en Wine in licht. Frames: uitvoer/vm-test/0.2.39-*.png. Niet live: planeet/Wine in vol, echte shell-crash.

## 25 oktober: versie 0.2.38 (portaal-vensteranimatie, mooiere ruimte, filmische in-/uitlog, lichte modus = zelfde in lagere kwaliteit; GEPUBLICEERD 25 okt 21:47, apt test + stable, commit ebdbbb4; geen ISO)
Jesse (t129u/t130u): vensters niet meer als bloem maar vanuit de aangeklikte planeet/snelkoppeling; alle animaties en de ruimte mooier; de lichte modus exact hetzelfde maar lichter.
- `flits.py`: portaal (venster groeit langs een gebogen baan met lichtspoor uit de bron, lichtpunt + lensstreep bij de bron; sluiten terug naar de bron of het midden; minimaliseren naar het dock). Eén tekenpad met `KWALITEIT` vol/licht (licht: minder gloedlagen/spoorpunten/schijfsegmenten, geen vensterinhoud, ~30 fps); ook gat en zwart gat. 'snel' alleen nog voor Animaties verminderd.
- `universe_shell.py`: flits_mode geeft 'licht' bij oude/zwakke videokaart of eenvoudige wereld; `launch_bron` (klikpunt van world/start naar schermpixels); bron per venster onthouden voor sluiten.
- `world.js`/`start.js`: klikpunt (planeetmidden of laatste aanwijzer) mee met apps.launch.
- `sterrenhemel.js` (nieuw): 9000 sterren in 3 dieptelagen met parallax, temperatuurkleuren, twinkeling (eigen canvas, 24/8 fps), melkwegband met nevels en stofbanen, warp-strepen. Licht = elke 3e ster, kleinere nevel, minder twinkel. Gebruikt in de wereld en op het inlogscherm (`space.js`).
- In-/uitloggen/opstarten (`animateWorld`): 2.8/2.3 s, sterren worden lichtstrepen, lensstreep bij de kern. Inlogscherm (`explode.js`): langer opladen/inklappen, planeet vormen 1.7 s, lensstreep.
- Planeten (`world.css`): atmosfeerrand + belichte kant, alleen gradients (geen blur).
- Vergrendelscherm: vergrendel-/ontgrendelanimatie met warp-sterren (zelfde als uitloggen), universe-lock wacht 2.3 s, gtklock-kaart en klok schuiven in beeld (keyframes), sterren.png en vergrendeld.png opnieuw gemaakt met de nieuwe ruimte.
- Samengevoegd (Jesse t134u): klus/1 (pyflakes-opruiming), klus/3 (build-scripts: versie via argv, build-iso stopt als build-deb faalt), klus/4 (config.read_json robuust + test), klus/5 (docs). klus/2 blijft staan.
- Tests: venster-animatie.py (portaal, bron, kwaliteit), lichte-hardware.py, nieuw sterrenhemel.mjs en vergrendelscherm.py. Frames: uitvoer/vm-test/0.2.38-*.png (cairo offscreen + headless Chrome harnas, geen echte sessie).
- Live getest in de laptop-VM, licht en vol (4aa64e1): zwart gat midden i.p.v. linksboven, eerste programma na inloggen krijgt portaal, menubron klopt, bron 30 s geldig. Screenshots: uitvoer/vm-test/0.2.38-live-*.png.
- Live2 (ebdbbb4, Jesse t142u): toetsen direct na Super+L kwamen in de app ('tes' in de rekenmachine). Nu labwc `Unfocus` vóór universe-lock + onzichtbare invoervanger in de shell tot gtklock het toetsenbord heeft; focus terug na ontgrendelen (test vergrendel-invoer.py; live: 36-42 toetsen tijdens de animatie, rekenmachine leeg). Nieuw venster: na de grim-opname het scherm van vóór het venster erover (flits_voor/bevries), afdekking = echte achtergrond (zachte rand als terugval); wek-timer brak het portaal en gaf zwarte beelden (opgelost). Afmeld-animatie vastgelegd. Screenshots: uitvoer/vm-test/0.2.38-live2-*.png. Rest: venster nog ~1 grim-opname zichtbaar (labwc 0.8.3 geeft geen vensterpositie).

## 25 oktober: versie 0.2.37 (animaties trager en zichtbaar, realistisch zwart gat; GEPUBLICEERD 25 okt 17:34, apt test + stable; geen ISO)
Jesse (t126u): animaties te snel, zwart gat moet echt lijken op een ster die wordt opgeslokt.
- `flits.py`: bloem openen 1.0 s, sluiten 0.9 s, minimaliseren 1.0 s, lichtflits + gat 1.1 s, met ease-in-out (geldt ook voor Wine/.exe-vensters: zelfde pad).
- Zwart gat (tidal disruption): zwarte horizon, gekantelde draaiende accretieschijf met Doppler-helderheid, gelensde achterkant van de schijf boven/onder het gat, fotonring met gloed; per bestand 1.8 s: uitrekken (spaghettificatie), spiraal als lichtstroom, roodverschoven uitdoven bij de horizon; schijf licht op bij elke 'maaltijd'; gat zakt in 1.2 s in. Totaal max 8 s (18 groepen, dichter op elkaar).
- Lichte modus/verminderd ongewijzigd (korte vervaging). Geen WebKit.
- Tests: venster-animatie.py, bestand-verwijderen.py, prullenbak-zwartgat.py bijgewerkt; lichte-hardware.py groen. Frames (offscreen cairo-render): uitvoer/vm-test/0.2.37-*.png.

## 25 oktober: versie 0.2.36 (bloem-animatie op echte venstergrootte, lichtflits + gat, zwart gat bij prullenbak legen; GEPUBLICEERD 25 okt 16:58, apt test + stable; geen ISO)
Jesse vond de 0.2.35-animatie een 'vierkante lichtflits'.
- Vensters (ook Wine/.exe via Xwayland): openen = bloem die vanuit het midden uitvouwt tot precies de rechthoek van het venster, met de echte inhoud; sluiten = dezelfde bloem andersom; minimaliseren vouwt dicht richting het dock. Open ~350 ms, sluiten ~250 ms.
- Geometrie: labwc 0.8.3 heeft geen IPC en geeft via wlr-foreign-toplevel geen positie; ext-image-copy-capture per venster pas in labwc 0.9. Daarom `shell/venstermeting.py`: één grim-opname (wlr-screencopy) en de actieve vensterrand (#85ffe3, 2 px, titelbalk #162335) terugzoeken = exacte rechthoek + inhoud. Gemaximaliseerd zonder rand: scherm min dock. Geen rand gevonden (splash, launcher, volledig scherm) = geen animatie.
- Geen dubbele animaties: Wine/X11-vensters die opnieuw mappen (zelfde app+titel binnen 1 s) en vensters die weg zijn voor de meting krijgen niets; sluiten alleen als het venster ooit gemeten is.
- Bestand naar de prullenbak: lichtflits op de plek (bureaublad: positie van het icoon; Thunar/gio: midden van het actieve venster) en een klein zwart gat. Via een Gio-monitor op trash:///. Windows-programma verwijderen (wine.remove) roept `universe-ctl flits verwijder <naam>`.
- Prullenbak legen (Thunar, gio, nieuw menu 'Prullenbak leegmaken' op het bureaublad-icoon): groot zwart gat met accretieschijf en lens-gloed slokt de bestanden één voor één op met lichtsporen; max ~3 s, boven 18 bestanden gegroepeerd ('+N').
- Verminderd/lichte modus/eenvoudige wereld: alleen een korte omlijning/vervaging (150 ms); Uit: niets. Elk kapot frame wordt overgeslagen.
- Bekend: de meting komt na het verschijnen van het venster (grim-opname), dus het venster is heel even zichtbaar voordat de bloem het afdekt (in de VM duidelijk, op echte hardware ~50-100 ms). Positie bij sluiten = laatst gemeten (bij activeren/maximaliseren), een venster dat daarna versleept is sluit op zijn oude plek.
- Tests: venster-animatie.py (herschreven), bestand-verwijderen.py, prullenbak-zwartgat.py. Screenshots: uitvoer/vm-test/0.2.36-*.png (0.2.33-demo in QEMU TCG, vertraagd x12).

## 24 oktober: versie 0.2.33 (opstartmenu in home-wereld-stijl; ISO gebouwd; GEPUBLICEERD 24 okt 23:29, apt test + stable)
- BIOS (syslinux) en UEFI (GRUB) tonen de ingelogde 'home'-wereld (aarde + sterren, zonder dock/bovenbalk) als achtergrond.
- Geen menutitel meer over het logo; één optie 'Universe OS' in een pil zoals de dock, aftelling en hint in shell-kleuren.
- GRUB: eigen thema (1920x1080, schaalt mee), Noto Sans als pf2 (grub-mkfont), geen piep meer. Geïnstalleerde GRUB ongewijzigd.
- Test: docs/tests/opstartmenu-thema.py.

## 24 oktober: versie 0.2.32 (lichte modus volledig automatisch, geen keuzescherm; ISO gebouwd; GEPUBLICEERD 24 okt 22:20, apt test + stable)
Jesse testte 0.2.31 op de GT 710: werkt. Wens: de gebruiker kiest niets.
- Installer: zichtbare stap 'Beeld' weg. Stille `shellprocess@beeld` (dontChroot) draait `universe-beeld-keuze ${ROOT}`: zelfde detectie als de live-sessie (plus de live-noodoptie `universe.gfx=licht`) en zet `grafisch-licht` of `grafisch-normaal` op de doelschijf. Handmatig wijzigen alleen in Controlecentrum > Vormgeving.
- Detectie robuuster (`grafisch.py`): bleef afhangen van de drm-driver op dat moment. Was nouveau nog niet gebonden (universe-gpu laadt hem laat, firmware), dan zag de shell alleen simpledrm en bleef normaal. Nu: wachten (max 10 s) tot elke PCI-videokaart een driver heeft, drivers ook via de PCI-apparaten, PCI-id-tabel (NVIDIA voor Maxwell <0x1340 zoals GT 710 10de:128b, NVIDIA zonder nvidia-driver, oude AMD/radeon, oude Intel), en als laatste de renderer-string (eglinfo/glxinfo: NVxx, GK/GF, Ivybridge/Haswell, radeon-families).
- Opstartmenu (aanvulling Jesse): nog maar één optie 'Universe OS' (grub en syslinux, eigen `menu.cfg` zonder Utilities/installer-submenu), start na 3 s vanzelf. Geen NVIDIA-, veilig-, nomodeset- of lichte-noodoptie meer; met 'e'/Tab blijven `universe.gfx=licht`, `universe.world=lite`, `universe.gpu=...` en `nomodeset` werken.
- Wat de demo zelf leerde gaat mee bij installeren: `universe-beeld-keuze` kopieert `grafisch.json` (kleurproef) en `grafisch-crash.json` (crash-terugval) naar `/etc/skel` en de nieuwe home; een crash-terugval of 'aan' in de demo geeft `grafisch-licht`.
- Test: `docs/tests/lichte-hardware.py` (GT 710 uit de diagnose, ook met alleen simpledrm of zonder driver).

## 24 oktober: versie 0.2.31 (lichte hardware-modus voor oude/zwakke videokaarten; ISO gebouwd; gepubliceerd 24 okt 22:20 als onderdeel van 0.2.32)
Oorzaak crash GT 710 (nouveau): WebKitGTK 2.54 tekent met Skia op de GPU in werkthreads; nouveau is niet thread-safe
(`free(): invalid pointer`). Lichte modus = Skia tekent tegels met de processor (`WEBKIT_SKIA_ENABLE_CPU_RENDERING=1`,
`WEBKIT_SKIA_GPU_PAINTING_THREADS=0`), de videokaart voegt alleen samen; plus gedeeld geheugen en `mesa_glthread=false`.
- Automatisch aan (`shell/grafisch.py`, `choose_light`): nouveau, radeon (r600/GCN1-2), ast/mgag200/gma500, oude Intel Gen3-7.5 (PCI-id), zwakke pc (<=2 kernen en <=4 GB), en na een eerdere world-crash (onthouden per driver+kernel). Niet bij nvidia/amdgpu/nieuwe Intel.
- Handmatig: opstartoptie `universe.gfx=licht` (nieuw item in GRUB/syslinux: "oude/zwakke videokaart (lichte modus)"), Controlecentrum > Vormgeving > Lichte grafische modus (auto/aan/uit), of `/etc/universe-os/grafisch-licht`. `universe.gfx=normal` of "uit" zet de automaat uit.
- Na een world-crash: eerst lichte modus, dan processor-tekenen (nouveau), dan 2D (`webview.py`).
- Wereld (`gfx=licht`): canvas max 1280x720 en dpr 1, 300 i.p.v. 900 sterren, max 30 fps, planeetplaatjes max 512 px, geen filter/schaduw/backdrop (`world.css`), lichte animaties (`motion.js`, `explode.js`).
- NVIDIA 470 legacy niet in de ISO: zit niet in trixie (alleen sid), DKMS-build breekt bij trixie-kernelupdates, EOL. Zie `docs/stuurprogrammas.md`.
- Installer (Calamares): nieuwe stap 'Beeld' (`packagechooser@beeld`) met 'Lichte modus voor oudere videokaarten' / 'Normale weergave'; `universe-install` laat `universe-beeld-keuze` vooraf de videokaart detecteren (zelfde `choose_light`) en vult de keuze in. `contextualprocess@beeld` schrijft `/etc/universe-os/grafisch-licht` of `grafisch-normaal` op de doelschijf. Controlecentrum wint per gebruiker.
- Elke world-crash (ook op een onbekende kaart) gaat eerst naar de lichte modus en onthoudt dat (`~/.local/state/universe-os/grafisch-crash.json`).
- Samengevoegd (Haiku): test-ai-preview, test-ai-switch, gitignore-live, sneltoetsen-help (Win+F1, overzicht in Controlecentrum).
- Test: `docs/tests/lichte-hardware.py`.

## 24 oktober: versie 0.2.30 (pc beneden: GT 710; Windows-sneltoetsen; ISO gebouwd; gepubliceerd 24 okt 22:20 als onderdeel van 0.2.32)
Diagnose pc beneden: GeForce GT 710 (GK208B, Kepler, id 128B). nvidia 550 kent Kepler niet, maar Debian's module heeft een
joker-alias, dus `universe-gpu` koos nvidia -> modprobe 'No such device' -> nouveau. Op nouveau crashte het WebKit-proces van
world.html steeds (`free(): invalid pointer`), na 3 keer world-lite (2D).
- `universe-gpu`: kaarten ouder dan Maxwell (PCI-id < 0x1340) krijgen meteen nouveau. Test: `docs/tests/nouveau-crash.py`.
- `shell/grafisch.py`: op nouveau gedeeld geheugen en `mesa_glthread=false`; na de eerste world-crash op nouveau tekent de processor (gfx=soft) vóór de 2D-terugval (`webview.py`). Test: `docs/tests/pagina-herstart.py`.
- Windows-sneltoetsen (Win+R/S/V/./M, Win+Shift+S, Ctrl+Alt+Del-menu) in `shortcuts.json`; `universe-klembord` (klembordgeschiedenis, emoji, Ctrl+Alt+Del); Ctrl+V plakt in de terminal (sessie zet `~/.config/xfce4/terminal/accels.scm` eenmalig neer). Overzicht: `docs/SNELTOETSEN.md`. Test: `docs/tests/sneltoetsen.py`.

## 24 oktober: versie 0.2.29 (NVIDIA-pc; ISO gebouwd; gepubliceerd 24 okt 22:20 als onderdeel van 0.2.32)
Gepubliceerd (apt test + stable): 0.2.24 t/m 0.2.28 (0.2.28 op 24 okt) en 0.2.32 (24 okt 22:20; bevat 0.2.29 t/m 0.2.31, die geen los pakket kregen), 0.2.33 (24 okt 23:29), 0.2.34 (25 okt 14:11), 0.2.35 (25 okt 15:51), 0.2.36 (25 okt 16:58), 0.2.37 (25 okt 17:34) 0.2.38 (25 okt 21:47), 0.2.39 (26 okt 09:25), 0.3.0 (26 okt 08:25) en 0.3.1 (27 okt 09:57).
- Met het eigen NVIDIA-stuurprogramma geen grafische proef meer en nooit processor-tekenen door een proefuitslag; normaal tekenen met gedeeld geheugen (`shell/grafisch.py`). Oorzaak van de 2D-terugval: proef zei 'safe' -> llvmpipe -> wereld te traag -> world-lite.
- Proefpagina neutraal donker (#050815 / #151828) met "Beeld wordt getest…" in plaats van blauw/paars (`shell/grafisch_proef.py`). Dat was het blauw/paarse beeld na inloggen.
- `ui/world.js`: frame-/planeetcontrole 25 s in plaats van 12/14 s bij `gfx=soft`.
- Test: `docs/tests/nvidia-proef.py`.
- Samengevoegd (Haiku-agents): playwright als devDependency in `docs/tests/package.json` (animation-layout.cjs meldt SKIP zonder), Nederlandse GRUB-teksten (`hooks/live/0400-grub-nl.hook.binary`, grub-common), Universe-splash i.p.v. Debian-logo (grub-pc/isolinux `splash.png`), Calamares bootloader-timeout 8 s en branding 0.2.29.

## 23 oktober: versies 0.2.24 en 0.2.25 (inmiddels gepubliceerd)
**0.2.24** (H310M en andere grote beeldschermen):
- Donkere, bijna ondoorzichtige taakbalk: de lichte glazen balk werd op de H310M een witte balk, met onzichtbare iconen (`ui/dock.html`).
- Eigen iconen voor de vaste knoppen (`ui/dock.js`).
- Schaal automatisch op schermhoogte: 1080 = 1x, 1440 = 1,25x, 2160 = 2x (`shell/universe_shell.py`, `screen_factor`). Paneelvenster schaalt mee.
- Opnieuw tekenen na opstarten en na grootte- of zoomwijziging, zonder dat de muis erover hoeft (`Surface.redraw`). Test: `docs/tests/ui-schaal.py`.
- Standaardresolutie 1920x1080 waar het scherm die heeft: `universe-displays resolution` draait als eerste in de labwc-autostart; instelling `displayResolution` (`'WxH'` of `'preferred'`). Het inlogscherm zet dezelfde modus met xrandr (`universe-xrandr-1080`). Test: `docs/tests/resolutie.py`.

**0.2.25** (wereld bevroor op NVIDIA na de resolutiewissel):
- Op NVIDIA gedeeld WebKit-geheugen (`WEBKIT_DMABUF_RENDERER_FORCE_SHM=1`), niet in de veilige modus en niet bij `universe.gfx=normal` (`shell/grafisch.py`). Test: `docs/tests/nvidia-wereld.py`.
- Na een schermmodus-wissel wacht `universe-displays` tot de nieuwe modus echt staat (maximaal 4 s) plus 1 s, voordat de shell start (`settle`).
- De intro van de wereld wacht hooguit 6 s op de planeten (`ui/world.js`).

**Ook in deze branch:**
- Logboek (`shell.log`): renderer-crashes en paginaladen-fouten (`webview.py`, via `bridge.log`), en de resolutiewissel (`universe-displays` schrijft naar stderr; de autostart voegt dat toe aan `shell.log`). Voorheen verdwenen die stil. Test: `docs/tests/shell-logboek.py`.
- Taakbalk toegankelijk met het toetsenbord en voor schermlezers: Nederlandse tooltips en `aria-label` op elke knop, pijltjestoetsen in het snelmenu, Escape zet de focus terug op de knop (`ui/dock.js`). Test: `docs/tests/dock-a11y.py`.
- Opstartmenu GRUB en syslinux: automatische start na 8 seconden (GRUB had geen timeout, syslinux `timeout 0` = eeuwig wachten). Syslinux-keuzes hebben Nederlandse helpteksten (`TEXT HELP`). Labels zijn ongewijzigd.
- `.gitignore`: ISO-bouw-artefacten (`iso/`, `live/.build/`, `live/binary/`, `live/cache/`, `live/chroot*`, `live/build.log`, ...).

**Nog niet gecontroleerd:**
- Startmenu op 1920x1080: horizontaal gecentreerd door layer-shell (geen links/rechts-anker), onderaan verankerd boven de taakbalk, schaalt via `ui_zoom`. Geen CSS-wijziging gedaan: de layout kon hier niet op een echt scherm bekeken worden.
- `docs/tests/animation-layout.cjs` vraagt het pakket `playwright` (sinds 0.2.29 devDependency in `docs/tests/package.json`: `cd docs/tests && npm install`; zonder meldt de test SKIP).

## 14 oktober: alles in main, ISO 0.2.15 klaar (update NIET gepubliceerd; online 0.2.12)
- PR #39-#44 (GitHub-assistent Henk: tests, Claude-harness, brein-nevel, AI-assistent, AI wisselen, Claude in Chrome) nagekeken
  en op volgorde samengevoegd in spoor-a; daarna spoor-a -> main (#38). Alle 20 tests (16 py, 4 js) slagen.
- ISO: `D:\UniverseOS-VMs\iso\universe-os-0.2.15-amd64.iso`, SHA-256 04cef4f0…3a93 (commit fa5e391).
- Kanttekeningen: "leren" staat standaard aan (alleen met eigen API-sleutel); oude modelnaam claude-haiku-4-5 in efficientie.py.

## 13 oktober 21:35: versie 0.2.14 (ISO klaar, update nog NIET gepubliceerd)
- ISO: `D:\UniverseOS-VMs\iso\universe-os-0.2.14-amd64.iso`, SHA-256 f5181cf8…277c.
- Grafisch model voor elke pc (`webview.webkit_safe_mode`): onbekende/zwakke kaart -> `WEBKIT_DMABUF_RENDERER_FORCE_SHM=1`.
  NIET `WEBKIT_DISABLE_DMABUF_RENDERER` of `WEBKIT_DISABLE_COMPOSITING_MODE`: dan tekenden de doorzichtige balken alleen
  het stuk onder de muis (balken verdwenen op de H310M-pc met 0.2.13). Getest in de VM met nagebootste NVIDIA-situatie.
- Gebruikersnaamveld laat tekens weg die niet in een gebruikersnaam kunnen (toetsenbord stuurde "\" bij eerste toets, ook in BIOS).

## 13 oktober avond: versie 0.2.13 (ISO klaar; update nog NIET gepubliceerd, Axel doet dat thuis)
- ISO: `D:\UniverseOS-VMs\iso\universe-os-0.2.13-amd64.iso`, SHA-256 8196828671…e747. Met WebKit-veilige modus voor NVIDIA/nouveau (H310M-pc).
- ISO-bouw liep 4x vast: apt in de chroot tot 5,7 GB (OOM) terwijl de VM namen niet kon opzoeken. Opgelost met vaste DNS in de bouw-VM (`/etc/systemd/resolved.conf.d/universe-bouw.conf`), `live/config/apt/apt.conf`, verse VM-start en bouwen onder `systemd-run -p MemoryMax=5000M`.
- polkit `60-universe-power.rules`: actieve lokale sessie mag zonder wachtwoord afsluiten/herstarten/slaapstand, ook met meerdere sessies (Axel: Claude kon de pc niet meer uitzetten). energie valt terug op een directe opdracht als de shell geen claude.power kent.
- ISO voor Axels tweede pc (Gigabyte H310M S2H 2.0, BIOS F12): "boot niet correct", nog onbekend wat hij precies ziet.

## 13 oktober: versie 0.2.12 (gepubliceerd 08:58)
- Claude: hulpmiddel energie (vergrendelen/afmelden/herstarten/afsluiten/slaapstand) via shell `claude.power`: altijd met animatie, Claude-paneel sluit eerst, antwoord meteen (vroeger: eigen lock-opdracht wachtte tot ontgrendelen). VM: vergrendelen en afsluiten met open paneel getest.
- Claude mag meer (geluidsuitgang, standaardbrowser, updates, bureaubladbestand); geweigerd: sudo/pkexec/su/passwd/gpg, energie-opdrachten in de terminal, bewerken van /usr, /etc, /var, ~/.claude, ~/.ssh, ~/.gnupg, en lockMinutes. Claude Code kent alleen Edit-regels (Write gaf waarschuwingen).

## 12 oktober nacht: versie 0.2.11 (gepubliceerd 23:45, test + stable)
- Vensters vastklikken zoals Windows (`session.py`: rij losse If-acties, labwc 0.8.3 staat geen If in If toe; gebieden helften/kwarten). Getest: alle Windows+pijl-stappen, slepen naar de rand, rand verslepen.
- Open vraag aan Axel: verplichte herstart bij elke update (ook Debian) of alleen bij Universe OS-updates?
- Niet in labwc 0.8.3: Snap Assist en de scheidslijn tussen twee vastgeklikte vensters slepen.
- Let op: elke geïnstalleerde update (ook Debian-beveiligingsupdates) geeft de verplichte herstart (gezien in de VM: librsvg).

## 12 oktober laat: versie 0.2.10 (gepubliceerd 23:20)
- Opstartgeluid op 100 % en volgens de laatste volumestand (`/var/lib/universe-os/geluid/volume`, gezet door de sessie, toegepast door het inlogscherm; volume niet te testen in de VM).
- Afsluitdeuntje = opstartgroove als afscheid (5,8 s); de pc gaat pas uit als het klaar is (VM: uit na 9 s).
- Volumedeuntje bij loslaten van de schuif en bij de volumetoetsen; meteoor bij beheerdersrechten (polkit-venster in de shell, sudo via PAM optional `universe-admin-geluid`).

## 12 oktober avond: versie 0.2.9 (gepubliceerd 22:37)
- Eigen "chill reggae space"-geluiden (`maak-geluiden.mjs`): opstarten (inlogscherm, 1x per opstart), in-/afmelden, afsluiten, melding, fout (kritieke melding), apparaat in/uit (udev), vergrendelen/ontgrendelen, verkeerd wachtwoord op het vergrendelscherm (PAM optional -> `universe-lock-poging`), prullenbak, schermafbeelding, volume, batterij 10/5 %.
- Afsluiten/herstarten = zelfde animatie als afmelden (`begin_logout(action)`).
- Verplicht herstarten na updates: melding "Sla je werk op", 2 min, laatste 10 s lancering-aftelling op de wereld; vangnet `shutdown -r +3` in `universe-updates-run`.
- Chrome: beleid HardwareAccelerationModeEnabled=false (beeld in blokken op Axels pc, ook native Wayland).
- VM: gtklock werkt niet op 640x480 (alleen VM); QEMU pauzeert bij een herstart van de test-VM (WHPX): proces herstarten.

## 12 oktober: versie 0.2.8 (getest in de test-VM)
- Vergrendelscherm = inlogscherm-stijl met naam/foto en wachtwoordveld (gtklock + userinfo, `pakket/.../gtklock`); ontgrendelen getest.
- Afmelden stopt de hele sessie (`universe-session` -> loginctl terminate-session; shellbewaking stopt zonder compositor): geen vastlopers bij opnieuw inloggen (3 rondes getest).
- Inloggen/afmelden als één animatie via de gloeiende kern (`kern.png`, `explode.js chargeToCore`, `world.js setCore/drawBoom`).
- Scherpe realistische planeten (`planets-hq.js`), pictogrammen 256 px, vloeiend zoomen/slepen, startring bij openen.
- Systeemgeluiden (`universe-geluid`, eigen geluiden uit `maak-geluiden.mjs`), instelling Systeemgeluiden.
- Chrome native Wayland + systeemtitelbalk (onleesbare tekst op Axels pc); min/max/sluiten op alle vensters (gsettings button-layout).
- ISO start ook met oud BIOS (syslinux + grub-pc in installer); installer-fout "Missing variables: d" opgelost.

## 11 oktober avond: echte Claude Code getest in de VM (Axel ingelogd, Haiku 5.5)
Werkt: vraag over het scherm (overzicht + schermafbeelding), Firefox en Rekenmachine openen (wacht nu op het venster),
onthouden en terugvinden in een nieuw gesprek (brein), zoeken in bestandsinhoud (recoll), personage loopt mee.
Opgelost tijdens de test: app_openen met "naam" i.p.v. "id" opende Atril; vertrouwensvraag bij elke start (Claude Code
onthoudt de thuismap niet; nu eigen werkmap `~/.local/share/universe-os/claude` + `--add-dir ~`); paneel onzichtbaar na sluiten;
typen (toetsenbord blijft bij het paneel); klikbare links en Ctrl+Shift+C/V. VM: virtio-vga + SSE4-processor (rust ~2 % i.p.v.
50-90 %). Snelheid: sterren/planeten/vensterlijst/netwerk via D-Bus. Open: eerste inlog na opstarten (57 s gemeten met oude
VGA), Chrome-sleutelbosvraag in de VM (oud wachtwoord), pakket opnieuw bouwen.

## 11 oktober: Claude in Universe OS, fase 1 (ontwerp: `docs/CLAUDE-IN-UNIVERSE.md`)
| Wat | Waar | Test |
|---|---|---|
| Claude-paneel (Windows+C of klik op personage): echte terminal met de ongewijzigde Claude Code, Haiku, `--continue` | `shell/claude_ui.py`, `bin/universe-claude` | VM met nep-`claude` (`~/.local/bin/claude` van tester) |
| Personage: zwevend slijm met ogen dat vervormt bij bewegen (Cairo, veer-demping, geen WebKit): denken, werken, toestemming, blij; loopt naar taakbalk/wereld/paneel | `shell/claude_ui.py` (Buddy), instelling `buddy` | VM: alle seintjes via de hook gezien |
| OS-hulpmiddelen + tweede brein (SQLite FTS5) als MCP-server | `lib/universe-os/claude/universe_mcp.py`, `brein.py` | VM: JSON-RPC, alle soorten aanroepen |
| Hooks -> `universe-ctl claude-event`; `universe-ctl call` met vaste toegestane lijst | `claude/universe-claude-hook`, `universe_shell.py` (CLAUDE_CALLS) | VM |
Later die middag: personage denkt vooruit (tekstballon: download, USB, batterij, gewoontes; `shell/buddy_hints.py`),
Disney-bewegingen (indrukken/uitrekken, aanloop, naslingeren, ademen), Recoll als bestandsindex (`claude/recoll_index.py`,
recoll in VM geïnstalleerd), tijdlijn, Controlecentrum-pagina Claude (agent), 2 reviewfouten hersteld. VM: ballon en sprong
gezien, recoll vond "pindakaas". Shell in rust met ademend personage: ~1,7 % CPU in de VM.
Nog niet getest: met de echte Claude Code (moet in de VM geïnstalleerd en ingelogd worden), typen in het paneel,
installatieknop in het Controlecentrum (nog niet gebouwd). Pakket niet opnieuw gebouwd: VM heeft losse bestanden.

## Later op 10 oktober: inloggen, afmelden en vergrendelen met animaties (t/m 78b70dd)
| Wat | Waar | Test |
|---|---|---|
| Inlog- en vergrendelscherm: de aarde in de ruimte (zelfde camera als het 3D-bureaublad) | `ui/login.*`, `ui/space.js`, `scripts/assets/vergrendeld.png` (gemaakt met `maak-vergrendeld.html`) | VM (vergrendelplaatje, inlogscherm) |
| Aarde als kant-en-klaar plaatje | `ui/earth.png` (720 px, earthNow) | VM |
| Inlogscherm: planeet vormt zich; bij inloggen opladen + ontploffen | `ui/explode.js` | preview; **Axel test in de VM** |
| Bureaublad: na inloggen/ontgrendelen spiralen planeten uit de aarde; afmelden/vergrendelen het omgekeerde | `ui/world.js` (animateWorld, intro.claim) | preview; **Axel test in de VM** |
| Vergrendelen met animatie: `universe-lock` -> `universe-ctl lock`, shell bewaakt swaylock en speelt uitloop; slaapstand `--direct` | `bin/universe-lock`, `universe-idle`, `universe_shell.py` | nog niet in VM gezien |
Axel vond de eerste versie van de animaties "niet goed genoeg"; deze versie is veel rijker, zijn oordeel volgt nog.
Open: zwart moment tussen ontploffing en bureaublad (sessiestart), animaties op echte pc bekijken, pakket opnieuw bouwen
(VM heeft losse bestanden over pakket 0.2.6 heen), alleen Full HD testen (4K liet de VM vastlopen).

## Nieuw op 10 oktober: bureaublad zoals Windows (concept van Axel)
Concept: foto's in `C:\Users\Axel Van Lienen\Downloads\foto`. Wens: "een normaal bureaublad, de planeten als
achtergrond (3D), pictogrammen en een menu zoals Windows, in de stijl van de foto's; alles optioneel".
| Wat | Waar | Test |
|---|---|---|
| **3D-bureaublad** (later die avond, vervangt achtergrond + pictogrammenraster): elk programma een planeet, aarde = Persoonlijke map, mappen/bestanden in een baan; wiel = zoom, slepen = schuiven, rechts slepen = draaien, object slepen = verplaatsen; 0 % CPU in rust | `ui/world.js`, `layout.json` (space) | VM |
| Bureaubladpictogrammen: Persoonlijke map, Prullenbak, `~/Bureaublad`, snelkoppelingen; slepen in raster, F2, Delete, Nieuwe map, rechtsklikmenu's | `ui/world.js`, `backend.desktop_*` | VM |
| Taakbalk (eigen lijst, verslepen, open vensters) | `ui/dock.*`, laag `dock` | VM |
| Startmenu (zoeken, vastgemaakt, alle apps, aan/uit), Windows-toets; Windows+Tab = taakweergave | `ui/start.*`, laag `start`, `shortcuts.json` | VM |
| Indeling per gebruiker | `~/.config/universe-os/layout.json` (`config.layout`) | VM |
| Fix vensterbewaking (registry bewaren) en veilige `desktop_app()` | `toplevels.py`, `backend.py` | VM |
Testverslag: `docs/tests/aarde-mappenbaan.md`. Pakket 0.2.6 uit commit 837c3f4 gebouwd en in de test-VM geïnstalleerd
(versienummer niet verhoogd; publiceren alleen als Axel het zegt).
Test-VM: ontwikkeltoegang (SSH 127.0.0.1:2223, sudo zonder wachtwoord), gebruiker `tester` / wachtwoord `tester`.
Nog open: wereldpagina soms traag in de VM (één keer 42 s), 1024×768/4K, twee schermen, ruimtestation/sterrenstelsel uit
het concept (eventueel als achtergrond of onderdelen van het startmenu).

## Klaar en getest (tot 9 oktober)
| Wat | Versie | Test |
|---|---|---|
| Zwart scherm 0.2.0 (één `)` te veel in world.js) | 0.2.1 | VM |
| Vangnet: melding "De ruimtewereld kon niet laden" + Opnieuw proberen/Afmelden, fouten in `shell.log` (PR #33 B, wachttijd 30 s) | 0.2.5 | VM, echte WebKit: `docs/tests/zwart-scherm-0.2.5.md` |
| Vensteroverzicht werkte nooit: `python3-cffi-backend` ontbrak | 0.2.5 | VM |
| Internet-planeet met browserkeuze, geen programmabalk (PR #31 B) | 0.2.2 | VM |
| Installer: vinkje automatisch aanmelden verborgen (`branding/universe/stylesheet.qss`) | ISO 0.2.5+ | nog niet in een ISO bekeken |
| Verplichte updates: `universe-updates.service` (timer, inloggen, knop), polkit zonder wachtwoord, alleen stable (PR #35 B = knop) | 0.2.6 | VM: `docs/tests/verplichte-updates-0.2.6.md` |
| `build-deb.sh` controleert Python + JS (node staat in de bouw-VM) | — | — |
| `vm/sync-naar-vm.ps1` maakt mappen eerst leeg (verwijderde bestanden bleven in de VM) | — | — |

## Bestanden en plekken
- ISO's: `D:\UniverseOS-VMs\iso\` — nieuwste **universe-os-0.2.6-amd64.iso** (SHA-256 `87026f3c…acdc150`), nog niet door Axel getest.
- Updatebron: https://itsamefork.github.io/universe-os-apt/ — online **0.2.4** (stable + test). 0.2.5/0.2.6 **niet** gepubliceerd.
- Publiceren: snelkoppeling "Universe OS update publiceren" (`vm\publiceer-update.ps1`), wachtwoordzin uit `F:\sleutel universe os\wachtwoordzin.txt`.
- Updatesleutel (nieuw, 7 okt): `19FAEFC86A1F7E25C78408AA0189D5914EAE81F2`, map `F:\sleutel universe os` (ook kopiëren naar tweede stick). Computers met de oude sleutel (0.2.0 en ouder) krijgen geen updates.
- Test-VM: geïnstalleerd systeem, gebruiker `tester` (testwachtwoord alleen voor de VM).

## Afspraken
- ISO bouwen alleen als Axel het zegt of ChatGPT op GitHub "ja" geeft.
- ChatGPT (spoor B) volgt issue #1 en de commits; berichten daar plaatsen. Taken voor B: issue #32.
- Publiceren alleen als Axel het zegt.

## Open
1. Axel test ISO 0.2.6 op de echte pc (live, installeren, inloggen, Windows-toets, Controlecentrum > Updates).
2. 0.2.6 publiceren als update (na akkoord Axel); daarna een echte universe-os-update via de bron testen.
3. Oorzaak van het oorspronkelijke zwarte scherm op de echte pc: niet nagebootst; bij een fout nu melding + `shell.log`.
4. Chrome-beeldcorruptie: PR #34 (B) is een diagnosetool, nog niet samengevoegd; hardwaregegevens van Axel nodig.
5. PR #28 en #30 kunnen dicht (vervangen).

## 0.2.34 (GEPUBLICEERD 25 okt 14:11, apt test + stable; geen ISO)
- Bovenbalk (pil) op de BOTTOM-laag: gemaximaliseerde/fullscreen vensters en vensters die erover staan bedekken hem; vervaagt zacht; komt terug bij herstellen/sluiten. Open paneel (klik/Win+A) gaat naar TOP.
- Tests: bovenbalk-bedekt.py, bovenbalk-gedrag.py, alle-tests.sh; tests werken vanuit elke map; sneltoetsen-docs compleet.

## 0.2.35 (GEPUBLICEERD 25 okt 15:51, apt test + stable; netwerkupdate, Jesse test zelf)
- Venster-animatie als ruimtebericht: overlay (flits.html/js, OVERLAY-laag, geen invoer) met mint-hologram vanuit het dock; sluiten/minimaliseren terug. Lichte modus, eenvoudige wereld, Animaties 'Verminderd': alleen vervagen; 'Uit': niets.
- Nog niet visueel bevestigd: in de QEMU-demo (TCG) was het hologram niet te zien; moet op echte hardware gecontroleerd worden.
