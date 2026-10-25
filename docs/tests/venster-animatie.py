#!/usr/bin/env python3
"""0.2.35: venster-animatie (hologram-transmissie). Controleert de shell-logica (welke gebeurtenis, welke modus),
de overlay zonder invoer en de pagina (duur, gloed alleen in de volle modus)."""
import ast, json, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
SHELL = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'
src = SHELL.read_text(encoding='utf-8')
tree = ast.parse(src)
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Shell')
cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('window_flits', 'flits_mode')]
settings = {'animations': 'full'}
light = {'on': False}
ns = {'config': SimpleNamespace(settings=lambda: settings), 'grafisch': SimpleNamespace(light_active=lambda: light['on'])}
exec(compile(ast.Module(body=[cls], type_ignores=[]), str(SHELL), 'exec'), ns)
fails = []


def check(name, ok):
    print(('OK   ' if ok else 'FOUT ') + name)
    ok or fails.append(name)


def shell():
    s = ns['Shell']()
    s.lite = None
    s.dock = SimpleNamespace(window=SimpleNamespace(get_visible=lambda: True))
    s.play_flits = Mock()
    return s


W = lambda i, **k: dict({'id': i, 'minimized': False, 'maximized': False, 'fullscreen': False}, **k)
s = shell()
check('eerste momentopname animeert niets', s.window_flits([W('1')]) == [])
e = s.window_flits([W('1'), W('2')])
check('nieuw venster -> open vanuit dock, vol', e == [{'soort': 'open', 'max': False, 'van': 'dock', 'snel': False}])
e = s.window_flits([W('1'), W('2', maximized=True)])
check('maximaliseren is geen nieuwe animatie', e == [])
e = s.window_flits([W('1', minimized=True), W('2', maximized=True)])
check('minimaliseren -> min', [x['soort'] for x in e] == ['min'])
e = s.window_flits([W('1'), W('2', maximized=True)])
check('herstellen uit dock -> open', [x['soort'] for x in e] == ['open'])
e = s.window_flits([W('1')])
check('sluiten -> sluit, met max-vak', e and e[0]['soort'] == 'sluit' and e[0]['max'] is True)
e = s.window_flits([W('1'), W('3'), W('4'), W('5')])
check('drie snel na elkaar -> drie berichten', [x['soort'] for x in e] == ['open'] * 3)
settings['animations'] = 'reduced'
check('verminderd -> snel', s.window_flits([W('1')])[0]['snel'] is True)
settings['animations'] = 'full'; light['on'] = True
check('lichte modus -> snel', s.window_flits([W('1'), W('6')])[0]['snel'] is True)
light['on'] = False; s.lite = 'test'
check('eenvoudige wereld -> snel', s.window_flits([W('1')])[0]['snel'] is True)
s.lite = None; settings['animations'] = 'off'
check('animaties uit -> niets', s.window_flits([W('1'), W('7')]) == [] and s.window_flits([W('1')]) == [])
settings['animations'] = 'full'
s.dock = None
check('geen dock -> vanuit midden', s.window_flits([W('1'), W('8')])[0]['van'] == 'midden')
check('windows_update roept window_flits aan', 'self.window_flits(windows)' in src)

FL = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/flits.py'
fsrc = FL.read_text(encoding='utf-8')
ft = ast.parse(fsrc)
keep = [n for n in ft.body if (isinstance(n, ast.FunctionDef) and n.name in ('ease_out', 'ease_in', 'vak', 'frame'))
        or (isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') in ('DUUR', 'SNEL'))]
fns = {}
import math; fns['math'] = math
exec(compile(ast.Module(body=keep, type_ignores=[]), str(FL), 'exec'), fns)
frame, DUUR, SNEL = fns['frame'], fns['DUUR'], fns['SNEL']
A = lambda soort, snel=False, mx=False: {'soort': soort, 'snel': snel, 'max': mx, 'van': 'dock', 'start': 0.0, 'traag': 1.0}
check('open 250-350 ms', 0.25 <= DUUR['open'] <= 0.35)
check('sluiten sneller (~180 ms)', DUUR['sluit'] == 0.18 and DUUR['sluit'] < DUUR['open'])
check('snel-modus kort (<=160 ms)', SNEL <= 0.16)
f0, fm, fe = frame(A('open'), 0.0, 1920, 1080), frame(A('open'), 0.15, 1920, 1080), frame(A('open'), 0.31, 1920, 1080)
check('open begint klein en onzichtbaar bij het dock', f0[4] == 0 and f0[2] < 200 and f0[1] > 900)
check('open midden: groot, zichtbaar, scanline + gloed', fm[2] > 900 and fm[4] > 0.5 and fm[5] is not None and fm[6])
check('daarna klaar (scherp echt venster)', fe is None)
fs = frame(A('open', snel=True), 0.07, 1920, 1080)
check('snel: geen scanline, geen gloed', fs[5] is None and fs[6] is False)
check('gemaximaliseerd vak = schermbreedte', frame(A('open', mx=True), 0.29, 1920, 1080)[2] > 1900)
fc = frame(A('sluit'), 0.17, 1920, 1080)
check('sluiten krimpt naar het dock', fc[2] < 800 and fc[1] > 300)
check('traag-factor alleen via testbestand', "TRAAG_BESTAND = '/tmp/universe-flits-traag'" in fsrc)
check('overlay: OVERLAY, geen toetsenbord, lege invoerregio, geen WebKit',
      'Layer.OVERLAY' in fsrc and 'KeyboardMode.NONE' in fsrc and 'input_shape_combine_region(cairo.Region()' in fsrc and 'WebKit' not in fsrc.split('"""', 2)[2])
check('zonder RGBA-visual geen overlay (geen zwart scherm)', 'if not self.transparent:' in fsrc)
check('overlay verdwijnt als alles klaar is', 'self.window.hide()' in fsrc)
check('mint #85ffe3', '0x85 / 255, 0xff / 255, 0xe3 / 255' in fsrc)
sys.exit(1 if fails else 0)
