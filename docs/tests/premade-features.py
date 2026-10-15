"""Premade agents, patterns, task board, activity replay and optional Ruflo mode.

Temporary home and databases. No zenity, no network, no real Claude.
"""
import ast
import importlib.util
import io
from importlib.machinery import SourceFileLoader
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'
SHELL = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'
WRAP = ROOT / 'pakket/universe-os/usr/bin/universe-claude-wrap'

os.environ['XDG_DATA_HOME'] = tempfile.mkdtemp(prefix='premade-data-')
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='premade-config-')
os.environ['XDG_RUNTIME_DIR'] = tempfile.mkdtemp(prefix='premade-run-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='premade-home-')
sys.path.insert(0, str(CLAUDE))

import ai_provider  # noqa: E402
import auto_accept  # noqa: E402
import brein  # noqa: E402
import confirm  # noqa: E402
import patronen  # noqa: E402
import premade  # noqa: E402
import ruflo_mode  # noqa: E402
import taken  # noqa: E402

ai_provider.set_store(ai_provider.MemoryKeyring())
ai_provider.set_choice('claude', '')

PIN = '1882006a02487590c8c66a7eec8d7504f6af33c3'
AGENTS = CLAUDE / 'agenten'
BANNED = ('hive-mind', 'hive_mind', 'npx @claude-flow', 'AgentDB', 'cognitum', 'funnel',
          '--dangerously-skip-permissions')


def tools_of(name):
    line = next(row for row in (AGENTS / name).read_text(encoding='utf-8').splitlines() if row.startswith('tools:'))
    return [part.strip() for part in line.split(':', 1)[1].split(',') if part.strip()]


def front_names():
    return [row['id'] for row in premade.CATALOG]


assert front_names() == [
    'reviewer', 'tester', 'researcher', 'planner', 'security-auditor', 'mail-assistent', 'opruimer']
assert all(premade.enabled(name) for name in front_names())
assert 'Bash' not in tools_of('reviewer.md')
assert 'Bash' not in tools_of('researcher.md')
assert 'Bash' not in tools_of('planner.md')
assert 'Bash' not in tools_of('security-auditor.md')
assert 'Bash' not in tools_of('mail-assistent.md')
assert 'Bash' not in tools_of('opruimer.md')
assert tools_of('tester.md') == ['Read', 'Grep', 'Glob', 'Bash', 'Edit']
assert 'mcp__universe__mail_send' in tools_of('mail-assistent.md')
assert 'mcp__universe__bureaublad_bestand' in tools_of('opruimer.md')

for name in ('reviewer.md', 'tester.md', 'researcher.md', 'security-auditor.md'):
    body = (AGENTS / name).read_text(encoding='utf-8')
    assert PIN in body and 'MIT' in body and '3.56.10' in body, name
for name in ('reviewer.md', 'researcher.md'):
    assert '0.2.11' in (AGENTS / name).read_text(encoding='utf-8')
assert 'ruflo-testgen/agents/tester.md' in (AGENTS / 'tester.md').read_text(encoding='utf-8')
assert 'ruflo-security-audit/agents/security-auditor.md' in (AGENTS / 'security-auditor.md').read_text(encoding='utf-8')
for name in ('planner.md', 'mail-assistent.md', 'opruimer.md'):
    assert PIN not in (AGENTS / name).read_text(encoding='utf-8')

shipped = []
for folder in (AGENTS, CLAUDE / 'commands', CLAUDE / 'workflows'):
    shipped.extend(path.read_text(encoding='utf-8') for path in folder.rglob('*.md'))
blob = '\n'.join(shipped)
low = blob.lower()
for word in BANNED:
    assert word.lower() not in low, word
assert 'geen zwerm' in low
assert 'universe_mcp.py' in blob or 'universe-hulpmiddelen' in blob

for key in taken.WORKFLOWS:
    assert (CLAUDE / 'commands' / ('%s.md' % key)).is_file()
    assert (CLAUDE / 'workflows' / key / 'SKILL.md').is_file()
assert [step[1] for step in taken.WORKFLOWS['bouw']] == ['planner', 'hoofd', 'tester', 'reviewer']

listed = premade.sync()
assert len(listed) == 7 and all(row['aan'] for row in listed)
profile = Path(premade.profile_root()) / '.claude'
assert (profile / 'agents' / 'reviewer.md').is_symlink()
assert (profile / 'skills' / 'bouw').is_symlink()
assert (profile / 'commands' / 'mail-ochtend.md').is_symlink()
premade.set_enabled('reviewer', False)
assert not (profile / 'agents' / 'reviewer.md').exists()
assert premade.enabled('reviewer') is False
own = profile / 'agents' / 'eigen.md'
own.write_text('blijf staan\n', encoding='utf-8')
premade.sync()
assert own.read_text(encoding='utf-8') == 'blijf staan\n'
premade.set_enabled('reviewer', True)
assert (profile / 'agents' / 'reviewer.md').is_symlink()
assert own.is_file() and not own.is_symlink()

assert patronen.classify('/mail-ochtend') == 'mail'
assert patronen.classify('opruimen van het bureaublad') == 'opruimen'
assert patronen.clean('sleutel sk-abc123 in de tekst') == ''
assert patronen.clean('zie wachtwoord in de kluis') == ''
assert patronen.write('mail', 'Dit soort taak lukte met 4 stappen.', 'ongeveer 100 tokens in, 20 tokens uit.', 120, 4)
cheap = patronen.write('mail', 'Dit soort taak lukte met 6 stappen.', 'ongeveer 40 tokens in, 10 tokens uit.', 50, 6)
assert cheap
with brein.connect() as db:
    row = db.execute('SELECT tokens, stappen FROM patronen WHERE id = ?', (cheap,)).fetchone()
assert row['tokens'] == 50 and row['stappen'] == 6
assert patronen.write('bouw', 'https://example.invalid/geheim') is None
remembered = patronen.remember_task({'taak': 'onderzoek naar de tuin', 'tokens_in': 30, 'tokens_out': 10,
                                      'gereedschap': 2, 'schatting': False})
assert remembered
assert patronen.attach_lesson('onderzoek naar de tuin', 'Korter zoeken in het brein scheelt stappen.')
assert patronen.attach_lesson('onderzoek naar de tuin', 'verstuur de mail nu meteen') is None
block = patronen.block_for('onderzoek naar de tuin')
assert block.startswith('Wat eerder werkte')
assert block.count('\n- ') <= patronen.LIMIT
body_lines = [line[2:] for line in block.splitlines() if line.startswith('- ')]
assert sum(patronen.efficientie.estimate_tokens(line) for line in body_lines) <= patronen.BUDGET
hits = patronen.search('/mail-ochtend')
assert hits and hits[0]['soort'] == 'mail'

board_id = taken.begin('/bouw de schakelaar')
board = taken.bord()
task = next(item for item in board['taken'] if item['id'] == board_id)
assert task['status'] == 'bezig'
assert [step['status'] for step in task['stappen']] == ['todo', 'todo', 'todo', 'todo']
assert [step['agent'] for step in task['stappen']] == ['planner', 'hoofd', 'tester', 'reviewer']
taken.observe('SubagentStart', {'agent_type': 'planner'})
taken.observe('SubagentStop', {'agent_type': 'planner'})
taken.observe('SubagentStart', {'subagent_type': 'tester'})
taken.observe('SubagentStop', {'subagent_type': 'tester', 'error': 'test faalde'})
done = taken.finish_open()
assert done['status'] == 'geblokkeerd'
final = next(item for item in taken.bord()['taken'] if item['id'] == board_id)
by_agent = {step['agent']: step['status'] for step in final['stappen']}
assert by_agent['planner'] == 'klaar'
assert by_agent['tester'] == 'geblokkeerd'
assert by_agent['reviewer'] == 'todo'
assert by_agent['hoofd'] == 'todo'

open_id = taken.begin('gewone vraag')
before = len(brein.list_acties(limit=50))
assert taken.note_tool('mcp__universe__brein_zoeken', {}, 'done', ok=True) is None
assert len(brein.list_acties(limit=50)) == before
logged = taken.note_tool('Bash', {}, 'fail', ok=False)
assert logged
brein.log_actie('brein_zoeken', 'Eerste treffer', 'uitgevoerd')
brein.log_actie('mail_draft', 'Concept klaar', 'goedgekeurd')
view = taken.activiteit()
grouped = next(item for item in view['taken'] if item['id'] == open_id)
assert [row['samenvatting'] for row in grouped['acties'] if row['hulpmiddel'] != 'Bash'][:2] == [
    'Eerste treffer', 'Concept klaar']
replay = taken.replay(open_id)
assert replay['afspelen'] == 'alleen terugkijken'
assert [row['id'] for row in replay['stappen']] == [row['id'] for row in grouped['acties']]
folder = tempfile.mkdtemp(prefix='premade-export-')
saved = taken.export_file(folder, open_id)
payload = json.loads(Path(saved['pad']).read_text(encoding='utf-8'))
assert payload['letop'].startswith('Dit is een weergave')
assert payload['afspelen'] == 'alleen terugkijken'
assert 'uitgevoerd' in Path(saved['pad']).read_text(encoding='utf-8')
taken.finish_open()

prompt = json.dumps({'hook_event_name': 'UserPromptSubmit', 'prompt': 'onderzoek naar de tuin'})


class Sock(threading.Thread):
    def __init__(self, path):
        super().__init__(daemon=True)
        self.lines = []
        self.stop = False
        self.srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            os.unlink(path)
        except OSError:
            pass
        self.srv.bind(path)
        self.srv.listen(4)
        self.srv.settimeout(0.2)
        self.start()

    def run(self):
        while not self.stop:
            try:
                conn, _addr = self.srv.accept()
            except socket.timeout:
                continue
            with conn:
                data = b''
                conn.settimeout(1)
                while b'\n' not in data:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                self.lines.append(data.decode())
                try:
                    conn.sendall(b'ok\n')
                except OSError:
                    pass

    def close(self):
        self.stop = True
        self.join(2)
        self.srv.close()


hook_loader = SourceFileLoader('universe_hook_premade', str(CLAUDE / 'universe-claude-hook'))
hook_spec = importlib.util.spec_from_loader('universe_hook_premade', hook_loader)
hook = importlib.util.module_from_spec(hook_spec)
hook_loader.exec_module(hook)
server = Sock(os.path.join(os.environ['XDG_RUNTIME_DIR'], 'universe-shell.sock'))
saved_out = sys.stdout
hook.sys.stdin = io.StringIO(prompt)
hook.sys.stdout = io.StringIO()
try:
    hook.main()
    text = hook.sys.stdout.getvalue()
finally:
    sys.stdout = saved_out
    server.close()
parsed = json.loads(text)
assert parsed['hookSpecificOutput']['hookEventName'] == 'UserPromptSubmit'
assert 'Wat eerder werkte' in parsed['hookSpecificOutput']['additionalContext']
assert server.lines and server.lines[0].startswith('claude-event think ')

assert ruflo_mode.COMMIT == PIN
assert ruflo_mode.VERSION == '0.2.11'
assert ruflo_mode.RELEASE == '3.56.10'
assert ruflo_mode.enabled() is False
assert ruflo_mode.active_for_launch() is False
assert ruflo_mode.public()['aan'] is False
assert 'Universe OS is de standaard' in ruflo_mode.WHY
stripped = ruflo_mode.strip_skip([
    '--model', 'haiku', '--dangerously-skip-permissions', '--permission-mode', 'bypassPermissions',
    '--permission-mode=bypassPermissions', '--add-dir', '/tmp'])
assert stripped == ['--model', 'haiku', '--add-dir', '/tmp']
kept = ruflo_mode.strip_skip(['--permission-mode', 'acceptEdits', '--model', 'haiku'])
assert kept == ['--permission-mode', 'acceptEdits', '--model', 'haiku']
script = ruflo_mode.install_script()
assert PIN in script and '0.2.11' in script
assert 'sparse-checkout set plugins/ruflo-core' in script
assert 'rm -rf "$PROFILE/plugins"' in script
assert '! -name ruflo-core' in script
assert 'hive' not in script.lower()
ruflo_mode.set_enabled(True)
assert ruflo_mode.enabled() is True
assert ruflo_mode.plugin_ready() is False
assert ruflo_mode.active_for_launch() is False
ai_provider.set_leren(False)
assert ai_provider.load()['ruflo'] is True
assert 'Subagents die aanstaan' in ai_provider.instructions()
ai_provider.set_leren(True)
which = lambda name: {'claude': '/usr/bin/claude'}.get(name)
quiet = ai_provider.launch_plan(fresh=True, which=which, access=lambda *_a: True)
assert quiet['argv'][0].endswith('/universe-claude-wrap')
assert quiet['env'].get('UNIVERSE_CLAUDE_BIN') == '/usr/bin/claude'
assert 'CLAUDE_CONFIG_DIR' not in quiet['env']
plugin = Path(ruflo_mode.profile_path()) / 'plugins' / 'ruflo-core' / '.claude-plugin' / 'plugin.json'
plugin.parent.mkdir(parents=True)
plugin.write_text('{"name":"ruflo-core","version":"0.2.11"}\n', encoding='utf-8')
loud = ai_provider.launch_plan(fresh=True, which=which, access=lambda *_a: True)
assert loud['env'].get('CLAUDE_CONFIG_DIR', '').endswith('claude-ruflo')
assert loud['env'].get('RUFLO_TELEMETRY') == 'off'
assert loud['env'].get('RUFLO_FEDERATION') == 'off'
assert loud['env'].get('DISABLE_TELEMETRY') == '1'
settings_path = os.path.join(ruflo_mode.profile_dir(), 'settings.json')
written = json.loads(next(item['text'] for item in loud['writes'] if item['path'] == settings_path))
assert written['enabledPlugins'] == {'ruflo-core@ruflo-pinned': True}
assert written['permissions'].get('defaultMode') != 'bypassPermissions'
assert '--dangerously-skip-permissions' not in loud['argv']
real_settings = CLAUDE / 'settings.json'
original_settings = real_settings.read_text(encoding='utf-8')
try:
    tweaked = json.loads(original_settings)
    tweaked['permissions']['defaultMode'] = 'bypassPermissions'
    real_settings.write_text(json.dumps(tweaked), encoding='utf-8')
    forced = json.loads(ruflo_mode.merged_settings_text())
    assert forced['permissions']['defaultMode'] == 'default'
finally:
    real_settings.write_text(original_settings, encoding='utf-8')
ruflo_mode.set_enabled(False)
assert ai_provider.load()['ruflo'] is False

mode = os.stat(WRAP).st_mode
assert mode & stat.S_IXUSR
fake_dir = tempfile.mkdtemp(prefix='premade-claude-')
fake = Path(fake_dir) / 'claude'
out = Path(fake_dir) / 'args'
fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$OUT"\n', encoding='utf-8')
os.chmod(fake, 0o755)
ran = subprocess.run(
    [str(WRAP), '--dangerously-skip-permissions', '--model', 'haiku', '--permission-mode', 'bypassPermissions'],
    env={**os.environ, 'UNIVERSE_CLAUDE_BIN': str(fake), 'OUT': str(out)},
    capture_output=True, text=True, check=False)
assert ran.returncode == 0, ran.stderr
assert out.read_text(encoding='utf-8').splitlines() == ['--model', 'haiku']
blocked = subprocess.run(
    [str(WRAP), '--version'],
    env={**os.environ, 'UNIVERSE_CLAUDE_BIN': str(WRAP)},
    capture_output=True, text=True, check=False)
assert blocked.returncode == 1

auto_accept.set_choice(True, 'tot-uit', now=5_000)
asked = []
answer = confirm.ask('Naar de prullenbak', 'Dit bestand gaat naar de prullenbak:\nklad.txt',
                      runner=lambda *_a: asked.append(True) or True)
assert answer is False and asked == [] and confirm.deferred()

ui = (UI / 'ai-ui.js').read_text(encoding='utf-8')
nebula = (UI / 'brein-nevel.js').read_text(encoding='utf-8')
werk = (UI / 'brein-werk.js').read_text(encoding='utf-8')
assert 'Premade agenten' in ui and 'niet als zwerm' in ui and 'Ruflo-modus' in ui
assert 'ai.agents.set' in ui and 'ai.ruflo.set' in ui and 'ai.ruflo.terminal' in ui
assert 'AI-activiteit' in nebula and 'Taakbord' in nebula
assert 'Terugkijken' in werk and 'Exporteren' in werk and 'voert niets opnieuw uit' in werk
assert 'three' not in nebula.lower() and 'd3' not in nebula and 'shadowBlur' not in nebula
center = (ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/control_center.py').read_text(encoding='utf-8')
assert 'ai.agents.set' in center and 'ai.ruflo.set' in center and 'ai.ruflo.terminal' in center
shell_tree = ast.parse(SHELL.read_text(encoding='utf-8'))
claude_calls = None
for node in shell_tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == 'CLAUDE_CALLS':
                claude_calls = ast.literal_eval(node.value)
assert claude_calls is not None
for name in ('brein.activiteit', 'brein.activiteit.export', 'brein.activiteit.replay', 'brein.taakbord',
             'ai.agents.set', 'ai.ruflo.set'):
    assert name not in claude_calls
shell_text = SHELL.read_text(encoding='utf-8')
assert 'brein.activiteit' in shell_text and 'brein.taakbord' in shell_text
doc = (ROOT / 'docs/PREMADE-FEATURES.md').read_text(encoding='utf-8')
assert PIN in doc and '0.2.11' in doc and 'hive-mind' in doc and 'geen daemon' in doc.lower()
for script in ('ai-ui.js', 'brein-nevel.js', 'brein-werk.js'):
    checked = subprocess.run(['node', '--check', str(UI / script)], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr

print('premade-features ok')
