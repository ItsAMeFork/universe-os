"""0.2.25 (23 Oct, H310M NVIDIA): shared-memory WebKit buffers on nvidia, settle after a mode change, intro never waits forever."""
import importlib.machinery, importlib.util, os, sys
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pakket', 'universe-os')
sys.path.insert(0, os.path.join(root, 'usr/lib/universe-os/shell'))
import grafisch
for k in ('WEBKIT_DMABUF_RENDERER_FORCE_SHM', 'LIBGL_ALWAYS_SOFTWARE', 'GALLIUM_DRIVER'):
    os.environ.pop(k, None)
grafisch.glob.glob = lambda pat: ['/sys/class/drm/card0/device/driver'] if 'card' in pat else ['/dev/dri/renderD128']
grafisch.os.path.realpath = lambda p: '/sys/bus/pci/drivers/nvidia'
grafisch.probed = lambda d: 'normal'
drivers, _, mode, reason = grafisch.apply()
assert drivers == ['nvidia'] and mode == 'normal', (drivers, mode)
assert os.environ.get('WEBKIT_DMABUF_RENDERER_FORCE_SHM') == '1' and 'LIBGL_ALWAYS_SOFTWARE' not in os.environ
loader = importlib.machinery.SourceFileLoader('displays', os.path.join(root, 'usr/lib/universe-os/universe-displays'))
spec = importlib.util.spec_from_loader('displays', loader); d = importlib.util.module_from_spec(spec); loader.exec_module(d)
seen = []
d.outputs = lambda: (seen.append(1), [{'name': 'HDMI-A-1', 'width': 1920 if len(seen) > 2 else 2560, 'height': 1080 if len(seen) > 2 else 1440}])[1]
d.time.sleep = lambda s: None
d.settle([('HDMI-A-1', 1920, 1080)])
assert len(seen) == 3
w = open(os.path.join(root, 'usr/share/universe-os/ui/world.js')).read()
assert 'wait(6000)' in w
print('ok')
