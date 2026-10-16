"""A locked keyring never blocks starting the AI (16 Oct: after a restart the AI waited on an unlock window)."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='ai-config-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='ai-home-')
sys.path.insert(0, str(ROOT / 'pakket/universe-os/usr/lib/universe-os/claude'))
import ai_provider  # noqa: E402

memory = ai_provider.MemoryKeyring()
ai_provider.set_store(memory)
ai_provider.set_key('claude', 'sk-test-sleutel')
# With a test store the lock cannot be checked: the key is read as before.
assert ai_provider.keyring_locked() is None
assert ai_provider.key_for('claude') == 'sk-test-sleutel'
# Locked: no key and, above all, no call to the keyring (that would open the unlock window and wait).
calls = []
real_get = memory.get_password
memory.get_password = lambda *a: calls.append(a) or real_get(*a)
ai_provider.keyring_locked = lambda: True
assert ai_provider.key_for('claude') == ''
assert calls == []
print('sleutelbos op slot: starten wacht niet op het ontgrendelvenster')
