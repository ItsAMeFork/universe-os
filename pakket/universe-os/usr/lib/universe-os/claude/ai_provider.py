"""Which assistant program the panel starts.

Claude Code, the OpenAI Codex CLI and the Gemini CLI all speak MCP. universe_mcp.py stays
the only tool server, so mail, calendar and screen confirmation stay in the shell no matter
which program is in the panel. Ollama is a model server, not an MCP client; ollama_host.py
is the small client that talks to it. Goose and OpenCode were not used: they bring a second
permission system and a second runtime, and they are not in Debian. See docs/REVIEW-AI-STACK.md.
"""
import json
import os
import re
import shutil
import urllib.parse

SERVICE = 'universe-os'
MODEL_RE = re.compile(r'[A-Za-z0-9._:+/-]{1,80}')
PROVIDERS = {
    'claude': {
        'naam': 'Claude Code',
        'kort': 'Claude Code',
        'bins': ('claude',),
        'extra': ('~/.local/bin/claude', '~/.claude/local/claude'),
        'default_model': 'haiku',
        'model_leeg': 'Haiku (snel, licht)',
        'key_env': 'ANTHROPIC_API_KEY',
        'sleutel': False,
        'uitleg': 'Standaard. Je meldt je aan met je eigen Claude-account in het paneel. Universe OS levert Claude Code niet mee.',
    },
    'codex': {
        'naam': 'ChatGPT',
        'kort': 'Codex',
        'bins': ('codex',),
        'extra': ('~/.local/bin/codex', '~/.npm-global/bin/codex'),
        'default_model': '',
        'model_leeg': 'het model van Codex',
        'key_env': 'OPENAI_API_KEY',
        'sleutel': True,
        'uitleg': 'Het Codex-programma van OpenAI. Aanmelden doe je in het paneel, of je bewaart hier een sleutel.',
    },
    'gemini': {
        'naam': 'Gemini',
        'kort': 'Gemini',
        'bins': ('gemini',),
        'extra': ('~/.local/bin/gemini', '~/.npm-global/bin/gemini'),
        'default_model': '',
        'model_leeg': 'het model van Gemini',
        'key_env': 'GEMINI_API_KEY',
        'sleutel': True,
        'uitleg': 'Het Gemini-programma van Google. Aanmelden in het paneel, of een sleutel in de sleutelbos.',
    },
    'ollama': {
        'naam': 'Op deze computer',
        'kort': 'Ollama',
        'bins': ('ollama',),
        'extra': ('/usr/local/bin/ollama',),
        'default_model': 'qwen2.5:3b',
        'model_leeg': 'qwen2.5:3b (klein, voor een trage computer)',
        'key_env': '',
        'sleutel': False,
        'uitleg': 'Ollama draait het model hier. Niets gaat naar een wolk. Een klein model is het enige dat een trage computer aankan. Grote modellen maken zo’n pc onbruikbaar. Een klein model volgt hulpmiddelen minder goed; de bevestiging op het scherm blijft wel.',
    },
}
_store = None


class MemoryKeyring:
    def __init__(self):
        self.data = {}

    def set_password(self, service, user, password):
        self.data[(service, user)] = password

    def get_password(self, service, user):
        return self.data.get((service, user))

    def delete_password(self, service, user):
        self.data.pop((service, user), None)


def set_store(backend):
    global _store
    _store = backend


def _backend():
    if _store is not None:
        return _store
    try:
        import keyring
    except ImportError as error:
        raise RuntimeError('De sleutelbos ontbreekt. Installeer python3-keyring en gnome-keyring.') from error
    return keyring


def _key_user(provider):
    return 'ai-sleutel:%s' % provider


def config_path():
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    folder = os.path.join(base, 'universe-os')
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return os.path.join(folder, 'ai.json')


def _read():
    path = config_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(data):
    path = config_path()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def clean_model(model):
    model = str(model or '').strip()
    if not model:
        return ''
    if not MODEL_RE.fullmatch(model):
        raise ValueError('Modelnaam mag alleen letters, cijfers, punt, dubbele punt, streepje en schuine streep.')
    return model


def clean_ollama_url(url):
    text = str(url or '').strip() or 'http://127.0.0.1:11434'
    parsed = urllib.parse.urlparse(text)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'http' or host not in ('127.0.0.1', 'localhost'):
        raise ValueError('Ollama moet op deze computer draaien (127.0.0.1). Een ander adres wordt niet gebruikt.')
    port = parsed.port or 11434
    if not (1 <= port <= 65535):
        raise ValueError('Poort van Ollama klopt niet.')
    return 'http://127.0.0.1:%d' % port


def load():
    raw = _read()
    provider = raw.get('provider') if raw.get('provider') in PROVIDERS else 'claude'
    try:
        model = clean_model(raw.get('model') or '')
    except ValueError:
        model = ''
    try:
        url = clean_ollama_url(raw.get('ollama_url') or '')
    except ValueError:
        url = 'http://127.0.0.1:11434'
    leren = True
    if 'leren' in raw:
        leren = bool(raw.get('leren'))
    return {'provider': provider, 'model': model, 'ollama_url': url, 'leren': leren}


def set_choice(provider, model='', ollama_url=None):
    if provider not in PROVIDERS:
        raise ValueError('Kies Claude Code, ChatGPT, Gemini of Ollama.')
    data = load()
    data['provider'] = provider
    data['model'] = clean_model(model)
    if ollama_url is not None:
        data['ollama_url'] = clean_ollama_url(ollama_url)
    _write(data)
    return public_status()


def set_leren(on):
    data = load()
    data['leren'] = bool(on)
    _write(data)
    return public_status()


def set_key(provider, key):
    if provider not in PROVIDERS or not PROVIDERS[provider]['key_env']:
        raise ValueError('Deze assistent gebruikt geen sleutel. Aanmelden doe je in het paneel.')
    key = str(key or '')
    if any(ch in key for ch in '\r\n'):
        raise ValueError('De sleutel mag geen regeleinde bevatten.')
    if not key.strip():
        try:
            _backend().delete_password(SERVICE, _key_user(provider))
        except Exception:
            pass
        return {'bewaard': False}
    _backend().set_password(SERVICE, _key_user(provider), key.strip())
    return {'bewaard': True}


def key_for(provider):
    if provider not in PROVIDERS or not PROVIDERS[provider]['key_env']:
        return ''
    try:
        value = _backend().get_password(SERVICE, _key_user(provider))
    except Exception:
        return ''
    return str(value or '')


def has_key(provider):
    return bool(key_for(provider))


def bin_for(provider, which=None, access=None):
    which = which or shutil.which
    access = access or os.access
    spec = PROVIDERS.get(provider)
    if not spec:
        return None
    for name in spec['bins']:
        found = which(name)
        if found and access(found, os.X_OK):
            return found
    for extra in spec['extra']:
        path = os.path.expanduser(extra)
        if access(path, os.X_OK):
            return path
    return None


def installed(provider, which=None, access=None):
    return bin_for(provider, which, access) is not None


def effective_model(cfg=None):
    cfg = cfg or load()
    if cfg['model']:
        return cfg['model']
    return PROVIDERS[cfg['provider']]['default_model']


def panel_title():
    cfg = load()
    spec = PROVIDERS[cfg['provider']]
    model = cfg['model'] or spec['model_leeg']
    return spec['naam'], '%s · %s' % (spec['kort'], model)


def public_status(which=None, access=None, sandbox_on=None):
    cfg = load()
    rows = []
    for pid, spec in PROVIDERS.items():
        rows.append({
            'id': pid,
            'naam': spec['naam'],
            'uitleg': spec['uitleg'],
            'geinstalleerd': installed(pid, which, access),
            'sleutel_mogelijk': bool(spec['key_env']),
            'sleutel_bewaard': has_key(pid),
            'model_leeg': spec['model_leeg'],
        })
    naam, regel = panel_title()
    trend, plugins = [], []
    try:
        import efficientie
        trend = efficientie.trend()
    except Exception:
        trend = []
    try:
        import plugins as plugin_catalog
        plugins = plugin_catalog.public_list()
    except Exception:
        plugins = []
    return {
        'provider': cfg['provider'],
        'model': cfg['model'],
        'model_effectief': effective_model(cfg),
        'ollama_url': cfg['ollama_url'],
        'leren': cfg.get('leren', True),
        'trend': trend,
        'plugins': plugins,
        'naam': naam,
        'regel': regel,
        'sandbox': bool(sandbox_on) if sandbox_on is not None else _sandbox_on(),
        'providers': rows,
    }


def _sandbox_on():
    try:
        import sandbox
        return sandbox.wanted()
    except Exception:
        return False


def _data_root():
    base = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    return os.path.join(base, 'universe-os')


def work_dir(provider):
    # Claude keeps the old folder so an existing conversation still continues.
    name = 'claude' if provider == 'claude' else os.path.join('ai', provider)
    path = os.path.join(_data_root(), name)
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path


def _claude_continue(work, fresh):
    if fresh:
        return False
    slug = re.sub(r'[^A-Za-z0-9]', '-', work)
    folder = os.path.expanduser(os.path.join('~/.claude/projects', slug))
    try:
        names = os.listdir(folder)
    except OSError:
        return False
    return any(name.endswith('.jsonl') for name in names)


def _write_text(path, text):
    folder = os.path.dirname(path)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        handle.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def instructions():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uitleg.md')
    try:
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
    except OSError:
        text = ''
    if not load().get('leren', True):
        return text
    try:
        import efficientie
        text += efficientie.lesson_block()
    except Exception:
        pass
    try:
        import plugins as plugin_catalog
        text += plugin_catalog.skill_line()
    except Exception:
        pass
    return text


def _toml_string(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def codex_config(mcp_path, model):
    lines = [
        '# Codex-eigen toestemming is niet de grens. Versturen, agenda en scherm vraagt de shell.',
        'approval_policy = "on-request"',
        'sandbox_mode = "workspace-write"',
    ]
    if model:
        lines.append('model = %s' % _toml_string(model))
    lines += [
        '',
        '[mcp_servers.universe]',
        'command = "python3"',
        'args = [%s]' % _toml_string(mcp_path),
        'enabled = true',
        '',
    ]
    return '\n'.join(lines)


def gemini_settings(mcp_path):
    return json.dumps({
        'mcpServers': {
            'universe': {
                'command': 'python3',
                'args': [mcp_path],
                'trust': True,
            },
        },
        'context': {'fileName': 'AGENTS.md'},
    }, ensure_ascii=False, indent=2) + '\n'


def install_script(provider):
    if provider == 'claude':
        return 'curl -fsSL https://claude.ai/install.sh | bash; echo; echo "Druk op Enter om dit venster te sluiten."; read -r _'
    if provider == 'codex':
        package = '@openai/codex'
    elif provider == 'gemini':
        package = '@google/gemini-cli'
    elif provider == 'ollama':
        return ('echo "Ollama staat niet in Debian 13. Installeer het van https://ollama.com en haal daarna een klein model op, bijvoorbeeld: ollama pull qwen2.5:3b"; '
                'echo; echo "Druk op Enter om dit venster te sluiten."; read -r _')
    else:
        raise ValueError('Onbekende assistent')
    return (
        'if ! command -v npm >/dev/null 2>&1; then echo "Node.js (npm) ontbreekt. Universe OS levert dit programma niet mee."; echo; echo "Druk op Enter."; read -r _; exit 1; fi; '
        'npm install -g %s; echo; echo "Druk op Enter om dit venster te sluiten."; read -r _' % package
    )


def _attach_mcp(provider, writes, argv, here, work, extra):
    """Adds reviewed MCP servers next to universe. No keys in the written file."""
    if provider == 'claude':
        base = os.path.join(here, 'mcp.json')
        try:
            with open(base, encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            data = {'mcpServers': {}}
        data.setdefault('mcpServers', {}).update(extra)
        path = os.path.join(work, 'mcp.json')
        writes.append({'path': path, 'text': json.dumps(data, ensure_ascii=False, indent=2) + '\n'})
        if '--mcp-config' in argv:
            argv[argv.index('--mcp-config') + 1] = path
        return
    if provider == 'codex':
        for item in writes:
            if item['path'].endswith('config.toml'):
                for name, spec in extra.items():
                    safe = ''.join(ch if ch.isalnum() else '_' for ch in name)
                    args = ', '.join(_toml_string(part) for part in spec['args'])
                    item['text'] += '\n[mcp_servers.%s]\ncommand = %s\nargs = [%s]\n' % (
                        safe, _toml_string(spec['command']), args)
        return
    if provider == 'gemini':
        for item in writes:
            if item['path'].endswith('settings.json') and '.gemini' in item['path']:
                data = json.loads(item['text'])
                data.setdefault('mcpServers', {}).update(extra)
                item['text'] = json.dumps(data, ensure_ascii=False, indent=2) + '\n'


def launch_plan(fresh=False, env=None, which=None, access=None):
    """How to start the selected CLI. Writes contain no API keys. The key is only in env."""
    env = dict(os.environ if env is None else env)
    cfg = load()
    provider = cfg['provider']
    spec = PROVIDERS[provider]
    binary = bin_for(provider, which, access)
    if not binary:
        return {'ok': False, 'provider': provider,
                'fout': '%s is niet geïnstalleerd. Zet het klaar op de pagina AI in het Controlecentrum.' % spec['naam']}
    here = os.path.dirname(os.path.abspath(__file__))
    mcp = os.path.join(here, 'universe_mcp.py')
    work = work_dir(provider)
    model = effective_model(cfg)
    key = key_for(provider)
    writes = [{'path': os.path.join(work, 'AGENTS.md'), 'text': instructions()}]
    argv = []
    if provider == 'claude':
        argv = [binary, '--model', model or 'haiku', '--add-dir', env.get('HOME') or os.path.expanduser('~'),
                '--mcp-config', os.path.join(here, 'mcp.json'), '--settings', os.path.join(here, 'settings.json'),
                '--append-system-prompt', instructions()]
        if _claude_continue(work, fresh):
            argv.insert(1, '--continue')
    elif provider == 'codex':
        home = os.path.join(work, 'codex-home')
        os.makedirs(home, mode=0o700, exist_ok=True)
        writes.append({'path': os.path.join(home, 'config.toml'), 'text': codex_config(mcp, model)})
        env['CODEX_HOME'] = home
        argv = [binary]
        if model:
            argv += ['--model', model]
    elif provider == 'gemini':
        writes.append({'path': os.path.join(work, '.gemini', 'settings.json'), 'text': gemini_settings(mcp)})
        writes.append({'path': os.path.join(work, 'GEMINI.md'), 'text': instructions()})
        argv = [binary]
        if model:
            argv += ['--model', model]
    else:
        host = os.path.join(here, 'ollama_host.py')
        argv = [env.get('PYTHON', '') or shutil.which('python3') or 'python3', host,
                '--model', model or 'qwen2.5:3b', '--url', cfg['ollama_url'], '--mcp', mcp,
                '--uitleg', os.path.join(here, 'uitleg.md')]
    if provider != 'claude':
        env['UNIVERSE_AI_EVENTS'] = '1'
    else:
        env.pop('UNIVERSE_AI_EVENTS', None)
    if cfg.get('leren', True):
        env['UNIVERSE_AI_REFLECT'] = '1'
    else:
        env.pop('UNIVERSE_AI_REFLECT', None)
    extra = {}
    try:
        import plugins as plugin_catalog
        extra = plugin_catalog.mcp_servers(env.get('HOME') or os.path.expanduser('~'))
    except Exception:
        extra = {}
    if extra:
        _attach_mcp(provider, writes, argv, here, work, extra)
    if spec['key_env']:
        if key:
            env[spec['key_env']] = key
        else:
            env.pop(spec['key_env'], None)
    env['UNIVERSE_AI'] = provider
    return {'ok': True, 'provider': provider, 'argv': argv, 'env': env, 'cwd': work, 'writes': writes,
            'binary': binary, 'key_env': spec['key_env'], 'key': key}
