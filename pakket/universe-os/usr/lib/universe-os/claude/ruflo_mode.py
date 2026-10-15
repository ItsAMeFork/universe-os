"""Optional Ruflo mode. Off by default.

Only the ruflo-core plugin, pinned, in its own Claude profile. Telemetry, cloud and
federation stay off. The wrapper drops --dangerously-skip-permissions so auto-accept
still follows universe_mcp.py and zenity.
"""
import json
import os

COMMIT = '1882006a02487590c8c66a7eec8d7504f6af33c3'
VERSION = '0.2.11'
RELEASE = '3.56.10'
WHY = ('Universe OS is de standaard: dezelfde soort hulp, maar alleen op deze computer, '
       'zonder telemetrie, wolk of federatie, en met onze bevestiging. Ruflo-core mag er '
       'los bij, in een eigen profiel. De zwerm, de daemon en de federatie blijven uit.')


def strip_skip(argv):
    """Remove the permission bypass. Other arguments stay, in order."""
    out = []
    skip_next = False
    for arg in argv:
        text = str(arg)
        if skip_next:
            skip_next = False
            if text == 'bypassPermissions':
                continue
            out.append('--permission-mode')
            out.append(text)
            continue
        if text == '--dangerously-skip-permissions' or text.startswith('--dangerously-skip-permissions='):
            continue
        if text == '--permission-mode=bypassPermissions':
            continue
        if text == '--permission-mode':
            skip_next = True
            continue
        out.append(text)
    if skip_next:
        out.append('--permission-mode')
    return out


def wrap_path():
    here = os.path.dirname(os.path.abspath(__file__))
    usr = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    return os.path.join(usr, 'bin', 'universe-claude-wrap')


def profile_path():
    """Separate from the managed Universe profile (~/.local/share/universe-os/claude)."""
    base = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    return os.path.join(base, 'universe-os', 'claude-ruflo')


def profile_dir():
    path = profile_path()
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path


def plugin_ready():
    return os.path.isfile(os.path.join(
        profile_path(), 'plugins', 'ruflo-core', '.claude-plugin', 'plugin.json'))


def enabled():
    try:
        import ai_provider
        return bool(ai_provider.load().get('ruflo'))
    except Exception:
        return False


def active_for_launch():
    """On, and the pinned plugin is actually in the separate profile."""
    return enabled() and plugin_ready()


def launch_env():
    return {
        'CLAUDE_CONFIG_DIR': profile_dir(),
        'DISABLE_TELEMETRY': '1',
        'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
        'DO_NOT_TRACK': '1',
        'RUFLO_TELEMETRY': 'off',
        'RUFLO_CLOUD': 'off',
        'RUFLO_FEDERATION': 'off',
    }


def merged_settings_text():
    """Our hooks and permissions, plus the pinned plugin, with the bypass refused."""
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
    with open(base, encoding='utf-8') as handle:
        data = json.load(handle)
    data['env'] = {
        'DISABLE_TELEMETRY': '1',
        'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
        'DO_NOT_TRACK': '1',
        'RUFLO_TELEMETRY': 'off',
        'RUFLO_CLOUD': 'off',
        'RUFLO_FEDERATION': 'off',
    }
    data['extraKnownMarketplaces'] = {
        'ruflo-pinned': {
            'source': {'source': 'directory', 'path': os.path.join(profile_path(), 'plugins')},
        },
    }
    data['enabledPlugins'] = {'ruflo-core@ruflo-pinned': True}
    perms = data.setdefault('permissions', {})
    if perms.get('defaultMode') == 'bypassPermissions':
        perms['defaultMode'] = 'default'
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'


def prepare_profile():
    """Write the declined settings. Does not download Ruflo."""
    folder = profile_dir()
    os.makedirs(os.path.join(folder, 'plugins'), mode=0o700, exist_ok=True)
    dest = os.path.join(folder, 'settings.json')
    tmp = dest + '.tmp'
    text = merged_settings_text()
    with open(tmp, 'w', encoding='utf-8') as handle:
        handle.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, dest)
    return dest


def install_script():
    """A terminal script. Only plugins/ruflo-core at the pinned commit."""
    commit = COMMIT
    version = VERSION
    return '''set -eu
COMMIT=%s
VER=%s
BASE="${XDG_DATA_HOME:-$HOME/.local/share}/universe-os"
PROFILE="$BASE/claude-ruflo"
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
git clone --filter=blob:none --sparse https://github.com/ruvnet/ruflo.git "$STAGE/ruflo"
git -C "$STAGE/ruflo" checkout "$COMMIT"
git -C "$STAGE/ruflo" sparse-checkout set plugins/ruflo-core
test -f "$STAGE/ruflo/plugins/ruflo-core/.claude-plugin/plugin.json"
python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); assert p.get("name")=="ruflo-core"; assert p.get("version")==sys.argv[2]' \\
  "$STAGE/ruflo/plugins/ruflo-core/.claude-plugin/plugin.json" "$VER"
rm -rf "$PROFILE/plugins"
mkdir -p "$PROFILE/plugins"
cp -a "$STAGE/ruflo/plugins/ruflo-core" "$PROFILE/plugins/ruflo-core"
find "$PROFILE/plugins" -mindepth 1 -maxdepth 1 ! -name ruflo-core -exec rm -rf {} +
python3 -c 'import sys; sys.path.insert(0, "/usr/lib/universe-os/claude"); import ruflo_mode; ruflo_mode.prepare_profile()'
echo "Alleen ruflo-core $VER ($COMMIT) staat in het aparte profiel."
echo "Telemetrie, wolk en federatie blijven uit. Geen daemon."
echo "Druk op Enter."; read -r _
''' % (commit, version)


def set_enabled(on):
    import ai_provider
    ai_provider.set_ruflo(bool(on))
    if on:
        prepare_profile()
    return public()


def public():
    on = enabled()
    ready = plugin_ready()
    if on and ready:
        tekst = 'Aan. Eigen profiel, telemetrie uit.'
    elif on:
        tekst = 'Aan, plugin nog niet geïnstalleerd. Tot die tijd blijft de sessie bij Universe.'
    else:
        tekst = 'Uit'
    return {
        'aan': on,
        'geinstalleerd': ready,
        'versie': VERSION,
        'commit': COMMIT,
        'release': RELEASE,
        'profiel': '~/.local/share/universe-os/claude-ruflo',
        'tekst': tekst,
        'waarom': WHY,
        'uitleg': ('Installeert alleen ruflo-core %s, vastgezet op commit %s, in een aparte map. '
                   'Onze wrapper haalt --dangerously-skip-permissions weg. Automatisch toestaan '
                   'blijft de regel van Universe OS.') % (VERSION, COMMIT[:12]),
    }
