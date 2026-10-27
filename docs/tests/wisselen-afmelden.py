"""g3: universe-wissel (vergrendelen -> inlogscherm) en echt afmelden, met nagebootste dm-tool/loginctl/gtklock op PATH."""
import os, shutil, stat, subprocess, sys, tempfile, textwrap, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'pakket/universe-os'
WISSEL = ROOT / 'usr/bin/universe-wissel'
sys.path.insert(0, str(ROOT / 'usr/lib/universe-os/shell'))


def script(map_, naam, tekst):
    p = Path(map_) / naam
    p.write_text('#!/bin/sh\n' + textwrap.dedent(tekst))
    p.chmod(p.stat().st_mode | stat.S_IEXEC)


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.log = Path(self.tmp) / 'log'
        self.bin = Path(self.tmp) / 'bin'
        self.bin.mkdir()
        self.env = {'PATH': '%s:/usr/bin:/bin' % self.bin, 'LOG': str(self.log), 'HOME': self.tmp}
        # 0.3.0: universe-wissel checks that the greeter became the active session; this logind says so once a
        # switch was asked (and the file 'negeer' is absent: LightDM dropped the request, see test_opnieuw_vragen)
        script(self.bin, 'loginctl', f'''case "$*" in
            *show-seat*) echo c1 ;;
            *show-session*) if [ ! -e "{self.tmp}/negeer" ] && grep -qi switch "$LOG" 2>/dev/null; then echo greeter; else echo user; fi ;;
            esac
            ''')

    def tearDown(self):
        subprocess.run(['pkill', '-f', self.tmp], check=False)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def regels(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def gtklock_nep(self, vertraging='0.3'):
        # nagebootste universe-lock: start een proces met de naam "gtklock" (zoals pgrep -x het verwacht)
        shutil.copy('/bin/sleep', self.bin / 'gtklock')
        script(self.bin, 'universe-lock', f'echo "lock $*" >> "$LOG"\nsleep {vertraging}\n"{self.bin}/gtklock" 20 &\n')

    def wissel(self, **extra):
        return subprocess.run(['sh', str(WISSEL)], env={**self.env, **extra}, capture_output=True, text=True, timeout=15)


class Wissel(Basis):
    def test_eerst_vergrendelen_dan_greeter(self):
        self.gtklock_nep()
        script(self.bin, 'dm-tool', 'echo "dm-tool $*" >> "$LOG"\n[ -n "$(pgrep -x gtklock)" ] && echo "vergrendeld" >> "$LOG"\n')
        r = self.wissel()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.regels(), ['lock --direct', 'dm-tool switch-to-greeter', 'vergrendeld'])

    def test_al_vergrendeld_niet_dubbel(self):
        self.gtklock_nep()
        script(self.bin, 'dm-tool', 'echo "dm-tool $*" >> "$LOG"\n')
        sl = subprocess.Popen([str(self.bin / 'gtklock'), '20'])
        try:
            r = self.wissel()
        finally:
            sl.kill()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.regels(), ['dm-tool switch-to-greeter'])

    def test_maximaal_3_seconden_wachten(self):
        script(self.bin, 'universe-lock', 'echo "lock $*" >> "$LOG"\n')  # gtklock komt nooit
        script(self.bin, 'dm-tool', 'echo "dm-tool $*" >> "$LOG"\n')
        import time
        t = time.monotonic()
        r = self.wissel()
        self.assertLess(time.monotonic() - t, 5)
        self.assertGreater(time.monotonic() - t, 2.5)
        self.assertIn('vergrendelen duurde te lang', r.stderr)
        self.assertEqual(self.regels(), ['lock --direct', 'dm-tool switch-to-greeter'])

    def test_terugval_dbus_send(self):
        self.gtklock_nep('0')
        script(self.bin, 'dm-tool', 'exit 1\n')
        script(self.bin, 'dbus-send', 'echo "dbus-send $*" >> "$LOG"\n')
        r = self.wissel(XDG_SEAT_PATH='/org/freedesktop/DisplayManager/Seat0')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('dbus-send --system --type=method_call --dest=org.freedesktop.DisplayManager '
                      '/org/freedesktop/DisplayManager/Seat0 org.freedesktop.DisplayManager.Seat.SwitchToGreeter', self.regels())

    def test_opnieuw_vragen_als_greeter_niet_komt(self):
        self.gtklock_nep('0')
        negeer = Path(self.tmp) / 'negeer'
        negeer.touch()
        # the first request is dropped by "LightDM"; dm-tool removes the marker so the second one works
        script(self.bin, 'dm-tool', f'echo "dm-tool $*" >> "$LOG"\n[ -e "{negeer}.1" ] && rm -f "{negeer}"\ntouch "{negeer}.1"\n')
        r = self.wissel()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('poging 1: inlogscherm niet actief', r.stderr)
        self.assertEqual(self.regels().count('dm-tool switch-to-greeter'), 2)

    def test_mislukt_geeft_fout(self):
        self.gtklock_nep('0')
        r = self.wissel()  # geen dm-tool en geen XDG_SEAT_PATH
        self.assertEqual(r.returncode, 1)
        self.assertIn('kon niet naar het inlogscherm', r.stderr)


class Afmelden(Basis):
    def run_end(self, sid, loginctl_rc=0, loginctl=True):
        import backend
        if loginctl:
            script(self.bin, 'loginctl', f'echo "loginctl $*" >> "$LOG"\nexit {loginctl_rc}\n')
        script(self.bin, 'labwc', 'echo "labwc $*" >> "$LOG"\n')
        old = {k: os.environ.get(k) for k in ('PATH', 'XDG_SESSION_ID', 'LOG')}
        os.environ.update({'PATH': self.env['PATH'], 'LOG': self.env['LOG']})
        os.environ.pop('XDG_SESSION_ID', None)
        if sid:
            os.environ['XDG_SESSION_ID'] = sid
        try:
            backend.power('logout')
            import time; time.sleep(0.5)  # spawn is losgekoppeld
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def test_terminate_session(self):
        self.run_end('c7')
        self.assertEqual(self.regels(), ['loginctl terminate-session c7'])

    def test_terugval_labwc_exit(self):
        self.run_end('c7', loginctl_rc=1)
        self.assertEqual(self.regels(), ['loginctl terminate-session c7', 'labwc --exit'])

    def test_zonder_sessie_id_labwc_exit(self):
        self.run_end(None)
        self.assertEqual(self.regels(), ['labwc --exit'])

    def test_switch_start_wissel(self):
        import backend
        script(self.bin, 'universe-wissel', 'echo "wissel" >> "$LOG"\n')
        old = {k: os.environ.get(k) for k in ('PATH', 'LOG')}
        os.environ.update({'PATH': self.env['PATH'], 'LOG': self.env['LOG']})
        try:
            backend.power('switch')
            import time; time.sleep(0.5)
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.assertEqual(self.regels(), ['wissel'])


class Menu(unittest.TestCase):
    def test_knoppen_aanwezig(self):
        ui = ROOT / 'usr/share/universe-os/ui'
        start = (ui / 'start.js').read_text()
        self.assertIn("label:'Andere gebruiker'", start)
        self.assertIn("action:'switch'", start)
        self.assertIn("ask('Afmelden','logout')", start)  # afmelden vraagt nog steeds bevestiging
        self.assertIn("action:'switch'", (ui / 'panel.js').read_text())


if __name__ == '__main__':
    unittest.main(verbosity=1)
