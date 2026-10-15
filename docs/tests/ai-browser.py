"""Headless: Claude in Chrome is the mail path, and ordinary replies can leave while auto-accept is on."""
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'
os.environ['XDG_DATA_HOME'] = tempfile.mkdtemp(prefix='browser-data-')
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='browser-config-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='browser-home-')
sys.path.insert(0, str(CLAUDE))

import accounts  # noqa: E402
import ai_provider  # noqa: E402
import auto_accept  # noqa: E402
import brein  # noqa: E402
import chrome_agent  # noqa: E402
import sandbox  # noqa: E402
import screen  # noqa: E402

ai_provider.set_store(ai_provider.MemoryKeyring())
accounts.set_store(accounts.MemoryKeyring())
ai_provider.set_choice('claude', '')

home = Path(os.environ['HOME'])
assert chrome_agent.status(home=home, which=lambda name: None)['chrome'] is False
assert chrome_agent.status(home=home, which=lambda name: None)['verbonden'] is False
ext = home / '.config/google-chrome/Default/Extensions' / chrome_agent.EXTENSION_ID / '1.0.36'
ext.mkdir(parents=True)
host = home / '.config/google-chrome/NativeMessagingHosts' / chrome_agent.HOST_FILE
host.parent.mkdir(parents=True)
host.write_text('{}\n', encoding='utf-8')
which_chrome = lambda name: '/usr/bin/google-chrome-stable' if name in ('google-chrome-stable', 'google-chrome') else None
connected = chrome_agent.status(home=home, which=which_chrome)
assert connected['chrome'] and connected['extensie'] and connected['host'] and connected['verbonden']
assert chrome_agent.binary(lambda name: '/opt/openclaude/google-chrome' if 'chrome' in name else None) is None
script = chrome_agent.install_script()
assert 'https://dl.google.com/linux/chrome/deb/' in script
assert chrome_agent.EXTENSION_ID in script
assert 'openclaude' not in script.lower()
assert chrome_agent.plan_setup(False)['script'].startswith('set -e')
assert chrome_agent.plan_setup(True)['open'][-1] == chrome_agent.STORE_URL

which = lambda name: {
    'claude': '/usr/bin/claude', 'python3': '/usr/bin/python3', 'google-chrome-stable': '/usr/bin/google-chrome-stable',
}.get(name)
plan = ai_provider.launch_plan(fresh=True, which=which, access=lambda *_a: True)
assert '--chrome' in plan['argv'] and plan['chrome'] is True
plain = lambda name: {'claude': '/usr/bin/claude', 'python3': '/usr/bin/python3'}.get(name)
without = ai_provider.launch_plan(fresh=True, which=plain, access=lambda *_a: True)
assert '--chrome' not in without['argv'] and without['chrome'] is False

wrapped = sandbox.command(['/usr/bin/claude', '--chrome'], '/tmp/work', str(home), ['/usr'],
                          '/run/user/1/universe-shell.sock', '/tmp/ai-runtime', share_host=True)
assert '--tmpfs' not in wrapped and '/tmp' in wrapped
assert 'DBUS_SESSION_BUS_ADDRESS' in wrapped and '/dev/uinput' in wrapped
assert '--setenv' not in wrapped
closed = sandbox.command(['/usr/bin/claude'], '/tmp/work', str(home), ['/usr'],
                         '/run/user/1/universe-shell.sock', '/tmp/ai-runtime')
assert '--tmpfs' in closed

mouse = screen.desktop_mouse_script()
assert 'trixie-backports' in mouse and 'KERNEL=="uinput"' in mouse

assert 'bank' in auto_accept.public()['regels'] and 'overheid' in auto_accept.public()['regels']
auto_accept.set_regels('school.example\nbank\n')
assert auto_accept.public()['regels'] == ['school.example', 'bank']
now = time.time()
auto_accept.remember_addresses(['docent@example.com'])
auto_accept.set_choice(True, 'tot-uit', now=now)
assert auto_accept.public()['regels'] == ['school.example', 'bank']
kind, reasons = auto_accept.mail_decision(['docent@example.com'], 'Hoi', 'Ik kom morgen.', now=now)
assert kind == 'automatisch' and reasons == []
kind, reasons = auto_accept.mail_decision(['nieuw@example.com'], 'Hoi', 'Kort.', now=now)
assert kind == 'wacht' and 'nieuwe ontvanger' in reasons
kind, reasons = auto_accept.mail_decision(['docent@example.com'], 'Factuur', 'De bank schrijft af.', now=now)
assert kind == 'wacht' and 'bank' in reasons
kind, reasons = auto_accept.mail_decision(['juf@school.example'], 'Hoi', 'Kort.', now=now)
assert kind == 'wacht' and 'school.example' in reasons
crowd = ['a@example.com', 'b@example.com', 'c@example.com', 'd@example.com']
auto_accept.remember_addresses(crowd)
kind, reasons = auto_accept.mail_decision(crowd, 'Hoi', 'Kort.', now=now)
assert kind == 'wacht' and 'meer dan 3 ontvangers' in reasons
kind, reasons = auto_accept.mail_decision(['docent@example.com'], 'Hoi', 'Kort.', bijlagen=1, now=now)
assert kind == 'wacht' and 'bijlage' in reasons
kind, reasons = auto_accept.mail_decision(['docent@example.com'], 'Hoi', 'Kort.', vlag=True, now=now)
assert kind == 'wacht' and 'gemarkeerd als belangrijk' in reasons
kind, reasons = auto_accept.mail_decision(['docent@example.com'], 'Hoi', 'x' * 900, now=now)
assert kind == 'wacht' and 'lang bericht' in reasons
auto_accept.stop(now=now + 10)
kind, _reasons = auto_accept.mail_decision(['docent@example.com'], 'Hoi', 'Ik kom morgen.', now=now + 10)
assert kind == 'vraag'

auto_accept.set_regels('\n'.join(auto_accept.DEFAULT_REGELS))
auto_accept.set_choice(True, 'tot-uit', now=time.time())


def boom(*_a):
    raise AssertionError('venster terwijl dit automatisch mag')


body = 'Ik kom morgen.\n' + ('zin ' * 120)
result = accounts.authorize_browser(to='docent@example.com', subject='Hoi', body=body, confirmer=boom)
assert result['mag'] is True and result['automatisch'] is True and result['verstuurd'] is False
logged = brein.list_acties(status='automatisch')[0]
assert body in logged['detail'] and len(logged['detail']) > 400
try:
    accounts.authorize_browser(to='docent@example.com', subject='Factuur', body='De bank schrijft af.', confirmer=boom)
    raise SystemExit('bankmail automatisch')
except PermissionError as error:
    assert 'terug' in str(error).lower()
assert body in brein.list_acties(status='wacht')[0]['detail'] or 'bank' in brein.list_acties(status='wacht')[0]['detail']
waiting = brein.list_acties(status='wacht')[0]
assert 'De bank schrijft af.' in waiting['detail']

sent = []


class FakeSMTP:
    def __init__(self, host, port, timeout=20):
        sent.append('open')

    def login(self, user, password):
        sent.append('login')

    def send_message(self, message):
        sent.append(message['Subject'])

    def quit(self):
        sent.append('quit')


public = accounts.add_imap('School', 'jesse@example.com', 'imap.example.com', 'smtp.example.com',
                           'jesse@example.com', 'geheim-wachtwoord-42', 993, 465)
ai_provider.set_mail_via('account')
delivered = accounts.send_mail(account=public['id'], to='docent@example.com', subject='Hoi', body='Ik kom morgen.',
                               confirmer=boom, smtp_factory=FakeSMTP)
assert delivered['verstuurd'] is True and 'Hoi' in sent
try:
    accounts.send_mail(account=public['id'], to='nieuw@example.com', subject='Hoi', body='Kort.',
                       confirmer=boom, smtp_factory=FakeSMTP)
    raise SystemExit('nieuwe ontvanger verstuurd')
except PermissionError:
    pass

assert chrome_agent.judge_browser('browser_navigate', {'url': 'https://mail.google.com'})[0] == 'uitgevoerd'
assert chrome_agent.judge_browser('browser_click', {'tekst': 'wachtwoord geheim'})[2] == 'Tekst niet opgeslagen.'
assert chrome_agent.judge_browser('browser_click', {'name': 'Send'})[0] == 'automatisch'
assert chrome_agent.judge_browser('mcp__universe__mail_send', {'name': 'Send'})[0] == 'vraag'
assert chrome_agent.judge_browser('browser_click', {'name': 'Betalen'})[0] == 'wacht'
assert chrome_agent.judge_browser('browser_click', {'name': 'Verwijderen'})[0] == 'wacht'

opened = []


def refuse_setup(*_a):
    return False


try:
    chrome_agent.perform_setup(opened.append, refuse_setup, lambda _name: '/usr/bin/xfce4-terminal', which=lambda _name: None)
    raise SystemExit('installatie zonder toestemming')
except PermissionError as error:
    assert 'niets geïnstalleerd' in str(error)
assert opened == []


def allow_setup(title, text):
    assert 'apt-bron' in text and 'Claude' in title
    return True


started = chrome_agent.perform_setup(opened.append, allow_setup, lambda _name: '/usr/bin/xfce4-terminal', which=lambda _name: None)
assert opened and opened[0][0] == 'xfce4-terminal' and 'google-chrome-stable' in opened[0][-1]
assert started['bezig'] is True and started['route'] == 'claude-in-chrome'
try:
    chrome_agent.perform_setup(opened.append, allow_setup, lambda _name: None, which=lambda _name: None)
    raise SystemExit('apt zonder terminal')
except RuntimeError as error:
    assert 'terminal' in str(error).lower()

import confirm  # noqa: E402
auto_accept.set_choice(True, 'tot-uit', now=time.time())
forced = []
assert confirm.ask('Chrome en Claude in Chrome', 'installeer uit de apt-bron', runner=lambda *_a: forced.append(1) or True, force=True) is True
assert forced == [1]
assert confirm.ask('Programma openen', 'Rekenmachine', runner=lambda *_a: forced.append(2) or True) is True
assert forced == [1]

ai = (UI / 'ai-ui.js').read_text(encoding='utf-8')
page = (UI / 'accounts-ui.js').read_text(encoding='utf-8')
assert 'Claude in Chrome' in ai and 'chrome.setup' in ai and 'Belangrijke domeinen en woorden' in ai
assert 'auto.regels' in ai and '--chrome' not in ai
assert 'voorkeursroute' in ai
assert 'Log gewoon in in Chrome' in page
assert 'Google maakt dit lastig' not in page
route = (UI / 'claude-route.js').read_text(encoding='utf-8')
world = (UI / 'world.js').read_text(encoding='utf-8')
dock = (UI / 'dock.js').read_text(encoding='utf-8')
shell = (ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py').read_text(encoding='utf-8')
assert 'Claude in Chrome installeren' in route and 'browser.claude.setup' in route
assert 'Versturen, betalen, wissen' in route
assert 'mountClaudeRoute' in world
assert "chooseBrowser:!!(data&&data.chooseBrowser)" in world or 'chooseBrowser' in world
assert 'Claude in Chrome' in dock and 'chooseBrowser:true' in dock
calls = shell.split('CLAUDE_CALLS = ')[1].split('}')[0]
assert 'browser.claude' not in calls
assert 'browser.claude.setup' in shell and 'force=True' in shell
review = (ROOT / 'docs/REVIEW-AI-STACK.md').read_text(encoding='utf-8')
assert 'dl.google.com/linux/chrome/deb' in review and 'trixie-backports' in review and 'OmniRoute' in review
assert 'OpenClaude' in review
assert 'Internet-planeet' in review
center = (ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/control_center.py').read_text(encoding='utf-8')
assert 'chrome.setup' in center and 'confirm.ask' in center and 'force=True' in center
print('PASS: ai-browser')
