import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
path = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell/update_channel.py'
spec = importlib.util.spec_from_file_location('update_channel', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with patch.object(module.os.path, 'exists', return_value=False):
    assert module.get() == {'active': False}
with patch.object(module.os.path, 'exists', side_effect=lambda p: p == module.BASE):
    assert module.get()['channel'] == 'stable'
with patch.object(module.os.path, 'exists', return_value=True):
    assert module.get()['channel'] == 'test'
    for code in (0, 126, 127, 1):
        with patch.object(module.subprocess, 'run', return_value=SimpleNamespace(returncode=code, stdout='ok', stderr='Testfout')):
            if code in (0, 126):
                result=module.set_channel({'channel': 'test'})
                assert result['changed'] == (code == 0)
            else:
                try:
                    module.set_channel({'channel': 'test'})
                except (PermissionError, RuntimeError):
                    pass
                else:
                    raise AssertionError(code)
    with patch.object(module.subprocess, 'run') as command:
        try: module.set_channel({'channel': 'invalid'})
        except ValueError: pass
        else: raise AssertionError('invalid channel accepted')
        command.assert_not_called()
print('PASS: inactive/stable/test, success, cancellation126, denied127, helper failure, invalid channel')
