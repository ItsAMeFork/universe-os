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
import re
import subprocess
import sys
import time

SAFE_FILE = '/etc/universe-os/grafisch-veilig'
SAFE_VARS = {'WEBKIT_DMABUF_RENDERER_FORCE_SHM': '1', 'LIBGL_ALWAYS_SOFTWARE': '1', 'GALLIUM_DRIVER': 'llvmpipe'}
# 23 Oct, H310M with the NVIDIA driver (0.2.24): after the screen mode changed at login the world page froze on its
# first picture (Earth in the warp streaks, the planets never came) and turned pale grey-blue when the start menu opened.
# WebKit's DMA-BUF buffers do not survive that on the proprietary driver; shared memory does (the GPU still draws).
NVIDIA_VARS = {'WEBKIT_DMABUF_RENDERER_FORCE_SHM': '1'}
# 24 Oct (0.2.30, pc beneden: GT 710 on nouveau): the world page's process died again and again with 'free(): invalid
# pointer' / 'realloc(): invalid pointer' (nouveau's GL is not safe with several GL threads). Shared memory buffers and
# no Mesa GL thread take two of those threads away; if the page still stops, webview.py lets the processor draw it.
NOUVEAU_VARS = {'WEBKIT_DMABUF_RENDERER_FORCE_SHM': '1', 'mesa_glthread': 'false'}
# 0.2.31 'lichte hardware'-modus (pc beneden: GT 710 op nouveau, en oude kantoor-pc's in het algemeen).
# WebKitGTK 2.54 tekent pagina's met Skia op de GPU in aparte werkthreads (standaard 1-2 GPU-threads). nouveau is niet
# veilig met meerdere GL-threads in één proces (Mesa nouveau multi-context, Ubuntu LP #2099654, Mesa #1110): dat is de
# 'free(): invalid pointer'. In de lichte modus tekent Skia de tegels met de processor (2 threads, geen GL) en doet de
# videokaart alleen het samenvoegen (compositing, één thread). Dat is ook op oude Intel/AMD sneller dan GPU-tegels.
# Bron: WebKitGTK environment-variables (WEBKIT_SKIA_*), WebKit PR #34502.
LIGHT_VARS = {'WEBKIT_SKIA_ENABLE_CPU_RENDERING': '1', 'WEBKIT_SKIA_CPU_PAINTING_THREADS': '2',
              'WEBKIT_SKIA_GPU_PAINTING_THREADS': '0', 'WEBKIT_DMABUF_RENDERER_FORCE_SHM': '1', 'mesa_glthread': 'false'}
LIGHT_FILE = '/etc/universe-os/grafisch-licht'
# Gezet door de installer als de gebruiker de lichte modus uitvinkte: systeembreed geen automatische lichte modus.
NORMAL_FILE = '/etc/universe-os/grafisch-normaal'
# Oude Intel-graphics (Gen3 t/m Gen7.5: GMA 3xxx/4500, HD 2000-4600, Bay Trail): i915/crocus, weinig rekenkracht.
# Broadwell (0x16xx) en nieuwer niet. Ranges van PCI device-id's.
OLD_INTEL = ((0x0040, 0x0200), (0x0400, 0x0E00), (0x0F00, 0x0F40), (0x2500, 0x2F00), (0x2770, 0x27B0),
             (0x8100, 0x8110), (0xA000, 0xA020))
# Drivers die altijd licht gaan: nouveau (alle NVIDIA zonder eigen driver), radeon (r600/r300/SI/CIK in Debian),
# en eenvoudige servervideo zonder 3D.
LIGHT_DRIVERS = ('nouveau', 'radeon', 'ast', 'mgag200', 'gma500', 'cirrus-qemu', 'bochs-drm')
# 0.2.32: ook op PCI-id, zodat de keuze niet afhangt van welk stuurprogramma op dat moment al geladen is (nouveau laadt
# pas via universe-gpu.service; tot dan is er alleen simpledrm). NVIDIA voor Maxwell (Kepler en ouder, o.a. GT 710 =
# GK208B 0x128b) krijgt altijd nouveau, en is dus altijd licht. Een NVIDIA-kaart zonder het eigen nvidia-stuurprogramma
# draait ook op nouveau of simpledrm: ook licht.
FIRST_MAXWELL_ID = 0x1340
# AMD-kaarten van voor GCN 1.2 (r100 t/m Southern/Sea Islands, ook Kaveri/Kabini-APU's): Debian gebruikt daar radeon.
OLD_AMD = ((0x1304, 0x131E), (0x4100, 0x5FFF), (0x6600, 0x6680), (0x6700, 0x67C0), (0x6800, 0x6860), (0x6880, 0x6900),
           (0x7100, 0x7300), (0x9400, 0x9A00), (0x9830, 0x9860))
# Renderer-strings (eglinfo/glxinfo) van oude kaarten, als laatste controle.
OLD_RENDERER = re.compile(r'\bNV[0-9A-F]{2,3}\b|\bG[KF]1[0-9]{2}|\bG[KF]2[0-9]{2}|\bGT2[0-9]{2}\b|Sandybridge|Ivybridge|Haswell|'
                          r'Ironlake|Bay ?Trail|\bi915\b|\bi965\b|\(radeon\)|\b(RV|R)[1-9][0-9]{2}\b|CEDAR|REDWOOD|JUNIPER|'
                          r'CYPRESS|BARTS|TURKS|CAICOS|CAYMAN|ARUBA|PALM|SUMO|TAHITI|PITCAIRN|VERDE|OLAND|HAINAN|'
                          r'BONAIRE|KAVERI|KABINI|MULLINS|HAWAII', re.I)


def pci_cards(root='/sys/bus/pci/devices'):
    """[(vendor, device)] of every display controller."""
    cards = []
    for dev in sorted(glob.glob(os.path.join(root, '*'))):
        try:
            klass = open(os.path.join(dev, 'class')).read().strip()
            if not klass.startswith('0x03'):
                continue
            cards.append((int(open(os.path.join(dev, 'vendor')).read(), 16), int(open(os.path.join(dev, 'device')).read(), 16)))
        except (OSError, ValueError):
            continue
    return cards


def old_card(vendor, device, drivers=()):
    """Reason when this PCI display card is old by its id alone, else None."""
    if vendor == 0x10de and (device < FIRST_MAXWELL_ID or 'nvidia' not in drivers):
        return 'oude/zwakke videokaart (NVIDIA 0x%04x, nouveau)' % device
    if vendor == 0x1002 and 'amdgpu' not in drivers and any(lo <= device < hi for lo, hi in OLD_AMD):
        return 'oude/zwakke videokaart (AMD 0x%04x, radeon)' % device
    if vendor == 0x8086 and old_intel(device):
        return 'oude Intel-graphics (0x%04x)' % device
    return None


def renderer_string(timeout=6):
    """OpenGL renderer string of this session (eglinfo/glxinfo), '' when unknown."""
    if os.environ.get('UNIVERSE_GFX_NO_RENDERER'):
        return ''
    for cmd in (['eglinfo', '-B'], ['glxinfo', '-B']):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        for line in out.splitlines():
            if 'renderer' in line.lower() and ':' in line:
                return line.split(':', 1)[1].strip()
    return ''


def bound_drivers(root='/sys'):
    """Kernel drivers of the display cards: drm cards plus the PCI display controllers themselves."""
    names = {os.path.basename(os.path.realpath(l)) for l in glob.glob(os.path.join(root, 'class/drm/card[0-9]*/device/driver'))}
    for dev in glob.glob(os.path.join(root, 'bus/pci/devices/*')):
        try:
            if open(os.path.join(dev, 'class')).read().startswith('0x03') and os.path.exists(os.path.join(dev, 'driver')):
                names.add(os.path.basename(os.path.realpath(os.path.join(dev, 'driver'))))
        except OSError:
            continue
    return sorted(names)


def wait_for_driver(seconds=10, root='/sys'):
    """Wait (max seconds) until every PCI display card has its own driver (not only simpledrm/efifb): nouveau is loaded
    late by universe-gpu.service and needs firmware. Returns the drivers."""
    deadline = time.monotonic() + seconds
    while True:
        pending = []
        for dev in glob.glob(os.path.join(root, 'bus/pci/devices/*')):
            try:
                if open(os.path.join(dev, 'class')).read().startswith('0x03') and not os.path.exists(os.path.join(dev, 'driver')):
                    pending.append(dev)
            except OSError:
                continue
        if not pending or time.monotonic() >= deadline:
            return bound_drivers(root)
        time.sleep(0.5)


def old_intel(device):
    return any(lo <= device < hi for lo, hi in OLD_INTEL)


def light_setting(path=None):
    """'auto' | 'on' | 'off' from the user's settings (Controlecentrum > Vormgeving > Lichte grafische modus)."""
    if path is None:
        base = os.environ.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'), '.config')
        path = os.path.join(base, 'universe-os', 'settings.json')
    try:
        with open(path) as f:
            value = json.load(f).get('lightGraphics', 'auto')
    except (OSError, ValueError, AttributeError):
        return 'auto'
    return value if value in ('auto', 'on', 'off') else 'auto'


def choose_light(cmdline, drivers, cards=(), setting='auto', light_file=False, crashed=False, cores=4, mem_gb=0,
                 normal_file=False, renderer=''):
    """Reason (str) for the light hardware mode, or None. Modern and game cards (nvidia, amdgpu, new Intel) stay as
    they are unless asked for by hand or the world crashed there before."""
    options = cmdline.split()
    if 'universe.gfx=licht' in options:
        return 'opstartoptie universe.gfx=licht'
    if 'universe.gfx=normal' in options or 'universe.gfx=vol' in options:
        return None
    if setting == 'on':
        return 'instelling: lichte grafische modus aan'
    if setting == 'off':
        return None
    if light_file:
        return LIGHT_FILE
    if normal_file and not crashed:
        return None
    for name in drivers:
        if name in LIGHT_DRIVERS:
            return 'oude/zwakke videokaart (%s)' % name
    for vendor, device in cards:
        reason = old_card(vendor, device, drivers)
        if reason and not (vendor == 0x8086 and ('nvidia' in drivers or 'amdgpu' in drivers)):
            return reason
    if renderer and OLD_RENDERER.search(renderer):
        return 'oude/zwakke videokaart (renderer %s)' % renderer
    if crashed:
        return 'wereld crashte eerder op deze pc'
    if cores <= 2 and 0 < mem_gb <= 4:
        return 'zwakke pc (%d kernen, %d GB)' % (cores, mem_gb)
    return None


def crash_file():
    return os.path.join(os.path.dirname(state_file()), 'grafisch-crash.json')


def crashed_before(drivers):
    try:
        with open(crash_file()) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and all(data.get(k) == v for k, v in fingerprint(drivers).items())


def remember_crash(drivers):
    try:
        os.makedirs(os.path.dirname(crash_file()), exist_ok=True)
        with open(crash_file(), 'w') as f:
            json.dump(fingerprint(drivers), f)
    except OSError:
        pass


def light_active():
    return os.environ.get('UNIVERSE_GFX_LIGHT') == '1'


def set_light():
    for name, value in LIGHT_VARS.items():
        os.environ[name] = value
    os.environ['UNIVERSE_GFX_LIGHT'] = '1'


def to_light(drivers):
    """After a world crash with normal drawing: light mode from now on (new page processes inherit it) and remembered
    for the next login. True when it switched. Not when the user chose normal/off by hand, or already light/soft."""
    try:
        with open('/proc/cmdline') as f:
            cmdline = f.read()
    except OSError:
        cmdline = ''
    if light_active() or os.environ.get('LIBGL_ALWAYS_SOFTWARE') == '1':
        return False
    if 'universe.gfx=normal' in cmdline.split() or light_setting() == 'off':
        return False
    remember_crash(drivers)
    set_light()
    return True


PROBE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grafisch_proef.py')
PROBE_TIMEOUT = 30


def state_file():
    """Where this account keeps the test result (lightdm's own home for the login screen)."""
    base = os.environ.get('XDG_STATE_HOME') or os.path.join(os.path.expanduser('~'), '.local', 'state')
    return os.path.join(base, 'universe-os', 'grafisch.json')


def choose(cmdline, safe_file, has_render_node, proef=None, nvidia=False):
    """'safe' or 'normal', with the reason (for shell.log). proef: the remembered test result of this pc, or None.
    nvidia: the own NVIDIA driver is active (0.2.29): never tested and a 'safe' test result never makes the processor
    draw there (24 Oct, NVIDIA pc: the test said 'safe', the world was too slow with llvmpipe and fell back to 2D)."""
    options = cmdline.split()
    if 'universe.gfx=normal' in options:
        return 'normal', 'opstartoptie universe.gfx=normal'
    if 'universe.gfx=safe' in options:
        return 'safe', 'opstartoptie universe.gfx=safe'
    if safe_file:
        return 'safe', SAFE_FILE
    if not has_render_node:
        return 'safe', 'geen render-node'
    if nvidia:
        return 'normal', 'nvidia: geen proef'
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
    drivers = wait_for_driver()
    has_render_node = bool(glob.glob('/dev/dri/renderD*'))
    try:
        with open('/proc/cmdline') as f:
            cmdline = f.read()
    except OSError:
        cmdline = ''
    safe_file = os.path.exists(SAFE_FILE)
    nvidia = 'nvidia' in drivers
    mode, reason = choose(cmdline, safe_file, has_render_node, nvidia=nvidia)
    # 0.2.31: light mode asked for by hand (boot option, setting 'on', file): no colour test, the GPU composites.
    forced_light = has_render_node and not safe_file and 'universe.gfx=safe' not in cmdline.split() and (
        'universe.gfx=licht' in cmdline.split() or light_setting() == 'on' or os.path.exists(LIGHT_FILE))
    if forced_light and reason == 'standaard':
        reason = 'lichte modus met de hand gekozen: geen proef'
    if needs_probe(reason) and not any(name in os.environ for name in SAFE_VARS):
        mode, reason = choose(cmdline, safe_file, has_render_node, probed(drivers), nvidia)
    light = None
    if mode != 'safe':
        try:
            mem_gb = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') // (1 << 30)
        except (OSError, ValueError):
            mem_gb = 0
        light = choose_light(cmdline, drivers, pci_cards(), light_setting(), os.path.exists(LIGHT_FILE),
                             crashed_before(drivers), os.cpu_count() or 4, mem_gb,
                             os.path.exists(NORMAL_FILE))
        if not light and light_setting() == 'auto' and not os.path.exists(NORMAL_FILE) and 'universe.gfx=normal' not in cmdline.split():
            light = choose_light('', [], (), renderer=renderer_string())
    if light:
        set_light()
        reason += '; lichte hardware-modus: %s' % light
    elif mode == 'safe':
        for name, value in SAFE_VARS.items():
            os.environ.setdefault(name, value)
    elif 'nvidia' in drivers and 'universe.gfx=normal' not in cmdline.split():
        for name, value in NVIDIA_VARS.items():
            os.environ.setdefault(name, value)
        reason += '; nvidia: gedeeld geheugen'
    elif 'nouveau' in drivers and 'universe.gfx=normal' not in cmdline.split():
        for name, value in NOUVEAU_VARS.items():
            os.environ.setdefault(name, value)
        reason += '; nouveau: gedeeld geheugen, geen GL-thread'
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
    if mode == 'safe' and 'nouveau' in drivers and 'universe.gfx=safe' not in options:
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


def to_processor(drivers):
    """After the world page crashed on nouveau with normal drawing: let the processor draw the pages from now on (new
    page processes inherit it). True when it switched, False when it already was (or the user chose normal by hand)."""
    try:
        with open('/proc/cmdline') as f:
            cmdline = f.read()
    except OSError:
        cmdline = ''
    if 'nouveau' not in drivers or 'universe.gfx=normal' in cmdline.split():
        return False
    if os.environ.get('LIBGL_ALWAYS_SOFTWARE') == '1':
        return False
    for name, value in SAFE_VARS.items():
        os.environ[name] = value
    return True


def detect_light():
    """Reason for the light mode on this pc from the hardware alone (installer, Calamares step 'Beeld'), or None."""
    drivers = wait_for_driver()
    try:
        mem_gb = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') // (1 << 30)
    except (OSError, ValueError):
        mem_gb = 0
    return choose_light('', drivers, pci_cards(), cores=os.cpu_count() or 4, mem_gb=mem_gb, renderer=renderer_string())
