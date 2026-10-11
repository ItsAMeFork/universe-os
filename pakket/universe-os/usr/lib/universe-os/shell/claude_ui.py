"""Claude in Universe OS: the Claude panel (a real terminal running the unmodified Claude Code) and the buddy.

The buddy is the body of Claude Code: it never talks to Claude itself. Claude Code reports every step through its
hooks (universe-claude-hook -> universe-ctl claude-event), and the buddy plays the matching animation and walks to
where the action is. Both only exist when Claude Code is installed (docs/CLAUDE-IN-UNIVERSE.md).

Light on purpose: no WebKit here. The buddy is a small Cairo-drawn layer surface that moves by changing its margins;
it only redraws while it animates (a blink every few seconds otherwise).
"""
import math
import os
import random
import shutil
import time

import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell  # noqa: E402

PANEL_WIDTH = 620
KEEP_ALIVE = 600  # seconds Claude Code keeps running after the panel is closed
BUDDY = (132, 150)  # surface size
TEAL = (0.52, 1.0, 0.89)
ORANGE = (1.0, 0.62, 0.26)

CSS = b"""
.claude-head { padding: 10px 12px 6px 16px; }
.claude-title { color: #e8fffa; font-weight: 700; font-size: 15px; }
.claude-sub { color: rgba(232, 255, 250, 0.55); font-size: 12px; }
.claude-dot { color: #85ffe3; }
.claude-btn { background: rgba(133, 255, 227, 0.08); color: #e8fffa; border: none; border-radius: 10px;
              padding: 4px 10px; box-shadow: none; text-shadow: none; }
.claude-btn:hover { background: rgba(255, 158, 66, 0.22); }
.claude-term { padding: 4px 10px 12px 14px; }
"""


def find_claude():
    """Path of the claude command, also when ~/.local/bin (official installer) is not on the shell's PATH."""
    for path in (shutil.which('claude'), os.path.expanduser('~/.local/bin/claude'), os.path.expanduser('~/.claude/local/claude')):
        if path and os.access(path, os.X_OK):
            return path
    return None


def ease(t):
    return 1 - (1 - t) ** 3


class ClaudeUI:
    def __init__(self, shell, log):
        self.shell = shell
        self.log = log
        self.panel = None
        self.term = None
        self.alive_timer = 0
        self.buddy = None
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def available(self):
        return find_claude() is not None

    def animations(self):
        import config
        return config.settings().get('animations', 'full')

    # ----- buddy -----
    def update_buddy(self):
        """Shows or removes the buddy according to the setting and whether Claude Code is installed."""
        import config
        want = bool(config.settings().get('buddy', True)) and self.available()
        if want and not self.buddy:
            self.buddy = Buddy(self)
        elif not want and self.buddy:
            self.buddy.destroy()
            self.buddy = None
        return False

    def event(self, kind, data=None):
        if kind == 'permission' and self.panel and not self.panel.get_visible():
            self.open()
        if self.buddy:
            self.buddy.event(kind, data or {})
        return True

    # ----- panel -----
    def toggle(self, open_=None):
        visible = bool(self.panel and self.panel.get_visible())
        if open_ is None:
            open_ = not visible
        if open_:
            self.open()
        else:
            self.close()
        return True

    def build_panel(self):
        L, E, K = GtkLayerShell.Layer, GtkLayerShell.Edge, GtkLayerShell.KeyboardMode
        win = Gtk.Window()
        win.set_title('Universe Claude')
        visual = win.get_screen().get_rgba_visual()
        if visual:
            win.set_visual(visual)
        win.set_app_paintable(True)
        GtkLayerShell.init_for_window(win)
        GtkLayerShell.set_namespace(win, 'universe-claude')
        GtkLayerShell.set_layer(win, L.TOP)
        for edge in (E.TOP, E.BOTTOM, E.RIGHT):
            GtkLayerShell.set_anchor(win, edge, True)
        GtkLayerShell.set_margin(win, E.TOP, 56)
        GtkLayerShell.set_margin(win, E.BOTTOM, 84)
        GtkLayerShell.set_margin(win, E.RIGHT, 12)
        GtkLayerShell.set_keyboard_mode(win, K.EXCLUSIVE)
        win.set_size_request(PANEL_WIDTH, -1)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class('claude-panel')
        head = Gtk.Box(spacing=8)
        head.get_style_context().add_class('claude-head')
        dot = Gtk.Label(label='●')
        dot.get_style_context().add_class('claude-dot')
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        title = Gtk.Label(label='Claude', xalign=0)
        title.get_style_context().add_class('claude-title')
        sub = Gtk.Label(label='Claude Code met Haiku · /model om te wisselen', xalign=0)
        sub.get_style_context().add_class('claude-sub')
        titles.pack_start(title, False, False, 0)
        titles.pack_start(sub, False, False, 0)
        new = Gtk.Button(label='Nieuw gesprek')
        new.connect('clicked', lambda b: self.restart(fresh=True))
        close = Gtk.Button(label='✕')
        close.set_tooltip_text('Sluiten (Windows+C)')
        close.connect('clicked', lambda b: self.close())
        for b in (new, close):
            b.get_style_context().add_class('claude-btn')
            b.set_can_focus(False)
        head.pack_start(dot, False, False, 0)
        head.pack_start(titles, True, True, 0)
        head.pack_end(close, False, False, 0)
        head.pack_end(new, False, False, 0)
        holder = Gtk.Box()
        holder.get_style_context().add_class('claude-term')
        box.pack_start(head, False, False, 0)
        box.pack_start(holder, True, True, 0)
        win.add(box)
        win.connect('draw', self.draw_panel)
        win.connect('delete-event', lambda *a: self.close() or True)
        self.panel = win
        self.holder = holder

    def draw_panel(self, win, cr):
        """Glass background with rounded corners (a GtkBox draws no CSS background in this GTK version)."""
        w, h, r = win.get_allocated_width(), win.get_allocated_height(), 18
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.new_sub_path()
        cr.arc(w - r - 0.5, r + 0.5, r, -math.pi / 2, 0)
        cr.arc(w - r - 0.5, h - r - 0.5, r, 0, math.pi / 2)
        cr.arc(r + 0.5, h - r - 0.5, r, math.pi / 2, math.pi)
        cr.arc(r + 0.5, r + 0.5, r, math.pi, 1.5 * math.pi)
        cr.close_path()
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgba(0, 0.035, 0.06, 0.15, 0.97)
        g.add_color_stop_rgba(1, 0.02, 0.035, 0.09, 0.97)
        cr.set_source(g)
        cr.fill_preserve()
        cr.set_line_width(1)
        cr.set_source_rgba(*TEAL, 0.32)
        cr.stroke()
        return False

    def start_terminal(self, fresh=False):
        gi.require_version('Vte', '2.91')
        from gi.repository import Pango, Vte
        term = Vte.Terminal()
        bg = Gdk.RGBA(0.02, 0.04, 0.10, 0.0)
        fg = Gdk.RGBA(0.91, 1.0, 0.98, 1.0)
        palette = [Gdk.RGBA() for _ in range(16)]
        for rgba, spec in zip(palette, ('#0b1022', '#ff6b6b', '#5ef0c4', '#ffb357', '#6aa8ff', '#c792ea', '#85ffe3', '#d8e6f0',
                                        '#3a4566', '#ff8b8b', '#85ffe3', '#ffc97a', '#8ec0ff', '#dcb2ff', '#b0fff0', '#ffffff')):
            rgba.parse(spec)
        term.set_colors(fg, bg, palette)
        term.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        term.set_scrollback_lines(5000)
        term.set_font(Pango.FontDescription('Monospace 11'))
        term.connect('child-exited', self.child_exited)
        argv = ['/usr/bin/universe-claude'] + (['--nieuw'] if fresh else [])
        term.spawn_async(Vte.PtyFlags.DEFAULT, os.path.expanduser('~'), argv, None, GLib.SpawnFlags.DEFAULT,
                         None, None, -1, None, None, None)
        self.holder.pack_start(term, True, True, 0)
        term.show()
        self.term = term

    def open(self):
        if not self.available():
            self.log('Claude Code is niet geïnstalleerd; paneel niet geopend.')
            return False
        if self.alive_timer:
            GLib.source_remove(self.alive_timer)
            self.alive_timer = 0
        if self.panel is None:
            self.build_panel()
        if self.term is None:
            self.start_terminal()
        E, K = GtkLayerShell.Edge, GtkLayerShell.KeyboardMode
        GtkLayerShell.set_keyboard_mode(self.panel, K.EXCLUSIVE)
        if not self.panel.get_visible():
            self.panel.show_all()
            if self.animations() == 'full':
                self.slide(-PANEL_WIDTH, 12)
        self.panel.present()
        self.term.grab_focus()
        # Typing goes to the panel now; afterwards a click elsewhere may take the keyboard again.
        GLib.timeout_add(400, lambda: self.panel and GtkLayerShell.set_keyboard_mode(self.panel, K.ON_DEMAND) and False)
        if self.buddy:
            self.buddy.event('panel', {})
        return True

    def slide(self, start, end, done=None):
        E = GtkLayerShell.Edge
        t0 = time.monotonic()

        def step():
            if not self.panel:
                return False
            t = min(1.0, (time.monotonic() - t0) / 0.22)
            GtkLayerShell.set_margin(self.panel, E.RIGHT, int(start + (end - start) * ease(t)))
            if t >= 1.0:
                if done:
                    done()
                return False
            return True
        GtkLayerShell.set_margin(self.panel, E.RIGHT, start)
        GLib.timeout_add(16, step)

    def close(self):
        if not (self.panel and self.panel.get_visible()):
            return False
        if self.animations() == 'full':
            self.slide(12, -PANEL_WIDTH, self.panel.hide)
        else:
            self.panel.hide()
        if self.term and not self.alive_timer:
            self.alive_timer = GLib.timeout_add_seconds(KEEP_ALIVE, self.stop_terminal)
        if self.buddy:
            self.buddy.event('home', {})
        return False

    def stop_terminal(self):
        """Claude Code stops some minutes after the panel closed, to give its memory back."""
        self.alive_timer = 0
        if self.term:
            self.term.destroy()  # closes the pty: Claude Code gets SIGHUP
            self.term = None
        return False

    def restart(self, fresh=False):
        self.stop_terminal()
        self.start_terminal(fresh=fresh)
        self.term.grab_focus()

    def child_exited(self, term, status):
        if term is self.term:
            self.term = None
            GLib.idle_add(lambda: term.destroy() or False)
            self.close()


class Buddy:
    """The placeholder character: a small planet with eyes and an orange ring. States: idle, listen, think, work,
    attention, happy. Walks between home (above the dock, right), the dock, the middle of the world and the panel."""

    def __init__(self, ui):
        self.ui = ui
        L, E, K = GtkLayerShell.Layer, GtkLayerShell.Edge, GtkLayerShell.KeyboardMode
        win = Gtk.Window()
        win.set_title('Universe Claude buddy')
        visual = win.get_screen().get_rgba_visual()
        if visual:
            win.set_visual(visual)
        win.set_app_paintable(True)
        GtkLayerShell.init_for_window(win)
        GtkLayerShell.set_namespace(win, 'universe-buddy')
        GtkLayerShell.set_layer(win, L.TOP)
        GtkLayerShell.set_anchor(win, E.BOTTOM, True)
        GtkLayerShell.set_anchor(win, E.RIGHT, True)
        GtkLayerShell.set_keyboard_mode(win, K.NONE)
        win.set_size_request(*BUDDY)
        area = Gtk.DrawingArea()
        area.set_size_request(*BUDDY)
        area.connect('draw', self.draw)
        area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        area.connect('button-press-event', self.clicked)
        win.add(area)
        win.set_tooltip_text('Claude (Windows+C)')
        self.window, self.area = win, area
        self.state = 'idle'
        self.state_since = time.monotonic()
        self.pos = self.place('home')
        self.target = self.pos
        self.move_from = self.pos
        self.move_t0 = 0
        self.facing = -1
        self.busy = False  # a program is in front: stand still
        self.blink = 0.0
        self.anim = 0
        self.slow_frames = 0
        self.last_frame = 0
        self.apply_pos()
        win.show_all()
        self.blink_timer = GLib.timeout_add_seconds(4, self.schedule_blink)
        # Arrive: a short hop out of the corner.
        self.set_state('happy')

    def destroy(self):
        for t in (self.anim, self.blink_timer):
            if t:
                GLib.source_remove(t)
        self.anim = self.blink_timer = 0
        self.window.destroy()

    # ----- places on screen (margins from the bottom-right corner) -----
    def screen(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geo = monitor.get_geometry()
        return geo.width, geo.height

    def place(self, name):
        w, h = self.screen()
        bw, bh = BUDDY
        if name == 'dock':
            return (w // 2 - bw // 2, 76)
        if name == 'world':
            return (w // 2 - bw // 2, h // 2 - bh // 2)
        if name == 'panel':
            return (PANEL_WIDTH + 24, 96)
        return (24, 84)  # home: above the dock, right

    def apply_pos(self):
        E = GtkLayerShell.Edge
        GtkLayerShell.set_margin(self.window, E.RIGHT, int(self.pos[0]))
        GtkLayerShell.set_margin(self.window, E.BOTTOM, int(self.pos[1]))

    def go(self, name):
        target = self.place(name)
        if target == self.target:
            return
        if self.ui.animations() != 'full':
            self.pos = self.target = target
            self.apply_pos()
            return
        self.move_from, self.target = self.pos, target
        self.move_t0 = time.monotonic()
        # Margins count from the right: a larger right margin = further left.
        self.facing = -1 if target[0] > self.pos[0] else 1
        self.run()

    # ----- events from Claude Code (hooks) -----
    def event(self, kind, data):
        place = data.get('place') if isinstance(data, dict) else None
        if kind == 'listen':
            self.set_state('listen')
        elif kind == 'think':
            self.set_state('think')
        elif kind == 'tool':
            self.set_state('work')
            if place in ('dock', 'world', 'panel', 'home'):
                self.go(place)
        elif kind == 'tool-done':
            self.set_state('think')
        elif kind == 'permission':
            self.go('panel')
            self.set_state('attention')
        elif kind == 'done':
            self.set_state('happy')
            GLib.timeout_add(1800, self.go_home_if_idle)
        elif kind == 'panel':
            self.go('panel')
            self.set_state('listen')
        elif kind == 'home':
            self.go('home')
            self.set_state('idle')
        return True

    def go_home_if_idle(self):
        if self.state in ('idle', 'happy') and not (self.ui.panel and self.ui.panel.get_visible()):
            self.go('home')
        return False

    def set_busy(self, busy):
        self.busy = busy

    def set_state(self, state):
        self.state = state
        self.state_since = time.monotonic()
        self.run()

    # ----- animation loop: only runs while something moves -----
    def moving(self):
        return self.pos != self.target

    def animated_state(self):
        if self.state == 'happy' and time.monotonic() - self.state_since > 1.6:
            self.state = 'idle'
        return self.state not in ('idle',)

    def run(self):
        if self.ui.animations() == 'off':
            self.area.queue_draw()
            return
        if not self.anim:
            self.slow_frames = 0
            self.last_frame = time.monotonic()
            self.anim = GLib.timeout_add(33, self.tick)
        self.area.queue_draw()

    def tick(self):
        now = time.monotonic()
        # Slow computer: two frames much later than planned -> stop animating, jump to the end (like the login).
        self.slow_frames = self.slow_frames + 1 if now - self.last_frame > 0.25 else 0
        self.last_frame = now
        if self.slow_frames >= 2:
            self.pos = self.target
            self.apply_pos()
            self.anim = 0
            self.area.queue_draw()
            return False
        if self.moving():
            t = min(1.0, (now - self.move_t0) / 0.9)
            k = ease(t)
            self.pos = (self.move_from[0] + (self.target[0] - self.move_from[0]) * k,
                        self.move_from[1] + (self.target[1] - self.move_from[1]) * k)
            if t >= 1.0:
                self.pos = self.target
            self.apply_pos()
        self.area.queue_draw()
        if self.moving() or self.animated_state() or self.blink > 0:
            if self.blink > 0:
                self.blink = max(0.0, self.blink - 0.2)
            return True
        self.anim = 0
        return False

    def schedule_blink(self):
        if not self.busy and self.ui.animations() != 'off' and random.random() < 0.8:
            self.blink = 1.0
            self.run()
        return True

    def clicked(self, widget, event):
        self.ui.toggle()
        return True

    # ----- drawing -----
    def draw(self, widget, cr):
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        w, h = BUDDY
        t = time.monotonic() - self.state_since
        state = self.state
        walking = self.moving()
        hop = 0.0
        if state == 'happy':
            hop = abs(math.sin(t * 7)) * 16 * max(0.0, 1 - t / 1.6)
        elif state == 'attention':
            hop = abs(math.sin(t * 9)) * 8
        elif walking:
            hop = abs(math.sin(time.monotonic() * 12)) * 6
        cx, cy, r = w / 2, h - 52 - hop, 34

        # shadow
        cr.save()
        cr.translate(cx, h - 12)
        cr.scale(1, 0.28)
        cr.arc(0, 0, r * (0.9 - hop / 80), 0, 2 * math.pi)
        cr.restore()
        cr.set_source_rgba(0, 0, 0, 0.35)
        cr.fill()

        # glow while listening / working
        if state in ('listen', 'work', 'attention'):
            pulse = 0.5 + 0.5 * math.sin(t * (8 if state == 'work' else 4))
            color = ORANGE if state == 'attention' else TEAL
            cr.arc(cx, cy, r + 8 + pulse * 4, 0, 2 * math.pi)
            cr.set_source_rgba(*color, 0.12 + 0.12 * pulse)
            cr.fill()

        # ring behind the body
        spin = t * (6 if state == 'work' else 0.8)
        self.ring(cr, cx, cy, r, spin, back=True)

        # body: a small teal planet
        g = cairo.RadialGradient(cx - r * 0.35, cy - r * 0.4, r * 0.1, cx, cy, r)
        g.add_color_stop_rgb(0, 0.75, 1.0, 0.95)
        g.add_color_stop_rgb(0.55, 0.20, 0.72, 0.70)
        g.add_color_stop_rgb(1, 0.05, 0.22, 0.32)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.set_source(g)
        cr.fill()

        # eyes
        look = 4 * -self.facing if walking else 0
        eye_y = cy - 4
        for ex in (cx - 11 + look, cx + 11 + look):
            if state == 'happy':
                cr.set_line_width(3)
                cr.set_source_rgb(0.04, 0.08, 0.16)
                cr.arc(ex, eye_y + 3, 6, math.pi * 1.1, math.pi * 1.9)
                cr.stroke()
                continue
            open_ = 1.0 - self.blink if self.blink > 0 else 1.0
            size = 8 if state in ('listen', 'attention') else 7
            if state == 'work':
                size = 6
            cr.save()
            cr.translate(ex, eye_y)
            cr.scale(1, max(0.12, open_))
            cr.arc(0, 0, size, 0, 2 * math.pi)
            cr.restore()
            cr.set_source_rgb(1, 1, 1)
            cr.fill()
            if open_ > 0.3:
                px = ex + (1.5 if state == 'think' else look * 0.4)
                py = eye_y - (3 if state == 'think' else 0)
                cr.arc(px, py, size * 0.5, 0, 2 * math.pi)
                cr.set_source_rgb(0.04, 0.08, 0.16)
                cr.fill()

        # mouth
        cr.set_line_width(2.5)
        cr.set_source_rgb(0.04, 0.08, 0.16)
        if state in ('happy', 'listen'):
            cr.arc(cx, cy + 9, 7, 0.15 * math.pi, 0.85 * math.pi)
        elif state == 'attention':
            cr.arc(cx, cy + 13, 4, 0, 2 * math.pi)
        else:
            cr.move_to(cx - 5, cy + 13)
            cr.line_to(cx + 5, cy + 13)
        cr.stroke()

        # ring in front
        self.ring(cr, cx, cy, r, spin, back=False)

        # thinking: three dots circling above the head
        if state in ('think', 'work'):
            for i in range(3):
                a = t * 3 + i * 2 * math.pi / 3
                cr.arc(cx + math.cos(a) * 18, cy - r - 16 + math.sin(a) * 5, 3.5, 0, 2 * math.pi)
                cr.set_source_rgba(*TEAL, 0.5 + 0.5 * (math.sin(a) + 1) / 2)
                cr.fill()
        # attention: an orange exclamation mark
        if state == 'attention':
            cr.set_source_rgb(*ORANGE)
            cr.rectangle(cx + r - 2, cy - r - 22, 6, 16)
            cr.fill()
            cr.arc(cx + r + 1, cy - r - 1, 3.5, 0, 2 * math.pi)
            cr.fill()
        # happy: sparkles
        if state == 'happy' and t < 1.6:
            for i in range(5):
                a = i * 2 * math.pi / 5 + t
                d = r + 10 + t * 18
                cr.arc(cx + math.cos(a) * d, cy + math.sin(a) * d * 0.7, 2.5 * (1 - t / 1.6), 0, 2 * math.pi)
                cr.set_source_rgba(*ORANGE, 1 - t / 1.6)
                cr.fill()
        return False

    def ring(self, cr, cx, cy, r, spin, back):
        """Orange ring around the planet, drawn in two halves so the body sits inside it."""
        cr.save()
        cr.translate(cx, cy)
        cr.rotate(-0.35)
        cr.scale(1, 0.28)
        cr.set_line_width(5)
        start, end = (math.pi, 2 * math.pi) if back else (0, math.pi)
        cr.arc(0, 0, r + 12, start, end)
        cr.restore()
        cr.set_source_rgba(*ORANGE, 0.55 if back else 0.95)
        cr.stroke()
        # a little moon on the ring shows the spin
        a = spin % (2 * math.pi)
        if (math.sin(a) >= 0) != back:
            x = math.cos(a) * (r + 12)
            y = math.sin(a) * (r + 12) * 0.28
            rx = x * math.cos(-0.35) - y * math.sin(-0.35)
            ry = x * math.sin(-0.35) + y * math.cos(-0.35)
            cr.arc(cx + rx, cy + ry, 4, 0, 2 * math.pi)
            cr.set_source_rgb(1, 0.85, 0.6)
            cr.fill()
