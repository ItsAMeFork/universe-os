"""Universe OS settings: system defaults (branding) + per-user settings, world layout and shortcuts."""
import copy
import json
import os

SYSTEM_DIR = '/usr/share/universe-os'
BRANDING = os.path.join(SYSTEM_DIR, 'universe.json')
DEFAULT_SHORTCUTS = os.path.join(SYSTEM_DIR, 'shortcuts.json')


def user_dir():
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'), '.config')
    path = os.path.join(base, 'universe-os')
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path


def read_json(path, fallback):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return copy.deepcopy(fallback)


def write_json(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def branding():
    return read_json(BRANDING, {'name': 'Universe OS', 'colors': {}, 'planets': [], 'defaults': {}})


SETTING_KEYS = {
    'animations': ('full', 'reduced', 'off'),
    'travel': (True, False),
    'uiScale': range(50, 301),
    'textScale': range(75, 251),
    'lockMinutes': range(0, 241),
    'screenOffMinutes': range(0, 241),
    'naturalScroll': (True, False),
    'tapToClick': (True, False),
    'pointerSpeed': [x / 10 for x in range(-10, 11)],
    'displayScales': None,  # dict output -> scale, validated separately
}


def settings():
    base = branding().get('defaults', {})
    merged = {'animations': 'full', 'travel': True, 'uiScale': 100, 'textScale': 100, 'lockMinutes': 10,
              'screenOffMinutes': 15, 'naturalScroll': False, 'tapToClick': True, 'pointerSpeed': 0.0, 'displayScales': {}}
    merged.update(base)
    merged.update(read_json(os.path.join(user_dir(), 'settings.json'), {}))
    return merged


def set_setting(key, value):
    if key not in SETTING_KEYS:
        raise ValueError('Onbekende instelling: %s' % key)
    allowed = SETTING_KEYS[key]
    if key == 'displayScales':
        if not isinstance(value, dict) or not all(isinstance(v, (int, float)) and 0.5 <= v <= 3 for v in value.values()):
            raise ValueError('Ongeldige schaal')
    elif key == 'pointerSpeed':
        value = max(-1.0, min(1.0, float(value)))
    elif value not in allowed:
        raise ValueError('Ongeldige waarde voor %s' % key)
    path = os.path.join(user_dir(), 'settings.json')
    data = read_json(path, {})
    data[key] = value
    write_json(path, data)


def world():
    """World layout: branding, optionally overridden per user (~/.config/universe-os/world.json)."""
    data = branding()
    own = read_json(os.path.join(user_dir(), 'world.json'), None)
    if isinstance(own, dict):
        if isinstance(own.get('planets'), list):
            by_id = {p.get('id'): p for p in own['planets'] if isinstance(p, dict)}
            data['planets'] = [dict(p, **by_id.get(p['id'], {})) for p in data.get('planets', [])]
        if isinstance(own.get('colors'), dict):
            data['colors'] = dict(data.get('colors', {}), **own['colors'])
    return {'name': data.get('name', 'Universe OS'), 'version': data.get('version', ''), 'colors': data.get('colors', {}), 'planets': data.get('planets', [])}


def shortcuts():
    defaults = read_json(DEFAULT_SHORTCUTS, [])
    own = read_json(os.path.join(user_dir(), 'shortcuts.json'), {})
    result = []
    for item in defaults:
        item = dict(item)
        if item['id'] in own:
            item['key'] = own[item['id']]
        result.append(item)
    return result


def set_shortcuts(changes):
    defaults = {s['id']: s for s in read_json(DEFAULT_SHORTCUTS, [])}
    own = read_json(os.path.join(user_dir(), 'shortcuts.json'), {})
    for sid, key in changes.items():
        if sid not in defaults:
            raise ValueError('Onbekende sneltoets: %s' % sid)
        if defaults[sid].get('fixed'):
            raise ValueError('Deze sneltoets is vast: %s' % defaults[sid]['name'])
        key = str(key).strip()
        if not key or any(c in key for c in '<>"&\''):
            raise ValueError('Ongeldige toetscombinatie')
        if key == defaults[sid]['key']:
            own.pop(sid, None)
        else:
            own[sid] = key
    merged = {s['id']: own.get(s['id'], s['key']) for s in defaults.values()}
    seen = {}
    for sid, key in merged.items():
        if key.lower() in seen:
            raise ValueError('Conflict: %s en %s gebruiken allebei %s' % (defaults[seen[key.lower()]]['name'], defaults[sid]['name'], key))
        seen[key.lower()] = sid
    write_json(os.path.join(user_dir(), 'shortcuts.json'), own)


def keyboard():
    """Keyboard layout for this user; falls back to the system layout (/etc/default/keyboard)."""
    own = read_json(os.path.join(user_dir(), 'keyboard.json'), None)
    if isinstance(own, dict) and own.get('layout'):
        return {'layout': own['layout'], 'variant': own.get('variant', ''), 'source': 'user'}
    layout, variant = 'us', 'intl'
    try:
        with open('/etc/default/keyboard', encoding='utf-8') as f:
            for line in f:
                k, _, v = line.strip().partition('=')
                v = v.strip('"')
                if k == 'XKBLAYOUT' and v:
                    layout = v.split(',')[0]
                elif k == 'XKBVARIANT':
                    variant = v.split(',')[0]
    except OSError:
        pass
    return {'layout': layout, 'variant': variant, 'source': 'system'}


def set_keyboard(layout, variant):
    write_json(os.path.join(user_dir(), 'keyboard.json'), {'layout': layout, 'variant': variant})


def locale():
    path = os.path.join(user_dir(), 'locale.env')
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.startswith('LANG='):
                    return {'lang': line.strip()[5:], 'source': 'user'}
    except OSError:
        pass
    lang = 'nl_NL.UTF-8'
    try:
        with open('/etc/default/locale', encoding='utf-8') as f:
            for line in f:
                if line.startswith('LANG='):
                    lang = line.strip()[5:].strip('"')
    except OSError:
        pass
    return {'lang': lang, 'source': 'system'}


def set_locale(lang):
    language = lang.split('.')[0]
    short = language.split('_')[0]
    with open(os.path.join(user_dir(), 'locale.env'), 'w', encoding='utf-8') as f:
        f.write('LANG=%s\nLANGUAGE=%s:%s\n' % (lang, language, short))
