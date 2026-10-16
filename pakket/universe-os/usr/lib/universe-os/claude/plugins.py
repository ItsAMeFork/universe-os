"""Curated skills and keyless MCP servers. Pinned, reviewed, and off the network until a fetch works.

Third-party hooks and rule packs are not installed. They run repository scripts on every tool call,
or they paste a whole skill into every session. Skills here are markdown the program can open when
the task needs them. See docs/AI-PLUGINS-EN-LESSEN.md.
"""
import copy
import json
import os
import time
import urllib.request

SUPERPOWERS = (
    'brainstorming', 'diagnosing-superpowers', 'dispatching-parallel-agents', 'executing-plans',
    'finishing-a-development-branch', 'receiving-code-review', 'requesting-code-review',
    'subagent-driven-development', 'systematic-debugging', 'test-driven-development',
    'using-git-worktrees', 'using-superpowers', 'verification-before-completion', 'writing-plans',
    'writing-skills',
)
COMMIT = {
    'superpowers': 'bb92a77741419a4ab5f06e711a283343f1ada0c3',
    'ecc': 'c05b2d6614f62f6db0047669aa4eefb223d478f9',
    'frontend-design': 'b0b7bed9820350bb0942e32c7f00752a99ea3555',
    'headroom': '855390d6110e0bbb199d9b97025baac16c2f5cf3',
    'omniroute': 'c1e30b7676975feb298b49eff6ff58923c04b89e',
    'impeccable': '2f98774f86bc05563876643db37e6c37c322850f',
    'design-taste-frontend': 'a60a36dc2bb3bb77ccf17f2f62041f5ca8a458b9',
    'chrome-devtools': 'bdc7e243a8d3397e871607fdb5c56cc7115ec5ae',
    'filesystem': 'bbb701e7ac1e57f3edd1c2836b94c5457eaf7b9c',
    'context7': '2dcbb295e4a2664b3b34aa6fa0c0b4f33fd08101',
}

def _files():
    rows = []
    for name in SUPERPOWERS:
        rows.append(('superpowers', 'https://github.com/obra/superpowers',
                     'skills/%s/SKILL.md' % name, 'superpowers-%s/SKILL.md' % name))
    for name in ('tdd-workflow', 'security-review', 'verification-loop'):
        rows.append(('ecc', 'https://github.com/affaan-m/ECC',
                     'skills/%s/SKILL.md' % name, 'ecc-%s/SKILL.md' % name))
    rows.append(('impeccable', 'https://github.com/pbakaus/impeccable',
                 'skill/SKILL.src.md', 'impeccable/SKILL.md'))
    rows.append(('design-taste-frontend', 'https://github.com/Leonxlnx/taste-skill',
                 'skills/taste-skill/SKILL.md', 'design-taste-frontend/SKILL.md'))
    rows.append(('frontend-design', 'https://github.com/anthropics/claude-code',
                 'plugins/frontend-design/skills/frontend-design/SKILL.md', 'frontend-design/SKILL.md'))
    return rows


FILES = _files()

CATALOG = (
    {
        'id': 'superpowers', 'naam': 'Superpowers', 'maker': 'obra', 'licentie': 'MIT',
        'soort': 'vaardigheden', 'standaard': True, 'providers': ('claude', 'codex', 'gemini', 'ollama'),
        'review': 'De SessionStart-hook leest alleen een lokaal bestand, maar plakt de hele vaardigheid in elke sessie. Die hook gaat niet aan. De vaardigheden wel, gepind op %s.' % COMMIT['superpowers'][:12],
    },
    {
        'id': 'ecc', 'naam': 'Everything Claude Code', 'maker': 'affaan-m', 'licentie': 'MIT',
        'soort': 'vaardigheden', 'standaard': True, 'providers': ('claude', 'codex', 'gemini'),
        'versie': '2.2.3',
        'review': 'Versie 2.2.3, tag-commit %s. Installeren: claude plugin marketplace add affaan-m/everything-claude-code en daarna claude plugin install ecc@ecc. Regels worden niet aangezet en niet gekopieerd. De hooks uit de repo schrijven we niet in settings.json. Drie vaardigheden komen uit die tag.' % COMMIT['ecc'][:12],
        'opdracht': (
            'claude plugin marketplace add affaan-m/everything-claude-code\n'
            'claude plugin install ecc@ecc\n'
            'rm -rf "${HOME}/.claude/rules/ecc"\n'
            'echo "ECC 2.2.3 staat er. Regels zijn niet aangezet."\n'
            'echo "Druk op Enter."; read -r _\n'
        ),
    },
    {
        'id': 'frontend-design', 'naam': 'Frontend design', 'maker': 'Anthropic', 'licentie': 'Apache-2.0',
        'soort': 'vaardigheden', 'standaard': True, 'providers': ('claude',),
        'review': 'Officieel, uit anthropics/claude-code op %s. Installeren: claude plugin install frontend-design@anthropic-plugin-directory. Alleen de vaardigheid; geen extra hook.' % COMMIT['frontend-design'][:12],
        'opdracht': (
            'claude plugin install frontend-design@anthropic-plugin-directory\n'
            'echo "Druk op Enter."; read -r _\n'
        ),
    },
    {
        'id': 'headroom', 'naam': 'Headroom', 'maker': 'headroomlabs-ai', 'licentie': 'Apache-2.0',
        'soort': 'programma', 'standaard': False, 'providers': ('claude',),
        'pakket': 'headroom-ai[all]==0.40.0',
        'review': 'Versie 0.40.0, commit %s. Het anonieme baken staat bij Headroom aan. universe-ai-headroom zet HEADROOM_BEACON=off en DO_NOT_TRACK=1 en start daarna headroom wrap claude. Serena (code-memory) wordt niet mee geïnstalleerd. Tokens besparen staat uit tot je het aanzet, en nooit tegelijk met de compressie van OmniRoute.' % COMMIT['headroom'][:12],
        'opdracht': (
            'if ! command -v uv >/dev/null 2>&1; then echo "uv ontbreekt. Headroom installeer je daarmee, niet via apt."; echo; echo "Druk op Enter."; read -r _; exit 1; fi\n'
            'uv tool install "headroom-ai[all]==0.40.0"\n'
            'echo "Headroom 0.40.0 staat er. Tokens besparen zet je apart aan op de pagina AI. Het baken blijft uit."\n'
            'echo "Druk op Enter."; read -r _\n'
        ),
    },
    {
        'id': 'omniroute', 'naam': 'OmniRoute', 'maker': 'diegosouzapw', 'licentie': 'MIT',
        'soort': 'programma', 'standaard': False, 'providers': ('claude', 'codex'),
        'pakket': 'omniroute@3.8.51',
        'review': 'Versie 3.8.51, commit %s. Alleen op deze computer, poort 20128. Blijft uit tot je zelf aanbieders toevoegt. Gratis aanbieders kunnen je vragen lezen. De compressie van OmniRoute en die van Headroom gaan niet samen.' % COMMIT['omniroute'][:12],
        'opdracht': (
            'if ! command -v npm >/dev/null 2>&1; then echo "Node.js (npm) ontbreekt."; echo; echo "Druk op Enter."; read -r _; exit 1; fi\n'
            'npm i -g omniroute@3.8.51\n'
            'echo "Start daarna zelf: omniroute"\n'
            'echo "Het paneel luistert op http://127.0.0.1:20128 . Gratis aanbieders kunnen je vragen lezen."\n'
            'echo "Druk op Enter."; read -r _\n'
        ),
    },
    {
        'id': 'impeccable', 'naam': 'Impeccable', 'maker': 'pbakaus', 'licentie': 'Apache-2.0',
        'soort': 'vaardigheden', 'standaard': True, 'providers': ('claude', 'codex', 'gemini'),
        'review': 'De design-hook draait een programma uit de repo na elke UI-wijziging. Alleen de markdown-vaardigheid gaat mee. Commit %s.' % COMMIT['impeccable'][:12],
    },
    {
        'id': 'design-taste-frontend', 'naam': 'Design taste', 'maker': 'Leonxlnx', 'licentie': 'MIT',
        'soort': 'vaardigheden', 'standaard': True, 'providers': ('claude', 'codex', 'gemini', 'ollama'),
        'review': 'Markdown, geen hooks. De experimentele v2-map gaat niet mee. Commit %s.' % COMMIT['design-taste-frontend'][:12],
    },
    {
        'id': 'filesystem', 'naam': 'Bestanden in de thuismap', 'maker': 'modelcontextprotocol',
        'licentie': 'MIT', 'soort': 'mcp', 'standaard': True, 'providers': ('claude', 'codex', 'gemini', 'ollama'),
        'pakket': '@modelcontextprotocol/server-filesystem@1.0.0',
        'review': 'Officiële server, alleen de thuismap als argument. Het pakket komt pas binnen als npx netwerk heeft; anders probeert de start het later opnieuw.',
    },
    {
        'id': 'chrome-devtools', 'naam': 'Chrome DevTools', 'maker': 'ChromeDevTools',
        'licentie': 'Apache-2.0', 'soort': 'mcp', 'standaard': False, 'providers': ('claude', 'codex', 'gemini'),
        'pakket': 'chrome-devtools-mcp@1.10.1',
        'review': 'Geen sleutel, wel een browser die het model kan sturen. Daarom uit tot je hem aanzet. Binnen de afscherming heeft hij geen Wayland.',
    },
    {
        'id': 'context7', 'naam': 'Context7', 'maker': 'upstash', 'licentie': 'MIT',
        'soort': 'mcp', 'standaard': False, 'providers': ('claude', 'codex', 'gemini'),
        'pakket': '@upstash/context7-mcp@4.4.1',
        'review': 'Een sleutel is niet verplicht, maar elke documentvraag gaat naar context7.com. Daarom uit tot je hem aanzet.',
    },
)


def accept_rel(rel):
    parts = [part for part in str(rel or '').split('/') if part != '']
    if not parts or str(rel).startswith('/') or '..' in parts:
        return False
    if any(part in ('hooks', 'rules', '.git') for part in parts):
        return False
    if not str(rel).endswith(('.md', '.txt')):
        return False
    return True


def _config_path():
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    folder = os.path.join(base, 'universe-os')
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return os.path.join(folder, 'ai-plugins.json')


def _store_root():
    base = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    folder = os.path.join(base, 'universe-os', 'ai', 'plugins')
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return folder


_read_cache = [None, None]  # [(mtime_ns, size, inode), parsed dict]


def _read_shared():
    """Parsed config, re-read only when the file changed. Callers must not mutate the result."""
    path = _config_path()
    try:
        st = os.stat(path)
        key = (st.st_mtime_ns, st.st_size, st.st_ino)
        if _read_cache[0] == key:
            return _read_cache[1]
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        _read_cache[0] = None
        return {}
    if not isinstance(data, dict):
        data = {}
    _read_cache[0], _read_cache[1] = key, data
    return data


def _read():
    return copy.deepcopy(_read_shared())


def _write(data):
    path = _config_path()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _item(plugin_id):
    for row in CATALOG:
        if row['id'] == plugin_id:
            return row
    return None


def _saved(plugin_id):
    items = _read_shared().get('items')
    if isinstance(items, dict) and isinstance(items.get(plugin_id), dict):
        return copy.deepcopy(items[plugin_id])
    return {}


def enabled(plugin_id):
    row = _item(plugin_id)
    if not row:
        return False
    saved = _saved(plugin_id)
    if 'aan' in saved:
        return bool(saved['aan'])
    return bool(row['standaard'])


def public_list():
    rows = []
    for row in CATALOG:
        saved = _saved(row['id'])
        rows.append({
            'id': row['id'], 'naam': row['naam'], 'licentie': row['licentie'], 'soort': row['soort'],
            'aan': enabled(row['id']), 'status': saved.get('status') or 'nog',
            'review': row['review'], 'commit': COMMIT.get(row['id'], ''),
            'versie': row.get('versie') or '',
            'installeren': bool(row.get('opdracht')),
        })
    return rows


def set_enabled(plugin_id, on):
    row = _item(plugin_id)
    if not row:
        raise ValueError('Onbekende plugin')
    data = _read()
    items = data.get('items') if isinstance(data.get('items'), dict) else {}
    current = dict(items.get(plugin_id) or {})
    current['aan'] = bool(on)
    if not on:
        current['status'] = 'uit'
    elif current.get('status') in (None, '', 'uit', 'nog') and row['soort'] == 'mcp':
        current['status'] = 'klaar'
    items[plugin_id] = current
    data['items'] = items
    _write(data)
    link_skills()
    return public_list()


def skill_root(provider, home=None):
    home = home or os.path.expanduser('~')
    if provider == 'codex':
        return os.path.join(home, '.codex', 'skills')
    if provider == 'gemini':
        return os.path.join(home, '.gemini', 'skills')
    if provider == 'ollama':
        return os.path.join(home, '.local', 'share', 'universe-os', 'ai', 'ollama-skills')
    return os.path.join(home, '.claude', 'skills')


def link_skills(home=None):
    """Symlink only our own skill folders. A disabled plugin loses the link, not the download."""
    home = home or os.path.expanduser('~')
    store = os.path.realpath(_store_root())
    for provider in ('claude', 'codex', 'gemini', 'ollama'):
        root = skill_root(provider, home)
        os.makedirs(root, mode=0o700, exist_ok=True)
        try:
            names = os.listdir(root)
        except OSError:
            names = []
        for name in names:
            path = os.path.join(root, name)
            if not os.path.islink(path):
                continue
            target = os.path.realpath(path)
            if target == store or target.startswith(store + os.sep):
                os.unlink(path)
        for plugin_id, _bron, _src, dest in FILES:
            row = _item(plugin_id)
            if not enabled(plugin_id) or provider not in row['providers']:
                continue
            folder = os.path.join(store, plugin_id, os.path.dirname(dest))
            if not os.path.isfile(os.path.join(folder, 'SKILL.md')):
                continue
            link = os.path.join(root, os.path.basename(os.path.dirname(dest)))
            if os.path.lexists(link):
                continue
            os.symlink(folder, link)


def _copies_rules(script):
    """Deleting ~/.claude/rules/ecc is allowed. Copying a rules tree in is not."""
    without_delete = str(script or '').replace('rm -rf "${HOME}/.claude/rules/ecc"', '')
    return 'cp ' in without_delete or 'rules/' in without_delete


def install_script(plugin_id):
    row = _item(plugin_id)
    if not row or not row.get('opdracht'):
        raise ValueError('Dit onderdeel heeft geen installatieprogramma.')
    if _copies_rules(row['opdracht']):
        raise ValueError('Het installatieprogramma mag geen regels kopiëren.')
    return row['opdracht']


def install_files(plugin_id, files):
    """files maps a relative destination to bytes. Paths outside the allow list are refused."""
    row = _item(plugin_id)
    if not row or row['soort'] != 'vaardigheden':
        raise ValueError('Geen vaardighedenpakket')
    root = os.path.join(_store_root(), plugin_id)
    written = 0
    for rel, blob in (files or {}).items():
        if not accept_rel(rel):
            continue
        dest = os.path.join(root, rel)
        folder = os.path.dirname(dest)
        os.makedirs(folder, mode=0o700, exist_ok=True)
        tmp = dest + '.tmp'
        with open(tmp, 'wb') as handle:
            handle.write(blob if isinstance(blob, bytes) else str(blob).encode())
        os.chmod(tmp, 0o644)
        os.replace(tmp, dest)
        written += 1
    data = _read()
    items = data.get('items') if isinstance(data.get('items'), dict) else {}
    current = dict(items.get(plugin_id) or {})
    current['status'] = 'klaar' if written else 'later'
    current['commit'] = COMMIT[plugin_id]
    current.setdefault('aan', row['standaard'])
    items[plugin_id] = current
    data['items'] = items
    _write(data)
    link_skills()
    return written


def _url(bron, commit, src):
    repo = bron.rstrip('/').split('github.com/')[-1]
    return 'https://raw.githubusercontent.com/%s/%s/%s' % (repo, commit, src)


def _mark(plugin_id, status):
    row = _item(plugin_id)
    data = _read()
    items = data.get('items') if isinstance(data.get('items'), dict) else {}
    current = dict(items.get(plugin_id) or {})
    current['status'] = status
    current['commit'] = COMMIT.get(plugin_id, '')
    current.setdefault('aan', bool(row and row['standaard']))
    current['geprobeerd'] = time.time()
    items[plugin_id] = current
    data['items'] = items
    _write(data)


def ensure(opener=None, home=None, budget=12):
    """Download pinned markdown. One failed probe marks the rest for later and returns at once."""
    opener = opener or urllib.request.urlopen
    home = home or os.path.expanduser('~')
    for row in CATALOG:
        if row['soort'] == 'mcp':
            _mark(row['id'], 'klaar' if enabled(row['id']) else 'uit')
        elif row['soort'] == 'programma':
            saved = _saved(row['id'])
            if saved.get('status') not in ('klaar', 'later'):
                _mark(row['id'], 'uit' if not enabled(row['id']) else 'nog')
    probe = _url('https://github.com/obra/superpowers', COMMIT['superpowers'], 'LICENSE')
    started = time.monotonic()
    try:
        _fetch(probe, opener, 2)
        online = True
    except Exception:
        online = False
    if not online:
        for row in CATALOG:
            if row['soort'] == 'vaardigheden' and enabled(row['id']) and _saved(row['id']).get('status') != 'klaar':
                _mark(row['id'], 'later')
        link_skills(home)
        return {'later': True, 'tekst': 'Geen netwerk. De plugins worden later opnieuw geprobeerd.'}
    grouped = {}
    for plugin_id, bron, src, dest in FILES:
        if not enabled(plugin_id):
            continue
        grouped.setdefault(plugin_id, []).append((bron, src, dest))
    for plugin_id, parts in grouped.items():
        blob = {}
        for bron, src, dest in parts:
            if time.monotonic() - started > budget:
                _mark(plugin_id, 'later')
                break
            try:
                blob[dest] = _fetch(_url(bron, COMMIT[plugin_id], src), opener, 4)
            except Exception:
                continue
        if blob:
            install_files(plugin_id, blob)
        elif _saved(plugin_id).get('status') != 'klaar':
            _mark(plugin_id, 'later')
    link_skills(home)
    waiting = any(item['status'] == 'later' for item in public_list())
    return {'later': waiting, 'tekst': 'Plugins bijgewerkt.' if not waiting else 'Een deel wacht op netwerk.'}


def _fetch(url, opener, timeout):
    request = urllib.request.Request(url, headers={'User-Agent': 'universe-os'})
    with opener(request, timeout=timeout) as response:
        data = response.read(400000)
    if not data or len(data) >= 400000:
        raise ValueError('bestand te groot of leeg')
    return data


def mcp_servers(home):
    """Enabled MCP rows. The filesystem server receives only the home directory."""
    home = os.path.realpath(home or os.path.expanduser('~'))
    servers = {}
    for row in CATALOG:
        if row['soort'] != 'mcp' or not enabled(row['id']):
            continue
        if _saved(row['id']).get('status') not in ('klaar', 'later'):
            continue
        if row['id'] == 'filesystem':
            args = ['-y', row['pakket'], home]
        else:
            args = ['-y', row['pakket']]
        servers[row['id']] = {'command': 'npx', 'args': args}
    return servers


def skill_line():
    names = [row['naam'] for row in CATALOG if row['soort'] == 'vaardigheden' and enabled(row['id']) and _saved(row['id']).get('status') == 'klaar']
    if not names:
        return ''
    return ('\nVaardigheden staan lokaal klaar (%s). Open er een alleen als de taak het vraagt. '
            'Hun hooks en regels staan uit.\n' % ', '.join(names))
