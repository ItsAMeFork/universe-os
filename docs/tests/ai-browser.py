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

ai = (UI / 'ai-ui.js').read_text(encoding='utf-8')
page = (UI / 'accounts-ui.js').read_text(encoding='utf-8')
assert 'Claude in Chrome' in ai and 'chrome.setup' in ai and 'Belangrijke domeinen en woorden' in ai
assert 'auto.regels' in ai and '--chrome' not in ai
assert 'Log gewoon in in Chrome' in page
assert 'Google maakt dit lastig' not in page
review = (ROOT / 'docs/REVIEW-AI-STACK.md').read_text(encoding='utf-8')
assert 'dl.google.com/linux/chrome/deb' in review and 'trixie-backports' in review and 'OmniRoute' in review
assert 'OpenClaude' in review
center = (ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/control_center.py').read_text(encoding='utf-8')
assert 'chrome.setup' in center and 'confirm.ask' in center
print('PASS: ai-browser')
