"""grafisch.py: normal WebKit drawing by default (as 0.2.12), the safe mode when asked for or when the one-time test of
this pc saw that normal drawing stays dark (16 Oct, H310M pc). Also checks the test's colour verdict and screen reading."""
import importlib.util
import json
import os
import tempfile
from pathlib import Path

shell = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell'


def load(name):
    spec = importlib.util.spec_from_file_location(name, shell / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


g = load('grafisch')

boot = 'BOOT_IMAGE=/boot/vmlinuz root=UUID=x ro quiet splash'
# Every pc with a graphics driver draws normally, whatever the driver (0.2.17 forced the processor on NVIDIA/unknown).
assert g.choose(boot, False, True) == ('normal', 'standaard')
assert g.needs_probe(g.choose(boot, False, True)[1])
# Asked for: boot option or the file of this pc.
assert g.choose(boot + ' universe.gfx=safe', False, True)[0] == 'safe'
assert g.choose(boot, True, True) == ('safe', g.SAFE_FILE)
# No usable graphics driver: the processor draws anyway.
assert g.choose(boot, False, False) == ('safe', 'geen render-node')
# universe.gfx=normal wins over the file, a missing render node and the test result.
assert g.choose(boot + ' universe.gfx=normal', True, False)[0] == 'normal'
assert g.choose(boot + ' universe.gfx=normal', False, True, 'safe')[0] == 'normal'
# Only a whole option counts.
assert g.choose(boot + ' universe.gfx=safer', False, True)[0] == 'normal'
# The test of this pc: dark stays dark (safe mode), seen stays normal; boot options and the file are never tested over.
assert g.choose(boot, False, True, 'safe') == ('safe', 'proef: normaal tekenen bleef donker')
assert g.choose(boot, False, True, 'normal') == ('normal', 'proef: normaal tekenen werkt')
assert not g.needs_probe(g.choose(boot + ' universe.gfx=safe', False, True)[1])
assert not g.needs_probe(g.choose(boot, True, True)[1])
assert not g.needs_probe(g.choose(boot, False, False)[1])

# The kept result only counts for the same drivers and kernel.
with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, 'universe-os', 'grafisch.json')
    assert g.remembered(path, ['nouveau']) is None
    g.remember(path, ['nouveau'], 'safe')
    assert g.remembered(path, ['nouveau']) == 'safe'
    assert g.remembered(path, ['i915']) is None
    with open(path) as f:
        data = json.load(f)
    data['kernel'] = 'een-andere-kernel'
    with open(path, 'w') as f:
        json.dump(data, f)
    assert g.remembered(path, ['nouveau']) is None
    with open(path, 'w') as f:
        f.write('kapot')
    assert g.remembered(path, ['nouveau']) is None

# Without a screen nothing is tested (and nothing is kept).
saved = {k: os.environ.pop(k) for k in ('WAYLAND_DISPLAY', 'DISPLAY') if k in os.environ}
assert g.run_probe() is None
os.environ.update(saved)

try:
    p = load('grafisch_proef')
except (ImportError, ValueError):
    p = None  # no GTK/WebKit here: the verdict is tested where the pakket runs (build VM)
if p:
    left, right, dark = p.LEFT, p.RIGHT, (5, 8, 21)
    assert p.verdict([left] * 50 + [right] * 50)
    assert p.verdict([dark] * 90 + [left] * 5 + [right] * 5)
    assert not p.verdict([dark] * 100)                 # the dark H310M screen
    assert not p.verdict([left] * 100)                 # page drawn, composited canvas missing
    assert not p.verdict([])
    assert p.verdict([tuple(c + 10 for c in left)] * 10 + [tuple(c - 10 for c in right)] * 10)
    ppm = b'P6\n# grim\n2 1\n255\n' + bytes(left) + bytes(right)
    assert p.ppm_pixels(ppm) == [left, right]
print('grafisch: normaal tekenen is standaard; een donker scherm bij de proef geeft de veilige modus')
