"""Headless contract for the Brein nebula: second-brain queries on a temporary database,
the shell allow-list (including forget-everything, which refuses without the phrase),
and the planet-brein animation. No GTK and no real Recoll."""
import ast
import importlib.util
import io
import json
from importlib.machinery import SourceFileLoader
import os
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
BREIN_PATH = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude/brein.py'
SHELL_PATH = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'
MCP_PATH = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude/universe_mcp.py'
HOOK_PATH = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude/universe-claude-hook'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'

os.environ['XDG_DATA_HOME'] = tempfile.mkdtemp(prefix='brein-data-')
os.environ['XDG_RUNTIME_DIR'] = tempfile.mkdtemp(prefix='brein-run-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='brein-home-')

spec = importlib.util.spec_from_file_location('brein_test', BREIN_PATH)
brein = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brein)

a = brein.remember('Houdt van koffie in de ochtend', 'voorkeur', 'koffie, ochtend')
b = brein.remember('Zwarte koffie, zonder suiker', 'voorkeur', 'koffie')
c = brein.remember('De planten in de tuin hebben water nodig', 'notitie', 'tuin')
d = brein.remember('Tuinieren op zaterdag, vooral de planten', 'notitie', '')
alone = brein.remember('De kat zit op de vensterbank', 'feit', '')
other = brein.remember('De hond slaapt in de gang', 'feit', '')

stars = {row['id']: row for row in brein.list_memories()}
assert {a, b, c, d, alone, other} <= set(stars)
assert stars[a]['soort'] == 'voorkeur' and stars[a]['labels'] == 'koffie, ochtend'
assert stars[a]['helderheid'] > 0.9

old = brein.remember('Een notitie van weken geleden over de sterrenhemel', 'notitie', '')
with brein.connect() as db:
    db.execute('UPDATE memories SET updated = ? WHERE id = ?', (time.time() - 20 * 86400, old))
dim = {row['id']: row for row in brein.list_memories()}
assert dim[a]['helderheid'] > dim[old]['helderheid'] > 0.28

found = {row['id'] for row in brein.search_memories('koffie')}
assert {a, b} <= found and c not in found
assert brein.search_memories('')  # empty query: recent stars, all of them lit

edges = brein.links()
pairs = {(min(e['van'], e['naar']), max(e['van'], e['naar'])): e['via'] for e in edges}
assert (min(a, b), max(a, b)) in pairs and pairs[(min(a, b), max(a, b))] == 'koffie'
assert (min(c, d), max(c, d)) in pairs and pairs[(min(c, d), max(c, d))] in ('tuin', 'planten')
assert (min(alone, other), max(alone, other)) not in pairs  # stopwords only, no constellation
assert all(e['via'] not in brein.STOPWORDS for e in edges)

with brein.connect() as db:
    base = time.time() - 1000
    for i in range(40):
        db.execute('INSERT INTO timeline(at, kind, item, label) VALUES (?, ?, ?, ?)',
                   (base + i, 'app' if i % 2 == 0 else 'file', 'item-%d' % i, 'Naam %d' % i))
trail = brein.trail()
assert 2 <= len(trail) <= brein.TRAIL_CAP
assert trail[0]['op'] < trail[-1]['op']
assert trail[-1]['wat'] == 'item-39'
assert {p['soort'] for p in trail} <= {'app', 'file'}

changed = brein.update(c, 'De planten in de tuin zijn water gegeven')
assert changed is True
assert 'water gegeven' in brein.get(c)['tekst']
try:
    brein.update(c, '   ')
    raise AssertionError('lege tekst geaccepteerd')
except ValueError:
    pass
brein.forget(other)
assert brein.get(other) is None
try:
    brein.forget(other)
    raise AssertionError('tweede keer vergeten lukte')
except ValueError:
    pass

brein.set_hint_answer('demo', 'nooit')
overview = brein.summary()
assert overview['herinneringen'] >= 5
assert overview['per_soort']['voorkeur'] >= 2
assert overview['tijdlijn'] == 40
assert overview['hints'] == 1
assert overview['bewaarplaats'].endswith('brein.db')

folder = tempfile.mkdtemp(prefix='brein-export-')
saved = brein.write_export(folder)
blob = json.loads(Path(saved['pad']).read_text(encoding='utf-8'))
assert saved['herinneringen'] == len(blob['herinneringen'])
assert saved['tijdlijn'] == 40 and blob['hints'][0]['antwoord'] == 'nooit'
assert oct(os.stat(saved['pad']).st_mode & 0o777) == '0o600'

try:
    brein.forget_all('ja')
    raise AssertionError('wissen zonder de zin')
except ValueError as error:
    assert brein.FORGET_PHRASE in str(error)
assert brein.summary()['herinneringen'] >= 5

brein.forget_all('  Alles vergeten ')
empty = brein.summary()
assert empty['herinneringen'] == 0 and empty['tijdlijn'] == 0 and empty['hints'] == 0
assert brein.list_memories() == [] and brein.trail() == [] and brein.links() == []
fresh = brein.remember('Na het wissen nog één feit', 'feit', 'wissen')
assert brein.recall('wissen')[0]['id'] == fresh
assert brein.resolve_flash({'id': fresh})['id'] == fresh
assert brein.resolve_flash({'tekst': 'Na het wissen nog één feit'})['id'] == fresh

# Cap: the database may hold more; the nebula list never returns more than STAR_CAP.
for i in range(brein.STAR_CAP + 5):
    brein.remember('Ster %d in de nevel van het tweede brein' % i, 'notitie', '')
assert len(brein.list_memories()) == brein.STAR_CAP
assert len(brein.list_memories(3)) == 3


def load(path, name):
    loaded = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(loaded)
    loaded.loader.exec_module(module)
    return module


mcp = load(MCP_PATH, 'universe_mcp_brein')
assert 'planeet-brein' in mcp.ANIMATIONS
assert 'brein' in mcp.PLANETS


class Server:
    def __init__(self, path):
        self.lines = []
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        self.sock.bind(path)
        self.sock.listen(8)
        self.sock.settimeout(0.2)
        self.stop = False
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        while not self.stop:
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                conn.settimeout(1)
                data = b''
                while b'\n' not in data:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                self.lines.append(data.decode().strip())
                conn.sendall(b'ok\n')
            finally:
                conn.close()

    def close(self):
        self.stop = True
        try:
            self.sock.close()
        except OSError:
            pass
        self.thread.join(2)


server = Server(mcp.SOCKET)
try:
    result = mcp.handle({'method': 'tools/call', 'params': {'name': 'brein_onthouden', 'arguments': {
        'tekst': 'Werkt het liefst met weinig afleiding', 'soort': 'voorkeur', 'labels': 'focus'}}})
finally:
    server.close()
assert not result.get('isError'), result
body = json.loads(result['content'][0]['text'])
assert brein.get(body['id'])['soort'] == 'voorkeur'
assert server.lines and server.lines[0].startswith('call ') is False
assert server.lines[0].startswith('claude-event brein ')
assert json.loads(server.lines[0].split(' ', 2)[2])['id'] == body['id']

hook_loader = SourceFileLoader('universe_hook_brein', str(HOOK_PATH))
hook_spec = importlib.util.spec_from_loader('universe_hook_brein', hook_loader)
hook = importlib.util.module_from_spec(hook_spec)
hook_loader.exec_module(hook)
hook_server = Server(os.path.join(os.environ['XDG_RUNTIME_DIR'], 'universe-shell.sock'))
hook.sys.stdin = io.StringIO(json.dumps({
    'hook_event_name': 'PostToolUse',
    'tool_name': 'mcp__universe__brein_onthouden',
    'tool_input': {'tekst': 'Na het wissen nog één feit', 'soort': 'feit', 'labels': 'wissen'},
}))
try:
    hook.main()
finally:
    hook_server.close()
kinds = [line.split()[1] for line in hook_server.lines]
assert kinds[0] == 'brein', hook_server.lines
assert 'Na het wissen' in hook_server.lines[0]
assert 'tool-done' in kinds


def shell_parts():
    tree = ast.parse(SHELL_PATH.read_text(encoding='utf-8'))
    nodes, found = [], set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            ids = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if any(name in ids for name in ('CLAUDE_CALLS', 'SECURITY_SETTINGS', 'ANIMATIONS', 'CLAUDE_RUN')):
                nodes.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == 'Shell':
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in ('call', 'show_animation'):
                    nodes.append(item)
                    found.add(item.name)
    assert {'call', 'show_animation'} <= found
    namespace = {'threading': threading}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SHELL_PATH), 'exec'), namespace)
    return namespace


shell = shell_parts()
needed = {'brein.list', 'brein.links', 'brein.timeline', 'brein.update', 'brein.forget', 'brein.search', 'brein.forget_all'}
assert needed <= shell['CLAUDE_CALLS']
assert shell['ANIMATIONS']['planeet-brein'] == ('planeet', 'brein')
shell_text = SHELL_PATH.read_text(encoding='utf-8')
for name in needed:
    assert "'%s'" % name in shell_text
assert 'brein-flash' in shell_text
assert "parts[1] == 'brein'" in shell_text


def answer_of(host, line):
    got = []
    shell['call'](host, line, got.append)
    return got


class Blocking:
    def handlers(self):
        raise AssertionError('handler mocht niet lopen')
    bridge = SimpleNamespace(threaded=set())


refused = answer_of(Blocking(), 'call brein.wissen {}')
assert refused == ['fout: niet toegestaan: brein.wissen']

seen = []


class Allow:
    def handlers(self):
        return {
            'brein.list': lambda args: seen.append(('list', args)) or {'sterren': []},
            'brein.forget_all': lambda args: seen.append(('forget', args)) or {'vergeten': 'alles'},
            'brein.search': lambda args: seen.append(('search', args)) or {'sterren': [], 'bestanden': []},
        }
    bridge = SimpleNamespace(threaded=set())


listed = answer_of(Allow(), 'call brein.list {"max": 10}')
assert seen[0] == ('list', {'max': 10})
assert listed[0].startswith('ok ')
wiped = answer_of(Allow(), 'call brein.forget_all {"bevestig": "alles vergeten"}')
assert seen[-1] == ('forget', {'bevestig': 'alles vergeten'})
assert wiped[0].startswith('ok ')


class World:
    def __init__(self):
        self.events = []
    def emit(self, name, data=None):
        self.events.append((name, data))


class Desk:
    def __init__(self):
        self.shown = False
    def show_desktop(self):
        self.shown = True


world = World()
desk = Desk()
host = SimpleNamespace(worlds=[world], toplevels=desk, claude=None)
assert shell['show_animation'](host, 'planeet-brein')
assert desk.shown and ('open-planet', {'id': 'brein'}) in world.events

branding = json.loads((ROOT / 'branding/universe.json').read_text(encoding='utf-8'))
planet = next(p for p in branding['planets'] if p['id'] == 'brein')
assert planet['name'] == 'Brein'

ui = (UI / 'brein-nevel.js').read_text(encoding='utf-8')
assert 'STAR_CAP' in ui and 'prefers-reduced-motion' in ui
assert 'three' not in ui.lower() and 'd3' not in ui
assert 'shadowBlur' not in ui
world_js = (UI / 'world.js').read_text(encoding='utf-8')
assert 'mountNebula' in world_js and "p.id==='brein'" in world_js
control = (UI / 'control.js').read_text(encoding='utf-8')
assert 'brein.summary' in control and 'brein.export' in control and 'brein.forget_all' in control
assert 'alles vergeten' in control
center = (ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/control_center.py').read_text(encoding='utf-8')
assert "'brein.summary'" in center and "'brein.export'" in center and "'brein.forget_all'" in center

for script in (UI / 'brein-nevel.js', UI / 'world.js', UI / 'control.js'):
    checked = subprocess.run(['node', '--check', str(script)], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr

print('PASS: brein-nevel')
