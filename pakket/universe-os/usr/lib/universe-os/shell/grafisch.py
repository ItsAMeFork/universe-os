"""How WebKit draws the Universe pages (shell and login screen). No GTK here, so the choice can be tested anywhere.

16 Oct: 0.2.15-0.2.17 let the processor draw (Mesa llvmpipe) on every pc whose graphics driver was not on a short list
(Intel, AMD, VM). On Axel's pc at home that made the picture slow and the session crashed, while the same pc runs well
with 0.2.12, which always uses WebKit's normal drawing. So normal drawing is the default again on every pc.

16 Oct, later: with normal drawing the H310M pc (NVIDIA card, nouveau) was dark again over the login screen and the
desktop, with only a text cursor; clicks and typing worked underneath (as on 13 Oct). A driver list cannot tell that pc
from the one at home, so each pc is now tested once: grafisch_proef.py shows two known colours in normal drawing and
looks whether they reach the screen. Not seen: this pc gets the safe mode (picture in shared memory, processor draws).
The result is kept per account (the login screen keeps its own) together with the drivers and the kernel, so a new
graphics card or kernel tests again.

The safe mode also comes with:
  - the kernel option universe.gfx=safe (type it in the boot menu with 'e'), or
  - the file /etc/universe-os/grafisch-veilig (stays on for this pc), or
  - no render node at all (no usable graphics driver): then the processor draws anyway.
universe.gfx=normal switches the safe mode off again, also when the file exists or the test chose it. A value set by
hand wins.
"""
import fcntl
import glob
import json
import os
import subprocess
import sys

SAFE_FILE = '/etc/universe-os/grafisch-veilig'
SAFE_VARS = {'WEBKIT_DMABUF_RENDERER_FORCE_SHM': '1', 'LIBGL_ALWAYS_SOFTWARE': '1', 'GALLIUM_DRIVER': 'llvmpipe'}
# 23 Oct, H310M with the NVIDIA driver (0.2.24): after the screen mode changed at login the world page froze on its
# first picture (Earth in the warp streaks, the planets never came) and turned pale grey-blue when the start menu opened.
# WebKit's DMA-BUF buffers do not survive that on the proprietary driver; shared memory does (the GPU still draws).
NVIDIA_VARS = {'WEBKIT_DMABUF_RENDERER_FORCE_SHM': '1'}
PROBE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grafisch_proef.py')
PROBE_TIMEOUT = 30


def state_file():
    """Where this account keeps the test result (lightdm's own home for the login screen)."""
    base = os.environ.get('XDG_STATE_HOME') or os.path.join(os.path.expanduser('~'), '.local', 'state')
    return os.path.join(base, 'universe-os', 'grafisch.json')


def choose(cmdline, safe_file, has_render_node, proef=None):
    """'safe' or 'normal', with the reason (for shell.log). proef: the remembered test result of this pc, or None."""
    options = cmdline.split()
    if 'universe.gfx=normal' in options:
        return 'normal', 'opstartoptie universe.gfx=normal'
    if 'universe.gfx=safe' in options:
        return 'safe', 'opstartoptie universe.gfx=safe'
    if safe_file:
        return 'safe', SAFE_FILE
    if not has_render_node:
        return 'safe', 'geen render-node'
    if proef == 'safe':
        return 'safe', 'proef: normaal tekenen bleef donker'
    if proef == 'normal':
        return 'normal', 'proef: normaal tekenen werkt'
    return 'normal', 'standaard'


def needs_probe(reason):
    """Only when nothing else decided: no boot option, no file, a render node and no remembered result."""
    return reason == 'standaard'


def fingerprint(drivers):
    """What the result belongs to: a different graphics driver or kernel tests again."""
    return {'drivers': list(drivers), 'kernel': os.uname().release}


def remembered(path, drivers):
    """The kept result ('normal' or 'safe') when it belongs to this pc as it is now, else None."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get('mode') not in ('normal', 'safe'):
        return None
    if any(data.get(key) != value for key, value in fingerprint(drivers).items()):
        return None
    return data['mode']


def remember(path, drivers, mode):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(dict(fingerprint(drivers), mode=mode), f)
        os.replace(tmp, path)
    except OSError:
        pass


def run_probe():
    """'normal', 'safe' or None (unknown: no screen to test on, or the test itself failed)."""
    if not (os.environ.get('WAYLAND_DISPLAY') or os.environ.get('DISPLAY')):
        return None
    env = {k: v for k, v in os.environ.items() if k not in SAFE_VARS}
    try:
        done = subprocess.run([sys.executable, PROBE], env=env, capture_output=True, text=True,
                              timeout=PROBE_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    word = done.stdout.strip().split()[-1:] or ['']
    return word[0] if word[0] in ('normal', 'safe') else None


def probed(drivers):
    """The test result of this pc, testing once when nothing is kept. A lock keeps two pages (shell and control centre)
    from testing at the same time: the second one waits and reads the first one's result."""
    path = state_file()
    mode = remembered(path, drivers)
    if mode:
        return mode
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        lock = open(path + '.lock', 'w')
    except OSError:
        return run_probe()
    with lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        mode = remembered(path, drivers)
        if mode:
            return mode
        mode = run_probe()
        if mode:
            remember(path, drivers, mode)
        return mode


def apply():
    """Sets the WebKit variables for this process (the Universe pages only; backend.program_env removes them again for
    programs started from the desktop). Returns (drivers, render node, mode, reason) for shell.log."""
    drivers = sorted({os.path.basename(os.path.realpath(link)) for link in glob.glob('/sys/class/drm/card[0-9]*/device/driver')})
    has_render_node = bool(glob.glob('/dev/dri/renderD*'))
    try:
        with open('/proc/cmdline') as f:
            cmdline = f.read()
    except OSError:
        cmdline = ''
    safe_file = os.path.exists(SAFE_FILE)
    mode, reason = choose(cmdline, safe_file, has_render_node)
    if needs_probe(reason) and not any(name in os.environ for name in SAFE_VARS):
        mode, reason = choose(cmdline, safe_file, has_render_node, probed(drivers))
    if mode == 'safe':
        for name, value in SAFE_VARS.items():
            os.environ.setdefault(name, value)
    elif 'nvidia' in drivers and 'universe.gfx=normal' not in cmdline.split():
        for name, value in NVIDIA_VARS.items():
            os.environ.setdefault(name, value)
        reason += '; nvidia: gedeeld geheugen'
    return drivers, has_render_node, mode, reason


def world_lite(cmdline, mode, drivers):
    """The simple 2D world (world-lite.html: plain icons, no animation) instead of the space world, or None.
    23 Oct (0.2.28, H310M: dark screen with only the blue glow, world never drew): the safe boot options and the
    nouveau driver in safe mode get the simple world at once; universe.world=full|lite decides by hand."""
    options = cmdline.split()
    if 'universe.world=full' in options:
        return None
    if 'universe.world=lite' in options:
        return 'opstartoptie universe.world=lite'
    if 'universe.gfx=safe' in options or 'universe.gpu=veilig' in options:
        return 'veilige grafische modus'
    if mode == 'safe' and 'nouveau' in drivers:
        return 'nouveau met processor-tekenen'
    return None


def lite_reason(graphics):
    """For the shell: graphics = the result of apply() (drivers, render node, mode, reason)."""
    try:
        with open('/proc/cmdline') as f:
            cmdline = f.read()
    except OSError:
        cmdline = ''
    return world_lite(cmdline, graphics[2], graphics[0])
