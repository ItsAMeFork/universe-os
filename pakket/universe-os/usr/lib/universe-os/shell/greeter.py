"""Universe planet greeter. Authentication belongs exclusively to LightDM/PAM."""
import os
import subprocess

import gi
import config

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('LightDM', '1')
from gi.repository import Gtk, Gdk, GLib, LightDM  # noqa: E402
from webview import Bridge, make_view, emit  # noqa: E402


def play(name, wait=False):
    """System sound on the login screen (universe-geluid; the greeter runs as the lightdm user with its own PipeWire)."""
    try:
        if wait:
            subprocess.run(['universe-geluid', name, '--wacht'], timeout=10, check=False)
        else:
            subprocess.Popen(['universe-geluid', name], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        pass


def startup_sound():
    """The startup sound (Axel, 12 Oct: like Windows, but chill reggae space), once per boot: not again after logging
    out. The marker carries the boot id, so a /tmp that survives a restart does not silence the next boot.
    Returns True on that first time: the login screen then also plays the start-up flight (opstartvlucht.js)."""
    try:
        with open('/proc/sys/kernel/random/boot_id') as f:
            boot = f.read().strip()
        fd = os.open('/tmp/.universe-opstart-' + boot, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.close(fd)
    except OSError:
        return False  # already played this boot (or /tmp unusable)
    play('opstarten')
    return True



TEST_FILTER = '/run/universe-os/greeter-testfilter'


def test_filter(lijst):
    """Test only (1/2-user login screen without deleting accounts): root can put user names, one per line, in a file
    on /run (tmpfs, gone after reboot). Only those users are shown. Missing or unreadable file: the normal list."""
    try:
        st = os.stat(TEST_FILTER)
        if st.st_uid != 0 or st.st_mode & 0o022:
            return lijst
        with open(TEST_FILTER) as f:
            namen = {r.strip() for r in f if r.strip()}
    except OSError:
        return lijst
    return [g for g in lijst if g['naam'] in namen] or lijst

class PlanetGreeter:
    def __init__(self):
        self.dm = LightDM.Greeter()
        self.prompt = None
        self.authorized = False
        self.starting = False
        self.timeout = None
        self.cancelling = False
        self.cancel_timeout = None
        self.attempt_active = False
        self.user = ''
        self.dm.connect('show-prompt', self.show_prompt)
        self.dm.connect('show-message', self.show_message)
        self.dm.connect('authentication-complete', self.authentication_complete)
        if not self.dm.connect_to_daemon_sync():
            raise RuntimeError('Geen verbinding met LightDM')
        self.window = Gtk.Window(title='Universe OS — aanmelden')
        self.window.set_decorated(False)
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        if monitor is None:
            raise RuntimeError('Geen beeldscherm gevonden')
        geometry = monitor.get_geometry()
        self.window.move(geometry.x, geometry.y)
        self.window.set_default_size(geometry.width, geometry.height)
        self.window.set_size_request(geometry.width, geometry.height)
        self.window.connect('realize', self.set_cursor)
        self.window.connect('delete-event', lambda *args: True)
        # Never log bridge arguments, responses, tracebacks or PAM text.
        bridge = Bridge({'login.ready': self.ready, 'login.authenticate': self.authenticate,
                         'login.respond': self.respond, 'login.start': self.start_session,
                         'login.cancel': self.cancel, 'power.get': self.power_get,
                         'power.shutdown': lambda _: self.power_action('shutdown'),
                         'power.suspend': lambda _: self.power_action('suspend'),
                         'power.restart': lambda _: self.power_action('restart')},
                        log=lambda *args: None)
        self.view = make_view('login.html', bridge)
        self.view.get_settings().set_enable_webgl(False)
        self.window.add(self.view)
        self.window.show_all()
        self.window.present()
        self.view.grab_focus()
        # 0.3.0: new or removed accounts appear/disappear in the planet row at once (liblightdm watches /etc/passwd)
        try:
            lijst = LightDM.UserList.get_instance()
            for sig in ('user-added', 'user-removed', 'user-changed'):
                lijst.connect(sig, lambda *_: self.users_changed())
        except Exception:
            pass

    def set_cursor(self, window):
        cursor = Gdk.Cursor.new_from_name(window.get_display(), 'default')
        if cursor is None:
            cursor = Gdk.Cursor.new_for_display(window.get_display(), Gdk.CursorType.LEFT_PTR)
        window.get_window().set_cursor(cursor)

    def ready(self, _):
        opstart = startup_sound()  # with the start-up flight (first time this boot) or the planet forming
        return {'user': self.dm.get_select_user_hint() or '', 'prompt': self.prompt, 'users': self.user_list(),
                'animations': config.settings().get('animations', 'full'), 'opstart': opstart}

    def users_changed(self):
        emit(self.view, 'login-users', {'users': self.user_list()})
        return False

    def user_list(self):
        """Name, display name, whether a (locked) session exists (liblightdm logged_in) and the profile photo (0.3.4,
        AccountsService via liblightdm, as a small data URL) of the users liblightdm knows, for the planet row;
        nothing else is shared."""
        try:
            import profielfoto
            users = LightDM.UserList.get_instance().get_users()
            lijst = [{'naam': u.get_name(), 'weergave': u.get_display_name() or u.get_name(),
                      'ingelogd': bool(u.get_logged_in()), 'foto': profielfoto.data_url_bestand(u.get_image())}
                     for u in users if u.get_name()]
        except Exception:
            return []
        return test_filter(lijst)

    def power_get(self, _):
        """Which power actions logind allows before signing in (via LightDM; no own privileges)."""
        return {'shutdown': bool(LightDM.get_can_shutdown()), 'suspend': bool(LightDM.get_can_suspend()),
                'restart': bool(LightDM.get_can_restart())}

    def power_action(self, action):
        """Suspend means suspend to RAM, never hibernate."""
        allowed = {'shutdown': (LightDM.get_can_shutdown, LightDM.shutdown, 'Afsluiten'),
                   'suspend': (LightDM.get_can_suspend, LightDM.suspend, 'Slaapstand'),
                   'restart': (LightDM.get_can_restart, LightDM.restart, 'Herstarten')}
        if action not in allowed:
            raise ValueError('Onbekende actie.')
        can, do, name = allowed[action]
        if self.starting:
            raise RuntimeError('Universe OS wordt al gestart.')
        if not can():
            raise RuntimeError('%s is op deze computer niet mogelijk.' % name)
        if action != 'suspend':
            play('afsluiten', wait=True)
        try:
            do()
        except GLib.Error:
            raise RuntimeError('%s is niet gelukt.' % name) from None
        return True

    def logged_in(self, name):
        """Whether this user already has a session (LightDM then switches back to it on start_session)."""
        try:
            for user in LightDM.UserList.get_instance().get_users():
                if user.get_name() == name:
                    return bool(user.get_logged_in())
        except (GLib.Error, AttributeError):
            pass
        return False

    def authenticate(self, args):
        """Selecting a user (or retrying after a wrong password) starts a fresh PAM conversation for that user.
        A running one, for another planet or the same, is cancelled first."""
        if self.starting:
            raise RuntimeError('De aanmelding wordt al gecontroleerd.')
        user = str(args.get('user', '')).strip()
        if not user or len(user) > 256:
            raise ValueError('Vul je gebruikersnaam in.')
        self.abort_attempt()
        self.attempt_active = True
        self.user = user
        try:
            self.dm.authenticate(user)
        except GLib.Error:
            self.attempt_active = False
            self.user = ''
            raise RuntimeError('Aanmelden kon niet worden gestart.') from None
        return True

    def abort_attempt(self):
        """Drop everything of the previous attempt, including a half-answered PAM conversation."""
        self.authorized = False
        self.attempt_active = False
        self.prompt = None
        self.user = ''
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None
        if self.dm.get_in_authentication():
            try:
                self.dm.cancel_authentication()
            except GLib.Error:
                pass  # authenticate() starts a new sequence; liblightdm ignores the old one.

    def show_prompt(self, _, text, kind):
        if self.cancelling or not self.attempt_active:
            return
        self.prompt = {'text': text, 'secret': kind == LightDM.PromptType.SECRET}
        emit(self.view, 'login-prompt', self.prompt)

    def respond(self, args):
        if not self.prompt or not self.dm.get_in_authentication():
            raise RuntimeError('Er is geen actieve wachtwoordvraag.')
        self.prompt = None
        try:
            self.dm.respond(str(args.get('response', '')))
        except GLib.Error:
            raise RuntimeError('Het antwoord kon niet worden verstuurd.') from None
        return True

    def show_message(self, _, text, kind):
        if self.cancelling or not self.attempt_active:
            return
        emit(self.view, 'login-message', {'text': text})

    def cancel(self, _):
        if self.starting:
            raise RuntimeError('Universe OS wordt al gestart.')
        self.cancelling = False
        # Returning to username must not wait for PAM to finish its old prompt.
        self.abort_attempt()
        emit(self.view, 'login-cancelled')
        return True

    def authentication_complete(self, _):
        self.prompt = None
        if not self.attempt_active:
            return
        self.attempt_active = False
        self.authorized = bool(self.dm.get_is_authenticated())
        if not self.authorized:
            # Never access. The page clears the field and asks for the same user again.
            emit(self.view, 'login-failed', {'user': self.user,
                                             'text': 'Onjuist wachtwoord. Probeer het opnieuw.'})
            return
        again = self.logged_in(self.user)
        emit(self.view, 'login-success', {'logged_in': again})
        # Recover if the page's animation callback fails; never bypass PAM.
        self.timeout = GLib.timeout_add(3000, self.start_after_timeout)

    def start_after_timeout(self):
        self.timeout = None
        self.start_session({})
        return False

    def start_session(self, _):
        if self.starting:
            return False
        if (not self.authorized or not self.dm.get_is_authenticated()
                or self.dm.get_authentication_user() != self.user):
            raise PermissionError('Je bent niet aangemeld.')
        self.starting = True
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None
        try:
            if not self.dm.start_session_sync('universe'):
                raise RuntimeError('Sessie niet gestart')
        except (GLib.Error, RuntimeError):
            self.starting = False
            self.authorized = False
            emit(self.view, 'login-error', 'Universe OS kon niet starten. Probeer opnieuw aan te melden.')
            return False
        return True


if __name__ == '__main__':
    try:  # 0.3.4: the screen stays on (unless an administrator chose a time); never keeps the login screen away
        import inlogscherm
        inlogscherm.toepassen()
    except Exception:  # noqa: BLE001
        pass
    PlanetGreeter()
    Gtk.main()
