"""0.2.30: Windows-sneltoetsen in het gegenereerde labwc rc.xml, geen onderschepte Ctrl+C/X/V, klembordhulp."""
import importlib.machinery
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / 'pakket/universe-os'
shortcuts = json.loads((PKG / 'usr/share/universe-os/shortcuts.json').read_text(encoding='utf-8'))
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp()
sys.path.insert(0, str(PKG / 'usr/lib/universe-os/shell'))
import config  # noqa: E402
config.DEFAULT_SHORTCUTS = str(PKG / 'usr/share/universe-os/shortcuts.json')
import session  # noqa: E402
rc = ET.fromstring(session.rc_xml())
binds = {b.get('key'): b for b in rc.iter('keybind')}
want = {'Super_L': 'universe-ctl start', 'W-Tab': 'universe-ctl overview', 'W-r': 'universe-ctl overview',
        'W-d': 'universe-ctl desktop', 'W-e': 'universe-ctl run files', 'W-l': 'universe-lock',
        'W-i': 'universe-ctl run control', 'W-v': 'universe-klembord kies', 'W-period': 'universe-klembord emoji',
        'W-S-s': 'universe-screenshot --gebied', 'Print': 'universe-screenshot',
        'C-S-Escape': 'universe-ctl run monitor', 'C-A-Delete': 'universe-klembord beveiliging'}
for key, command in want.items():
    assert key in binds, key
    assert binds[key].find('action').get('command') == command, key
for key, action in {'A-Tab': 'NextWindow', 'A-S-Tab': 'PreviousWindow', 'A-F4': 'Close'}.items():
    assert binds[key].find('action').get('name') == action, key
for key in ('W-Left', 'W-Right', 'W-Up', 'W-Down'):
    assert key in binds, key
# Copy/cut/paste and the other app shortcuts stay with the programs.
for key in ('C-c', 'C-x', 'C-v', 'C-a', 'C-z', 'C-y', 'C-s', 'C-f', 'C-p', 'C-n', 'C-w', 'C-t', 'F2', 'Delete', 'S-Delete'):
    assert key not in binds and key.lower() not in {k.lower() for k in binds}, key
keys = [s['key'].lower() for s in shortcuts]
assert len(keys) == len(set(keys)), 'dubbele sneltoets'
assert 'universe-klembord bewaak' in session.AUTOSTART
assert '"<Primary>v"' in (PKG / 'etc/xdg/xfce4/terminal/accels.scm').read_text()

# Clipboard history: newest on top, no doubles, max 25, no empty text.
kl = importlib.machinery.SourceFileLoader('kl', str(PKG / 'usr/bin/universe-klembord')).load_module()
items = []
for i in range(30):
    items = kl.add(items, 'tekst %d' % i)
assert len(items) == 25 and items[0] == 'tekst 29'
items = kl.add(items, 'tekst 10')
assert items[0] == 'tekst 10' and items.count('tekst 10') == 1
assert kl.add(items, '   ') == items and kl.add(items, 'x' * 20000) == items
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, 'k.json')
    kl.save(items, p)
    assert kl.load(p) == items and (os.stat(p).st_mode & 0o777) == 0o600
# WebKit pages: no page swallows Ctrl+key events globally.
for js in (PKG / 'usr/share/universe-os/ui').glob('*.js'):
    text = js.read_text(encoding='utf-8', errors='replace')
    assert "ctrlKey&&e.preventDefault" not in text.replace(' ', ''), js
print('PASS: sneltoetsen')
