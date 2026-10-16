"""System functions behind the Universe interface. Everything runs with the user's normal rights; tasks that need
administrator rights go through pkexec/polkit (universe-admin-helper) or through systemd services that ask polkit.
"""
import collections
import grp
import json
import os
import pwd
import re
import shutil
import subprocess
import time

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk  # noqa: E402

import config  # noqa: E402
import updates  # noqa: E402
import update_channel  # noqa: E402
import audio  # noqa: E402
import app_planets  # noqa: E402
import network_status  # noqa: E402
import chrome_status  # noqa: E402

HELPER = '/usr/lib/universe-os/universe-admin-helper'


def desktop_app(desktop_id):
    """Gio.DesktopAppInfo.new raises TypeError ('constructor returned NULL') for an unknown id in this PyGObject
    instead of returning None; every lookup goes through here so a missing program never breaks a page (10 Oct)."""
    try:
        return Gio.DesktopAppInfo.new(desktop_id)
    except TypeError:
        return None


# Set by webview.webkit_safe_mode for the Universe pages only (software drawing on NVIDIA/unknown graphics).
SOFTWARE_GL_VARS = ('LIBGL_ALWAYS_SOFTWARE', 'GALLIUM_DRIVER', 'WEBKIT_DMABUF_RENDERER_FORCE_SHM')


def program_env():
    """The environment for programs the user starts: with the normal graphics of this pc."""
    return {k: v for k, v in os.environ.items() if k not in SOFTWARE_GL_VARS}


def spawn(args, **kw):
    """Start a program detached from the shell: it keeps running when the shell restarts."""
    if not shutil.which(args[0]) and not os.path.exists(args[0]):
        raise RuntimeError('Programma niet gevonden: %s' % args[0])
    kw.setdefault('env', program_env())
    subprocess.Popen(args, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)


def out(args, timeout=5):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ''


def is_live():
    try:
        return 'boot=live' in open('/proc/cmdline').read()
    except OSError:
        return False


def user_info():
    pw = pwd.getpwuid(os.getuid())
    groups = {grp.getgrgid(g).gr_name for g in os.getgrouplist(pw.pw_name, pw.pw_gid)}
    return {'name': pw.pw_name, 'fullName': pw.pw_gecos.split(',')[0] or pw.pw_name, 'home': pw.pw_dir,
            'admin': 'sudo' in groups, 'live': is_live()}


def full_config():
    return {'settings': config.settings(), 'world': config.world(), 'layout': config.layout(), 'user': user_info()}


# ---------- programs ----------
_theme = None


def icon_uri(icon, size=64):
    global _theme
    if icon is None:
        return None
    if isinstance(icon, Gio.FileIcon):
        path = icon.get_file().get_path()
        return GLib.filename_to_uri(path) if path else None
    if isinstance(icon, Gio.ThemedIcon):
        if _theme is None:
            _theme = Gtk.IconTheme.get_default() or Gtk.IconTheme()
        info = _theme.choose_icon(icon.get_names(), size, Gtk.IconLookupFlags.FORCE_SIZE)
        if info and info.get_filename():
            return GLib.filename_to_uri(info.get_filename())
    return None


HIDDEN_APPS = {'universe-control-center.desktop', 'universe-install.desktop'}


_apps_cache = (0.0, None)


def apps(max_age=120):
    """Installed programs. Cached: every keystroke in the start menu search read all .desktop files and looked up
    256 px icons again. The shell calls apps_changed() when programs are installed or removed."""
    global _apps_cache
    if _apps_cache[1] is None or time.monotonic() - _apps_cache[0] > max_age:
        _apps_cache = (time.monotonic(), _read_apps())
    return _apps_cache[1]


def apps_changed():
    global _apps_cache
    _apps_cache = (0.0, None)


def _read_apps():
    result = []
    for app in Gio.AppInfo.get_all():
        if not isinstance(app, Gio.DesktopAppInfo) or not app.should_show() or app.get_id() in HIDDEN_APPS:
            continue
        cats = [c for c in (app.get_categories() or '').split(';') if c]
        result.append({'id': app.get_id(), 'name': app.get_display_name() or app.get_name(), 'comment': app.get_description() or '',
                       'icon': icon_uri(app.get_icon(), 256), 'categories': cats, 'game': 'Game' in cats,
                       'keywords': ' '.join(app.get_keywords() or [])})
    result.sort(key=lambda a: a['name'].lower())
    return result


def launch(app_id):
    if not re.fullmatch(r'[\w.+-]+\.desktop', app_id or ''):
        raise ValueError('Ongeldig programma')
    if not desktop_app(app_id):
        raise RuntimeError('Dit programma is niet (meer) geïnstalleerd.')
    spawn(['gtk-launch', app_id])


def chrome():
    return chrome_status.read(desktop_app('google-chrome.desktop') is not None)


def browsers():
    default = Gio.AppInfo.get_default_for_type('x-scheme-handler/https', False)
    available = {app.get_id(): app for app in Gio.AppInfo.get_all()
                 if isinstance(app, Gio.DesktopAppInfo) and app.should_show()
                 and ('WebBrowser' in (app.get_categories() or '').split(';')
                      or 'x-scheme-handler/https' in (app.get_supported_types() or []))}
    default_id = default.get_id() if default and default.get_id() in available else None
    return {'default': default_id, 'apps': [
        {'id': key, 'name': app.get_display_name(), 'icon': icon_uri(app.get_icon())}
        for key, app in sorted(available.items(), key=lambda item: item[1].get_display_name().lower())]}


def browser_select(app_id):
    if app_id not in {app['id'] for app in browsers()['apps']}:
        raise ValueError('Deze browser is niet beschikbaar.')
    app = desktop_app(app_id)
    for mime in ('x-scheme-handler/http', 'x-scheme-handler/https', 'text/html'):
        if not app.set_as_default_for_type(mime):
            raise RuntimeError('De standaardbrowser kon niet worden opgeslagen.')
    return browsers()


def desktop_apps():
    path = os.path.join(config.user_dir(), 'app-planets.json')
    installed = apps()
    previous = config.read_json(path, None)
    state = app_planets.reconcile(installed, previous)
    if state != previous:
        config.write_json(path, state)
    by_id = {app['id']: app for app in installed}
    return [by_id[app_id] for app_id in state['planets']]


# ---------- files ----------
PLACES = [('home', 'Persoonlijke map', None), ('documents', 'Documenten', GLib.UserDirectory.DIRECTORY_DOCUMENTS),
          ('downloads', 'Downloads', GLib.UserDirectory.DIRECTORY_DOWNLOAD), ('pictures', 'Afbeeldingen', GLib.UserDirectory.DIRECTORY_PICTURES),
          ('music', 'Muziek', GLib.UserDirectory.DIRECTORY_MUSIC), ('videos', "Video's", GLib.UserDirectory.DIRECTORY_VIDEOS)]


def places():
    GLib.reload_user_special_dirs_cache()
    home = os.path.expanduser('~')
    result = []
    for pid, name, special in PLACES:
        path = home if special is None else (GLib.get_user_special_dir(special) or os.path.join(home, name))
        result.append({'id': pid, 'name': name, 'path': path, 'exists': os.path.isdir(path)})
    result.append({'id': 'trash', 'name': 'Prullenbak', 'path': 'trash:///', 'exists': True})
    return result


def open_path(path):
    if path == 'trash:///':
        return spawn(['thunar', 'trash:///'])
    path = os.path.realpath(os.path.expanduser(path))
    if not os.path.exists(path):
        raise RuntimeError('Bestand of map bestaat niet meer.')
    if not os.access(path, os.R_OK):
        raise PermissionError('Je hebt geen toegang tot dit bestand.')
    if os.path.isdir(path):
        return spawn(['thunar', path])
    spawn(['gio', 'open', path])


# ---------- search (start menu, Claude) ----------
# Faster and more forgiving (Axel, 13 Oct: "finds things better"): one name index of the home folder that is reused for
# a minute instead of a new walk on every keystroke (that walk stopped after 0.8 s, so deep files were never found);
# accents do not matter (e = é), words may come in any order, and one typo in a longer word is still found.
SKIP_DIRS = {'node_modules', '__pycache__', 'snap', 'site-packages', 'venv', '.venv'}
_files_cache = (0.0, None)


def fold(text):
    """Lower case without accents: 'Café Ü' -> 'cafe u'."""
    if text.isascii():
        return text.lower()  # nothing to strip: skips the per-character work for most names
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


def _file_index(max_entries=60000, budget=2.5):
    global _files_cache
    if _files_cache[1] is not None and time.monotonic() - _files_cache[0] < 60:
        return _files_cache[1]
    home = os.path.expanduser('~')
    index, queue, start = [], collections.deque([(home, 0)]), time.monotonic()
    while queue and len(index) < max_entries and time.monotonic() - start < budget:
        folder, depth = queue.popleft()
        try:
            entries = list(os.scandir(folder))
        except OSError:
            continue
        for entry in entries:
            if entry.name.startswith('.') or entry.name in SKIP_DIRS:
                continue
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue
            name = entry.name
            folded = fold(name)
            if folded == name:
                folded = name  # already lower case: keep one string instead of two equal ones
            index.append((folded, name, folder, is_dir, depth))  # folder, not the full path: the folder string is shared
            if is_dir and depth < 8:
                queue.append((entry.path, depth + 1))
    stamp = time.monotonic()
    _files_cache = (stamp, index)
    # One-shot timer: free the index once it is stale. Without it the index stayed in memory until the next search.
    GLib.timeout_add_seconds(61, lambda: _drop_file_index(stamp) or False)
    return index


def _drop_file_index(stamp):
    """Frees the index built at `stamp`, unless a newer one has replaced it (that one has its own timer)."""
    global _files_cache
    if _files_cache[0] == stamp:
        _files_cache = (0.0, None)


def files_changed():
    global _files_cache
    _files_cache = (0.0, None)


def _near(word, text):
    """True if word occurs in text with at most one wrong, missing or extra letter (only for words of 5+ letters)."""
    if word in text:
        return True
    if len(word) < 5:
        return False
    for token in re.split(r'[^a-z0-9]+', text):
        if abs(len(token) - len(word)) > 1 or not token:
            continue
        if len(token) == len(word):
            diff = [k for k in range(len(word)) if word[k] != token[k]]
            if len(diff) == 2 and diff[1] == diff[0] + 1 and word[diff[0]] == token[diff[1]] and word[diff[1]] == token[diff[0]]:
                return True  # two letters swapped: rekenmachien -> rekenmachine
        a, b = (token, word) if len(token) >= len(word) else (word, token)
        i = j = edits = 0
        while i < len(a) and j < len(b):
            if a[i] == b[j]:
                i, j = i + 1, j + 1
                continue
            edits += 1
            if edits > 1:
                break
            if len(a) == len(b):
                j += 1
            i += 1
        if edits + (len(a) - i) + (len(b) - j) <= 1:
            return True
    return False


def _score(words, name, extra='', typos=True):
    """None when not all words match; lower is better (exact start of the name first)."""
    full = name + ' ' + extra
    if not all((_near(w, full) if typos else w in full) for w in words):
        return None
    joined = ' '.join(words)
    return (0 if name.startswith(joined) else 1 if all(w in name for w in words) else 2 if all(w in full for w in words) else 3)


def search_files(query, limit=30):
    """Searches the user's own home folder by name. Only readable entries; hidden folders are skipped."""
    words = fold(query).split()
    if not words:
        return []
    home = os.path.expanduser('~')
    hits = []
    joined = ' '.join(words)
    first, rest = words[0], words[1:]
    join = os.path.join
    for folded, name, folder, is_dir, depth in _file_index():
        # Same ranking as _score(words, folded, typos=False) (words hold no spaces, so only the name can match),
        # without building a string and a generator per name: tens of thousands of names per keystroke.
        if first in folded and all(w in folded for w in rest):
            hits.append((0 if folded.startswith(joined) else 1, depth, len(name), name, join(folder, name), is_dir))
    hits.sort()
    found = []
    for _s, _d, _l, name, path, is_dir in hits:
        if os.access(path, os.R_OK):
            found.append({'name': name, 'path': path, 'dir': is_dir, 'display': '~' + path[len(home):]})
            if len(found) >= limit:
                break
    return found


_folded = (None, None)


def _folded_apps():
    """(app, folded name, folded extra text) per program, folded once per app list instead of on every keystroke."""
    global _folded
    installed = apps()
    if _folded[0] is not installed:
        _folded = (installed, [(a, fold(a['name']), fold(a['comment'] + ' ' + a['keywords'] + ' ' + a['id'])) for a in installed])
    return _folded[1]


def search(query):
    words = fold(query or '').split()
    if not words:
        return {'apps': [], 'files': []}
    ranked = []
    for a, name, extra in _folded_apps():
        score = _score(words, name, extra)
        if score is not None:
            # Desktop settings launchers also match program names; prefer the program.
            ranked.append(('Settings' in a['categories'], score, a['name'].lower(), a))
    ranked.sort(key=lambda r: r[:3])
    return {'apps': [r[3] for r in ranked[:12]], 'files': search_files(query)}


# ---------- status ----------
_network = (0.0, None)


def network(max_age=30):
    """Network state, at most every 30 s: it costs three nmcli processes, and the panel asks every 10 s (in the VM
    those spawns were a large part of the load of a quiet desktop)."""
    global _network
    if _network[1] is None or time.monotonic() - _network[0] > max_age:
        _network = (time.monotonic(), network_status.status())
    return _network[1]


def volume():
    text = out(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'])
    m = re.search(r'Volume:\s*([\d.]+)', text)
    if not m:
        return None
    return {'level': round(float(m.group(1)) * 100), 'muted': 'MUTED' in text}


def battery():
    base = '/sys/class/power_supply'
    try:
        for name in sorted(os.listdir(base)):
            path = os.path.join(base, name)
            try:
                if open(os.path.join(path, 'type')).read().strip() != 'Battery':
                    continue
                cap = int(open(os.path.join(path, 'capacity')).read().strip())
                state = open(os.path.join(path, 'status')).read().strip()
            except (OSError, ValueError):
                continue
            names = {'Charging': 'Opladen', 'Discharging': 'Op batterij', 'Full': 'Vol', 'Not charging': 'Laadt niet op'}
            return {'present': True, 'percent': cap, 'charging': state == 'Charging', 'state': names.get(state, state)}
    except OSError:
        pass
    return {'present': False}


_cleared = 0


def notifications():
    text = out(['makoctl', 'history'])
    items = []
    try:  # older mako: JSON
        data = json.loads(text)
        for group in data.get('data', []):
            for n in group:
                items.append({'id': int(n.get('id', {}).get('data', 0)), 'app': n.get('app-name', {}).get('data', ''),
                              'summary': n.get('summary', {}).get('data', ''), 'body': n.get('body', {}).get('data', '')})
    except ValueError:  # mako >= 1.9: text blocks "Notification 3: summary" + indented fields
        current = None
        for line in text.splitlines():
            m = re.match(r'Notification (\d+): (.*)', line)
            if m:
                current = {'id': int(m.group(1)), 'summary': m.group(2), 'app': '', 'body': ''}
                items.append(current)
            elif current and line.strip().startswith('App name:'):
                current['app'] = line.split(':', 1)[1].strip()
            elif current and line.strip() and not re.match(r'\s+\w[\w ]*:', line):
                current['body'] = (current['body'] + ' ' + line.strip()).strip()
    items = [n for n in items if n['id'] > _cleared]
    items.sort(key=lambda n: -n['id'])
    return items


def clear_notifications():
    global _cleared
    items = notifications()
    if items:
        _cleared = max(n['id'] for n in items)
    out(['makoctl', 'dismiss', '--all'])


def can_suspend():
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        res = bus.call_sync('org.freedesktop.login1', '/org/freedesktop/login1', 'org.freedesktop.login1.Manager', 'CanSuspend',
                            None, GLib.VariantType('(s)'), Gio.DBusCallFlags.NONE, 2000, None)
        return res.unpack()[0] in ('yes', 'challenge')
    except GLib.Error:
        return False


def status():
    return {'network': network(), 'volume': volume(), 'battery': battery(), 'notifications': notifications()[:20],
            'rebootRequired': os.path.exists('/run/reboot-required'), 'canSuspend': can_suspend()}


def set_volume(level):
    level = max(0, min(100, int(level)))
    subprocess.run(['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', '%d%%' % level], check=False)


def volume_ping():
    """Like Windows: when the slider is let go, a short tune at the new volume (also remembers the volume for the
    login screen, see universe-geluid)."""
    sound('volume')
    return True


def toggle_mute():
    subprocess.run(['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle'], check=False)
    sound('volume')


def sound(name):
    """A Universe system sound (universe-geluid; silent when Systeemgeluiden is off). Never fails."""
    try:
        spawn(['universe-geluid', name])
    except (OSError, RuntimeError):
        pass


def power(action, sound_first=True):
    if action == 'lock':
        return spawn(['universe-lock'])
    if action == 'logout':
        return spawn(['labwc', '--exit'])
    if action in ('reboot', 'poweroff', 'suspend'):
        if action != 'suspend' and sound_first:
            subprocess.run(['universe-geluid', 'afsluiten', '--wacht'], timeout=10, check=False)  # like Windows: first the sound
        r = subprocess.run(['systemctl', action], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise RuntimeError('De energieactie is mislukt.' +
                               (' Technische melding: ' + r.stderr.strip() if r.stderr.strip() else ''))
        return
    raise ValueError('Onbekende actie')


def updates_status():
    return updates.status()


# ---------- tools ----------
def run_tool(tool, args):
    if tool == 'files':
        return spawn(['thunar'] + ([args['path']] if args.get('path') else []))
    if tool == 'terminal':
        return spawn(['xfce4-terminal'])
    if tool == 'monitor':
        return spawn(['gnome-system-monitor', '-p'])
    if tool == 'software':
        cmd = ['gnome-software']
        if args.get('mode') in ('updates', 'installed', 'overview'):
            cmd.append('--mode=%s' % args['mode'])
        if args.get('search'):
            cmd.append('--search=%s' % args['search'])
        return spawn(cmd)
    if tool == 'deb':
        return spawn(['universe-install-deb'])
    if tool == 'control':
        if not os.path.exists('/usr/share/universe-os/ui/control.html'):
            raise RuntimeError('Het Controlecentrum is nog in aanbouw; deze instelling kan nog niet worden geopend.')
        page = args.get('page') or ''
        return spawn(['universe-control-center'] + (['--pagina', page] if re.fullmatch(r'[a-z]+', page) else []))
    if tool == 'installer':
        if not is_live():
            raise RuntimeError('Installeren kan alleen vanaf de live-USB.')
        return spawn(['universe-install'])
    if tool in ('network-editor', 'pavucontrol', 'wdisplays', 'blueman-manager'):
        cmd = {'network-editor': 'nm-connection-editor'}.get(tool, tool)
        return spawn([cmd])
    raise ValueError('Onbekend hulpmiddel: %s' % tool)


def pick_path(kind):
    """Lets the user choose a folder or file to put in the space world (native dialog via zenity). None = cancelled."""
    cmd = ['zenity', '--file-selection', '--title', 'Map kiezen' if kind == 'folder' else 'Bestand kiezen',
           '--filename', os.path.expanduser('~') + '/']
    if kind == 'folder':
        cmd.append('--directory')
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError('Kiezen lukt niet: %s' % error)
    path = result.stdout.strip()
    if result.returncode != 0 or not path:
        return None
    return {'path': path, 'name': os.path.basename(path.rstrip('/')) or path}


# ---------- desktop (like Windows: the Bureaublad folder plus fixed icons and shortcuts) ----------
def desktop_dir():
    GLib.reload_user_special_dirs_cache()
    return GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP) or os.path.join(os.path.expanduser('~'), 'Bureaublad')


def _themed(*names):
    return icon_uri(Gio.ThemedIcon.new_from_names(list(names)))


def _file_entry(path, key, source):
    gfile = Gio.File.new_for_path(path)
    try:
        info = gfile.query_info('standard::icon,standard::display-name,standard::type', Gio.FileQueryInfoFlags.NONE, None)
    except GLib.Error:
        return None
    folder = info.get_file_type() == Gio.FileType.DIRECTORY
    entry = {'key': key, 'name': info.get_display_name(), 'kind': 'folder' if folder else 'file', 'target': path,
             'icon': icon_uri(info.get_icon()), 'source': source}
    if not folder and path.endswith('.desktop'):
        app = Gio.DesktopAppInfo.new_from_filename(path)
        if app:
            entry.update(kind='launcher', name=app.get_display_name(), icon=icon_uri(app.get_icon(), 256))
    return entry


def _trash_full():
    try:
        info = Gio.File.new_for_uri('trash:///').query_info('trash::item-count', Gio.FileQueryInfoFlags.NONE, None)
        return info.get_attribute_uint32('trash::item-count') > 0
    except GLib.Error:
        return False


def desktop_list():
    """Everything on the desktop: fixed icons, the files in the Bureaublad folder and the user's shortcuts."""
    lay = config.layout()
    hidden = set(lay.get('hiddenIcons') or [])
    home = os.path.expanduser('~')
    entries = []
    if is_live():
        entries.append({'key': 'sys:install', 'name': 'Universe OS installeren', 'kind': 'install', 'target': '', 'icon': _themed('system-software-install', 'system-installer'), 'source': 'system'})
    if 'sys:home' not in hidden:
        entries.append({'key': 'sys:home', 'name': 'Persoonlijke map', 'kind': 'folder', 'target': home, 'icon': _themed('user-home', 'folder'), 'source': 'system'})
    if 'sys:trash' not in hidden:
        entries.append({'key': 'sys:trash', 'name': 'Prullenbak', 'kind': 'folder', 'target': 'trash:///',
                        'icon': _themed('user-trash-full' if _trash_full() else 'user-trash', 'user-trash'), 'source': 'system'})
    folder = desktop_dir()
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder), key=str.lower)[:300]:
            if name.startswith('.'):
                continue
            entry = _file_entry(os.path.join(folder, name), 'f:' + name, 'desktop')
            if entry:
                entries.append(entry)
    for item in lay.get('items') or []:
        if item['kind'] == 'app':
            app = desktop_app(item['target'])
            if not app:
                continue
            entries.append({'key': item['id'], 'name': app.get_display_name(), 'kind': 'app', 'target': item['target'],
                            'icon': icon_uri(app.get_icon(), 256), 'source': 'shortcut'})
        elif os.path.exists(item['target']):
            entry = _file_entry(item['target'], item['id'], 'shortcut')
            if entry:
                entries.append(entry)
    return {'dir': folder, 'entries': entries}


def _in_desktop(path):
    folder = os.path.realpath(desktop_dir())
    real = os.path.realpath(os.path.dirname(path.rstrip('/')))
    if real != folder:
        raise PermissionError('Dit kan alleen voor bestanden op het bureaublad.')
    return path


def _valid_name(name):
    name = (name or '').strip()
    if not name or name in ('.', '..') or '/' in name or '\0' in name or len(name.encode()) > 255:
        raise ValueError('Deze naam kan niet: geen / gebruiken en niet leeg laten.')
    return name


def desktop_mkdir():
    folder = desktop_dir()
    os.makedirs(folder, exist_ok=True)
    name, n = 'Nieuwe map', 1
    while os.path.exists(os.path.join(folder, name)):
        n += 1
        name = 'Nieuwe map (%d)' % n
    os.mkdir(os.path.join(folder, name))
    return {'key': 'f:' + name, 'path': os.path.join(folder, name)}


def desktop_rename(path, name):
    path = _in_desktop(path)
    name = _valid_name(name)
    target = os.path.join(os.path.dirname(path), name)
    if os.path.exists(target):
        raise FileExistsError('Er staat al iets met de naam "%s" op het bureaublad.' % name)
    os.rename(path, target)
    return {'key': 'f:' + name}


def desktop_trash(path):
    Gio.File.new_for_path(_in_desktop(path)).trash(None)
    sound('prullenbak')
    return True


def desktop_launch(path):
    """Starts a .desktop launcher that lies on the desktop (like a shortcut on the Windows desktop)."""
    path = _in_desktop(path)
    if not os.access(path, os.X_OK):
        # Like GNOME: a launcher only runs when the user marked it as trusted (executable), so a downloaded file
        # cannot start a program by itself.
        raise PermissionError('Deze snelkoppeling is niet vertrouwd. Maak haar uitvoerbaar in Bestanden (Eigenschappen > Rechten).')
    app = Gio.DesktopAppInfo.new_from_filename(path)
    if not app:
        raise RuntimeError('Deze snelkoppeling werkt niet.')
    context = Gio.AppLaunchContext()
    for name in SOFTWARE_GL_VARS:
        context.unsetenv(name)
    app.launch([], context)
    return True
