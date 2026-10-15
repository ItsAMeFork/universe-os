"""Local switches for the premade desk features. One file, nothing leaves the computer."""
import json
import os

DEFAULTS = {
    'scherm': {'aan': False, 'pauze': False, 'dagen': 7, 'elke': 60, 'uitsluiten': []},
    'stem': {'aan': False},
    'briefing': {'aan': True, 'gezien': ''},
    'ghost': {
        'aan': False, 'stil_van': '22:00', 'stil_tot': '07:30',
        'max_per_dag': 3, 'minuten': 90, 'dag': '', 'aantal': 0, 'laatst': 0.0,
    },
    'doelen': {'achtergrond': False},
}


def path():
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    folder = os.path.join(base, 'universe-os')
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return os.path.join(folder, 'leven.json')


def load():
    try:
        with open(path(), encoding='utf-8') as handle:
            raw = json.load(handle)
    except (OSError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    out = {}
    for key, default in DEFAULTS.items():
        cur = dict(default)
        got = raw.get(key)
        if isinstance(got, dict):
            for name in default:
                if name in got:
                    cur[name] = got[name]
        out[key] = cur
    extra = out['scherm'].get('uitsluiten')
    if not isinstance(extra, list):
        extra = []
    out['scherm']['uitsluiten'] = [str(item).strip()[:40] for item in extra if str(item).strip()][:40]
    return out


def save(data):
    dest = path()
    tmp = dest + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, dest)


def update(name, **fields):
    if name not in DEFAULTS:
        raise ValueError('Onbekend onderdeel')
    data = load()
    row = data[name]
    allowed = set(DEFAULTS[name])
    for key, value in fields.items():
        if key in allowed:
            row[key] = value
    data[name] = row
    save(data)
    return load()[name]
