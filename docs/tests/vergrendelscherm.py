"""0.2.38 vergrendelscherm (Jesse t132u/t133u): dezelfde nieuwe ruimte en mooiere animaties bij vergrendelen en
ontgrendelen, vol en licht (zelfde verloop, minder kwaliteit)."""
import re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'pakket/universe-os'
fails = []
def check(name, ok):
    print(('OK   ' if ok else 'FOUT ') + name)
    if not ok:
        fails.append(name)
world = (P / 'usr/share/universe-os/ui/world.js').read_text()
lock = (P / 'usr/bin/universe-lock').read_text()
css = (P / 'usr/share/universe-os/gtklock/style.css').read_text()
out_ms = int(re.search(r"animate\(dir==='in'\?(\d+):(\d+)", world).group(2))
sleep = float(re.search(r'sleep ([\d.]+)', lock).group(1))
check('vergrendelen wacht precies de uitloop-animatie af (%d ms / sleep %.1f s)' % (out_ms, sleep), abs(out_ms / 1000 - sleep) < 0.05)
check('vergrendelen/ontgrendelen: sterren worden lichtstrepen (warp)', "warp=Math.sin(Math.PI*e)*.8" in world and "on('lock-begin'" in world and "on('unlock'" in world)
check('lichte modus: zelfde warp (geen apart pad), minder sterren', 'licht:SKY_LIGHT(),warp' in world)
check('gtklock: kaart en klok komen in beeld (keyframes, geen blur)', '@keyframes universe-kaart-in' in css and 'animation: universe-kaart-in' in css and 'blur' not in css)
check('gtklock-achtergrond is de nieuwe ruimte (sterren.png uit sterrenhemel.js, 1920x1080)', (ROOT / 'scripts/assets/sterren.png').stat().st_size > 300000)
sys.exit(1 if fails else 0)
