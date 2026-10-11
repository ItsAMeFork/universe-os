"""The second brain: one local SQLite database with full-text search (FTS5), for Claude Code via universe-mcp.

Lives in ~/.local/share/universe-os/brein.db and never leaves the computer; only what Claude asks for goes into the
conversation. Phase 1: preferences, notes and facts. File index and timeline follow later (docs/CLAUDE-IN-UNIVERSE.md).
"""
import os
import sqlite3
import time

KINDS = ('voorkeur', 'notitie', 'feit')


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
    """)
    return db


def _row(r):
    return {'id': r['id'], 'soort': r['kind'], 'tekst': r['text'], 'labels': r['tags'],
            'datum': time.strftime('%Y-%m-%d', time.localtime(r['updated']))}


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
