"""Which assistant program the panel starts.

Claude Code, the OpenAI Codex CLI and the Gemini CLI all speak MCP. universe_mcp.py stays
the only tool server, so mail, calendar and screen confirmation stay in the shell no matter
which program is in the panel. Ollama is a model server, not an MCP client; ollama_host.py
is the small client that talks to it. OpenCode (MIT) and Goose (Apache-2.0) are optional
extra agents, not the default. Their own permission system is not the confirmation boundary.
OpenClaude is refused. See docs/REVIEW-AI-STACK.md.
"""
import json
import os
import re
import shutil
import urllib.parse

SERVICE = 'universe-os'
MODEL_RE = re.compile(r'[A-Za-z0-9._:+/-]{1,80}')
UPSTREAM_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,39}')
COMPRESSIE = ('geen', 'headroom', 'omniroute')
ROUTES = ('claude', 'omniroute', 'litellm')
OMNIROUTE_BASE = 'http://127.0.0.1:20128'
LITELLM_DEFAULT = 'http://127.0.0.1:4000'
WAARSCHUWING_GRATIS = 'Gratis aanbieders kunnen je vragen lezen. Zet OmniRoute alleen aan als je dat wilt.'
GATEWAY_KEYS = {'litellm': 'ANTHROPIC_AUTH_TOKEN'}
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
    'opencode': {
        'naam': 'OpenCode',
        'kort': 'OpenCode',
        'bins': ('opencode',),
        'extra': ('~/.local/bin/opencode', '~/.opencode/bin/opencode'),
        'default_model': '',
        'model_leeg': 'het model van OpenCode',
        'key_env': '',
        'sleutel': False,
        'uitleg': 'MIT. Alleen als je een andere agent dan Claude wilt. Niet OpenClaude. Universe koppelt alleen zijn eigen hulpmiddelen; zet de computer-besturing van OpenCode niet aan.',
    },
    'goose': {
        'naam': 'Goose',
        'kort': 'Goose',
        'bins': ('goose',),
        'extra': ('~/.local/bin/goose',),
        'default_model': '',
        'model_leeg': 'het model van Goose',
        'key_env': '',
        'sleutel': False,
        'uitleg': 'Apache-2.0. Alleen als je een andere agent dan Claude wilt. Niet OpenClaude. Alleen de Universe-hulpmiddelen worden aangezet.',
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


def refuse_openclaude(name):
    if 'openclaude' in str(name or '').lower():
        raise ValueError('OpenClaude wordt niet gebruikt. Het is een ongeautoriseerde afgeleide en stuurt standaard via een betaalde gateway. Kies Claude, OmniRoute of LiteLLM.')


def clean_local_url(url, default, label):
    text = str(url or '').strip() or default
    parsed = urllib.parse.urlparse(text)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'http' or host not in ('127.0.0.1', 'localhost'):
        raise ValueError('%s moet op deze computer draaien (127.0.0.1).' % label)
    port = parsed.port or urllib.parse.urlparse(default).port
    if not (1 <= port <= 65535):
        raise ValueError('Poort van %s klopt niet.' % label)
    return 'http://127.0.0.1:%d' % port


def clean_upstream(name):
    text = str(name or '').strip()
    if not UPSTREAM_RE.fullmatch(text):
        raise ValueError('De naam van een aanbieder mag alleen letters, cijfers, punt, streepje en plus bevatten. Geen adres.')
    return text


def _compressie_fields(raw):
    modus = raw.get('compressie') if raw.get('compressie') in COMPRESSIE else 'geen'
    names = []
    for item in raw.get('omniroute_providers') or []:
        try:
            clean = clean_upstream(item)
        except ValueError:
            continue
        if clean not in names:
            names.append(clean)
        if len(names) >= 12:
            break
    router = bool(raw.get('omniroute_router')) and bool(names)
    if modus == 'omniroute' and not names:
        modus = 'geen'
    return modus, names, router


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
    compressie, upstreams, router = _compressie_fields(raw)
    route = raw.get('sessie_route') if raw.get('sessie_route') in ROUTES else 'claude'
    if route == 'omniroute' and not upstreams:
        route = 'claude'
    try:
        litellm = clean_local_url(raw.get('litellm_url') or '', LITELLM_DEFAULT, 'LiteLLM')
    except ValueError:
        litellm = LITELLM_DEFAULT
    return {
        'provider': provider, 'model': model, 'ollama_url': url, 'leren': leren,
        'compressie': compressie, 'omniroute_providers': upstreams, 'omniroute_router': router,
        'sessie_route': route, 'litellm_url': litellm,
        'mail_via': 'account' if raw.get('mail_via') == 'account' else 'browser',
    }


def set_choice(provider, model='', ollama_url=None):
    refuse_openclaude(provider)
    if provider not in PROVIDERS:
        raise ValueError('Kies Claude Code, ChatGPT, Gemini, Ollama, OpenCode of Goose.')
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


def set_compressie(modus):
    """One compressor at a time. OmniRoute compression needs a provider the user added."""
    if modus not in COMPRESSIE:
        raise ValueError('Kies geen compressie, Headroom of OmniRoute.')
    data = load()
    if modus == 'omniroute' and not data['omniroute_providers']:
        raise ValueError('Voeg eerst een aanbieder toe. OmniRoute comprimeert pas daarna.')
    data['compressie'] = modus
    _write(data)
    return public_status()


def add_upstream(name):
    clean = clean_upstream(name)
    data = load()
    names = list(data['omniroute_providers'])
    if clean not in names:
        if len(names) >= 12:
            raise ValueError('Hoogstens twaalf aanbieders.')
        names.append(clean)
    data['omniroute_providers'] = names
    _write(data)
    return public_status()


def remove_upstream(name):
    clean = clean_upstream(name)
    data = load()
    names = [item for item in data['omniroute_providers'] if item != clean]
    data['omniroute_providers'] = names
    if not names:
        data['omniroute_router'] = False
        if data['compressie'] == 'omniroute':
            data['compressie'] = 'geen'
    _write(data)
    return public_status()


def set_router(on):
    data = load()
    if on and not data['omniroute_providers']:
        raise ValueError('Voeg eerst een aanbieder toe. De router blijft uit tot die er is.')
    data['omniroute_router'] = bool(on) and bool(data['omniroute_providers'])
    _write(data)
    return public_status()


def set_sessie(route):
    """Which model endpoint this Claude session uses. claude means Anthropic directly."""
    refuse_openclaude(route)
    if route not in ROUTES:
        raise ValueError('Kies Claude, OmniRoute of LiteLLM.')
    data = load()
    if route == 'omniroute' and not data['omniroute_providers']:
        raise ValueError('Voeg eerst een aanbieder toe. OmniRoute blijft uit tot die er is.')
    data['sessie_route'] = route
    _write(data)
    return public_status()


def set_mail_via(route):
    """browser is the default: Gmail and Outlook in the signed-in Chrome. account uses IMAP or OAuth."""
    if route not in ('browser', 'account'):
        raise ValueError('Kies mail via de browser, of via een gekoppeld account.')
    data = load()
    data['mail_via'] = route
    _write(data)
    return public_status()


def set_litellm_url(url):
    data = load()
    data['litellm_url'] = clean_local_url(url, LITELLM_DEFAULT, 'LiteLLM')
    _write(data)
    return public_status()


def set_key(provider, key):
    refuse_openclaude(provider)
    if provider not in GATEWAY_KEYS and (provider not in PROVIDERS or not PROVIDERS[provider]['key_env']):
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
    if provider not in GATEWAY_KEYS and (provider not in PROVIDERS or not PROVIDERS[provider]['key_env']):
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
        if found and access(found, os.X_OK) and 'openclaude' not in found.lower():
            return found
    for extra in spec['extra']:
        path = os.path.expanduser(extra)
        if access(path, os.X_OK) and 'openclaude' not in path.lower():
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
    route = cfg.get('sessie_route') or 'claude'
    via = ''
    if cfg['provider'] == 'claude' and route == 'omniroute':
        via = ' · via OmniRoute'
    elif cfg['provider'] == 'claude' and route == 'litellm':
        via = ' · via LiteLLM'
    return spec['naam'], '%s · %s%s' % (spec['kort'], model, via)


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
        'compressie': cfg.get('compressie') or 'geen',
        'omniroute_providers': list(cfg.get('omniroute_providers') or []),
        'omniroute_router': bool(cfg.get('omniroute_router')),
        'omniroute_waarschuwing': WAARSCHUWING_GRATIS,
        'mail_via': cfg.get('mail_via') or 'browser',
        'sessie_route': cfg.get('sessie_route') or 'claude',
        'litellm_url': cfg.get('litellm_url') or LITELLM_DEFAULT,
        'litellm_sleutel': has_key('litellm'),
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
    elif provider == 'opencode':
        return ('echo "OpenCode (MIT). Dit is niet OpenClaude."; '
                'curl -fsSL https://opencode.ai/install | bash; echo; echo "Druk op Enter om dit venster te sluiten."; read -r _')
    elif provider == 'goose':
        return ('echo "Goose (Apache-2.0). Dit is niet OpenClaude."; '
                'curl -fsSL https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh | CONFIGURE=false bash; '
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
    elif provider == 'opencode':
        conf_home = os.path.join(work, 'xdg-config')
        os.makedirs(os.path.join(conf_home, 'opencode'), mode=0o700, exist_ok=True)
        writes.append({'path': os.path.join(conf_home, 'opencode', 'opencode.json'), 'text': json.dumps({
            'mcp': {'servers': {'universe': {'type': 'local', 'command': ['python3', mcp], 'enabled': True}}},
        }, ensure_ascii=False, indent=2) + '\n'})
        env['XDG_CONFIG_HOME'] = conf_home
        env['XDG_DATA_HOME'] = os.path.join(work, 'xdg-data')
        argv = [binary]
    elif provider == 'goose':
        conf_home = os.path.join(work, 'xdg-config')
        os.makedirs(os.path.join(conf_home, 'goose'), mode=0o700, exist_ok=True)
        writes.append({'path': os.path.join(conf_home, 'goose', 'config.yaml'), 'text': (
            'extensions:\n  universe:\n    enabled: true\n    type: stdio\n    name: universe\n'
            '    cmd: python3\n    args:\n      - %s\n    timeout: 300\n' % json.dumps(mcp)[1:-1]
        )})
        env['XDG_CONFIG_HOME'] = conf_home
        env['XDG_DATA_HOME'] = os.path.join(work, 'xdg-data')
        argv = [binary, 'session']
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
    chrome_on = False
    if provider == 'claude':
        import chrome_agent
        if chrome_agent.binary(which):
            argv.append('--chrome')
            chrome_on = True
    # Headroom wraps Claude only. OmniRoute compression is the other choice, never both.
    if cfg.get('compressie') == 'headroom' and provider == 'claude':
        argv = ['/usr/bin/universe-ai-headroom'] + argv[1:]
        env['HEADROOM_BEACON'] = 'off'
        env['DO_NOT_TRACK'] = '1'
    route = cfg.get('sessie_route') or 'claude'
    if provider == 'claude' and route == 'claude':
        env.pop('ANTHROPIC_BASE_URL', None)
        env.pop('ANTHROPIC_AUTH_TOKEN', None)
    elif provider == 'claude' and route == 'omniroute':
        if not cfg.get('omniroute_providers'):
            return {'ok': False, 'provider': provider,
                    'fout': 'Voeg eerst een aanbieder toe. Deze sessie blijft bij Claude.'}
        env['ANTHROPIC_BASE_URL'] = OMNIROUTE_BASE
        env['OMNIROUTE_COMPRESSION'] = 'standard' if cfg.get('compressie') == 'omniroute' else 'off'
    elif provider == 'claude' and route == 'litellm':
        env['ANTHROPIC_BASE_URL'] = cfg.get('litellm_url') or LITELLM_DEFAULT
        env.pop('OMNIROUTE_COMPRESSION', None)
        token = key_for('litellm')
        if token:
            env['ANTHROPIC_AUTH_TOKEN'] = token
            env.pop('ANTHROPIC_API_KEY', None)
    if cfg.get('omniroute_router') and provider == 'codex':
        env['OPENAI_BASE_URL'] = OMNIROUTE_BASE + '/v1'
        env['OMNIROUTE_COMPRESSION'] = 'standard' if cfg.get('compressie') == 'omniroute' else 'off'
    if spec['key_env']:
        if key:
            env[spec['key_env']] = key
        else:
            env.pop(spec['key_env'], None)
    env['UNIVERSE_AI'] = provider
    return {'ok': True, 'provider': provider, 'argv': argv, 'env': env, 'cwd': work, 'writes': writes,
            'binary': binary, 'key_env': spec['key_env'], 'key': key, 'chrome': chrome_on}
