"""Zen and God stay off until the user turns them on.

God auto-approves ordinary confirmations. Sending, paying, deleting and passwords
still open the dialog. The assistant cannot turn God on.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude'
SHELL = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'
os.environ['XDG_DATA_HOME'] = tempfile.mkdtemp(prefix='modes-data-')
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='modes-config-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='modes-home-')
sys.path.insert(0, str(SHELL))
sys.path.insert(0, str(CLAUDE))

import auto_accept  # noqa: E402
import confirm  # noqa: E402
import config  # noqa: E402
import modes  # noqa: E402
import universe_mcp  # noqa: E402

assert config.settings()['zen'] is False
assert config.settings()['god'] is False
assert modes.zen() is False
assert modes.god() is False
assert universe_mcp.SECURITY_SETTINGS == {'lockMinutes', 'god'}


def boom(*_a):
    raise AssertionError('venster terwijl God gewone stappen zelf doet')


assert confirm.ask('Programma openen', 'Bestanden', runner=lambda *_a: False) is False
config.set_setting('god', True)
assert modes.god() is True
assert confirm.ask('Programma openen', 'Bestanden en een concept', runner=boom) is True
assert confirm.ask('Agenda lezen', 'Komende afspraken', runner=boom) is True
assert confirm.ask('AI mag het scherm bedienen', 'tot je afmeldt', runner=boom) is True
assert confirm.ask('Firewall', 'regel aanpassen', runner=boom) is True
for title, text in (
    ('Claude wil een e-mail versturen', 'Naar a@b.c'),
    ('Klik op: Verwijderen', 'Bestand weg'),
    ('Betaling', 'Nu betalen'),
    ('Wachtwoord', 'veld'),
    ('Prullenbak', 'map wissen'),
):
    assert confirm.ask(title, text, runner=lambda *_a: False) is False
    assert confirm.deferred() is False

auto_accept.set_choice(True, 'tot-uit', now=5_000)
assert confirm.ask('Betaling', 'Nu betalen', runner=boom) is False
assert confirm.deferred() is True
assert confirm.ask('Programma openen', 'Bestanden', runner=boom) is True
auto_accept.stop(now=9_000)

kind, _reasons = auto_accept.mail_decision(['docent@example.com'], 'Hoi', 'Kort bericht.')
assert kind == 'vraag'

config.set_setting('god', False)
assert modes.god() is False
assert confirm.ask('Programma openen', 'Bestanden', runner=lambda *_a: False) is False
config.set_setting('zen', True)
assert modes.zen() is True
assert config.settings()['zen'] is True
config.set_setting('zen', False)
assert modes.zen() is False

ui = (UI / 'ai-ui.js').read_text(encoding='utf-8')
panel = (UI / 'panel.js').read_text(encoding='utf-8')
api = (UI / 'api.js').read_text(encoding='utf-8')
css = (UI / 'common.css').read_text(encoding='utf-8')
world = (UI / 'world.js').read_text(encoding='utf-8')
shell = (ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py').read_text(encoding='utf-8')
hints = (ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/buddy_hints.py').read_text(encoding='utf-8')
assert "modeSwitch('Zen'" in ui and "modeSwitch('God'" in ui
assert 'config.set' in ui and 'zen:true' not in ui and 'god:true' not in ui
assert "modeSwitch('Zen'" in panel and "modeSwitch('God'" in panel
assert 'mode-zen' in api and 'mode-god' in api
assert 'html.mode-zen .dock' in css and 'html.mode-zen .zen-input' in css
assert 'claude.ask' in world and 'zen-input' in world
assert "SECURITY_SETTINGS = {'lockMinutes', 'god'}" in shell
assert 'claude.ask' not in shell.split('CLAUDE_CALLS', 1)[1].split('CLAUDE_RUN', 1)[0]
assert "set_setting('god', False)" in shell
assert "config.settings().get('zen')" in hints
print('PASS: zen-god')
