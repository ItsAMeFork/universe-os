"""Animaties van vensters en bestanden (0.2.38): het portaal, het kleine gat en het zwarte gat.

Alles wordt getekend met GTK/cairo op een eigen layer-shell-oppervlak (OVERLAY, geen toetsenbord, lege invoerregio).
Het echte venster is daardoor meteen klikbaar en houdt de focus. Het oppervlak staat alleen tijdens een animatie op
het scherm. Zonder RGBA-visual tekenen we niets, want dan zou het een zwart scherm worden (0.2.35, laptop-VM).

 * portaal  (0.2.38, Jesse: 'geen bloem maar de planeet die word aangeklikt of snelkoppelingen in het menu')
            Een venster komt tevoorschijn uit de planeet of de menu-snelkoppeling waarop geklikt is ('bron'): een
            lichtpunt flitst op, het venster groeit langs een licht gebogen baan met een lichtspoor naar zijn echte
            rechthoek en echte inhoud. Sluiten speelt hetzelfde andersom, terug naar de bron (of het midden).
            Minimaliseren gaat naar het dock. Geldt voor elk venster, ook Wine/.exe.
 * gat      Een bestand gaat naar de prullenbak: een lichtflits, waarna het in een klein zwart gat verdwijnt.
 * zwartgat Bij het legen van de prullenbak: een zwart gat zoals bij een ster die wordt opgeslokt (zie zwartgat_item).
Kwaliteit (0.2.38, Jesse: 'de lichte modus moet het zelfde zijn maar dan lichter dus minder kwaliteit'): één tekenpad
voor alles; 'kwaliteit': 'licht' (oude/zwakke videokaart, eenvoudige wereld) tekent dezelfde animatie met dezelfde
beweging en duur, alleen met minder lagen gloed, minder spoorpunten/schijfsegmenten, zonder vensterinhoud en op
~30 beelden per seconde. 'snel' is alleen nog 'Animaties verminderd' (toegankelijkheid): korte vervaging.
"""
import math
import random
import time

MINT = (0x85 / 255, 0xff / 255, 0xe3 / 255)
RUIMTE = (0x05 / 255, 0x08 / 255, 0x15 / 255)
DUUR = {'open': 1.0, 'sluit': 0.9, 'min': 1.0, 'gat': 1.1}
KWALITEIT = {
    'vol': {'gloed': ((10, 0.10), (5, 0.22), (2, 0.85)), 'spoor': 14, 'segmenten': 48, 'ringen': 4, 'lens': 3, 'tick': 16,
            'inhoud': True},
    'licht': {'gloed': ((2, 0.85),), 'spoor': 6, 'segmenten': 16, 'ringen': 3, 'lens': 1, 'tick': 33, 'inhoud': False},
}


def kwaliteit(anim):
    return KWALITEIT['licht' if anim.get('kwaliteit') == 'licht' else 'vol']
SNEL = 0.15
ONTHUL_BIJ = 0.75  # 0.2.39: portal progress at which the hidden window is restored under the (still opaque) card
MAX_ANIMS = 24  # several windows can close at once, each with its own card in the one overlay
ONTHUL_FADE = 0.9  # the card fades only after this: the restored window has had time to draw itself
ZACHT = 28  # px: soft edge of the cover when there is no picture of the background
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


# ---------- het portaal ----------
PORTAAL_START = 36  # px: the window starts as a small square of light at the source


def portaal_bron(anim):
    """Source point: the clicked planet/shortcut ('bron'), the dock (minimise) or the middle of the screen."""
    x, y, w, h = anim['rect']
    if anim['soort'] == 'min' and anim.get('dock'):
        return anim['dock']
    b = anim.get('bron')
    if b:
        return float(b[0]), float(b[1])
    sw, sh = anim.get('scherm') or (0, 0)
    return (sw / 2, sh / 2) if sw > 1 else (x + w / 2, y + h / 2)


def portaal_alfa(tt):
    """Alpha of the card on its own curve (opening direction, tt 0..1): fades in quickly in the first 40 %."""
    return clamp(0.3 + 0.7 * ease_out(clamp(tt / 0.4)))


def portaal_schaal(p):
    """How much the glow and the mint edge scale with the card: thin and faint while it is a small square of light,
    full width when it is the window."""
    return 0.45 + 0.55 * clamp(p)


def portaal_frame(anim, t):
    """Window at time t (0..1): rect (x, y, w, h) on its way between source and real rectangle, p (0 = at the source,
    1 = exactly the window), alpha, flare (light point at the source), dek (dark cover over the real window while
    opening). Path: a gentle arc, not a straight line, so it looks thrown out of the planet."""
    x, y, w, h = anim['rect']
    bx, by = portaal_bron(anim)
    soort = anim['soort']
    # 0.3: easing per property. Position ease-out-cubic (quick away from the source, soft landing), size ease-in-out,
    # alpha on its own curve. Closing: size and alpha are the reverse in time of opening; the position is ease-out in the
    # direction of travel as well (quick away from the window, soft landing in the source).
    tt = t if soort == 'open' else 1 - t
    pos = ease_out(tt) if soort == 'open' else 1 - ease_out(t)
    p = ease_in_out(tt)
    tx, ty = x + w / 2, y + h / 2
    # quadratic Bezier with the control point beside the straight line (arc)
    mx, my = (bx + tx) / 2, (by + ty) / 2
    dx, dy = tx - bx, ty - by
    cx, cy = mx - dy * 0.18, my + dx * 0.18
    u = pos
    px = (1 - u) ** 2 * bx + 2 * (1 - u) * u * cx + u ** 2 * tx
    py = (1 - u) ** 2 * by + 2 * (1 - u) * u * cy + u ** 2 * ty
    s = PORTAAL_START
    rw, rh = s + (w - s) * p, s + (h - s) * p
    if soort == 'open':
        flare = math.sin(math.pi * clamp(t / 0.35))
        dek = 1.0 if t < 0.85 else 1 - (t - 0.85) / 0.15
        alpha = portaal_alfa(t)
    else:
        flare = math.sin(math.pi * clamp((t - 0.65) / 0.35))
        dek = 0.0
        alpha = portaal_alfa(1 - t) if t < 0.95 else clamp((1 - t) * 20) * 0.5
    return {'rect': (px - rw / 2, py - rh / 2, rw, rh), 'p': p, 'pos': pos, 'schaal': portaal_schaal(p), 'cx': px, 'cy': py, 'bron': (bx, by),
            'ctrl': (cx, cy), 'doel': (tx, ty), 'alpha': alpha, 'flare': flare, 'dek': dek}


def portaal_spoor(anim, t, punten):
    """The light trail: points on the arc from the window back towards the source (the last 40 % of the way),
    newest first. Fewer points in the light version, the same path."""
    f = portaal_frame(anim, t)
    (bx, by), (cx, cy), (tx, ty) = f['bron'], f['ctrl'], f['doel']
    out = []
    for j in range(punten):
        u = f['pos'] - 0.4 * j / max(1, punten - 1)
        if u < 0:
            break
        out.append(((1 - u) ** 2 * bx + 2 * (1 - u) * u * cx + u ** 2 * tx,
                    (1 - u) ** 2 * by + 2 * (1 - u) * u * cy + u ** 2 * ty, u))
    return out


def rond_pad(cr, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
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
        self.bevroren = None  # (pixbuf, until): the screen as it was before the new window, while it is measured
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
        self.window.connect('show', self.no_input)

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
        if any(e.get('soort') == 'open' for e in events):
            self.bevroren = None  # the portal (with the background under the window) takes over
        for e in events:
            a = dict(e, start=now, traag=factor)
            if a['soort'] == 'zwartgat':
                a['plan'] = zwartgat_plan(a.get('namen') or [])
            # a window that closes during its own opening: replace that animation, never two flowers at once
            if a.get('wid'):
                self.anims = [x for x in self.anims if x.get('wid') != a['wid']]
            self.anims.append(a)
        self.anims = self.anims[-MAX_ANIMS:]
        if not self.window.get_visible():
            self.window.show_all()
            self.no_input()
        if not self.tick:
            licht = all(a.get('kwaliteit') == 'licht' for a in self.anims)
            self.tick = GLib.timeout_add(KWALITEIT['licht' if licht else 'vol']['tick'], self.step)
        return True

    def wek(self, seconden=3.0):
        """Map the (empty, transparent) overlay ahead of an animation that is coming (a program was just clicked), so
        the first frame of the portal does not wait for the layer surface to be configured first."""
        if not self.transparent:
            return False
        from gi.repository import GLib
        if not self.window.get_visible():
            self.window.show_all()
            self.no_input()
        if getattr(self, 'wek_timer', 0):
            GLib.source_remove(self.wek_timer)
        self.wek_timer = GLib.timeout_add(int(seconden * 1000 * traag()), self.wek_klaar)
        return True

    def wek_klaar(self):
        self.wek_timer = 0
        if not self.anims and not self.tick:
            self.window.hide()
        return False

    def bevries(self, pix, seconden=1.5):
        """Show the screen as it was right after the click (before the new window existed) over everything, so the new
        window stays out of sight while it is measured; the portal takes over (ontdooi) or it ends by itself."""
        if not self.transparent or pix is None:
            return False
        from gi.repository import GLib
        self.bevroren = (pix, time.monotonic() + seconden * traag())
        if not self.window.get_visible():
            self.window.show_all()
            self.no_input()
        self.window.queue_draw()
        if not self.tick:
            self.tick = GLib.timeout_add(KWALITEIT['vol']['tick'], self.step)
        return True

    def ontdooi(self):
        if self.bevroren is not None:
            self.bevroren = None
            self.window.queue_draw()

    def klaar(self, now=None):
        """Drop finished animations (also when no frame was drawn), run a reveal that was missed; returns what is left."""
        now = time.monotonic() if now is None else now
        rest = []
        for a in self.anims:
            if voortgang(a, now) is None:
                if a.get('onthul') and not a.get('onthuld'):
                    a['onthuld'] = True
                    from gi.repository import GLib
                    GLib.idle_add(lambda a=a: a['onthul']() and False)
            else:
                rest.append(a)
        self.anims = rest
        return rest

    def step(self):
        self.klaar()
        self.window.queue_draw()
        if self.bevroren is not None and time.monotonic() > self.bevroren[1]:
            self.bevroren = None
        if not self.anims and self.bevroren is None:
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
        if self.bevroren is not None:
            from gi.repository import Gdk
            Gdk.cairo_set_source_pixbuf(cr, self.bevroren[0], 0, 0)
            cr.paint()
        now, alive = time.monotonic(), []
        for anim in self.anims:
            t = voortgang(anim, now)
            if t is None:
                if anim.get('onthul') and not anim.get('onthuld'):  # slow frames skipped the reveal point
                    anim['onthuld'] = True
                    from gi.repository import GLib
                    GLib.idle_add(lambda a=anim: a['onthul']() and False)
                continue
            alive.append(anim)
            try:
                cr.save()
                getattr(self, 'teken_' + ('portaal' if anim['soort'] in ('open', 'sluit', 'min') else anim['soort']))(cr, anim, t, w, h)
            except Exception as error:  # noqa: BLE001 - a broken frame is skipped, never a black screen
                alive.remove(anim)
                self.log('animatie overgeslagen: %s' % error)
            finally:
                cr.restore()
        self.anims = alive
        return True

    # ----- portaal -----
    def teken_portaal(self, cr, anim, t, w, h):
        import cairo
        x, y, bw, bh = anim['rect']
        if anim.get('snel'):  # Animaties verminderd: soft outline on the real rectangle, fade
            open_ = anim['soort'] == 'open'
            a = (1 - t) if open_ else (1 - t) * 0.8
            cr.rectangle(x, y, bw, bh)
            cr.set_source_rgba(*MINT, 0.5 * a)
            cr.set_line_width(2)
            cr.stroke()
            return
        q = kwaliteit(anim)
        anim.setdefault('scherm', (w, h))
        f = portaal_frame(anim, t)
        if anim.get('verborgen') and t > ONTHUL_FADE:  # the real window is there and drawn: the card fades away
            f['alpha'] *= clamp((1 - t) / (1 - ONTHUL_FADE))
        rx, ry, rw, rh = f['rect']
        bx, by = f['bron']
        # 1. while opening: the real window stays hidden behind a dark cover until the portal arrives
        if f['dek'] > 0.01 and not anim.get('verborgen'):  # 0.2.39: a window hidden at map needs no cover
            self.teken_dek(cr, anim, x, y, bw, bh, f['dek'])
        if anim.get('onthul') and t >= ONTHUL_BIJ and not anim.get('onthuld'):
            anim['onthuld'] = True  # the window is restored under the arriving card, which then fades out
            from gi.repository import GLib
            GLib.idle_add(lambda: anim['onthul']() and False)
        # 2. light trail from the source along the arc to the window (tapered, fading towards the source)
        spoor = portaal_spoor(anim, t, q['spoor'])
        zicht = math.sin(math.pi * clamp(f['pos'] * 0.98 + 0.02)) if anim['soort'] == 'open' else math.sin(math.pi * f['pos'])
        sc = f['schaal']
        for j in range(len(spoor) - 1):
            (x0, y0, _), (x1, y1, _) = spoor[j], spoor[j + 1]
            fade = (1 - j / len(spoor)) * zicht
            for width, a in q['gloed']:
                cr.set_line_width((width * 2.4 * (1 - j / len(spoor)) + 1.0) * sc)
                cr.set_source_rgba(*MINT, a * fade)
                cr.move_to(x0, y0)
                cr.line_to(x1, y1)
                cr.stroke()
        # 3. the window itself on its way: real content (vol) or a glowing glass card (licht)
        radius = 6 + 18 * (1 - f['p'])
        cr.save()
        rond_pad(cr, rx, ry, rw, rh, radius)
        cr.clip()
        pix = anim.get('pix') if q['inhoud'] else None
        if pix is not None:
            from gi.repository import Gdk
            cr.save()
            cr.translate(rx, ry)
            cr.scale(rw / pix.get_width(), rh / pix.get_height())
            Gdk.cairo_set_source_pixbuf(cr, pix, 0, 0)
            cr.paint_with_alpha(f['alpha'])
            cr.restore()
        else:
            grad = cairo.LinearGradient(rx, ry, rx, ry + rh)
            grad.add_color_stop_rgba(0, 0.16, 0.22, 0.32, 0.92 * f['alpha'])
            grad.add_color_stop_rgba(1, 0.07, 0.10, 0.18, 0.92 * f['alpha'])
            cr.set_source(grad)
            cr.paint()
            cr.rectangle(rx, ry, rw, min(rh, 28 * max(0.3, f['p'])))  # title bar
            cr.set_source_rgba(*MINT, 0.18 * f['alpha'])
            cr.fill()
        # light washing over the window while it is still small
        licht = (1 - f['p']) * f['alpha']
        if licht > 0.02:
            cr.set_source_rgba(0.9, 1, 0.97, 0.55 * licht)
            cr.paint()
        cr.restore()
        # 4. glowing edge, strongest while travelling
        rand = (0.25 + 0.75 * (1 - f['p'])) * f['alpha']
        rond_pad(cr, rx, ry, rw, rh, radius)
        for width, a in q['gloed']:
            cr.set_line_width(width * sc)  # glow and mint edge scale with the card
            cr.set_source_rgba(*MINT, a * rand)
            cr.stroke_preserve()
        cr.new_path()
        # 5. the flare at the planet / shortcut: the window is born from (or returns into) a point of light
        if f['flare'] > 0.02:
            r = (26 + 46 * f['flare']) * (0.7 + 0.3 * sc)
            grad = cairo.RadialGradient(bx, by, 0, bx, by, r)
            grad.add_color_stop_rgba(0, 1, 1, 1, 0.95 * f['flare'])
            grad.add_color_stop_rgba(0.35, *MINT, 0.55 * f['flare'])
            grad.add_color_stop_rgba(1, *MINT, 0)
            cr.set_source(grad)
            cr.arc(bx, by, r, 0, 2 * math.pi)
            cr.fill()
            if q['lens'] > 1:  # thin horizontal lens streak
                lin = cairo.LinearGradient(bx - r * 2.5, by, bx + r * 2.5, by)
                lin.add_color_stop_rgba(0, *MINT, 0)
                lin.add_color_stop_rgba(0.5, 1, 1, 1, 0.6 * f['flare'])
                lin.add_color_stop_rgba(1, *MINT, 0)
                cr.set_source(lin)
                cr.rectangle(bx - r * 2.5, by - 1.5, r * 5, 3)
                cr.fill()

    def teken_dek(self, cr, anim, x, y, bw, bh, dek):
        """0.2.38 (Jesse: the dark cover looked like a dark block): cover the real window with what was behind it (a
        screenshot taken right after the click, 'achter'), so it simply looks like the window is not there yet. Without
        that picture: the space colour with soft edges fading outwards, never a hard rectangle."""
        import cairo
        achter = anim.get('achter')
        if achter is not None:
            from gi.repository import Gdk
            ax, ay = anim.get('achter_xy', (x, y))
            cr.save()
            cr.rectangle(x, y, bw, bh)
            cr.clip()
            Gdk.cairo_set_source_pixbuf(cr, achter, ax, ay)
            cr.paint_with_alpha(dek)
            cr.restore()
            return
        r = ZACHT
        cr.save()
        cr.rectangle(x, y, bw, bh)
        cr.set_source_rgba(*RUIMTE, dek)
        cr.fill()
        for (gx0, gy0, gx1, gy1, rx, ry, rw, rh) in (
                (x, 0, x - r, 0, x - r, y, r, bh), (x + bw, 0, x + bw + r, 0, x + bw, y, r, bh),
                (0, y, 0, y - r, x, y - r, bw, r), (0, y + bh, 0, y + bh + r, x, y + bh, bw, r)):
            g = cairo.LinearGradient(gx0, gy0, gx1, gy1)
            g.add_color_stop_rgba(0, *RUIMTE, dek)
            g.add_color_stop_rgba(1, *RUIMTE, 0)
            cr.set_source(g)
            cr.rectangle(rx, ry, rw, rh)
            cr.fill()
        for (cx, cy, hx, hy) in ((x, y, -1, -1), (x + bw, y, 1, -1), (x, y + bh, -1, 1), (x + bw, y + bh, 1, 1)):
            g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
            g.add_color_stop_rgba(0, *RUIMTE, dek)
            g.add_color_stop_rgba(1, *RUIMTE, 0)
            cr.set_source(g)
            cr.rectangle(min(cx, cx + hx * r), min(cy, cy + hy * r), r, r)
            cr.fill()
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
            self.zwartgat_schijf(cr, x, y, g, G, f['draai'], voeding, achter=True, anim=anim)
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
            ringgloed = ((g * 0.5, 0.08), (g * 0.22, 0.18), (g * 0.08, 0.5), (1.6, 0.95))
            for width, a in (ringgloed if kwaliteit(anim)['lens'] > 1 else ringgloed[2:]):
                cr.set_line_width(width)
                cr.set_source_rgba(1, 0.9, 0.72, a * G * (1 + 0.5 * voeding))
                cr.arc(x, y, g * 1.06, 0, 2 * math.pi)
                cr.stroke()
            self.zwartgat_schijf(cr, x, y, g, G, f['draai'], voeding, achter=False, anim=anim)

    def zwartgat_schijf(self, cr, x, y, g, G, draai, voeding, achter, anim=None):
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
            for rr, a in ((1.35, 0.55), (1.6, 0.3), (1.9, 0.14))[:kwaliteit(anim or {})['lens']]:
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
        q = kwaliteit(anim or {})
        segmenten = q['segmenten']
        a0, a1 = (math.pi, 2 * math.pi) if achter else (0, math.pi)
        for ring, (rr, breed, helder) in enumerate(((1.5, 0.35, 1.0), (2.0, 0.45, 0.8), (2.7, 0.6, 0.5), (3.5, 0.7, 0.25))[:q['ringen']]):
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
            for j in range(kwaliteit(anim)['spoor']):
                sp = zwartgat_item(item, max(item['vertrek'], s - j * 0.025))
                if isinstance(sp, dict):
                    punten.append((x + sp['r'] * math.cos(sp['a']), y + sp['r'] * math.sin(sp['a']), sp['rood']))
            for j in range(len(punten) - 1):
                (x0, y0, r0), (x1, y1, _) = punten[j], punten[j + 1]
                col = roodverschuiving(r0)
                fade = (1 - j / len(punten)) * licht * zicht
                for width, al in (((9, 0.12), (4, 0.35), (1.6, 0.95)) if kwaliteit(anim)['lens'] > 1 else ((3, 0.6),)):
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
