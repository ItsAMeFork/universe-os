#!/usr/bin/env python3
"""0.2.39 (Jesse t146u: 'eerst animatie dan de venster tonen', alle vensters, licht en normaal): labwc verbergt elk nieuw
venster bij het mappen (windowRule Iconify), de shell speelt het portaal naar de plek waar het komt en zet het venster
pas aan het eind terug. Door de gebruiker geminimaliseerde vensters blijven met rust; na een shell-herstart worden
verborgen vensters meteen getoond."""
import ast, sys, time, os, tempfile
from pathlib import Path
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[2]
SH = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell'
sys.path.insert(0, str(SH))
os.environ['XDG_RUNTIME_DIR'] = tempfile.mkdtemp()
fails = []
def check(name, ok):
    print(('OK   ' if ok else 'FOUT ') + name)
    ok or fails.append(name)
tree = ast.parse((SH / 'universe_shell.py').read_text())
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Shell')
names = {'onthul_apps', 'onthul_check', 'onthul_sleutel', 'onthul_gebruiker', 'onthul_rect', 'onthul_onthoud', 'onthul_start', 'onthul',
         'venster_activeer', 'window_flits', 'flits_scherm', 'flits_dock'}
cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
mode = {'m': 'vol'}
timers = []
ns = {'time': time, 'os': os, 'log': print, 'BRON_GELDIG': 30, 'ONTHUL_UITERLIJK': 1.5, 'VENSTERS_BESTAND': os.path.join(os.environ['XDG_RUNTIME_DIR'], 'v', 'vensters.json'),
      'GLib': SimpleNamespace(timeout_add=lambda ms, f: timers.append(f) or 1), 'Gdk': None, 'staticmethod': staticmethod}
exec(compile(ast.Module(body=[cls], type_ignores=[]), 'universe_shell.py', 'exec'), ns)
S = ns['Shell']
W = lambda i, **k: dict({'id': i, 'appId': 'app' + i, 'title': 't' + i, 'minimized': False, 'maximized': False,
                         'fullscreen': False, 'activated': False}, **k)
def shell():
    s = S.__new__(S)
    s.lite = None
    s.flits_mode = lambda: mode['m']
    s.dock = SimpleNamespace(window=SimpleNamespace(get_visible=lambda: True))
    s.played, s.activated = [], []
    s.flits = SimpleNamespace(size=lambda: (1920, 1080), play=lambda ev: s.played.extend(ev) or True)
    s.flits_overlay = lambda: s.flits
    s.toplevels = SimpleNamespace(activate=s.activated.append, list=lambda: s.lijst)
    s.lijst = []
    s.gemeten = []
    s.flits_meet = s.gemeten.append
    return s
s = shell()
s.onthul_check([W('1')])
s.onthul_check([W('1'), W('2', minimized=True)])
check('nieuw venster (verborgen bij mappen): portaal speelt, venster nog NIET getoond', len(s.played) == 1 and s.activated == []
      and s.played[0]['verborgen'] and s.played[0]['soort'] == 'open')
check('portaal komt uit het dock (onderbalk) zonder klikpunt', s.played[0]['bron'] == (960, 1040))
s.played[0]['onthul']()
check('aan het eind van het portaal: venster getoond', s.activated == ['2'])
s.played[0]['onthul'](); [f() for f in timers]
check('veiligheidstimer toont niet nog eens', s.activated == ['2'])
s.flits_seen = {'1': W('1'), '2': W('2', minimized=True)}
s.flits_mode = lambda: 'vol'
s.play_flits = lambda ev: None
ev = s.window_flits([W('1'), W('2', activated=True)])
check('ons eigen terugzetten: alleen meten, geen tweede portaal', [x['soort'] for x in ev] == ['meet'])
s.flits_mode = lambda: mode['m']
s.onthul_onthoud({'appId': 'app3'}, (10, 20, 300, 200), 'PIX')
s.onthul_check([W('1'), W('2'), W('3', minimized=True)])
check('bekend programma: portaal naar de vorige rechthoek met inhoud', s.played[-1]['rect'] == (10, 20, 300, 200) and s.played[-1]['pix'] == 'PIX')
mode['m'] = 'licht'
s.onthul_check([W('1'), W('2'), W('3', minimized=True), W('4', minimized=True)])
check('lichte modus: zelfde portaal, glazen kaart (geen inhoud)', s.played[-1]['kwaliteit'] == 'licht' and s.played[-1]['pix'] is None)
mode['m'] = None
s.onthul_check([W('1'), W('2'), W('3', minimized=True), W('4', minimized=True), W('5', minimized=True)])
check('animaties uit: venster meteen getoond', s.activated[-1] == '5')
mode['m'] = 'vol'
s.onthul_check([W('1', minimized=True), W('2'), W('3', minimized=True), W('4', minimized=True), W('5', minimized=True)])
check('door de gebruiker geminimaliseerd: blijft verborgen en wordt onthouden', s.activated[-1] == '5' and 'app1\tt1' in s.onthul_gebruiker())
s2 = shell()
s2.onthul_check([W('1', minimized=True), W('9', minimized=True)])
check('shell-herstart: verborgen vensters meteen getoond, gebruikers-minimalisatie niet', s2.activated == ['9'])
s3 = shell()
s3.onthul_check([])
s3.flits_cache = {'7': {'rect': (5, 5, 400, 300), 'pix': None}}
s3.lijst = [W('7', minimized=True)]
s3.venster_activeer('7')
check('dock: geminimaliseerd venster eerst portaal, dan pas tonen', s3.activated == [] and s3.played[-1]['verborgen'])
s3.played[-1]['onthul']()
check('... en daarna getoond', s3.activated == ['7'])
s4 = shell()
check('rechthoek per programma bewaard over een herstart', s4.onthul_rect({'appId': 'app3'})[0] == (10, 20, 300, 200))
import session
x = session.rc_xml()
check('labwc: elk nieuw venster verborgen bij mappen (Iconify), plaatsing midden', 'action name="Iconify"' in x and '<policy>center</policy>' in x)
check('herstelmodus (geen shell): geen verbergregel', 'Iconify' not in session.rc_xml(True))
import flits
check('venster wordt onder de nog dichte kaart teruggezet, kaart vervaagt pas daarna', 0.6 <= flits.ONTHUL_BIJ < flits.ONTHUL_FADE < 1)

# 0.2.39 safety net: without a living shell (no heartbeat) new windows are never hidden
import os as _os, sys as _sys, tempfile as _tf, time as _t
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', 'pakket/universe-os/usr/lib/universe-os/shell'))
_os.environ['XDG_RUNTIME_DIR'] = _tf.mkdtemp()
import session as _s
assert not _s.shell_leeft(), 'geen hartslag -> shell leeft niet'
assert 'Iconify' not in _s.rc_xml(verbergen=_s.shell_leeft()), 'zonder shell geen verborgen vensters'
open(_s.hartslag_pad(), 'w').close()
assert _s.shell_leeft() and 'Iconify' in _s.rc_xml(verbergen=_s.shell_leeft()), 'met hartslag wel'
_os.utime(_s.hartslag_pad(), (_t.time() - 10, _t.time() - 10))
assert not _s.shell_leeft(), 'oude hartslag -> vrijgeven'
assert 'Iconify' not in _s.rc_xml(recovery=True), 'herstelmodus nooit verborgen'
src = open(_os.path.join(_os.path.dirname(_s.__file__), 'vensterwacht.py')).read()
assert 'unset_minimized' in open(_os.path.join(_os.path.dirname(_s.__file__), 'toplevels.py')).read() and 'toon_verborgen' in src
sup = open(_os.path.join(_os.path.dirname(_s.__file__), '..', '..', '..', 'bin', 'universe-shell-supervisor')).read()
assert 'vensterwacht.py >>' in sup and 'vensterwacht.py vrijgeven' in sup, 'supervisor start de wacht en geeft vrij na een crash'
print('ok veiligheidsnet')
s = shell(); s.lijst = [W('9', minimized=True)]; s.onthul_check(s.lijst); s.lijst = [W('9', minimized=True), W('10', minimized=True)]
timers.clear(); s.onthul_check(s.lijst); [e['onthul']() for e in s.played if e.get('onthul')]; [f() for f in list(timers)]
check('na het tonen wordt het venster gemeten (voor de sluitanimatie), na het vervagen van de kaart', any(e.get('na_onthul') and e['wid'] == '10' for e in s.gemeten))
s = shell(); s.lijst = [W('1')]; s.onthul_check(s.lijst); s.lijst = [W('1'), W('2')]; s.onthul_check(s.lijst); s.lijst = [W('1'), W('2', minimized=True)]; s.onthul_check(s.lijst)
check('Iconify pas in een latere melding: toch het portaal, geen gebruikersminimalisatie', any(e.get('wid') == '2' for e in s.played))
sys.exit(1 if fails else 0)
