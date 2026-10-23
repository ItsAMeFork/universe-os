"""Ghost mode stays off until the user turns it on.

Off: logging, file index, login update check and cloud assistants behave as before.
On: no new brain timeline, action or token rows, no file-content index, shell lines
lose their payload, login does not phone home, and cloud assistants do not start.
The local model still may. This is not the suggestion limiter on henk/premade-features.
"""
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude'
SHELL = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='ghost-config-')
os.environ['XDG_DATA_HOME'] = tempfile.mkdtemp(prefix='ghost-data-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='ghost-home-')
sys.path.insert(0, str(CLAUDE))
sys.path.insert(0, str(SHELL))

import ghost_modus  # noqa: E402
import brein  # noqa: E402
import launch  # noqa: E402
import recoll_index  # noqa: E402
import updates  # noqa: E402

updates.STATUS = os.path.join(os.environ['XDG_DATA_HOME'], 'updates-status.json')

assert ghost_modus.enabled() is False
assert ghost_modus.public()['aan'] is False
assert ghost_modus.public()['tekst'] == 'Uit'
assert 'logboek' in ghost_modus.public()['uitleg'].lower()
assert 'wolk' in ghost_modus.public()['uitleg'].lower()
assert ghost_modus.cloud_refusal('claude') is None
assert ghost_modus.cloud_refusal('ollama') is None
assert ghost_modus.shell_line('modules geladen na 1.2 s; pad /home/geheim') == 'modules geladen na 1.2 s; pad /home/geheim'

secret = 'wachtwoord-niet-in-het-logboek'
row = brein.log_actie('mail_read', 'Gelezen: hallo', 'uitgevoerd', secret)
assert row
assert brein.list_acties(query='hallo')
brein.log_event('app', 'firefox.desktop', 'Firefox')
assert brein.timeline(days=1)
eff = brein.log_efficientie('claude', 'haiku', 10, 4, True, 1, 2, 'korte taak')
assert eff
assert 'recollindex' in recoll_index.index_command()

called = {'install': 0}

def boom():
    called['install'] += 1
    raise AssertionError('updatecontrole terwijl ghost uit hoort de echte taak te mogen starten')

updates.install = boom
try:
    updates.check_at_login()
except AssertionError:
    pass
assert called['install'] == 1

launched = {}

def fake_plan(**_kwargs):
    launched['yes'] = True
    return {'ok': True, 'provider': 'claude', 'argv': ['/usr/bin/claude'],
            'env': {'UNIVERSE_AI_SANDBOX': '0'}, 'writes': [], 'cwd': '/tmp'}

real_plan = launch.ai_provider.launch_plan
launch.ai_provider.launch_plan = fake_plan
open_plan = launch.prepare()
assert open_plan['ok'] is True and launched.get('yes') is True
launch.ai_provider.launch_plan = real_plan

turned = ghost_modus.set_enabled(True)
assert turned['aan'] is True and turned['tekst'] == 'Aan'
assert ghost_modus.enabled() is True
mode = os.stat(os.path.join(os.environ['XDG_CONFIG_HOME'], 'universe-os', 'ghost-modus.json')).st_mode & 0o777
assert mode == 0o600
raw = json.loads(Path(os.environ['XDG_CONFIG_HOME'], 'universe-os', 'ghost-modus.json').read_text())
assert raw == {'aan': True}

assert ghost_modus.shell_line('ruimtewereld zichtbaar na 0.4 s; pad /home/geheim') is None
assert ghost_modus.shell_line('opdracht mail versturen mislukt: %s' % secret) == 'mislukt'
assert secret not in (ghost_modus.shell_line('UI ai: %s' % secret) or '')
assert ghost_modus.shell_line('UI ai: %s' % secret) == 'fout'
refusal = ghost_modus.cloud_refusal('claude')
assert refusal and 'Ghost-modus' in refusal and 'wolk' in refusal.lower()
assert ghost_modus.cloud_refusal('codex') and ghost_modus.cloud_refusal('gemini')
assert ghost_modus.cloud_refusal('opencode') and ghost_modus.cloud_refusal('goose')
assert ghost_modus.cloud_refusal('ollama') is None

before = len(brein.list_acties())
assert brein.log_actie('mail_read', 'Gelezen: geheim', 'uitgevoerd', secret) is None
assert len(brein.list_acties()) == before
assert not any(item['wat'] == 'ghost-secret.desktop' for item in brein.timeline(days=1))
brein.log_event('app', 'ghost-secret.desktop', secret)
assert not any(item['wat'] == 'ghost-secret.desktop' for item in brein.timeline(days=1))
assert brein.log_efficientie('claude', 'haiku', 3, 3, True, 0, 1, secret) is None
assert recoll_index.index_command() == ['true']
assert recoll_index.search('geheim document') == []

called['install'] = 0
assert updates.check_at_login() is False
assert called['install'] == 0

launch.ai_provider.launch_plan = fake_plan
blocked = launch.prepare()
assert blocked['ok'] is False
assert 'Ghost-modus' in blocked['fout']
assert blocked.get('writes') in (None, [])

def local_plan(**_kwargs):
    return {'ok': True, 'provider': 'ollama', 'argv': ['python3', 'ollama_host.py'],
            'env': {'HOME': os.environ['HOME'], 'UNIVERSE_AI_SANDBOX': '0'},
            'writes': [], 'cwd': os.environ['HOME'], 'key_env': '', 'key': None}

launch.ai_provider.launch_plan = local_plan
local = launch.prepare()
assert local['ok'] is True and local['provider'] == 'ollama'
launch.ai_provider.launch_plan = real_plan

off = ghost_modus.set_enabled(False)
assert off['aan'] is False and ghost_modus.enabled() is False
assert ghost_modus.cloud_refusal('claude') is None
assert 'recollindex' in recoll_index.index_command()
broken = Path(os.environ['XDG_CONFIG_HOME'], 'universe-os', 'ghost-modus.json')
broken.write_text('{', encoding='utf-8')
importlib.reload(ghost_modus)
assert ghost_modus.enabled() is False

ui = (UI / 'ghost-ui.js').read_text(encoding='utf-8')
control = (UI / 'control.js').read_text(encoding='utf-8')
center = (SHELL / 'control_center.py').read_text(encoding='utf-8')
index = (UI / 'settings-index.js').read_text(encoding='utf-8')
assert 'ghost-hero' in ui and 'width:120px' in ui and 'height:68px' in ui
assert 'Ghost-modus' in ui
assert "mountGhost" in control and "call('ghost.status')" in control and "call('ghost.set'" in control
assert control.index('mountGhost') < control.index("call('firewall.get')")
assert "'ghost.status'" in center and "'ghost.set'" in center
assert 'ghost' in index and 'logboek' in index and 'wolk' in index
assert not (CLAUDE / 'ghost.py').exists()
