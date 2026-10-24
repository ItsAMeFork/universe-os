"""0.2.31 lichte hardware-modus: oude/zwakke videokaarten (GT 710 op nouveau, oude Intel/Radeon) krijgen automatisch
CPU-tegels + GPU-compositing en een lichtere wereld; moderne kaarten en game-pc's blijven ongemoeid."""
import importlib.util
import importlib.machinery
import json
import os
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
shell = root / 'pakket/universe-os/usr/lib/universe-os/shell'
spec = importlib.util.spec_from_file_location('grafisch', shell / 'grafisch.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

boot = 'BOOT_IMAGE=/boot/vmlinuz quiet splash'
c = g.choose_light
# Automatisch licht: nouveau (GT 710/730/610), radeon (r600, GCN1/2 in Debian), oude Intel (HD 2000-4600, GMA).
assert c(boot, ['nouveau']).startswith('oude/zwakke videokaart')
assert c(boot, ['radeon'])
assert c(boot, ['i915'], [(0x8086, 0x0412)])          # HD 4600 (Haswell)
assert c(boot, ['i915'], [(0x8086, 0x0152)])          # HD 2500 (Ivy Bridge)
assert c(boot, ['i915'], [(0x8086, 0x2A42)])          # GMA 4500
# Ongemoeid: eigen NVIDIA-driver, amdgpu, nieuwe Intel (Skylake 0x1912, Coffee Lake 0x3E92, Alder Lake 0x4680), virtio.
assert c(boot, ['nvidia']) is None
assert c(boot, ['amdgpu']) is None
for dev in (0x1912, 0x3E92, 0x4680, 0x1616):
    assert c(boot, ['i915'], [(0x8086, dev)]) is None, hex(dev)
assert c(boot, ['virtio_gpu']) is None
# Game-pc met NVIDIA + oude Intel iGPU: blijft vol.
assert c(boot, ['i915', 'nvidia'], [(0x8086, 0x0412), (0x10de, 0x2484)]) is None
# Handmatig: opstartoptie, instelling, bestand; universe.gfx=normal en instelling 'uit' winnen van de automaat.
assert c(boot + ' universe.gfx=licht', ['nvidia']) == 'opstartoptie universe.gfx=licht'
assert c(boot, ['amdgpu'], setting='on')
assert c(boot, ['amdgpu'], light_file=True) == g.LIGHT_FILE
assert c(boot + ' universe.gfx=normal', ['nouveau']) is None
assert c(boot, ['nouveau'], setting='off') is None
# Na een crash, en op een zwakke pc.
assert c(boot, ['amdgpu'], crashed=True)
assert c(boot, ['i915'], [(0x8086, 0x3E92)], cores=2, mem_gb=4)
assert c(boot, ['i915'], [(0x8086, 0x3E92)], cores=8, mem_gb=16) is None
# Variabelen: CPU-tegels, geen GPU-werkthreads (nouveau is niet thread-safe), gedeeld geheugen, geen glthread.
v = g.LIGHT_VARS
assert v['WEBKIT_SKIA_ENABLE_CPU_RENDERING'] == '1' and v['WEBKIT_SKIA_GPU_PAINTING_THREADS'] == '0'
assert v['WEBKIT_DMABUF_RENDERER_FORCE_SHM'] == '1' and v['mesa_glthread'] == 'false'
assert 'WEBKIT_DISABLE_DMABUF_RENDERER' not in v  # crasht WebKitGTK 2.52+ (null backing store)
assert 'LIBGL_ALWAYS_SOFTWARE' not in v            # de videokaart blijft samenvoegen
# Instelling uit settings.json.
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, 's.json')
    assert g.light_setting(p) == 'auto'
    json.dump({'lightGraphics': 'on'}, open(p, 'w'))
    assert g.light_setting(p) == 'on'
    json.dump({'lightGraphics': 'kapot'}, open(p, 'w'))
    assert g.light_setting(p) == 'auto'
    # Crash onthouden per driver+kernel; to_light zet de modus aan en daarna niet nog eens.
    os.environ['XDG_STATE_HOME'] = d
    os.environ['XDG_CONFIG_HOME'] = d
    for k in list(v) + ['UNIVERSE_GFX_LIGHT', 'LIBGL_ALWAYS_SOFTWARE']:
        os.environ.pop(k, None)
    assert not g.crashed_before(['amdgpu'])
    if 'universe.gfx=normal' not in open('/proc/cmdline').read():
        assert g.to_light(['amdgpu']) and g.light_active()
        assert g.crashed_before(['amdgpu']) and not g.crashed_before(['nouveau'])
        assert not g.to_light(['amdgpu'])
# Pagina's: gfx=licht, en de wereld gebruikt hem.
ui = root / 'pakket/universe-os/usr/share/universe-os/ui'
assert "params.append('gfx=licht')" in (shell / 'webview.py').read_text()
w = (ui / 'world.js').read_text()
for part in ("get('gfx')==='licht'", 'STARS.slice(0,300)', 'lastFrameAt<32', 'LIGHT_GFX||(MEMORY_GB'):
    assert part in w, part
assert 'html.licht' in (ui / 'world.css').read_text()
assert "'lightGraphics'" in (ui / 'control.js').read_text()
assert "'lightGraphics': ('auto', 'on', 'off')" in (shell / 'config.py').read_text()
for f in ('live/config/bootloaders/grub-pc/grub.cfg', 'live/config/bootloaders/syslinux_common/live.cfg.in'):
    assert 'universe.gfx=licht' in (root / f).read_text(), f
    t_ = (root / f).read_text(); assert t_.index('noodoptie lichte modus') > t_.index('veilige grafische modus'), f
print('PASS: lichte-hardware')
assert 'lichte modus met de hand gekozen: geen proef' in (shell / 'grafisch.py').read_text()
# 0.2.32 Installer: geen zichtbare stap 'Beeld', wel een stille shellprocess-stap met dezelfde detectie.
import subprocess, sys as _sys, tempfile, os as _os
cal = root / 'live/config/includes.chroot_after_packages/etc/calamares'
st = (cal / 'settings.conf').read_text()
assert 'packagechooser' not in st and 'contextualprocess' not in st
assert '- shellprocess@beeld' in st and st.index('shellprocess@beeld') < st.index('shellprocess@afronden')
assert not (cal / 'modules/packagechooser-beeld.conf').exists()
sp = (cal / 'modules/shellprocess-beeld.conf').read_text()
assert 'dontChroot: true' in sp and 'universe-beeld-keuze ${ROOT}' in sp
assert 'universe-beeld-keuze' not in (root / 'pakket/universe-os/usr/bin/universe-install').read_text()
spec2 = importlib.util.spec_from_file_location('keuze', root / 'pakket/universe-os/usr/lib/universe-os/universe-beeld-keuze',
                                              loader=importlib.machinery.SourceFileLoader('keuze', str(root / 'pakket/universe-os/usr/lib/universe-os/universe-beeld-keuze')))
k = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(k)
assert k.decide('oude/zwakke videokaart (nouveau)', '') == 'licht' and k.decide(None, 'boot=live') == 'normaal'
assert k.decide(None, 'boot=live universe.gfx=licht') == 'licht'
with tempfile.TemporaryDirectory() as t:
    k.write(t, 'normaal'); k.write(t, 'licht')
    assert sorted(_os.listdir(t + '/etc/universe-os')) == ['grafisch-licht']
try:
    import yaml
    yaml.safe_load(st); yaml.safe_load(sp)
except ImportError:
    pass
# 0.2.32: GT 710 uit de diagnose (10de:128b, GK208B) gaat licht, ook als nouveau nog niet geladen is.
pass  # g = grafisch (boven)
gt710 = [(0x10de, 0x128b)]
for drv in (['nouveau'], ['simpledrm'], [], ['efifb']):
    assert g.choose_light('', drv, gt710), drv
assert 'NVIDIA 0x128b' in g.choose_light('', ['simpledrm'], gt710)
assert g.choose_light('', ['nvidia'], [(0x10de, 0x2484)]) is None          # RTX 3070
assert g.choose_light('', ['amdgpu'], [(0x1002, 0x73bf)]) is None          # RX 6800
assert g.choose_light('', [], [(0x1002, 0x6798)])                          # HD 7970 (radeon)
assert g.choose_light('', ['i915'], [(0x8086, 0x0166)])                    # HD 4000
assert g.choose_light('', ['i915'], [(0x8086, 0x3e92)]) is None            # UHD 630
assert g.choose_light('', ['virtio_gpu'], [(0x1af4, 0x1050)]) is None
assert g.choose_light('', [], [], renderer='NVE7')
assert g.choose_light('', [], [], renderer='Mesa Intel(R) HD Graphics 4000 (IVB GT2) Ivybridge')
assert g.choose_light('', [], [], renderer='AMD Radeon RX 6800 (radeonsi, navi21, LLVM 19)') is None
assert g.choose_light('', [], [], renderer='Mesa Intel(R) UHD Graphics 620 (KBL GT2)') is None
assert g.choose_light('universe.gfx=normal', ['simpledrm'], gt710) is None
# Wacht op de driver: fake sysfs met een videokaart zonder driver -> geeft na de wachttijd terug.
with tempfile.TemporaryDirectory() as t:
    d = _os.path.join(t, 'bus/pci/devices/0000:01:00.0'); _os.makedirs(d)
    open(d + '/class', 'w').write('0x030000\n')
    assert g.wait_for_driver(0.6, t) == []
    _os.makedirs(t + '/bus/pci/drivers/nouveau'); _os.symlink(t + '/bus/pci/drivers/nouveau', d + '/driver')
    assert g.bound_drivers(t) == ['nouveau'] and g.wait_for_driver(5, t) == ['nouveau']
# Systeembreed 'normaal' (installer) schakelt de automaat uit, maar niet na een crash.
assert c(boot, ['nouveau'], normal_file=True) is None
assert c(boot, ['nouveau'], normal_file=True, crashed=True)
print('PASS: lichte-hardware installer')
