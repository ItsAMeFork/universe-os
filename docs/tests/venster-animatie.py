#!/usr/bin/env python3
"""0.2.36: venster-animatie als bloem op de echte venstergrootte. Controleert de shell-logica (welke gebeurtenis, welke
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
cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('window_flits', 'flits_mode', 'play_flits', 'flits_gemeten')]
settings = {'animations': 'full'}
light = {'on': False}
ns = {'config': SimpleNamespace(settings=lambda: settings), 'grafisch': SimpleNamespace(light_active=lambda: light['on']),
      'time': time, 'log': print, 'GLib': SimpleNamespace(timeout_add=lambda *a: 1)}
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
check('lichte modus -> snel', s.window_flits([W('1'), W('6')])[0]['snel'] is True)
light['on'] = False; s.lite = 'test'
check('eenvoudige wereld -> snel', s.window_flits([W('1')])[0]['snel'] is True)
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
check('grim met time-out (nooit hangen)', 'timeout=timeout' in (SH / 'venstermeting.py').read_text())

s = shell(echte_play=True)
s.flits_overlay = lambda: over
over.play.reset_mock()
venstermeting.inhoud = lambda *a: 'PIX'
s.toplevels = SimpleNamespace(list=lambda: [W('5', activated=True)])
s.flits_cache = {}
s.flits_wacht = {'5': {'soort': 'open', 'wid': '5', 'snel': False, 'gevraagd': time.monotonic()}}
s.flits_gemeten((WD, HD, scherm((37, 41, 250, 180))))
check('gemeten -> bloem op de echte rechthoek met echte inhoud',
      over.play.called and over.play.call_args[0][0][0]['rect'] == (37, 41, 250, 180) and s.flits_cache['5']['pix'] == 'PIX')
over.play.reset_mock()
s.toplevels = SimpleNamespace(list=lambda: [])
s.flits_wacht = {'6': {'soort': 'open', 'wid': '6', 'snel': False, 'gevraagd': time.monotonic()}}
s.flits_gemeten((WD, HD, scherm((37, 41, 250, 180))))
check('al weg bij het meten (splash/launcher) -> niets', not over.play.called and '6' not in s.flits_cache)
s.toplevels = SimpleNamespace(list=lambda: [W('7', activated=True)])
s.flits_wacht = {'7': {'soort': 'open', 'wid': '7', 'snel': False, 'gevraagd': time.monotonic() - 2}}
s.flits_gemeten((WD, HD, scherm((37, 41, 250, 180))))
check('te late meting -> geen bloem, wel onthouden voor sluiten', not over.play.called and '7' in s.flits_cache)
s.toplevels = SimpleNamespace(list=lambda: [W('8', activated=True)])
s.flits_wacht = {'8': {'soort': 'open', 'wid': '8', 'snel': False, 'gevraagd': time.monotonic()}}
s.flits_gemeten(None)
check('opname mislukt -> overslaan', not over.play.called)

# the flower itself
import flits
A = lambda soort, snel=False: {'soort': soort, 'snel': snel, 'rect': (100, 100, 800, 500), 'start': 0.0, 'traag': 1.0}
check('openen goed zichtbaar (0.8-1.2 s)', 0.8 <= flits.DUUR['open'] <= 1.2)
check('sluiten/minimaliseren goed zichtbaar (0.8-1.2 s)', all(0.8 <= flits.DUUR[k] <= 1.2 for k in ('sluit', 'min')))
check('easing in-out (traag begin en eind)', flits.ease_in_out(0.1) < 0.1 and flits.ease_in_out(0.9) > 0.9 and abs(flits.ease_in_out(0.5) - 0.5) < 1e-9)
check('snel-modus kort (<=160 ms)', flits.SNEL <= 0.16)
f0, f1 = flits.bloem_frame(A('open'), 0.0, None), flits.bloem_frame(A('open'), 0.999, None)
check('open begint als punt in het midden van het venster', f0['p'] == 0 and (f0['cx'], f0['cy']) == (500, 350))
check('open eindigt op de exacte rechthoek, afdekking weg', f1['p'] > 0.99 and f1['schaal'] > 0.99 and f1['dek'] < 0.01)
check('bloem dekt bij p=1 de hele rechthoek', flits.bloem_straal(800, 500) * 0.82 >= math.hypot(400, 250) - 0.01)
same = all(abs(flits.bloem_frame(A('open'), t, None)['p'] - flits.bloem_frame(A('sluit'), 1 - t, None)['p']) < 1e-9 for t in (0.1, 0.3, 0.5, 0.9))
check('sluiten = open precies andersom', same)
fm = flits.bloem_frame(dict(A('min'), soort='min'), 0.9, (960, 1040))
check('minimaliseren vouwt dicht richting het dock', fm['cy'] > 700 and fm['p'] < 0.3)
check('voortgang klaar na de duur', flits.voortgang(A('open'), 1.01) is None and flits.voortgang(A('open'), 0.5) is not None and flits.voortgang(A('sluit'), 0.91) is None)
check('traag-factor alleen via testbestand', flits.TRAAG_BESTAND == '/tmp/universe-flits-traag')
fsrc = (SH / 'flits.py').read_text()
check('overlay: OVERLAY, geen toetsenbord, lege invoerregio, geen WebKit',
      'Layer.OVERLAY' in fsrc and 'KeyboardMode.NONE' in fsrc and 'input_shape_combine_region(cairo.Region()' in fsrc and 'WebKit' not in fsrc.split('"""', 2)[2])
check('zonder RGBA-visual geen overlay (geen zwart scherm)', 'if not self.transparent:' in fsrc)
check('kapot frame wordt overgeslagen', 'animatie overgeslagen' in fsrc)
check('overlay verdwijnt als alles klaar is', 'self.window.hide()' in fsrc)
check('afdekking alleen op de eigen rechthoek (nooit volledig scherm)', 'cr.rectangle(x, y, bw, bh)' in fsrc)
sys.exit(1 if fails else 0)
