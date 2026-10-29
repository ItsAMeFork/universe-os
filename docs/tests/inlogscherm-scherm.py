"""0.3.4 (Axel, 28 Oct): het scherm van het inlog- en vergrendelscherm blijft standaard aan; een beheerder kan een
tijd kiezen (0 = nooit, max 120 min). Test van shell/inlogscherm.py. Draai: python3 docs/tests/inlogscherm-scherm.py"""
import json, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'pakket/universe-os'
sys.path.insert(0, str(ROOT / 'usr/lib/universe-os/shell'))
import inlogscherm as ls  # noqa: E402

fout = []
def eis(ok, tekst):
    print(('OK   ' if ok else 'FOUT ') + tekst)
    if not ok:
        fout.append(tekst)

with tempfile.TemporaryDirectory() as d:
    p = Path(d) / 'inlogscherm.json'
    eis(ls.scherm_uit_minuten(str(p)) == 0, 'geen instelling: scherm nooit uit')
    for inhoud, verwacht in (('{"schermUitMinuten": 30}', 30), ('{"schermUitMinuten": 500}', 120),
                             ('{"schermUitMinuten": -4}', 0), ('{"schermUitMinuten": "x"}', 0), ('kapot', 0), ('[]', 0)):
        p.write_text(inhoud)
        eis(ls.scherm_uit_minuten(str(p)) == verwacht, 'lezen %s -> %d' % (inhoud, verwacht))
    ls.zet(45, str(p))
    eis(json.loads(p.read_text()) == {'schermUitMinuten': 45}, 'zet schrijft de instelling')
    eis(oct(p.stat().st_mode & 0o777) in ('0o644', '0o666') or sys.platform == 'win32', 'leesbaar voor het inlogscherm (0644)')
    for slecht in (-1, 121, 'tien', None, 2.5):
        try:
            ls.zet(slecht, str(p))
            eis(False, 'ongeldige waarde %r geweigerd' % (slecht,))
        except ValueError:
            eis(json.loads(p.read_text()) == {'schermUitMinuten': 45}, 'ongeldige waarde %r geweigerd, oude blijft' % (slecht,))

eis(ls.xset_opdrachten(0) == [['xset', 's', 'off'], ['xset', 's', 'noblank'], ['xset', '-dpms']],
    '0 minuten: schermbeveiliging en DPMS uit (beeld blijft aan)')
eis(ls.xset_opdrachten(30) == [['xset', 's', 'off'], ['xset', 's', 'noblank'], ['xset', '+dpms'], ['xset', 'dpms', '0', '0', '1800']],
    '30 minuten: alleen DPMS uit na 1800 s')

helper = (ROOT / 'usr/lib/universe-os/universe-admin-helper').read_text()
eis("'set-greeter-screen-off'" in helper and 'inlogscherm' in helper, 'beheerdershelper kent set-greeter-screen-off')
eis("'set-greeter-screen-off'" not in helper.split('SELF_ACTIONS')[1].split('\n')[0], 'alleen een beheerder mag het (geen eigen-actie)')
g = (ROOT / 'usr/lib/universe-os/shell/greeter.py').read_text()
eis('inlogscherm.toepassen' in g, 'het inlogscherm past de instelling toe bij het starten')

print('\n'.join(fout) or 'OK inlogscherm-scherm')
sys.exit(bool(fout))
