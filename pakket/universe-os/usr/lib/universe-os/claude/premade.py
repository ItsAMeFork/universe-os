"""Premade Claude Code agents and workflows, shipped in the managed profile.

The files live in this package. Enabled agents are symlinks under
~/.local/share/universe-os/claude/.claude/agents, which is the working directory
of a Universe session. Workflows are always linked. Turning an agent off removes
only our symlink.
"""
import json
import os

CATALOG = (
    {
        'id': 'reviewer', 'naam': 'Reviewer', 'bestand': 'reviewer.md', 'standaard': True,
        'rechten': 'Alleen lezen',
        'uitleg': 'Leest code en meldt fouten, veiligheid en stijl. Past niets aan.',
        'bron': 'Ruflo reviewer, MIT',
    },
    {
        'id': 'tester', 'naam': 'Tester', 'bestand': 'tester.md', 'standaard': True,
        'rechten': 'Lezen, tests schrijven en draaien',
        'uitleg': 'Schrijft en draait tests. Geen mail, geen wissen, geen installatie.',
        'bron': 'Ruflo tester, MIT',
    },
    {
        'id': 'researcher', 'naam': 'Onderzoeker', 'bestand': 'researcher.md', 'standaard': True,
        'rechten': 'Alleen lezen, lokaal zoeken',
        'uitleg': 'Zoekt in bestanden en in het brein. Verandert niets.',
        'bron': 'Ruflo researcher, MIT',
    },
    {
        'id': 'planner', 'naam': 'Planner', 'bestand': 'planner.md', 'standaard': True,
        'rechten': 'Alleen lezen',
        'uitleg': 'Maakt een kort plan. Schrijft geen bestanden.',
        'bron': '',
    },
    {
        'id': 'security-auditor', 'naam': 'Beveiliging', 'bestand': 'security-auditor.md', 'standaard': True,
        'rechten': 'Alleen lezen',
        'uitleg': 'Kijkt naar secrets, paden en invoer. Rapporteert, herstelt niet zelf.',
        'bron': 'Ruflo security-auditor, MIT',
    },
    {
        'id': 'mail-assistent', 'naam': 'Mail-assistent', 'bestand': 'mail-assistent.md', 'standaard': True,
        'rechten': 'Alleen mail en agenda',
        'uitleg': 'Leest en maakt concepten. Versturen blijft een vraag, of automatisch toestaan.',
        'bron': '',
    },
    {
        'id': 'opruimer', 'naam': 'Opruimer', 'bestand': 'opruimer.md', 'standaard': True,
        'rechten': 'Alleen het bureaublad',
        'uitleg': 'Ruimt het bureaublad op. De prullenbak vraagt altijd eerst.',
        'bron': '',
    },
)


def _item(agent_id):
    for row in CATALOG:
        if row['id'] == agent_id:
            return row
    return None


def _config_path():
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    folder = os.path.join(base, 'universe-os')
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return os.path.join(folder, 'ai-agents.json')


def _read():
    try:
        with open(_config_path(), encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(data):
    path = _config_path()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _saved(agent_id):
    items = _read().get('items')
    if isinstance(items, dict) and isinstance(items.get(agent_id), dict):
        return items[agent_id]
    return {}


def enabled(agent_id):
    row = _item(agent_id)
    if not row:
        return False
    saved = _saved(agent_id)
    if 'aan' in saved:
        return bool(saved['aan'])
    return bool(row['standaard'])


def public_list():
    rows = []
    for row in CATALOG:
        rows.append({
            'id': row['id'], 'naam': row['naam'], 'aan': enabled(row['id']),
            'rechten': row['rechten'], 'uitleg': row['uitleg'], 'bron': row['bron'],
        })
    return rows


def package_dir():
    return os.path.dirname(os.path.abspath(__file__))


def profile_root():
    """The managed Claude working directory, not ~/.claude and not the Ruflo profile."""
    base = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    path = os.path.join(base, 'universe-os', 'claude')
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path


def _link(src, dest):
    src = os.path.realpath(src)
    if not os.path.exists(src):
        return
    if os.path.lexists(dest):
        if os.path.islink(dest) and os.path.realpath(dest) == src:
            return
        if os.path.islink(dest):
            os.unlink(dest)
        else:
            return
    os.symlink(src, dest)


def sync():
    """Refresh symlinks. Disabled agents disappear. Real files the user made stay."""
    root = os.path.join(profile_root(), '.claude')
    agents = os.path.join(root, 'agents')
    commands = os.path.join(root, 'commands')
    skills = os.path.join(root, 'skills')
    for folder in (agents, commands, skills):
        os.makedirs(folder, mode=0o700, exist_ok=True)
    pkg = os.path.realpath(os.path.join(package_dir(), 'agenten'))
    try:
        names = os.listdir(agents)
    except OSError:
        names = []
    for name in names:
        path = os.path.join(agents, name)
        if not os.path.islink(path):
            continue
        target = os.path.realpath(path)
        if target == pkg or target.startswith(pkg + os.sep):
            os.unlink(path)
    for row in CATALOG:
        if not enabled(row['id']):
            continue
        _link(os.path.join(pkg, row['bestand']), os.path.join(agents, row['bestand']))
    flow = os.path.join(package_dir(), 'workflows')
    command_dir = os.path.join(package_dir(), 'commands')
    try:
        flows = os.listdir(flow)
    except OSError:
        flows = []
    for name in flows:
        folder = os.path.join(flow, name)
        if os.path.isdir(folder):
            _link(folder, os.path.join(skills, name))
    try:
        cmds = os.listdir(command_dir)
    except OSError:
        cmds = []
    for name in cmds:
        if name.endswith('.md'):
            _link(os.path.join(command_dir, name), os.path.join(commands, name))
    return public_list()


def set_enabled(agent_id, on):
    if not _item(agent_id):
        raise ValueError('Onbekende agent')
    data = _read()
    items = data.get('items') if isinstance(data.get('items'), dict) else {}
    current = dict(items.get(agent_id) or {})
    current['aan'] = bool(on)
    items[agent_id] = current
    data['items'] = items
    _write(data)
    sync()
    return public_list()


def line():
    names = [row['naam'] for row in public_list() if row['aan']]
    if not names:
        return ''
    return ('\nSubagents die aanstaan: %s. Roep ze aan als subagent, niet als zwerm. '
            'Hun rechten zijn klein. Mail, wissen en het scherm gaan door de universe-hulpmiddelen.\n'
            % ', '.join(names))
