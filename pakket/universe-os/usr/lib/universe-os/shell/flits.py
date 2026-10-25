"""Animaties van vensters en bestanden (0.2.37: trager en beter zichtbaar, realistisch zwart gat): de bloem, het kleine gat en het zwarte gat.

Alles wordt getekend met GTK/cairo op een eigen layer-shell-oppervlak (OVERLAY, geen toetsenbord, lege invoerregio).
Het echte venster is daardoor meteen klikbaar en houdt de focus. Het oppervlak staat alleen tijdens een animatie op
het scherm. Zonder RGBA-visual tekenen we niets, want dan zou het een zwart scherm worden (0.2.35, laptop-VM).

 * bloem    Een venster vouwt open als een bloem, op zijn echte rechthoek en met zijn echte inhoud. Sluiten speelt
            dezelfde bloem andersom. Minimaliseren vouwt dicht richting het dock. De rechthoek en de inhoud komen uit
            venstermeting.py.
 * gat      Een bestand gaat naar de prullenbak: een korte lichtflits, waarna het in een klein zwart gat verdwijnt.
 * zwartgat Bij het legen van de prullenbak verschijnt een zwart gat zoals bij een ster die wordt opgeslokt (tidal
            disruption): zwarte kern, gloeiende draaiende accretieschijf (helderder aan de naderende kant), fotonring
            met lensgloed. Elk bestand wordt uitgerekt (spaghettificatie), spiraalt als lichtstroom naar binnen en dooft
            roodverschoven bij de horizon: licht dat niet meer ontsnapt. Per bestand ~1.8 s, achter elkaar; samen
            hooguit ~8 s (bij veel bestanden gegroepeerd en dichter op elkaar). Aan het eind zakt het gat langzaam in.
Jesse (25 okt): 'de animaties gaan te snel en zie er niks van' -> 0.8-1.2 s per venster-/bestandsanimatie, met easing.
Snel ('snel': lichte modus, eenvoudige wereld, Animaties verminderd): alleen korte vervaging en schaal, geen effecten.
"""
import math
import random
import time

MINT = (0x85 / 255, 0xff / 255, 0xe3 / 255)
RUIMTE = (0x05 / 255, 0x08 / 255, 0x15 / 255)
DUUR = {'open': 1.0, 'sluit': 0.9, 'min': 1.0, 'gat': 1.1}
SNEL = 0.15
BLADEREN = 8
ZWARTGAT_MAX = 8.0
ZG_GROEI = 0.8      # s: het gat verschijnt
ZG_SLOK = 1.8       # s: één bestand wordt opgeslokt
ZG_TUSSEN = 0.6     # s: tussen twee bestanden (kleiner bij veel bestanden)
ZG_INZAK = 1.2      # s: het gat zakt in
ZWARTGAT_GROEPEN = 18  # meer bestanden worden gegroepeerd ("+12")
TRAAG_BESTAND = '/tmp/universe-flits-traag'  # alleen voor tests: een factor (bv. 20) maakt de animaties trager


def traag():
    try:
        with open(TRAAG_BESTAND) as f:
            return max(1.0, min(50.0, float(f.read().strip() or 1)))
    except (OSError, ValueError):
        return 1.0


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in(t):
    return t ** 3


def ease_in_out(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def duur(anim):
    soort = anim['soort']
    if soort == 'zwartgat':
        basis = zwartgat_duur(len(anim.get('namen') or []), anim.get('snel'))
    elif anim.get('snel'):
        basis = SNEL
    else:
        basis = DUUR.get(soort, DUUR['open'])
    return basis * anim.get('traag', 1.0)


def voortgang(anim, now):
    """0..1 of the animation, None when it is over."""
    t = (now - anim['start']) / duur(anim)
    if t >= 1:
        return None
    return clamp(t)


# ---------- de bloem ----------
def bloem_frame(anim, t, dock):
    """Shape of the flower at time t (0..1). Returns dict(p, cx, cy, schaal, draai, alpha, dek): p is how far the flower
    is open (0 = a point, 1 = exactly the window rectangle), dek how much the dark cover hides the real window
    (only while opening)."""
    x, y, w, h = anim['rect']
    soort = anim['soort']
    cx, cy = x + w / 2, y + h / 2
    if soort == 'open':
        p = ease_in_out(t)
        dek = 1.0 if t < 0.85 else 1 - (t - 0.85) / 0.15
    else:  # sluit/min: exactly the opening animation in reverse
        p = 1 - ease_in_out(t)
        dek = 0.0
        if soort == 'min' and dock:
            k = ease_in(t)
            cx, cy = cx + (dock[0] - cx) * k, cy + (dock[1] - cy) * k
    alpha = 1.0 if soort == 'open' else clamp(p * 1.6)
    return {'p': p, 'cx': cx, 'cy': cy, 'schaal': 0.55 + 0.45 * p, 'draai': (1 - p) * 0.6, 'alpha': alpha, 'dek': dek}


def bloem_straal(w, h):
    """Radius at which the flower (petal dents included) covers the whole rectangle."""
    return math.hypot(w, h) / 2 / 0.82


def bloem_pad(cr, cx, cy, straal, draai, bladeren=BLADEREN):
    """A flower curve: r(a) = R * (0.82 + 0.18 * |cos(n a / 2)|), drawn as one path."""
    stappen = bladeren * 12
    for i in range(stappen + 1):
        a = 2 * math.pi * i / stappen
        r = straal * (0.82 + 0.18 * abs(math.cos(bladeren * (a + draai) / 2)))
        px, py = cx + r * math.cos(a + draai), cy + r * math.sin(a + draai)
        if i == 0:
            cr.move_to(px, py)
        else:
            cr.line_to(px, py)
    cr.close_path()


# ---------- het kleine gat ----------
def gat_frame(t):
    """Flash first (0-0.3), then the file shrinks and spirals into a small hole (0.25-1)."""
    flits = math.sin(math.pi * clamp(t / 0.3)) if t < 0.3 else 0.0
    k = ease_in_out(clamp((t - 0.25) / 0.65))
    gat = math.sin(math.pi * clamp((t - 0.1) / 0.9)) * 22
    return {'flits': flits, 'kaart': 1 - k, 'hoek': k * 4.0, 'gat': gat}


# ---------- het zwarte gat ----------
def zwartgat_tussen(n):
    """Seconds between two files: ZG_TUSSEN, smaller when needed so that everything fits in ZWARTGAT_MAX."""
    if n <= 1:
        return 0.0
    return min(ZG_TUSSEN, (ZWARTGAT_MAX - ZG_GROEI - ZG_SLOK - ZG_INZAK) / (n - 1))


def zwartgat_duur(n, snel=False):
    if snel:
        return 0.6
    n = max(1, min(n, ZWARTGAT_GROEPEN))
    return ZG_GROEI + (n - 1) * zwartgat_tussen(n) + ZG_SLOK + ZG_INZAK


def zwartgat_groepen(namen):
    namen = [str(n) for n in namen if str(n)] or ['bestand']
    if len(namen) <= ZWARTGAT_GROEPEN:
        return namen
    rest = len(namen) - (ZWARTGAT_GROEPEN - 1)
    return namen[:ZWARTGAT_GROEPEN - 1] + ['+%d' % rest]


def zwartgat_plan(namen, seed=7):
    """Per (group of) file(s): start angle, distance and departure in seconds after the start: one by one."""
    groepen = zwartgat_groepen(namen)
    rnd = random.Random(seed)
    gap = zwartgat_tussen(len(groepen))
    return [{'naam': g, 'hoek': rnd.uniform(0, 2 * math.pi), 'afstand': rnd.uniform(260, 420),
             'vertrek': ZG_GROEI + i * gap} for i, g in enumerate(groepen)]


def zwartgat_frame(t, totaal=None):
    """Hole grows (first ZG_GROEI s), swallows, then slowly sinks in (last ZG_INZAK s). t is 0..1 of totaal seconds."""
    totaal = totaal or zwartgat_duur(1)
    s = t * totaal
    if s < ZG_GROEI:
        groot = ease_out(s / ZG_GROEI)
    elif s > totaal - ZG_INZAK:
        groot = 1 - ease_in_out(clamp((s - (totaal - ZG_INZAK)) / ZG_INZAK))
    else:
        groot = 1.0
    return {'groot': groot, 's': s, 'draai': s * 1.6}


def zwartgat_item(item, s):
    """State of one file at s seconds: 'wacht' before it leaves, None once swallowed, else dict:
    r/a position (spiral, faster inside: ~Kepler), k = how much is still 'file' (1 -> 0), rek = stretch along the
    direction of fall (spaghettification), rood = redshift 0..1 near the horizon, licht = brightness of the stream."""
    local = (s - item['vertrek']) / ZG_SLOK
    if local < 0:
        return 'wacht'
    if local >= 1:
        return None
    q = ease_in(local) * 0.55 + ease_in_out(local) * 0.45
    r = item['afstand'] * (1 - q) + 64 * q  # ends just at the photon ring/horizon
    rel = r / item['afstand']
    a = item['hoek'] + 1.2 * (rel ** -1.5 - 1) * 0.35
    k = clamp(1 - local / 0.55)  # the card is torn into a stream in the first half
    rek = 1 + 6 * clamp(local / 0.7) ** 2
    rood = clamp((local - 0.6) / 0.4)
    licht = clamp(local / 0.25) * (1 - rood ** 2)
    return {'r': r, 'a': a, 'k': k, 'rek': rek, 'rood': rood, 'licht': licht}


def roodverschuiving(rood):
    """White-blue light -> orange -> deep red as it reaches the horizon."""
    if rood < 0.5:
        u = rood / 0.5
        return (0.85 + 0.15 * u, 0.95 - 0.35 * u, 1.0 - 0.75 * u)
    u = (rood - 0.5) / 0.5
    return (1.0 - 0.45 * u, 0.6 - 0.55 * u, 0.25 - 0.2 * u)


class Flits:
    def __init__(self, log):
        import gi
        gi.require_version('Gtk', '3.0')
        gi.require_version('GtkLayerShell', '0.1')
        from gi.repository import Gtk, GtkLayerShell
        self.log = log
        self.anims = []
        self.tick = 0
        self.window = Gtk.Window()
        self.window.set_title('Universe venster-animatie')
        visual = self.window.get_screen().get_rgba_visual()
        self.transparent = visual is not None
        if visual:
            self.window.set_visual(visual)
        self.window.set_app_paintable(True)
        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_namespace(self.window, 'universe-flits')
        GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.OVERLAY)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self.window, edge, True)
        GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_exclusive_zone(self.window, -1)
        self.window.connect('draw', self.draw)
        self.window.connect('realize', self.no_input)
        self.window.connect('map', self.no_input)

    def no_input(self, *args):
        import cairo
        gdk_window = self.window.get_window()
        if gdk_window:
            gdk_window.input_shape_combine_region(cairo.Region(), 0, 0)
        return False

    def size(self):
        return self.window.get_allocated_width(), self.window.get_allocated_height()

    def play(self, events):
        if not self.transparent:
            return False  # without an RGBA visual the overlay would be a black screen: no animation
        from gi.repository import GLib
        now, factor = time.monotonic(), traag()
        for e in events:
            a = dict(e, start=now, traag=factor)
            if a['soort'] == 'zwartgat':
                a['plan'] = zwartgat_plan(a.get('namen') or [])
            # a window that closes during its own opening: replace that animation, never two flowers at once
            if a.get('wid'):
                self.anims = [x for x in self.anims if x.get('wid') != a['wid']]
            self.anims.append(a)
        self.anims = self.anims[-12:]
        if not self.window.get_visible():
            self.window.show_all()
            self.no_input()
        if not self.tick:
            self.tick = GLib.timeout_add(16, self.step)
        return True

    def step(self):
        self.window.queue_draw()
        if not self.anims:
            self.tick = 0
            self.window.hide()
            return False
        return True

    def draw(self, widget, cr):
        import cairo
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        w, h = widget.get_allocated_width(), widget.get_allocated_height()
        now, alive = time.monotonic(), []
        for anim in self.anims:
            t = voortgang(anim, now)
            if t is None:
                continue
            alive.append(anim)
            try:
                cr.save()
                getattr(self, 'teken_' + ('bloem' if anim['soort'] in ('open', 'sluit', 'min') else anim['soort']))(cr, anim, t, w, h)
            except Exception as error:  # noqa: BLE001 - a broken frame is skipped, never a black screen
                alive.remove(anim)
                self.log('animatie overgeslagen: %s' % error)
            finally:
                cr.restore()
        self.anims = alive
        return True

    # ----- bloem -----
    def teken_bloem(self, cr, anim, t, w, h):
        import cairo
        x, y, bw, bh = anim['rect']
        if anim.get('snel'):  # cheap: soft outline on the real rectangle, small scale, fade
            open_ = anim['soort'] == 'open'
            a = (1 - t) if open_ else (1 - t) * 0.8
            s = 0.97 + 0.03 * (t if open_ else 1 - t)
            cx, cy = x + bw / 2, y + bh / 2
            cr.rectangle(cx - bw * s / 2, cy - bh * s / 2, bw * s, bh * s)
            cr.set_source_rgba(*MINT, 0.5 * a)
            cr.set_line_width(2)
            cr.stroke()
            return
        f = bloem_frame(anim, t, anim.get('dock'))
        p, cx, cy = f['p'], f['cx'], f['cy']
        straal = bloem_straal(bw, bh) * max(0.02, p)
        # 1. while opening: the real window is still hidden behind a dark cover, only on its own rectangle
        if f['dek'] > 0.01:
            cr.rectangle(x, y, bw, bh)
            cr.set_source_rgba(*RUIMTE, 0.96 * f['dek'])
            cr.fill()
        # 2. the flower: clipped to the window rectangle (moved and scaled when minimising), real content inside
        s = f['schaal']
        rx, ry, rw, rh = cx - bw * s / 2, cy - bh * s / 2, bw * s, bh * s
        cr.save()
        cr.rectangle(rx, ry, rw, rh)
        cr.clip()
        bloem_pad(cr, cx, cy, straal, f['draai'])
        cr.clip()
        pix = anim.get('pix')
        if pix is not None:
            from gi.repository import Gdk
            cr.save()
            cr.translate(rx, ry)
            cr.scale(rw / pix.get_width(), rh / pix.get_height())
            Gdk.cairo_set_source_pixbuf(cr, pix, 0, 0)
            cr.paint_with_alpha(f['alpha'])
            cr.restore()
        else:
            grad = cairo.RadialGradient(cx, cy, 0, cx, cy, max(1.0, straal))
            grad.add_color_stop_rgba(0, 0.91, 1, 0.98, 0.5 * f['alpha'])
            grad.add_color_stop_rgba(1, *MINT, 0.12 * f['alpha'])
            cr.set_source(grad)
            cr.paint()
        # light on the petals, fading as the flower is fully open
        licht = (1 - p) * f['alpha']
        if licht > 0.02:
            grad = cairo.RadialGradient(cx, cy, 0, cx, cy, max(1.0, straal))
            grad.add_color_stop_rgba(0, 0.91, 1, 0.98, 0.55 * licht)
            grad.add_color_stop_rgba(0.6, *MINT, 0.18 * licht)
            grad.add_color_stop_rgba(1, *MINT, 0.0)
            cr.set_source(grad)
            cr.paint()
        cr.restore()
        # 3. petal edges: a mint glow along the flower curve (no filters, a few wider strokes)
        rand = (1 - p) * f['alpha']
        if rand > 0.02 and straal > 3:
            cr.save()
            cr.rectangle(rx - 16, ry - 16, rw + 32, rh + 32)
            cr.clip()
            bloem_pad(cr, cx, cy, straal, f['draai'])
            for width, a in ((10, 0.10), (5, 0.22), (2, 0.8)):
                cr.set_line_width(width)
                cr.set_source_rgba(*MINT, a * rand)
                cr.stroke_preserve()
            cr.new_path()
            cr.restore()

    # ----- klein gat -----
    def teken_gat(self, cr, anim, t, w, h):
        import cairo
        x, y = anim['x'], anim['y']
        if anim.get('snel'):
            cr.arc(x, y, 18 + 10 * t, 0, 2 * math.pi)
            cr.set_source_rgba(*MINT, 0.5 * (1 - t))
            cr.fill()
            return
        f = gat_frame(t)
        if f['gat'] > 0.5:  # the small black hole with a thin bright rim
            g = f['gat']
            rim = cairo.RadialGradient(x, y, g * 0.6, x, y, g * 1.9)
            rim.add_color_stop_rgba(0, 0, 0, 0, 1)
            rim.add_color_stop_rgba(0.45, 0, 0, 0, 1)
            rim.add_color_stop_rgba(0.55, *MINT, 0.7)
            rim.add_color_stop_rgba(1, *MINT, 0)
            cr.set_source(rim)
            cr.arc(x, y, g * 1.9, 0, 2 * math.pi)
            cr.fill()
        if f['kaart'] > 0.02:  # the file: a small card that spirals inwards
            k = f['kaart']
            cr.save()
            cr.translate(x, y)
            cr.rotate(f['hoek'])
            cr.scale(k, k)
            cr.rectangle(-20, -24, 40, 48)
            cr.set_source_rgba(0.89, 0.9, 0.98, 0.85 * k)
            cr.fill_preserve()
            cr.set_source_rgba(*MINT, 0.9 * k)
            cr.set_line_width(2)
            cr.stroke()
            cr.restore()
        if f['flits'] > 0.02:
            r = 70 * f['flits']
            grad = cairo.RadialGradient(x, y, 0, x, y, r)
            grad.add_color_stop_rgba(0, 1, 1, 1, 0.95 * f['flits'])
            grad.add_color_stop_rgba(0.4, *MINT, 0.5 * f['flits'])
            grad.add_color_stop_rgba(1, *MINT, 0)
            cr.set_source(grad)
            cr.arc(x, y, r, 0, 2 * math.pi)
            cr.fill()

    # ----- groot zwart gat -----
    def teken_zwartgat(self, cr, anim, t, w, h):
        import cairo
        x, y = anim.get('x', w / 2), anim.get('y', h / 2)
        if anim.get('snel'):
            a = math.sin(math.pi * t)
            cr.arc(x, y, 60, 0, 2 * math.pi)
            cr.set_source_rgba(0, 0, 0, 0.8 * a)
            cr.fill_preserve()
            cr.set_source_rgba(*MINT, 0.6 * a)
            cr.set_line_width(2)
            cr.stroke()
            return
        totaal = duur(anim) / anim.get('traag', 1.0)
        f = zwartgat_frame(t, totaal)
        s, G = f['s'], f['groot']
        g = 60 * G
        # feeding: the disk flares up while a file reaches the horizon
        voeding = 0.0
        staten = []
        for item in anim['plan']:
            st = zwartgat_item(item, s)
            staten.append((item, st))
            if isinstance(st, dict):
                voeding = max(voeding, st['rood'])
        if g > 1:
            self.zwartgat_schijf(cr, x, y, g, G, f['draai'], voeding, achter=True)
        # the files and their light streams (before the horizon, so the horizon covers what falls in)
        for item, st in staten:
            if st is None:
                continue
            self.zwartgat_bestand(cr, anim, item, st, s, x, y, G)
        if g > 1:
            # event horizon: pure black, nothing comes out
            cr.arc(x, y, g, 0, 2 * math.pi)
            cr.set_source_rgba(0, 0, 0, 1)
            cr.fill()
            # photon ring: thin, very bright, with a lensing glow around it
            for width, a in ((g * 0.5, 0.08), (g * 0.22, 0.18), (g * 0.08, 0.5), (1.6, 0.95)):
                cr.set_line_width(width)
                cr.set_source_rgba(1, 0.9, 0.72, a * G * (1 + 0.5 * voeding))
                cr.arc(x, y, g * 1.06, 0, 2 * math.pi)
                cr.stroke()
            self.zwartgat_schijf(cr, x, y, g, G, f['draai'], voeding, achter=False)

    def zwartgat_schijf(self, cr, x, y, g, G, draai, voeding, achter):
        """Accretion disk, tilted. achter=True: the far half plus the lensed image of the disk arching over the hole
        (gravitational lensing); achter=False: the near half in front of the hole. Doppler beaming: the side that moves
        towards us (left) is brighter and whiter, the other side dimmer and redder."""
        import cairo
        if achter:
            glow = cairo.RadialGradient(x, y, g, x, y, g * 4.5)
            glow.add_color_stop_rgba(0, 1, 0.75, 0.45, 0.28 * G * (1 + voeding))
            glow.add_color_stop_rgba(0.35, 0.9, 0.45, 0.25, 0.1 * G)
            glow.add_color_stop_rgba(1, 0.5, 0.2, 0.3, 0)
            cr.set_source(glow)
            cr.arc(x, y, g * 4.5, 0, 2 * math.pi)
            cr.fill()
            # lensed disk: the back of the disk seen bent over and under the horizon
            for rr, a in ((1.35, 0.55), (1.6, 0.3), (1.9, 0.14)):
                cr.save()
                cr.translate(x, y)
                cr.scale(1.0, 0.92)
                cr.set_line_width(g * 0.22)
                cr.set_source_rgba(1, 0.82, 0.55, a * G * (1 + 0.4 * voeding))
                cr.arc(0, 0, g * rr, math.pi * 1.05, math.pi * 1.95)
                cr.stroke()
                cr.set_source_rgba(1, 0.7, 0.45, a * 0.45 * G)
                cr.arc(0, 0, g * rr * 0.92, math.pi * 0.1, math.pi * 0.9)
                cr.stroke()
                cr.restore()
        cr.save()
        cr.translate(x, y)
        cr.rotate(-0.18)
        cr.scale(1.0, 0.24)
        segmenten = 48
        a0, a1 = (math.pi, 2 * math.pi) if achter else (0, math.pi)
        for ring, (rr, breed, helder) in enumerate(((1.5, 0.35, 1.0), (2.0, 0.45, 0.8), (2.7, 0.6, 0.5), (3.5, 0.7, 0.25))):
            snelheid = 1.0 / rr ** 1.5  # inner rings turn faster
            for i in range(segmenten // 2):
                b0 = a0 + (a1 - a0) * i / (segmenten // 2)
                b1 = a0 + (a1 - a0) * (i + 1.05) / (segmenten // 2)
                mid = (b0 + b1) / 2
                doppler = 0.55 + 0.45 * -math.cos(mid)  # left side (cos<0) approaches: brighter
                streep = 0.75 + 0.25 * math.sin(mid * 6 - draai * snelheid * 4 + ring)  # turning clumps of gas
                a = helder * doppler * streep * G * (0.7 + 0.5 * voeding)
                col = (1.0, 0.55 + 0.4 * doppler, 0.25 + 0.55 * doppler * (1 - ring * 0.2))
                cr.set_line_width(g * breed)
                cr.set_source_rgba(*col, clamp(a))
                cr.arc(0, 0, g * rr, b0, b1)
                cr.stroke()
        cr.restore()

    def zwartgat_bestand(self, cr, anim, item, st, s, x, y, G):
        import cairo
        if st == 'wacht':
            r, a = item['afstand'], item['hoek'] + 0.04 * math.sin(s * 2 + item['hoek'])
            k, rek, rood, licht = 1.0, 1.0, 0.0, 0.0
        else:
            r, a, k, rek, rood, licht = st['r'], st['a'], st['k'], st['rek'], st['rood'], st['licht']
        px, py = x + r * math.cos(a), y + r * math.sin(a)
        zicht = min(1.0, G * 2)
        # light stream: the path of the last ~0.35 s, colour shifting to red near the horizon
        if st != 'wacht' and licht > 0.01:
            punten = []
            for j in range(14):
                sp = zwartgat_item(item, max(item['vertrek'], s - j * 0.025))
                if isinstance(sp, dict):
                    punten.append((x + sp['r'] * math.cos(sp['a']), y + sp['r'] * math.sin(sp['a']), sp['rood']))
            for j in range(len(punten) - 1):
                (x0, y0, r0), (x1, y1, _) = punten[j], punten[j + 1]
                col = roodverschuiving(r0)
                fade = (1 - j / len(punten)) * licht * zicht
                for width, al in ((9, 0.12), (4, 0.35), (1.6, 0.95)):
                    cr.set_line_width(width * (1 - 0.5 * rood))
                    cr.set_source_rgba(*col, al * fade)
                    cr.move_to(x0, y0)
                    cr.line_to(x1, y1)
                    cr.stroke()
            col = roodverschuiving(rood)
            kop = cairo.RadialGradient(px, py, 0, px, py, 14)
            kop.add_color_stop_rgba(0, *col, 0.9 * licht * zicht)
            kop.add_color_stop_rgba(1, *col, 0)
            cr.set_source(kop)
            cr.arc(px, py, 14, 0, 2 * math.pi)
            cr.fill()
        # the file itself: stretched along the direction of fall and squeezed sideways (spaghettification)
        if k > 0.02:
            cr.save()
            cr.translate(px, py)
            cr.rotate(math.atan2(py - y, px - x))
            cr.scale(rek, 1.0 / (1 + 0.5 * (rek - 1)))
            cr.rectangle(-20, -16, 40, 32)
            cr.set_source_rgba(0.89, 0.9, 0.98, 0.9 * k * zicht)
            cr.fill_preserve()
            cr.set_source_rgba(*MINT, 0.8 * k * zicht)
            cr.set_line_width(1.5)
            cr.stroke()
            cr.restore()
            if k > 0.6:
                cr.set_source_rgba(0.89, 0.9, 0.98, 0.9 * (k - 0.6) / 0.4 * zicht)
                cr.select_font_face('Noto Sans')
                cr.set_font_size(11)
                naam = item['naam'] if len(item['naam']) <= 18 else item['naam'][:17] + '…'
                ext = cr.text_extents(naam)
                cr.move_to(px - ext.width / 2, py + 34)
                cr.show_text(naam)
