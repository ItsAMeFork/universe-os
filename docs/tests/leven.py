"""Screen history, local voice, morning briefing, ghost hints, goals and zen/god.

Temporary home. No grim, no tesseract, no microphone, no zenity.
"""
import ast
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude'
SHELL = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'

os.environ['XDG_DATA_HOME'] = tempfile.mkdtemp(prefix='leven-data-')
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='leven-config-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='leven-home-')
sys.path.insert(0, str(CLAUDE))
sys.path.insert(0, str(SHELL))

import brein  # noqa: E402
import briefing  # noqa: E402
import doelen  # noqa: E402
import ghost  # noqa: E402
import kast  # noqa: E402
import schermgeschiedenis as scherm  # noqa: E402
import stem  # noqa: E402
import taken  # noqa: E402
import config  # noqa: E402

PNG = b'\x89PNG\r\nkoffie'
when = time.mktime((2026, 10, 15, 8, 0, 0, 0, 0, -1))

assert scherm.public()['aan'] is False
assert scherm.grab('firefox', 'nieuws', shot=lambda: PNG, read_text=lambda _b: 'koffie', now=when)['reden'] == 'uit'
scherm.configure({'aan': True, 'elke': 0, 'dagen': 7})
assert scherm.grab('org.keepassxc.KeePassXC', 'Kluis', shot=lambda: PNG, read_text=lambda _b: 'geheim', now=when)['reden'] == 'uitgesloten'
assert scherm.grab('firefox', 'Rabobank internetbankieren', shot=lambda: PNG, read_text=lambda _b: 'saldo', now=when)['reden'] == 'uitgesloten'
assert scherm.lijst() == []
saved = scherm.grab('firefox', 'Ochtend', shot=lambda: PNG, read_text=lambda _b: 'koffie op het bureau', now=when)
assert saved['bewaard'] is True
assert scherm.search('koffie')[0]['tekst'].startswith('koffie')
assert 'pad' not in scherm.search('koffie')[0]
scherm.configure({'uitsluiten': ['thunderbird']})
assert scherm.grab('thunderbird', 'post', shot=lambda: PNG, read_text=lambda _b: 'mail', now=when + 5)['reden'] == 'uitgesloten'
scherm.configure({'pauze': True})
assert scherm.grab('firefox', 'later', shot=lambda: PNG, read_text=lambda _b: 'x', now=when + 10)['reden'] == 'pauze'
with brein.connect() as db:
    db.execute('UPDATE scherm_beelden SET op = ?', (when - 10 * 86400,))
removed = scherm.purge(when)
assert removed == 1 and scherm.lijst() == []
scherm.configure({'aan': False, 'pauze': False})

assert stem.enabled() is False
spoken = []
assert stem.speak('hoi', runner=spoken.append)['reden'] == 'uit'
assert spoken == []
opened = []
assert stem.listen_once(capture=lambda: opened.append('mic') or b'wav', transcribe=lambda _b: 'hé buddy')['reden'] == 'uit'
assert opened == []
stem.configure({'aan': True})
heard_clip = stem.listen_once(capture=lambda: b'wav', transcribe=lambda _b: 'Hé Buddy, de agenda')
assert heard_clip['gehoord'] is True and 'agenda' in heard_clip['tekst']
assert stem.listen_once(capture=lambda: b'', transcribe=lambda _b: 'hé buddy')['reden'] == 'stil'
assert stem.speak('hoi buddy', runner=spoken.append)['ok'] is True
assert spoken == ['hoi buddy']
assert stem.heard('Hé Buddy, wat staat er vandaag')
assert stem.heard('hey buddy') is True
assert stem.heard('goedemorgen') is False
script = stem.install_script()
assert 'OWW=0.6.0' in script and 'openwakeword==$OWW' in script
assert 'v1.9.5' in script and 'd1be6fde11ac6e0407606b4e42fe72d34add8037' in script
assert '5359861c739e955e79d9a303bcbc70fb988958b1' in script and 'ggml-base.bin' in script
assert '2023.11.14-2' in script
assert 'screenpipe' not in script.lower()
assert 'whisper.cpp' in script and 'piper' in script
stem.configure({'aan': False})

brein.upsert_agenda('thuis', 'tand', 'Tandarts', when + 2 * 3600, when + 3 * 3600, 'Centrum')
brein.upsert_agenda('thuis', 'dienst', 'Nachtdienst', when + 5 * 3600, when + 8 * 3600, 'Plein')
brein.upsert_mail('thuis', 'brief', 'Ouderavond', 'school@example.com', 'donderdag', when, True)
info = briefing.compose(when)
assert info['aan'] is True
assert info['aftellen']['titel'] == 'Tandarts'
assert info['aftellen']['tekst'] == 'over 2 uur'
assert any(item['titel'] == 'Nachtdienst' for item in info['diensten'])
assert any('Ouderavond' in line for line in info['regels'])
morning = briefing.due(when)
assert morning and morning['dag'] == '2026-10-15'
briefing.mark_seen(when)
assert briefing.due(when) is None
assert briefing.due(when + 8 * 3600) is None
briefing.configure({'aan': False})
assert briefing.compose(when)['aan'] is False
briefing.configure({'aan': True})

assert ghost.public()['aan'] is False
assert ghost.pick(when, items=[{'key': 'a', 'tekst': 'hoi'}]) is None
kast.update('ghost', aan=True, minuten=15, max_per_dag=2)
night = time.mktime((2026, 10, 15, 23, 0, 0, 0, 0, -1))
assert ghost.quiet(night) is True
assert ghost.allow(night) is False
assert ghost.allow(when) is True
choice = ghost.pick(when, items=[{'key': 'afspraak:1', 'tekst': 'Over 10 min: Tandarts.'}])
assert choice['key'] == 'afspraak:1'
ghost.mark(when)
ghost.mark(when + 16 * 60)
assert ghost.allow(when + 40 * 60) is False
kast.update('ghost', aan=False)

made = doelen.add('leer de sterren')
board = next(item for item in taken.bord()['taken'] if item['id'] == made['taak_id'])
assert board['soort'] == 'doel'
assert [step['status'] for step in board['stappen']] == ['todo', 'todo', 'todo', 'todo']
assert doelen.tick()['reden'] == 'uit'
doelen.set_background(True)
plan = doelen.tick()
assert plan['starten'] is True and 'leer de sterren' in plan['prompt']
assert 'toestemming' in plan['prompt']
assert doelen.tick()['reden'] == 'bezig'
assert 'Open doel' in doelen.line()
with brein.connect() as db:
    db.execute("UPDATE doelen SET status = 'klaar'")
    db.execute("UPDATE taken SET status = 'klaar', eind = ? WHERE soort = 'doel'", (when,))
paid = doelen.add('betaal de rekening')
waiting = doelen.tick()
assert waiting['starten'] is False and waiting['wacht'] is True
with brein.connect() as db:
    statuses = [row['status'] for row in db.execute(
        'SELECT status FROM stappen WHERE taak_id = ? ORDER BY volgorde', (paid['taak_id'],))]
assert statuses == ['todo', 'todo', 'todo', 'todo']
doelen.set_background(False)

assert config.settings()['aiBlik'] == 'god'
config.set_setting('aiBlik', 'zen')
assert config.settings()['aiBlik'] == 'zen'
try:
    config.set_setting('aiBlik', 'zwerm')
    raise SystemExit('blik zwerm')
except ValueError:
    pass
config.set_setting('aiBlik', 'god')

blob = '\n'.join(path.read_text(encoding='utf-8') for path in CLAUDE.glob('*.py'))
assert 'screenpipe' not in blob.lower()
assert 'Screenpipe' in (ROOT / 'docs/PREMADE-FEATURES.md').read_text(encoding='utf-8')
assert '0.6.0' in (ROOT / 'docs/PREMADE-FEATURES.md').read_text(encoding='utf-8')

shell = (SHELL / 'universe_shell.py').read_text(encoding='utf-8')
tree = ast.parse(shell)
calls = None
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == 'CLAUDE_CALLS':
                calls = ast.literal_eval(node.value)
for name in ('brein.scherm.lijst', 'brein.scherm.wissen', 'briefing.nu', 'buddy.vraag', 'leven.set', 'stem.terminal'):
    assert name not in calls
assert 'briefing.nu' in shell and 'buddy.vraag' in shell

ui = (UI / 'leven-ui.js').read_text(encoding='utf-8')
nebula = (UI / 'brein-nevel.js').read_text(encoding='utf-8')
common = (UI / 'common.css').read_text(encoding='utf-8')
assert 'Hé Buddy' in ui and 'Ghost-modus' in ui and 'Mission Control' in ui and 'Brein-tijdlijn' in ui
assert 'Tijdlijn' in nebula
assert 'mode-zen' in common and 'zen-input' in common
assert 'three' not in nebula.lower() and 'd3' not in nebula and 'shadowBlur' not in nebula
for script in ('leven-ui.js', 'brein-werk.js', 'brein-nevel.js', 'ai-ui.js', 'world.js', 'api.js'):
    checked = subprocess.run(['node', '--check', str(UI / script)], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr

print('leven ok')
