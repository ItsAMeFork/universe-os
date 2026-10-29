#!/usr/bin/env python3
"""0.2.38 live2 (security): keys typed right after Super+L reached the app in front ('tes' of the password in the
calculator) until gtklock held the session lock. The shell now catches the keyboard from the first moment."""
import ast, sys, time
from pathlib import Path
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[2]
SH = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'
LOCK = (ROOT / 'pakket/universe-os/usr/bin/universe-lock').read_text()
fails = 0
def check(name, ok):
    global fails
    print(('OK   ' if ok else 'FOUT ') + name)
    fails += not ok
tree = ast.parse(SH.read_text())
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and any(isinstance(f, ast.FunctionDef) and f.name == 'lock_begin' for f in n.body))
cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('lock_begin', 'watch_lock', 'lock_focus_weg', 'lock_focus_terug')]
timers = []
settings = {'animations': 'full'}
ns = {'config': SimpleNamespace(settings=lambda: settings), 'time': time, 'log': lambda *a: None,
      'GLib': SimpleNamespace(timeout_add=lambda ms, f: timers.append(f) or 1, timeout_add_seconds=lambda s, f: 1),
      'GtkLayerShell': SimpleNamespace(set_layer=lambda *a: None, Layer=SimpleNamespace(OVERLAY=1, BACKGROUND=0))}
exec(compile(ast.Module(body=[cls], type_ignores=[]), 'universe_shell.py', 'exec'), ns)
S = ns[cls.name]
def shell(**kw):
    s = S.__new__(S)
    s.catch = []
    s.lock_catch = lambda on: s.catch.append(on)
    s.worlds = [SimpleNamespace(window=None, emit=lambda *a: None)]
    s.logout_pending = False
    s.claude = None
    s.locked = False
    s.lock_locked = lambda: s.locked
    s.lock_vanger = SimpleNamespace(connect=lambda *a: None, disconnect_by_func=lambda f: None)
    s.__dict__.update(kw)
    return s
for mode in ('full', 'reduced'):
    settings['animations'] = mode
    s = shell()
    r = s.lock_begin()
    check('%s: toetsenbord meteen gevangen bij vergrendelen' % mode, s.catch == [True] and r == ('anim' if mode == 'full' else 'direct'))
    s.watch_lock()
    check('%s: vanger blijft zolang het slot er nog niet is' % mode, s.catch == [True])
    s.locked = True
    s.watch_lock()
    check('%s: gtklock-proces alleen is niet genoeg' % mode, s.catch == [True])
    s.lock_focus_weg(s.lock_vanger, None)
    check('%s: los zodra het slot het toetsenbord pakt' % mode, s.catch == [True, False])
s = shell()
s.lock_begin()
s.lock_focus_weg(s.lock_vanger, None)
check('focusverlies vóór het slot: blijft vangen', s.catch == [True])
s.lock_started = time.monotonic() - 20
check('slot start nooit: vanger weg (niet vastzitten)', s.watch_lock() is False and s.catch[-1] is False)
check('universe-lock vraagt de shell vóór geluid en animatie',
      LOCK.index('universe-ctl lock') < LOCK.index('universe-geluid vergrendelen') < LOCK.index('sleep 2.3'))
src = SH.read_text()
check('vanger: OVERLAY + EXCLUSIVE + slikt toetsen', "'universe-lock-input'" in src and 'KeyboardMode.EXCLUSIVE)' in src and "'key-press-event', lambda *a: True" in src)
s = shell()
act = []
s.laatst_actief = '4'
s.toplevels = SimpleNamespace(list=lambda: [{'id': 4}, {'id': 5}], activate=act.append)
s.lock_focus_terug()
check('na ontgrendelen: focus terug naar het venster van voor Super+L', act == ['4'])
act.clear()
s.toplevels = SimpleNamespace(list=lambda: [{'id': 4}, {'id': 5, 'activated': True}], activate=act.append)
s.lock_focus_terug()
check('al een ander venster gekozen: niet afpakken', act == [])
sys.path.insert(0, str(SH.parent))
import session
xml = session._keybind({'key': 'W-l', 'command': 'universe-lock'})
check('Super+L: labwc haalt de focus meteen weg (Unfocus vóór universe-lock)', xml.index('Unfocus') < xml.index('universe-lock'))
check('andere sneltoetsen ongewijzigd', 'Unfocus' not in session._keybind({'key': 'W-e', 'command': 'universe-ctl run files'}))
sys.exit(1 if fails else 0)
