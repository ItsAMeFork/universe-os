"""Task board and the activity view. Both are filled from the hooks and the action log.

Replay only walks the stored rows. It does not run a tool again.
"""
import json
import os
import time

import brein

STEP_STATUS = ('todo', 'bezig', 'klaar', 'geblokkeerd')
WORKFLOWS = {
    'bouw': (
        ('Plan', 'planner'),
        ('Bouwen', 'hoofd'),
        ('Testen', 'tester'),
        ('Review', 'reviewer'),
    ),
    'onderzoek': (('Onderzoek', 'researcher'),),
    'opruimen': (('Opruimen', 'opruimer'),),
    'mail-ochtend': (('Ochtendmail', 'mail-assistent'),),
}


def workflow_of(text):
    raw = str(text or '').strip().lower()
    token = raw.split()[0] if raw else ''
    token = token.lstrip('/').rstrip('.,:;')
    return token if token in WORKFLOWS else ''


def _task(row):
    return {'id': row['id'], 'titel': row['titel'], 'soort': row['soort'], 'start': row['start'],
            'eind': row['eind'], 'status': row['status'], 'tijd': brein._clock(row['start'])}


def _step(row):
    return {'id': row['id'], 'taak_id': row['taak_id'], 'titel': row['titel'], 'agent': row['agent'],
            'status': row['status'], 'volgorde': row['volgorde']}


def begin(prompt):
    """Closes a leftover open task and starts a new one, with steps when it is a workflow."""
    import patronen
    prompt = str(prompt or '').strip()
    titel = prompt.replace('\n', ' ')[:160] or 'Taak'
    key = workflow_of(prompt)
    soort = key or patronen.classify(prompt)
    now = time.time()
    steps = WORKFLOWS.get(key) or (('Taak', 'hoofd'),)
    with brein.connect() as db:
        db.execute(
            """UPDATE taken SET eind = ?,
               status = CASE WHEN status = 'geblokkeerd' THEN 'geblokkeerd' ELSE 'klaar' END
               WHERE eind IS NULL""",
            (now,))
        cur = db.execute(
            'INSERT INTO taken(titel, soort, start, eind, status) VALUES (?, ?, ?, NULL, ?)',
            (titel, soort, now, 'bezig'))
        taak_id = cur.lastrowid
        for index, (name, agent) in enumerate(steps):
            db.execute(
                '''INSERT INTO stappen(taak_id, titel, agent, status, volgorde, op)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (taak_id, name, agent, 'todo', index, now))
    return taak_id


def _current(db):
    return db.execute('SELECT * FROM taken WHERE eind IS NULL ORDER BY id DESC LIMIT 1').fetchone()


def _set_step(db, taak_id, agent, status):
    if status not in STEP_STATUS or not agent:
        return
    row = db.execute(
        'SELECT id FROM stappen WHERE taak_id = ? AND agent = ? ORDER BY volgorde LIMIT 1',
        (taak_id, agent)).fetchone()
    if row:
        db.execute('UPDATE stappen SET status = ?, op = ? WHERE id = ?', (status, time.time(), row['id']))


def _agent_from_tool(tool, tool_input):
    name = str(tool or '')
    short = name.split('__')[-1]
    if short not in ('Agent', 'Task') and name not in ('Agent', 'Task'):
        return ''
    data = tool_input if isinstance(tool_input, dict) else {}
    who = str(data.get('subagent_type') or data.get('subagent') or data.get('name') or data.get('agent') or '')
    return who.split(':')[-1].strip().lower()[:40]


def note_tool(tool, tool_input, phase, ok=True):
    """Move a step. Universe tools already write their own audit row on success."""
    agent = _agent_from_tool(tool, tool_input)
    name = str(tool or '')
    universe = name.startswith('mcp__universe__')
    with brein.connect() as db:
        task = _current(db)
        if task:
            if phase == 'start' and agent:
                _set_step(db, task['id'], agent, 'bezig')
            elif phase == 'start':
                db.execute(
                    """UPDATE stappen SET status = 'bezig', op = ? WHERE taak_id = ? AND agent = 'hoofd'
                       AND status = 'todo'""",
                    (time.time(), task['id']))
            elif phase == 'fail' or (phase == 'done' and not ok):
                if agent:
                    _set_step(db, task['id'], agent, 'geblokkeerd')
                else:
                    db.execute(
                        """UPDATE stappen SET status = 'geblokkeerd', op = ? WHERE taak_id = ? AND status = 'bezig'""",
                        (time.time(), task['id']))
            elif phase == 'done' and agent:
                _set_step(db, task['id'], agent, 'klaar')
    if phase == 'start':
        return None
    if universe and ok and phase == 'done':
        return None
    status = 'mislukt' if (phase == 'fail' or not ok) else 'uitgevoerd'
    label = (agent or name.split('__')[-1] or 'hulpmiddel')[:80]
    summary = ('Subagent %s' % agent) if agent else label
    return brein.log_actie(label, summary, status)


def block_open(reason):
    with brein.connect() as db:
        task = _current(db)
        if task:
            db.execute(
                """UPDATE stappen SET status = 'geblokkeerd', op = ? WHERE taak_id = ? AND status = 'bezig'""",
                (time.time(), task['id']))
    return brein.log_actie('toestemming', str(reason or 'Vraag op het scherm')[:400], 'wacht')


def finish_open():
    now = time.time()
    with brein.connect() as db:
        task = _current(db)
        if not task:
            return None
        blocked = db.execute(
            "SELECT count(*) FROM stappen WHERE taak_id = ? AND status = 'geblokkeerd'", (task['id'],)).fetchone()[0]
        db.execute(
            """UPDATE stappen SET status = 'klaar', op = ? WHERE taak_id = ? AND status = 'bezig'""",
            (now, task['id']))
        final = 'geblokkeerd' if blocked else 'klaar'
        db.execute('UPDATE taken SET eind = ?, status = ? WHERE id = ?', (now, final, task['id']))
        return {'id': task['id'], 'status': final, 'titel': task['titel'], 'soort': task['soort']}


def observe(event, data):
    """One hook event. Returns extra context for the start of a task, otherwise ''."""
    data = data if isinstance(data, dict) else {}
    event = str(event or '')
    if event == 'UserPromptSubmit':
        prompt = data.get('prompt') or data.get('user_prompt') or ''
        begin(prompt)
        import patronen
        return patronen.block_for(prompt)
    if event == 'PreToolUse':
        note_tool(data.get('tool_name'), data.get('tool_input'), 'start')
    elif event == 'PostToolUse':
        note_tool(data.get('tool_name'), data.get('tool_input'), 'done', ok=True)
    elif event == 'PostToolUseFailure':
        note_tool(data.get('tool_name'), data.get('tool_input'), 'fail', ok=False)
    elif event == 'SubagentStart':
        who = data.get('agent_type') or data.get('subagent_type') or data.get('agent_name') or ''
        note_tool('Agent', {'subagent_type': who}, 'start')
    elif event == 'SubagentStop':
        who = data.get('agent_type') or data.get('subagent_type') or data.get('agent_name') or ''
        ok = str(data.get('status') or '') != 'error' and not data.get('error')
        note_tool('Agent', {'subagent_type': who}, 'done' if ok else 'fail', ok=ok)
    elif event == 'Notification':
        message = str(data.get('message') or '').lower()
        if data.get('notification_type') == 'permission_prompt' or 'permission' in message:
            block_open('Vraag op het scherm')
    elif event == 'Stop':
        finish_open()
    return ''


def activiteit(limit=20):
    limit = max(1, min(int(limit or 20), 50))
    with brein.connect() as db:
        tasks = db.execute('SELECT * FROM taken ORDER BY start DESC, id DESC LIMIT ?', (limit,)).fetchall()
        out = []
        for task in tasks:
            actions = db.execute(
                'SELECT * FROM acties WHERE taak_id = ? ORDER BY op ASC, id ASC', (task['id'],)).fetchall()
            out.append(dict(_task(task), acties=[brein._actie_row(row) for row in actions]))
        loose = db.execute(
            'SELECT * FROM acties WHERE taak_id IS NULL ORDER BY op DESC, id DESC LIMIT ?', (limit,)).fetchall()
    return {'taken': out, 'los': [brein._actie_row(row) for row in loose]}


def replay(taak_id):
    """Ordered log rows. The caller shows them. Nothing is executed again."""
    with brein.connect() as db:
        task = db.execute('SELECT * FROM taken WHERE id = ?', (int(taak_id),)).fetchone()
        if not task:
            raise ValueError('Taak niet gevonden')
        actions = db.execute(
            'SELECT * FROM acties WHERE taak_id = ? ORDER BY op ASC, id ASC', (task['id'],)).fetchall()
    return {'afspelen': 'alleen terugkijken', 'taak': _task(task),
            'stappen': [brein._actie_row(row) for row in actions]}


def export_file(folder, taak_id=None):
    data = replay(taak_id) if taak_id else activiteit(50)
    data['letop'] = 'Dit is een weergave van het log. Er wordt niets opnieuw uitgevoerd.'
    os.makedirs(folder, mode=0o700, exist_ok=True)
    dest = os.path.join(folder, 'ai-activiteit-%s.json' % time.strftime('%Y%m%d-%H%M%S'))
    tmp = dest + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, dest)
    return {'pad': dest}


def bord(limit=20):
    limit = max(1, min(int(limit or 20), 50))
    with brein.connect() as db:
        tasks = db.execute('SELECT * FROM taken ORDER BY start DESC, id DESC LIMIT ?', (limit,)).fetchall()
        out = []
        for task in tasks:
            steps = db.execute(
                'SELECT * FROM stappen WHERE taak_id = ? ORDER BY volgorde, id', (task['id'],)).fetchall()
            out.append(dict(_task(task), stappen=[_step(row) for row in steps]))
    return {'taken': out}
