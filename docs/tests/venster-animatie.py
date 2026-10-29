#!/usr/bin/env python3
"""0.2.38: venster-animatie als portaal vanuit de aangeklikte planeet/snelkoppeling naar de echte venstergrootte. Controleert de shell-logica (welke gebeurtenis, welke
modus, geen dubbele animaties bij Wine/X11-vensters en splash-schermen), de vensterherkenning in een schermopname
(venstermeting.py) en de bloem zelf (open = punt -> exacte rechthoek, sluiten = precies andersom, duur)."""
import ast, math, sys, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
SH = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell'
sys.path.insert(0, str(SH))
src = (SH / 'universe_shell.py').read_text(encoding='utf-8')
tree = ast.parse(src)
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Shell')
cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('window_flits', 'flits_mode', 'play_flits', 'flits_gemeten', 'launch_bron', 'flits_scherm', 'flits_basis', 'flits_achter', 'flits_voor_opname', 'flits_ontdooi', 'flits_bevries', 'onthul_onthoud', 'onthul_apps')]
settings = {'animations': 'full'}
light = {'on': False}
ns = {'config': SimpleNamespace(settings=lambda: settings), 'grafisch': SimpleNamespace(light_active=lambda: light['on']),
      'time': time, 'log': print, 'GLib': SimpleNamespace(timeout_add=lambda *a: 1), 'Gdk': None, 'BRON_GELDIG': 30, 'VENSTERS_BESTAND': '/tmp/universe-test-vensters.json', 'os': __import__('os')}
exec(compile(ast.Module(body=[cls], type_ignores=[]), 'universe_shell.py', 'exec'), ns)
fails = []


def check(name, ok):
    print(('OK   ' if ok else 'FOUT ') + name)
    ok or fails.append(name)


def shell(echte_play=False):
    s = ns['Shell']()
    s.lite = None
    s.dock = SimpleNamespace(window=SimpleNamespace(get_visible=lambda: True))
    if not echte_play:
        s.play_flits = Mock()
    return s


W = lambda i, **k: dict({'id': i, 'appId': 'app' + i, 'title': 't' + i, 'minimized': False, 'maximized': False,
                         'fullscreen': False, 'activated': False}, **k)
soorten = lambda e: [x['soort'] for x in e]
s = shell()
check('eerste momentopname animeert niets', s.window_flits([W('1')]) == [])
e = s.window_flits([W('1'), W('2', activated=True)])
check('nieuw venster -> open (bloem), vol', soorten(e) == ['open'] and e[0]['wid'] == '2' and e[0]['snel'] is False)
e = s.window_flits([W('1'), W('2', activated=True, maximized=True)])
check('maximaliseren -> alleen opnieuw meten', soorten(e) == ['meet'])
e = s.window_flits([W('1'), W('2', minimized=True)])
check('minimaliseren -> min', soorten(e) == ['min'])
e = s.window_flits([W('1'), W('2', activated=True)])
check('herstellen uit dock -> open', soorten(e) == ['open'])
e = s.window_flits([W('1')])
check('sluiten -> sluit', soorten(e) == ['sluit'] and e[0]['wid'] == '2')
e = s.window_flits([W('1'), W('3'), W('4'), W('5')])
check('drie snel na elkaar -> drie bloemen', soorten(e) == ['open'] * 3)
# Wine/Xwayland: the same program window unmaps and maps again (new id, same appId + title)
s.window_flits([W('1'), W('3'), W('4')])
e = s.window_flits([W('1'), W('3'), W('4'), dict(W('9'), appId='app5', title='t5')])
check('Wine/X11-venster dat opnieuw mapt -> geen tweede bloem', e == [])
e = s.window_flits([W('1'), W('3'), W('4'), W('9'), dict(W('10'), appId='app9', title='t9'), dict(W('11'), appId='app9', title='t9')])
check('twee keer hetzelfde venster tegelijk -> één bloem', soorten(e) == ['open'])
settings['animations'] = 'reduced'
check('verminderd -> snel', s.window_flits([W('1')])[0]['snel'] is True)
settings['animations'] = 'full'; light['on'] = True
ev = s.window_flits([W('1'), W('6')])[0]
check('lichte modus -> dezelfde animatie in lichte kwaliteit (niet meer alleen vervagen)', ev['snel'] is False and ev['kwaliteit'] == 'licht')
light['on'] = False; s.lite = 'test'
ev = s.window_flits([W('1')])[0]
check('eenvoudige wereld -> lichte kwaliteit', ev['snel'] is False and ev['kwaliteit'] == 'licht')
s.lite = None; settings['animations'] = 'off'
check('animaties uit -> niets', s.window_flits([W('1'), W('7')]) == [] and s.window_flits([W('1')]) == [])
settings['animations'] = 'full'
check('windows_update roept window_flits aan', 'self.window_flits(windows)' in src)

# play_flits: closing uses the measured rectangle; never measured (splash, no border) -> nothing
s = shell(echte_play=True)
over = Mock(); over.size = lambda: (1920, 1080)
s.flits_overlay = lambda: over
s.flits_dock = lambda: (960, 1040)
s.flits_meet = Mock()
s.flits_cache = {'2': {'rect': (100, 120, 800, 500), 'pix': 'PIX'}}
s.flits_bronnen = {'2': (640, 360)}
s.play_flits([{'soort': 'sluit', 'wid': '2', 'snel': False, 'van': 'dock'}])
arg = over.play.call_args[0][0][0]
check('sluiten speelt op de gemeten rechthoek met inhoud', arg['rect'] == (100, 120, 800, 500) and arg['pix'] == 'PIX')
check('na sluiten vergeten', '2' not in s.flits_cache)
over.play.reset_mock()
s.play_flits([{'soort': 'sluit', 'wid': '77', 'snel': False, 'van': 'dock'}])
check('nooit gemeten venster (splash) -> geen animatie', not over.play.called)
s.play_flits([{'soort': 'open', 'wid': '5', 'snel': False, 'van': 'dock'}])
check('openen gaat eerst via de meting', s.flits_meet.called and not over.play.called)

# flits_gemeten: gone/not active -> nothing; measured -> flower on the rectangle
import venstermeting
WD, HD = 400, 300
def scherm(rect=None):
    data = bytearray(b'\x05\x08\x15' * WD * HD)
    if rect:
        x, y, w, h = rect
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                rand = yy < y + 2 or yy >= y + h - 2 or xx < x + 2 or xx >= x + w - 2
                kleur = venstermeting.RAND if rand else (venstermeting.TITEL if yy < y + 30 else b'\xee\xee\xee')
                # rounded corners (radius 10): outside the circle stays background
                cx = x + 10 if xx < x + 10 else (x + w - 11 if xx > x + w - 11 else None)
                cy = y + 10 if yy < y + 10 else None  # labwc: only the top corners are rounded
                if cx is not None and cy is not None and math.hypot(xx - cx, yy - cy) > 10:
                    continue
                if cx is not None and cy is not None and math.hypot(xx - cx, yy - cy) > 8:
                    kleur = venstermeting.RAND
                i = (yy * WD + xx) * 3
                data[i:i + 3] = kleur
    return bytes(data)

r = venstermeting.vind_actief(WD, HD, scherm((37, 41, 250, 180)))
check('vensterrand gevonden op de exacte rechthoek (%s)' % (r,), r == (37, 41, 250, 180))
check('geen rand -> None (geen gok)', venstermeting.vind_actief(WD, HD, scherm()) is None)
klein = venstermeting.vind_actief(WD, HD, scherm((10, 10, 90, 50)))
check('te klein (tooltip/splash) -> None', klein is None)
ppm = b'P6\n# grim\n2 1\n255\n' + b'\x01\x02\x03\x04\x05\x06'
check('PPM van grim lezen', venstermeting.lees_ppm(ppm) == (2, 1, b'\x01\x02\x03\x04\x05\x06'))
check('grim met time-out (nooit hangen)', 'threading.Timer(timeout, proc.kill)' in (SH / 'venstermeting.py').read_text())

# 0.2.38: the window comes out of what was clicked
s = shell()
s.worlds = [SimpleNamespace(view=SimpleNamespace(get_zoom_level=lambda: 1.0))]
s.start = SimpleNamespace(view=SimpleNamespace(get_zoom_level=lambda: 1.5), window=SimpleNamespace(get_allocated_width=lambda: 990))
s.flits_overlay = lambda: SimpleNamespace(size=lambda: (1920, 1080), wek=lambda: True)
b = s.launch_bron({'x': 100, 'y': 200, 'bron': 'start'})
check('start-menu: paginapunt -> schermpunt (zoom, gecentreerd, bovenmarge)', b[:2] == ((1920 - 990) / 2 + 150, 300 + 56))
check('planeet in de wereld: zelfde punt', s.launch_bron({'x': 640, 'y': 360, 'bron': 'world'})[:2] == (640, 360))
check('Claude/zonder punt: geen bron', s.launch_bron({'id': 'x'}) is None)
s.window_flits([W('1')])
e = s.window_flits([W('1'), W('2', activated=True)])
check('nieuw venster na klik -> komt uit de planeet', e[0].get('bron') == (640, 360) and s.flits_bron is None and s.flits_bronnen['2'] == (640, 360))
e = s.window_flits([W('1'), W('2'), W('3')])
check('volgend venster zonder klik -> geen bron (midden)', 'bron' not in e[0])

s = shell(echte_play=True)
s.flits_overlay = lambda: over
over.play.reset_mock()
venstermeting.inhoud = lambda *a: 'PIX'
s.toplevels = SimpleNamespace(list=lambda: [W('5', activated=True)])
s.flits_cache = {}
s.flits_wacht = {'5': {'soort': 'open', 'wid': '5', 'snel': False, 'gevraagd': time.monotonic()}}
s.flits_gemeten((WD, HD, scherm((37, 41, 250, 180))))
check('gemeten -> portaal op de echte rechthoek met echte inhoud',
      over.play.called and over.play.call_args[0][0][0]['rect'] == (37, 41, 250, 180) and s.flits_cache['5']['pix'] == 'PIX')
over.play.reset_mock()
s.toplevels = SimpleNamespace(list=lambda: [])
s.flits_wacht = {'6': {'soort': 'open', 'wid': '6', 'snel': False, 'gevraagd': time.monotonic()}}
s.flits_gemeten((WD, HD, scherm((37, 41, 250, 180))))
check('al weg bij het meten (splash/launcher) -> niets', not over.play.called and '6' not in s.flits_cache)
s.toplevels = SimpleNamespace(list=lambda: [W('7', activated=True)])
s.flits_wacht = {'7': {'soort': 'open', 'wid': '7', 'snel': False, 'gevraagd': time.monotonic() - 2}}
s.flits_gemeten((WD, HD, scherm((37, 41, 250, 180))))
check('te late meting -> geen portaal, wel onthouden voor sluiten', not over.play.called and '7' in s.flits_cache)
s.toplevels = SimpleNamespace(list=lambda: [W('8', activated=True)])
s.flits_wacht = {'8': {'soort': 'open', 'wid': '8', 'snel': False, 'gevraagd': time.monotonic()}}
s.flits_gemeten(None)
check('opname mislukt -> overslaan', not over.play.called)

# the portal itself
import flits
A = lambda soort, snel=False: {'soort': soort, 'snel': snel, 'rect': (100, 100, 800, 500), 'start': 0.0, 'traag': 1.0}
check('openen goed zichtbaar (0.8-1.2 s)', 0.8 <= flits.DUUR['open'] <= 1.2)
check('sluiten/minimaliseren goed zichtbaar (0.8-1.2 s)', all(0.8 <= flits.DUUR[k] <= 1.2 for k in ('sluit', 'min')))
check('easing in-out (traag begin en eind)', flits.ease_in_out(0.1) < 0.1 and flits.ease_in_out(0.9) > 0.9 and abs(flits.ease_in_out(0.5) - 0.5) < 1e-9)
check('snel-modus kort (<=160 ms)', flits.SNEL <= 0.16)
P = lambda soort, bron=(300, 900): dict(A(soort), bron=bron, scherm=(1920, 1080))
f0, f1 = flits.portaal_frame(P('open'), 0.0), flits.portaal_frame(P('open'), 0.999)
check('open begint klein bij de aangeklikte planeet/snelkoppeling', f0['p'] == 0 and abs(f0['cx'] - 300) < 1e-6 and abs(f0['cy'] - 900) < 1e-6
      and f0['rect'][2] == flits.PORTAAL_START)
check('open eindigt op de exacte rechthoek, afdekking weg', f1['p'] > 0.99 and abs(f1['rect'][2] - 800) < 2 and abs(f1['rect'][0] - 100) < 2 and f1['dek'] < 0.01)
fm_ = flits.portaal_frame(P('open'), 0.5)
lijn = ((fm_['cx'] - 300) * (350 - 900) - (fm_['cy'] - 900) * (500 - 300))
check('gebogen baan (geen rechte lijn) met lichtpunt bij de bron', abs(lijn) > 1000 and flits.portaal_frame(P('open'), 0.17)['flare'] > 0.9)
check('zonder bron: vanuit het midden van het scherm', flits.portaal_bron(dict(A('open'), scherm=(1920, 1080))) == (960, 540))
same = all(abs(flits.portaal_frame(P('open'), t)['p'] - flits.portaal_frame(P('sluit'), 1 - t)['p']) < 1e-9 for t in (0.1, 0.3, 0.5, 0.9))
check('sluiten = open precies andersom, terug naar de bron', same and abs(flits.portaal_frame(P('sluit'), 0.999)['cx'] - 300) < 2)
fm = flits.portaal_frame(dict(A('min'), soort='min', dock=(960, 1040)), 0.9)
check('minimaliseren gaat naar het dock', fm['cy'] > 900 and fm['p'] < 0.1)
sp = flits.portaal_spoor(P('open'), 0.5, flits.KWALITEIT['vol']['spoor'])
check('lichtspoor: lichte modus minder punten, zelfde baan', len(flits.portaal_spoor(P('open'), 0.5, flits.KWALITEIT['licht']['spoor'])) < len(sp) and sp[0][:2] == (fm_['cx'], fm_['cy']))
check('één tekenpad, kwaliteit als parameter', flits.kwaliteit({'kwaliteit': 'licht'}) is flits.KWALITEIT['licht'] and flits.kwaliteit({}) is flits.KWALITEIT['vol']
      and flits.KWALITEIT['licht']['tick'] >= 30 and not flits.KWALITEIT['licht']['inhoud'])
check('lichte modus: zelfde duur', flits.duur(dict(A('open'), kwaliteit='licht')) == flits.duur(A('open')))
check('voortgang klaar na de duur', flits.voortgang(A('open'), 1.01) is None and flits.voortgang(A('open'), 0.5) is not None and flits.voortgang(A('sluit'), 0.91) is None)
check('traag-factor alleen via testbestand', flits.TRAAG_BESTAND == '/tmp/universe-flits-traag')
fsrc = (SH / 'flits.py').read_text()
check('overlay: OVERLAY, geen toetsenbord, lege invoerregio, geen WebKit',
      'Layer.OVERLAY' in fsrc and 'KeyboardMode.NONE' in fsrc and 'input_shape_combine_region(cairo.Region()' in fsrc and 'WebKit' not in fsrc.split('"""', 2)[2])
check('zonder RGBA-visual geen overlay (geen zwart scherm)', 'if not self.transparent:' in fsrc)
check('kapot frame wordt overgeslagen', 'animatie overgeslagen' in fsrc)
check('overlay verdwijnt als alles klaar is', 'self.window.hide()' in fsrc)
check('afdekking alleen op de eigen rechthoek (nooit volledig scherm)', 'cr.rectangle(x, y, bw, bh)' in fsrc)
# 0.2.38 live test: overlay still 1x1 (never shown) -> ask the monitor, never the top-left corner
s = shell()
s.flits_overlay = lambda: SimpleNamespace(size=lambda: (1, 1))
geo = SimpleNamespace(width=1920, height=1080)
ns['Gdk'] = SimpleNamespace(Display=SimpleNamespace(get_default=lambda: SimpleNamespace(get_primary_monitor=lambda: None, get_monitor=lambda i: SimpleNamespace(get_geometry=lambda: geo))))
check('overlay nog 1x1: schermmaat van de monitor', s.flits_scherm() == (1920, 1080))
ns['Gdk'] = None
check('zonder monitor: geen crash', s.flits_scherm() == (1, 1))
check('trage pc: bron blijft 30 s geldig', 'BRON_GELDIG = 30' in (SH / 'universe_shell.py').read_text() and 't - bron[2] < BRON_GELDIG' in (SH / 'universe_shell.py').read_text())
# 0.2.38 live test: the first program after logging in also gets its portal (snapshot when the window list connects)
s = shell()
s.toplevels = SimpleNamespace(list=lambda: [])
s.flits_basis()
e = s.window_flits([W('7', activated=True)])
check('eerste programma na inloggen: ook een portaal', [x['soort'] for x in e] == ['open'])
s = shell()
s.toplevels = SimpleNamespace(list=lambda: [W('3')])
s.flits_basis()
check('vensters die al open waren bij herstart: geen portaal', s.window_flits([W('3')]) == [])
# 0.2.38 live test: the start menu is already hidden when the launch arrives (allocated width 1): use its fixed width
s = shell()
s.worlds = []
s.start = SimpleNamespace(view=SimpleNamespace(get_zoom_level=lambda: 1.0), window=SimpleNamespace(get_allocated_width=lambda: 1, get_size_request=lambda: (660, -1)))
s.flits_overlay = lambda: SimpleNamespace(size=lambda: (1920, 1080), wek=lambda: True)
check('menu al verborgen: snelkoppeling op de juiste plek', s.launch_bron({'x': 488, 'y': 347, 'bron': 'start'})[:2] == (488 + 630, 347 + 56))

# 0.2.38 live2: the cover shows what was behind the window (screenshot right after the click), not a dark block
from gi.repository import GLib as _G
ns['GLib'].Bytes = _G.Bytes
s = shell()
achter_shot = (WD, HD, scherm((500, 500, 200, 150)))  # anything; the window is not in it
s.flits_voor = (time.monotonic() - 1, achter_shot)
r = s.flits_achter((37, 41, 250, 180), {'bron': (1, 2), 'gevraagd': time.monotonic()})
check('achtergrond onder het nieuwe venster uitgeknipt', 'achter' in r and r['achter_xy'] == (37, 41)
      and (r['achter'].get_width(), r['achter'].get_height()) == (250, 180))
check('opname van na het verschijnen -> niet gebruiken', s.flits_achter((37, 41, 250, 180), {'bron': (1, 2), 'gevraagd': time.monotonic() - 5}) == {})
check('zonder klik (geen bron) -> geen achtergrond', s.flits_achter((37, 41, 250, 180), {'gevraagd': time.monotonic()}) == {})
import cairo
from gi.repository import GdkPixbuf
F = flits.Flits.__new__(flits.Flits)
img = cairo.ImageSurface(cairo.FORMAT_ARGB32, 400, 300)
cr = cairo.Context(img)
F.teken_dek(cr, {}, 100, 100, 200, 100, 1.0)
px = lambda x, y: img.get_data()[(y * img.get_stride() + x * 4) + 3]
check('donkere afdekking zonder opname: zachte randen (geen blok)', px(150, 150) == 255 and 0 < px(150, 88) < 255 and px(150, 60) == 0)
img = cairo.ImageSurface(cairo.FORMAT_ARGB32, 400, 300)
cr = cairo.Context(img)
pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 200, 100)
pb.fill(0x336699ff)
F.teken_dek(cr, {'achter': pb, 'achter_xy': (100, 100)}, 100, 100, 200, 100, 1.0)
d = img.get_data(); i = 150 * img.get_stride() + 150 * 4
check('afdekking met opname: precies de achtergrond, buiten het venster niets', (d[i + 2], d[i + 1], d[i]) == (0x33, 0x66, 0x99) and px(150, 95) == 0)
check('nieuw venster meteen meten (geen 50 ms wachten)', "0 if e['soort'] == 'open' else 50" in (SH / 'universe_shell.py').read_text())
# live2: wek() (overlay ready after a click) must not take the frame timer: the portal was never drawn
src = (SH / 'flits.py').read_text()
wek = src[src.index('def wek('):src.index('def wek_klaar')]
check('wek() gebruikt niet de beeldtimer (self.tick)', 'self.tick =' not in wek)
# live2: the screen from before the window covers it once grim has its picture (never before: grim would see it)
import subprocess as _sp, types as _t
calls = []
class _P:
    def __init__(self, *a, **k):
        import os
        r, w = os.pipe()
        os.write(w, b'P6\n2 1\n255\n' + b'\x01' * 6); os.close(w)
        self.stdout = os.fdopen(r, 'rb')
    def wait(self): return 0
    def kill(self): pass
_orig = venstermeting.subprocess.Popen
venstermeting.subprocess.Popen = _P
r = venstermeting.opname(timeout=2, gemaakt=lambda: calls.append('gemaakt'))
venstermeting.subprocess.Popen = _orig
check('grim: melding "foto gemaakt" zodra grim schrijft, daarna de hele opname', calls == ['gemaakt'] and r == (2, 1, b'\x01' * 6))
F = flits.Flits.__new__(flits.Flits)
F.anims, F.bevroren, F.transparent, F.tick = [], None, True, 1
F.window = SimpleNamespace(get_visible=lambda: True, queue_draw=lambda: None, show_all=lambda: None, hide=lambda: None)
pb2 = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 40, 30); pb2.fill(0x204060ff)
F.bevries(pb2)
img = cairo.ImageSurface(cairo.FORMAT_ARGB32, 40, 30); cr = cairo.Context(img)
F.draw(SimpleNamespace(get_allocated_width=lambda: 40, get_allocated_height=lambda: 30), cr)
d = img.get_data(); i = 10 * img.get_stride() + 10 * 4
check('vastgehouden scherm: het oude beeld over alles (nieuw venster onzichtbaar)', (d[i + 2], d[i + 1], d[i], d[i + 3]) == (0x20, 0x40, 0x60, 255))
F.play([{'soort': 'open', 'wid': '9', 'rect': (0, 0, 10, 10)}])
check('portaal neemt het over (vasthouden stopt)', F.bevroren is None)
s = shell(echte_play=True)
s.flits = SimpleNamespace(bevroren=('x', 0), ontdooi=lambda: setattr(s.flits, 'bevroren', None))
s.flits_ontdooi()
check('meting mislukt terwijl vastgehouden: echte scherm terug, niet opnieuw vasthouden', s.flits.bevroren is None and s.flits_ontdooid)
sys.exit(1 if fails else 0)
