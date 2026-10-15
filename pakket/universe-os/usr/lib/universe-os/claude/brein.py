"""The second brain: one local SQLite database with full-text search (FTS5), for Claude Code via universe-mcp.

Lives in ~/.local/share/universe-os/brein.db and never leaves the computer; only what Claude asks for goes into the
conversation. Preferences, notes and facts, plus a 30-day timeline. The Brein nebula reads the same rows: stars are
capped, and constellation lines come from shared tags and words through FTS5 (no embeddings).
"""
import json
import math
import os
import sqlite3
import time

KINDS = ('voorkeur', 'notitie', 'feit', 'les')
# The nebula draws one star per memory. Past this, older rows stay in the database but not on the canvas.
STAR_CAP = 160
TRAIL_CAP = 36
EDGE_CAP = 200
FORGET_PHRASE = 'alles vergeten'
# Short words that show up in almost every sentence. Tags may be shorter (length 2) and are not filtered here.
STOPWORDS = frozenset('''
de het een van en is dat die voor met op te zijn niet je jij ik in om aan ook als maar of er bij tot uit nog wel
dan naar over deze dit wat hoe waar mijn jou we ze zij hun ons onze kan moet wil graag heel meer veel iets niets
alles hier daar zo al nu later altijd nooit the and for you with this that from your are was were have has not but
about into over just like
'''.split())


def path():
    base = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    folder = os.path.join(base, 'universe-os')
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return os.path.join(folder, 'brein.db')


def connect():
    db = sqlite3.connect(path(), timeout=5)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, text TEXT NOT NULL,
                                             tags TEXT NOT NULL DEFAULT '', created REAL NOT NULL, updated REAL NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(text, tags, content='memories', content_rowid='id');
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, text, tags) VALUES (new.id, new.text, new.tags); END;
        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, text, tags) VALUES ('delete', old.id, old.text, old.tags); END;
        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, text, tags) VALUES ('delete', old.id, old.text, old.tags);
            INSERT INTO memories_fts(rowid, text, tags) VALUES (new.id, new.text, new.tags); END;
        CREATE TABLE IF NOT EXISTS timeline (at REAL NOT NULL, kind TEXT NOT NULL, item TEXT NOT NULL, label TEXT NOT NULL DEFAULT '');
        CREATE INDEX IF NOT EXISTS timeline_at ON timeline(at);
        CREATE TABLE IF NOT EXISTS hints (key TEXT PRIMARY KEY, answer TEXT NOT NULL, at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY, provider TEXT NOT NULL, naam TEXT NOT NULL,
            adres TEXT NOT NULL DEFAULT '', scopes TEXT NOT NULL DEFAULT '[]', extra TEXT NOT NULL DEFAULT '{}',
            created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS mail_items (id INTEGER PRIMARY KEY, account TEXT NOT NULL, extern TEXT NOT NULL,
            onderwerp TEXT NOT NULL, van TEXT NOT NULL DEFAULT '', samenvatting TEXT NOT NULL DEFAULT '',
            belangrijk INTEGER NOT NULL DEFAULT 1, wanneer REAL NOT NULL, UNIQUE(account, extern));
        CREATE TABLE IF NOT EXISTS agenda_items (id INTEGER PRIMARY KEY, account TEXT NOT NULL, extern TEXT NOT NULL,
            titel TEXT NOT NULL, start REAL NOT NULL, eind REAL NOT NULL, plek TEXT NOT NULL DEFAULT '',
            UNIQUE(account, extern));
        CREATE TABLE IF NOT EXISTS acties (id INTEGER PRIMARY KEY, op REAL NOT NULL, hulpmiddel TEXT NOT NULL,
            samenvatting TEXT NOT NULL, status TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '');
        CREATE INDEX IF NOT EXISTS acties_op ON acties(op);
        CREATE TABLE IF NOT EXISTS efficientie (id INTEGER PRIMARY KEY, op REAL NOT NULL, provider TEXT NOT NULL,
            model TEXT NOT NULL DEFAULT '', tokens_in INTEGER NOT NULL DEFAULT 0, tokens_out INTEGER NOT NULL DEFAULT 0,
            kosten REAL, schatting INTEGER NOT NULL DEFAULT 0, gereedschap INTEGER NOT NULL DEFAULT 0,
            duur REAL NOT NULL DEFAULT 0, taak TEXT NOT NULL DEFAULT '', soort TEXT NOT NULL DEFAULT 'sessie',
            les_id INTEGER, overgeslagen TEXT NOT NULL DEFAULT '');
        CREATE INDEX IF NOT EXISTS efficientie_op ON efficientie(op);
    """)
    columns = [row['name'] for row in db.execute('PRAGMA table_info(acties)')]
    if 'ongedaan' not in columns:
        db.execute("ALTER TABLE acties ADD COLUMN ongedaan TEXT NOT NULL DEFAULT ''")
    memory_columns = [row['name'] for row in db.execute('PRAGMA table_info(memories)')]
    if 'actief' not in memory_columns:
        db.execute('ALTER TABLE memories ADD COLUMN actief INTEGER NOT NULL DEFAULT 1')
    return db


def _aan(row):
    try:
        if 'actief' not in row.keys() or row['actief'] is None:
            return True
    except (AttributeError, IndexError):
        return True
    return bool(row['actief'])


def _row(r):
    return {'id': r['id'], 'soort': r['kind'], 'tekst': r['text'], 'labels': r['tags'],
            'aan': _aan(r), 'datum': time.strftime('%Y-%m-%d', time.localtime(r['updated']))}


def remember(text, kind='notitie', tags=''):
    text = str(text or '').strip()
    if not text:
        raise ValueError('Lege tekst')
    if len(text) > 4000:
        raise ValueError('Te lang (maximaal 4000 tekens)')
    if kind not in KINDS:
        raise ValueError('Soort moet een van %s zijn' % ', '.join(KINDS))
    now = time.time()
    with connect() as db:
        cur = db.execute('INSERT INTO memories(kind, text, tags, created, updated) VALUES (?, ?, ?, ?, ?)',
                         (kind, text, str(tags or '')[:200], now, now))
        return cur.lastrowid


def _match(query):
    """Turns free text into a safe FTS5 query: every word as a prefix term, any of them may match."""
    words = [''.join(c for c in w if c.isalnum()) for w in str(query).split()]
    return ' OR '.join('"%s"*' % w for w in words if w)


def recall(query='', kind=None, limit=20):
    limit = max(1, min(int(limit or 20), 100))
    with connect() as db:
        match = _match(query)
        if match:
            sql = ('SELECT m.* FROM memories_fts f JOIN memories m ON m.id = f.rowid WHERE memories_fts MATCH ?'
                   + (' AND m.kind = ?' if kind else '') + ' ORDER BY rank LIMIT ?')
            params = [match] + ([kind] if kind else []) + [limit]
        else:
            sql = 'SELECT * FROM memories' + (' WHERE kind = ?' if kind else '') + ' ORDER BY updated DESC LIMIT ?'
            params = ([kind] if kind else []) + [limit]
        return [_row(r) for r in db.execute(sql, params)]


def update(memory_id, text):
    text = str(text or '').strip()
    if not text:
        raise ValueError('Lege tekst')
    with connect() as db:
        cur = db.execute('UPDATE memories SET text = ?, updated = ? WHERE id = ?', (text[:4000], time.time(), int(memory_id)))
        if not cur.rowcount:
            raise ValueError('Herinnering %s bestaat niet' % memory_id)
    return True


def forget(memory_id):
    with connect() as db:
        cur = db.execute('DELETE FROM memories WHERE id = ?', (int(memory_id),))
        if not cur.rowcount:
            raise ValueError('Herinnering %s bestaat niet' % memory_id)
    return True


def _brightness(updated, now):
    """1.0 just written, fading toward 0.28 over a couple of weeks. The nebula uses this as star brightness."""
    age = max(0.0, float(now) - float(updated))
    return round(0.28 + 0.72 * math.exp(-age / (12 * 86400)), 3)


def _present(row, now=None):
    now = time.time() if now is None else now
    bright = _brightness(row['updated'], now)
    if row['kind'] == 'les' and not _aan(row):
        bright = round(bright * 0.35, 3)
    return {'id': row['id'], 'soort': row['kind'], 'tekst': row['text'], 'labels': row['tags'],
            'aan': _aan(row), 'aangemaakt': row['created'], 'bijgewerkt': row['updated'],
            'helderheid': bright}


def set_lesson_active(memory_id, aan):
    """Keep a lesson in the brain, but stop carrying it into the next session when aan is false."""
    if isinstance(aan, str):
        aan = aan.strip().lower() not in ('0', 'false', 'nee', 'uit', 'off')
    else:
        aan = bool(aan)
    with connect() as db:
        row = db.execute('SELECT kind FROM memories WHERE id = ?', (int(memory_id),)).fetchone()
        if not row or row['kind'] != 'les':
            raise ValueError('Dit is geen les')
        db.execute('UPDATE memories SET actief = ? WHERE id = ?', (1 if aan else 0, int(memory_id)))
    return get(memory_id)


def get(memory_id):
    with connect() as db:
        row = db.execute('SELECT * FROM memories WHERE id = ?', (int(memory_id),)).fetchone()
    return _present(row) if row else None


def list_memories(limit=STAR_CAP):
    """Newest memories for the nebula, never more than STAR_CAP."""
    limit = max(1, min(int(limit or STAR_CAP), STAR_CAP))
    now = time.time()
    with connect() as db:
        rows = db.execute('SELECT * FROM memories ORDER BY updated DESC, id DESC LIMIT ?', (limit,))
        return [_present(r, now) for r in rows]


def _tokens(text, min_len):
    raw = str(text or '').lower().replace(',', ' ').replace(';', ' ')
    words = []
    for part in raw.split():
        word = ''.join(ch for ch in part if ch.isalnum())
        if len(word) >= min_len and word not in STOPWORDS and word not in words:
            words.append(word)
    return words


def links(limit=STAR_CAP, max_edges=EDGE_CAP):
    """Constellation edges: memories that share a tag or a distinctive word, confirmed with FTS5.

    A token has to match through the full-text index, not only a Python substring. Tokens shared by two to eight
    memories become a chain (a line of stars), so one common word cannot fill the sky with edges.
    """
    rows = list_memories(limit)
    ids = {r['id'] for r in rows}
    grouped = {}  # token -> (id list, came from a tag)
    for row in rows:
        tagged = _tokens(row['labels'], 2)
        words = []
        for token in tagged:
            words.append(token)
        for token in _tokens(row['tekst'], 4):
            if token not in words:
                words.append(token)
            if len(words) >= 10:
                break
        for token in words:
            have, from_tag = grouped.get(token, ([], False))
            if row['id'] not in have:
                have.append(row['id'])
            grouped[token] = (have, from_tag or token in tagged)
    shared = [(token, members, from_tag) for token, (members, from_tag) in grouped.items() if 2 <= len(members) <= 8]
    shared.sort(key=lambda item: (0 if item[2] else 1, len(item[1]), -len(item[0])))
    edges, seen = [], set()
    with connect() as db:
        for token, members, _from_tag in shared[:80]:
            if len(edges) >= max_edges:
                break
            try:
                found = {r[0] for r in db.execute('SELECT rowid FROM memories_fts WHERE memories_fts MATCH ?', ('"%s"' % token,))}
            except sqlite3.OperationalError:
                continue
            confirmed = [mid for mid in members if mid in found and mid in ids]
            if len(confirmed) < 2:
                continue
            for left, right in zip(confirmed, confirmed[1:]):
                key = (min(left, right), max(left, right))
                if key in seen:
                    continue
                seen.add(key)
                edges.append({'van': left, 'naar': right, 'via': token})
                if len(edges) >= max_edges:
                    break
    return edges


def search_memories(query='', limit=40):
    """Memories matching a nebula search. An empty query is the recent list (every star lit)."""
    limit = max(1, min(int(limit or 40), STAR_CAP))
    match = _match(query)
    now = time.time()
    with connect() as db:
        if match:
            rows = db.execute('SELECT m.* FROM memories_fts f JOIN memories m ON m.id = f.rowid '
                              'WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?', (match, limit))
        else:
            rows = db.execute('SELECT * FROM memories ORDER BY updated DESC, id DESC LIMIT ?', (limit,))
        return [_present(r, now) for r in rows]


def resolve_flash(data):
    """The memory a hook or MCP just stored, so the open nebula can flash that star."""
    data = data if isinstance(data, dict) else {}
    if data.get('id'):
        row = get(data['id'])
        if row:
            return row
    text = str(data.get('tekst') or '').strip()
    if text:
        with connect() as db:
            row = db.execute('SELECT * FROM memories WHERE text = ? ORDER BY id DESC LIMIT 1', (text,)).fetchone()
        if row:
            return _present(row)
    fresh = list_memories(1)
    return fresh[0] if fresh else None


def forget_all(confirm):
    """Wipes memories, the timeline, hint answers, cached mail, agenda and the audit log.

    Connected accounts stay (those are logins, removed from the Accounts page). Refuses unless confirm is the exact phrase.
    """
    if str(confirm or '').strip().lower() != FORGET_PHRASE:
        raise ValueError('Typ "%s" om alles te vergeten.' % FORGET_PHRASE)
    with connect() as db:
        db.execute('DELETE FROM memories')
        db.execute('DELETE FROM timeline')
        db.execute('DELETE FROM hints')
        db.execute('DELETE FROM mail_items')
        db.execute('DELETE FROM agenda_items')
        db.execute('DELETE FROM acties')
        db.execute('DELETE FROM efficientie')
    return True


def summary():
    with connect() as db:
        per_kind = {kind: db.execute('SELECT count(*) FROM memories WHERE kind = ?', (kind,)).fetchone()[0] for kind in KINDS}
        return {
            'herinneringen': sum(per_kind.values()),
            'per_soort': per_kind,
            'tijdlijn': db.execute('SELECT count(*) FROM timeline').fetchone()[0],
            'hints': db.execute('SELECT count(*) FROM hints').fetchone()[0],
            'mail': db.execute('SELECT count(*) FROM mail_items').fetchone()[0],
            'agenda': db.execute('SELECT count(*) FROM agenda_items').fetchone()[0],
            'acties': db.execute('SELECT count(*) FROM acties').fetchone()[0],
            'accounts': db.execute('SELECT count(*) FROM accounts').fetchone()[0],
            'bewaarplaats': '~/.local/share/universe-os/brein.db',
            'dagen_tijdlijn': TIMELINE_DAYS,
        }


def export_data():
    now = time.time()
    with connect() as db:
        memories = [_present(r, now) for r in db.execute('SELECT * FROM memories ORDER BY id')]
        events = [{'op': r['at'], 'soort': r['kind'], 'wat': r['item'], 'naam': r['label']}
                  for r in db.execute('SELECT * FROM timeline ORDER BY at')]
        hints = [{'sleutel': r['key'], 'antwoord': r['answer'], 'op': r['at']}
                 for r in db.execute('SELECT * FROM hints ORDER BY key')]
        mail = [_mail_row(r) for r in db.execute('SELECT * FROM mail_items ORDER BY wanneer DESC')]
        agenda = [_agenda_row(r) for r in db.execute('SELECT * FROM agenda_items ORDER BY start')]
        actions = [_actie_row(r) for r in db.execute('SELECT * FROM acties ORDER BY op')]
    return {'herinneringen': memories, 'tijdlijn': events, 'hints': hints, 'mail': mail, 'agenda': agenda,
            'acties': actions, 'gemaakt': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(now))}


def write_export(folder):
    """Writes export_data() as JSON (mode 0600) and returns the path plus counts."""
    data = export_data()
    os.makedirs(folder, mode=0o700, exist_ok=True)
    dest = os.path.join(folder, 'brein-%s.json' % time.strftime('%Y%m%d-%H%M%S'))
    tmp = dest + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, dest)
    return {'pad': dest, 'herinneringen': len(data['herinneringen']), 'tijdlijn': len(data['tijdlijn']),
            'hints': len(data['hints'])}


# ----- timeline: what the user opened (30 days), for Claude and for the buddy's suggestions -----
TIMELINE_DAYS = 30


def log_event(kind, item, label=''):
    """kind: 'app' (a .desktop id) or 'file' (a path). Old entries go away after TIMELINE_DAYS."""
    now = time.time()
    with connect() as db:
        db.execute('INSERT INTO timeline(at, kind, item, label) VALUES (?, ?, ?, ?)', (now, kind, str(item)[:500], str(label)[:200]))
        if int(now) % 50 == 0:  # tidy up now and then, not on every insert
            db.execute('DELETE FROM timeline WHERE at < ?', (now - TIMELINE_DAYS * 86400,))


def timeline(days=7, kind=None, limit=100):
    since = time.time() - max(1, min(int(days or 7), TIMELINE_DAYS)) * 86400
    with connect() as db:
        rows = db.execute('SELECT * FROM timeline WHERE at >= ?' + (' AND kind = ?' if kind else '') + ' ORDER BY at DESC LIMIT ?',
                          [since] + ([kind] if kind else []) + [max(1, min(int(limit or 100), 500))])
        return [{'wanneer': time.strftime('%Y-%m-%d %H:%M', time.localtime(r['at'])), 'soort': r['kind'],
                 'wat': r['item'], 'naam': r['label']} for r in rows]


def _trail_point(row):
    return {'op': row['at'], 'soort': row['kind'], 'wat': row['item'], 'naam': row['label'] or row['item']}


def trail(limit=TRAIL_CAP):
    """Chronological comet trail for the nebula (oldest first), capped and evenly sampled."""
    limit = max(1, min(int(limit or TRAIL_CAP), TRAIL_CAP))
    since = time.time() - TIMELINE_DAYS * 86400
    with connect() as db:
        rows = list(db.execute('SELECT * FROM timeline WHERE at >= ? ORDER BY at ASC', (since,)))
    if len(rows) > limit:
        step = (len(rows) - 1) / (limit - 1)
        rows = [rows[round(i * step)] for i in range(limit)]
    return [_trail_point(r) for r in rows]


def habits(hour, weekday=None, min_count=3):
    """Apps the user often opens around this hour (±1) in the last 30 days, most frequent first."""
    since = time.time() - TIMELINE_DAYS * 86400
    hours = ['%02d' % ((hour + d) % 24) for d in (-1, 0, 1)]
    with connect() as db:
        rows = db.execute("SELECT item, max(label) AS label, count(DISTINCT date(at, 'unixepoch', 'localtime')) AS days "
                          "FROM timeline WHERE kind = 'app' AND at >= ? AND strftime('%H', at, 'unixepoch', 'localtime') IN (?, ?, ?) "
                          "GROUP BY item HAVING days >= ? ORDER BY days DESC LIMIT 5", [since] + hours + [min_count])
        return [{'id': r['item'], 'naam': r['label'], 'dagen': r['days']} for r in rows]


def hint_answer(key):
    with connect() as db:
        row = db.execute('SELECT answer, at FROM hints WHERE key = ?', (key,)).fetchone()
        return (row['answer'], row['at']) if row else (None, 0)


def set_hint_answer(key, answer):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO hints(key, answer, at) VALUES (?, ?, ?)', (key, answer, time.time()))


# ----- accounts (no secrets), mail, agenda, audit log -----
# Secrets never reach this database. accounts.py refuses banned keys before insert.
BANNED_ACCOUNT_KEYS = frozenset({
    'password', 'wachtwoord', 'token', 'secret', 'geheim', 'refresh_token', 'access_token',
    'client_secret', 'device_code', 'authorization',
})
ACTIE_STATUS = ('goedgekeurd', 'geweigerd', 'uitgevoerd', 'mislukt', 'automatisch', 'wacht', 'ongedaan')
MAIL_STAR = 1_000_000_000
AGENDA_STAR = 2_000_000_000
ACTIE_STAR = 3_000_000_000
LIST_FILTERS = ('alles', 'herinneringen', 'lessen', 'mail', 'agenda', 'acties')


def _check_public(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in BANNED_ACCOUNT_KEYS:
                raise ValueError('Geheimen horen in de sleutelbos, niet in het brein.')
            _check_public(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            _check_public(value)


def _clock(ts):
    return time.strftime('%Y-%m-%d %H:%M', time.localtime(float(ts)))


def save_account(row):
    """Stores a connected account without secrets. Raises if a banned key is present."""
    row = dict(row or {})
    _check_public(row)
    account_id = str(row.get('id') or '').strip()
    provider = str(row.get('provider') or '').strip()
    if not account_id or not provider:
        raise ValueError('Account-id en provider zijn verplicht')
    extra = row.get('extra') if isinstance(row.get('extra'), dict) else {}
    _check_public(extra)
    scopes = row.get('scopes') if isinstance(row.get('scopes'), list) else []
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO accounts(id, provider, naam, adres, scopes, extra, created) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (account_id[:80], provider[:40], str(row.get('naam') or '')[:200], str(row.get('adres') or '')[:200],
                    json.dumps(scopes, ensure_ascii=False), json.dumps(extra, ensure_ascii=False),
                    float(row.get('created') or time.time())))
    return get_account(account_id)


def _account_row(r):
    try:
        scopes = json.loads(r['scopes'] or '[]')
    except ValueError:
        scopes = []
    try:
        extra = json.loads(r['extra'] or '{}')
    except ValueError:
        extra = {}
    return {'id': r['id'], 'provider': r['provider'], 'naam': r['naam'], 'adres': r['adres'],
            'scopes': scopes if isinstance(scopes, list) else [], 'extra': extra if isinstance(extra, dict) else {},
            'created': r['created']}


def get_account(account_id):
    with connect() as db:
        row = db.execute('SELECT * FROM accounts WHERE id = ?', (str(account_id),)).fetchone()
    return _account_row(row) if row else None


def list_accounts():
    with connect() as db:
        return [_account_row(r) for r in db.execute('SELECT * FROM accounts ORDER BY created')]


def delete_account(account_id):
    with connect() as db:
        cur = db.execute('DELETE FROM accounts WHERE id = ?', (str(account_id),))
        db.execute('DELETE FROM mail_items WHERE account = ?', (str(account_id),))
        db.execute('DELETE FROM agenda_items WHERE account = ?', (str(account_id),))
    return cur.rowcount > 0


def upsert_mail(account, extern, onderwerp, van='', samenvatting='', wanneer=None, belangrijk=1):
    extern = str(extern or '').strip()
    if not extern:
        raise ValueError('Bericht zonder id')
    now = time.time() if wanneer is None else float(wanneer)
    with connect() as db:
        db.execute('''INSERT INTO mail_items(account, extern, onderwerp, van, samenvatting, belangrijk, wanneer)
                      VALUES (?, ?, ?, ?, ?, ?, ?)
                      ON CONFLICT(account, extern) DO UPDATE SET onderwerp=excluded.onderwerp, van=excluded.van,
                      samenvatting=excluded.samenvatting, belangrijk=excluded.belangrijk, wanneer=excluded.wanneer''',
                   (str(account)[:80], extern[:200], str(onderwerp or '')[:300], str(van or '')[:200],
                    str(samenvatting or '')[:500], 1 if belangrijk else 0, now))


def _mail_row(r):
    return {'id': r['id'], 'account': r['account'], 'extern': r['extern'], 'onderwerp': r['onderwerp'],
            'van': r['van'], 'samenvatting': r['samenvatting'], 'belangrijk': bool(r['belangrijk']),
            'wanneer': r['wanneer'], 'tijd': _clock(r['wanneer'])}


def list_mail(limit=12, query=''):
    limit = max(1, min(int(limit or 12), 40))
    query = str(query or '').strip()
    like = '%' + query.replace('%', '').replace('_', '') + '%'
    with connect() as db:
        if query:
            rows = db.execute('''SELECT * FROM mail_items WHERE belangrijk = 1 AND (onderwerp LIKE ? OR van LIKE ?
                                 OR samenvatting LIKE ?) ORDER BY wanneer DESC LIMIT ?''', (like, like, like, limit))
        else:
            rows = db.execute('SELECT * FROM mail_items WHERE belangrijk = 1 ORDER BY wanneer DESC LIMIT ?', (limit,))
        return [_mail_row(r) for r in rows]


def upsert_agenda(account, extern, titel, start, eind, plek=''):
    extern = str(extern or '').strip()
    if not extern:
        raise ValueError('Afspraak zonder id')
    with connect() as db:
        db.execute('''INSERT INTO agenda_items(account, extern, titel, start, eind, plek) VALUES (?, ?, ?, ?, ?, ?)
                      ON CONFLICT(account, extern) DO UPDATE SET titel=excluded.titel, start=excluded.start,
                      eind=excluded.eind, plek=excluded.plek''',
                   (str(account)[:80], extern[:200], str(titel or '')[:300], float(start), float(eind), str(plek or '')[:200]))


def _agenda_row(r):
    return {'id': r['id'], 'account': r['account'], 'extern': r['extern'], 'titel': r['titel'],
            'start': r['start'], 'eind': r['eind'], 'plek': r['plek'],
            'van': _clock(r['start']), 'tot': _clock(r['eind'])}


def list_agenda(limit=12, query='', now=None):
    limit = max(1, min(int(limit or 12), 40))
    now = time.time() if now is None else float(now)
    query = str(query or '').strip()
    like = '%' + query.replace('%', '').replace('_', '') + '%'
    with connect() as db:
        if query:
            rows = db.execute('''SELECT * FROM agenda_items WHERE eind >= ? AND (titel LIKE ? OR plek LIKE ?)
                                 ORDER BY start LIMIT ?''', (now - 3600, like, like, limit))
        else:
            rows = db.execute('SELECT * FROM agenda_items WHERE eind >= ? ORDER BY start LIMIT ?', (now - 3600, limit))
        return [_agenda_row(r) for r in rows]


def log_actie(hulpmiddel, samenvatting, status, detail='', ongedaan='', volledig=False):
    """Audit row. Callers must not put passwords or tokens in samenvatting or detail.

    volledig keeps an auto-sent message intact. Other rows stay short.
    """
    if status not in ACTIE_STATUS:
        raise ValueError('Status moet een van %s zijn' % ', '.join(ACTIE_STATUS))
    limit = 100000 if volledig else 400
    with connect() as db:
        cur = db.execute(
            'INSERT INTO acties(op, hulpmiddel, samenvatting, status, detail, ongedaan) VALUES (?, ?, ?, ?, ?, ?)',
            (time.time(), str(hulpmiddel or '')[:80], str(samenvatting or '')[:400], status,
             str(detail or '')[:limit], str(ongedaan or '')[:400]))
        return cur.lastrowid


def undo_actie(actie_id):
    """Reverses a logged action when it names a file under the home directory or a memory."""
    with connect() as db:
        row = db.execute('SELECT * FROM acties WHERE id = ?', (int(actie_id),)).fetchone()
    if not row:
        raise ValueError('Actie niet gevonden')
    try:
        payload = json.loads(row['ongedaan'] or '{}')
    except ValueError:
        payload = {}
    if not isinstance(payload, dict) or not payload.get('soort'):
        raise ValueError('Dit kan niet ongedaan worden gemaakt.')
    if payload.get('soort') == 'herinnering':
        forget(payload.get('id'))
    elif payload.get('soort') == 'bestand':
        _trash_file(payload.get('pad'))
    else:
        raise ValueError('Dit kan niet ongedaan worden gemaakt.')
    with connect() as db:
        db.execute('UPDATE acties SET status = ? WHERE id = ?', ('ongedaan', int(actie_id)))
    return {'ongedaan': True, 'id': int(actie_id)}


def _trash_file(raw):
    path = os.path.realpath(str(raw or ''))
    home = os.path.realpath(os.path.expanduser('~'))
    if not path or path == home or not path.startswith(home + os.sep) or os.path.islink(str(raw or '')):
        raise ValueError('Dit bestand kan niet ongedaan worden gemaakt.')
    if not os.path.isfile(path):
        raise ValueError('Het bestand staat er niet meer.')
    trash = os.path.join(home, '.local', 'share', 'Trash', 'files')
    os.makedirs(trash, mode=0o700, exist_ok=True)
    dest = os.path.join(trash, os.path.basename(path))
    if os.path.exists(dest):
        dest = dest + '-%d' % int(time.time())
    os.replace(path, dest)


def _actie_row(r):
    return {'id': r['id'], 'op': r['op'], 'tijd': _clock(r['op']), 'hulpmiddel': r['hulpmiddel'],
            'samenvatting': r['samenvatting'], 'status': r['status'], 'detail': r['detail'],
            'ongedaan': r['ongedaan'] if 'ongedaan' in r.keys() else ''}


def list_acties(limit=80, query='', status=None):
    limit = max(1, min(int(limit or 80), 200))
    query = str(query or '').strip()
    like = '%' + query.replace('%', '').replace('_', '') + '%'
    clauses, params = [], []
    if status:
        clauses.append('status = ?')
        params.append(status)
    if query:
        clauses.append('(samenvatting LIKE ? OR hulpmiddel LIKE ? OR detail LIKE ?)')
        params.extend((like, like, like))
    where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
    with connect() as db:
        rows = db.execute('SELECT * FROM acties' + where + ' ORDER BY op DESC LIMIT ?', params + [limit])
        return [_actie_row(r) for r in rows]


def _mail_star(row):
    text = '%s — %s' % (row['onderwerp'], row['samenvatting'])
    return {'id': MAIL_STAR + int(row['id']), 'bron': 'mail', 'bron_id': row['id'], 'soort': 'mail',
            'tekst': text.strip(' —'), 'labels': row['van'], 'aangemaakt': row['wanneer'], 'bijgewerkt': row['wanneer'],
            'helderheid': 0.92, 'account': row['account']}


def _agenda_star(row):
    text = row['titel'] + ((' · ' + row['plek']) if row['plek'] else '')
    return {'id': AGENDA_STAR + int(row['id']), 'bron': 'agenda', 'bron_id': row['id'], 'soort': 'agenda',
            'tekst': '%s (%s)' % (text, row['van']), 'labels': row['plek'], 'aangemaakt': row['start'],
            'bijgewerkt': row['start'], 'helderheid': 0.9, 'account': row['account']}


def _actie_star(row):
    return {'id': ACTIE_STAR + int(row['id']), 'bron': 'actie', 'bron_id': row['id'], 'soort': 'actie',
            'tekst': '%s · %s · %s' % (row['tijd'], row['status'], row['samenvatting']), 'labels': row['hulpmiddel'],
            'aangemaakt': row['op'], 'bijgewerkt': row['op'], 'helderheid': 0.75}


def sterren_extra(limit=24):
    """Mail, agenda and audit rows as nebula stars (ids live in a high range, away from memories)."""
    each = max(1, min(int(limit or 24), 40) // 3 or 1)
    stars = [_mail_star(r) for r in list_mail(each)]
    stars += [_agenda_star(r) for r in list_agenda(each)]
    stars += [_actie_star(r) for r in list_acties(each)]
    return stars


def lijst(soort='alles', zoek='', limit=40):
    """Flat, filterable list for the Brein page: memories, mail, agenda, actions."""
    soort = str(soort or 'alles').strip().lower()
    if soort not in LIST_FILTERS:
        raise ValueError('Filter moet een van %s zijn' % ', '.join(LIST_FILTERS))
    limit = max(1, min(int(limit or 40), 80))
    query = str(zoek or '').strip()
    needle = query.lower()
    rows = []

    def add(row):
        blob = ' '.join(str(row.get(key) or '') for key in ('titel', 'tekst', 'status', 'van')).lower()
        if needle and needle not in blob:
            return
        rows.append(row)

    if soort in ('alles', 'herinneringen', 'lessen'):
        memories = search_memories(query, limit) if query else list_memories(limit)
        for item in memories:
            lesson = item['soort'] == 'les'
            if lesson and soort == 'herinneringen':
                continue
            if not lesson and soort == 'lessen':
                continue
            add({'soort': 'les' if lesson else 'herinnering', 'id': item['id'],
                 'titel': 'Les' if lesson else item['soort'], 'tekst': item['tekst'],
                 'aan': bool(item.get('aan', True)),
                 'wanneer': item['bijgewerkt'], 'tijd': _clock(item['bijgewerkt']), 'status': ''})
    if soort in ('alles', 'mail'):
        for item in list_mail(limit, query):
            add({'soort': 'mail', 'id': item['id'], 'titel': item['onderwerp'], 'tekst': item['samenvatting'],
                 'van': item['van'], 'wanneer': item['wanneer'], 'tijd': item['tijd'], 'status': ''})
    if soort in ('alles', 'agenda'):
        for item in list_agenda(limit, query):
            add({'soort': 'agenda', 'id': item['id'], 'titel': item['titel'], 'tekst': item['plek'],
                 'wanneer': item['start'], 'tijd': item['van'], 'status': ''})
    if soort in ('alles', 'acties'):
        for item in list_acties(limit, query):
            add({'soort': 'actie', 'id': item['id'], 'titel': item['hulpmiddel'], 'tekst': item['samenvatting'],
                 'wanneer': item['op'], 'tijd': item['tijd'], 'status': item['status'],
                 'ongedaan': item.get('ongedaan') or ''})
    rows.sort(key=lambda row: row.get('wanneer') or 0, reverse=True)
    return {'rijen': rows[:limit], 'sterren': sterren_extra(limit)}


def log_efficientie(provider, model, tokens_in, tokens_out, schatting, gereedschap, duur, taak,
                    soort='sessie', kosten=None, overgeslagen=''):
    """One finished task or one reflection. taak is a short scrubbed title, never a secret."""
    if soort not in ('sessie', 'reflectie'):
        raise ValueError('Soort moet sessie of reflectie zijn')
    with connect() as db:
        cur = db.execute(
            '''INSERT INTO efficientie(op, provider, model, tokens_in, tokens_out, kosten, schatting, gereedschap,
               duur, taak, soort, overgeslagen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (time.time(), str(provider or '')[:40], str(model or '')[:80], int(tokens_in or 0), int(tokens_out or 0),
             kosten, 1 if schatting else 0, int(gereedschap or 0), float(duur or 0), str(taak or '')[:160],
             soort, str(overgeslagen or '')[:80]))
        return cur.lastrowid


def mark_efficientie(row_id, overgeslagen='', les_id=None):
    with connect() as db:
        db.execute('UPDATE efficientie SET overgeslagen = ?, les_id = COALESCE(?, les_id) WHERE id = ?',
                   (str(overgeslagen or '')[:80], les_id, int(row_id)))


def recent_efficientie(limit=8, soort='sessie'):
    limit = max(1, min(int(limit or 8), 40))
    with connect() as db:
        rows = db.execute(
            'SELECT * FROM efficientie WHERE soort = ? ORDER BY op DESC, id DESC LIMIT ?', (soort, limit))
        return [{
            'id': r['id'], 'op': r['op'], 'provider': r['provider'], 'model': r['model'],
            'tokens_in': r['tokens_in'], 'tokens_out': r['tokens_out'], 'schatting': bool(r['schatting']),
            'gereedschap': r['gereedschap'], 'duur': r['duur'], 'taak': r['taak'],
            'overgeslagen': r['overgeslagen'], 'les_id': r['les_id'],
        } for r in rows]


def reflectie_tokens_since(since):
    with connect() as db:
        row = db.execute(
            'SELECT COALESCE(SUM(tokens_in + tokens_out), 0) FROM efficientie WHERE soort = ? AND op >= ?',
            ('reflectie', float(since))).fetchone()
        return int(row[0] or 0)
