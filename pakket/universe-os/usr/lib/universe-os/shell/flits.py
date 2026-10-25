"""Venster-animatie (0.2.35): een venster komt binnen als ruimtebericht / hologram-transmissie.

Native GTK/cairo op een eigen layer-shell-oppervlak (OVERLAY, geen toetsenbord, lege invoerregio): het echte venster is
meteen klikbaar en houdt de focus. Eerst was dit een WebKit-pagina, maar een volledig scherm WebKit-oppervlak tekent
zwart zolang de pagina laadt (laptop-VM 25 Oct: zwart scherm). Cairo op een RGBA-visual is vanaf het eerste beeld
doorzichtig. Het oppervlak staat alleen tijdens een animatie op het scherm.
"""
import math
import os
import time

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import GLib, Gtk, GtkLayerShell  # noqa: E402

MINT = (0x85 / 255, 0xff / 255, 0xe3 / 255)
DUUR = {'open': 0.30, 'sluit': 0.18, 'min': 0.22}
SNEL = 0.15
TRAAG_BESTAND = '/tmp/universe-flits-traag'  # alleen voor tests: een factor (bv. 20) maakt de animatie trager


def traag():
    try:
        with open(TRAAG_BESTAND) as f:
            return max(1.0, min(50.0, float(f.read().strip() or 1)))
    except (OSError, ValueError):
        return 1.0


def ease_out(t):
    return 1 - (1 - t) ** 4


def ease_in(t):
    return t ** 3


def vak(maximized, w, h):
    if maximized:
        return 0.0, 0.0, float(w), float(h - 80)
    vw, vh = w * 0.55, h * 0.55
    return (w - vw) / 2, (h - vh) / 2.4, vw, vh


def frame(anim, now, w, h):
    """State of one animation at time now: None when finished, else (x, y, bw, bh, alpha, scan, glow)."""
    soort, snel = anim['soort'], anim['snel']
    duur = (SNEL if snel else DUUR.get(soort, DUUR['open'])) * anim.get('traag', 1.0)
    t = (now - anim['start']) / duur
    if t >= 1:
        return None
    t = max(0.0, t)
    x, y, bw, bh = vak(anim['max'], w, h)
    ox, oy = (w / 2, h - 40) if anim['van'] == 'dock' else (x + bw / 2, y + bh / 2)
    if soort == 'open':
        if snel:
            scale, alpha = 0.96 + 0.04 * ease_out(t), math.sin(math.pi * t) * 0.6
        else:
            p = ease_out(min(1.0, t / 0.6))
            scale = 0.08 + 0.92 * p
            alpha = p if t < 0.6 else 1 - (t - 0.6) / 0.4  # in, then fades into the sharp real window
            if 0.62 < t < 0.72:
                alpha *= 0.7  # one short flicker
    else:
        if snel:
            scale, alpha = 1 - 0.04 * t, 0.5 * (1 - t)
        else:
            scale, alpha = 1 - 0.92 * ease_in(t), 0.9 * (1 - ease_in(t))
    nx, ny = ox + (x - ox) * scale, oy + (y - oy) * scale
    return nx, ny, bw * scale, bh * scale, max(0.0, min(1.0, alpha)), (t if soort == 'open' and not snel else None), not snel


def rounded(cr, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


class Flits:
    def __init__(self, log):
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

    def play(self, events):
        if not self.transparent:
            return False  # without an RGBA visual the overlay would be a black screen: no animation
        now, factor = time.monotonic(), traag()
        for e in events:
            self.anims.append(dict(e, start=now, traag=factor))
        self.anims = self.anims[-6:]
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
            f = frame(anim, now, w, h)
            if f is None:
                continue
            alive.append(anim)
            x, y, bw, bh, alpha, scan, glow = f
            if bw < 2 or bh < 2 or alpha <= 0.01:
                continue
            r = 12 * min(1.0, bw / 200)
            rounded(cr, x, y, bw, bh, r)
            cr.set_source_rgba(*MINT, (0.06 if glow else 0.03) * alpha)
            cr.fill_preserve()
            if glow:  # wider, fainter strokes make the glow; no filters
                for width, a in ((14, 0.08), (8, 0.16), (4, 0.3)):
                    cr.set_line_width(width)
                    cr.set_source_rgba(*MINT, a * alpha)
                    cr.stroke_preserve()
            cr.set_line_width(2)
            cr.set_source_rgba(*MINT, (1.0 if glow else 0.45) * alpha)
            cr.stroke()
            if scan is not None:
                cr.save()
                rounded(cr, x, y, bw, bh, r)
                cr.clip()
                cr.set_source_rgba(*MINT, 0.07 * alpha)
                for ly in range(int(y), int(y + bh), 4):  # faint hologram lines
                    cr.rectangle(x, ly, bw, 1)
                cr.fill()
                sy = y - bh * 0.2 + (bh * 1.2) * ease_out(scan)
                grad = cairo.LinearGradient(0, sy, 0, sy + bh * 0.2)
                grad.add_color_stop_rgba(0, *MINT, 0)
                grad.add_color_stop_rgba(0.5, 0.91, 1, 0.98, 0.55 * alpha)
                grad.add_color_stop_rgba(1, *MINT, 0)
                cr.set_source(grad)
                cr.rectangle(x, sy, bw, bh * 0.2)
                cr.fill()
                cr.restore()
        self.anims = alive
        return True
