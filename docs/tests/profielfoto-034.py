"""0.3.4: eigen profielfoto (shell/profielfoto.py). Uitsnede altijd; omzetten alleen waar GdkPixbuf er is (VM).
Draai: python3 docs/tests/profielfoto-034.py"""
import base64, os, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell'))
import profielfoto as pf  # noqa: E402

fout = []
def eis(ok, tekst):
    print(('OK   ' if ok else 'FOUT ') + tekst)
    if not ok:
        fout.append(tekst)

# Uitsnede: vierkant, binnen de foto, niet kleiner dan 16 px en niet groter dan de korte zijde.
eis(pf.vierkant(100, 50, 300, 1000, 800) == (100, 50, 300), 'uitsnede blijft zoals gevraagd als hij past')
eis(pf.vierkant(-40, -10, 300, 1000, 800) == (0, 0, 300), 'uitsnede links/boven buiten de foto wordt teruggeschoven')
eis(pf.vierkant(900, 700, 300, 1000, 800) == (700, 500, 300), 'uitsnede rechts/onder buiten de foto wordt teruggeschoven')
eis(pf.vierkant(0, 0, 5000, 1000, 800) == (0, 0, 800), 'te grote uitsnede wordt de korte zijde')
eis(pf.vierkant(10.6, 20.4, 2, 1000, 800) == (11, 20, 16), 'minstens 16 px, afgerond op hele pixels')
eis(pf.vierkant(0, 0, 100, 10, 10) == (0, 0, 10), 'foto kleiner dan 16 px: de hele foto')

# Data-URL: alleen bekende beeldtypen en niet te groot.
with tempfile.TemporaryDirectory() as d:
    png = Path(d) / 'a'; png.write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 20)
    jpg = Path(d) / 'b'; jpg.write_bytes(b'\xff\xd8\xff' + b'0' * 20)
    txt = Path(d) / 'c'; txt.write_bytes(b'<script>alert(1)</script>')
    groot = Path(d) / 'd'; groot.write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * (pf.MAX_BYTES + 1))
    eis((pf.data_url_bestand(str(png)) or '').startswith('data:image/png;base64,'), 'PNG wordt een data-URL')
    eis((pf.data_url_bestand(str(jpg)) or '').startswith('data:image/jpeg;base64,'), 'JPEG wordt een data-URL')
    eis(pf.data_url_bestand(str(txt)) is None, 'geen beeld: geen data-URL')
    eis(pf.data_url_bestand(str(groot)) is None, 'te groot bestand: geen data-URL')
    eis(pf.data_url_bestand(str(Path(d) / 'bestaat-niet')) is None and pf.data_url_bestand('') is None,
        'ontbrekend bestand: geen data-URL, geen fout')

try:
    import gi
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import GdkPixbuf
except (ImportError, ValueError):
    GdkPixbuf = None

if GdkPixbuf is None:
    print('OVERGESLAGEN omzetten: GdkPixbuf ontbreekt (draai in de VM)')
else:
    with tempfile.TemporaryDirectory() as d:
        def maak_foto(naam, w, h, soort):
            pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, w, h)
            pb.fill(0x3366ccff)
            # a red square in the top left corner, to see that the crop really takes the asked part
            pb.new_subpixbuf(0, 0, w // 4, h // 4).fill(0xff0000ff)
            p = str(Path(d) / naam)
            pb.savev(p, soort, [], [])
            return p
        jpg = maak_foto('foto.jpg', 3000, 2000, 'jpeg')
        png = maak_foto('foto.png', 640, 960, 'png')
        v = pf.voorbeeld(jpg)
        eis(v['breedte'] == 3000 and v['hoogte'] == 2000, 'voorbeeld geeft de echte maat van het origineel')
        kop = base64.b64decode(v['beeld'].split(',', 1)[1])[:4]
        eis(v['beeld'].startswith('data:image/') and kop[:2] in (b'\xff\xd8', b'\x89P'), 'voorbeeld is een beeld-data-URL')
        loader = GdkPixbuf.PixbufLoader(); loader.write(base64.b64decode(v['beeld'].split(',', 1)[1])); loader.close()
        vb = loader.get_pixbuf()
        eis(max(vb.get_width(), vb.get_height()) <= pf.VOORBEELD, 'voorbeeld van een grote foto is hooguit %d px' % pf.VOORBEELD)
        data = pf.maak(jpg, 0, 0, 500)
        eis(data[:8] == b'\x89PNG\r\n\x1a\n', 'resultaat is een PNG')
        loader = GdkPixbuf.PixbufLoader(); loader.write(data); loader.close(); r = loader.get_pixbuf()
        eis((r.get_width(), r.get_height()) == (pf.MAAT, pf.MAAT), 'resultaat is %dx%d' % (pf.MAAT, pf.MAAT))
        px = r.get_pixels()
        eis(px[0] > 200 and px[1] < 60, 'uitsnede linksboven bevat het rode vlak')
        loader = GdkPixbuf.PixbufLoader(); loader.write(pf.maak(png, 0, 300, 640)); loader.close()
        eis(loader.get_pixbuf().get_width() == pf.MAAT, 'staande PNG wordt ook vierkant')
        kapot = Path(d) / 'kapot.jpg'; kapot.write_bytes(b'\xff\xd8\xff dit is geen jpeg')
        for p in (str(kapot), str(Path(d) / 'bestaat-niet.png')):
            try:
                pf.voorbeeld(p)
                eis(False, 'onleesbaar bestand geeft een nette fout (%s)' % os.path.basename(p))
            except ValueError as e:
                eis(str(e) == pf.FOUT, 'onleesbaar bestand geeft een nette fout (%s)' % os.path.basename(p))
        print('Formaten die GdkPixbuf hier kan lezen:', ' '.join(sorted(f.get_name() for f in GdkPixbuf.Pixbuf.get_formats())))

print('\n'.join(fout) or 'OK profielfoto')
sys.exit(bool(fout))
