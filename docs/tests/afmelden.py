"""Exercise actual logout methods with mocked compositor/backend, without GTK."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

path = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'
tree = ast.parse(path.read_text(encoding='utf-8'))
shell = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Shell')
shell.body = [node for node in shell.body if isinstance(node, ast.FunctionDef) and node.name in ('power', 'begin_logout', 'finish_logout')]
namespace = {'GLib': Mock(), 'backend': Mock(), 'GtkLayerShell': Mock()}
namespace['GLib'].timeout_add.return_value = 42
exec(compile(ast.Module(body=[shell], type_ignores=[]), str(path), 'exec'), namespace)
obj = namespace['Shell']()
obj.logout_pending = False
obj.logout_timer = None
obj.worlds = [SimpleNamespace(window=Mock(), emit=Mock())]
obj.panel = Mock()
obj.hide_overview = Mock()
obj.begin_logout()
assert obj.logout_pending and obj.logout_timer == 42
obj.begin_logout()
assert namespace['GLib'].timeout_add.call_count == 1
obj.finish_logout()
namespace['backend'].power.assert_called_once_with('logout')
obj.finish_logout()
assert namespace['backend'].power.call_count == 1
obj.begin_logout()
namespace['backend'].power.side_effect = RuntimeError('testfout')
obj.finish_logout()
obj.worlds[0].emit.assert_called_with('logout-error', 'testfout')
assert not obj.logout_pending
print('PASS: repeated logout, bounded fallback, single exit, error restores world')
