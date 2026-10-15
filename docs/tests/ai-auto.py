"""Headless: Claude sessions use OmniRoute or LiteLLM, never OpenClaude, and auto-accept stays off."""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'
os.environ['XDG_DATA_HOME'] = tempfile.mkdtemp(prefix='auto-data-')
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='auto-config-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='auto-home-')
sys.path.insert(0, str(CLAUDE))

import ai_provider  # noqa: E402
import auto_accept  # noqa: E402
import brein  # noqa: E402
import confirm  # noqa: E402

ai_provider.set_store(ai_provider.MemoryKeyring())
ai_provider.set_choice('claude', '')

assert ai_provider.load()['sessie_route'] == 'claude'
assert 'openclaude' not in ai_provider.PROVIDERS
try:
    ai_provider.set_choice('openclaude', '')
    raise SystemExit('openclaude geaccepteerd')
except ValueError as error:
    assert 'OpenClaude' in str(error)
try:
    ai_provider.set_sessie('omniroute')
    raise SystemExit('omniroute zonder aanbieder')
except ValueError:
    pass
ai_provider.add_upstream('openrouter')
ai_provider.set_sessie('omniroute')
which = lambda name: {'claude': '/usr/bin/claude', 'python3': '/usr/bin/python3'}.get(name)
plan = ai_provider.launch_plan(fresh=True, which=which, access=lambda *_a: True)
assert plan['env'].get('ANTHROPIC_BASE_URL') == 'http://127.0.0.1:20128'
ai_provider.set_sessie('claude')
back = ai_provider.launch_plan(fresh=True, which=which, access=lambda *_a: True)
assert back['env'].get('ANTHROPIC_BASE_URL') is None
assert back['argv'][0].endswith('/universe-claude-wrap')
assert back['env'].get('UNIVERSE_CLAUDE_BIN') == '/usr/bin/claude'
try:
    ai_provider.set_litellm_url('https://gateway.example/v1')
    raise SystemExit('litellm buiten de computer')
except ValueError:
    pass
ai_provider.set_litellm_url('http://127.0.0.1:4000')
ai_provider.set_sessie('litellm')
lite = ai_provider.launch_plan(fresh=True, which=which, access=lambda *_a: True)
assert lite['env'].get('ANTHROPIC_BASE_URL') == 'http://127.0.0.1:4000'
assert '20128' not in lite['env'].get('ANTHROPIC_BASE_URL', '')
assert ai_provider.bin_for('claude', lambda name: '/opt/openclaude/claude' if name == 'claude' else None, lambda path, *_a: 'openclaude' in str(path).lower()) is None
assert ai_provider.PROVIDERS['opencode']['uitleg'].startswith('MIT')
assert 'Apache-2.0' in ai_provider.PROVIDERS['goose']['uitleg']
opencode_script = ai_provider.install_script('opencode')
goose_script = ai_provider.install_script('goose')
assert 'OpenCode' in opencode_script and 'opencode.ai/install' in opencode_script
assert 'openclaude' not in opencode_script.split('curl', 1)[1].lower()
assert 'Goose' in goose_script and 'aaif-goose/goose' in goose_script
assert 'openclaude' not in goose_script.split('curl', 1)[1].lower()

assert auto_accept.active(now=1_000) is False
assert confirm.ask('Programma openen', 'Bestanden', runner=lambda *_a: False) is False
started = auto_accept.set_choice(True, '30m', now=1_000)
assert started['aan'] is True and started['tekst'].startswith('Aan tot')
assert auto_accept.active(now=1_000 + 29 * 60) is True
assert auto_accept.active(now=1_000 + 31 * 60) is False

def boom(*_a):
    raise AssertionError('venster terwijl automatisch aan staat')

auto_accept.set_choice(True, 'tot-uit', now=5_000)
assert auto_accept.active(now=5_000 + 10 * 3600) is True
assert confirm.ask('Programma openen', 'Bestanden en een concept', runner=boom) is True
assert confirm.ask('Agenda lezen', 'Komende afspraken', runner=boom) is True
assert brein.list_acties(status='automatisch')
for title, text in (
    ('Claude wil een e-mail versturen', 'Naar a@b.c'),
    ('Klik op: Verwijderen', 'Bestand weg'),
    ('Betaling', 'Nu betalen'),
    ('Wachtwoord', 'veld'),
    ('AI mag het scherm bedienen', 'tot je afmeldt'),
):
    assert confirm.ask(title, text, runner=boom) is False
    assert confirm.deferred() is True
assert brein.list_acties(status='wacht')
assert auto_accept.stop(now=9_000)['aan'] is False
assert confirm.ask('Programma openen', 'Bestanden', runner=lambda *_a: False) is False

folder = Path(os.environ['HOME']) / 'klad'
folder.mkdir()
target = folder / 'notitie.txt'
target.write_text('hallo', encoding='utf-8')
row = brein.log_actie('bestand', 'Notitie', 'automatisch', 'gemaakt',
                      json.dumps({'soort': 'bestand', 'pad': str(target)}))
assert brein.undo_actie(row)['ongedaan'] is True
assert not target.exists()
assert brein.list_acties()[0]['status'] == 'ongedaan'
try:
    brein.undo_actie(brein.log_actie('mail_send', 'verstuurd', 'wacht', 'wacht'))
    raise SystemExit('wachtende mail ongedaan gemaakt')
except ValueError:
    pass

ui = (UI / 'ai-ui.js').read_text(encoding='utf-8')
panel = (UI / 'panel.js').read_text(encoding='utf-8')
shell = (ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py').read_text(encoding='utf-8')
assert 'Automatisch toestaan' in ui and 'auto.set' in ui and 'Terug naar Claude' in ui
assert 'Geen OpenClaude' in ui and 'LiteLLM' in ui
assert 'Automatisch toestaan' in panel and 'auto.set' in panel
assert 'auto_accept.stop' in shell
center = (ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/claude_ui.py').read_text(encoding='utf-8')
assert 'Terug naar Claude' in center and 'Automatisch toestaan' in center
print('PASS: ai-auto')
