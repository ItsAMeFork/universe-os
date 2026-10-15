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


DEFAULT_REGELS = (
    'bank', 'overheid', 'government', 'verzekering', 'insurance',
    'werkgever', 'employer', 'verhuurder', 'landlord',
    'geld', 'money', 'betalen', 'payment', 'contract', 'juridisch', 'legal',
    'gezondheid', 'health', 'baan', 'job', 'salaris', 'belasting',
    'wachtwoord', 'password',
)
SHORT_MAIL = 800


def _clean_regels(lines):
    if isinstance(lines, str):
        lines = lines.splitlines()
    out = []
    seen = set()
    for item in lines or []:
        text = ' '.join(str(item or '').split())
        if not text or len(text) > 80:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= 40:
            break
    return out


def regels_van(data=None):
    data = _read() if data is None else data
    clean = _clean_regels(data.get('regels'))
    return clean or list(DEFAULT_REGELS)


def public(now=None):
    now = time.time() if now is None else float(now)
    data = _read()
    aan = bool(data.get('aan'))
    duur = data.get('duur') if data.get('duur') in DUREN else '30m'
    tot = data.get('tot')
    if aan and tot not in (None, '') and float(tot) <= now:
        aan = False
        data['aan'] = False
        data['duur'] = duur
        data['tot'] = None
        _write(data)
        tot = None
    if aan and duur == 'tot-uit':
        tekst = 'Aan tot je het uitzet. Super+Escape zet het direct uit.'
    elif aan and tot:
        tekst = 'Aan tot %s. Super+Escape zet het direct uit.' % time.strftime('%H:%M', time.localtime(float(tot)))
    else:
        tekst = 'Uit'
    return {'aan': aan, 'duur': duur if aan or duur in DUREN else '30m', 'tot': tot if aan else None,
            'wacht': _wacht_count(), 'tekst': tekst, 'regels': regels_van(data)}


def active(now=None):
    return bool(public(now).get('aan'))


def set_choice(on, duur='30m', now=None):
    now = time.time() if now is None else float(now)
    duur = duur if duur in DUREN else '30m'
    data = _read()
    if not on:
        data.update({'aan': False, 'duur': duur, 'tot': None})
        _write(data)
        return public(now)
    seconds = DUREN[duur]
    tot = None if seconds is None else now + seconds
    data.update({'aan': True, 'duur': duur, 'tot': tot})
    _write(data)
    return public(now)


def set_regels(lines):
    clean = _clean_regels(lines)
    if not clean:
        raise ValueError('Zet minstens één woord of domein op de lijst.')
    data = _read()
    data['regels'] = clean
    _write(data)
    return public()


def known_addresses():
    found = set()
    for item in _read().get('bekenden') or []:
        text = str(item or '').strip().lower()
        if '@' in text and len(text) <= 200:
            found.add(text)
    return found


def remember_addresses(addresses):
    data = _read()
    found = known_addresses()
    for item in addresses or []:
        text = str(item or '').strip().lower()
        if '@' in text and len(text) <= 200:
            found.add(text)
    data['bekenden'] = sorted(found)[:200]
    _write(data)
    return data['bekenden']


def mail_decision(recipients, subject, body, bijlagen=0, vlag=False, now=None):
    """vraag, automatisch, or wacht, plus the reasons a message stays important."""
    recipients = [str(item or '').strip() for item in (recipients or []) if str(item or '').strip()]
    reasons = []
    if vlag:
        reasons.append('gemarkeerd als belangrijk')
    if len(recipients) > 3:
        reasons.append('meer dan 3 ontvangers')
    try:
        attached = int(bijlagen or 0)
    except (TypeError, ValueError):
        attached = 1 if bijlagen else 0
    if attached > 0:
        reasons.append('bijlage')
    if len(str(body or '')) > SHORT_MAIL:
        reasons.append('lang bericht')
    known = known_addresses()
    if any(addr.lower() not in known for addr in recipients):
        reasons.append('nieuwe ontvanger')
    blob = '\n'.join([str(subject or ''), str(body or '')] + recipients).lower()
    for rule in regels_van():
        if rule.lower() in blob:
            reasons.append(rule)
            break
    if not active(now):
        return 'vraag', reasons
    if reasons:
        return 'wacht', reasons
    return 'automatisch', []


def recent_mail_ok(now=None, window=180):
    """True when a send was just approved, so a following browser click may press Send."""
    import brein
    now = time.time() if now is None else float(now)
    for row in brein.list_acties(limit=8):
        if row.get('hulpmiddel') == 'mail_send' and row.get('status') in ('automatisch', 'goedgekeurd'):
            if now - float(row.get('op') or 0) <= window:
                return True
    return False


def stop(now=None):
    return set_choice(False, _read().get('duur') or '30m', now)


def sensitive(title, text):
    blob = '%s\n%s' % (title or '', text or '')
    return bool(_WACHT.search(blob))


def decide(title, text, now=None):
    """vraag, automatisch, or wacht.

    Away mode still defers anything sensitive. God, when the user is here, says
    yes to ordinary work and still asks for sending, paying, deleting and passwords.
    """
    import modes
    if active(now):
        if sensitive(title, text):
            return 'wacht'
        return 'automatisch'
    if modes.god() and not modes.stops(title, text):
        return 'automatisch'
    return 'vraag'


def record(title, text, status):
    import brein
    summary = str(title or 'Actie')[:180]
    detail = str(text or '')[:400]
    if re.search(r'wachtwoord|password|pin', detail, re.I):
        detail = 'Tekst niet opgeslagen.'
    return brein.log_actie('auto', summary, status, detail)
