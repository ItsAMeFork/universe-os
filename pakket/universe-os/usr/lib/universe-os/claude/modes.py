"""Zen and God. Both stay off until the user turns them on in Controlecentrum or the panel.

Zen is only the desktop: no taskbar and no planets. God lets the assistant finish
ordinary steps without a dialog. Sending, paying, deleting and passwords still
ask on screen. The assistant cannot turn God on; that key is a security setting.
"""
import json
import os
import re

# Narrower than away-mode. Screen control, sudo and firewall are ordinary under God.
_STOP = re.compile(
    r'(betalen|betaal|betaling|payment|purchase|aankoop|checkout|\bkopen\b|'
    r'verwijder|delete|\bwissen\b|prullenbak|'
    r'versturen|verstuur|verzend|verzenden|\bsturen\b|\bstuur\b|\bsend\b|'
    r'wachtwoord|password|\bpin\b|gevoelig veld)',
    re.I)


def _path():
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    return os.path.join(base, 'universe-os', 'settings.json')


def _read():
    try:
        with open(_path(), encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def zen():
    return _read().get('zen') is True


def god():
    return _read().get('god') is True


def stops(title, text):
    """True when God must still show the dialog: send, pay, delete or password."""
    blob = '%s\n%s' % (title or '', text or '')
    return bool(_STOP.search(blob))
