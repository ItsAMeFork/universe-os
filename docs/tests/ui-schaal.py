"""Auto scale of the shell pages by screen height, and the dark dock (23 Oct, Axel's H310M)."""
import ast, os, re
root = os.path.join(os.path.dirname(__file__), '..', '..', 'pakket', 'universe-os', 'usr')
src = open(os.path.join(root, 'lib/universe-os/shell/universe_shell.py')).read()
ns = {}
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == 'auto_factor')
exec(compile(ast.Module([fn], []), 'x', 'exec'), ns)
f = ns['auto_factor']
assert f(720) == 1.0 and f(1080) == 1.0 and f(1440) == 1.25 and f(2160) == 2.0 and f(4320) == 2.0
assert "['uiScale'] / 100" not in src.replace('ui_scale / 100', '')
dock = open(os.path.join(root, 'share/universe-os/ui/dock.html')).read()
assert '#e8eeff2e' not in dock and re.search(r'\.dock\{[^}]*background:#0b1021e6', dock)
js = open(os.path.join(root, 'share/universe-os/ui/dock.js')).read()
assert "img:key==='browser'?browserIcon:null" in js and "iconName:'folder'" in js
assert src.count('.redraw()') >= 4 and 'def redraw(self)' in src
print('ok')
