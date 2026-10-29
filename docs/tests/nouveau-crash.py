"""0.2.30, pc beneden (GT 710 / Kepler): geen nvidia 550 op Kepler, nouveau-crash -> processor-tekenen vóór 2D."""
import importlib.machinery
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
gpu = importlib.machinery.SourceFileLoader('g', str(ROOT / 'live/config/includes.chroot_after_packages/usr/lib/universe-os/universe-gpu')).load_module()
gt710 = 'pci:v000010DEd0000128Bsv000019DAsd00007326bc03sc00i00'
gtx750 = 'pci:v000010DEd00001380sv00001043sd00008434bc03sc00i00'
wild = ['pci:v000010DEd*sv*sd*bc03sc00i00']  # what Debian's nvidia 550 module really lists
assert gpu.device_id(gt710) == 0x128B
assert gpu.choose('quiet', [gt710], wild)[0] == 'nouveau'
assert gpu.choose('quiet', [gtx750], wild)[0] == 'nvidia'
assert gpu.choose('quiet universe.gpu=nvidia', [gt710], wild)[0] == 'nvidia'

sys.path.insert(0, str(ROOT / 'pakket/universe-os/usr/lib/universe-os/shell'))
for k in ('LIBGL_ALWAYS_SOFTWARE', 'GALLIUM_DRIVER', 'WEBKIT_DMABUF_RENDERER_FORCE_SHM'):
    os.environ.pop(k, None)
import grafisch  # noqa: E402
assert grafisch.to_processor(['i915']) is False and 'LIBGL_ALWAYS_SOFTWARE' not in os.environ
assert grafisch.to_processor(['nouveau']) is True and os.environ['LIBGL_ALWAYS_SOFTWARE'] == '1'
assert grafisch.to_processor(['nouveau']) is False  # only once
src = (ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/webview.py').read_text()
assert 'grafisch.to_processor(WEBKIT_GRAPHICS[0])' in src
assert grafisch.NOUVEAU_VARS['mesa_glthread'] == 'false'
print('PASS: nouveau-crash')
