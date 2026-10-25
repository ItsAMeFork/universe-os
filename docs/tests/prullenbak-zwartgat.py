#!/usr/bin/env python3
"""0.2.36: prullenbak legen (Thunar of 'Prullenbak leegmaken' op het bureaublad): een groot zwart gat met accretieschijf
slokt de bestanden één voor één op, met lichtsporen, en verdwijnt. Hooguit ~3 s; veel bestanden worden gegroepeerd."""
import ast, math, sys, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
SH = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'
sys.path.insert(0, str(SH))
import flits
src = (SH / 'universe_shell.py').read_text(encoding='utf-8')
cls = next(n for n in ast.parse(src).body if isinstance(n, ast.ClassDef) and n.name == 'Shell')
cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in
            ('flits_mode', 'flits_plek', 'prullenbak_vergelijk', 'flits_zwartgat', 'flits_bestand', 'empty_trash')]
settings = {'animations': 'full'}
backend = SimpleNamespace(trash_empty=Mock(return_value=True))
ns = {'config': SimpleNamespace(settings=lambda: settings), 'grafisch': SimpleNamespace(light_active=lambda: False),
      'time': time, 'log': print, 'backend': backend}
exec(compile(ast.Module(body=[cls], type_ignores=[]), 'universe_shell.py', 'exec'), ns)
fails = []


def check(name, ok):
    print(('OK   ' if ok else 'FOUT ') + name)
    ok or fails.append(name)


over = Mock(); over.size = lambda: (1920, 1080)
s = ns['Shell'](); s.lite = None
s.flits_overlay = lambda: over
s.toplevels = SimpleNamespace(list=lambda: [])
s.flits_cache = {}
s.trash_names = {'a': 'a.txt', 'b': 'foto.png', 'c': 'map'}
ev = s.prullenbak_vergelijk({})
e = over.play.call_args[0][0][0]
check('prullenbak leeg -> zwart gat met alle namen', ev == [('zwartgat', ['a.txt', 'foto.png', 'map'])] and e['soort'] == 'zwartgat' and len(e['namen']) == 3)
s.empty_trash({'x': 120, 'y': 900})
check('Prullenbak leegmaken op het bureaublad leegt echt', backend.trash_empty.called)
s.trash_names = {'a': 'a.txt'}
s.prullenbak_vergelijk({})
e = over.play.call_args[0][0][0]
check('zwart gat bij het prullenbak-icoon', (e['x'], e['y']) == (120, 900))
over.play.reset_mock()
s.trash_names = {}
s.prullenbak_vergelijk({})
check('lege prullenbak blijft leeg -> niets', not over.play.called)
settings['animations'] = 'off'
s.trash_names = {'a': 'a'}
s.prullenbak_vergelijk({})
check('animaties uit -> niets', not over.play.called)
settings['animations'] = 'full'
check('menu Prullenbak leegmaken in world.js', "label:'Prullenbak leegmaken'" in (UI / 'world.js').read_text() and "'desktop.empty-trash'" in src)

check('duur groeit met het aantal bestanden', flits.zwartgat_duur(1) < flits.zwartgat_duur(10))
check('maximaal ~3 s, ook bij 500 bestanden', flits.zwartgat_duur(500) <= 3.0)
g = flits.zwartgat_groepen(['f%d' % i for i in range(500)])
check('500 bestanden -> %d groepen, laatste "+483"' % len(g), len(g) == flits.ZWARTGAT_GROEPEN and g[-1] == '+483')
plan = flits.zwartgat_plan(['a', 'b', 'c', 'd'])
check('één voor één (oplopende vertrektijd)', [p['vertrek'] for p in plan] == sorted(p['vertrek'] for p in plan) and len({p['vertrek'] for p in plan}) == 4)
it = plan[0]
p1, p2 = flits.zwartgat_item(it, it['vertrek'] + 0.05), flits.zwartgat_item(it, it['vertrek'] + 0.2)
check('versnelt naar binnen (lichtsporen)', p1[0] > p2[0] and (p1[0] - p2[0]) > (it['afstand'] - p1[0]))
check('opgeslokt -> weg', flits.zwartgat_item(it, it['vertrek'] + 0.3) is None)
check('wacht vóór vertrek', flits.zwartgat_item(plan[-1], 0.0) == 'wacht')
f0, f1, f2 = flits.zwartgat_frame(0.05), flits.zwartgat_frame(0.5), flits.zwartgat_frame(0.999)
check('gat groeit, slokt, verdwijnt', 0 < f0['groot'] < 1 and f1['groot'] == 1 and f2['groot'] < 0.05)
check('snel-modus kort', flits.zwartgat_duur(50, snel=True) <= 0.6)
sys.exit(1 if fails else 0)
