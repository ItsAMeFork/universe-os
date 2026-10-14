"""Headless contract for the assistant: keyring (no plaintext), confirmation before send
and calendar create, screen-control session gate, audit log, and the Claude allow-list.
No GTK, no real network, no real keyring, no /dev/uinput."""
import ast
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'
SHELL = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'
os.environ['XDG_DATA_HOME'] = tempfile.mkdtemp(prefix='assistent-data-')
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='assistent-config-')
os.environ['XDG_RUNTIME_DIR'] = tempfile.mkdtemp(prefix='assistent-run-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='assistent-home-')
sys.path.insert(0, str(CLAUDE))

import accounts  # noqa: E402
import brein  # noqa: E402
import confirm  # noqa: E402
import screen  # noqa: E402
import universe_mcp as mcp  # noqa: E402

PASSWORD = 'geheim-wachtwoord-42'
TOKEN = 'ya29-super-geheim-token-zz'
REFRESH = '1//super-geheim-refresh-zz'
CLIENT_SECRET = 'geheim-client-zz'
memory = accounts.MemoryKeyring()
accounts.set_store(memory)


def db_text():
    return Path(brein.path()).read_bytes()


# --- keyring: the password is not in brein.db ---
public = accounts.add_imap('School', 'jesse@example.com', 'imap.example.com', 'smtp.example.com',
                           'jesse@example.com', PASSWORD, 993, 465)
assert public['adres'] == 'jesse@example.com'
assert public['scopes'] == ['IMAP', 'SMTP']
assert PASSWORD.encode() not in db_text()
blob = memory.get_password(accounts.SERVICE, 'koppeling:' + public['id'])
assert PASSWORD in blob and 'imap.example.com' not in blob

try:
    brein.save_account({'id': 'x', 'provider': 'imap', 'naam': 'x', 'password': PASSWORD})
    raise AssertionError('wachtwoord in het brein geaccepteerd')
except ValueError as error:
    assert 'sleutelbos' in str(error)

listed = accounts.list_public()
assert listed[0]['id'] == public['id']
assert PASSWORD not in json.dumps(listed)

# --- OAuth device flow stores the token only in the keyring ---
calls = []


def http(method, url, data=None, headers=None):
    calls.append((method, url.split('?')[0]))
    if url.endswith('/device/code'):
        return {'status': 200, 'json': {'device_code': 'dev-code', 'user_code': 'ABCD-1234',
                'verification_url': 'https://example.test/device', 'interval': 1}}
    if url.endswith('/token'):
        return {'status': 200, 'json': {'access_token': TOKEN, 'refresh_token': REFRESH, 'expires_in': 3600}}
    if 'userinfo' in url:
        return {'status': 200, 'json': {'email': 'jesse@example.com'}}
    raise AssertionError(url)


started = accounts.start_oauth('google', 'device', client_id='public.apps.googleusercontent.com',
                               client_secret=CLIENT_SECRET, http=http)
assert started['user_code'] == 'ABCD-1234'
assert 'device_code' not in started
assert TOKEN not in json.dumps(started)
config_text = Path(accounts._config_path()).read_text(encoding='utf-8')
assert 'public.apps.googleusercontent.com' in config_text
assert CLIENT_SECRET not in config_text
done = accounts.poll_oauth(started['flow'], http=http)
assert done['klaar'] is True and done['account']['adres'] == 'jesse@example.com'
assert TOKEN not in json.dumps(done)
assert TOKEN.encode() not in db_text() and REFRESH.encode() not in db_text()
assert CLIENT_SECRET.encode() not in db_text()

loop = accounts.start_oauth('microsoft', 'loopback', client_id='public-ms', client_secret=CLIENT_SECRET, serve=False)
assert 'code_challenge=' in loop['url'] and 'code_challenge_method=S256' in loop['url']
assert CLIENT_SECRET not in loop['url']
assert '127.0.0.1' in loop['url']

# --- mail send is impossible without a yes, and the dialog shows the letter ---
sent = []


class FakeSMTP:
    def __init__(self, host, port, timeout=20):
        sent.append(('open', host, port))

    def login(self, user, password):
        assert password == PASSWORD
        sent.append('login')

    def send_message(self, message):
        sent.append(('send', message['To'], message['Subject']))

    def quit(self):
        sent.append('quit')


seen = {}


def confirmer(title, text):
    seen['title'] = title
    seen['text'] = text
    return seen.get('yes', False)


try:
    accounts.send_mail(account=public['id'], to='docent@example.com', subject='Ouderavond', body='Ik kom.', confirmer=None, smtp_factory=FakeSMTP)
    raise AssertionError('verstuurd zonder dialoog')
except PermissionError:
    pass
assert sent == []
assert brein.list_acties(status='geweigerd')[-1]['hulpmiddel'] == 'mail_send'

seen['yes'] = False
try:
    accounts.send_mail(account=public['id'], to='docent@example.com', subject='Ouderavond', body='Ik kom morgen.', confirmer=confirmer, smtp_factory=FakeSMTP)
    raise AssertionError('verstuurd na weigeren')
except PermissionError:
    pass
assert sent == []
assert 'docent@example.com' in seen['text'] and 'Ouderavond' in seen['text'] and 'Ik kom morgen.' in seen['text']
assert brein.list_acties(status='geweigerd')[-1]['samenvatting'].startswith('Naar docent@example.com')

try:
    accounts.send_mail(account=public['id'], to='docent@example.com', subject='Hoi\nBcc: ander@example.com', body='x', confirmer=confirmer, smtp_factory=FakeSMTP)
    raise AssertionError('koptekstinjectie')
except ValueError:
    pass
assert sent == []

seen['yes'] = True
result = accounts.send_mail(account=public['id'], to=['docent@example.com'], subject='Ouderavond', body='Ik kom.', confirmer=confirmer, smtp_factory=FakeSMTP)
assert result['verstuurd'] is True
assert ('send', 'docent@example.com', 'Ouderavond') in sent
assert brein.list_acties(status='goedgekeurd')[-1]['hulpmiddel'] == 'mail_send'
assert PASSWORD.encode() not in db_text()

# --- calendar create asks, and a denial does not call the server ---
cal = accounts.add_caldav('Agenda', 'jesse@example.com', 'https://cal.example.com/jesse/', 'jesse@example.com', PASSWORD)
puts = []


def opener(method, url, data, headers):
    puts.append((method, url, data))
    if method == 'REPORT':
        return 200, 'BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:les-1\nSUMMARY:Ouderavond\nDTSTART:20261014T170000Z\nDTEND:20261014T180000Z\nLOCATION:School\nEND:VEVENT\nEND:VCALENDAR\n'
    return 201, ''


seen['yes'] = False
try:
    accounts.create_event(account=cal['id'], titel='Tandarts', start='2026-10-20 09:00', eind='2026-10-20 09:30', plek='Centrum', confirmer=confirmer, opener=opener)
    raise AssertionError('afspraak gezet na weigeren')
except PermissionError:
    pass
assert puts == []
assert 'Tandarts' in seen['text'] and 'Centrum' in seen['text']

seen['yes'] = True
made = accounts.create_event(account=cal['id'], titel='Tandarts', start='2026-10-20 09:00', eind='2026-10-20 09:30', plek='Centrum', confirmer=confirmer, opener=opener)
assert made['gemaakt'] is True and puts and puts[0][0] == 'PUT' and 'SUMMARY:Tandarts' in puts[0][2]
assert PASSWORD.encode() not in db_text()
upcoming = accounts.list_events(account=cal['id'], opener=opener)
assert any(item['titel'] == 'Ouderavond' for item in upcoming)
brein.upsert_mail(public['id'], 'brief-1', 'Ouderavond', 'school@example.com', 'Donderdag om zeven')
lijst = brein.lijst('alles')
assert {'mail', 'agenda', 'actie'} <= {row['soort'] for row in lijst['rijen']}
assert any(star['soort'] == 'agenda' for star in lijst['sterren'])
assert any(row['status'] == 'goedgekeurd' for row in brein.lijst('acties')['rijen'])
only = brein.lijst('acties', 'Tandarts')
assert only['rijen'] and all('Tandarts' in row['tekst'] or 'Tandarts' in row['titel'] for row in only['rijen'])

# --- screen: off by default, panic clears it, sensitive keys and passwords ask ---
ran = []


def runner(op):
    ran.append(op)


try:
    screen.perform('muis', {'x': 10, 'y': 20}, confirmer=confirmer, runner=runner, have='ydotool')
    raise AssertionError('muis zonder toestemming')
except PermissionError as error:
    assert 'AI mag scherm bedienen' in str(error)
assert ran == []
assert brein.list_acties()[0]['status'] == 'geweigerd'

screen.allow()
assert screen.enabled()
screen.perform('muis', {'x': 12, 'y': 34}, confirmer=lambda *a: (_ for _ in ()).throw(AssertionError('dialoog')), runner=runner, have='ydotool')
assert ran[-1]['argv'][:4] == ['ydotool', 'mousemove', '--absolute', '-x']
assert ran[-1]['argv'][4:] == ['12', '-y', '34']

seen['yes'] = False
try:
    screen.perform('toets', {'toets': 'alt+f4'}, confirmer=confirmer, runner=runner, have='ydotool')
    raise AssertionError('alt+f4 zonder ja')
except PermissionError:
    pass
assert not any(op.get('argv', [None])[1:2] == ['key'] for op in ran)

seen['yes'] = True
before = len(ran)
screen.perform('toets', {'toets': 'ctrl+w'}, confirmer=confirmer, runner=runner, have='ydotool')
assert ran[-1]['argv'][0] == 'ydotool' and ran[-1]['argv'][1] == 'key'
assert len(ran) == before + 1

phrase = 'WACHTWOORD-NIET-LOGGEN-99'
seen['yes'] = True


def show_secret(title, text):
    seen['pw'] = text
    return True


screen.perform('typ', {'tekst': phrase, 'veld': 'wachtwoord'}, confirmer=show_secret, runner=runner, have='wtype')
assert phrase not in seen['pw']
assert phrase.encode() not in db_text()
assert any(phrase in json.dumps(op) for op in ran)  # the keystroke itself still has to carry the text
assert 'niet gelogd' in brein.list_acties()[0]['samenvatting']

seen['yes'] = False
try:
    screen.perform('klik', {'doel': 'Verwijderen'}, confirmer=confirmer, runner=runner, have='ydotool')
    raise AssertionError('verwijderen zonder ja')
except PermissionError:
    pass

screen.revoke()
assert not screen.enabled()
try:
    screen.perform('scroll', {'dy': -1}, runner=runner, have='evdev')
    raise AssertionError('scroll na paniek')
except PermissionError:
    pass

try:
    screen.plan('wtype', 'muis', {'x': 1, 'y': 1})
    raise AssertionError('wtype verplaatste de muis')
except RuntimeError as error:
    assert 'muis' in str(error).lower()

assert confirm.ask('Titel', 'Tekst', runner=lambda title, text: False) is False
assert confirm.ask('Titel', 'Tekst', runner=lambda title, text: title == 'Titel' and text == 'Tekst') is True

# --- allow-list: Claude cannot flip the screen switch or connect an account ---
def shell_parts():
    tree = ast.parse(SHELL.read_text(encoding='utf-8'))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            ids = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if 'CLAUDE_CALLS' in ids:
                nodes.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == 'Shell':
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == 'call':
                    nodes.append(item)
    namespace = {'threading': threading}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SHELL), 'exec'), namespace)
    return namespace


shell = shell_parts()
assert 'mail.send' in shell['CLAUDE_CALLS'] and 'agenda.create' in shell['CLAUDE_CALLS']
assert 'scherm.typ' in shell['CLAUDE_CALLS'] and 'scherm.focus' in shell['CLAUDE_CALLS']
for blocked in ('scherm.toestaan', 'scherm.intrekken', 'accounts.oauth_start', 'accounts.imap', 'accounts.disconnect'):
    assert blocked not in shell['CLAUDE_CALLS']
shell_text = SHELL.read_text(encoding='utf-8')
assert 'confirmer=_confirm' in shell_text
assert "cmd == 'scherm-stop'" in shell_text


def answer_of(host, line):
    got = []
    shell['call'](host, line, got.append)
    return got


class Blocking:
    def handlers(self):
        raise AssertionError('handler mocht niet lopen')

    bridge = type('B', (), {'threaded': set()})()


assert answer_of(Blocking(), 'call scherm.toestaan {}') == ['fout: niet toegestaan: scherm.toestaan']
assert answer_of(Blocking(), 'call accounts.imap {}') == ['fout: niet toegestaan: accounts.imap']

mcp_text = (CLAUDE / 'universe_mcp.py').read_text(encoding='utf-8')
assert 'smtplib' not in mcp_text and "shell('mail.send'" in mcp_text
assert mcp.TOOLS['mail_send'][3] is False
schema = mcp.TOOLS['mail_send'][1]
assert 'naar' in schema['required'] and 'onderwerp' in schema['required']


class FakeShell:
    def __init__(self):
        self.lines = []
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            os.unlink(mcp.SOCKET)
        except FileNotFoundError:
            pass
        self.sock.bind(mcp.SOCKET)
        self.sock.listen(4)
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
                data = b''
                conn.settimeout(1)
                while b'\n' not in data:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                self.lines.append(data.decode())
                conn.sendall(b'ok {"verstuurd": true}\n')
            finally:
                conn.close()

    def close(self):
        self.stop = True
        self.sock.close()
        self.thread.join(2)


fake = FakeShell()
try:
    reply = mcp.handle({'method': 'tools/call', 'params': {'name': 'mail_send', 'arguments': {
        'naar': 'docent@example.com', 'onderwerp': 'Hoi', 'tekst': 'Dag'}}})
finally:
    fake.close()
assert not reply.get('isError'), reply
assert fake.lines and fake.lines[0].startswith('call mail.send ')
body = json.loads(fake.lines[0].split(' ', 2)[2])
assert body['naar'] == 'docent@example.com' and body['onderwerp'] == 'Hoi' and 'bevestig' not in body

center = (ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/control_center.py').read_text(encoding='utf-8')
assert "'accounts.list'" in center and "'scherm.toestaan'" in center and '_grant_screen' in center
control = (UI / 'control.js').read_text(encoding='utf-8')
assert 'mountAccounts' in control and 'accounts:' in control
ui_accounts = (UI / 'accounts-ui.js').read_text(encoding='utf-8')
assert 'AI mag scherm bedienen' in ui_accounts and 'Super+Escape' in ui_accounts
nebula = (UI / 'brein-nevel.js').read_text(encoding='utf-8')
assert 'Mail' in nebula and 'Agenda' in nebula and 'Acties' in nebula
assert 'shadowBlur' not in nebula
deb = (ROOT / 'pakket/universe-os/DEBIAN/control').read_text(encoding='utf-8')
for package in ('python3-keyring', 'gnome-keyring', 'libpam-gnome-keyring', 'python3-evdev', 'wtype', 'python3-caldav'):
    assert package in deb
handleiding = (ROOT / 'docs/HANDLEIDING.md').read_text(encoding='utf-8')
claude_doc = (ROOT / 'docs/CLAUDE-IN-UNIVERSE.md').read_text(encoding='utf-8')
assert 'AI mag scherm bedienen' in handleiding and 'sleutelbos' in handleiding
assert 'mail_send' in claude_doc and 'scherm.toestaan' in claude_doc
shortcuts = (ROOT / 'pakket/universe-os/usr/share/universe-os/shortcuts.json').read_text(encoding='utf-8')
assert 'scherm-stop' in shortcuts and 'W-Escape' in shortcuts

for script in ('accounts-ui.js', 'brein-nevel.js', 'control.js', 'panel.js', 'settings-index.js'):
    checked = subprocess.run(['node', '--check', str(UI / script)], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr

print('PASS: ai-assistent')
