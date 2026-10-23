"""0.2.26: page processes that stop are logged and reloaded; no JIT without SSE4.2 or after repeated stops."""
import os, sys, tempfile, types
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pakket', 'universe-os', 'usr/lib/universe-os/shell')
src = open(os.path.join(root, 'webview.py')).read()
assert "connect('web-process-terminated', _restart_page, page, uri)" in src
ns = {'os': os, 'GLib': types.SimpleNamespace(timeout_add=lambda ms, fn: calls.append(ms))}
calls = []
start = src.index('_restarts = {}'); end = src.index('\ndef _policy')
code = src[start:end].replace("if cpu_lacks_jit_features():\n    no_jit('processor zonder SSE4.2')\n", '')
exec(code, ns)
def cpu(flags):
    f = tempfile.NamedTemporaryFile('w', delete=False); f.write('processor : 0\nflags : %s\n' % flags); f.close(); return f.name
assert ns['cpu_lacks_jit_features'](cpu('fpu sse sse2 pni cx16')) is True
assert ns['cpu_lacks_jit_features'](cpu('fpu sse2 sse4_1 sse4_2 avx avx2')) is False
os.environ.pop('JSC_useJIT', None)
v = types.SimpleNamespace(load_uri=lambda u: None)
ns['_restart_page'](v, 'crashed', 'world.html', 'file:///x')
assert calls == [500] and 'JSC_useJIT' not in os.environ
ns['_restart_page'](v, 'crashed', 'world.html', 'file:///x')
assert os.environ.get('JSC_useJIT') == '0'
for _ in range(3): ns['_restart_page'](v, 'crashed', 'world.html', 'file:///x')
assert calls[-1] == 10000
b = open(os.path.join(root, 'backend.py')).read()
assert "'JSC_useJIT')" in b
print('ok')
