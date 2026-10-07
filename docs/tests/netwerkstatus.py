"""Run with Python 3; no NetworkManager installation required."""
import importlib.util
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell/network_status.py'
spec = importlib.util.spec_from_file_location('network_status', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for devices, radio, connectivity, reason in [
    ('loopback:connected (externally):lo', 'enabled', 'unknown', 'no-device'),
    ('wifi:unavailable:', 'disabled', 'none', 'wifi-off'),
    ('wifi:disconnected:', 'enabled', 'none', 'disconnected'),
    ('ethernet:unavailable:', 'enabled', 'none', 'device-unavailable'),
    ('ethernet:unavailable:\nwifi-p2p:disconnected:\nwireguard:connected:wg0\ndummy:connected:dummy0',
     'enabled', 'unknown', 'device-unavailable'),
    ('wifi-p2p:disconnected:\nwireguard:connected:wg0\ndummy:disconnected:',
     'enabled', 'unknown', 'no-device'),
    ('wifi:connecting (prepare):Thuis', 'enabled', 'none', 'connecting'),
    ('ethernet:connecting:', 'enabled', 'unknown', 'connecting'),
    ('wifi:connecting (configuring):Thuis\nethernet:connected:Kabel', 'enabled', 'full', 'full'),
    ('ethernet:unmanaged:', 'enabled', 'none', 'unmanaged'),
    *[('wifi:connected:Naam:met:punt', 'enabled', value, value)
      for value in ('full', 'portal', 'limited', 'none', 'unknown')],
    ('wifi:unavailable:\nethernet:connected:Kabel', 'disabled', 'full', 'full'),
]:
    state = module.classify(devices, radio, connectivity)
    assert state['reason'] == reason, state
    if devices.startswith('wifi:connected:'):
        assert state['name'] == 'Naam:met:punt'
with patch.object(module, 'query', side_effect=RuntimeError('offline')):
    assert module.status()['state'] == 'unavailable'
print('PASS: network reasons, unknown connectivity, colon in name, wired precedence, manager failure')
