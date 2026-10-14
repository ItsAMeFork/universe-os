"""The buddy thinks ahead: small suggestions in a speech bubble, with buttons that arrange things at once.

Pre-programmed on purpose: no AI and no Claude requests of its own (only the user talks to Claude, in the panel).
It watches a few cheap signals (a finished download, a USB stick, a low battery, the apps the user usually opens at
this hour from the second brain's timeline) and asks. "Vraag Claude" puts a ready-made question in the Claude panel;
the user sends it with Enter. Every answer is remembered (brein.hints): "Nooit" stops that suggestion for good,
"Niet nu" for the rest of the day.
"""
import os
import sys
import threading
import time

from gi.repository import Gio, GLib

sys.path.insert(0, '/usr/lib/universe-os/claude')
import backend  # noqa: E402

PARTIAL = ('.part', '.crdownload', '.download', '.tmp', '.partial')
HABIT_EVERY = 15 * 60
INDEX_EVERY = 30 * 60
BATTERY_EVERY = 180


def brein():
    import brein as module  # /usr/lib/universe-os/claude/brein.py
    return module


def log_event(kind, item, label=''):
    """Timeline entry in the background (SQLite must not delay the click)."""
    def work():
        try:
            brein().log_event(kind, item, label)
        except Exception:  # noqa: BLE001 - the timeline is optional
            pass
    threading.Thread(target=work, daemon=True).start()


class Hints:
    def __init__(self, ui, log):
        self.ui = ui
        self.log = log
        self.monitors = []
        self.shown_today = {}
        self.battery_warned = False
        self.started = time.time()
        self.watch_downloads()
        self.volumes = Gio.VolumeMonitor.get()
        self.volumes.connect('mount-added', self.mount_added)
        GLib.timeout_add_seconds(90, self.check_habits)  # first look shortly after login
        GLib.timeout_add_seconds(HABIT_EVERY, self.check_habits_repeat)
        GLib.timeout_add_seconds(BATTERY_EVERY, self.check_battery)
        self.indexer = None
        GLib.timeout_add_seconds(300, self.update_index)  # not during login
        GLib.timeout_add_seconds(INDEX_EVERY, self.update_index_repeat)

    # ----- asking -----
    def suggest(self, key, text, actions, claude=None, wait=False):
        """actions: [(label, fn)]. claude: a question to prepare in the Claude panel. wait: only when nothing is in
        front (habits); downloads and USB sticks are about what the user just did, so they show at once."""
        buddy = self.ui.buddy
        if not buddy:
            return False
        if wait and buddy.busy:
            return False
        day = time.strftime('%Y-%m-%d')
        if self.shown_today.get(key) == day:
            return False
        try:
            answer, at = brein().hint_answer(key)
        except Exception:  # noqa: BLE001
            answer, at = None, 0
        if answer == 'nooit' or (answer == 'niet-nu' and time.strftime('%Y-%m-%d', time.localtime(at)) == day):
            return False
        self.shown_today[key] = day
        buttons = list(actions)
        if claude:
            buttons.append(('Vraag de AI', lambda: self.ui.ask(claude)))
        buddy.show_hint(text, buttons, on_answer=lambda a: self.answered(key, a))
        return True

    def answered(self, key, answer):
        try:
            brein().set_hint_answer(key, answer)
        except Exception:  # noqa: BLE001
            pass

    # ----- downloads -----
    def watch_downloads(self):
        folder = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) or os.path.expanduser('~/Downloads')
        if not os.path.isdir(folder):
            return
        monitor = Gio.File.new_for_path(folder).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
        monitor.connect('changed', self.download_changed)
        self.monitors.append(monitor)

    def download_changed(self, monitor, file, other, event):
        E = Gio.FileMonitorEvent
        target = other if event == E.RENAMED else file
        if event not in (E.CHANGES_DONE_HINT, E.RENAMED, E.MOVED_IN) or not target:
            return
        path = target.get_path() or ''
        name = os.path.basename(path)
        if not name or name.startswith('.') or name.lower().endswith(PARTIAL) or not os.path.isfile(path):
            return
        if time.time() - self.started < 30:
            return  # not the files that were already there at login
        actions = [('Openen', lambda: backend.open_path(path)),
                   ('Map tonen', lambda: backend.spawn(['thunar', os.path.dirname(path)]))]
        if name.lower().endswith('.deb'):
            actions = [('Installeren', lambda: backend.run_tool('deb', {}))] + actions[1:]
        self.suggest('download:' + path, '%s is gedownload.' % name, actions,
                     claude='Ik heb net "%s" gedownload in %s. Wat is het en wat kan ik ermee?' % (name, os.path.dirname(path)))

    # ----- USB sticks and other drives -----
    def mount_added(self, monitor, mount):
        root = mount.get_root()
        path = root.get_path() if root else None
        if not path or not mount.can_unmount():
            return
        name = mount.get_name()
        self.suggest('mount:%s:%d' % (name, time.time() // 60), '%s is aangesloten.' % name,
                     [('Openen', lambda: backend.spawn(['thunar', path]))],
                     claude='Ik heb "%s" aangesloten (%s). Wat staat erop?' % (name, path))

    # ----- habits from the timeline -----
    def check_habits_repeat(self):
        self.check_habits()
        return True

    def check_habits(self):
        def work():
            try:
                hits = brein().habits(time.localtime().tm_hour)
            except Exception:  # noqa: BLE001
                return
            GLib.idle_add(self.offer_habit, hits)
        threading.Thread(target=work, daemon=True).start()
        return False

    def offer_habit(self, hits):
        try:
            running = {(w.get('appId') or '').lower() for w in self.ui.shell.toplevels.list()} if self.ui.shell.toplevels else set()
        except Exception:  # noqa: BLE001
            running = set()
        for hit in hits:
            app_id = hit['id']
            if app_id[:-len('.desktop')].lower() in running or not backend.desktop_app(app_id):
                continue
            name = hit['naam'] or app_id
            self.suggest('habit:%s:%d' % (app_id, time.localtime().tm_hour // 3),
                         'Je opent rond deze tijd vaak %s. Zal ik het openen?' % name,
                         [('Openen', lambda a=app_id, n=name: self.launch(a, n))], wait=True)
            break
        return False

    def launch(self, app_id, name):
        backend.launch(app_id)
        log_event('app', app_id, name)

    # ----- file index of the second brain (Recoll, if installed) -----
    def update_index_repeat(self):
        self.update_index()
        return True

    def update_index(self):
        try:
            import recoll_index
            if not recoll_index.available() or (self.indexer and self.indexer.poll() is None):
                return False
            bat = backend.battery()
            if bat.get('present') and not bat.get('charging') and bat.get('percent', 100) < 30:
                return False  # spare an almost empty battery
            import subprocess
            self.indexer = subprocess.Popen(recoll_index.index_command(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                            start_new_session=True)
        except Exception as error:  # noqa: BLE001
            self.log('Bestandsindex bijwerken mislukt: %s' % error)
        return False

    # ----- battery -----
    def check_battery(self):
        try:
            bat = backend.battery()
        except Exception:  # noqa: BLE001
            return True
        if not bat.get('present') or bat.get('charging') or bat.get('percent', 100) > 15:
            self.battery_warned = False
            return True
        if not self.battery_warned:
            self.battery_warned = True
            self.shown_today.pop('battery', None)
            self.suggest('battery', 'De batterij is bijna leeg (%d%%). Zal ik het scherm wat donkerder zetten?' % bat['percent'],
                         [('Ja', lambda: backend.spawn(['brightnessctl', 'set', '40%']))])
        return True
