"""0.2.29 (24 Oct, NVIDIA pc: blue/purple test page after login, then 2D): with the own nvidia driver no test and never
processor drawing from a test result; the test page is neutral dark; world.js waits longer when the processor draws."""
import os, sys
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pakket', 'universe-os')
sys.path.insert(0, os.path.join(root, 'usr/lib/universe-os/shell'))
import grafisch
boot = 'BOOT_IMAGE=/boot/vmlinuz ro quiet'
assert grafisch.choose(boot, False, True, nvidia=True) == ('normal', 'nvidia: geen proef')
assert not grafisch.needs_probe(grafisch.choose(boot, False, True, nvidia=True)[1])
assert grafisch.choose(boot, False, True, 'safe', True)[0] == 'normal'
assert grafisch.choose(boot, False, True, 'safe')[0] == 'safe'  # nouveau/others unchanged
assert grafisch.choose(boot + ' universe.gfx=safe', False, True, nvidia=True)[0] == 'safe'  # asked for by hand
for k in grafisch.SAFE_VARS:
    os.environ.pop(k, None)
grafisch.glob.glob = lambda pat: ['/sys/class/drm/card0/device/driver'] if 'card' in pat else ['/dev/dri/renderD128']
grafisch.os.path.realpath = lambda p: '/sys/bus/pci/drivers/nvidia'
def no_probe(d):
    raise AssertionError('proef op nvidia')
grafisch.probed = no_probe
drivers, _, mode, reason = grafisch.apply()
assert mode == 'normal' and 'LIBGL_ALWAYS_SOFTWARE' not in os.environ
assert os.environ.get('WEBKIT_DMABUF_RENDERER_FORCE_SHM') == '1'
import types
src = open(os.path.join(root, 'usr/lib/universe-os/shell/grafisch_proef.py')).read()  # no gi here: read the constants
p = types.SimpleNamespace(); ns = {}
exec(src[src.index('LEFT ='):src.index('def ppm_pixels')], ns); p.__dict__.update(ns)
assert all(c < 0x30 for c in p.LEFT + p.RIGHT)
assert not p.matches(p.LEFT, p.RIGHT) and not p.matches(p.RIGHT, p.LEFT)
assert 'Beeld wordt getest' in p.PAGE
w = open(os.path.join(root, 'usr/share/universe-os/ui/world.js')).read()
assert '(SOFT_GFX||LIGHT_GFX)?25000:12000' in w and '(SOFT_GFX||LIGHT_GFX)?25000:14000' in w
print('ok')
