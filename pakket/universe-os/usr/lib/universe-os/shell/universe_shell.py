"""Universe shell: the space world as the main interface, on top of the labwc compositor.

Layer-shell surfaces (wlr-layer-shell, via gtk-layer-shell):
  world     background layer, one per screen: the space world with the planets
  panel     top layer: the compact control panel (always reachable, also above full-screen-ish windows)
  dock      top layer at the bottom: fixed programs and open windows; reserves its height so windows stay above it
  start     top layer above the dock, fixed size: the start menu (start button / Windows key), built on first use
  overview  overlay layer: open programs + search (Windows key)
Programs are normal windows managed by labwc. The shell can be restarted without closing them: programs are started
in their own session (backend.spawn) and the window list comes back from the compositor.
Commands from keyboard shortcuts arrive on a Unix socket (universe-ctl).
"""
import os
import subprocess
import sys
import threading
import time

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gdk, Gio, GLib, Gtk, GtkLayerShell  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backend  # noqa: E402
import config  # noqa: E402
import session  # noqa: E402
from webview import WEBKIT_GRAPHICS, Bridge, emit, emit_code, event_code, make_view  # noqa: E402

SOCKET = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), 'universe-shell.sock')
# Page handlers that Claude Code may use through `universe-ctl call` (the universe-mcp tools): what a user does in the
# desktop (Axel, 13 Oct: "Claude can do everything in the software, except security and the code itself"). Power goes
# through claude.power, so locking and shutting down always play the same animations as the buttons. Missing on purpose:
# installing software and the shell's own surfaces and layout internals.
CLAUDE_CALLS = {'status', 'apps.list', 'apps.launch', 'windows.list', 'windows.activate', 'windows.close', 'windows.minimize',
                'desktop.show', 'world.open', 'open.path', 'search', 'search.files', 'volume.set', 'volume.mute',
                'notifications.clear', 'run', 'desktop.list', 'desktop.mkdir', 'desktop.rename', 'desktop.trash',
                'desktop.launch', 'browser.list', 'browser.select', 'audio.outputs', 'audio.select', 'config.get',
                'config.set', 'start.toggle', 'layout.get', 'updates.status', 'updates.refresh', 'updates.install',
                'claude.power', 'claude.anim', 'brein.list', 'brein.links', 'brein.timeline', 'brein.update', 'brein.forget',
                'brein.search', 'brein.forget_all', 'brein.lijst', 'brein.ochtend',
                'mail.search', 'mail.read', 'mail.draft', 'mail.send', 'agenda.list', 'agenda.create',
                'scherm.status', 'scherm.muis', 'scherm.klik', 'scherm.typ', 'scherm.toets', 'scherm.scroll', 'scherm.focus'}
# terminal is not here: the assistant must not open a shell it can then type into.
CLAUDE_RUN = {'files', 'monitor', 'software', 'control', 'pavucontrol', 'wdisplays', 'blueman-manager', 'network-editor'}
# Same set as universe_mcp.SECURITY_SETTINGS: `universe-ctl call config.set` must not bypass the MCP check.
SECURITY_SETTINGS = {'lockMinutes'}
# Fixed list for claude.anim / animatie_tonen. Planet flights are the existing world.open route (open-planet);
# ruimte leaves the room (show-space). Buddy states and walks are the ones claude_ui.Buddy already plays.
ANIMATIONS = {
    'planeet-thuis': ('planeet', 'home'),
    'planeet-applicaties': ('planeet', 'apps'),
    'planeet-winkel': ('planeet', 'store'),
    'planeet-controle': ('planeet', 'control'),
    'planeet-internet': ('planeet', 'chat'),
    'planeet-games': ('planeet', 'games'),
    'planeet-brein': ('planeet', 'brein'),
    'ruimte': ('ruimte', None),
    'buddy-rust': ('buddy', 'idle'),
    'buddy-luisteren': ('buddy', 'listen'),
    'buddy-denken': ('buddy', 'think'),
    'buddy-werken': ('buddy', 'work'),
    'buddy-aandacht': ('buddy', 'attention'),
    'buddy-blij': ('buddy', 'happy'),
    'buddy-naar-huis': ('plek', 'home'),
    'buddy-naar-dock': ('plek', 'dock'),
    'buddy-naar-wereld': ('plek', 'world'),
    'buddy-naar-paneel': ('plek', 'panel'),
}
PANEL_CLOSED = (430, 44)
PANEL_OPEN = (400, 700)
DOCK_HEIGHT = 64  # CSS pixels of .dock in dock.html
DOCK_MARGIN = 8


_ghost = None


def log(text):
    """Session log. Ghost mode keeps a short failure label and drops routine lines and payloads."""
    global _ghost
    if _ghost is None:
        try:
            folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'claude')
            if folder not in sys.path:
                sys.path.insert(0, folder)
            import ghost_modus
            _ghost = ghost_modus
        except Exception:  # noqa: BLE001 - logging must keep working if the switch cannot be read
            _ghost = False
    if _ghost:
        text = _ghost.shell_line(text)
    if text:
        print('[universe-shell] %s' % text, file=sys.stderr, flush=True)


def _brein():
    """brein.py lives next to the shell, under claude/ (installed: /usr/lib/universe-os/claude)."""
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'claude')
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import brein
    return brein


def _ochtend():
    """Read-only morning briefing. Sending and paying stay on mail.send and the confirmation dialog."""
    _brein()
    import ochtend
    return ochtend


def _brein_files(query, limit=10):
    """Recoll hits as moons; without Recoll, the shell's own file-name search."""
    query = str(query or '').strip()
    if not query:
        return []
    limit = max(1, min(int(limit or 10), 12))
    found = None
    try:
        folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'claude')
        if folder not in sys.path:
            sys.path.insert(0, folder)
        import recoll_index
        found = recoll_index.search(query, limit)
    except Exception:  # noqa: BLE001 - the nebula still works without file search
        found = None
    if found is not None:
        moons = []
        for item in found[:limit]:
            path = item.get('pad') or ''
            moons.append({'naam': (item.get('titel') or os.path.basename(path) or path)[:180], 'pad': path, 'soort': 'bestand'})
        return moons
    try:
        named = backend.search_files(query, limit)
    except Exception:  # noqa: BLE001
        return []
    return [{'naam': item.get('name') or '', 'pad': item.get('path') or '',
             'soort': 'map' if item.get('dir') else 'bestand'} for item in named[:limit]]


def _brein_update(args):
    text = args.get('tekst') if 'tekst' in args else args.get('text')
    brain = _brein()
    brain.update(args.get('id'), text)
    return brain.get(int(args.get('id')))


def _brein_forget(args):
    memory_id = int(args.get('id'))
    _brein().forget(memory_id)
    return {'vergeten': memory_id}


def _brein_search(args):
    query = args.get('q') if 'q' in args else args.get('zoek', '')
    brain = _brein()
    result = {'sterren': brain.search_memories(query, args.get('max') or 40), 'bestanden': _brein_files(query)}
    needle = str(query or '').strip().lower()
    if needle:
        result['extra'] = [star for star in brain.sterren_extra(40)
                           if needle in (star.get('tekst') or '').lower() or needle in (star.get('labels') or '').lower()]
    return result


def _brein_forget_all(args):
    phrase = args.get('bevestig') if 'bevestig' in args else args.get('confirm', '')
    _brein().forget_all(phrase)
    return {'vergeten': 'alles'}


def _claude_dir():
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'claude')
    if folder not in sys.path:
        sys.path.insert(0, folder)
    return folder


def _accounts():
    _claude_dir()
    import accounts
    return accounts


def _screen():
    _claude_dir()
    import screen
    return screen


def _peer():
    _claude_dir()
    import peer
    return peer


def _auto():
    _claude_dir()
    import auto_accept
    return auto_accept


def _confirm(title, text):
    """Dialog on the user's screen. A missing zenity counts as no. Arguments from Claude are never a yes."""
    _claude_dir()
    import confirm
    return confirm.ask(title, text)


def _mail_kwargs(args):
    return {'account': args.get('account'), 'to': args.get('naar') if 'naar' in args else args.get('to'),
            'subject': args.get('onderwerp') if 'onderwerp' in args else args.get('subject'),
            'body': args.get('tekst') if 'tekst' in args else args.get('body') or ''}


def _mail_via(args):
    if args.get('via') in ('browser', 'account'):
        return args.get('via')
    _claude_dir()
    import ai_provider
    return ai_provider.load().get('mail_via') or 'browser'


def _mail_send(args):
    """Browser is the default. A linked account is used only when the user chose that route."""
    kwargs = _mail_kwargs(args)
    extra = {'bijlagen': args.get('bijlagen') or 0, 'vlag': bool(args.get('belangrijk'))}
    if _mail_via(args) == 'browser':
        return _accounts().authorize_browser(to=kwargs['to'], subject=kwargs['subject'], body=kwargs['body'],
                                              confirmer=_confirm, **extra)
    return _accounts().send_mail(confirmer=_confirm, **kwargs, **extra)


class Surface:
    def __init__(self, shell, name, page, layer, anchors, keyboard, size=None, monitor=None, transparent=False, namespace=None):
        self.name = name
        self.window = Gtk.Window()
        self.window.set_title('Universe %s' % name)
        if transparent:
            visual = self.window.get_screen().get_rgba_visual()
            if visual:
                self.window.set_visual(visual)
            self.window.set_app_paintable(True)
        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_namespace(self.window, namespace or 'universe-%s' % name)
        GtkLayerShell.set_layer(self.window, layer)
        for edge in anchors:
            GtkLayerShell.set_anchor(self.window, edge, True)
        GtkLayerShell.set_keyboard_mode(self.window, keyboard)
        if monitor is not None:
            GtkLayerShell.set_monitor(self.window, monitor)
        if layer == GtkLayerShell.Layer.BACKGROUND:
            GtkLayerShell.set_exclusive_zone(self.window, -1)
        if size:
            self.window.set_size_request(*size)
            self.window.set_default_size(*size)
        self.view = make_view(page, shell.bridge, transparent=transparent, zoom=config.settings()['uiScale'] / 100)
        self.view.surface = self
        self.window.add(self.view)

    def emit(self, name, data=None):
        emit(self.view, name, data)


class Shell:
    def __init__(self):
        self.started = time.time()
        self.started_monotonic = time.monotonic()
        self.world_ready = False
        self.toplevels = None  # run(): imported after the world window exists (pywayland, asyncio, ssl: seconds on a cold disk)
        self.bridge = Bridge(self.handlers(), threaded={'status', 'audio.outputs', 'audio.select', 'updates.status', 'power', 'volume.set', 'volume.mute',
                                                        'notifications.clear', 'search.files', 'updates.status', 'updates.refresh', 'updates.install', 'pick.path',
                                                        'brein.search', 'brein.lijst', 'mail.search', 'mail.read', 'mail.draft', 'mail.send',
                                                        'agenda.list', 'agenda.create', 'scherm.muis', 'scherm.klik', 'scherm.typ', 'scherm.toets',
                                                        'scherm.scroll', 'scherm.focus'}, log=log)
        self.worlds = []
        self.panel = None
        self.last_status = self.last_auto = None  # what the panel page was last sent (status_tick)
        self.dock = None
        self.start = None
        self.overview = None
        self.panel_open = False
        self.logout_pending = False
        self.logout_timer = None
        self.claude = None  # claude_ui.ClaudeUI (panel + buddy), made in run()

    # ----- surfaces -----
    def build(self):
        display = Gdk.Display.get_default()
        for i in range(display.get_n_monitors()):
            self.add_world(display.get_monitor(i))
        display.connect('monitor-added', lambda d, m: self.add_world(m))
        display.connect('monitor-removed', self.remove_world)
        # Panel and dock follow once the world is visible (ready()): every page starts its own WebKit process, and
        # three at once made the world wait for the CPU after login. The timeout covers a world that never reports.
        GLib.timeout_add_seconds(15, lambda: self.build_bars() and False)
        try:
            self.watch_desktop()
        except Exception as error:  # pragma: no cover - only logged
            log('Bureaubladmap niet te volgen: %s' % error)
        # Search/overview is constructed on first use, not during login.

    def build_bars(self):
        if self.panel:
            return False
        L, E, K = GtkLayerShell.Layer, GtkLayerShell.Edge, GtkLayerShell.KeyboardMode
        self.panel = Surface(self, 'panel', 'panel.html', L.TOP, [E.TOP], K.ON_DEMAND, size=PANEL_CLOSED, transparent=True)
        self.panel.window.show_all()
        self.dock = Surface(self, 'dock', 'dock.html', L.TOP, [E.BOTTOM], K.ON_DEMAND, size=(420, DOCK_HEIGHT), transparent=True)
        GtkLayerShell.set_margin(self.dock.window, E.BOTTOM, DOCK_MARGIN)
        self.dock.window.show_all()
        self.resize_dock(420)
        if self.claude:
            GLib.timeout_add_seconds(3, self.claude.update_buddy)  # the buddy comes last, after panel and dock
        return False

    def add_world(self, monitor):
        L, E, K = GtkLayerShell.Layer, GtkLayerShell.Edge, GtkLayerShell.KeyboardMode
        world = Surface(self, 'world', 'world.html', L.BACKGROUND, [E.TOP, E.BOTTOM, E.LEFT, E.RIGHT], K.ON_DEMAND, monitor=monitor)
        world.monitor = monitor
        world.window.show_all()
        self.worlds.append(world)
        if len(self.worlds) == 1:
            # Initial keyboard focus, without requiring a click on the desktop.
            GtkLayerShell.set_keyboard_mode(world.window, K.EXCLUSIVE)
            world.view.grab_focus()
            world.window.connect('key-press-event', self.release_initial_focus)
            world.window.connect('button-press-event', self.release_initial_focus)

    def release_initial_focus(self, *args):
        for world in self.worlds:
            GtkLayerShell.set_keyboard_mode(world.window, GtkLayerShell.KeyboardMode.ON_DEMAND)
        return False

    def remove_world(self, display, monitor):
        for world in [w for w in self.worlds if w.monitor == monitor]:
            world.window.destroy()
            self.worlds.remove(world)

    def surfaces(self):
        return self.worlds + [s for s in (self.panel, self.dock, self.start, self.overview) if s]

    def broadcast(self, name, data=None):
        code = event_code(name, data)  # serialise once, not once per surface
        for s in self.surfaces():
            emit_code(s.view, code)

    def show_overview(self):
        if self.overview is None:
            L, E, K = GtkLayerShell.Layer, GtkLayerShell.Edge, GtkLayerShell.KeyboardMode
            self.overview = Surface(self, 'overview', 'overview.html', L.OVERLAY,
                                    [E.TOP, E.BOTTOM, E.LEFT, E.RIGHT], K.EXCLUSIVE, transparent=True)
            self.overview.window.connect('key-press-event', self.overview_key)
        if self.panel_open:
            self.panel.emit('panel-close')
        self.overview.window.show_all()
        self.overview.window.present()
        self.overview.emit('windows', self.window_list())
        self.overview.emit('shown')

    def hide_overview(self):
        if self.overview:
            self.overview.window.hide()

    def toggle_overview(self):
        if self.overview and self.overview.window.get_visible():
            self.hide_overview()
        else:
            self.show_overview()

    def overview_key(self, widget, event):
        return False

    def resize_panel(self, open_):
        self.panel_open = open_
        win = self.panel.window
        if open_:
            height = min(PANEL_OPEN[1], win.get_screen().get_height() - 20) if win.get_screen() else PANEL_OPEN[1]
            win.set_size_request(PANEL_OPEN[0], height)
            win.resize(PANEL_OPEN[0], height)
            GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        else:
            win.set_size_request(*PANEL_CLOSED)
            win.resize(*PANEL_CLOSED)
            GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.ON_DEMAND)
        return True

    def watch_desktop(self):
        """Tells the world when files appear on or disappear from the Bureaublad folder (like a desktop refresh)."""
        folder = backend.desktop_dir()
        os.makedirs(folder, exist_ok=True)
        self.desktop_monitor = Gio.File.new_for_path(folder).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
        self.desktop_timer = 0

        def changed(*args):
            if self.desktop_timer:
                GLib.source_remove(self.desktop_timer)
            self.desktop_timer = GLib.timeout_add(300, fire)

        def fire():
            self.desktop_timer = 0
            for w in self.worlds:
                w.emit('desktop-changed')
            return False
        self.desktop_monitor.connect('changed', changed)

    def lock_begin(self):
        """universe-lock: the desktop is pulled into the Earth before swaylock shows the same Earth; afterwards it comes
        out again. The world is raised above the windows for the animation; the shell watches swaylock itself, so the
        world always goes back below the windows (also when swaylock does not start). Returns 'anim' or 'direct'."""
        if not self.worlds or self.logout_pending or getattr(self, 'lock_watch', 0):
            return 'direct'
        if config.settings().get('animations') != 'full':
            return 'direct'
        if self.claude:
            self.claude.toggle(False)  # the Claude panel lies above the world: it would hide the animation
        for world in self.worlds:
            GtkLayerShell.set_layer(world.window, GtkLayerShell.Layer.OVERLAY)
            world.emit('lock-begin')
        self.lock_seen = False
        self.lock_started = time.monotonic()
        self.lock_watch = GLib.timeout_add(700, self.watch_lock)
        return 'anim'

    def watch_lock(self):
        running = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'gtklock|swaylock'], stdout=subprocess.DEVNULL).returncode == 0
        if running:
            self.lock_seen = True
            return True
        if not self.lock_seen and time.monotonic() - self.lock_started < 12:
            return True
        self.lock_watch = 0
        for world in self.worlds:
            world.emit('unlock')
        GLib.timeout_add(4000, self.unlock_done)  # fallback if the page does not answer
        return False

    def unlock_done(self):
        if not getattr(self, 'lock_watch', 0):
            for world in self.worlds:
                GtkLayerShell.set_layer(world.window, GtkLayerShell.Layer.BACKGROUND)
        return False

    def claim_intro(self):
        """True only the first time in a login session (the login animation continues on the desktop). The marker
        lives in XDG_RUNTIME_DIR, so a shell restart does not replay it."""
        # Per login session: the runtime dir is only emptied when all sessions of the user end (e.g. not with SSH open).
        session = os.environ.get('XDG_SESSION_ID', 'x').replace('/', '')
        marker = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), 'universe-intro-shown-%s' % session)
        try:
            fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return False
        except OSError:
            return False
        os.close(fd)
        backend.spawn(['universe-geluid', 'inloggen'])  # with the planets flying out of the Earth
        return True

    def make_start(self):
        """Builds the (hidden) start menu surface once."""
        if self.start is None:
            L, E, K = GtkLayerShell.Layer, GtkLayerShell.Edge, GtkLayerShell.KeyboardMode
            # Anchored top and bottom: the height always follows the real screen (a fixed height from the monitor
            # geometry was stale after a resolution change and the menu fell off a 1024x768 screen, 10 Oct).
            # The page limits the menu itself to 700 px and puts it at the bottom.
            self.start = Surface(self, 'start', 'start.html', L.TOP, [E.TOP, E.BOTTOM], K.EXCLUSIVE, size=(660, -1), transparent=True)
            GtkLayerShell.set_margin(self.start.window, E.BOTTOM, DOCK_HEIGHT + DOCK_MARGIN + 6)
            GtkLayerShell.set_margin(self.start.window, E.TOP, 56)
        return True

    def start_menu(self, open_=None):
        """Start menu: its own fixed-size surface above the dock (growing the dock surface did not reliably resize the
        page, VM 10 Oct). open_ None toggles. It has the keyboard while visible."""
        visible = bool(self.start and self.start.window.get_visible())
        if open_ is None:
            open_ = not visible
        if open_ and not visible:
            self.make_start()
            self.hide_overview()
            self.start.window.show_all()
            self.start.view.grab_focus()
            self.start.emit('start-shown')
        elif not open_ and visible:
            self.start.window.hide()
        self.broadcast('start-state', bool(open_))
        return True

    def resize_dock(self, width, height=None):
        """The page reports the size of its contents (CSS pixels); the window follows, scaled with the zoom.
        height > DOCK_HEIGHT while its context menu is open (the surface grows upwards, the reserved space stays).
        width 0 = the user removed everything from the dock: hide it and give the space back."""
        zoom = self.dock.view.get_zoom_level()
        if width <= 0:
            GtkLayerShell.set_exclusive_zone(self.dock.window, 0)
            self.dock.window.hide()
            return True
        w = max(80, min(int(width * zoom), 3000))
        h = int(max(DOCK_HEIGHT, min(height or DOCK_HEIGHT, 700)) * zoom)
        self.dock.window.set_size_request(w, h)
        self.dock.window.resize(w, h)
        GtkLayerShell.set_exclusive_zone(self.dock.window, int(DOCK_HEIGHT * zoom))
        if not self.dock.window.get_visible():
            self.dock.window.show_all()
        return True

    # ----- windows -----
    def window_list(self, windows=None):
        """Windows with program name and icon. The lookup (a search through all .desktop files and an icon theme
        lookup) is cached per appId: the list is rebuilt on every window change, also when a title ticks.
        windows: a snapshot the caller already took, so the windows are not copied a second time."""
        cache = self.__dict__.setdefault('app_cache', {})
        result = []
        for w in (self.toplevels.list() if windows is None else windows):
            key = w['appId']
            if key not in cache:
                app = None
                if key:
                    app = backend.desktop_app(key + '.desktop') or backend.desktop_app(key.lower() + '.desktop')
                    if not app:
                        hits = Gio.DesktopAppInfo.search(key)
                        if hits and hits[0]:
                            app = backend.desktop_app(hits[0][0])
                cache[key] = (app.get_display_name() if app else key, backend.icon_uri(app.get_icon()) if app else None)
            w['appName'], w['icon'] = cache[key]
            result.append(w)
        return result

    def windows_changed(self):
        """Many window events come in a burst (activating one window changes two): one update per 60 ms is enough."""
        if not getattr(self, 'windows_timer', 0):
            self.windows_timer = GLib.timeout_add(60, self.windows_update)
        return False

    def windows_update(self):
        self.windows_timer = 0
        windows = self.toplevels.list()
        # A request for administrator rights (the polkit password window, e.g. installing software): a meteor shoots
        # past (Axel, 12 Oct). sudo in a terminal gets the same sound through PAM (universe-admin-geluid).
        auth = {str(w.get('id')) for w in windows if 'polkit' in (w.get('appId') or '').lower()}
        if auth - getattr(self, 'auth_windows', set()):
            backend.sound('meteoor')
        self.auth_windows = auth
        busy = any(not w.get('minimized') for w in windows)
        if busy != getattr(self, 'last_busy', None):  # the world only needs to hear when it changes
            self.last_busy = busy
            for world in self.worlds:
                world.emit('background-busy', busy)
        if self.claude and self.claude.buddy:
            self.claude.buddy.set_busy(busy)
            # A maximised or full-screen window that is not minimised: the slime steps aside until it is smaller again.
            self.claude.buddy.set_covered(any(not w.get('minimized') and (w.get('maximized') or w.get('fullscreen'))
                                              for w in windows))
        if windows:
            self.release_initial_focus()
        code = None
        if self.overview and self.overview.window.get_visible():
            code = event_code('windows', self.window_list(windows))  # same list for both: serialise once
            emit_code(self.overview.view, code)
        if self.dock:
            emit_code(self.dock.view, code if code is not None else event_code('windows', self.window_list(windows)))
        return False

    def desktop_toggle(self):
        self.hide_overview()
        result = self.toplevels.toggle_desktop()
        if result == 'space':
            for w in self.worlds:
                w.emit('show-space')
        return result

    # ----- commands from the pages -----
    def handlers(self):
        def config_changed():
            data = backend.full_config()
            for s in self.surfaces():
                s.view.set_zoom_level(data['settings']['uiScale'] / 100)
            self.broadcast('config', data)
            if self.claude:
                self.claude.update_buddy()

        def set_config(a):
            config.set_setting(a['key'], a['value'])
            if a['key'] in ('naturalScroll', 'tapToClick', 'pointerSpeed'):
                session.reconfigure()
            config_changed()
            return True

        def layout_set(a):
            clean = config.set_layout(a.get('layout'))
            self.broadcast('layout', clean)
            return clean

        def layout_reset(a):
            clean = config.reset_layout()
            self.broadcast('layout', clean)
            return clean

        def search(a):
            return backend.search(a.get('q', ''))

        def surface_hide(a):
            if a.get('name') == 'overview':
                self.hide_overview()
            elif a.get('name') == 'start':
                self.start_menu(False)
            return True

        def surface_show(a):
            if a.get('name') == 'overview':
                self.show_overview()
            return True

        def launch(a):
            result = backend.launch(a.get('id'))
            app = backend.desktop_app(a.get('id'))
            from buddy_hints import log_event  # timeline of the second brain (habits for the buddy)
            log_event('app', a.get('id'), app.get_display_name() if app else '')
            return result

        def open_path(a):
            result = backend.open_path(a.get('path', ''))
            from buddy_hints import log_event
            log_event('file', a.get('path', ''), os.path.basename(str(a.get('path', ''))))
            return result

        def world_open(a):
            self.toplevels.show_desktop()
            for w in self.worlds:
                w.emit('open-planet', {'id': a.get('id')})
            return True

        return {
            'background.busy': lambda a: any(not w.get('minimized') for w in self.toplevels.list()),
            'world.ready': lambda a: self.ready(a),
            'ui.error': lambda a: log('UI %s: %s' % (str(a.get('page', 'unknown'))[:40], str(a.get('message', ''))[:1500].replace('\n', ' '))),
            'config.get': lambda a: backend.full_config(),
            'config.set': set_config,
            'apps.list': lambda a: backend.apps(),
            'apps.desktop': lambda a: backend.desktop_apps(),
            'apps.launch': launch,
            'browser.list': lambda a: backend.browsers(),
            'browser.select': lambda a: backend.browser_select(a.get('id')),
            'chrome.status': lambda a: backend.chrome(),
            'files.places': lambda a: backend.places(),
            'open.path': open_path,
            'search': search,
            'search.files': lambda a: backend.search_files((a.get('q') or '').strip()),
            'status': lambda a: backend.status(),
            'audio.outputs': lambda a: backend.audio.outputs(),
            'audio.select': lambda a: backend.audio.select(a),
            'volume.set': lambda a: backend.set_volume(a.get('level', 50)),
            'volume.mute': lambda a: backend.toggle_mute(),
            'volume.ping': lambda a: backend.volume_ping(),
            'notifications.clear': lambda a: backend.clear_notifications(),
            'power': lambda a: self.power(a.get('action')),
            'claude.power': lambda a: self.claude_power(a.get('action')),
            'claude.anim': lambda a: self.show_animation(a.get('naam')),
            'logout.finish': lambda a: self.finish_logout(),
            'updates.status': lambda a: backend.updates_status(),
            'updates.refresh': lambda a: backend.updates.refresh(),
            'updates.install': lambda a: backend.updates.install(),
            'run': lambda a: backend.run_tool(a.get('tool'), a),
            'windows.list': lambda a: self.window_list(),
            'windows.activate': lambda a: self.toplevels.activate(str(a.get('id'))),
            'windows.close': lambda a: self.toplevels.close(str(a.get('id'))),
            'windows.minimize': lambda a: self.toplevels.minimize(str(a.get('id'))),
            'desktop.show': lambda a: self.toplevels.show_desktop(),
            'world.open': world_open,
            'surface.hide': surface_hide,
            'surface.show': surface_show,
            'surface.size': lambda a: self.resize_panel(bool(a.get('open'))),
            'dock.size': lambda a: self.resize_dock(float(a.get('width') or 0), float(a.get('height') or 0) or None),
            'layout.get': lambda a: config.layout(),
            'layout.set': layout_set,
            'layout.reset': layout_reset,
            'pick.path': lambda a: backend.pick_path('folder' if a.get('kind') == 'folder' else 'file'),
            'desktop.list': lambda a: backend.desktop_list(),
            'desktop.mkdir': lambda a: backend.desktop_mkdir(),
            'desktop.rename': lambda a: backend.desktop_rename(str(a.get('path') or ''), a.get('name')),
            'desktop.trash': lambda a: backend.desktop_trash(str(a.get('path') or '')),
            'desktop.launch': lambda a: backend.desktop_launch(str(a.get('path') or '')),
            'start.toggle': lambda a: self.start_menu(a.get('open')),
            'intro.claim': lambda a: self.claim_intro(),
            'lock.ready': lambda a: True,
            'unlock.done': lambda a: self.unlock_done(),
            'claude.available': lambda a: bool(self.claude and self.claude.available()),
            'claude.toggle': lambda a: bool(self.claude) and self.claude.toggle(a.get('open')),
            'brein.list': lambda a: {'sterren': _brein().list_memories(a.get('max'))},
            'brein.links': lambda a: {'lijnen': _brein().links(a.get('max'))},
            'brein.timeline': lambda a: {'spoor': _brein().trail(a.get('max')), 'dagen': _brein().TIMELINE_DAYS},
            'brein.update': _brein_update,
            'brein.forget': _brein_forget,
            'brein.search': _brein_search,
            'brein.forget_all': _brein_forget_all,
            'brein.lijst': lambda a: _brein().lijst(a.get('soort') or a.get('filter') or 'alles', a.get('q') if 'q' in a else a.get('zoek') or '', a.get('max') or 40),
            'brein.ochtend': lambda a: _ochtend().compose(),
            'brein.les': lambda a: _brein().set_lesson_active(a.get('id'), a.get('aan')),
            # Not in CLAUDE_CALLS: the user turns spoken prompts on in the Brein. Off stays silent.
            'buddy.stem': lambda a: __import__('buddy_voice').configure(a.get('aan')),
            'brein.ongedaan': lambda a: _brein().undo_actie(a.get('id')),
            'auto.status': lambda a: _auto().public(),
            'auto.set': lambda a: self._auto_set(a),
            'auto.regels': lambda a: self._auto_regels(a),
            'mail.search': lambda a: _accounts().search_mail(a.get('q') if 'q' in a else a.get('zoek') or '', a.get('account'), a.get('max') or 8),
            'mail.read': lambda a: _accounts().read_mail(a.get('account'), a.get('id')),
            'mail.draft': lambda a: _accounts().draft_mail(**_mail_kwargs(a)),
            # confirmer is always the on-screen dialog. A "bevestig" field from Claude is ignored.
            'mail.send': lambda a: _mail_send(a),
            'agenda.list': lambda a: _accounts().list_events(a.get('account')),
            'agenda.create': lambda a: _accounts().create_event(a.get('account'), a.get('titel') or a.get('title'), a.get('start'),
                                                                a.get('eind') if 'eind' in a else a.get('end'), a.get('plek') or a.get('location') or '',
                                                                confirmer=_confirm),
            'scherm.status': lambda a: _screen().status(),
            'scherm.muis': lambda a: self._screen_act('muis', a),
            'scherm.klik': lambda a: self._screen_act('klik', a),
            'scherm.typ': lambda a: self._screen_act('typ', a),
            'scherm.toets': lambda a: self._screen_act('toets', a),
            'scherm.scroll': lambda a: self._screen_act('scroll', a),
            'scherm.focus': lambda a: self._screen_focus(a),
            # Not in CLAUDE_CALLS: only the Accounts page (this process's buttons, via the control centre) may flip the switch.
            'scherm.toestaan': lambda a: self._screen_grant(True),
            'scherm.intrekken': lambda a: self._screen_grant(False),
        }

    def _focused_app(self):
        try:
            windows = self.window_list()
        except Exception:
            return ''
        for window in windows:
            if window.get('activated'):
                return window.get('appId') or ''
        return ''

    def _screen_act(self, kind, args):
        """Pointer, keys and typing. The banner is up for the whole call, including the confirmation dialog.
        The focused program is filled in here so the model cannot claim a terminal is something else."""
        screen = _screen()
        args = dict(args or {})
        args['venster'] = self._focused_app()
        self.broadcast('scherm', {**screen.status(), 'bezig': True, 'actie': kind})
        try:
            return screen.perform(kind, args, confirmer=_confirm)
        finally:
            self.broadcast('scherm', screen.status())

    def _screen_focus(self, args):
        screen = _screen()
        if not screen.enabled():
            _brein().log_actie('scherm_focus', 'Schermbediening stond uit', 'geweigerd')
            raise PermissionError('AI mag het scherm niet bedienen. Zet het aan in Controlecentrum → Accounts.')
        target = ''
        for window in self.window_list():
            if str(window.get('id')) == str(args.get('id')):
                target = window.get('appId') or ''
        if screen.terminal_app(target):
            _brein().log_actie('scherm_focus', 'Terminal geweigerd', 'geweigerd')
            raise PermissionError('Een terminal mag de assistent niet naar voren halen.')
        self.broadcast('scherm', {**screen.status(), 'bezig': True, 'actie': 'focus'})
        try:
            self.toplevels.activate(str(args.get('id')))
            _brein().log_actie('scherm_focus', 'Venster %s' % args.get('id'), 'uitgevoerd')
            return {'gelukt': True}
        finally:
            self.broadcast('scherm', screen.status())

    def _auto_set(self, args):
        info = _auto().set_choice(bool(args.get('aan')), args.get('duur') or '30m')
        self.broadcast('auto', info)
        return info

    def _auto_regels(self, args):
        info = _auto().set_regels(args.get('regels') if 'regels' in args else args.get('lijst') or '')
        self.broadcast('auto', info)
        return info

    def _screen_grant(self, on):
        screen = _screen()
        result = screen.allow() if on else screen.revoke()
        self.broadcast('scherm', result)
        return result

    # ----- universe-ctl socket -----
    def serve(self):
        try:
            os.unlink(SOCKET)
        except FileNotFoundError:
            pass
        service = Gio.SocketService()
        service.add_address(Gio.UnixSocketAddress.new(SOCKET), Gio.SocketType.STREAM, Gio.SocketProtocol.DEFAULT, None)
        os.chmod(SOCKET, 0o600)
        service.connect('incoming', self.incoming)
        service.start()
        self.service = service

    def incoming(self, service, connection, source):
        stream = Gio.DataInputStream.new(connection.get_input_stream())
        line, _ = stream.read_line_utf8(None)
        line = (line or '').strip()

        def answer(text):
            try:
                connection.get_output_stream().write_all((text + '\n').encode(), None)
                connection.close(None)
            except Exception as error:  # the caller gave up (timeout)
                log('antwoord niet verstuurd: %s' % error)
            return False
        if line.startswith('call '):
            # Same-user processes can open this socket. Only the real MCP server may call handlers.
            if not _peer().allow_call(line, _peer().cmdline_of_connection(connection)):
                return answer('fout: alleen de assistent-hulpmiddelen mogen dit. Een terminal kan het niet.')
            self.call(line, answer)
        else:
            answer(self.command(line))
        return True

    def call(self, line, answer):
        """universe-ctl call <handler> [json]: a page handler for the Claude tools (universe-mcp). Slow handlers run
        in a thread, like for the pages; the answer is 'ok <json>' or 'fout: <message>'."""
        import json
        parts = line.split(maxsplit=2)
        name = parts[1] if len(parts) > 1 else ''
        if name not in CLAUDE_CALLS:
            return answer('fout: niet toegestaan: %s' % name)
        try:
            args = json.loads(parts[2]) if len(parts) > 2 else {}
            if not isinstance(args, dict):
                raise ValueError('argumenten moeten een object zijn')
        except ValueError as error:
            return answer('fout: %s' % error)
        if name == 'run' and args.get('tool') not in CLAUDE_RUN:  # not the .deb installer or the system installer
            return answer('fout: niet toegestaan: run %s' % args.get('tool'))
        if name == 'config.set' and args.get('key') in SECURITY_SETTINGS:
            return answer('fout: Dit is een beveiligingsinstelling; die verandert de gebruiker zelf in het Controlecentrum.')
        if name == 'config.set' and args.get('key') == 'heBuddy':
            return answer('fout: Hé Buddy zet je zelf aan in het Brein.')
        if name == 'claude.anim' and args.get('naam') not in ANIMATIONS:
            return answer('fout: Onbekende animatie: %s. Kies uit: %s' % (args.get('naam'), ', '.join(ANIMATIONS)))
        fn = self.handlers()[name]

        def work():
            try:
                text = 'ok ' + json.dumps(fn(args), ensure_ascii=False, default=str)
            except Exception as error:
                text = 'fout: %s' % (str(error) or error.__class__.__name__)
            return text
        if name in self.bridge.threaded or name == 'search':  # search also scans files (up to 0.8 s)
            threading.Thread(target=lambda: answer(work()), daemon=True).start()
        else:
            answer(work())

    def command(self, line):
        parts = line.split(maxsplit=2)
        if not parts:
            return 'fout: leeg'
        cmd = parts[0]
        try:
            if cmd == 'ping':
                return 'ok %d' % (time.time() - self.started)
            if cmd == 'overview':
                self.toggle_overview()
            elif cmd == 'start':
                self.start_menu()
            elif cmd == 'lock':
                return 'ok ' + self.lock_begin()
            elif cmd == 'desktop':
                return 'ok ' + self.desktop_toggle()
            elif cmd == 'panel' and self.panel:
                self.panel.emit('panel-toggle')
            elif cmd == 'world' and len(parts) > 1:
                self.handlers()['world.open']({'id': parts[1]})
            elif cmd == 'run' and len(parts) > 1:
                backend.run_tool(parts[1], {'page': parts[2]} if len(parts) > 2 else {})
            elif cmd == 'windows':
                import json
                return json.dumps(self.window_list(), ensure_ascii=False)
            elif cmd == 'config':
                data = backend.full_config()
                for s in self.surfaces():
                    s.view.set_zoom_level(data['settings']['uiScale'] / 100)
                self.broadcast('config', data)
                if self.claude:
                    self.claude.update_buddy()  # buddy switched on/off in the Control Center
            elif cmd == 'logout':  # the same animated logout as the start menu (also for scripts and tests)
                GLib.idle_add(self.begin_logout)
            elif cmd == 'scherm-stop':
                # Panic hotkey (Super+Escape). Drops screen control and auto-accept before the next action.
                _claude_dir()
                import auto_accept
                self.broadcast('auto', auto_accept.stop())
                self.broadcast('scherm', _screen().revoke())
            elif cmd == 'scherm-aan':
                import json
                result = _screen().request_grant(_confirm)
                self.broadcast('scherm', result)
                return 'ok ' + json.dumps(result, ensure_ascii=False)
            elif cmd == 'scherm-uit':
                import json
                result = _screen().revoke()
                self.broadcast('scherm', result)
                return 'ok ' + json.dumps(result, ensure_ascii=False)
            elif cmd == 'scherm':
                import json
                result = _screen().status()
                self.broadcast('scherm', result)
                return 'ok ' + json.dumps(result, ensure_ascii=False)
            elif cmd == 'claude':
                if not (self.claude and self.claude.available()):
                    return 'fout: De gekozen AI is niet geïnstalleerd'
                self.claude.toggle()
            elif cmd == 'claude-ask' and len(parts) > 1:
                # Puts a question ready in the panel (the user sends it with Enter). The buddy never sends it.
                if not (self.claude and self.claude.available()):
                    return 'fout: De gekozen AI is niet geïnstalleerd'
                self.claude.ask(line.split(maxsplit=1)[1])
            elif cmd == 'claude-event' and len(parts) > 1:
                import json
                data = {}
                if len(parts) > 2:
                    try:
                        data = json.loads(parts[2])
                    except ValueError:
                        pass
                if not isinstance(data, dict):
                    data = {}
                if parts[1] == 'brein':
                    self.flash_brein(data)  # a new memory: the open nebula flashes a star
                elif self.claude:
                    self.claude.event(parts[1], data)
            elif cmd == 'apps-changed':
                self.broadcast('apps-changed')
            elif cmd == 'reload':
                for s in self.surfaces():
                    s.view.reload()
            else:
                return 'fout: onbekende opdracht'
            return 'ok'
        except Exception as error:
            log('opdracht %s mislukt: %s' % (line, error))
            return 'fout: %s' % error

    # ----- system sounds like Windows (Axel, 12 Oct): devices in/out, low battery -----
    def watch_devices(self):
        """One sound per physical USB device (stick, mouse, phone...): udev reports usb_device once per device,
        its interfaces are filtered out. stdbuf: udevadm buffers its output in a pipe (the sounds came much later);
        setpriv: it stops together with the shell. It sleeps in the kernel until something happens: no polling."""
        try:
            proc = Gio.Subprocess.new(['setpriv', '--pdeathsig', 'TERM', 'stdbuf', '-oL', 'udevadm', 'monitor', '--udev', '--subsystem-match=usb/usb_device'],
                                      Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
        except GLib.Error as error:
            log('apparaatgeluiden niet beschikbaar: %s' % error.message)
            return
        self.udev = proc
        self.udev_lines = Gio.DataInputStream.new(proc.get_stdout_pipe())
        self.device_sound_at = 0.0
        self.udev_lines.read_line_async(GLib.PRIORITY_LOW, None, self.device_event)

    def device_event(self, stream, result):
        try:
            line, _ = stream.read_line_finish_utf8(result)
        except GLib.Error:
            return
        if line is None:
            return  # udevadm stopped
        words = line.split()
        if len(words) > 2 and words[0] == 'UDEV' and words[2] in ('add', 'remove'):
            now = time.monotonic()
            if now - self.device_sound_at > 1.0:  # a hub with several devices: one sound
                self.device_sound_at = now
                backend.sound('apparaat-in' if words[2] == 'add' else 'apparaat-uit')
        stream.read_line_async(GLib.PRIORITY_LOW, None, self.device_event)

    def check_battery_sound(self):
        """Warning sound when the battery drops to 10 % and again at 5 % (not charging)."""
        try:
            bat = backend.battery()
        except Exception:  # noqa: BLE001
            return True
        if not bat.get('present'):
            return False  # desktop pc: stop checking
        level = bat.get('percent', 100)
        if bat.get('charging') or level > 10:
            self.battery_level_warned = 100
        elif level <= 10 < self.battery_level_warned or level <= 5 < self.battery_level_warned:
            self.battery_level_warned = 5 if level <= 5 else 10
            backend.sound('waarschuwing')
        return True

    # ----- mandatory restart after updates (Axel, 12 Oct) -----
    # universe-updates-run writes restartRequired + installedAt. From the moment the message is shown the computer
    # restarts after 2 minutes; the last 10 seconds are a launch countdown on the world, then the shutdown animation.
    RESTART_AFTER = 120
    LAUNCH_SECONDS = 10

    def check_restart(self):
        if getattr(self, 'restart_deadline', 0) or self.logout_pending:
            return
        data = backend.updates._read()
        at = data.get('installedAt')
        if not data.get('restartRequired') or not isinstance(at, (int, float)) or at < boot_time():
            return  # nothing installed since this boot
        if backend.is_live():
            return
        self.restart_deadline = time.monotonic() + self.RESTART_AFTER
        self.restart_version = str(data.get('version') or '')
        self.restart_reminded = False
        log('Updates geïnstalleerd (%s): herstart over %d s.' % (self.restart_version or '?', self.RESTART_AFTER))
        self.notify('Sla je werk op',
                    'Er zijn updates geïnstalleerd. Over 2 minuten wordt de computer opnieuw opgestart.')
        GLib.timeout_add(1000, self.restart_tick)

    def notify(self, title, body):
        try:
            backend.spawn(['notify-send', '-u', 'critical', '-c', 'universe.restart', '-a', 'Universe OS',
                           '-i', 'system-software-update', title, body])
        except RuntimeError:
            pass

    def restart_tick(self):
        if self.logout_pending:
            return False  # the user restarted or logged out himself
        left = self.restart_deadline - time.monotonic()
        if left <= 60 and not self.restart_reminded:
            self.restart_reminded = True
            self.notify('Nog 1 minuut', 'De computer wordt over 1 minuut opnieuw opgestart. Sla je werk op.')
        if left <= self.LAUNCH_SECONDS + 0.5:
            self.begin_launch(max(1, round(left)))
            return False
        return True

    def begin_launch(self, seconds):
        """The launch of the new software: the world rises above all windows and counts down from 10."""
        self.hide_overview()
        if self.panel:
            self.panel.emit('panel-close')
        if self.start:
            self.start_menu(False)
        for world in self.worlds:
            GtkLayerShell.set_layer(world.window, GtkLayerShell.Layer.OVERLAY)
            world.emit('launch-countdown', {'seconds': seconds, 'version': self.restart_version})
        self.launch_left = seconds
        backend.sound('aftellen')
        def tick():
            self.launch_left -= 1
            if self.launch_left > 0:
                backend.sound('aftellen')
                return True
            self.launch_timer = 0
            self.begin_logout('reboot', sound='lancering')
            return False
        self.launch_timer = GLib.timeout_add(1000, tick)

    def status_tick(self):
        self.check_restart()
        if self.panel:
            def work():
                try:
                    data = backend.status()
                except Exception as error:
                    log('status: %s' % error)
                    return
                # Only tell the page when something changed: it has the last values and asks again when it loads.
                if data != self.last_status:
                    self.last_status = data
                    GLib.idle_add(self.panel.emit, 'status', data)
                try:
                    auto = _auto().public()
                    if auto != self.last_auto:
                        self.last_auto = auto
                        GLib.idle_add(self.panel.emit, 'auto', auto)
                except Exception:
                    pass
            import threading
            threading.Thread(target=work, daemon=True).start()
        return True

    def ready(self, data):
        if not self.world_ready:
            self.world_ready = True
            log('ruimtewereld zichtbaar na %.3f s; pagina %.0f ms' %
                (time.monotonic() - self.started_monotonic, float(data.get('milliseconds', 0))))
            GLib.idle_add(self.build_bars)
            # Load the start menu in the background, so the first press of the Windows key is instant
            # (building it on first use took ~15 s in the VM).
            GLib.timeout_add_seconds(5, lambda: self.make_start() and False)
        return True

    def power(self, action):
        if action not in ('logout', 'reboot', 'poweroff'):
            return backend.power(action)
        # Shutting down and restarting look like logging out (Axel, 12 Oct): everything is pulled into the Earth and
        # the glowing core; then the shutdown sound and the power action.
        GLib.idle_add(self.begin_logout, action)
        return True

    def flash_brein(self, data):
        """Push one memory to every world. The nebula ignores it when it is closed."""
        payload = {}
        try:
            payload = _brein().resolve_flash(data or {}) or {}
        except Exception as error:  # noqa: BLE001 - the hook must not break the shell
            log('brein-flits: %s' % error)
        for world in self.worlds:
            world.emit('brein-flash', payload)

    def show_animation(self, name):
        """Play one allow-listed animation the world or the buddy already knows (animatie_tonen)."""
        spec = ANIMATIONS.get(name)
        if not spec:
            raise ValueError('Onbekende animatie: %s' % name)
        kind, arg = spec
        if kind == 'planeet':  # same flight as world.open: the planet room opens
            self.toplevels.show_desktop()
            for world in self.worlds:
                world.emit('open-planet', {'id': arg})
            return True
        if kind == 'ruimte':
            for world in self.worlds:
                world.emit('show-space')
            return True
        buddy = self.claude.buddy if self.claude else None
        if not buddy:
            raise RuntimeError('De buddy is er niet (uitgezet of de gekozen AI ontbreekt).')
        if kind == 'buddy':
            buddy.set_state(arg)
        elif kind == 'plek':
            buddy.go(arg)
        else:
            raise ValueError('Onbekende animatie: %s' % name)
        return True

    def claude_power(self, action):
        """Locking, logging out, restarting, shutting down or sleep on Claude's request (Axel, 13 Oct): exactly the
        path of the buttons, so the animations always play. Claude gets its answer at once; running the lock command
        itself, it waited until the screen was unlocked again (the panel hung, and there was no animation)."""
        if action not in ('lock', 'logout', 'reboot', 'poweroff', 'suspend'):
            raise ValueError('Onbekende actie: %s' % action)
        def go():
            if self.claude:
                self.claude.toggle(False)  # the Claude panel lies above everything: first out of the way
            if action == 'lock':
                backend.power('lock')  # universe-lock: the desktop into the Earth, then the lock screen
            elif action == 'suspend':
                threading.Thread(target=backend.power, args=('suspend',), daemon=True).start()
            else:
                self.begin_logout(action)
            return False
        GLib.timeout_add(400, go)  # first the answer to Claude, then the animation
        return True

    def begin_logout(self, action='logout', sound=None):
        if self.logout_pending:
            return False
        if self.claude:
            self.claude.toggle(False)
        self.logout_pending = action
        self.logout_started = time.monotonic()
        backend.sound(sound or ('afmelden' if action == 'logout' else 'afsluiten'))
        if getattr(self, 'launch_timer', 0):
            GLib.source_remove(self.launch_timer)
            self.launch_timer = 0
        self.hide_overview()
        if self.panel:
            self.panel.emit('panel-close')
        for world in self.worlds:
            GtkLayerShell.set_layer(world.window, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_keyboard_mode(world.window, GtkLayerShell.KeyboardMode.EXCLUSIVE)
            world.emit('logout-begin', {'action': action})
        # Logging out must still work if artwork or the JavaScript callback fails.
        self.logout_timer = GLib.timeout_add(4500, self.finish_logout)  # the page says when its animation is done; 1.8 s cut it off
        return False

    def finish_logout(self):
        if not self.logout_pending:
            return False
        action, self.logout_pending = self.logout_pending, False
        if self.logout_timer:
            GLib.source_remove(self.logout_timer)
            self.logout_timer = None
        try:
            if action == 'logout':
                backend.power('logout')
            else:
                # The shutdown tune (5.8 s, like the startup one) started with the animation (~3-4 s): the computer
                # only goes off when it has finished.
                wait = 5.6 - (time.monotonic() - self.logout_started)
                GLib.timeout_add(max(1, int(wait * 1000)), self.power_off_now, action)
        except Exception as error:
            self.power_failed(error)
        return False

    def power_off_now(self, action):
        try:
            backend.power(action, sound_first=False)
        except Exception as error:
            self.power_failed(error)
        return False

    def power_failed(self, error):
        for world in self.worlds:
            GtkLayerShell.set_layer(world.window, GtkLayerShell.Layer.BACKGROUND)
            GtkLayerShell.set_keyboard_mode(world.window, GtkLayerShell.KeyboardMode.ON_DEMAND)
            world.emit('logout-error', str(error))

    def run(self):
        if not GtkLayerShell.is_supported():
            log('De compositor ondersteunt wlr-layer-shell niet; de Universe-shell kan niet starten.')
            return 2
        self.build()
        # The world page now loads in its own WebKit process while Python imports the window list.
        from toplevels import Toplevels
        self.toplevels = Toplevels(self.windows_changed, log)  # windows_changed coalesces bursts
        try:
            from claude_ui import ClaudeUI  # cheap: panel and buddy are only built when needed
            self.claude = ClaudeUI(self, log)
        except Exception as error:  # pragma: no cover - only logged; the desktop works without Claude
            log('Claude-onderdelen niet geladen: %s' % error)
        self.app_monitor = Gio.AppInfoMonitor.get()
        self.apps_changed_timer = None
        self.app_monitor.connect('changed', self.schedule_apps_changed)
        self.serve()
        # Verplichte updates: bij inloggen een echte controle (+ installatie) als de laatste controle ouder is dan 20 uur.
        GLib.timeout_add_seconds(45, self.check_updates_at_login)
        if not self.toplevels.start():
            log('Zonder vensteroverzicht verder.')
        GLib.timeout_add_seconds(10, self.status_tick)
        self.watch_devices()
        self.battery_level_warned = 100
        GLib.timeout_add_seconds(60, self.check_battery_sound)
        Gtk.main()
        return 0

    def check_updates_at_login(self):
        if backend.is_live():
            return False  # live-sessie van de USB-stick: niet bijwerken
        def work():
            if backend.updates.check_at_login():
                log('Updatecontrole bij inloggen gestart.')
        threading.Thread(target=work, daemon=True).start()
        return False

    def schedule_apps_changed(self, *_):
        if self.apps_changed_timer:
            GLib.source_remove(self.apps_changed_timer)
        def send():
            self.apps_changed_timer = None
            self.__dict__.pop('app_cache', None)  # names and icons of windows may have changed
            backend.apps_changed()  # the start menu search reads the programs again
            self.broadcast('apps-changed')
            return False
        self.apps_changed_timer = GLib.timeout_add(300, send)


def boot_time():
    """When this computer started (epoch seconds), from /proc/stat."""
    try:
        with open('/proc/stat') as f:
            for line in f:
                if line.startswith('btime '):
                    return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return time.time()  # unknown: never restart because of an old status


def process_age():
    """Seconds since this process started (for the startup log: how much of a slow login is Python and GTK)."""
    try:
        with open('/proc/self/stat') as f:
            start = int(f.read().rsplit(')', 1)[1].split()[19]) / os.sysconf('SC_CLK_TCK')
        with open('/proc/uptime') as f:
            return float(f.read().split()[0]) - start
    except (OSError, ValueError, IndexError):
        return 0.0


def main():
    log('modules geladen na %.1f s; grafische drivers %s, render-node %s, tekenmodus %s (%s)' % (
        process_age(), ','.join(WEBKIT_GRAPHICS[0]) or 'geen', WEBKIT_GRAPHICS[1], WEBKIT_GRAPHICS[2], WEBKIT_GRAPHICS[3]))
    Gtk.init(sys.argv)
    return Shell().run()


if __name__ == '__main__':
    sys.exit(main())
