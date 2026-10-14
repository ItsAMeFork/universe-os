"""Claude in Universe OS: the Claude panel (a real terminal running the unmodified Claude Code) and the buddy.

The buddy (a floating slime with eyes) is the body of Claude Code: it never talks to Claude itself. Claude Code reports every step through its
hooks (universe-claude-hook -> universe-ctl claude-event), and the buddy plays the matching animation and walks to
where the action is. Both only exist when Claude Code is installed (docs/CLAUDE-IN-UNIVERSE.md).

Light on purpose: no WebKit here. The buddy is a small Cairo-drawn layer surface that moves by changing its margins;
it only redraws while it animates (a blink every few seconds otherwise).
"""
import math
import os
import random
import sys
import time

import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gdk, Gio, GLib, Gtk, GtkLayerShell  # noqa: E402

PANEL_WIDTH = 620
KEEP_ALIVE = 600  # seconds Claude Code keeps running after the panel is closed
BUDDY = (132, 150)  # surface size
BUBBLE_WIDTH = 330  # surface width while the speech bubble shows
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
.buddy-hint { padding: 14px 16px 24px 16px; }
.buddy-text { color: #e8fffa; font-size: 14px; }
.buddy-main { background: rgba(255, 158, 66, 0.85); color: #1a0e02; font-weight: 700; }
"""


def _ai():
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'claude')
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import ai_provider
    return ai_provider


def find_claude():
    """Path of the claude command, also when ~/.local/bin (official installer) is not on the shell's PATH."""
    return _ai().bin_for('claude')


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
        info = _ai().load()
        return _ai().installed(info['provider'])

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
            if not getattr(self, 'hints', None):
                try:
                    from buddy_hints import Hints
                    self.hints = Hints(self, self.log)
                except Exception as error:  # pragma: no cover - only logged
                    self.log('Suggesties van het personage niet gestart: %s' % error)
        elif not want and self.buddy:
            self.buddy.destroy()
            self.buddy = None
        return False

    def ask(self, question):
        """Puts a ready-made question in the Claude panel. The user sends it with Enter: the buddy itself never sends
        anything to Claude. A freshly started Claude Code needs a few seconds before it reads input."""
        fresh = self.term is None
        if not self.available():
            self.log('De gekozen AI is niet geïnstalleerd; paneel niet geopend.')
            return False
        if not self.open():
            return False
        text = question.replace('\n', ' ')

        def type_it():
            if self.term:
                data = text.encode()
                try:
                    self.term.feed_child(data)
                except TypeError:  # older bindings want a list of ints
                    self.term.feed_child(list(data))
            return False
        GLib.timeout_add(5000 if fresh else 300, type_it)
        return True

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
        win.set_title('Universe AI')
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
        naam, regel = 'AI', 'Kies een assistent in Controlecentrum → AI'
        try:
            naam, regel = _ai().panel_title()
        except Exception:
            pass
        title = Gtk.Label(label=naam, xalign=0)
        title.get_style_context().add_class('claude-title')
        sub = Gtk.Label(label=regel, xalign=0)
        sub.get_style_context().add_class('claude-sub')
        self.title_label = title
        self.sub_label = sub
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
        bg = Gdk.RGBA(0.03, 0.05, 0.12, 1.0)  # opaque: VTE replaces (not blends) its background, planets shone through
        fg = Gdk.RGBA(0.91, 1.0, 0.98, 1.0)
        palette = [Gdk.RGBA() for _ in range(16)]
        for rgba, spec in zip(palette, ('#0b1022', '#ff6b6b', '#5ef0c4', '#ffb357', '#6aa8ff', '#c792ea', '#85ffe3', '#d8e6f0',
                                        '#3a4566', '#ff8b8b', '#85ffe3', '#ffc97a', '#8ec0ff', '#dcb2ff', '#b0fff0', '#ffffff')):
            rgba.parse(spec)
        term.set_colors(fg, bg, palette)
        term.set_cursor_blink_mode(Vte.CursorBlinkMode.OFF)  # every blink is a screen update (costly without a GPU)
        term.set_scrollback_lines(5000)
        term.set_font(Pango.FontDescription('Monospace 11'))
        term.connect('child-exited', self.child_exited)
        # Links (like the sign-in link of Claude Code) open with a click; Ctrl+Shift+C/V copy and paste (the sign-in
        # code has to be pasted back). VTE does neither by itself.
        term.set_allow_hyperlink(True)
        try:
            regex = Vte.Regex.new_for_match(r'https?://[^\s<>"\']+', -1, 0x00000400)  # PCRE2_MULTILINE
            term.match_set_cursor_name(term.match_add_regex(regex, 0), 'pointer')
        except Exception as error:  # noqa: BLE001 - only clickable links are lost
            self.log('Links in het Claude-paneel niet klikbaar: %s' % error)
        term.connect('button-press-event', self.terminal_click)
        term.connect('key-press-event', self.terminal_key)
        argv = ['/usr/bin/universe-ai'] + (['--nieuw'] if fresh else [])
        term.spawn_async(Vte.PtyFlags.DEFAULT, os.path.expanduser('~'), argv, None, GLib.SpawnFlags.DEFAULT,
                         None, None, -1, None, None, None)
        self.holder.pack_start(term, True, True, 0)
        term.show()
        self.term = term

    def open(self):
        if not self.available():
            self.log('De gekozen AI is niet geïnstalleerd; paneel niet geopend.')
            return False
        if getattr(self, 'title_label', None):
            try:
                naam, regel = _ai().panel_title()
                self.title_label.set_text(naam)
                self.sub_label.set_text(regel)
            except Exception:
                pass
        if self.alive_timer:
            GLib.source_remove(self.alive_timer)
            self.alive_timer = 0
        self.slide_id = getattr(self, 'slide_id', 0) + 1  # stop a closing fade that is still running
        if self.panel is not None:
            self.panel.set_opacity(1.0)
        if self.panel is not None and not self.panel.get_visible():
            # A layer surface that was hidden stayed invisible when shown again (labwc, 11 Oct): build a new window
            # and move the running terminal into it, so the conversation with Claude Code continues.
            if self.term:
                self.holder.remove(self.term)
            self.panel.destroy()
            self.panel = None
        if self.panel is None:
            self.build_panel()
            if self.term:
                self.holder.pack_start(self.term, True, True, 0)
        if self.term is None:
            self.start_terminal()
        E, K = GtkLayerShell.Edge, GtkLayerShell.KeyboardMode
        GtkLayerShell.set_keyboard_mode(self.panel, K.EXCLUSIVE)
        if not self.panel.get_visible():
            self.panel.show_all()
            if self.animations() == 'full':
                self.fade(0.0, 1.0)
        self.panel.present()
        self.term.grab_focus()
        # The keyboard stays with the panel while it is open (like the start menu). Switching to on-demand after a
        # moment lost the keyboard in labwc: typing in the terminal did not work (Axel, 11 Oct).
        if self.buddy:
            self.buddy.event('panel', {})
        return True

    def fade(self, start, end, done=None):
        """Fade the panel in or out (0.18 s). Not a slide from outside the screen: a layer surface that had a negative
        margin stayed invisible when it was shown again (labwc, 11 Oct)."""
        t0 = time.monotonic()
        self.slide_id = getattr(self, 'slide_id', 0) + 1  # a newer slide (open while closing) cancels this one
        mine = self.slide_id

        def step():
            if not self.panel or mine != self.slide_id:
                return False
            t = min(1.0, (time.monotonic() - t0) / 0.18)
            self.panel.set_opacity(start + (end - start) * ease(t))
            if t >= 1.0:
                if done:
                    done()
                return False
            return True
        self.panel.set_opacity(start)
        GLib.timeout_add(16, step)

    def close(self):
        if not (self.panel and self.panel.get_visible()):
            return False
        if self.animations() == 'full':
            self.fade(1.0, 0.0, self.panel.hide)
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

    def terminal_click(self, term, event):
        if event.button != 1 or event.type != Gdk.EventType.BUTTON_PRESS:
            return False
        uri = term.hyperlink_check_event(event)
        if not uri:
            match = term.match_check_event(event)
            uri = match[0] if match else None
        if uri and uri.startswith(('http://', 'https://')):
            try:
                Gio.AppInfo.launch_default_for_uri(uri, None)
            except GLib.Error as error:
                self.log('Link openen mislukt: %s' % error.message)
            return True
        return False

    def terminal_key(self, term, event):
        mods = event.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)
        if mods == (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
            from gi.repository import Vte
            key = Gdk.keyval_to_lower(event.keyval)
            if key == Gdk.KEY_c:
                term.copy_clipboard_format(Vte.Format.TEXT)
                return True
            if key == Gdk.KEY_v:
                term.paste_clipboard()
                return True
        return False

    def child_exited(self, term, status):
        if term is self.term:
            self.term = None
            GLib.idle_add(lambda: term.destroy() or False)
            self.close()


class Buddy:
    """The placeholder character: a floating blob of slime with eyes that deforms as it moves. States: idle, listen, think, work,
    attention, happy. Walks between home (above the dock, right), the dock, the middle of the world and the panel."""

    def __init__(self, ui):
        self.ui = ui
        L, E, K = GtkLayerShell.Layer, GtkLayerShell.Edge, GtkLayerShell.KeyboardMode
        win = Gtk.Window()
        win.set_title('Universe AI')
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
        area.set_halign(Gtk.Align.END)
        area.set_tooltip_text('AI (Windows+C)')
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.bubble = Gtk.EventBox()
        self.bubble.set_app_paintable(True)
        self.bubble.connect('draw', self.draw_bubble)
        self.bubble.set_no_show_all(True)
        box.pack_start(self.bubble, False, False, 0)
        box.pack_start(area, False, False, 0)
        win.add(box)
        self.window, self.area = win, area
        self.hint_timer = 0
        self.state = 'idle'
        self.state_since = time.monotonic()
        self.pos = self.place('home')
        self.target = self.pos
        self.move_from = self.pos
        self.move_t0 = 0
        self.facing = -1
        self.last_pos = self.pos
        self.deform, self.deform_v = [0.0, 0.0], [0.0, 0.0]  # slime stretch (screen x, y) and its speed
        self.busy = False  # a program is in front: stand still
        self.wiggle_until = 0.0
        self.clock = 0.0  # animation time: only runs while frames are drawn, so a still slime does not jump
        self.clock_at = time.monotonic()
        self.breath_until = 0.0
        self.blink = 0.0
        self.anim = 0
        self.slow_frames = 0
        self.last_frame = 0
        self.apply_pos()
        win.show_all()
        self.blink_timer = GLib.timeout_add_seconds(6, self.schedule_blink)  # every frame costs the compositor
        # Arrive: a short hop out of the corner.
        self.set_state('happy')

    def destroy(self):
        for t in (self.anim, self.blink_timer, self.hint_timer):
            if t:
                GLib.source_remove(t)
        self.anim = self.blink_timer = self.hint_timer = 0
        self.window.destroy()

    # ----- speech bubble with quick actions (buddy_hints) -----
    def show_hint(self, text, actions, on_answer=None):
        """text + buttons [(label, fn)]; 'Niet nu' and 'Nooit' are always added. Hides itself after 25 s."""
        self.hide_hint()
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.get_style_context().add_class('buddy-hint')
        label = Gtk.Label(label=text, xalign=0)
        label.set_line_wrap(True)
        label.set_max_width_chars(34)
        label.get_style_context().add_class('buddy-text')
        inner.pack_start(label, False, False, 0)
        row = Gtk.FlowBox()
        row.set_selection_mode(Gtk.SelectionMode.NONE)
        row.set_max_children_per_line(4)
        row.set_column_spacing(6)
        row.set_row_spacing(6)

        def pressed(fn, answer):
            self.hide_hint()
            if on_answer:
                on_answer(answer)
            if fn:
                try:
                    fn()
                except Exception as error:  # shown as a notification instead of a silent failure
                    self.ui.log('Suggestie mislukt: %s' % error)
                    try:
                        import backend
                        backend.spawn(['notify-send', '-a', 'AI', 'Dat lukte niet', str(error)[:200]])
                    except Exception:  # noqa: BLE001
                        pass
                self.set_state('happy')
        for i, (title, fn) in enumerate(list(actions) + [('Niet nu', None), ('Nooit', None)]):
            button = Gtk.Button(label=title)
            button.set_can_focus(False)
            ctx = button.get_style_context()
            ctx.add_class('claude-btn')
            if i == 0:
                ctx.add_class('buddy-main')
            answer = 'ja' if fn else ('nooit' if title == 'Nooit' else 'niet-nu')
            button.connect('clicked', lambda b, f=fn, a=answer: pressed(f, a))
            row.add(button)
        inner.pack_start(row, False, False, 0)
        self.bubble.add(inner)
        self.window.set_size_request(BUBBLE_WIDTH, -1)
        inner.show_all()  # the bubble itself has no_show_all, so show_all() on it would do nothing
        self.bubble.show()
        self.set_state('attention' if self.state == 'idle' else self.state)
        self.hint_timer = GLib.timeout_add_seconds(25, self.expire_hint, on_answer)

    def expire_hint(self, on_answer):
        self.hint_timer = 0
        self.hide_hint()
        return False

    def hide_hint(self):
        if self.hint_timer:
            GLib.source_remove(self.hint_timer)
            self.hint_timer = 0
        child = self.bubble.get_child()
        if child:
            child.destroy()
        self.bubble.hide()
        self.window.set_size_request(*BUDDY)
        self.window.resize(*BUDDY)
        if self.state == 'attention':
            self.set_state('idle')

    def draw_bubble(self, widget, cr):
        w, h, r = widget.get_allocated_width(), widget.get_allocated_height() - 12, 16
        cr.new_sub_path()
        cr.arc(w - r - 1, r + 1, r, -math.pi / 2, 0)
        cr.arc(w - r - 1, h - r, r, 0, math.pi / 2)
        cr.line_to(w - 50, h)
        cr.line_to(w - 62, h + 11)  # the tail points at the buddy
        cr.line_to(w - 72, h)
        cr.arc(r + 1, h - r, r, math.pi / 2, math.pi)
        cr.arc(r + 1, r + 1, r, math.pi, 1.5 * math.pi)
        cr.close_path()
        cr.set_source_rgba(0.035, 0.06, 0.15, 0.96)
        cr.fill_preserve()
        cr.set_line_width(1.2)
        cr.set_source_rgba(*ORANGE, 0.6)
        cr.stroke()
        return False

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
        if not busy:
            self.breathe()

    def set_state(self, state):
        self.state = state
        self.state_since = time.monotonic()
        if self.anim and state != 'idle':  # a slow rest loop (blink, breath) becomes the full 30 fps loop
            GLib.source_remove(self.anim)
            self.anim = 0
        self.run()

    # ----- animation loop: only runs while something moves -----
    def moving(self):
        return self.pos != self.target

    def animated_state(self):
        if self.state == 'happy' and time.monotonic() - self.state_since > 1.6:
            self.state = 'idle'
        t = time.monotonic() - self.state_since
        if self.state == 'listen':
            return t < 2.5  # then it holds still while you type (the panel can stay open for a long time)
        if self.state == 'attention':
            return t < 6
        return self.state != 'idle' or time.monotonic() < self.wiggle_until

    def run(self):
        if self.ui.animations() == 'off':
            self.area.queue_draw()
            return
        if not self.anim:
            self.slow_frames = 0
            self.last_frame = time.monotonic()
            # 30 fps for walking and the states; a blink or wiggle at rest is fine at 15 fps (half the frames to draw)
            self.anim = GLib.timeout_add(66 if self.state == "idle" and not self.moving() else 33, self.tick)
        self.area.queue_draw()

    def tick(self):
        now = time.monotonic()
        dt = now - self.last_frame
        # Slow computer: two frames much later than planned -> stop animating, jump to the end (like the login).
        self.slow_frames = self.slow_frames + 1 if dt > 0.25 else 0
        self.last_frame = now
        if self.slow_frames >= 2:
            self.pos = self.target
            self.last_pos = self.pos
            self.deform, self.deform_v = [0.0, 0.0], [0.0, 0.0]
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
        self.jiggle(dt)
        self.advance()
        self.area.queue_draw()
        if self.moving() or self.animated_state() or self.blink > 0 or self.jiggling():
            if self.blink > 0:
                self.blink = max(0.0, self.blink - 0.2)
            return True
        self.anim = 0
        self.breathe()
        return False

    def breathe(self):
        """After it came to rest a few seconds of slow breathing, then the slime stands still. Every frame of a layer
        surface costs the compositor (without a GPU: labwc + kernel ~50 % CPU in the VM at 10 fps), so at rest only a
        blink or a short wiggle now and then (schedule_blink)."""
        if self.anim or self.busy or self.ui.animations() != 'full':
            return
        self.breath_until = time.monotonic() + 4
        self.anim = GLib.timeout_add(100, self.breath_tick)

    def advance(self):
        now = time.monotonic()
        self.clock += min(now - self.clock_at, 0.1)
        self.clock_at = now

    def breath_tick(self):
        self.advance()
        if time.monotonic() > self.breath_until and self.state == 'idle' and not self.moving() and self.blink <= 0:
            self.anim = 0
            self.area.queue_draw()
            return False
        if self.state != 'idle' or self.moving() or self.busy or self.blink > 0:
            self.anim = 0
            if not self.busy or self.state != 'idle':
                self.run()  # back to the fast loop (a blink, a jump, a walk)
            return False
        self.area.queue_draw()
        return True

    def schedule_blink(self):
        if not self.busy and self.ui.animations() != 'off':
            r = random.random()
            if r < 0.15 and self.ui.animations() == "full":
                self.wiggle_until = time.monotonic() + 1.2  # a short jelly wiggle
                self.run()
            elif r < 0.85:
                self.blink = 1.0
                self.run()
        return True

    def clicked(self, widget, event):
        self.ui.toggle()
        return True

    # ----- drawing -----
    # ----- the slime: physics -----
    def jiggle(self, dt):
        """Spring-damped deformation that follows the speed of the buddy: it stretches along the movement, the back
        lags behind, and when it stops the jelly overshoots and wobbles out (follow-through)."""
        dx = -(self.pos[0] - self.last_pos[0])  # right margin grows = moves left on screen
        dy = -(self.pos[1] - self.last_pos[1])  # bottom margin grows = moves up
        self.last_pos = self.pos
        dt = max(0.016, min(dt, 0.1))
        target = (max(-1.0, min(1.0, dx / dt / 900)), max(-1.0, min(1.0, dy / dt / 900)))
        for i in (0, 1):
            acc = (target[i] - self.deform[i]) * 90 - self.deform_v[i] * 9
            self.deform_v[i] += acc * dt
            self.deform[i] += self.deform_v[i] * dt

    def jiggling(self):
        return abs(self.deform[0]) + abs(self.deform[1]) + abs(self.deform_v[0]) + abs(self.deform_v[1]) > 0.02

    def pose(self, t, state):
        """(float height, squash x, squash y, wobble) per state. It always floats; it never touches the ground."""
        now = self.clock
        lift = 6 * math.sin(now * 1.8)  # hovering
        sx = sy = 1.0
        wobble = 0.035
        if state == 'happy':
            if t < 0.18:  # anticipation: sinks and flattens
                k = math.sin(t / 0.18 * math.pi / 2)
                lift -= 8 * k
                sx, sy = 1 + 0.2 * k, 1 - 0.22 * k
            elif t < 1.6:
                u = t - 0.18
                n, phase = int(u / 0.45), (u % 0.45) / 0.45
                height = 26 * (0.5 ** n)
                lift += height * math.sin(phase * math.pi)
                v = abs(math.cos(phase * math.pi)) * height / 26
                sx, sy = 1 - 0.12 * v, 1 + 0.2 * v
                if phase > 0.85 or phase < 0.1:  # at the low point: splat
                    f = max(0.0, 1 - min(phase, 1 - phase) / 0.15)
                    sx, sy = 1 + 0.18 * f * height / 26, 1 - 0.18 * f * height / 26
            wobble = 0.07
        elif state == 'attention':
            lift += abs(math.sin(t * 7)) * 8
            sx, sy = 1 - 0.05 * math.sin(t * 14), 1 + 0.05 * math.sin(t * 14)
            wobble = 0.06
        elif state == 'listen':
            sy = 1.04 + 0.02 * math.sin(t * 3)
        elif state in ('think', 'work'):
            wobble = 0.06 if state == 'work' else 0.045
        else:  # idle: breathing slime (it stands still between the short breaths and wiggles)
            b = math.sin(now * 2.1)
            sx, sy = 1 + 0.02 * b, 1 - 0.025 * b
            left = self.wiggle_until - time.monotonic()
            if left > 0:
                k = math.sin(left / 1.2 * math.pi)
                wobble = 0.035 + 0.06 * k
                sx, sy = sx + 0.05 * k * math.sin(now * 16), sy - 0.05 * k * math.sin(now * 16)
        return lift, sx, sy, wobble

    # ----- the slime: drawing -----
    def blob_points(self, cx, cy, r, sx, sy, wobble, now):
        """Outline of the slime: a circle whose radius wobbles like jelly, squashed per state and stretched along the
        deformation (the leading side round, the trailing side pulled out like a drop)."""
        ddx, ddy = self.deform
        mag = min(0.55, math.hypot(ddx, ddy))
        ang = math.atan2(-ddy, ddx)  # screen y grows downwards
        points = []
        n = 18
        for i in range(n):
            a = 2 * math.pi * i / n
            k = 1 + wobble * math.sin(3 * a + now * 2.3) + wobble * 0.7 * math.sin(5 * a - now * 3.1) \
                + wobble * 0.4 * math.sin(2 * a + now * 1.3)
            along = math.cos(a - ang)
            k *= 1 + mag * (0.35 * along * along - 0.15)  # longer along the movement, thinner across
            if along < 0:
                k *= 1 + mag * 0.45 * -along  # the back trails behind
            x = math.cos(a) * r * k * sx
            y = math.sin(a) * r * k * sy
            if y > 0:
                y *= 1 + 0.12 * (1 - abs(math.cos(a)))  # heavier at the bottom, like a drop of slime
            points.append((cx + x, cy + y))
        return points

    def smooth_path(self, cr, pts):
        """Closed Catmull-Rom curve through the points (soft, no corners)."""
        n = len(pts)
        cr.move_to(*pts[0])
        for i in range(n):
            p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
            cr.curve_to(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                        p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1])
        cr.close_path()

    def draw(self, widget, cr):
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        w, h = BUDDY
        now = self.clock  # wobble, hover and bubbles follow the animation clock
        t = time.monotonic() - self.state_since
        state = self.state
        lift, sx, sy, wobble = self.pose(t, state)
        r = 32
        cx = w / 2 - self.deform[0] * 6
        cy = h - 62 - lift + self.deform[1] * 6

        # soft shadow far below: it floats
        cr.save()
        cr.translate(w / 2, h - 10)
        cr.scale(1, 0.25)
        cr.arc(0, 0, r * max(0.4, 0.8 - lift / 160), 0, 2 * math.pi)
        cr.restore()
        cr.set_source_rgba(0, 0, 0, max(0.08, 0.28 - lift / 140))
        cr.fill()

        # glow while listening / working / asking
        if state in ('listen', 'work', 'attention'):
            pulse = 0.5 + 0.5 * math.sin(t * (8 if state == 'work' else 4))
            color = ORANGE if state == 'attention' else TEAL
            g = cairo.RadialGradient(cx, cy, r * 0.6, cx, cy, r + 16)
            g.add_color_stop_rgba(0, *color, 0.25 + 0.15 * pulse)
            g.add_color_stop_rgba(1, *color, 0)
            cr.arc(cx, cy, r + 16, 0, 2 * math.pi)
            cr.set_source(g)
            cr.fill()

        # body: translucent glossy slime
        self.smooth_path(cr, self.blob_points(cx, cy, r, sx, sy, wobble, now))
        g = cairo.RadialGradient(cx - r * 0.3, cy - r * 0.45, r * 0.15, cx, cy + r * 0.2, r * 1.3)
        g.add_color_stop_rgba(0, 0.80, 1.0, 0.94, 0.95)
        g.add_color_stop_rgba(0.45, 0.30, 0.88, 0.76, 0.88)
        g.add_color_stop_rgba(1, 0.05, 0.42, 0.42, 0.92)
        cr.set_source(g)
        cr.fill_preserve()
        cr.set_line_width(1.5)
        cr.set_source_rgba(0.7, 1.0, 0.92, 0.5)
        cr.stroke()
        # two little air bubbles rising inside the slime
        for bx, by, br, speed in ((-0.35, 0.35, 4.0, 0.7), (0.4, 0.15, 2.6, 1.1)):
            yy = cy + r * by - ((now * speed * 9) % (r * 0.9))
            cr.arc(cx + r * bx * sx, yy, br, 0, 2 * math.pi)
            cr.set_source_rgba(1, 1, 1, 0.25)
            cr.fill()
        # gloss highlight
        cr.save()
        cr.translate(cx - r * 0.38 * sx, cy - r * 0.5 * sy)
        cr.rotate(-0.5)
        cr.scale(1, 0.55)
        cr.arc(0, 0, r * 0.28, 0, 2 * math.pi)
        cr.restore()
        cr.set_source_rgba(1, 1, 1, 0.55)
        cr.fill()

        # eyes: they look where it goes and deform with the body
        look_x = max(-5.0, min(5.0, self.deform[0] * 14))
        look_y = max(-4.0, min(4.0, -self.deform[1] * 10))
        eye_y = cy - 4 * sy
        open_ = 1.0 - self.blink if self.blink > 0 else 1.0
        size = {'listen': 9, 'attention': 9.5, 'work': 6.5}.get(state, 8)
        for side in (-1, 1):
            ex = cx + side * 12 * sx + look_x * 0.5
            if state == 'happy':
                cr.set_line_width(3)
                cr.set_source_rgb(0.03, 0.12, 0.14)
                cr.arc(ex, eye_y + 3, 6, math.pi * 1.1, math.pi * 1.9)
                cr.stroke()
                continue
            cr.save()
            cr.translate(ex, eye_y)
            cr.scale(sx, max(0.1, open_) * sy * (1.12 if state == 'attention' else 1))
            cr.arc(0, 0, size, 0, 2 * math.pi)
            cr.restore()
            cr.set_source_rgb(1, 1, 1)
            cr.fill()
            if open_ > 0.3:
                px = ex + (2 if state == 'think' else look_x * 0.6)
                py = eye_y + (-3.5 if state == 'think' else look_y * 0.6)
                cr.arc(px, py, size * 0.52, 0, 2 * math.pi)
                cr.set_source_rgb(0.03, 0.10, 0.14)
                cr.fill()
                cr.arc(px - size * 0.18, py - size * 0.2, size * 0.16, 0, 2 * math.pi)
                cr.set_source_rgb(1, 1, 1)
                cr.fill()

        # mouth
        cr.set_line_width(2.4)
        cr.set_source_rgb(0.03, 0.12, 0.14)
        my = cy + 11 * sy
        if state in ('happy', 'listen'):
            cr.arc(cx + look_x * 0.4, my - 2, 6, 0.15 * math.pi, 0.85 * math.pi)
            cr.stroke()
        elif state == 'attention':
            cr.arc(cx, my + 1, 3.5, 0, 2 * math.pi)
            cr.fill()
        elif state == 'work':
            cr.move_to(cx - 4, my + 1)
            cr.curve_to(cx - 1, my - 2, cx + 1, my + 4, cx + 4, my + 1)
            cr.stroke()
        else:
            cr.arc(cx + look_x * 0.4, my - 3, 4, 0.25 * math.pi, 0.75 * math.pi)
            cr.stroke()

        # thinking: three little slime drops circling above the head
        if state in ('think', 'work'):
            for i in range(3):
                a = t * 3 + i * 2 * math.pi / 3
                cr.arc(cx + math.cos(a) * 18, cy - r - 14 + math.sin(a) * 5, 3.5, 0, 2 * math.pi)
                cr.set_source_rgba(*TEAL, 0.5 + 0.5 * (math.sin(a) + 1) / 2)
                cr.fill()
        # attention: an orange exclamation mark
        if state == 'attention':
            cr.set_source_rgb(*ORANGE)
            cr.rectangle(cx + r - 2, cy - r - 22, 6, 16)
            cr.fill()
            cr.arc(cx + r + 1, cy - r - 1, 3.5, 0, 2 * math.pi)
            cr.fill()
        # happy: little slime drops fly off
        if state == 'happy' and 0.18 < t < 1.6:
            k = (t - 0.18) / 1.42
            for i in range(6):
                a = i * 2 * math.pi / 6 + 0.3
                d = r + 6 + k * 30
                cr.arc(cx + math.cos(a) * d, cy + math.sin(a) * d * 0.8 + k * k * 20, 3 * (1 - k), 0, 2 * math.pi)
                cr.set_source_rgba(0.45, 0.95, 0.82, 1 - k)
                cr.fill()
        return False
