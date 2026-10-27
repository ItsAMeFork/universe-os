"""UOS-ANIM-001: the restart after an update, with the update scene. Runs the real Shell methods with a fake clock and
fake GLib timers (no GTK): start 16 s before the deadline, sounds on the beat, one restart, power only after the
shutdown tune, no double start, no restart without a successful update."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

path = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'
tree = ast.parse(path.read_text(encoding='utf-8'))
shell = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Shell')
NAMES = ('check_restart', 'restart_tick', 'begin_launch', 'schedule_launch_tick', 'launch_tick', 'begin_logout',
         'finish_logout', 'power_off_now', 'power_failed')
shell.body = [n for n in shell.body if (isinstance(n, ast.FunctionDef) and n.name in NAMES) or
              (isinstance(n, ast.Assign) and n.targets[0].id in ('RESTART_AFTER', 'LAUNCH_SECONDS', 'LAUNCH_RUNUP',
                                                                'SHUTDOWN_SOUND_AT', 'SHUTDOWN_SOUND_LENGTH'))]


class Clock:
    """time.monotonic plus GLib.timeout_add/source_remove on one fake clock."""
    def __init__(self):
        self.now, self.timers, self.next_id = 1000.0, {}, 1

    def monotonic(self):
        return self.now

    def timeout_add(self, ms, fn, *args):
        self.next_id += 1
        self.timers[self.next_id] = (self.now + ms / 1000, ms / 1000, fn, args)
        return self.next_id

    def source_remove(self, tid):
        self.timers.pop(tid, None)

    def run_until(self, until):
        while True:
            due = [(t[0], tid) for tid, t in self.timers.items() if t[0] <= until]
            if not due:
                break
            at, tid = min(due)
            self.now = at
            _, every, fn, args = self.timers.pop(tid)
            if fn(*args):
                self.timers[tid] = (self.now + every, every, fn, args)
        self.now = until


def make(status):
    clock, sounds = Clock(), []
    backend = Mock()
    backend.sound.side_effect = lambda name: sounds.append((round(clock.now - 1000, 2), name))
    backend.updates._read.return_value = status
    backend.is_live.return_value = False
    glib = SimpleNamespace(timeout_add=clock.timeout_add, source_remove=clock.source_remove)
    ns = {'GLib': glib, 'backend': backend, 'GtkLayerShell': Mock(), 'time': SimpleNamespace(monotonic=clock.monotonic),
          'boot_time': lambda: 0, 'log': lambda *a: None}
    exec(compile(ast.Module(body=[shell], type_ignores=[]), str(path), 'exec'), ns)
    obj = ns['Shell']()
    obj.logout_pending = False
    obj.logout_timer = None
    obj.claude = None
    obj.panel = obj.start = None
    obj.hide_overview = Mock()
    obj.notify = Mock()
    obj.worlds = [SimpleNamespace(window=Mock(), emit=Mock()), SimpleNamespace(window=Mock(), emit=Mock())]
    return obj, clock, backend, sounds


OK = {'restartRequired': True, 'installedAt': 50, 'version': '0.3.2'}

# 1. Successful update: scene 16 s before the deadline, sounds on the beat, restart on the deadline, power after the tune.
obj, clock, backend, sounds = make(OK)
obj.check_restart()
deadline = obj.restart_deadline
obj.check_restart()  # repeated status message: nothing new
obj.check_restart()
clock.run_until(deadline - 16.6)
assert not any(w.emit.called for w in obj.worlds), 'too early'
clock.run_until(deadline - 15)
for w in obj.worlds:  # every world gets the scene, once
    calls = [c for c in w.emit.call_args_list if c.args[0] == 'launch-countdown']
    assert len(calls) == 1 and calls[0].args[1] == {'seconds': 10, 'runup': 6, 'version': '0.3.2'}, calls
start = deadline - 16
assert sounds == [(round(start - 1000, 2), 'update-inslag')], sounds  # once, not per world
assert obj.begin_launch(16) is False and len(sounds) == 1  # double start: no-op
clock.run_until(deadline + 0.5)
counts = [t for t, n in sounds if n == 'aftellen']
assert len(counts) == 10 and [round(t - (start - 1000), 2) for t in counts] == [float(i) for i in range(6, 16)], counts
assert (round(deadline - 1000, 2), 'lancering') in sounds, sounds  # zero = the existing deadline
assert obj.logout_pending == 'reboot'
for w in obj.worlds:
    w.emit.assert_any_call('logout-begin', {'action': 'reboot'})
obj.finish_logout()  # the page says its implosion is done (~1.9 s after zero)
clock.run_until(deadline + 7.6)
assert [n for t, n in sounds].count('afsluiten') == 1 and (round(deadline + 1.9 - 1000, 2), 'afsluiten') in sounds, sounds
backend.power.assert_not_called()  # the shutdown tune (1.9 + 5.8 s) is still playing
clock.run_until(deadline + 8)
backend.power.assert_called_once_with('reboot', sound_first=False)
clock.run_until(deadline + 60)
assert backend.power.call_count == 1 and [n for t, n in sounds].count('afsluiten') == 1
print('PASS: scene 16 s before the deadline, sounds T=0/6..15/16/17.9 once, one restart after the shutdown tune')

# 2. Failed update (no restartRequired) and an update from before this boot: never a scene or a restart.
for status in ({'state': 'error', 'error': 'Installeren is niet gelukt.'},
               {'restartRequired': True, 'installedAt': -5}, {'restartRequired': False, 'installedAt': 50}):
    obj, clock, backend, sounds = make(status)
    obj.check_restart()
    clock.run_until(clock.now + 300)
    assert not sounds and not backend.power.called and not obj.logout_pending, status
print('PASS: failed or old update: no scene, no restart')

# 3. Logged out by hand during the run-up: the countdown stops, no 'lancering', no extra afsluiten, no reboot.
obj, clock, backend, sounds = make(OK)
obj.check_restart()
clock.run_until(obj.restart_deadline - 13)
obj.begin_logout('logout')
clock.run_until(obj.restart_deadline + 30)
names = [n for t, n in sounds]
assert 'lancering' not in names and 'aftellen' not in names and 'afsluiten' not in names, names
backend.power.assert_called_once_with('logout')
print('PASS: logout during the run-up: no countdown, no restart')

# 4. Power fails: the world comes back, no second restart from the shell.
obj, clock, backend, sounds = make(OK)
obj.check_restart()
backend.power.side_effect = RuntimeError('testfout')
clock.run_until(obj.restart_deadline + 30)
obj.worlds[0].emit.assert_any_call('logout-error', 'testfout')
assert backend.power.call_count == 1 and not obj.launch_reboot
obj.check_restart()
clock.run_until(obj.restart_deadline + 300)
assert backend.power.call_count == 1
print('PASS: failed power action: world restored, no second restart (shutdown -r +3 stays the safety net)')

# 5. Late start (less than 16 s left, e.g. a suspended timer): countdown only, restart still on the deadline.
obj, clock, backend, sounds = make(OK)
obj.restart_deadline, obj.restart_version = clock.now + 12, ''
obj.begin_launch(12)
obj.worlds[0].emit.assert_any_call('launch-countdown', {'seconds': 10, 'runup': 2, 'version': ''})
clock.run_until(clock.now + 12.1)
assert 'update-inslag' not in [n for t, n in sounds] and obj.logout_pending == 'reboot'
print('PASS: late start: shorter run-up, no off-beat scene sound, restart on the deadline')
