"""Local Brein timeline: off until the user turns it on.

Pause writes no new rows. The switch and the rows stay on this computer.
Ghost mode (when that module is present) still stops the open-app timeline.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BREIN_PATH = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude/brein.py'
SHELL_PATH = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui/brein-nevel.js'
CSS = ROOT / 'pakket/universe-os/usr/share/universe-os/ui/world.css'

os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='tijdlijn-config-')
os.environ['XDG_DATA_HOME'] = tempfile.mkdtemp(prefix='tijdlijn-data-')
os.environ['XDG_RUNTIME_DIR'] = tempfile.mkdtemp(prefix='tijdlijn-run-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='tijdlijn-home-')

spec = importlib.util.spec_from_file_location('brein_tijdlijn', BREIN_PATH)
brein = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brein)


def rows():
    with brein.connect() as db:
        return list(db.execute('SELECT item FROM timeline ORDER BY at'))


def count():
    return len(rows())


status = brein.timeline_status()
assert status['aan'] is False and status['pauze'] is False
assert status['lokaal'] is True and status['wolk'] is False
assert status['tekst'] == 'Uit'
assert 'computer' in status['uitleg'].lower()
assert not Path(brein.timeline_config_path()).exists()

brein.log_event('app', 'firefox.desktop', 'Firefox')
assert count() == 0

turned = brein.set_timeline(aan=True)
assert turned['aan'] is True and turned['pauze'] is False and turned['wolk'] is False
assert turned['tekst'] == 'Aan'
config_path = Path(brein.timeline_config_path())
assert config_path.parent == Path(os.environ['XDG_CONFIG_HOME']) / 'universe-os'
assert oct(config_path.stat().st_mode & 0o777) == '0o600'
stored = json.loads(config_path.read_text(encoding='utf-8'))
assert stored == {'aan': True, 'pauze': False}
assert 'http' not in config_path.read_text(encoding='utf-8').lower()

brein.log_event('app', 'firefox.desktop', 'Firefox')
assert [row['item'] for row in rows()] == ['firefox.desktop']

paused = brein.set_timeline(pauze=True)
assert paused['aan'] is True and paused['pauze'] is True and paused['tekst'] == 'Pauze'
assert 'niets' in paused['uitleg'].lower()
brein.log_event('app', 'geheim.desktop', 'Geheim')
assert [row['item'] for row in rows()] == ['firefox.desktop']

resumed = brein.set_timeline(pauze=False)
assert resumed['pauze'] is False and resumed['tekst'] == 'Aan'
brein.log_event('file', '/tmp/notitie.txt', 'notitie.txt')
assert [row['item'] for row in rows()] == ['firefox.desktop', '/tmp/notitie.txt']

off = brein.set_timeline(aan=False)
assert off['aan'] is False and off['tekst'] == 'Uit'
brein.log_event('app', 'na-uit.desktop', 'Na uit')
assert count() == 2

# Ghost mode wins: an enabled switch stops new open-app rows even when the timeline is on.
brein.set_timeline(aan=True, pauze=False)
ghost = types.ModuleType('ghost_modus')
ghost.enabled = lambda: True
sys.modules['ghost_modus'] = ghost
try:
    brein.log_event('app', 'tijdens-ghost.desktop', 'Ghost')
    assert not any(row['item'] == 'tijdens-ghost.desktop' for row in rows())
    ghost.enabled = lambda: (_ for _ in ()).throw(RuntimeError('kapot'))
    brein.log_event('app', 'ghost-kapot.desktop', 'Kapot')
    assert any(row['item'] == 'ghost-kapot.desktop' for row in rows())
finally:
    sys.modules.pop('ghost_modus', None)

brein.log_event('app', 'na-ghost.desktop', 'Na ghost')
assert any(row['item'] == 'na-ghost.desktop' for row in rows())

config_path.write_text('{', encoding='utf-8')
broken = brein.timeline_status()
assert broken['aan'] is False and broken['pauze'] is False
brein.log_event('app', 'kapotte-config.desktop', 'Kapot')
assert not any(row['item'] == 'kapotte-config.desktop' for row in rows())

source = BREIN_PATH.read_text(encoding='utf-8')
for needle in ('urlopen', 'requests', 'http://', 'https://'):
    assert needle not in source

shell = SHELL_PATH.read_text(encoding='utf-8')
assert "'brein.tijdlijn'" in shell and "'brein.tijdlijn.set'" in shell
assert "'brein.tijdlijn'" not in shell.split('CLAUDE_CALLS', 1)[1].split('}', 1)[0]
assert "'brein.tijdlijn.set'" not in shell.split('CLAUDE_CALLS', 1)[1].split('}', 1)[0]

ui = UI.read_text(encoding='utf-8')
assert "class:'nebula-pause'" in ui
assert "'Pauze'" in ui
assert "call('brein.tijdlijn.set'" in ui
assert 'aria-pressed' in ui
css = CSS.read_text(encoding='utf-8')
assert '.nebula-pause' in css

checked = subprocess.run(['node', '--check', str(UI)], capture_output=True, text=True)
assert checked.returncode == 0, checked.stderr

print('PASS: brein-tijdlijn')
