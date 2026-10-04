"""Windows programs via Wine, one Wine environment (prefix) per program per user.

Layout (all inside the user's own home, mode 0700):
  ~/.local/share/universe-os/wine/<slug>/app.json     name, installer, status, shortcuts
  ~/.local/share/universe-os/wine/<slug>/prefix/      the Wine environment (C: drive, registry, saved data)
  ~/.local/share/universe-os/wine/<slug>/icons/       icons of the shortcuts
  ~/.local/state/universe-os/wine/<slug>/*.log        technical logs (installation and starts)
  ~/.local/share/applications/universe-wine-<slug>-<n>.desktop   shortcuts for the Universe app system

A separate prefix keeps settings and dependencies of programs apart. It is NOT a security sandbox: a Windows
program can read everything the user can read. Windows programs never run as root.
"""
import datetime
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import struct
import subprocess
import time

from gi.repository import GLib

APPS_DIR = os.path.join(GLib.get_user_data_dir(), 'applications')
NOT_A_SANDBOX = ('Een aparte Wine-omgeving houdt instellingen en onderdelen van programma\'s gescheiden, maar is geen beveiligde '
                 'sandbox: een Windows-programma kan alles lezen wat jij kunt lezen. Installeer alleen programma\'s die je vertrouwt.')
MACHINES = {0x14c: ('32', '32-bit (x86)'), 0x8664: ('64', '64-bit (x86-64)'), 0xaa64: ('arm', 'ARM64'), 0x1c4: ('arm', 'ARM (32-bit)'), 0x200: ('ia64', 'Itanium')}
SKIP_SHORTCUT = re.compile(r'uninstall|unins\d*|verwijder|deinstall|readme|lees mij|help|website|homepage|license|licentie', re.I)


class WineError(RuntimeError):
    """An error with a message for the user (Dutch); technical details are in the log."""


def base_dir():
    path = os.path.join(GLib.get_user_data_dir(), 'universe-os', 'wine')
    os.makedirs(path, mode=0o700, exist_ok=True)
    os.chmod(os.path.join(GLib.get_user_data_dir(), 'universe-os'), 0o700)
    return path


def log_dir(slug):
    path = os.path.join(GLib.get_user_state_dir(), 'universe-os', 'wine', slug)
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path


def refuse_root():
    if os.geteuid() == 0 or os.environ.get('SUDO_USER') or os.environ.get('PKEXEC_UID'):
        raise WineError('Windows-programma\'s worden nooit als beheerder (root) uitgevoerd. Start dit als gewone gebruiker.')


# ---------- what is supported ----------
def support():
    version = ''
    try:
        version = subprocess.run(['wine', '--version'], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    has64 = os.path.exists('/usr/lib/wine/wine64')
    has32 = os.path.exists('/usr/lib/wine/wine') or os.path.exists('/usr/lib/i386-linux-gnu/wine/wine')
    machine = os.uname().machine
    notes = []
    if not version:
        notes.append('Wine is niet geïnstalleerd. Windows-programma\'s kunnen niet worden uitgevoerd.')
    if machine != 'x86_64':
        notes.append('Deze computer heeft geen x86-64-processor (%s); Wine voert hier geen Windows-programma\'s voor pc uit.' % machine)
    if version and not has64:
        notes.append('64-bit Windows-programma\'s worden niet ondersteund: het pakket wine64 ontbreekt.')
    if version and not has32:
        notes.append('32-bit Windows-programma\'s worden niet ondersteund: het pakket wine32 (i386) ontbreekt.')
    notes.append('Windows-programma\'s voor ARM worden niet ondersteund.')
    notes.append('.NET-programma\'s hebben Wine Mono nodig en webinhoud in programma\'s Wine Gecko. Die worden alleen op jouw verzoek gedownload (internet nodig).')
    return {'wine': version, 'win64': has64 and machine == 'x86_64', 'win32': has32 and machine == 'x86_64', 'cpu': machine,
            'msitools': bool(shutil.which('msiinfo')), 'notes': notes, 'sandbox': NOT_A_SANDBOX}


# ---------- installer files ----------
def file_info(path):
    """What would be executed: name, folder, size, checksum, type and processor architecture."""
    path = os.path.realpath(path)
    if not os.path.isfile(path):
        raise WineError('Het bestand bestaat niet (meer): %s' % path)
    if not os.access(path, os.R_OK):
        raise WineError('Je hebt geen leesrechten op dit bestand.')
    st = os.stat(path)
    sha = hashlib.sha256()
    with open(path, 'rb') as f:
        head = f.read(4096)
        sha.update(head)
        for chunk in iter(lambda: f.read(1 << 20), b''):
            sha.update(chunk)
    kind, arch, arch_text = 'onbekend', None, 'onbekend'
    if head[:2] == b'MZ' and len(head) >= 0x40:
        kind = 'exe'
        offset = struct.unpack_from('<I', head, 0x3c)[0]
        try:
            with open(path, 'rb') as f:
                f.seek(offset)
                pe = f.read(6)
            if pe[:4] == b'PE\0\0':
                arch, arch_text = MACHINES.get(struct.unpack_from('<H', pe, 4)[0], ('?', 'onbekende processor'))
            else:
                arch, arch_text = 'dos', 'MS-DOS-programma (niet ondersteund)'
        except (OSError, struct.error):
            pass
    elif head[:8] == bytes.fromhex('d0cf11e0a1b11ae1'):
        kind = 'msi'
        template = ''
        if shutil.which('msiinfo'):
            text = subprocess.run(['msiinfo', 'suminfo', path], capture_output=True, text=True).stdout
            m = re.search(r'Template:\s*(\S+)', text)
            template = m.group(1) if m else ''
        if template.startswith(('x64', 'Intel64', 'AMD64')):
            arch, arch_text = '64', '64-bit Windows Installer-pakket'
        elif template.startswith('Intel'):
            arch, arch_text = '32', '32-bit Windows Installer-pakket'
        elif template.startswith('Arm64'):
            arch, arch_text = 'arm', 'ARM64 Windows Installer-pakket'
        else:
            arch, arch_text = None, 'Windows Installer-pakket (architectuur niet vast te stellen)'
    downloads = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) or ''
    return {'path': path, 'name': os.path.basename(path), 'folder': os.path.dirname(path), 'size': st.st_size,
            'modified': datetime.datetime.fromtimestamp(st.st_mtime).strftime('%d-%m-%Y %H:%M'), 'sha256': sha.hexdigest(),
            'kind': kind, 'arch': arch, 'archText': arch_text,
            'downloaded': bool(downloads) and path.startswith(downloads + os.sep),
            'executableBit': bool(st.st_mode & 0o111)}


def check_supported(info, sup=None):
    sup = sup or support()
    if not sup['wine']:
        raise WineError('Wine is niet geïnstalleerd, dus dit Windows-programma kan niet worden geïnstalleerd.')
    if info['kind'] not in ('exe', 'msi'):
        raise WineError('Dit is geen Windows-programma of Windows Installer-pakket (.exe of .msi).')
    if info['arch'] in ('arm', 'ia64', 'dos', '?'):
        raise WineError('Dit programma is gemaakt voor %s. Dat wordt niet ondersteund.' % info['archText'])
    if info['arch'] == '64' and not sup['win64']:
        raise WineError('Dit is een 64-bit Windows-programma, maar 64-bit-ondersteuning (wine64) ontbreekt.')
    if info['arch'] == '32' and not sup['win32']:
        raise WineError('Dit is een 32-bit Windows-programma, maar 32-bit-ondersteuning (wine32) ontbreekt op dit systeem.')


# ---------- program records ----------
def slugify(name):
    base = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:40] or 'programma'
    slug, n = base, 2
    while os.path.exists(os.path.join(base_dir(), slug)):
        slug, n = '%s-%d' % (base, n), n + 1
    return slug


def app_dir(slug):
    if not re.fullmatch(r'[a-z0-9-]{1,48}', slug or ''):
        raise WineError('Ongeldige programmanaam.')
    return os.path.join(base_dir(), slug)


def load(slug):
    try:
        with open(os.path.join(app_dir(slug), 'app.json'), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        raise WineError('Dit Windows-programma is niet gevonden.')


def save(app):
    path = os.path.join(app_dir(app['slug']), 'app.json')
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(app, f, ensure_ascii=False, indent=2)
    os.replace(path + '.tmp', path)


def list_apps():
    result = []
    for path in sorted(glob.glob(os.path.join(base_dir(), '*', 'app.json'))):
        try:
            with open(path, encoding='utf-8') as f:
                result.append(json.load(f))
        except (OSError, ValueError):
            continue
    return result


def environment(app, extra=None):
    env = dict(os.environ)
    env.update({'WINEPREFIX': os.path.join(app_dir(app['slug']), 'prefix'), 'WINEARCH': app.get('winearch', 'win64'),
                'WINEDEBUG': 'fixme-all', 'LANG': os.environ.get('LANG', 'nl_NL.UTF-8')})
    if not app.get('components', {}).get('mono'):
        env['WINEDLLOVERRIDES'] = 'mscoree,mshtml='  # no download dialog for Mono/Gecko unless the user asks
    env.update(extra or {})
    return env


def _log_file(slug, kind):
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    folder = log_dir(slug)
    logs = sorted(glob.glob(os.path.join(folder, kind + '-*.log')))
    for old in logs[:-9]:  # keep the last 10 per kind
        os.unlink(old)
    return os.path.join(folder, '%s-%s.log' % (kind, stamp))


def _notify(summary, body, urgency='normal'):
    subprocess.run(['notify-send', '-u', urgency, '-a', 'Windows-programma\'s', summary, body], capture_output=True)


def _apps_changed():
    subprocess.run(['update-desktop-database', '-q', APPS_DIR], capture_output=True)
    subprocess.run(['universe-ctl', 'apps-changed'], capture_output=True)


# ---------- installation ----------
def install(path, name, progress=print):
    """Install a Windows program into its own new Wine environment. Called only after the user confirmed the file."""
    refuse_root()
    info = file_info(path)
    sup = support()
    check_supported(info, sup)
    name = (name or os.path.splitext(info['name'])[0]).strip()[:60]
    slug = slugify(name)
    folder = app_dir(slug)
    os.makedirs(os.path.join(folder, 'icons'), mode=0o700)
    app = {'slug': slug, 'name': name, 'created': datetime.datetime.now().isoformat(timespec='seconds'),
           'installer': {k: info[k] for k in ('path', 'name', 'sha256', 'kind', 'arch', 'archText', 'size')},
           'winearch': 'win64' if sup['win64'] else 'win32', 'wine': sup['wine'], 'install': {'status': 'bezig'},
           'run': {'status': 'niet-getest'}, 'entries': [], 'components': {}}
    save(app)
    log = _log_file(slug, 'installatie')
    # Shortcuts made by Wine (winemenubuilder) go to a staging area first; Universe makes its own from them.
    stage = os.path.join(folder, 'menu-staging')
    for sub in ('data', 'config', 'desktop'):
        os.makedirs(os.path.join(stage, sub), exist_ok=True)
    with open(os.path.join(stage, 'config', 'user-dirs.dirs'), 'w') as f:
        f.write('XDG_DESKTOP_DIR="%s"\n' % os.path.join(stage, 'desktop'))
    env = environment(app, {'XDG_DATA_HOME': os.path.join(stage, 'data'), 'XDG_CONFIG_HOME': os.path.join(stage, 'config')})
    started = time.time()
    with open(log, 'w', encoding='utf-8', errors='replace') as out:
        out.write('Universe OS installatie van %s\nBestand: %s\nSHA-256: %s\nType: %s\n%s\n\n' % (name, info['path'], info['sha256'], info['archText'], sup['wine']))
        out.flush()
        progress({'stap': 'omgeving', 'tekst': 'Nieuwe Wine-omgeving voorbereiden…'})
        r = subprocess.run(['wineboot', '-i'], env=env, stdout=out, stderr=subprocess.STDOUT)
        subprocess.run(['wineserver', '-w'], env=env, stdout=out, stderr=subprocess.STDOUT)
        if r.returncode != 0:
            app['install'] = {'status': 'mislukt', 'reden': 'De Wine-omgeving kon niet worden aangemaakt.', 'log': log}
            save(app)
            raise WineError(app['install']['reden'] + ' Technische details: ' + log)
        progress({'stap': 'installeren', 'tekst': 'Het installatieprogramma draait. Volg de stappen in het venster van het installatieprogramma.'})
        if info['kind'] == 'msi':
            cmd = ['wine', 'msiexec', '/i', info['path']]
        else:
            cmd = ['wine', info['path']]
        out.write('\n$ %s\n' % ' '.join(shlex.quote(c) for c in cmd))
        out.flush()
        r = subprocess.run(cmd, env=env, stdout=out, stderr=subprocess.STDOUT, cwd=info['folder'])
        subprocess.run(['wineserver', '-w'], env=env, stdout=out, stderr=subprocess.STDOUT)
        out.write('\nAfsluitcode installatieprogramma: %s (na %.0f s)\n' % (r.returncode, time.time() - started))
    entries = collect_shortcuts(app, stage)
    shutil.rmtree(stage, ignore_errors=True)
    app['entries'] = entries
    if r.returncode not in (0, 3010):  # 3010 = success, restart required (msiexec)
        status, reason = 'mislukt', 'Het installatieprogramma is gestopt met foutcode %s. Mogelijk werkt dit programma niet met Wine, of is de installatie geannuleerd.' % r.returncode
    elif not entries:
        status, reason = 'geen-snelkoppeling', 'De installatie is afgerond, maar er is geen programma-snelkoppeling gevonden. Kies het programmabestand in het beheerscherm.'
    else:
        status, reason = 'geslaagd', 'De installatie is afgerond. Of het programma goed werkt, blijkt pas bij gebruik.'
    app['install'] = {'status': status, 'reden': reason, 'log': log, 'code': r.returncode}
    app['candidates'] = find_executables(app) if status != 'geslaagd' else []
    save(app)
    write_desktop_files(app)
    progress({'stap': 'klaar', 'status': status, 'tekst': reason, 'slug': slug})
    return app


def _windows_to_unix(app, value):
    """C:\\x\\y -> path inside this program's prefix (only drive C is used)."""
    m = re.match(r'^[cC]:[\\/](.*)$', value)
    if not m:
        return None
    return os.path.join(app_dir(app['slug']), 'prefix', 'drive_c', *re.split(r'[\\/]+', m.group(1)))


def collect_shortcuts(app, stage):
    files = glob.glob(os.path.join(stage, 'data', 'applications', 'wine', '**', '*.desktop'), recursive=True)
    files += glob.glob(os.path.join(stage, 'desktop', '*.desktop'))
    entries, seen = [], set()
    for path in files:
        kf = GLib.KeyFile()
        try:
            kf.load_from_file(path, GLib.KeyFileFlags.NONE)
            name = kf.get_string('Desktop Entry', 'Name')
            exec_line = kf.get_string('Desktop Entry', 'Exec')
        except GLib.Error:
            continue
        if SKIP_SHORTCUT.search(name):
            continue
        try:
            argv = shlex.split(exec_line)
        except ValueError:
            continue
        if 'wine' not in argv:
            continue
        args = argv[argv.index('wine') + 1:]
        if not args or (args[0], name) in seen:
            continue
        seen.add((args[0], name))
        icon = None
        try:
            icon_name = kf.get_string('Desktop Entry', 'Icon')
            found = sorted(glob.glob(os.path.join(stage, 'data', 'icons', '**', icon_name + '.png'), recursive=True),
                           key=lambda p: -os.path.getsize(p))
            if found:
                icon = os.path.join(app_dir(app['slug']), 'icons', '%d.png' % len(entries))
                shutil.copy(found[0], icon)
        except GLib.Error:
            pass
        workdir = None
        try:
            workdir = kf.get_string('Desktop Entry', 'Path')
        except GLib.Error:
            pass
        wm = kf.get_string('Desktop Entry', 'StartupWMClass') if kf.has_key('Desktop Entry', 'StartupWMClass') else ''
        entries.append({'name': name, 'args': args, 'workdir': workdir, 'icon': icon, 'wmclass': wm})
    return entries


def find_executables(app):
    """Program files the user can choose when the installer made no shortcut."""
    drive = os.path.join(app_dir(app['slug']), 'prefix', 'drive_c')
    result = []
    for root in ('Program Files', 'Program Files (x86)', 'users'):
        for path in glob.glob(os.path.join(drive, root, '**', '*.exe'), recursive=True):
            rel = os.path.relpath(path, drive)
            if SKIP_SHORTCUT.search(os.path.basename(path)) or os.sep + 'Temp' + os.sep in path:
                continue
            if rel.startswith('users') and 'AppData' not in rel:
                continue
            result.append('C:\\' + rel.replace(os.sep, '\\'))
    return sorted(result)[:40]


def choose_executable(slug, windows_path):
    app = load(slug)
    unix = _windows_to_unix(app, windows_path)
    if not unix or not os.path.isfile(unix):
        raise WineError('Dit programmabestand bestaat niet in de Wine-omgeving van dit programma.')
    app['entries'].append({'name': app['name'], 'args': [windows_path], 'workdir': os.path.dirname(unix), 'icon': None,
                           'wmclass': os.path.basename(unix).lower()})
    if app['install']['status'] == 'geen-snelkoppeling':
        app['install']['status'] = 'geslaagd'
        app['install']['reden'] = 'De installatie is afgerond; het programmabestand is handmatig gekozen.'
    save(app)
    write_desktop_files(app)
    return app


def _desktop_escape(value):
    return value.replace('\\', '\\\\').replace('\n', ' ')


def write_desktop_files(app):
    os.makedirs(APPS_DIR, exist_ok=True)
    for old in glob.glob(os.path.join(APPS_DIR, 'universe-wine-%s-*.desktop' % app['slug'])):
        os.unlink(old)
    for i, entry in enumerate(app['entries']):
        lines = ['[Desktop Entry]', 'Type=Application', 'Name=%s' % _desktop_escape(entry['name']),
                 'Comment=Windows-programma (Wine) — %s' % _desktop_escape(app['name']),
                 'Exec=universe-wine start %s %d' % (app['slug'], i),
                 'Icon=%s' % (entry['icon'] or 'wine'), 'Categories=X-Universe-Windows;', 'Keywords=windows;wine;',
                 'X-Universe-Wine=%s' % app['slug'], 'StartupNotify=false']
        if entry.get('wmclass'):
            lines.append('StartupWMClass=%s' % entry['wmclass'])
        path = os.path.join(APPS_DIR, 'universe-wine-%s-%d.desktop' % (app['slug'], i))
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    _apps_changed()


# ---------- starting ----------
def start(slug, index=0):
    """Start a program (called by its shortcut). Waits until the program has ended to judge the result."""
    refuse_root()
    app = load(slug)
    if not app['entries']:
        raise WineError('Er is nog geen programmabestand gekozen voor %s.' % app['name'])
    entry = app['entries'][min(int(index), len(app['entries']) - 1)]
    env = environment(app)
    args = list(entry['args'])
    if args[0].lower().endswith('.lnk'):
        args = ['start', '/wait'] + args
    cmd = ['wine'] + args
    workdir = entry.get('workdir') if entry.get('workdir') and os.path.isdir(entry['workdir']) else os.path.join(app_dir(slug), 'prefix', 'drive_c')
    log = _log_file(slug, 'start')
    started = time.time()
    with open(log, 'w', encoding='utf-8', errors='replace') as out:
        out.write('Start %s (%s)\n$ %s\nWine-omgeving: %s\n\n' % (entry['name'], app['name'], ' '.join(shlex.quote(c) for c in cmd), env['WINEPREFIX']))
        out.flush()
        try:
            r = subprocess.run(cmd, env=env, cwd=workdir, stdout=out, stderr=subprocess.STDOUT)
            subprocess.run(['wineserver', '-w'], env=env, stdout=out, stderr=subprocess.STDOUT)
            code = r.returncode
        except OSError as error:
            out.write('Kon wine niet starten: %s\n' % error)
            code = 127
        duration = time.time() - started
        out.write('\nAfsluitcode: %s na %.0f seconden\n' % (code, duration))
    app = load(slug)
    run = {'last': datetime.datetime.now().isoformat(timespec='seconds'), 'code': code, 'seconds': round(duration), 'log': log,
           'verdict': app['run'].get('verdict')}
    if code == 127:
        run['status'] = 'start-mislukt'
        _notify('%s kon niet starten' % entry['name'], 'Wine is niet gevonden of kon niet worden uitgevoerd. Logboek: %s' % log, 'critical')
    elif code != 0 and duration < 15:
        run['status'] = 'fout'
        _notify('%s is direct gestopt' % entry['name'],
                'Het Windows-programma stopte met foutcode %s. Mogelijk werkt het niet (goed) met Wine. Logboek: %s' % (code, log), 'critical')
    else:
        run['status'] = 'gestart'
    app['run'] = run
    save(app)
    return run


def set_verdict(slug, verdict):
    if verdict not in ('werkt', 'problemen', None):
        raise WineError('Ongeldige keuze')
    app = load(slug)
    app['run']['verdict'] = verdict
    save(app)
    return app


def enable_mono(slug):
    """Allow Wine to offer Wine Mono / Gecko (downloaded by Wine itself after the user agrees in Wine's dialog)."""
    app = load(slug)
    app.setdefault('components', {})['mono'] = True
    save(app)
    log = _log_file(slug, 'componenten')
    with open(log, 'w') as out:
        subprocess.run(['wineboot', '-u'], env=environment(app), stdout=out, stderr=subprocess.STDOUT)
        subprocess.run(['wineserver', '-w'], env=environment(app), stdout=out, stderr=subprocess.STDOUT)
    return load(slug)


def winecfg(slug):
    app = load(slug)
    subprocess.Popen(['winecfg'], env=environment(app), start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------- removing ----------
def remove(slug, wipe_data=False):
    """Remove a program. Without wipe_data the user's saved data (C:\\users\\<naam>) is kept in wine-bewaard."""
    refuse_root()
    app = load(slug)
    folder = app_dir(slug)
    prefix = os.path.join(folder, 'prefix')
    subprocess.run(['wineserver', '-k'], env=environment(app), capture_output=True, timeout=30)
    kept = None
    if not wipe_data:
        user_data = os.path.join(prefix, 'drive_c', 'users', os.environ.get('USER', ''))
        if os.path.isdir(user_data):
            kept = os.path.join(GLib.get_user_data_dir(), 'universe-os', 'wine-bewaard', '%s-%s' % (slug, datetime.datetime.now().strftime('%Y%m%d-%H%M%S')))
            os.makedirs(os.path.dirname(kept), mode=0o700, exist_ok=True)
            # Wine links Documents etc. to the real home folders: copy only real data, never follow links.
            shutil.copytree(user_data, kept, symlinks=True)
    for path in glob.glob(os.path.join(APPS_DIR, 'universe-wine-%s-*.desktop' % slug)):
        os.unlink(path)
    shutil.rmtree(folder, ignore_errors=True)
    if wipe_data:
        shutil.rmtree(log_dir(slug), ignore_errors=True)
    _apps_changed()
    return {'kept': kept}
