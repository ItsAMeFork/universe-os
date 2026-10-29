#!/usr/bin/env python3
"""0.2.34: de bovenbalk verdwijnt onder gemaximaliseerde/gesleepte vensters (BOTTOM-laag, TOP als hij open is)."""
import pathlib, re, sys
R = pathlib.Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr'
sh = (R / 'lib/universe-os/shell/universe_shell.py').read_text()
js = (R / 'share/universe-os/ui/panel.js').read_text()
css = (R / 'share/universe-os/ui/panel.html').read_text()
checks = {
    'paneel start op BOTTOM-laag': "'panel.html', L.BOTTOM, [E.TOP]" in sh,
    'open paneel naar TOP': re.search(r"if open_:.*?Layer\.TOP.*?else:.*?Layer\.BOTTOM", sh, re.S) is not None,
    'geen exclusieve zone voor paneel': 'set_exclusive_zone(self.panel' not in sh,
    'bar-covered gemeld': "self.panel.emit('bar-covered'" in sh,
    'pagina luistert': "on('bar-covered'" in js,
    'vervaag-animatie': 'body.bedekt .pill' in css and 'transition:opacity' in css,
}
bad = [k for k, v in checks.items() if not v]
for k, v in checks.items():
    print(('OK  ' if v else 'FOUT') + ' ' + k)
sys.exit(1 if bad else 0)
