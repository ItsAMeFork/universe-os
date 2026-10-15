"""Privacy Ghost mode. Off until the user turns it on.

This is not the suggestion limiter (quiet hours, a few hints a day). That one
lives on another branch. Here, on means less written down and less cloud:
no new brain timeline, action or token rows, no file-content index, short
shell failure lines only, no automatic update check at login, and cloud
assistants do not start. The local model still may. Turning it off restores
the previous behaviour. The choice sits in the user's own config, mode 0600.
"""
import json
import os

_KEEP = (
    ('mislukt', 'mislukt'),
    ('fout', 'fout'),
    ('error', 'fout'),
    ('ondersteunt', 'niet ondersteund'),
    ('niet geladen', 'niet beschikbaar'),
    ('niet verstuurd', 'niet beschikbaar'),
    ('niet beschikbaar', 'niet beschikbaar'),
)
_UITLEG_UIT = (
    'Uit. Logboek, bestandsindex, updatecontrole en wolk-assistenten werken zoals altijd.'
)
_UITLEG_AAN = (
    'Aan. Minder logboek: geen tijdlijn van wat je opent, geen tokenlog, geen bestandsindex '
    'en kortere shell-regels. Geen automatische updatecontrole. Wolk-assistenten starten niet; '
    'het lokale model blijft. Handmatig bijwerken kan nog via Software en updates.'
)


def _path():
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'), '.config')
    folder = os.path.join(base, 'universe-os')
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return os.path.join(folder, 'ghost-modus.json')


def enabled():
    """True only when the file says aan is the boolean true. Missing or broken means off."""
    try:
        with open(_path(), encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get('aan') is True


def _as_bool(value):
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'aan', 'ja')
    return bool(value)


def set_enabled(on):
    path = _path()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump({'aan': _as_bool(on)}, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    return public()


def public():
    on = enabled()
    return {'aan': on, 'tekst': 'Aan' if on else 'Uit', 'uitleg': _UITLEG_AAN if on else _UITLEG_UIT}


def shell_line(text):
    """Full line when Ghost is off. On: drop chatter, and keep a short label for failures."""
    text = '' if text is None else str(text)
    if not enabled():
        return text
    low = text.lower()
    if low.startswith('ui '):
        return 'fout'
    for needle, label in _KEEP:
        if needle in low:
            return label
    return None


def cloud_refusal(provider):
    """None when this assistant may start. A Dutch sentence when Ghost blocks a cloud one."""
    if not enabled() or str(provider or '') == 'ollama':
        return None
    return (
        'Ghost-modus staat aan. Wolk-assistenten starten niet. '
        'Kies Op deze computer, of zet Ghost-modus uit op Beveiliging.'
    )
