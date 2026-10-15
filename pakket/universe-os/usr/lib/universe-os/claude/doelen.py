"""Goals on the task board. Background work stays inside the confirmation gate.

Payments, deleting, passwords and important mail are never started from here.
The next safe step is prepared for the panel; the buddy does not press Enter.
"""
import re
import time

import brein
import kast

_WACHT = re.compile(
    r'(betalen|betaal|betaling|payment|purchase|aankoop|checkout|\bkopen\b|'
    r'verwijder|delete|\bwissen\b|prullenbak|'
    r'versturen|verstuur|verzend|verzenden|\bsturen\b|\bstuur\b|\bsend\b|'
    r'wachtwoord|password|\bpin\b|'
    r'belangrijke mail|belangrijk mail)',
    re.I)
_STEPS = (
    ('Begrijpen', 'planner'),
    ('Opdelen', 'planner'),
    ('Doen', 'hoofd'),
    ('Nakijken', 'reviewer'),
)


def background():
    return bool(kast.load()['doelen'].get('achtergrond'))


def set_background(on):
    kast.update('doelen', achtergrond=bool(on))
    return public()


def sensitive(text):
    return bool(_WACHT.search(str(text or '')))


def _steps_for(titel):
    lines = [line.strip() for line in str(titel or '').splitlines() if line.strip()]
    if len(lines) > 1:
        return [(line[:120], 'hoofd') for line in lines[:8]]
    return list(_STEPS)


def add(titel):
    raw = str(titel or '').strip()
    if not raw:
        raise ValueError('Een doel heeft een naam nodig.')
    steps = _steps_for(raw)
    titel = ' '.join(raw.split())[:200]
    now = time.time()
    with brein.connect() as db:
        cur = db.execute(
            'INSERT INTO taken(titel, soort, start, eind, status) VALUES (?, ?, ?, NULL, ?)',
            (titel[:160], 'doel', now, 'bezig'))
        taak_id = cur.lastrowid
        for index, (name, agent) in enumerate(steps):
            db.execute(
                '''INSERT INTO stappen(taak_id, titel, agent, status, volgorde, op)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (taak_id, name, agent, 'todo', index, now))
        goal = db.execute(
            'INSERT INTO doelen(titel, status, taak_id, op) VALUES (?, ?, ?, ?)',
            (titel, 'bezig', taak_id, now))
        goal_id = goal.lastrowid
    return {'id': goal_id, 'taak_id': taak_id, 'titel': titel}


def _open(db):
    return db.execute(
        "SELECT * FROM doelen WHERE status = 'bezig' ORDER BY op ASC, id ASC LIMIT 1").fetchone()


def waiting():
    """A goal whose next step must stay a question. None when there is nothing to wait for."""
    if not background():
        return None
    with brein.connect() as db:
        goal = _open(db)
        if not goal:
            return None
        step = db.execute(
            "SELECT * FROM stappen WHERE taak_id = ? AND status = 'todo' ORDER BY volgorde, id LIMIT 1",
            (goal['taak_id'],)).fetchone()
    if not step:
        return None
    if sensitive(goal['titel']) or sensitive(step['titel']):
        return {'id': goal['id'], 'titel': goal['titel'], 'stap': step['titel']}
    return None


def prompt_for(titel, stap):
    return (
        'Doel: %s\nStap: %s\n'
        'Werk alleen deze stap, als subagent, niet als zwerm. '
        'Betalen, wissen, wachtwoorden en belangrijke mail blijven een vraag via de universe-hulpmiddelen. '
        'Zet nooit een vlag die de toestemming overslaat.'
    ) % (titel, stap)


def peek():
    """The open step, without changing the board."""
    if not background():
        return None
    with brein.connect() as db:
        goal = _open(db)
        if not goal:
            return None
        step = db.execute(
            """SELECT * FROM stappen WHERE taak_id = ? AND status IN ('bezig', 'todo')
               ORDER BY CASE status WHEN 'bezig' THEN 0 ELSE 1 END, volgorde, id LIMIT 1""",
            (goal['taak_id'],)).fetchone()
        if not step:
            return None
        titel, stap = goal['titel'], step['titel']
    if sensitive(titel) or sensitive(stap):
        return {'wacht': True, 'titel': titel, 'stap': stap,
                'tekst': 'Doel %s wacht op een vraag: %s.' % (titel, stap)}
    return {'wacht': False, 'titel': titel, 'stap': stap, 'prompt': prompt_for(titel, stap)}


def tick():
    """Move one safe step to bezig. Sensitive steps stay todo."""
    if not background():
        return {'starten': False, 'reden': 'uit'}
    with brein.connect() as db:
        goal = _open(db)
        if not goal:
            return {'starten': False, 'reden': 'geen'}
        titel = goal['titel']
        taak_id = goal['taak_id']
        busy = db.execute(
            "SELECT * FROM stappen WHERE taak_id = ? AND status = 'bezig' ORDER BY volgorde LIMIT 1",
            (taak_id,)).fetchone()
        if busy:
            return {'starten': False, 'reden': 'bezig', 'prompt': prompt_for(titel, busy['titel']),
                    'taak_id': taak_id, 'stap': busy['titel'], 'titel': titel}
        step = db.execute(
            "SELECT * FROM stappen WHERE taak_id = ? AND status = 'todo' ORDER BY volgorde, id LIMIT 1",
            (taak_id,)).fetchone()
        if not step:
            db.execute("UPDATE doelen SET status = 'klaar' WHERE id = ?", (goal['id'],))
            db.execute("UPDATE taken SET status = 'klaar', eind = ? WHERE id = ?", (time.time(), taak_id))
            return {'starten': False, 'reden': 'klaar'}
        stap = step['titel']
        if sensitive(titel) or sensitive(stap):
            return {'starten': False, 'wacht': True, 'reden': 'Dit blijft een vraag.',
                    'taak_id': taak_id, 'stap': stap, 'titel': titel}
        db.execute("UPDATE stappen SET status = 'bezig', op = ? WHERE id = ?", (time.time(), step['id']))
    return {'starten': True, 'reden': 'stap', 'prompt': prompt_for(titel, stap),
            'taak_id': taak_id, 'stap': stap, 'titel': titel}


def line():
    info = peek()
    if not info:
        return ''
    if info.get('wacht'):
        return '\n%s Betalen, wissen, wachtwoorden en belangrijke mail blijven een vraag.\n' % info['tekst']
    return '\nOpen doel op het taakbord.\n%s\n' % info['prompt']


def lijst():
    with brein.connect() as db:
        rows = db.execute('SELECT * FROM doelen ORDER BY op DESC, id DESC LIMIT 20').fetchall()
    return [{'id': row['id'], 'titel': row['titel'], 'status': row['status'], 'taak_id': row['taak_id']} for row in rows]


def public():
    return {
        'achtergrond': background(),
        'tekst': 'Achtergrond aan' if background() else 'Alleen op het bord',
        'lijst': lijst(),
        'uitleg': ('Een doel wordt stappen op het taakbord. Op de achtergrond pakt de volgende sessie '
                   'één veilige stap. Betalen, wissen, wachtwoorden en belangrijke mail blijven een vraag.'),
    }
