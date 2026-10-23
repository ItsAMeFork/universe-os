"""Silent failures reach shell.log (0.2.25 work): renderer crash, page load failure, resolution change."""
import os, re
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pakket', 'universe-os', 'usr', 'lib', 'universe-os')
web = open(os.path.join(root, 'shell', 'webview.py'), encoding='utf-8').read()
assert "'web-process-crashed'" in web and "'load-failed'" in web
assert 'bridge.log(' in web  # the bridge log is the shell log (stdout, supervisor writes it to shell.log)
displays = open(os.path.join(root, 'universe-displays'), encoding='utf-8').read()
# universe-displays writes its own failures to shell.log (the autostart sends its output to /dev/null).
assert 'def note(' in displays and "note('resolutie niet ingesteld" in displays
assert "note('%s naar" in displays and 'r.returncode' in displays and 'else:\n        note(' in displays
assert "'shell.log'" in displays
# 0.2.26 safety net stays: stopped page processes are logged and reloaded.
assert "'web-process-terminated', _restart_page" in web
print('ok')
