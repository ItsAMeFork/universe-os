"""Headless contract for the Claude harness: power fallback and animatie_tonen against a fake shell socket,
and the shell allow-list (lockMinutes, animation names). No GTK and no real power commands."""
import ast
import importlib.util
import json
import os
import socket
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
MCP_PATH = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude/universe_mcp.py'
SHELL_PATH = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'

os.environ['XDG_RUNTIME_DIR'] = tempfile.mkdtemp(prefix='universe-mcp-')
os.environ['XDG_DATA_HOME'] = tempfile.mkdtemp(prefix='universe-data-')
spec = importlib.util.spec_from_file_location('universe_mcp_test', MCP_PATH)
mcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp)
mcp.subprocess.Popen = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('echte power-opdracht: %s' % (args,)))


class FakeShell:
    def __init__(self, path, reply):
        self.lines = []
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        self.sock.bind(path)
        self.sock.listen(1)
        self.reply = reply
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        self.sock.settimeout(5)
        try:
            conn, _ = self.sock.accept()
        except OSError:
            return
        try:
            data = b''
            while b'\n' not in data:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            self.lines.append(data.decode().strip())
            if self.reply is not None:
                text = self.reply if str(self.reply).endswith('\n') else str(self.reply) + '\n'
                conn.sendall(text.encode())
        finally:
            conn.close()

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass
        self.thread.join(5)


def tool(name, arguments):
    return mcp.handle({'method': 'tools/call', 'params': {'name': name, 'arguments': arguments}})


def text_of(result):
    return result['content'][0]['text']


def energie(actie, reply):
    """reply None: no socket (shell unreachable). Otherwise the fake shell answers with that line."""
    powered = []
    mcp.direct_power = lambda action, reason: powered.append((action, str(reason)))
    server = None
    if reply is None:
        try:
            os.unlink(mcp.SOCKET)
        except FileNotFoundError:
            pass
    else:
        server = FakeShell(mcp.SOCKET, reply)
    try:
        result = tool('energie', {'actie': actie})
    finally:
        if server:
            server.close()
    return powered, result, server.lines if server else []


# Shell down, or this shell does not know claude.power yet: do not power off anyway.
powered, result, _ = energie('afsluiten', None)
assert powered == [], powered
assert result.get('isError') is True
assert 'shell' in text_of(result).lower()

powered, result, _ = energie('opnieuw_opstarten', 'fout: niet toegestaan: claude.power')
assert powered == [], powered
assert result.get('isError') is True

# Lock may still fall back when the shell is gone. Reboot may not.
powered, result, _ = energie('vergrendelen', None)
assert powered and powered[0][0] == 'lock', powered
assert not result.get('isError')

# Any other shell error (refusal, handler exception, silence) must reach Claude. Do not power off.
powered, result, _ = energie('afsluiten', 'fout: Onbekende actie: poweroff')
assert powered == [], powered
assert result.get('isError') is True
assert 'Onbekende actie' in text_of(result)
assert 'afgesloten' not in text_of(result)

powered, result, _ = energie('opnieuw_opstarten', 'fout: geweigerd')
assert powered == [], powered
assert result.get('isError') is True
assert 'geweigerd' in text_of(result)

powered, result, _ = energie('vergrendelen', 'fout: niet toegestaan: config.set')
assert powered == [], powered
assert result.get('isError') is True

powered, result, _ = energie('afsluiten', '')
assert powered == [], powered
assert result.get('isError') is True

powered, result, _ = energie('afsluiten', 'ok true')
assert powered == []
assert not result.get('isError')
assert 'afgesloten' in text_of(result)

# Animations the world and the buddy already play. Names are the contract; the shell maps them.
ANIMATIONS = {
    'planeet-thuis': ('planeet', 'home'),
    'planeet-applicaties': ('planeet', 'apps'),
    'planeet-winkel': ('planeet', 'store'),
    'planeet-controle': ('planeet', 'control'),
    'planeet-internet': ('planeet', 'chat'),
    'planeet-games': ('planeet', 'games'),
    'planeet-brein': ('planeet', 'brein'),
    'ruimte': ('ruimte', None),
    'buddy-rust': ('buddy', 'idle'),
    'buddy-luisteren': ('buddy', 'listen'),
    'buddy-denken': ('buddy', 'think'),
    'buddy-werken': ('buddy', 'work'),
    'buddy-aandacht': ('buddy', 'attention'),
    'buddy-blij': ('buddy', 'happy'),
    'buddy-naar-huis': ('plek', 'home'),
    'buddy-naar-dock': ('plek', 'dock'),
    'buddy-naar-wereld': ('plek', 'world'),
    'buddy-naar-paneel': ('plek', 'panel'),
}
tool_list = mcp.handle({'method': 'tools/list'})
names = [item['name'] for item in tool_list['tools']]
assert 'animatie_tonen' in names
schema = next(item for item in tool_list['tools'] if item['name'] == 'animatie_tonen')
assert schema['inputSchema']['properties']['naam']['enum'] == list(ANIMATIONS)
assert 'animatie_tonen' in (MCP_PATH.read_text(encoding='utf-8'))
uitleg = (ROOT / 'pakket/universe-os/usr/lib/universe-os/claude/uitleg.md').read_text(encoding='utf-8')
assert 'animatie_tonen' in uitleg
for name in ANIMATIONS:
    assert name in uitleg

powered = []
mcp.direct_power = lambda action, reason: powered.append(action)
server = FakeShell(mcp.SOCKET, 'ok true')
try:
    result = tool('animatie_tonen', {'naam': 'planeet-games'})
finally:
    server.close()
assert server.lines and server.lines[0].startswith('call claude.anim ')
assert json.loads(server.lines[0].split(' ', 2)[2]) == {'naam': 'planeet-games'}
assert not result.get('isError')
assert powered == []

server = FakeShell(mcp.SOCKET, 'fout: De buddy is er niet.')
try:
    result = tool('animatie_tonen', {'naam': 'buddy-blij'})
finally:
    server.close()
assert result.get('isError') is True
assert 'buddy' in text_of(result).lower()
assert powered == []

result = tool('animatie_tonen', {'naam': 'poweroff'})
assert result.get('isError') is True
assert powered == []


def shell_parts():
    tree = ast.parse(SHELL_PATH.read_text(encoding='utf-8'))
    nodes = []
    found = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            ids = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if any(name in ids for name in ('CLAUDE_CALLS', 'SECURITY_SETTINGS', 'ANIMATIONS')):
                nodes.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == 'Shell':
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in ('call', 'show_animation'):
                    nodes.append(item)
                    found.add(item.name)
    missing = {'call', 'show_animation'} - found
    assert not missing, missing
    namespace = {'threading': threading}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SHELL_PATH), 'exec'), namespace)
    return namespace


shell = shell_parts()
assert shell['ANIMATIONS'] == ANIMATIONS
assert shell['SECURITY_SETTINGS'] == {'lockMinutes'}
assert 'claude.anim' in shell['CLAUDE_CALLS']


def answer_to(calls):
    got = []

    def answer(text):
        got.append(text)
    calls(answer)
    return got


class Blocking:
    def handlers(self):
        raise AssertionError('handler mocht niet lopen')
    bridge = SimpleNamespace(threaded=set())


got = answer_to(lambda answer: shell['call'](Blocking(), 'call config.set {"key":"lockMinutes","value":0}', answer))
assert got == ['fout: Dit is een beveiligingsinstelling; die verandert de gebruiker zelf in het Controlecentrum.']

seen = []


class Allow:
    def handlers(self):
        return {'config.set': lambda args: seen.append(args) or True, 'claude.anim': lambda args: seen.append(args) or True}
    bridge = SimpleNamespace(threaded=set())


got = answer_to(lambda answer: shell['call'](Allow(), 'call config.set {"key":"uiScale","value":120}', answer))
assert seen[0] == {'key': 'uiScale', 'value': 120}
assert got[0].startswith('ok ')

got = answer_to(lambda answer: shell['call'](Blocking(), 'call claude.anim {"naam":"poweroff"}', answer))
assert got[0].startswith('fout:')
assert 'poweroff' in got[0] or 'Onbekende animatie' in got[0]

seen.clear()
got = answer_to(lambda answer: shell['call'](Allow(), 'call claude.anim {"naam":"buddy-blij"}', answer))
assert seen[-1] == {'naam': 'buddy-blij'}
assert got[0].startswith('ok ')


class World:
    def __init__(self):
        self.events = []
    def emit(self, name, data=None):
        self.events.append((name, data))


class Buddy:
    def __init__(self):
        self.state = None
        self.place = None
    def set_state(self, state):
        self.state = state
    def go(self, place):
        self.place = place


class Desktop:
    def __init__(self, world):
        self.world = world
        self.shown = False
    def show_desktop(self):
        self.shown = True


world = World()
buddy = Buddy()
desktop = Desktop(world)
host = SimpleNamespace(worlds=[world], toplevels=desktop, claude=SimpleNamespace(buddy=buddy))
assert shell['show_animation'](host, 'planeet-games')
assert desktop.shown
assert ('open-planet', {'id': 'games'}) in world.events
assert shell['show_animation'](host, 'ruimte')
assert ('show-space', None) in world.events
assert shell['show_animation'](host, 'buddy-blij')
assert buddy.state == 'happy'
assert shell['show_animation'](host, 'buddy-naar-dock')
assert buddy.place == 'dock'
try:
    shell['show_animation'](host, 'poweroff')
except ValueError:
    pass
else:
    raise AssertionError('onbekende animatie geaccepteerd')
host.claude = None
try:
    shell['show_animation'](host, 'buddy-rust')
except RuntimeError as error:
    assert 'buddy' in str(error).lower()
else:
    raise AssertionError('buddy-animatie zonder buddy geaccepteerd')

print('PASS: claude-harness')
