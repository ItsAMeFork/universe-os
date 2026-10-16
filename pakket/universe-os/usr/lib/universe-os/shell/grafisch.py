"""How WebKit draws the Universe pages (shell and login screen). No GTK here, so the choice can be tested anywhere.

16 Oct: 0.2.15-0.2.17 let the processor draw (Mesa llvmpipe) on every pc whose graphics driver was not on a short list
(Intel, AMD, VM). On Axel's pc at home that made the picture slow and the session crashed, while the same pc runs well
with 0.2.12, which always uses WebKit's normal drawing. So normal drawing is the default again on every pc. The safe
mode (picture in shared memory, processor draws) stays available for a pc that needs it, such as the H310M pc where the
login screen stayed dark (13 Oct):
  - the kernel option universe.gfx=safe (type it in the boot menu with 'e'), or
  - the file /etc/universe-os/grafisch-veilig (stays on for this pc), or
  - no render node at all (no usable graphics driver): then the processor draws anyway.
universe.gfx=normal switches the safe mode off again, also when the file exists. A value set by hand wins.
"""
import glob
import os

SAFE_FILE = '/etc/universe-os/grafisch-veilig'
SAFE_VARS = {'WEBKIT_DMABUF_RENDERER_FORCE_SHM': '1', 'LIBGL_ALWAYS_SOFTWARE': '1', 'GALLIUM_DRIVER': 'llvmpipe'}


def choose(cmdline, safe_file, has_render_node):
    """'safe' or 'normal', with the reason (for shell.log)."""
    options = cmdline.split()
    if 'universe.gfx=normal' in options:
        return 'normal', 'opstartoptie universe.gfx=normal'
    if 'universe.gfx=safe' in options:
        return 'safe', 'opstartoptie universe.gfx=safe'
    if safe_file:
        return 'safe', SAFE_FILE
    if not has_render_node:
        return 'safe', 'geen render-node'
    return 'normal', 'standaard'


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
    mode, reason = choose(cmdline, os.path.exists(SAFE_FILE), has_render_node)
    if mode == 'safe':
        for name, value in SAFE_VARS.items():
            os.environ.setdefault(name, value)
    return drivers, has_render_node, mode, reason
