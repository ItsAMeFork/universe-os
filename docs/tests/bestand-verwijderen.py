#!/usr/bin/env python3
"""0.2.36: een bestand naar de prullenbak (bureaublad, Thunar, Windows-programma verwijderen): een lichtflits op de plek
van het bestand en daarna verdwijnt het in een klein zwart gat. Controleert de shell-koppelingen en de animatie."""
import ast, sys, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
SH = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'
sys.path.insert(0, str(SH))
src = (SH / 'universe_shell.py').read_text(encoding='utf-8')
cls = next(n for n in ast.parse(src).body if isinstance(n, ast.ClassDef) and n.name == 'Shell')
cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in
            ('flits_mode', 'flits_bestand', 'flits_plek', 'desktop_trash', 'prullenbak_vergelijk', 'flits_zwartgat')]
settings = {'animations': 'full'}
backend = SimpleNamespace(desktop_trash=Mock())
ns = {'config': SimpleNamespace(settings=lambda: settings), 'grafisch': SimpleNamespace(light_active=lambda: False),
      'time': time, 'log': print, 'backend': backend, 'os': __import__('os')}
exec(compile(ast.Module(body=[cls], type_ignores=[]), 'universe_shell.py', 'exec'), ns)
fails = []


def check(name, ok):
    print(('OK   ' if ok else 'FOUT ') + name)
    ok or fails.append(name)


over = Mock(); over.size = lambda: (1920, 1080)
s = ns['Shell'](); s.lite = None
s.flits_overlay = lambda: over
s.toplevels = SimpleNamespace(list=lambda: [{'id': '3', 'activated': True}])
s.flits_cache = {'3': {'rect': (100, 100, 600, 400)}}
s.desktop_trash({'path': '/home/j/Bureaublad/foto.png', 'x': 300, 'y': 420})
e = over.play.call_args[0][0][0]
check('bureaublad: bestand echt naar de prullenbak', backend.desktop_trash.called)
check('bureaublad: gat op de plek van het icoon', e['soort'] == 'gat' and (e['x'], e['y']) == (300, 420) and e['naam'] == 'foto.png')
over.play.reset_mock()
s.trash_names = {}
s.flits_eigen = -99
ev = s.prullenbak_vergelijk({'a.txt': 'a.txt'})
e = over.play.call_args[0][0][0]
check('Thunar/Delete: nieuw in de prullenbak -> gat midden in het actieve venster', ev == [('gat', ['a.txt'])] and (e['x'], e['y']) == (400, 300))
over.play.reset_mock()
s.flits_eigen = time.monotonic()
s.prullenbak_vergelijk({'a.txt': 'a.txt', 'b.txt': 'b.txt'})
check('bureaublad flitste al zelf -> niet dubbel', not over.play.called)
s.flits_eigen = -99
s.prullenbak_vergelijk({'a.txt': 'a.txt'})
check('terugzetten uit de prullenbak -> geen animatie', not over.play.called)
s.toplevels = SimpleNamespace(list=lambda: [])
s.flits_bestand(naam='Notepad++')
e = over.play.call_args[0][0][0]
check('Windows-programma verwijderd zonder venster -> midden van het scherm', (e['x'], e['y']) == (960, 540))
settings['animations'] = 'reduced'
s.flits_bestand(1, 2)
check('verminderd -> snel', over.play.call_args[0][0][0]['snel'] is True)
over.play.reset_mock(); settings['animations'] = 'off'
s.flits_bestand(1, 2)
check('animaties uit -> niets', not over.play.called)
settings['animations'] = 'full'

wsrc = (SH / 'wine.py').read_text()
check('Windows-programma verwijderen -> universe-ctl flits verwijder', "['universe-ctl', 'flits', 'verwijder'" in wsrc)
check('shell kent de opdracht flits verwijder', "cmd == 'flits'" in src and "parts[1] == 'verwijder'" in src)
check('world.js geeft de plek van het icoon mee', "call('desktop.trash',{path:o.target,...(r&&r.width?{x:" in (UI / 'world.js').read_text())
check('prullenbak wordt gevolgd (Gio-monitor op trash:///)', "new_for_uri('trash:///')" in src and 'monitor_directory' in src)

import flits
g0, g1, g2 = flits.gat_frame(0.15), flits.gat_frame(0.6), flits.gat_frame(0.99)
check('eerst een lichtflits', g0['flits'] > 0.9 and g0['kaart'] == 1)
check('dan krimpt het bestand het gat in', g1['flits'] == 0 and 0 < g1['kaart'] < 1 and g1['gat'] > 5)
check('aan het eind is alles weg', g2['kaart'] < 0.01 and g2['gat'] < 1)
check('duur kort (~0.55 s)', flits.DUUR['gat'] <= 0.6)
sys.exit(1 if fails else 0)
