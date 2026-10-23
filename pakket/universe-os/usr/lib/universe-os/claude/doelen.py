"""Goals the assistant may pursue in the background, from the Brein.

Routine steps become a note in the Brein. Paying, deleting, passwords and
important mail always stay a question: the on-screen dialog, even when
auto-accept would let an ordinary step through. This module never sends mail,
pays, or deletes a file.
"""
import json
import os
import re
import threading
import time

import auto_accept
import brein

_LOCK = threading.Lock()
_PAY = re.compile(
    r'(betalen|betaal|betaling|payment|purchase|aankoop|checkout|\bkopen\b)', re.I)
_DELETE = re.compile(r'(verwijder|delete|\bwissen\b|prullenbak)', re.I)
_SECRET = re.compile(r'(wachtwoord|password|\bpin\b)', re.I)
_SEND = re.compile(
    r'(versturen|verstuur|verzend|verzenden|\bsturen\b|\bstuur\b|\bsend\b)', re.I)
_MAIL = re.compile(r'\b(mail|e-mail|email)\b', re.I)
_COPY = {
    'wachtwoord': (
        'Dit doel raakt een wachtwoord',
        'Een wachtwoord blijft een vraag, ook als automatisch toestaan aan staat. '
        'De tekst wordt niet bewaard. Dit doel vult het zelf niet in.',
    ),
    'betalen': (
        'Dit doel wil betalen',
        'Betalen blijft een vraag, ook als automatisch toestaan aan staat. '
        'Dit doel betaalt zelf niet.\n\n%s',
    ),
    'wissen': (
        'Dit doel wil wissen',
        'Wissen blijft een vraag, ook als automatisch toestaan aan staat. '
        'Dit doel wist zelf niets.\n\n%s',
    ),
    'mail': (
        'Dit doel wil mail versturen',
        'Belangrijke mail en versturen blijven een vraag, ook als automatisch toestaan aan staat. '
        'Dit doel verstuurt zelf niets.\n\n%s',
    ),
}
UITLEG = (
    'De assistent pakt veilige stappen op de achtergrond. Betalen, wissen, wachtwoorden en '
    'belangrijke mail blijven een vraag, ook als automatisch toestaan aan staat.'
)


def _path():
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    folder = os.path.join(base, 'universe-os')
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return os.path.join(folder, 'doelen.json')


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


def background():
    return bool(_read().get('achtergrond'))


def set_background(on):
    data = _read()
    data['achtergrond'] = bool(on)
    _write(data)
    return public()


def important_mail(text):
    low = str(text or '').lower()
    if 'belangrijke mail' in low or 'belangrijk mail' in low or 'important mail' in low:
        return True
    if not _MAIL.search(low):
        return False
    for rule in auto_accept.regels_van():
        if rule.lower() in low:
            return True
    return False


def gate(text):
    """betalen, wissen, wachtwoord, mail, or '' when the step may run."""
    raw = str(text or '')
    if _SECRET.search(raw):
        return 'wachtwoord'
    if _PAY.search(raw):
        return 'betalen'
    if _DELETE.search(raw):
        return 'wissen'
    if _SEND.search(raw) or important_mail(raw):
        return 'mail'
    return ''


def sensitive(text):
    return bool(gate(text))


def _steps_for(titel):
    lines = [line.strip() for line in str(titel or '').splitlines() if line.strip()]
    if not lines:
        raise ValueError('Een doel heeft een naam nodig.')
    return [{'titel': line[:160], 'status': 'todo'} for line in lines[:8]]


def _load_steps(raw):
    try:
        steps = json.loads(raw or '[]')
    except ValueError:
        steps = []
    if not isinstance(steps, list):
        return []
    clean = []
    for step in steps:
        if isinstance(step, dict) and step.get('titel'):
            clean.append({'titel': str(step['titel'])[:160], 'status': str(step.get('status') or 'todo')})
    return clean


def _question(kind, step):
    title, text = _COPY[kind]
    if kind == 'wachtwoord':
        return title, text
    return title, text % str(step or '')[:300]


def _summary(kind, step):
    if kind == 'wachtwoord':
        return 'Wachtwoord'
    return str(step or 'Doel')[:180]


def add(titel):
    steps = _steps_for(titel)
    name = ' '.join(str(titel or '').split())[:200]
    now = time.time()
    with brein.connect() as db:
        db.execute(
            'INSERT INTO doelen(titel, status, stappen, reden, gevraagd, op) VALUES (?, ?, ?, ?, ?, ?)',
            (name, 'bezig', json.dumps(steps, ensure_ascii=False), '', 0, now))
    return public()


def _open(db):
    return db.execute(
        "SELECT * FROM doelen WHERE status = 'bezig' ORDER BY op ASC, id ASC LIMIT 1").fetchone()


def _save(db, row_id, status, steps, reden, gevraagd):
    db.execute(
        'UPDATE doelen SET status = ?, stappen = ?, reden = ?, gevraagd = ? WHERE id = ?',
        (status, json.dumps(steps, ensure_ascii=False), str(reden or '')[:400], float(gevraagd or 0), int(row_id)))


def opnieuw(goal_id):
    with brein.connect() as db:
        row = db.execute('SELECT * FROM doelen WHERE id = ?', (int(goal_id),)).fetchone()
        if not row:
            raise ValueError('Dit doel staat er niet.')
        steps = _load_steps(row['stappen'])
        for step in steps:
            if step['status'] == 'todo':
                break
        else:
            raise ValueError('Dit doel heeft geen open stap.')
        _save(db, row['id'], 'bezig', steps, '', 0)
    return public()


def _routine(goal_titel, step):
    note = 'Doel: %s. Stap gedaan: %s.' % (str(goal_titel or '')[:80], str(step or '')[:120])
    brein.remember(note, 'notitie', 'doel')
    brein.log_actie('doel', str(step or 'Stap')[:180], 'uitgevoerd', 'Notitie in het brein.')


def tick(confirmer=None, now=None):
    """One step. Sensitive steps call confirmer and are never carried out here."""
    if not background():
        return {'starten': False, 'reden': 'uit'}
    if not _LOCK.acquire(blocking=False):
        return {'starten': False, 'reden': 'bezig'}
    try:
        return _tick(confirmer, now)
    finally:
        _LOCK.release()


def _tick(confirmer, now):
    now = time.time() if now is None else float(now)
    with brein.connect() as db:
        row = _open(db)
        if not row:
            waiting = db.execute("SELECT id FROM doelen WHERE status = 'wacht' LIMIT 1").fetchone()
            if waiting:
                return {'starten': False, 'reden': 'wacht', 'wacht': True}
            return {'starten': False, 'reden': 'geen'}
        goal_id = row['id']
        goal_titel = row['titel']
        steps = _load_steps(row['stappen'])
        index = next((i for i, step in enumerate(steps) if step['status'] == 'todo'), None)
        if index is None:
            _save(db, goal_id, 'klaar', steps, row['reden'], 0)
            return {'starten': False, 'reden': 'klaar'}
        step = steps[index]['titel']
        kind = gate(step)
    if kind:
        import confirm
        if confirm.busy():
            return {'starten': False, 'reden': 'bezig', 'wacht': True}
        title, text = _question(kind, step)
        if confirmer is None:
            with brein.connect() as db:
                _save(db, goal_id, 'wacht', steps, 'Dit blijft een vraag.', now)
            return {'starten': False, 'wacht': True, 'reden': 'wacht', 'stap': _summary(kind, step)}
        allowed = bool(confirmer(title, text))
        if not allowed:
            with brein.connect() as db:
                _save(db, goal_id, 'wacht', steps, 'Geweigerd. De stap is niet gedaan.', now)
            brein.log_actie('doel', _summary(kind, step), 'geweigerd', 'Niet uitgevoerd vanuit het doel.')
            return {'starten': False, 'wacht': True, 'reden': 'wacht', 'stap': _summary(kind, step),
                    'titel': title}
        steps[index]['status'] = 'goedgekeurd'
        more = any(item['status'] == 'todo' for item in steps)
        with brein.connect() as db:
            _save(db, goal_id, 'bezig' if more else 'klaar', steps,
                  'Goedgekeurd. Niet uitgevoerd vanuit het doel.', 0)
        brein.log_actie('doel', _summary(kind, step), 'goedgekeurd', 'Niet uitgevoerd vanuit het doel.')
        return {'starten': False, 'wacht': True, 'goedgekeurd': True, 'reden': 'goedgekeurd',
                'stap': _summary(kind, step), 'titel': title}
    _routine(goal_titel, step)
    steps[index]['status'] = 'klaar'
    more = any(item['status'] == 'todo' for item in steps)
    with brein.connect() as db:
        _save(db, goal_id, 'bezig' if more else 'klaar', steps,
              '' if more else 'Opgeschreven in het brein.', 0)
    return {'starten': True, 'reden': 'stap', 'stap': step}


def lijst():
    with brein.connect() as db:
        rows = db.execute('SELECT * FROM doelen ORDER BY op DESC, id DESC LIMIT 20').fetchall()
    out = []
    for row in rows:
        steps = _load_steps(row['stappen'])
        current = next((step['titel'] for step in steps if step['status'] == 'todo'), '')
        out.append({
            'id': row['id'], 'titel': row['titel'], 'status': row['status'],
            'stap': current, 'reden': row['reden'],
        })
    return out


def public():
    on = background()
    return {
        'achtergrond': on,
        'tekst': 'Aan' if on else 'Uit',
        'uitleg': UITLEG,
        'lijst': lijst(),
    }
