import importlib.util
import json
import tempfile
from pathlib import Path

path = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell/chrome_status.py'
spec = importlib.util.spec_from_file_location('chrome_status', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as folder:
    status = Path(folder) / 'chrome.json'
    assert module.read(False, status)['state'] == 'pending'
    for state in ('offline', 'installing', 'installed', 'error'):
        status.write_text(json.dumps({'state': state, 'message': 'Testbericht'}), encoding='utf-8')
        result = module.read(False, status)
        assert not result['available']
        assert result['state'] == ('error' if state == 'installed' else state)
        assert module.read(True, status)['state'] == 'installed'
    for content in ('{', '[]', '{"state":"unknown"}'):
        status.write_text(content, encoding='utf-8')
        assert module.read(False, status)['state'] == 'error'
print('PASS: missing/download/error/installed states, malformed file, desktop presence authoritative')
