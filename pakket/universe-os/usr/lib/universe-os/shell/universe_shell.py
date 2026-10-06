"""Universe shell: the space world as the main interface, on top of the labwc compositor.

Three layer-shell surfaces (wlr-layer-shell, via gtk-layer-shell):
  world     background layer, one per screen: the space world with the planets
  panel     top layer: the compact control panel (always reachable, also above full-screen-ish windows)
  overview  overlay layer: open programs + search (Windows key)
Programs are normal windows managed by labwc. The shell can be restarted without closing them: programs are started
in their own session (backend.spawn) and the window list comes back from the compositor.
Commands from keyboard shortcuts arrive on a Unix socket (universe-ctl).
"""
import os
import sys
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
from toplevels import Toplevels  # noqa: E402
from webview import Bridge, emit, make_view  # noqa: E402

SOCKET = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), 'universe-shell.sock')
PANEL_CLOSED = (430, 44)
PANEL_OPEN = (400, 700)


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
        self.toplevels = Toplevels(self.windows_changed, log)
        self.bridge = Bridge(self.handlers(), threaded={'status', 'audio.outputs', 'audio.select', 'updates.status', 'power', 'volume.set', 'volume.mute',
                                                        'notifications.clear', 'search.files', 'updates.status', 'updates.refresh'}, log=log)
        self.worlds = []
        self.panel = None
        self.overview = None
        self.panel_open = False

    # ----- surfaces -----
    def build(self):
        display = Gdk.Display.get_default()
        for i in range(display.get_n_monitors()):
            self.add_world(display.get_monitor(i))
        display.connect('monitor-added', lambda d, m: self.add_world(m))
        display.connect('monitor-removed', self.remove_world)
        L, E, K = GtkLayerShell.Layer, GtkLayerShell.Edge, GtkLayerShell.KeyboardMode
        self.panel = Surface(self, 'panel', 'panel.html', L.TOP, [E.TOP], K.ON_DEMAND, size=PANEL_CLOSED, transparent=True)
        self.panel.window.show_all()
        # Search/overview is constructed on first use, not during login.

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
        return self.worlds + [s for s in (self.panel, self.overview) if s]

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

    # ----- windows -----
    def window_list(self):
        result = []
        for w in self.toplevels.list():
            app = None
            if w['appId']:
                app = Gio.DesktopAppInfo.new(w['appId'] + '.desktop') or Gio.DesktopAppInfo.new(w['appId'].lower() + '.desktop')
                if not app:
                    hits = Gio.DesktopAppInfo.search(w['appId'])
                    if hits and hits[0]:
                        app = Gio.DesktopAppInfo.new(hits[0][0])
            w['appName'] = app.get_display_name() if app else w['appId']
            w['icon'] = backend.icon_uri(app.get_icon()) if app else None
            result.append(w)
        return result

    def windows_changed(self):
        if self.toplevels.list():
            self.release_initial_focus()
        if self.overview and self.overview.window.get_visible():
            self.overview.emit('windows', self.window_list())
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

        def set_config(a):
            config.set_setting(a['key'], a['value'])
            if a['key'] in ('naturalScroll', 'tapToClick', 'pointerSpeed'):
                session.reconfigure()
            config_changed()
            return True

        def search(a):
            return backend.search(a.get('q', ''))

        def surface_hide(a):
            if a.get('name') == 'overview':
                self.hide_overview()
            return True

        def surface_show(a):
            if a.get('name') == 'overview':
                self.show_overview()
            return True

        def world_open(a):
            self.toplevels.show_desktop()
            for w in self.worlds:
                w.emit('open-planet', {'id': a.get('id')})
            return True

        return {
            'world.ready': lambda a: self.ready(a),
            'config.get': lambda a: backend.full_config(),
            'config.set': set_config,
            'apps.list': lambda a: backend.apps(),
            'apps.launch': lambda a: backend.launch(a.get('id')),
            'chrome.status': lambda a: backend.chrome(),
            'files.places': lambda a: backend.places(),
            'open.path': lambda a: backend.open_path(a.get('path', '')),
            'search': search,
            'status': lambda a: backend.status(),
            'audio.outputs': lambda a: backend.audio.outputs(),
            'audio.select': lambda a: backend.audio.select(a),
            'volume.set': lambda a: backend.set_volume(a.get('level', 50)),
            'volume.mute': lambda a: backend.toggle_mute(),
            'notifications.clear': lambda a: backend.clear_notifications(),
            'power': lambda a: backend.power(a.get('action')),
            'updates.status': lambda a: backend.updates_status(),
            'updates.refresh': lambda a: backend.updates.refresh(),
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
        answer = self.command((line or '').strip())
        connection.get_output_stream().write_all((answer + '\n').encode(), None)
        connection.close(None)
        return True

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
            elif cmd == 'desktop':
                return 'ok ' + self.desktop_toggle()
            elif cmd == 'panel':
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
        return True

    def run(self):
        if not GtkLayerShell.is_supported():
            log('De compositor ondersteunt wlr-layer-shell niet; de Universe-shell kan niet starten.')
            return 2
        self.build()
        self.serve()
        if not self.toplevels.start():
            log('Zonder vensteroverzicht verder.')
        GLib.timeout_add_seconds(10, self.status_tick)
        Gtk.main()
        return 0


def main():
    Gtk.init(sys.argv)
    return Shell().run()


if __name__ == '__main__':
    sys.exit(main())
