#!/usr/bin/env python3
"""0.2.34: de bovenbalk krijgt 'bar-covered' alleen als een niet-geminimaliseerd venster gemaximaliseerd of fullscreen is."""
import ast
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

path = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'
tree = ast.parse(path.read_text(encoding='utf-8'))
shell = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Shell')
shell.body = [n for n in shell.body if isinstance(n, ast.FunctionDef) and n.name == 'windows_update']
namespace = {'GLib': Mock(), 'backend': Mock()}
exec(compile(ast.Module(body=[shell], type_ignores=[]), str(path), 'exec'), namespace)


def make_shell(windows, panel=True):
    obj = namespace['Shell']()
    obj.worlds = [SimpleNamespace(emit=Mock())]
    obj.toplevels = Mock()
    obj.toplevels.list.return_value = windows
    obj.overview = None
    obj.dock = None
    obj.claude = None
    obj.release_initial_focus = Mock()
    obj.panel = SimpleNamespace(emit=Mock()) if panel else None
    return obj


def covered_calls(obj):
    return [c for c in obj.panel.emit.call_args_list if c.args[0] == 'bar-covered']


failures = []


def check(name, ok):
    print(('OK   ' if ok else 'FOUT ') + name)
    if not ok:
        failures.append(name)


# Eén update per toestand; het laatste emit-argument moet de bedekt-waarde zijn.
cases = [
    ('geen venster -> False', [], False),
    ('gemaximaliseerd -> True', [{'id': 1, 'maximized': True}], True),
    ('geminimaliseerd+gemaximaliseerd -> False', [{'id': 1, 'minimized': True, 'maximized': True}], False),
    ('fullscreen -> True', [{'id': 2, 'fullscreen': True}], True),
    ('gewoon venster -> False', [{'id': 3}], False),
    ('gemaximaliseerd + gewoon venster -> True', [{'id': 3}, {'id': 4, 'maximized': True}], True),
]
for name, windows, expected in cases:
    obj = make_shell(windows)
    obj.windows_update()
    calls = covered_calls(obj)
    check(name, len(calls) == 1 and calls[0].args == ('bar-covered', expected))

# Alleen bij verandering een emit: dezelfde toestand twee keer levert één emit op.
obj = make_shell([{'id': 1, 'maximized': True}])
obj.windows_update()
obj.windows_update()
check('zelfde toestand -> geen tweede emit', len(covered_calls(obj)) == 1)

obj.toplevels.list.return_value = []
obj.windows_update()
check('verandering naar geen venster -> tweede emit met False',
      [c.args for c in covered_calls(obj)] == [('bar-covered', True), ('bar-covered', False)])

# Zonder paneel: geen fout en geen emit.
try:
    obj = make_shell([{'id': 1, 'maximized': True}], panel=False)
    obj.windows_update()
    check('zonder paneel geen fout', True)
except Exception as err:  # noqa: BLE001 - the test reports any failure
    check(f'zonder paneel geen fout ({err!r})', False)

if failures:
    print(f'{len(failures)} test(s) gefaald')
    sys.exit(1)
print('PASS: bovenbalk wordt alleen bedekt gemeld voor niet-geminimaliseerde maximale of fullscreen vensters')
