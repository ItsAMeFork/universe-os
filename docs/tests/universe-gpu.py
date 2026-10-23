"""universe-gpu (0.2.23): nvidia only for cards nvidia 550 knows, nouveau for the rest, nothing on pc's without NVIDIA."""
import importlib.machinery
import importlib.util
import os
import tempfile
from pathlib import Path

path = Path(__file__).resolve().parents[2] / 'live/config/includes.chroot_after_packages/usr/lib/universe-os/universe-gpu'
loader = importlib.machinery.SourceFileLoader('universe_gpu', str(path))
spec = importlib.util.spec_from_loader('universe_gpu', loader)
gpu = importlib.util.module_from_spec(spec)
loader.exec_module(gpu)

boot = 'BOOT_IMAGE=/live/vmlinuz boot=live quiet splash'
gtx1060 = 'pci:v000010DEd00001C03sv00001462sd00003283bc03sc00i00'
gt210 = 'pci:v000010DEd00000A65sv00001043sd00008334bc03sc00i00'
aliases = ['pci:v000010DEd00001C03sv*sd*bc03sc*i*', 'pci:v000010DEd00002484sv*sd*bc03sc*i*']

# No NVIDIA card (Intel, AMD, VM): nothing is loaded or changed.
assert gpu.choose(boot, [], aliases) == (None, 'geen NVIDIA-kaart')
assert gpu.choose(boot + ' universe.gpu=nvidia', [], aliases)[0] is None
# A card nvidia 550 knows: nvidia. An old card: nouveau.
assert gpu.choose(boot, [gtx1060], aliases)[0] == 'nvidia'
assert gpu.choose(boot, [gt210], aliases)[0] == 'nouveau'
# Two cards, one old: nouveau drives both (the nvidia module would leave the old one dark).
assert gpu.choose(boot, [gtx1060, gt210], aliases)[0] == 'nouveau'
# Module missing (build or kernel without DKMS module): nouveau.
assert gpu.choose(boot, [gtx1060], [])[0] == 'nouveau'
# Boot options win; nomodeset means no driver at all.
assert gpu.choose(boot + ' universe.gpu=nouveau', [gtx1060], aliases)[0] == 'nouveau'
assert gpu.choose(boot + ' universe.gpu=nvidia', [gt210], aliases)[0] == 'nvidia'
assert gpu.choose(boot + ' universe.gpu=veilig', [gtx1060], aliases)[0] == 'veilig'
assert gpu.choose(boot + ' nomodeset', [gtx1060], aliases)[0] == 'veilig'
assert gpu.choose(boot + ' universe.gpu=raar', [gtx1060], aliases)[0] == 'nvidia'

# Reading the PCI bus: only NVIDIA display controllers count (not its HDMI sound, not other vendors).
with tempfile.TemporaryDirectory() as root:
    def dev(name, vendor, klass, alias):
        d = os.path.join(root, name)
        os.makedirs(d)
        for key, value in (('vendor', vendor), ('class', klass), ('modalias', alias)):
            with open(os.path.join(d, key), 'w') as f:
                f.write(value + '\n')
    dev('0000:00:02.0', '0x8086', '0x030000', 'pci:v00008086d00003E92sv*')
    dev('0000:01:00.0', '0x10de', '0x030000', gtx1060)
    dev('0000:01:00.1', '0x10de', '0x040300', 'pci:v000010DEd000010F1sv*')
    assert gpu.nvidia_gpus(root) == [gtx1060]

# The modprobe rules: nouveau and nvidia never load by themselves, and nvidia-drm gets modeset (needed for Wayland).
conf = (path.parents[3] / 'etc/modprobe.d/universe-gpu.conf').read_text(encoding='utf-8')
for name in ('nouveau', 'nvidia', 'nvidia-current', 'nvidia-current-drm'):
    assert f'blacklist {name}\n' in conf
assert 'options nvidia-current-drm modeset=1' in conf
# The boot menu has the NVIDIA and safe entries in GRUB (UEFI) and syslinux (BIOS).
live = path.parents[5]
grub = (live / 'config/bootloaders/grub-pc/grub.cfg').read_text(encoding='utf-8')
syslinux = (live / 'config/bootloaders/syslinux_common/live.cfg.in').read_text(encoding='utf-8')
for text in (grub, syslinux):
    assert 'universe.gpu=nvidia' in text and 'universe.gpu=veilig universe.gfx=safe' in text and 'nomodeset' in text
assert '@LINUX_LIVE@' in grub
print('PASS: universe-gpu')
