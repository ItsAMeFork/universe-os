"""Controlecentrum: system settings of Universe OS as a normal window (one instance; --pagina opens a page)."""
import json
import os
import pty
import pwd
import grp
import re
import select
import shutil
import subprocess
import sys
import time

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backend  # noqa: E402
import config  # noqa: E402
import session  # noqa: E402
from webview import Bridge, emit, make_view  # noqa: E402

def _claude():
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'claude')
    if folder not in sys.path:
        sys.path.insert(0, folder)
    return folder


def _brein():
    _claude()
    import brein
    return brein


def _accounts():
    _claude()
    import accounts
    return accounts


def _screen():
    _claude()
    import screen
    return screen


def _ai():
    _claude()
    import ai_provider
    return ai_provider


def _plugins():
    _claude()
    import plugins
    return plugins


def _shell_json(command, timeout=8):
    """Ask the running shell. Screen control lives there, not in a file this process could write."""
    done = subprocess.run(['universe-ctl', command], capture_output=True, text=True, timeout=timeout)
    text = (done.stdout or '').strip()
    if text.startswith('ok '):
        try:
            data = json.loads(text[3:])
        except ValueError:
            data = None
        if isinstance(data, dict):
            return data
    if text == 'ok':
        return _screen().status()
    message = text[6:] if text.startswith('fout: ') else text
    raise RuntimeError(message or 'De shell gaf geen antwoord.')


def _grant_screen(on):
    # Turning it on shows a dialog in the shell. This process must not flip the switch itself.
    return _shell_json('scherm-aan' if on else 'scherm-uit', timeout=200)


def _screen_status_for_ui():
    try:
        return _shell_json('scherm')
    except (RuntimeError, OSError, subprocess.SubprocessError):
        state = _screen().status()
        state['toegestaan'] = False
        return state


def _oauth_start(args):
    result = _accounts().start_oauth(args.get('provider'), args.get('methode') or 'loopback', args.get('client_id') or '', args.get('client_secret') or None)
    url = result.get('url') or result.get('verificatie') or ''
    if str(url).startswith('http'):
        backend.spawn(['xdg-open', url])
    return result


def _download_dir():
    try:
        out = subprocess.run(['xdg-user-dir', 'DOWNLOAD'], capture_output=True, text=True, timeout=2)
        folder = out.stdout.strip()
        if out.returncode == 0 and folder and os.path.isdir(os.path.dirname(folder) or folder):
            return folder
    except (OSError, subprocess.SubprocessError):
        pass
    return os.path.join(os.path.expanduser('~'), 'Downloads')


HELPER = '/usr/lib/universe-os/universe-admin-helper'
LANGUAGES = [('nl_NL.UTF-8', 'Nederlands (Nederland)'), ('nl_BE.UTF-8', 'Nederlands (België)'), ('en_US.UTF-8', 'English (United States)'),
             ('en_GB.UTF-8', 'English (United Kingdom)'), ('de_DE.UTF-8', 'Deutsch'), ('fr_FR.UTF-8', 'Français'), ('es_ES.UTF-8', 'Español')]
LAYOUTS = [('us', 'intl', 'Verenigde Staten Internationaal (QWERTY, met dode toetsen) — standaard'), ('us', '', 'Verenigde Staten (QWERTY)'),
           ('us', 'altgr-intl', 'Verenigde Staten Internationaal met AltGr-dode toetsen'), ('nl', '', 'Nederlands'),
           ('be', '', 'Belgisch (AZERTY)'), ('gb', '', 'Verenigd Koninkrijk'), ('de', '', 'Duits (QWERTZ)'), ('fr', '', 'Frans (AZERTY)')]


def notify_shell():
    subprocess.run(['universe-ctl', 'config'], capture_output=True)


def pkexec_helper(args, stdin=None):
    r = subprocess.run(['pkexec', HELPER] + args, input=stdin, capture_output=True, text=True)
    if r.returncode in (126, 127):
        raise PermissionError('Geen toestemming: het beheerderswachtwoord is niet bevestigd.')
    if r.returncode:
        raise RuntimeError('De systeemwijziging is mislukt.' +
                           (' Technische melding: ' + r.stderr.strip() if r.stderr.strip() else ''))
    return True


def locales_available():
    have = set(l.strip().lower().replace('utf8', 'utf-8') for l in backend.out(['locale', '-a']).splitlines())
    return [{'id': lid, 'name': name, 'installed': lid.lower() in have} for lid, name in LANGUAGES]


def change_own_password(current, new):
    """Runs passwd in a pseudo terminal (normal PAM rules, no extra rights)."""
    if len(new) < 6:
        raise ValueError('Het nieuwe wachtwoord moet minstens 6 tekens hebben.')
    pid, fd = pty.fork()
    if pid == 0:
        os.environ['LC_ALL'] = 'C'
        os.execvp('passwd', ['passwd'])
    answers, buf, deadline = [current, new, new], b'', time.time() + 20
    while time.time() < deadline:
        r, _, _ = select.select([fd], [], [], 1)
        if not r:
            continue
        try:
            chunk = os.read(fd, 1024)
        except OSError:
            break
        if not chunk:
            break
        buf += chunk
        if buf.rstrip().endswith(b':') and answers:
            os.write(fd, (answers.pop(0) + '\n').encode())
            buf = b''
    _, status = os.waitpid(pid, 0)
    if os.waitstatus_to_exitcode(status) != 0:
        raise RuntimeError('Wachtwoord niet gewijzigd. Controleer je huidige wachtwoord; het nieuwe wachtwoord kan te eenvoudig zijn.')
    return True


def users():
    sudo = set(grp.getgrnam('sudo').gr_mem)
    me = pwd.getpwuid(os.getuid()).pw_name
    result = []
    for pw in pwd.getpwall():
        if 1000 <= pw.pw_uid < 60000 and not pw.pw_shell.endswith(('nologin', 'false')):
            result.append({'name': pw.pw_name, 'fullName': pw.pw_gecos.split(',')[0], 'admin': pw.pw_name in sudo, 'me': pw.pw_name == me})
    return sorted(result, key=lambda u: u['name'])


def wifi_list():
    lines = backend.out(['nmcli', '-t', '-f', 'IN-USE,SSID,SIGNAL,SECURITY', 'device', 'wifi', 'list', '--rescan', 'auto'], timeout=15)
    seen, nets = set(), []
    for line in lines.splitlines():
        parts = re.split(r'(?<!\\):', line)
        if len(parts) < 4 or not parts[1] or parts[1] in seen:
            continue
        seen.add(parts[1])
        nets.append({'ssid': parts[1].replace('\\:', ':'), 'active': parts[0] == '*', 'signal': int(parts[2] or 0), 'secure': bool(parts[3])})
    return sorted(nets, key=lambda n: -n['signal'])


def wifi_connect(ssid, password):
    cmd = ['nmcli', '--ask', 'device', 'wifi', 'connect', ssid]
    r = subprocess.run(cmd, input=(password or '') + '\n', capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise RuntimeError('Verbinden mislukt. Controleer het wachtwoord.')
    return True


def firewall():
    enabled = False
    try:
        enabled = 'ENABLED=yes' in open('/etc/ufw/ufw.conf').read()
    except OSError:
        pass
    active = backend.out(['systemctl', 'is-active', 'ufw']).strip() == 'active'
    return {'installed': os.path.exists('/usr/sbin/ufw'), 'enabled': enabled and active}


def about():
    osr = {}
    for line in open('/etc/os-release'):
        k, _, v = line.strip().partition('=')
        osr[k] = v.strip('"')
    mem = 0
    for line in open('/proc/meminfo'):
        if line.startswith('MemTotal'):
            mem = int(line.split()[1]) // 1024
    def read(p):
        try:
            return open(p).read().strip()
        except OSError:
            return ''
    version = ''
    try:
        version = open('/usr/share/universe-os/version').read().strip()
    except OSError:
        pass
    cpu = ''
    for line in open('/proc/cpuinfo'):
        if line.startswith('model name'):
            cpu = line.split(':', 1)[1].strip()
            break
    return {'universe': version, 'base': osr.get('PRETTY_NAME', ''), 'kernel': os.uname().release, 'cpu': cpu, 'memoryMB': mem,
            'machine': (read('/sys/class/dmi/id/sys_vendor') + ' ' + read('/sys/class/dmi/id/product_name')).strip(),
            'labwc': backend.out(['labwc', '--version']).strip(), 'secureBoot': secure_boot(),
            'efi': os.path.isdir('/sys/firmware/efi')}


def secure_boot():
    text = backend.out(['mokutil', '--sb-state']) if shutil.which('mokutil') else ''
    return 'aan' if 'enabled' in text else 'uit' if 'disabled' in text else 'onbekend'


def claude_path():
    """Same lookup as the AI page (also when ~/.local/bin is not on PATH)."""
    return _ai().bin_for('claude')


def ai_install(provider):
    """Opens a terminal with the official install command. Universe OS does not ship the CLIs."""
    if not shutil.which('xfce4-terminal'):
        raise RuntimeError('Er is geen terminal beschikbaar om de installatie te starten.')
    script = _ai().install_script(provider or 'claude')
    backend.spawn(['xfce4-terminal', '--title', 'AI installeren', '-x', 'bash', '-c', script])
    return True


def plugin_terminal(plugin_id):
    """User-started install. Rules are not copied; the script itself refuses a copy."""
    if not shutil.which('xfce4-terminal'):
        raise RuntimeError('Er is geen terminal beschikbaar om de installatie te starten.')
    script = _plugins().install_script(plugin_id)
    backend.spawn(['xfce4-terminal', '--title', 'Plugin installeren', '-x', 'bash', '-c', script])
    return True


def claude_status():
    path = claude_path()
    if not path:
        return {'installed': False, 'version': ''}
    return {'installed': True, 'version': backend.out([path, '--version'], timeout=5).strip()}


def claude_install():
    """Runs Anthropic's official installer in a terminal, so the user sees what happens."""
    return ai_install('claude')


def handlers(app):
    def set_config(a):
        config.set_setting(a['key'], a['value'])
        if a['key'] in ('naturalScroll', 'tapToClick', 'pointerSpeed'):
            session.reconfigure()
        if a['key'] in ('lockMinutes', 'screenOffMinutes'):
            backend.spawn(['/usr/lib/universe-os/universe-idle'])
        notify_shell()
        return backend.full_config()

    def set_keyboard(a):
        layout, variant = a.get('layout', ''), a.get('variant', '')
        if (layout, variant) not in [(l, v) for l, v, _ in LAYOUTS]:
            raise ValueError('Onbekende toetsenbordindeling')
        config.set_keyboard(layout, variant)
        session.reconfigure()
        if a.get('system'):
            r = subprocess.run(['localectl', 'set-x11-keymap', layout, 'pc105', variant], capture_output=True, text=True)
            if r.returncode:
                raise RuntimeError('Systeemindeling niet gewijzigd (geen beheerdersrechten?).')
        return config.keyboard()

    def set_locale(a):
        lang = a.get('lang')
        if lang not in [l for l, _ in LANGUAGES]:
            raise ValueError('Onbekende taal')
        config.set_locale(lang)
        if a.get('system'):
            r = subprocess.run(['localectl', 'set-locale', 'LANG=%s' % lang], capture_output=True, text=True)
            if r.returncode:
                raise RuntimeError('Systeemtaal niet gewijzigd (geen beheerdersrechten?).')
        return config.locale()

    def set_timezone(a):
        zone = a.get('zone', '')
        if zone not in backend.out(['timedatectl', 'list-timezones']).split():
            raise ValueError('Onbekende tijdzone')
        r = subprocess.run(['timedatectl', 'set-timezone', zone], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError('Tijdzone niet gewijzigd: beheerdersrechten nodig.')
        return True

    def timezone(a):
        text = backend.out(['timedatectl', 'show', '-p', 'Timezone', '--value']).strip()
        return {'zone': text, 'zones': backend.out(['timedatectl', 'list-timezones']).split(),
                'ntp': backend.out(['timedatectl', 'show', '-p', 'NTP', '--value']).strip() == 'yes'}

    def displays(a):
        try:
            return json.loads(backend.out(['/usr/lib/universe-os/universe-displays', 'list']) or '[]')
        except ValueError:
            return []

    def display_scale(a):
        r = subprocess.run(['/usr/lib/universe-os/universe-displays', 'scale', str(a['name']), str(float(a['scale']))], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError('De beeldschermschaal is niet gewijzigd.' +
                               (' Technische melding: ' + r.stderr.strip() if r.stderr.strip() else ''))
        return True

    def set_shortcuts(a):
        config.set_shortcuts(a.get('changes') or {})
        session.reconfigure()
        return config.shortcuts()

    def mic(a):
        text = backend.out(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SOURCE@'])
        m = re.search(r'Volume:\s*([\d.]+)', text)
        return {'level': round(float(m.group(1)) * 100), 'muted': 'MUTED' in text} if m else None

    def set_mic(a):
        subprocess.run(['wpctl', 'set-volume', '@DEFAULT_AUDIO_SOURCE@', '%d%%' % max(0, min(100, int(a.get('level', 50))))], check=False)
        return True

    def bluetooth(a):
        text = backend.out(['bluetoothctl', 'list'], timeout=4) if shutil.which('bluetoothctl') else ''
        return {'adapter': 'Controller' in text}

    return {
        'config.get': lambda a: backend.full_config(),
        'config.set': set_config,
        'apps.launch': lambda a: backend.launch(a.get('id')),
        'run': lambda a: backend.run_tool(a.get('tool'), a),
        'status': lambda a: backend.status(),
        'audio.outputs': lambda a: backend.audio.outputs(),
        'audio.select': lambda a: backend.audio.select(a),
        'volume.set': lambda a: backend.set_volume(a.get('level', 50)),
        'volume.mute': lambda a: backend.toggle_mute(),
        'mic.get': mic, 'mic.set': set_mic,
        'locale.get': lambda a: {'current': config.locale(), 'list': locales_available()},
        'locale.set': set_locale,
        'keyboard.get': lambda a: {'current': config.keyboard(), 'list': [{'layout': l, 'variant': v, 'name': n} for l, v, n in LAYOUTS]},
        'keyboard.set': set_keyboard,
        'timezone.get': timezone, 'timezone.set': set_timezone,
        'users.list': lambda a: users(),
        'users.add': lambda a: pkexec_helper(['add-user', a['name'], a.get('fullName', ''), 'admin' if a.get('admin') else 'standard'], a['password'] + '\n'),
        'users.remove': lambda a: pkexec_helper(['remove-user', a['name'], 'delete-home' if a.get('deleteHome') else 'keep-home']),
        'users.admin': lambda a: pkexec_helper(['set-admin', a['name'], 'yes' if a.get('admin') else 'no']),
        'users.password': lambda a: pkexec_helper(['set-password', a['name']], a['password'] + '\n'),
        'account.password': lambda a: change_own_password(a['current'], a['new']),
        'shortcuts.get': lambda a: config.shortcuts(),
        'shortcuts.set': set_shortcuts,
        'displays.list': displays, 'displays.scale': display_scale,
        'wifi.list': lambda a: wifi_list(),
        'wifi.connect': lambda a: wifi_connect(a['ssid'], a.get('password', '')),
        'network.status': lambda a: backend.network(),
        'bluetooth.get': bluetooth,
        'firewall.get': lambda a: firewall(),
        'updates.status': lambda a: backend.updates_status(),
        'updates.channel.get': lambda a: backend.update_channel.get(),
        'updates.channel.set': lambda a: backend.update_channel.set_channel(a),
        'updates.refresh': lambda a: backend.updates.refresh(),
        'updates.install': lambda a: backend.updates.install(),
        'about': lambda a: about(),
        'claude.status': lambda a: claude_status(),
        'claude.install': lambda a: claude_install(),
        'claude.open': lambda a: backend.spawn(['universe-ctl', 'claude']),
        'ai.status': lambda a: _ai().public_status(),
        'ai.set': lambda a: _ai().set_choice(a.get('provider'), a.get('model') or '', a.get('ollama_url')),
        'ai.key': lambda a: _ai().set_key(a.get('provider'), a.get('sleutel') if 'sleutel' in a else a.get('key')),
        'ai.open': lambda a: backend.spawn(['universe-ctl', 'claude']),
        'ai.install': lambda a: ai_install(a.get('provider') or 'claude'),
        'ai.leren': lambda a: _ai().set_leren(a.get('aan')),
        'ai.compressie': lambda a: _ai().set_compressie(a.get('modus') or a.get('compressie') or 'geen'),
        'ai.omniroute.add': lambda a: _ai().add_upstream(a.get('naam') or a.get('name')),
        'ai.omniroute.remove': lambda a: _ai().remove_upstream(a.get('naam') or a.get('name')),
        'ai.omniroute.router': lambda a: _ai().set_router(a.get('aan')),
        'ai.plugins': lambda a: _plugins().public_list(),
        'ai.plugins.set': lambda a: _plugins().set_enabled(a.get('id'), a.get('aan')),
        'ai.plugins.install': lambda a: _plugins().ensure(),
        'ai.plugins.terminal': lambda a: plugin_terminal(a.get('id')),
        'window.page': lambda a: app.pending_page,
        'brein.summary': lambda a: _brein().summary(),
        'brein.export': lambda a: _brein().write_export(_download_dir()),
        'brein.forget_all': lambda a: _brein().forget_all(a.get('bevestig') if 'bevestig' in a else a.get('confirm', '')) or {'vergeten': 'alles'},
        'accounts.list': lambda a: _accounts().list_public(),
        'accounts.clients': lambda a: _accounts().clients_public(),
        'accounts.client': lambda a: _accounts().save_client(a.get('provider'), a.get('client_id'), a.get('client_secret') or None),
        'accounts.oauth_start': _oauth_start,
        'accounts.oauth_poll': lambda a: _accounts().poll_oauth(a.get('flow')),
        'accounts.imap': lambda a: _accounts().add_imap(a.get('naam'), a.get('adres'), a.get('imap_host'), a.get('smtp_host'), a.get('user'), a.get('password'), a.get('imap_port'), a.get('smtp_port')),
        'accounts.caldav': lambda a: _accounts().add_caldav(a.get('naam'), a.get('adres'), a.get('url'), a.get('user'), a.get('password')),
        'accounts.disconnect': lambda a: _accounts().disconnect(a.get('id')),
        'scherm.status': lambda a: _screen_status_for_ui(),
        'scherm.toestaan': lambda a: _grant_screen(True),
        'scherm.intrekken': lambda a: _grant_screen(False),
    }


class ControlCenter(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='nl.universeos.ControlCenter', flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None
        self.pending_page = 'appearance'

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        if '--pagina' in args and args.index('--pagina') + 1 < len(args):
            self.pending_page = args[args.index('--pagina') + 1]
            if self.pending_page == 'claude':
                self.pending_page = 'ai'
        self.activate()
        if self.window and self.view:
            emit(self.view, 'page', self.pending_page)
        return 0

    def do_activate(self):
        if self.window:
            self.window.present()
            return
        bridge = Bridge(handlers(self), threaded={'updates.channel.set', 'network.status', 'status', 'audio.outputs', 'audio.select', 'wifi.list', 'wifi.connect', 'users.add', 'users.remove', 'users.admin',
                                                   'users.password', 'account.password', 'timezone.set', 'updates.status', 'keyboard.set',
                                                   'locale.set', 'bluetooth.get', 'updates.refresh', 'updates.install', 'claude.status',
                                                   'ai.status', 'ai.set', 'ai.key', 'ai.install', 'ai.leren',
                                                   'ai.compressie', 'ai.omniroute.add', 'ai.omniroute.remove', 'ai.omniroute.router',
                                                   'ai.plugins', 'ai.plugins.set', 'ai.plugins.install', 'ai.plugins.terminal',
                                                   'accounts.list', 'accounts.clients', 'accounts.client', 'accounts.oauth_start',
                                                   'accounts.oauth_poll', 'accounts.imap', 'accounts.caldav', 'accounts.disconnect',
                                                   'scherm.status', 'scherm.toestaan', 'scherm.intrekken'}, log=lambda *args: None)
        self.window = Gtk.ApplicationWindow(application=self, title='Controlecentrum')
        self.window.set_default_size(1040, 720)
        self.window.set_icon_name('preferences-system')
        self.view = make_view('control.html', bridge, zoom=config.settings()['uiScale'] / 100)
        self.window.add(self.view)
        self.window.show_all()


if __name__ == '__main__':
    GLib.set_prgname('nl.universeos.ControlCenter')
    sys.exit(ControlCenter().run(sys.argv))
