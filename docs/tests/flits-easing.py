#!/usr/bin/env python3
"""g5: easing per eigenschap van het portaal, meelschalende gloed en meerdere gelijktijdige animaties in één overlay."""
import sys, time
from pathlib import Path
SH = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os/shell'
sys.path.insert(0, str(SH))
import flits
fails = []
def check(name, ok):
    print(('OK   ' if ok else 'FOUT ') + name)
    ok or fails.append(name)
def A(soort, **k):
    return dict({'soort': soort, 'rect': (500, 300, 800, 500), 'bron': (300, 900), 'scherm': (1920, 1080), 'start': 100.0}, **k)
o = lambda t: flits.portaal_frame(A('open'), t)
check('positie ease-out: na 30% al meer dan de helft onderweg, grootte (ease-in-out) nog niet', o(0.3)['pos'] > 0.6 and o(0.3)['p'] < 0.25)
check('positie en grootte lopen van 0 naar 1', o(0)['pos'] == 0 and o(0)['p'] == 0 and abs(o(1)['pos'] - 1) < 1e-9 and abs(o(1)['p'] - 1) < 1e-9)
check('positie en grootte monotoon', all(o(i / 20)['pos'] <= o((i + 1) / 20)['pos'] and o(i / 20)['p'] <= o((i + 1) / 20)['p'] for i in range(20)))
check('alfa apart: al bijna vol terwijl de kaart nog klein is', o(0.4)['alpha'] > 0.95 and o(0.4)['p'] < 0.4 and o(0)['alpha'] < 0.4)
c = lambda t: flits.portaal_frame(A('sluit'), t)
check('sluiten: grootte spiegelt openen, eindigt in de bron', all(abs(c(t)['p'] - o(1 - t)['p']) < 1e-9 for t in (.1, .5, .9)) and abs(c(1)['cx'] - 300) < 1e-6)
check('sluiten: positie zacht aankomend in de bron (ease-out)', c(0.7)['pos'] < 0.05 and c(0.1)['pos'] > 0.5 and c(0)['pos'] == 1)
check('gloed en mintrand schalen mee met de kaart', o(0)['schaal'] < 0.5 and abs(o(1)['schaal'] - 1) < 1e-9 and o(0.5)['schaal'] > o(0.2)['schaal'])
check('easing-functies: grenzen', all(f(0) == 0 and abs(f(1) - 1) < 1e-9 for f in (flits.ease_out, flits.ease_in_out)))
# tijdgebaseerd: voortgang hangt alleen van de klok af
a = A('open')
check('voortgang is tijdgebaseerd (halverwege na halve duur, klaar na de duur)', abs(flits.voortgang(a, 100.5) - 0.5) < 1e-9 and flits.voortgang(a, 101.01) is None)
check('traag-factor rekt de klok', abs(flits.voortgang(dict(a, traag=2.0), 101.0) - 0.5) < 1e-9)

class Venster:
    def __init__(self): self.getekend = 0
    def queue_draw(self): self.getekend += 1
    def hide(self): self.verborgen = True
f = flits.Flits.__new__(flits.Flits)
f.anims = [A('sluit', wid=str(i), start=100.0) for i in range(5)] + [A('sluit', wid='lang', start=100.0, snel=False, traag=3.0)]
f.bevroren = None; f.window = Venster(); f.tick = 7; f.log = print
check('vijf vensters sluiten tegelijk in één overlay: allemaal actief', len(f.klaar(100.3)) == 6)
check('elk met eigen voortgang en eigen frame', len({round(flits.portaal_frame(x, flits.voortgang(x, 100.4))['cx'], 3) for x in f.anims}) >= 1)
check('na de duur blijft alleen de langzame over', [x['wid'] for x in f.klaar(101.0)] == ['lang'])
onthuld = []
f.anims = [A('open', wid='n', verborgen=True, onthul=lambda: onthuld.append(1))]
f.klaar(105.0)
check('klaar() zonder getekend frame: lege lijst', f.anims == [])
f.tick = 7
check('zuinig: stap zonder animaties stopt de tick en verbergt de overlay', f.step() is False and f.tick == 0 and getattr(f.window, 'verborgen', False))
check('constanten 0.2.39 behouden', flits.ONTHUL_BIJ == 0.75 and flits.ONTHUL_FADE == 0.9 and flits.MAX_ANIMS >= 12)
print('\nFOUT: %s' % fails if fails else '\nalles OK')
sys.exit(1 if fails else 0)
