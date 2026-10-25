"""Animaties van vensters en bestanden (0.2.36): de bloem, het kleine gat en het zwarte gat.

Alles wordt getekend met GTK/cairo op een eigen layer-shell-oppervlak (OVERLAY, geen toetsenbord, lege invoerregio).
Het echte venster is daardoor meteen klikbaar en houdt de focus. Het oppervlak staat alleen tijdens een animatie op
het scherm. Zonder RGBA-visual tekenen we niets, want dan zou het een zwart scherm worden (0.2.35, laptop-VM).

 * bloem    Een venster vouwt open als een bloem, op zijn echte rechthoek en met zijn echte inhoud. Sluiten speelt
            dezelfde bloem andersom. Minimaliseren vouwt dicht richting het dock. De rechthoek en de inhoud komen uit
            venstermeting.py.
 * gat      Een bestand gaat naar de prullenbak: een korte lichtflits, waarna het in een klein zwart gat verdwijnt.
 * zwartgat Bij het legen van de prullenbak verschijnt een groot zwart gat met een accretieschijf. Het slokt de bestanden
            één voor één op, met lichtsporen. Het duurt hooguit ongeveer 3 seconden: bij veel bestanden worden ze
            gegroepeerd.
Snel ('snel': lichte modus, eenvoudige wereld, Animaties verminderd): alleen korte vervaging en schaal, geen effecten.
"""
import math
import random
import time

MINT = (0x85 / 255, 0xff / 255, 0xe3 / 255)
RUIMTE = (0x05 / 255, 0x08 / 255, 0x15 / 255)
DUUR = {'open': 0.35, 'sluit': 0.25, 'min': 0.28, 'gat': 0.55}
SNEL = 0.15
BLADEREN = 8
ZWARTGAT_MAX = 3.0
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
        p = ease_out(t)
        dek = 1.0 if t < 0.8 else 1 - (t - 0.8) / 0.2
    else:  # sluit/min: exactly the opening animation in reverse
        p = ease_out(1 - t)
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
    k = ease_in(clamp((t - 0.25) / 0.65))
    gat = math.sin(math.pi * clamp((t - 0.1) / 0.9)) * 22
    return {'flits': flits, 'kaart': 1 - k, 'hoek': k * 4.0, 'gat': gat}


# ---------- het zwarte gat ----------
def zwartgat_duur(n, snel=False):
    if snel:
        return 0.6
    return min(ZWARTGAT_MAX, 1.1 + 0.11 * min(n, ZWARTGAT_GROEPEN))


def zwartgat_groepen(namen):
    namen = [str(n) for n in namen if str(n)] or ['bestand']
    if len(namen) <= ZWARTGAT_GROEPEN:
        return namen
    rest = len(namen) - (ZWARTGAT_GROEPEN - 1)
    return namen[:ZWARTGAT_GROEPEN - 1] + ['+%d' % rest]


def zwartgat_plan(namen, seed=7):
    """Start angle, distance and departure time (0..1 of the middle part) per (group of) file(s): one by one."""
    groepen = zwartgat_groepen(namen)
    rnd = random.Random(seed)
    n = len(groepen)
    return [{'naam': g, 'hoek': rnd.uniform(0, 2 * math.pi), 'afstand': rnd.uniform(240, 420),
             'vertrek': (i / max(1, n)) * 0.75} for i, g in enumerate(groepen)]


def zwartgat_frame(t):
    """Hole grows (0-0.15), swallows (0.15-0.85), collapses with a last flash (0.85-1)."""
    if t < 0.15:
        groot = ease_out(t / 0.15)
    elif t < 0.85:
        groot = 1.0
    else:
        groot = 1 - ease_in((t - 0.85) / 0.15)
    flits = math.sin(math.pi * clamp((t - 0.85) / 0.15)) if t > 0.85 else 0.0
    return {'groot': groot, 'midden': clamp((t - 0.15) / 0.7), 'flits': flits}


def zwartgat_item(item, midden):
    """Position of one file at 'midden' (0..1): None before it leaves or after it was swallowed. Speeds up while
    spiralling in (ease_in), which makes the light trails."""
    local = (midden - item['vertrek']) / 0.25
    if local < 0:
        return 'wacht'
    if local >= 1:
        return None
    k = ease_in(local)
    r = item['afstand'] * (1 - k)
    a = item['hoek'] + k * 3.2
    return r, a, 1 - k


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
        f = zwartgat_frame(t)
        g = 70 * f['groot']
        if g > 1:
            # lens glow
            glow = cairo.RadialGradient(x, y, g, x, y, g * 3.2)
            glow.add_color_stop_rgba(0, 1, 0.85, 0.6, 0.35 * f['groot'])
            glow.add_color_stop_rgba(0.3, *MINT, 0.18 * f['groot'])
            glow.add_color_stop_rgba(1, *MINT, 0)
            cr.set_source(glow)
            cr.arc(x, y, g * 3.2, 0, 2 * math.pi)
            cr.fill()
            # accretion disk: flattened rings, slowly turning
            cr.save()
            cr.translate(x, y)
            cr.rotate(-0.35 + t * 0.6)
            cr.scale(1.0, 0.32)
            for i, (rr, col, a) in enumerate(((2.6, (1, 0.72, 0.4), 0.35), (2.1, (1, 0.9, 0.7), 0.55), (1.6, MINT, 0.6))):
                cr.set_line_width(g * (0.35 - i * 0.08))
                cr.set_source_rgba(*col, a * f['groot'])
                cr.arc(0, 0, g * rr, 0, 2 * math.pi)
                cr.stroke()
            cr.restore()
            # event horizon
            cr.arc(x, y, g, 0, 2 * math.pi)
            cr.set_source_rgba(0, 0, 0, 1)
            cr.fill_preserve()
            cr.set_source_rgba(1, 0.95, 0.85, 0.8 * f['groot'])
            cr.set_line_width(2)
            cr.stroke()
        # the files, one by one, with light trails from their speed
        for item in anim['plan']:
            pos = zwartgat_item(item, f['midden'])
            if pos is None:
                continue
            if pos == 'wacht':
                r, a, k = item['afstand'], item['hoek'], 1.0
            else:
                r, a, k = pos
            px, py = x + r * math.cos(a), y + r * math.sin(a)
            if pos != 'wacht' and k < 0.98:
                spoor = zwartgat_item(item, max(item['vertrek'], f['midden'] - 0.06))
                if spoor and spoor != 'wacht':
                    sx, sy = x + spoor[0] * math.cos(spoor[1]), y + spoor[0] * math.sin(spoor[1])
                    lin = cairo.LinearGradient(sx, sy, px, py)
                    lin.add_color_stop_rgba(0, *MINT, 0)
                    lin.add_color_stop_rgba(1, 1, 1, 1, 0.9)
                    cr.set_source(lin)
                    cr.set_line_width(3 * k + 1)
                    cr.move_to(sx, sy)
                    cr.line_to(px, py)
                    cr.stroke()
            cr.save()
            cr.translate(px, py)
            cr.scale(max(0.05, k), max(0.05, k))
            cr.rectangle(-16, -20, 32, 40)
            cr.set_source_rgba(0.89, 0.9, 0.98, 0.9 * (1.0 if pos == 'wacht' else k) * min(1.0, f['groot'] * 2))
            cr.fill()
            if k > 0.5:
                cr.set_source_rgba(0.89, 0.9, 0.98, 0.9 * k * min(1.0, f['groot'] * 2))
                cr.select_font_face('Noto Sans')
                cr.set_font_size(11)
                naam = item['naam'] if len(item['naam']) <= 18 else item['naam'][:17] + '…'
                ext = cr.text_extents(naam)
                cr.move_to(-ext.width / 2, 34)
                cr.show_text(naam)
            cr.restore()
        if f['flits'] > 0.02:
            r = 160 * f['flits']
            grad = cairo.RadialGradient(x, y, 0, x, y, r)
            grad.add_color_stop_rgba(0, 1, 1, 1, 0.9 * f['flits'])
            grad.add_color_stop_rgba(1, *MINT, 0)
            cr.set_source(grad)
            cr.arc(x, y, r, 0, 2 * math.pi)
            cr.fill()
