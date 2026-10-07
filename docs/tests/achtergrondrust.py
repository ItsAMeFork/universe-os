"""Actual window-change method with synthetic compositor events."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

path = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'
tree = ast.parse(path.read_text(encoding='utf-8'))
shell = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Shell')
shell.body = [n for n in shell.body if isinstance(n, ast.FunctionDef) and n.name == 'windows_changed']
namespace = {}
exec(compile(ast.Module(body=[shell], type_ignores=[]), str(path), 'exec'), namespace)
obj = namespace['Shell']()
obj.worlds = [SimpleNamespace(emit=Mock()), SimpleNamespace(emit=Mock())]
obj.toplevels = Mock()
obj.overview = None
obj.release_initial_focus = Mock()
for windows, busy in [([], False), ([{'minimized': True}], False),
                      ([{'minimized': False}], True),
                      ([{'minimized': True}, {'minimized': False}], True)]:
    obj.toplevels.list.return_value = windows
    obj.windows_changed()
    for world in obj.worlds:
        world.emit.assert_called_with('background-busy', busy)
print('PASS: visible/minimized/closed windows update all background surfaces')
