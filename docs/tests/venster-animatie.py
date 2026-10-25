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
check('overlay: OVERLAY-laag, geen toetsenbord, lege invoerregio',
      "'flits.html', L.OVERLAY" in src and 'K.NONE' in src and 'input_shape_combine_region(cairo.Region()' in src)
check('overlay verdwijnt na de animatie', 'self.flits_hide' in src)
check('windows_update roept window_flits aan', 'self.window_flits(windows)' in src)

js = r'''
globalThis.window=globalThis;globalThis.addEventListener=()=>{};
import(process.argv[1]).then(m=>{
 const o=m.plan({soort:'open',van:'dock'},1920,1080), c=m.plan({soort:'sluit',van:'dock'},1920,1080),
       f=m.plan({soort:'open',snel:true},1920,1080), x=m.plan({soort:'open',max:true},1920,1080);
 console.log(JSON.stringify({o:o.duur,c:c.duur,f:f.duur,fl:f.lijnen,ol:o.lijnen,ease:o.easing,xw:x.v.w,end:o.frames.at(-1).opacity,start:o.frames[0].opacity}));
});'''
out = subprocess.run(['node', '-e', js, (UI / 'flits.js').as_uri()], capture_output=True, text=True)
try:
    r = json.loads(out.stdout)
except Exception:
    r = {}
    print(out.stderr)
check('open 250-350 ms ease-out', 250 <= r.get('o', 0) <= 350 and r.get('ease', '').startswith('cubic-bezier(.16'))
check('sluiten sneller (~180 ms)', r.get('c') == 180 and r.get('c', 999) < r.get('o', 0))
check('snel: kort, geen scanlines', r.get('f', 999) <= 160 and r.get('fl') is False and r.get('ol') is True)
check('gemaximaliseerd vak = schermbreedte', r.get('xw') == 1920)
check('begint en eindigt onzichtbaar (scherp echt venster)', r.get('start') == 0 and r.get('end') == 0)
css = (UI / 'flits.html').read_text()
check('mint-gloed #85ffe3, geen CSS-filters', '#85ffe3' in css and 'filter:' not in css and 'pointer-events:none' in css)
check('snel-modus zonder gloed', '.holo.snel{' in css and 'box-shadow:none' in css)
sys.exit(1 if fails else 0)
