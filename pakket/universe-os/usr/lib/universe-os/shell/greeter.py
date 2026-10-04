"""Universe planet greeter. Authentication belongs exclusively to LightDM/PAM."""
import gi
import config

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('LightDM', '1')
from gi.repository import Gtk, Gdk, GLib, LightDM  # noqa: E402
from webview import Bridge, make_view, emit  # noqa: E402


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
                         'login.cancel': self.cancel},
                        log=lambda *args: None)
        self.view = make_view('login.html', bridge)
        self.view.get_settings().set_enable_webgl(False)
        self.window.add(self.view)
        self.window.show_all()
        self.window.present()
        self.view.grab_focus()

    def set_cursor(self, window):
        cursor = Gdk.Cursor.new_from_name(window.get_display(), 'default')
        if cursor is None:
            cursor = Gdk.Cursor.new_for_display(window.get_display(), Gdk.CursorType.LEFT_PTR)
        window.get_window().set_cursor(cursor)

    def ready(self, _):
        return {'user': self.dm.get_select_user_hint() or '', 'prompt': self.prompt,
                'animations': config.settings().get('animations', 'full')}

    def authenticate(self, args):
        if self.starting:
            raise RuntimeError('De aanmelding wordt al gecontroleerd.')
        user = str(args.get('user', '')).strip()
        if not user or len(user) > 256:
            raise ValueError('Vul je gebruikersnaam in.')
        self.authorized = False
        self.prompt = None
        self.attempt_active = True
        try:
            self.dm.authenticate(user)
        except GLib.Error:
            self.attempt_active = False
            raise RuntimeError('Aanmelden kon niet worden gestart.') from None
        return True

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
        self.authorized = False
        self.attempt_active = False
        self.prompt = None
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None
        # Returning to username must not wait for PAM to finish its old prompt.
        # The next authenticate() replaces it using liblightdm's sequence number.
        self.cancelling = False
        if self.dm.get_in_authentication():
            try:
                self.dm.cancel_authentication()
            except GLib.Error:
                pass  # A fresh authenticate() remains available to recover.
        emit(self.view, 'login-cancelled')
        return True

    def authentication_complete(self, _):
        self.prompt = None
        if not self.attempt_active:
            return
        self.attempt_active = False
        self.authorized = bool(self.dm.get_is_authenticated())
        if not self.authorized:
            emit(self.view, 'login-error', 'Aanmelden mislukt. Controleer je account en wachtwoord.')
            return
        emit(self.view, 'login-success')
        # Recover if the page's animation callback fails; never bypass PAM.
        self.timeout = GLib.timeout_add(3000, self.start_after_timeout)

    def start_after_timeout(self):
        self.timeout = None
        self.start_session({})
        return False

    def start_session(self, _):
        if self.starting:
            return False
        if not self.authorized or not self.dm.get_is_authenticated():
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
    PlanetGreeter()
    Gtk.main()
