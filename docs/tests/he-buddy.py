"""Hé Buddy: optional spoken prompts. Off until the user turns it on in the Brein.

No GTK, no microphone, no real speech synthesis. A runner stands in for espeak.
"""
import ast
import importlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHELL = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'

os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='he-buddy-config-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='he-buddy-home-')
sys.path.insert(0, str(SHELL))

config = importlib.import_module('config')
buddy_voice = importlib.import_module('buddy_voice')

assert config.settings()['heBuddy'] is False
spoken = []
assert buddy_voice.speak('hallo', runner=spoken.append)['reden'] == 'uit'
assert spoken == []

quiet = buddy_voice.speak('hallo', runner=spoken.append, settings={'heBuddy': False})
assert quiet['reden'] == 'uit' and quiet.get('ok') is not True
assert spoken == []

on = buddy_voice.speak('  De batterij   is bijna leeg.  ', runner=spoken.append, settings={'heBuddy': True})
assert on['ok'] is True and on['tekst'] == 'De batterij is bijna leeg.'
assert spoken == ['De batterij is bijna leeg.']
assert buddy_voice.speak('   ', runner=spoken.append, settings={'heBuddy': True})['reden'] == 'leeg'
assert spoken == ['De batterij is bijna leeg.']

public = buddy_voice.configure(True)
assert public['aan'] is True and public['tekst'] == 'Aan'
assert config.settings()['heBuddy'] is True
assert buddy_voice.enabled() is True
buddy_voice.speak('tweede melding', runner=spoken.append)
assert spoken[-1] == 'tweede melding'
off = buddy_voice.configure(False)
assert off['aan'] is False and off['tekst'] == 'Uit'
assert buddy_voice.speak('derde', runner=spoken.append)['reden'] == 'uit'
assert spoken == ['De batterij is bijna leeg.', 'tweede melding']
assert 'stil' in off['uitleg'].lower()

# Off never starts a speech process, even when a binary is on PATH.
calls = []
buddy_voice.shutil.which = lambda name: calls.append(name) or '/usr/bin/espeak-ng'
assert buddy_voice.speak('niet hardop', settings={'heBuddy': False})['reden'] == 'uit'
assert calls == []

hints = (SHELL / 'buddy_hints.py').read_text(encoding='utf-8')
assert 'buddy_voice.speak' in hints
shell = (SHELL / 'universe_shell.py').read_text(encoding='utf-8')
assert "'buddy.stem'" in shell
assert 'Hé Buddy zet je zelf aan in het Brein.' in shell
tree = ast.parse(shell)
calls_allow = None
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == 'CLAUDE_CALLS':
                calls_allow = ast.literal_eval(node.value)
assert calls_allow is not None
assert 'buddy.stem' not in calls_allow

ui = (UI / 'brein-nevel.js').read_text(encoding='utf-8')
css = (UI / 'world.css').read_text(encoding='utf-8')
assert 'Hé Buddy' in ui
assert "call('buddy.stem'" in ui
assert "role:'switch'" in ui
assert 'nebula-voice' in ui and 'nebula-voice' in css
assert 'heBuddy' in ui
for script in (UI / 'brein-nevel.js',):
    checked = subprocess.run(['node', '--check', str(script)], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr

print('PASS: he-buddy')
