import importlib.util
from pathlib import Path
path = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell/app_planets.py'
spec = importlib.util.spec_from_file_location('app_planets', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
old = [{'id': 'old.desktop'}]
state = module.reconcile(old, None)
assert state['planets'] == []
installed = old + [{'id': 'chrome.desktop'}, {'id': 'universe-wine-test-0.desktop'}]
state = module.reconcile(installed, state)
assert state['planets'] == ['chrome.desktop', 'universe-wine-test-0.desktop']
assert module.reconcile(installed, state) == state
state = module.reconcile(old, state)
assert state['planets'] == []
assert module.reconcile(installed, state)['planets'] == ['chrome.desktop', 'universe-wine-test-0.desktop']
assert module.reconcile(old, {'seen': [[]], 'planets': {}})['planets'] == ['old.desktop']
print('PASS: baseline, install, Wine, persistence, removal, reinstall, malformed saved data')
