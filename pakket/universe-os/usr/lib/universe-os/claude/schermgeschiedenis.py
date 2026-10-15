"""Local screen history for the Brein. Screenshots and OCR stay on this computer.

Off until the user turns it on. Password managers and banking never get a frame,
even if the user clears the extra exclude list. Capture and OCR are our own.
"""
import os
import re
import shutil
import subprocess
import time

import brein
import kast

# Always excluded. The user list is extra, not a way to turn these back on.
HARD = (
    'keepass', 'bitwarden', '1password', 'kwallet', 'seahorse', 'gnome-keyring',
    'protonpass', 'proton pass', 'passbolt', 'enpass', 'dashlane',
    'internetbankieren', 'rabobank', 'abn amro', 'abnamro', 'ing bankieren',
    'asn bank', 'knab', 'bunq', 'paypal', 'revolut',
)
_TITLE = re.compile(r'wachtwoord|password|\bpin\b|bankieren', re.I)


def _int(value, default, low, high):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def state():
    row = kast.load()['scherm']
    return {
        'aan': bool(row.get('aan')),
        'pauze': bool(row.get('pauze')),
        'dagen': _int(row.get('dagen'), 7, 1, 90),
        'elke': _int(row.get('elke'), 60, 0, 3600),
        'uitsluiten': list(row.get('uitsluiten') or []),
    }


def configure(args):
    args = args if isinstance(args, dict) else {}
    fields = {}
    if 'aan' in args:
        fields['aan'] = bool(args.get('aan'))
    if 'pauze' in args:
        fields['pauze'] = bool(args.get('pauze'))
    if 'dagen' in args:
        fields['dagen'] = _int(args.get('dagen'), 7, 1, 90)
    if 'elke' in args:
        fields['elke'] = _int(args.get('elke'), 60, 0, 3600)
    if 'uitsluiten' in args:
        raw = args.get('uitsluiten')
        if isinstance(raw, str):
            raw = raw.splitlines()
        fields['uitsluiten'] = [str(item).strip()[:40] for item in (raw or []) if str(item).strip()][:40]
    if fields:
        kast.update('scherm', **fields)
    return public()


def image_dir():
    base = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    folder = os.path.join(base, 'universe-os', 'schermgeschiedenis')
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return folder


def remove_files():
    folder = image_dir()
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for name in names:
        try:
            os.remove(os.path.join(folder, name))
        except OSError:
            pass


def excluded(app, titel, extra=()):
    blob = ('%s %s' % (app or '', titel or '')).lower()
    if _TITLE.search(blob):
        return True
    for word in list(HARD) + list(extra or []):
        needle = str(word or '').strip().lower()
        if needle and needle in blob:
            return True
    return False


def _clock(stamp):
    try:
        return time.strftime('%Y-%m-%d %H:%M', time.localtime(float(stamp)))
    except (TypeError, ValueError, OSError):
        return ''


def _row(r):
    return {
        'id': r['id'], 'op': r['op'], 'tijd': _clock(r['op']), 'app': r['app'],
        'titel': r['titel'], 'tekst': (r['tekst'] or '')[:280], 'beeld': bool(r['pad']),
    }


def purge(now=None):
    cfg = state()
    now = time.time() if now is None else float(now)
    cutoff = now - cfg['dagen'] * 86400
    with brein.connect() as db:
        rows = db.execute('SELECT id, pad FROM scherm_beelden WHERE op < ?', (cutoff,)).fetchall()
        db.execute('DELETE FROM scherm_beelden WHERE op < ?', (cutoff,))
    for row in rows:
        if row['pad'] and os.path.isfile(row['pad']):
            try:
                os.remove(row['pad'])
            except OSError:
                pass
    return len(rows)


def _store(app, titel, png, tekst, now):
    tekst = re.sub(r'\s+', ' ', str(tekst or '')).strip()[:2000]
    with brein.connect() as db:
        cur = db.execute(
            'INSERT INTO scherm_beelden(op, app, titel, tekst, pad) VALUES (?, ?, ?, ?, ?)',
            (now, str(app or '')[:80], str(titel or '')[:160], tekst, ''))
        frame_id = cur.lastrowid
        dest = ''
        if png:
            dest = os.path.join(image_dir(), '%d.png' % frame_id)
            tmp = dest + '.tmp'
            with open(tmp, 'wb') as handle:
                handle.write(png)
            os.chmod(tmp, 0o600)
            os.replace(tmp, dest)
            db.execute('UPDATE scherm_beelden SET pad = ? WHERE id = ?', (dest, frame_id))
    purge(now)
    return {'bewaard': True, 'id': frame_id}


def grab(app='', titel='', shot=None, read_text=None, now=None):
    """One frame. shot() returns png bytes or b''. read_text(png) returns OCR text."""
    cfg = state()
    now = time.time() if now is None else float(now)
    if not cfg['aan']:
        return {'bewaard': False, 'reden': 'uit'}
    if cfg['pauze']:
        return {'bewaard': False, 'reden': 'pauze'}
    if excluded(app, titel, cfg['uitsluiten']):
        return {'bewaard': False, 'reden': 'uitgesloten'}
    with brein.connect() as db:
        last = db.execute('SELECT op FROM scherm_beelden ORDER BY op DESC LIMIT 1').fetchone()
    if last and cfg['elke'] and now - float(last['op']) < cfg['elke']:
        return {'bewaard': False, 'reden': 'wacht'}
    if shot is None:
        shot = _grim
    if read_text is None:
        read_text = _tesseract
    try:
        png = shot() or b''
    except Exception:
        png = b''
    if not png:
        return {'bewaard': False, 'reden': 'geen beeld'}
    try:
        tekst = read_text(png) or ''
    except Exception:
        tekst = ''
    return _store(app, titel, png, tekst, now)


def _grim():
    if not shutil.which('grim'):
        return b''
    try:
        done = subprocess.run(['grim', '-t', 'png', '-'], capture_output=True, timeout=8, check=False)
    except (OSError, subprocess.SubprocessError):
        return b''
    if done.returncode != 0 or not done.stdout.startswith(b'\x89PNG'):
        return b''
    return done.stdout


def _tesseract(png):
    if not shutil.which('tesseract') or not png:
        return ''
    folder = image_dir()
    src = os.path.join(folder, '.ocr.png')
    try:
        with open(src, 'wb') as handle:
            handle.write(png)
        os.chmod(src, 0o600)
        for lang in ('nld+eng', 'eng'):
            done = subprocess.run(
                ['tesseract', src, 'stdout', '-l', lang],
                capture_output=True, timeout=20, check=False)
            if done.returncode == 0 and done.stdout.strip():
                return done.stdout.decode('utf-8', 'replace')
        return ''
    except (OSError, subprocess.SubprocessError):
        return ''
    finally:
        try:
            os.remove(src)
        except OSError:
            pass


def search(query, limit=30):
    limit = max(1, min(int(limit or 30), 80))
    match = brein._match(query)
    with brein.connect() as db:
        if match:
            try:
                rows = db.execute(
                    '''SELECT s.* FROM scherm_fts f JOIN scherm_beelden s ON s.id = f.rowid
                       WHERE scherm_fts MATCH ? ORDER BY s.op DESC LIMIT ?''', (match, limit)).fetchall()
            except brein.sqlite3.OperationalError:
                rows = []
        else:
            rows = db.execute('SELECT * FROM scherm_beelden ORDER BY op DESC LIMIT ?', (limit,)).fetchall()
    return [_row(row) for row in rows]


def lijst(limit=40):
    limit = max(1, min(int(limit or 40), 80))
    with brein.connect() as db:
        rows = db.execute('SELECT * FROM scherm_beelden ORDER BY op DESC LIMIT ?', (limit,)).fetchall()
    return [_row(row) for row in rows]


def clear():
    with brein.connect() as db:
        db.execute('DELETE FROM scherm_beelden')
    remove_files()
    return public()


def public():
    cfg = state()
    return {
        'aan': cfg['aan'],
        'pauze': cfg['pauze'],
        'dagen': cfg['dagen'],
        'uitsluiten': cfg['uitsluiten'],
        'vast': list(HARD),
        'tekst': 'Aan' if cfg['aan'] and not cfg['pauze'] else ('Pauze' if cfg['aan'] else 'Uit'),
        'uitleg': ('Schermafbeeldingen en tekstherkenning blijven op deze computer. '
                   'Uit tot je het aanzet. Pauze stopt meteen. Wachtwoordbeheerders en bankieren '
                   'worden nooit bewaard. Oude beelden verdwijnen na %d dagen.') % cfg['dagen'],
    }
