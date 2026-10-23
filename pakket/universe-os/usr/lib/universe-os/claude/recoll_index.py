"""File index of the second brain: Recoll (Xapian full-text search, offline, in Debian). Optional: without the
recoll package the MCP tool falls back to the shell's quick file search.

The index covers the user's own folders only (Documenten, Bureaublad, Downloads, Afbeeldingen, Muziek, Video's) and is
updated incrementally on the lowest CPU and disk priority, every half hour, by the shell (buddy_hints)."""
import base64
import os
import shutil
import subprocess

CONF_DIR = os.path.expanduser('~/.recoll')


def available():
    return bool(shutil.which('recollq') and shutil.which('recollindex'))


def folders():
    result = []
    for key in ('DESKTOP', 'DOCUMENTS', 'DOWNLOAD', 'PICTURES', 'MUSIC', 'VIDEOS'):
        try:
            path = subprocess.run(['xdg-user-dir', key], capture_output=True, text=True, timeout=3).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if path and path != os.path.expanduser('~') and os.path.isdir(path) and path not in result:
            result.append(path)
    return result or [os.path.expanduser('~')]


def ensure_config():
    """A small recoll.conf of our own, only if the user has none yet (theirs always wins)."""
    conf = os.path.join(CONF_DIR, 'recoll.conf')
    if os.path.exists(conf):
        return
    os.makedirs(CONF_DIR, mode=0o700, exist_ok=True)
    quoted = ' '.join('"%s"' % p.replace('"', '') for p in folders())
    with open(conf, 'w', encoding='utf-8') as f:
        f.write('# Gemaakt door Universe OS (tweede brein van Claude). Je mag dit aanpassen.\n'
                'topdirs = %s\n'
                'skippedNames+ = node_modules .git .cache __pycache__ *.iso *.qcow2\n'
                'indexallfilenames = 1\n'
                'idxflushmb = 10\n' % quoted)


def _ghost():
    try:
        import ghost_modus
        return ghost_modus.enabled()
    except Exception:  # noqa: BLE001 - indexing stays available if the switch cannot be read
        return False


def index_command():
    """Incremental update, as gentle as possible. Ghost mode does not read the folders."""
    if _ghost():
        return ['true']
    ensure_config()
    cmd = ['nice', '-n', '19']
    if shutil.which('ionice'):
        cmd += ['ionice', '-c', '3']
    return cmd + ['recollindex']


def search(query, limit=20):
    """Returns [{'pad', 'titel', 'soort', 'samenvatting'}]. Ghost mode returns no file contents."""
    if _ghost():
        return []
    if not available():
        return None
    ensure_config()
    limit = max(1, min(int(limit or 20), 50))
    try:
        out = subprocess.run(['recollq', '-n', '0-%d' % (limit - 1), '-F', 'url title mtype abstract', str(query)],
                             capture_output=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    result = []
    for line in out.decode('utf-8', 'replace').splitlines():
        fields = line.split(' ')
        if len(fields) < 3:
            continue  # header lines ("Recoll query: ...", "N results")
        try:
            url, title, mtype = (base64.b64decode(x).decode('utf-8', 'replace') for x in fields[:3])
            abstract = base64.b64decode(fields[3]).decode('utf-8', 'replace') if len(fields) > 3 else ''
        except (ValueError, UnicodeError):
            continue
        if not url.startswith('file://'):
            continue
        result.append({'pad': url[len('file://'):], 'titel': title, 'soort': mtype, 'samenvatting': abstract[:300]})
    return result
