"""Recovery notifications must not call the potentially missing api.js reply handler."""
import ast
import json
from pathlib import Path
tree = ast.parse(Path('pakket/universe-os/usr/lib/universe-os/shell/webview.py').read_text())
reply = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'reply')
calls = []
ns = {'json': json, '_js': lambda view, code: calls.append(code)}
exec(compile(ast.Module(body=[reply], type_ignores=[]), '<reply>', 'exec'), ns)
for mid in (-1, -2, -3):
    assert ns['reply'](None, mid, True, None) is False
assert not calls
ns['reply'](None, 1, True, 'ok')
assert len(calls) == 1 and '__universeReply(1,' in calls[0]
print('Recovery fire-and-forget and regular bridge replies OK')
