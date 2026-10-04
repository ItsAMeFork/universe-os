"""Open windows of the session via the wlr-foreign-toplevel-management protocol (supported by labwc).

Runs its own Wayland connection in a thread; changes are handed to the GTK main loop with GLib.idle_add.
Used for the overview of open programs (also minimised ones), activating/closing windows and Windows+D.
"""
import struct
import threading

from gi.repository import GLib

try:
    from pywayland.client import Display
    from protocols.wayland import WlSeat
    from protocols.wlr_foreign_toplevel_management_unstable_v1 import ZwlrForeignToplevelManagerV1
    AVAILABLE = True
except Exception as error:  # pragma: no cover - reported in the log and the UI
    AVAILABLE = False
    IMPORT_ERROR = error

# zwlr_foreign_toplevel_handle_v1.state values
MAXIMIZED, MINIMIZED, ACTIVATED, FULLSCREEN = 0, 1, 2, 3


def _states(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        data = bytes(value)
        return set(struct.unpack('%dI' % (len(data) // 4), data[: len(data) // 4 * 4]))
    try:
        return set(int(v) for v in value)
    except TypeError:
        return set()


class Toplevels:
    def __init__(self, on_change, log):
        self.on_change = on_change
        self.log = log
        self.windows = {}  # id -> dict
        self.handles = {}  # id -> handle
        self.next_id = 1
        self.seat = None
        self.display = None
        self.lock = threading.Lock()
        # Windows+D: the windows we minimised, restored on the next press.
        self.hidden_by_us = []

    def start(self):
        if not AVAILABLE:
            self.log('Vensteroverzicht niet beschikbaar: %s' % IMPORT_ERROR)
            return False
        try:
            self.display = Display()
            self.display.connect()
        except Exception as error:
            self.log('Geen Wayland-verbinding voor het vensteroverzicht: %s' % error)
            return False
        registry = self.display.get_registry()
        registry.dispatcher['global'] = self._global
        self.display.roundtrip()
        if not getattr(self, 'manager', None):
            self.log('De compositor ondersteunt wlr-foreign-toplevel niet.')
            return False
        self.display.roundtrip()
        threading.Thread(target=self._loop, name='toplevels', daemon=True).start()
        return True

    def _global(self, registry, name, interface, version):
        if interface == 'zwlr_foreign_toplevel_manager_v1':
            self.manager = registry.bind(name, ZwlrForeignToplevelManagerV1, min(version, 3))
            self.manager.dispatcher['toplevel'] = self._toplevel
        elif interface == 'wl_seat' and self.seat is None:
            self.seat = registry.bind(name, WlSeat, min(version, 5))

    def _loop(self):
        while True:
            try:
                if self.display.dispatch(block=True) == -1:
                    break
            except Exception as error:
                self.log('Vensteroverzicht gestopt: %s' % error)
                break

    def _toplevel(self, manager, handle):
        wid = str(self.next_id)
        self.next_id += 1
        info = {'id': wid, 'title': '', 'appId': '', 'minimized': False, 'maximized': False, 'activated': False, 'fullscreen': False}
        with self.lock:
            self.windows[wid] = info
            self.handles[wid] = handle

        def title(h, value):
            info['title'] = value

        def app_id(h, value):
            info['appId'] = value

        def state(h, value):
            s = _states(value)
            info['minimized'] = MINIMIZED in s
            info['maximized'] = MAXIMIZED in s
            info['activated'] = ACTIVATED in s
            info['fullscreen'] = FULLSCREEN in s

        def done(h):
            GLib.idle_add(self.on_change)

        def closed(h):
            with self.lock:
                self.windows.pop(wid, None)
                self.handles.pop(wid, None)
                if wid in self.hidden_by_us:
                    self.hidden_by_us.remove(wid)
            try:
                h.destroy()
            except Exception:
                pass
            GLib.idle_add(self.on_change)

        handle.dispatcher['title'] = title
        handle.dispatcher['app_id'] = app_id
        handle.dispatcher['state'] = state
        handle.dispatcher['done'] = done
        handle.dispatcher['closed'] = closed

    def list(self):
        with self.lock:
            return [dict(w) for w in self.windows.values()]

    def _request(self, wid, fn):
        with self.lock:
            handle = self.handles.get(wid)
        if not handle:
            raise ValueError('Dit venster bestaat niet meer.')
        fn(handle)
        self.display.flush()

    def activate(self, wid):
        def go(h):
            if self.windows.get(wid, {}).get('minimized'):
                h.unset_minimized()
            h.activate(self.seat)
        self._request(wid, go)
        if wid in self.hidden_by_us:
            self.hidden_by_us.remove(wid)

    def close(self, wid):
        self._request(wid, lambda h: h.close())

    def minimize(self, wid):
        self._request(wid, lambda h: h.set_minimized())

    def toggle_desktop(self):
        """Windows+D: minimise all windows; pressing again restores exactly those windows (last active on top)."""
        visible = [w for w in self.list() if not w['minimized']]
        if visible:
            self.hidden_by_us = [w['id'] for w in sorted(visible, key=lambda w: w['activated'])]
            for w in visible:
                self.minimize(w['id'])
            return 'space'
        restore = [wid for wid in self.hidden_by_us if wid in self.windows]
        self.hidden_by_us = []
        for wid in restore:
            self.activate(wid)
        return 'windows' if restore else 'space'

    def show_desktop(self):
        """Always go to the space world (used by planet/overview buttons)."""
        if any(not w['minimized'] for w in self.list()):
            return self.toggle_desktop()
        return 'space'
