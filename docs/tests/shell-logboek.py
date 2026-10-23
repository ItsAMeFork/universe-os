"""Silent failures reach shell.log (0.2.25 work): renderer crash, page load failure, resolution change."""
import os, re
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pakket', 'universe-os', 'usr', 'lib', 'universe-os')
web = open(os.path.join(root, 'shell', 'webview.py'), encoding='utf-8').read()
assert "'web-process-crashed'" in web and "'load-failed'" in web
assert 'bridge.log(' in web  # the bridge log is the shell log (stdout, supervisor writes it to shell.log)
displays = open(os.path.join(root, 'universe-displays'), encoding='utf-8').read()
assert 'def note(' in displays and "note('resolutie niet gezet" in displays
assert "note('%s naar" in displays and 'done.returncode' in displays and 'else:\n        note(' in displays
session = open(os.path.join(root, 'shell', 'session.py'), encoding='utf-8').read()
line = next(l for l in session.splitlines() if 'universe-displays resolution' in l)
assert '2>>' in line and 'shell.log' in line and '>/dev/null 2>&1' not in line
assert 'mkdir -p' in session and session.index('mkdir -p') < session.index('universe-displays resolution')
print('ok')
