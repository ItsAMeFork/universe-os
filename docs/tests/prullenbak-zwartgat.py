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
            ('flits_mode', 'flits_plek', 'flits_scherm', 'prullenbak_vergelijk', 'flits_zwartgat', 'flits_bestand', 'empty_trash')]
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
check('1 bestand: ~1.5-2.5 s opslokken, totaal met verschijnen/inzakken < 4.5 s', 1.5 <= flits.ZG_SLOK <= 2.5 and flits.zwartgat_duur(1) < 4.5)
check('maximaal ~8 s, ook bij 500 bestanden', flits.zwartgat_duur(500) <= 8.0 + 1e-9)
g = flits.zwartgat_groepen(['f%d' % i for i in range(500)])
check('500 bestanden -> %d groepen, laatste "+483"' % len(g), len(g) == flits.ZWARTGAT_GROEPEN and g[-1] == '+483')
plan = flits.zwartgat_plan(['a', 'b', 'c', 'd'])
check('één voor één (oplopende vertrektijd)', [p['vertrek'] for p in plan] == sorted(p['vertrek'] for p in plan) and len({p['vertrek'] for p in plan}) == 4)
plan18 = flits.zwartgat_plan(['f%d' % i for i in range(500)])
check('laatste groep is binnen ~8 s opgeslokt', plan18[-1]['vertrek'] + flits.ZG_SLOK + flits.ZG_INZAK <= 8.0 + 1e-9)
it = plan[0]
v = it['vertrek']
p1, p2, p3 = (flits.zwartgat_item(it, v + d) for d in (0.3, 0.9, 1.6))
check('spiraalt naar binnen en versnelt', p1['r'] > p2['r'] > p3['r'] and (p2['r'] - p3['r']) / 0.7 > (it['afstand'] - p1['r']) / 0.3)
check('spaghettificatie: wordt uitgerekt', p1['rek'] < p2['rek'] < p3['rek'] and p3['rek'] > 4)
check('bestand wordt een lichtstroom (kaart weg, licht aan)', p1['k'] > 0.5 and p3['k'] == 0 and p2['licht'] > 0.5)
check('roodverschoven bij de horizon, dooft uit', p1['rood'] == 0 and p3['rood'] > 0.6 and flits.zwartgat_item(it, v + 1.79)['licht'] < 0.05)
check('kleur verschuift van wit-blauw naar rood', flits.roodverschuiving(0)[2] > 0.9 and flits.roodverschuiving(1)[0] > flits.roodverschuiving(1)[2] * 5)
check('opgeslokt -> weg (ontsnapt niet)', flits.zwartgat_item(it, v + flits.ZG_SLOK + 0.01) is None)
check('wacht vóór vertrek', flits.zwartgat_item(plan[-1], 0.0) == 'wacht')
T = flits.zwartgat_duur(4)
f0, f1, f2, f3 = (flits.zwartgat_frame(x, T) for x in (0.05, 0.5, (T - 0.6) / T, 0.999))
check('gat groeit, slokt, zakt langzaam in', 0 < f0['groot'] < 1 and f1['groot'] == 1 and 0.2 < f2['groot'] < 0.8 and f3['groot'] < 0.05)
check('snel-modus kort', flits.zwartgat_duur(50, snel=True) <= 0.6)
sys.exit(1 if fails else 0)
