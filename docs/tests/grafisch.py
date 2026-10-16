"""grafisch.py: normal WebKit drawing by default (as 0.2.12), the safe mode only when asked for (16 Oct)."""
import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell/grafisch.py'
spec = importlib.util.spec_from_file_location('grafisch', path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

boot = 'BOOT_IMAGE=/boot/vmlinuz root=UUID=x ro quiet splash'
# Every pc with a graphics driver draws normally, whatever the driver (0.2.17 forced the processor on NVIDIA/unknown).
assert g.choose(boot, False, True) == ('normal', 'standaard')
# Asked for: boot option or the file of this pc.
assert g.choose(boot + ' universe.gfx=safe', False, True)[0] == 'safe'
assert g.choose(boot, True, True) == ('safe', g.SAFE_FILE)
# No usable graphics driver: the processor draws anyway.
assert g.choose(boot, False, False) == ('safe', 'geen render-node')
# universe.gfx=normal wins over the file and a missing render node.
assert g.choose(boot + ' universe.gfx=normal', True, False)[0] == 'normal'
# Only a whole option counts.
assert g.choose(boot + ' universe.gfx=safer', False, True)[0] == 'normal'
print('grafisch: normaal tekenen is standaard, veilige modus alleen op verzoek')
