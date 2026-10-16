# Universe OS – perf/henk-snelheid

Gebaseerd op de nieuwste main (f160975, merge van PR #48). Vier Claude-agents werkten elk in een eigen worktree aan één gebied. Het doel was geen zichtbare verandering en geen gedragsverandering.

## Wat er sneller is
- **Opstarten (session.py):** `xml.sax.saxutils` wordt nu pas geladen als het nodig is (lazy import). Daardoor worden urllib, http, ssl en email niet meer bij de start van de shell geladen. De importtijd gaat van 36,4 naar 11,6 ms en de wandkloktijd van 47,3 naar 23,7 ms. De rc.xml-uitvoer is byte-voor-byte gelijk.
- **Zoeken (backend.py, startmenu):**
  - een snelle route voor ASCII bij het opvouwen van tekst (hoofdletters en accenten). Het bouwen van de index gaat van 24,5 naar 11,4 ms per 20.000 namen.
  - een kortere matchlus voor bestanden. Dat gaat van ~18,7 naar ~2,6 ms per toetsaanslag bij 60.000 namen.
  - de opgevouwen app-teksten worden bewaard, en die cache wordt ongeldig bij `apps_changed`.
  - de wachtrij is nu een `deque`.
  - Voor 6 testzoekopdrachten zijn de resultaten identiek aan de oude code.
- **Rust (universe_shell.py):**
  - `watch_lock` doet nog maar 1 `pgrep` per tick in plaats van 2 (15,3 naar 7,1 ms per tick).
  - `status_tick` stuurt `status` en `auto` alleen naar het paneel als er iets veranderd is. Dat zijn ~12 WebKit-berichten per minuut minder. Bij het laden haalt de paneelpagina zelf status op met `refresh()` (gecontroleerd).
- **UI (world.js):** de `gfx=soft`-vlag wordt één keer gelezen in plaats van bij elk beeld. Dat levert verwaarloosbare winst op.

## Eerlijk
De codebase was al goed op prestaties ingericht: veel dingen werden al uitgesteld, animaties stonden al stil in rust en er waren al caches. De winst is daarom vooral te merken in het startmenu-zoeken en bij de shell-start, niet als "dramatisch" sneller overal.

## Tests en risico
- De repo heeft geen geautomatiseerde testsuite (docs/tests bevat handmatige rapporten). Gedraaid zijn `py_compile` en `node --check` op alle gewijzigde bestanden: alles slaagt.
- GTK en WebKit zijn niet op de box geïnstalleerd, dus de echte shell is niet live gestart. Een rooktest in een VM wordt aangeraden.
- Risico bij `pgrep -x 'gtklock|swaylock'`: dit is een regex en moet hetzelfde werken (handmatig gecontroleerd).
- Risico bij `status_tick`: als het paneel opnieuw wordt gebouwd, haalt de pagina zelf status op, dus dat is ok.

## Ronde 2: doorlopende pipeline (16 okt, 15:41–15:50)
Er draaiden steeds 4 Claude-lanes tegelijk, in totaal 35 lanes. Daarvan zijn er 11 gemerged. De rest vond niets wat veilig was. De details staan per lane in PERF_NOTES_R*.md.
- **earth.png:** verlustloos opnieuw opgeslagen, van 326.003 naar 289.391 bytes (−11%). De pixels zijn identiek (RGBA-vergelijking).
- **plugins.py:** de config wordt gecachet op mtime, grootte en inode. `public_list` gaat van 0,57 naar 0,13 ms.
- **brein.py:** het schema wordt nog maar één keer per proces gecontroleerd. `connect` gaat van 0,215 naar 0,056 ms (~35 aanroeppunten).
- **auto_accept.active():** gaat niet meer via `public()`, dus niet meer via een Brein-query. Van 0,331 naar 0,012 ms per aanroep.
- **backend.py, bestandsindex:** gebruikt minder geheugen, van 16,9 naar 9,3 MB per 60.000 bestanden. De zoekuitvoer is identiek (md5).
- **world.js:**
  - `project()` cachet de trig-waarden.
  - `ring()` gebruikt vooraf berekende sinus en cosinus, ~3x sneller (14 naar 4 µs per frame).
  - De hash per planeet wordt gecachet.
  - De uitvoer is bit-identiek.
- **brein-nevel.js:** `motionOn()` wordt 1x per frame aangeroepen in plaats van ~170x. Sterposities worden gecachet per canvasgrootte.
- **explode.js:** kleine optimalisatie per frame.
- **webview.py en de broadcast:**
  - er is één gedeelde JSON-encoder (0,58 naar 0,07 µs voor een string).
  - een broadcast wordt 1x geserialiseerd in plaats van per surface.

Gestopt omdat de Claude-sessielimiet op was, bij zowel sonnet als haiku. De limiet reset om 20:30 (Amsterdam).
Na het mergen slagen `py_compile` en `node --check` nog steeds. De patch staat in perf.patch, met binary voor de png (`git apply` werkt).

## Ronde 3: doorlopende pipeline (16 okt, 20:45–21:10)
Na de reset van 20:30 draaiden weer steeds 4 Claude-lanes tegelijk (sonnet, daarna haiku), tot de sessielimiet opnieuw op was (reset 01:40). Ongeveer 70 lanes, 15 gemerged; de rest vond niets wat nog veilig was. Details per lane in PERF_NOTES_R*.md.
- **Afbeeldingen (verlustloos, pixels identiek):** `vergrendeld.png` (vergrendelscherm) van 1.063.032 naar 849.956 bytes (−20%), `kern.png` −3,2%, `overgang.png` −17,5% (alleen repo, niet geïnstalleerd).
- **plugins.py `public_list()`:** config één keer lezen per aanroep in plaats van ~20 keer: 110,8 naar 10,4 µs (~10x).
- **screen.py `status()`:** de beschikbaarheidscheck nog maar 1x in plaats van 4x: 147 naar 41 µs.
- **ai_provider.py `launch_plan()`:** de instructies (uitleg.md + Brein-query) worden 1x per start gebouwd in plaats van 2x (~0,7 ms per start).
- **universe_mcp.py:** `recoll_index`, `base64`, `subprocess` en `socket` pas laden als een tool ze nodig heeft. Opstart van de MCP-server van 26,2 naar ~19–20 ms.
- **world.js `drawBoom()` (login-explosie):** trig en kleurstrings per frame in plaats van per vonk, ~1/3 sneller; uitvoer bit-identiek.
- **planets-hq.js:** kraters die een pixel nooit raken overslaan vóór de `acos`: planeet tekenen ~11% sneller, pixels identiek.
- **Geheugen:**
  - backend.py: de bestandsindex (~9,8 MB) wordt 61 s na het bouwen vrijgegeven in plaats van de hele sessie te blijven.
  - accounts.py: afgebroken inlogflows (en hun callback-server) worden na 15 min opgeruimd.
  - buddy_hints.py: `shown_today` wordt per dag geleegd, groeit niet meer onbeperkt.
- **IPC (toplevels.py, universe_shell.py):** een burst vensterevents geeft nog 1 idle-callback (1000 events: 1000 naar 1); de venstersnapshot wordt niet meer dubbel gekopieerd.
- **build-deb.sh:** de `node --check` van ui/*.js loopt parallel: 2,17 naar 0,40 s (alleen bij het bouwen).

Na het mergen slagen `py_compile`, `node --check` en `bash -n` op alle gewijzigde bestanden. perf.patch is opnieuw gemaakt vanaf f160975 (met binary, `git apply --check` werkt). Nog steeds niet live getest in GTK/WebKit: rooktest in een VM aanbevolen.
