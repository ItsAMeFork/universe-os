"""Damaged or empty user config files fall back to defaults instead of crashing the shell."""
import os
import sys
import tempfile
from pathlib import Path

shell = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell'
sys.path.insert(0, str(shell))
import config  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    os.environ['XDG_CONFIG_HOME'] = d
    own = Path(config.user_dir())
    defaults = config.settings()
    for content in ('', '{kapot', '\xff\xfe', 'null', '[1, 2]', '"tekst"', '42'):
        for name in ('settings.json', 'shortcuts.json', 'layout.json', 'world.json', 'keyboard.json'):
            (own / name).write_bytes(content.encode('latin-1'))
        assert config.settings() == defaults, content
        assert isinstance(config.shortcuts(), list), content
        assert config.layout() == config.DEFAULT_LAYOUT, content
        assert isinstance(config.world()['planets'], list), content
        assert config.keyboard()['source'] == 'system', content
        config.set_setting('zen', True)
        assert config.settings()['zen'] is True, content
        assert config.read_json(str(own / 'ontbreekt.json'), {'a': 1}) == {'a': 1}
print('PASS: empty, corrupt and wrong-shape config files fall back to defaults')
