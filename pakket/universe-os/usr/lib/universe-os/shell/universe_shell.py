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
from webview import Bridge, emit, make_view  # noqa: E402

SOCKET = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), 'universe-shell.sock')
# Page handlers that Claude Code may use through `universe-ctl call` (the universe-mcp tools). Logging out, power,
# installing and updates are deliberately missing.
CLAUDE_CALLS = {'status', 'apps.list', 'apps.launch', 'windows.list', 'windows.activate', 'windows.close', 'windows.minimize',
                'desktop.show', 'world.open', 'open.path', 'search', 'search.files', 'volume.set', 'volume.mute',
                'notifications.clear', 'run', 'desktop.list', 'desktop.mkdir', 'browser.list', 'config.get', 'config.set',
                'start.toggle', 'layout.get'}
CLAUDE_RUN = {'files', 'terminal', 'monitor', 'software', 'control', 'pavucontrol', 'wdisplays', 'blueman-manager', 'network-editor'}
PANEL_CLOSED = (430, 44)
PANEL_OPEN = (400, 700)
DOCK_HEIGHT = 64  # CSS pixels of .dock in dock.html
DOCK_MARGIN = 8


def log(text):
    print('[universe-shell] %s' % text, file=sys.stderr, flush=True)


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
                                                        'notifications.clear', 'search.files', 'updates.status', 'updates.refresh', 'updates.install', 'pick.path'}, log=log)
        self.worlds = []
        self.panel = None
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
        for s in self.surfaces():
            s.emit(name, data)

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
        for world in self.worlds:
            GtkLayerShell.set_layer(world.window, GtkLayerShell.Layer.OVERLAY)
            world.emit('lock-begin')
        self.lock_seen = False
        self.lock_started = time.monotonic()
        self.lock_watch = GLib.timeout_add(700, self.watch_lock)
        return 'anim'

    def watch_lock(self):
        running = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'swaylock'], stdout=subprocess.DEVNULL).returncode == 0
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
    def window_list(self):
        """Windows with program name and icon. The lookup (a search through all .desktop files and an icon theme
        lookup) is cached per appId: the list is rebuilt on every window change, also when a title ticks."""
        cache = self.__dict__.setdefault('app_cache', {})
        result = []
        for w in self.toplevels.list():
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
        busy = any(not w.get('minimized') for w in windows)
        if busy != getattr(self, 'last_busy', None):  # the world only needs to hear when it changes
            self.last_busy = busy
            for world in self.worlds:
                world.emit('background-busy', busy)
        if self.claude and self.claude.buddy:
            self.claude.buddy.set_busy(busy)
        if windows:
            self.release_initial_focus()
        listed = None
        if self.overview and self.overview.window.get_visible():
            listed = self.window_list()
            self.overview.emit('windows', listed)
        if self.dock:
            self.dock.emit('windows', listed if listed is not None else self.window_list())
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
            'notifications.clear': lambda a: backend.clear_notifications(),
            'power': lambda a: self.power(a.get('action')),
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
        }

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
            elif cmd == 'claude':
                if not (self.claude and self.claude.available()):
                    return 'fout: Claude Code is niet geïnstalleerd'
                self.claude.toggle()
            elif cmd == 'claude-event' and len(parts) > 1:
                import json
                data = {}
                if len(parts) > 2:
                    try:
                        data = json.loads(parts[2])
                    except ValueError:
                        pass
                if self.claude:
                    self.claude.event(parts[1], data if isinstance(data, dict) else {})
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

    def status_tick(self):
        if self.panel:
            def work():
                try:
                    data = backend.status()
                except Exception as error:
                    log('status: %s' % error)
                    return
                GLib.idle_add(self.panel.emit, 'status', data)
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
        if action != 'logout':
            return backend.power(action)
        GLib.idle_add(self.begin_logout)
        return True

    def begin_logout(self):
        if self.logout_pending:
            return False
        self.logout_pending = True
        self.hide_overview()
        if self.panel:
            self.panel.emit('panel-close')
        for world in self.worlds:
            GtkLayerShell.set_layer(world.window, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_keyboard_mode(world.window, GtkLayerShell.KeyboardMode.EXCLUSIVE)
            world.emit('logout-begin')
        # Logging out must still work if artwork or the JavaScript callback fails.
        self.logout_timer = GLib.timeout_add(1800, self.finish_logout)
        return False

    def finish_logout(self):
        if not self.logout_pending:
            return False
        self.logout_pending = False
        if self.logout_timer:
            GLib.source_remove(self.logout_timer)
            self.logout_timer = None
        try:
            backend.power('logout')
        except Exception as error:
            for world in self.worlds:
                GtkLayerShell.set_layer(world.window, GtkLayerShell.Layer.BACKGROUND)
                GtkLayerShell.set_keyboard_mode(world.window, GtkLayerShell.KeyboardMode.ON_DEMAND)
                world.emit('logout-error', str(error))
        return False

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
            self.broadcast('apps-changed')
            return False
        self.apps_changed_timer = GLib.timeout_add(300, send)


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
    log('modules geladen na %.1f s' % process_age())
    Gtk.init(sys.argv)
    return Shell().run()


if __name__ == '__main__':
    sys.exit(main())
