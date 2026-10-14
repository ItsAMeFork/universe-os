"""Away mode: accept ordinary confirmations for a limited time.

Off until the user turns it on. Payments, deletion, sending, passwords and
system changes are never accepted here; they wait in the Brein until the user
is back. Super+Escape calls stop().
"""
import json
import os
import re
import time

DUREN = {'30m': 30 * 60, '1u': 60 * 60, '2u': 2 * 60 * 60, 'tot-uit': None}
_WACHT = re.compile(
    r'(betalen|betaal|betaling|payment|purchase|aankoop|checkout|\bkopen\b|'
    r'verwijder|delete|\bwissen\b|prullenbak|'
    r'versturen|verstuur|verzend|verzenden|\bsturen\b|\bstuur\b|\bsend\b|overschrijf|'
    r'wachtwoord|password|\bpin\b|gevoelig veld|'
    r'beveiliging|firewall|\bsudo\b|pkexec|scherm bedienen)',
    re.I)


def _path():
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    folder = os.path.join(base, 'universe-os')
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return os.path.join(folder, 'auto-accept.json')


def _read():
    try:
        with open(_path(), encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(data):
    path = _path()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _wacht_count():
    try:
        import brein
        return len(brein.list_acties(limit=80, status='wacht'))
    except Exception:
        return 0


def public(now=None):
    now = time.time() if now is None else float(now)
    data = _read()
    aan = bool(data.get('aan'))
    duur = data.get('duur') if data.get('duur') in DUREN else '30m'
    tot = data.get('tot')
    if aan and tot not in (None, '') and float(tot) <= now:
        aan = False
        _write({'aan': False, 'duur': duur, 'tot': None})
        tot = None
    if aan and duur == 'tot-uit':
        tekst = 'Aan tot je het uitzet. Super+Escape zet het direct uit.'
    elif aan and tot:
        tekst = 'Aan tot %s. Super+Escape zet het direct uit.' % time.strftime('%H:%M', time.localtime(float(tot)))
    else:
        tekst = 'Uit'
    return {'aan': aan, 'duur': duur if aan or duur in DUREN else '30m', 'tot': tot if aan else None,
            'wacht': _wacht_count(), 'tekst': tekst}


def active(now=None):
    return bool(public(now).get('aan'))


def set_choice(on, duur='30m', now=None):
    now = time.time() if now is None else float(now)
    duur = duur if duur in DUREN else '30m'
    if not on:
        _write({'aan': False, 'duur': duur, 'tot': None})
        return public(now)
    seconds = DUREN[duur]
    tot = None if seconds is None else now + seconds
    _write({'aan': True, 'duur': duur, 'tot': tot})
    return public(now)


def stop(now=None):
    return set_choice(False, _read().get('duur') or '30m', now)


def sensitive(title, text):
    blob = '%s\n%s' % (title or '', text or '')
    return bool(_WACHT.search(blob))


def decide(title, text, now=None):
    """vraag, automatisch, or wacht. Sensitive work never becomes automatisch."""
    if not active(now):
        return 'vraag'
    if sensitive(title, text):
        return 'wacht'
    return 'automatisch'


def record(title, text, status):
    import brein
    summary = str(title or 'Actie')[:180]
    detail = str(text or '')[:400]
    if re.search(r'wachtwoord|password|pin', detail, re.I):
        detail = 'Tekst niet opgeslagen.'
    return brein.log_actie('auto', summary, status, detail)
