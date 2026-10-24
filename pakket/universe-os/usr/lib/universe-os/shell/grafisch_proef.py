"""Checks whether WebKit's normal drawing actually reaches the screen of this pc (grafisch.py runs it once per pc).

16 Oct: on Axel's H310M pc (NVIDIA card, nouveau) the login screen and the desktop stayed dark with only a text cursor:
the pages ran and took clicks and typing, but WebKit's picture (DMA-BUF) never reached the screen. On his pc at home the
same normal drawing works well, and the safe mode made that pc slow. No driver list tells the two apart, so this test
looks: it shows a page with two known colours (the page itself and a composited canvas) in normal drawing mode, takes a
picture of the screen (X11 for the login screen, grim on Wayland) and looks for both colours.

Prints one word and exits with: 'normal' (0) both colours seen, 'safe' (1) not seen in time, 'onbekend' (2) the screen
could not be read or no window could be shown. Never touches the WebKit variables of grafisch.SAFE_VARS: the caller
removes them, so this tests normal drawing."""
import subprocess
import sys

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, WebKit2  # noqa: E402

# 0.2.29: neutral dark near the world background #050815 (24 Oct: the blue/purple test page was seen after login)
LEFT = (0x05, 0x08, 0x15)   # page background
RIGHT = (0x15, 0x18, 0x28)  # canvas on its own composited layer (a little lighter)
TOLERANCE = 6               # per channel: dithering and colour depth
SHARE = 0.01                # each colour must cover at least 1 % of the screen picture
WAIT_MS = 6000              # after the page has loaded
POLL_MS = 300

PAGE = '''<!doctype html><html><head><meta charset="utf-8"><style>
html, body { margin: 0; height: 100%%; background: rgb(%d,%d,%d); overflow: hidden; cursor: none; }
canvas { position: fixed; top: 0; right: 0; width: 50%%; height: 100%%; will-change: transform; transform: translateZ(0); }
</style></head><body><div style="position:fixed;left:0;right:0;bottom:12%%;text-align:center;font:24px sans-serif;color:#8a90a8">Beeld wordt getest…</div><canvas id="c" width="64" height="64"></canvas><script>
const c = document.getElementById('c').getContext('2d');
c.fillStyle = 'rgb(%d,%d,%d)'; c.fillRect(0, 0, 64, 64);
</script></body></html>''' % (LEFT + RIGHT)


def matches(pixel, colour):
    return all(abs(a - b) <= TOLERANCE for a, b in zip(pixel, colour))


def verdict(pixels):
    """True when both test colours cover enough of the picture (pixels: (r, g, b) tuples)."""
    total = left = right = 0
    for p in pixels:
        total += 1
        if matches(p, LEFT):
            left += 1
        elif matches(p, RIGHT):
            right += 1
    return total > 0 and left >= total * SHARE and right >= total * SHARE


def ppm_pixels(data):
    """Pixels of a binary PPM (P6, 8 bit) as made by grim -t ppm."""
    fields, pos = [], 0
    while len(fields) < 4:
        while data[pos:pos + 1].isspace():
            pos += 1
        if data[pos:pos + 1] == b'#':
            pos = data.index(b'\n', pos) + 1
            continue
        end = pos
        while not data[end:end + 1].isspace():
            end += 1
        fields.append(data[pos:end])
        pos = end
    if fields[0] != b'P6' or int(fields[3]) != 255:
        raise ValueError('geen 8-bit P6')
    width, height = int(fields[1]), int(fields[2])
    body = data[pos + 1:pos + 1 + width * height * 3]
    return [tuple(body[i:i + 3]) for i in range(0, len(body) - 2, 3)]


def pixbuf_pixels(pixbuf):
    data, stride, step = pixbuf.get_pixels(), pixbuf.get_rowstride(), pixbuf.get_n_channels()
    return [tuple(data[y * stride + x * step:y * stride + x * step + 3])
            for y in range(pixbuf.get_height()) for x in range(pixbuf.get_width())]


def screen_pixels():
    """A small picture of the whole screen as the user sees it, or None."""
    display = Gdk.Display.get_default()
    if 'X11' in type(display).__name__:  # the login screen (LightDM's X server)
        root = Gdk.get_default_root_window()
        pixbuf = Gdk.pixbuf_get_from_window(root, 0, 0, root.get_width(), root.get_height())
        if pixbuf is None:
            return None
        width = max(1, pixbuf.get_width() // 16)
        height = max(1, pixbuf.get_height() // 16)
        return pixbuf_pixels(pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.NEAREST))
    try:
        data = subprocess.run(['grim', '-s', '0.0625', '-t', 'ppm', '-'], capture_output=True, timeout=3,
                              check=True).stdout
        return ppm_pixels(data)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


class Proef:
    def __init__(self):
        self.result = 'onbekend'
        self.deadline = None
        self.window = Gtk.Window(title='Universe OS')
        self.window.set_decorated(False)
        self.view = WebKit2.WebView()
        self.view.connect('load-changed', self.load_changed)
        self.window.add(self.view)
        self.window.fullscreen()
        self.window.show_all()
        self.view.load_html(PAGE, 'about:blank')
        GLib.timeout_add(WAIT_MS * 3, self.give_up)  # the page never loaded

    def load_changed(self, _view, event):
        if event == WebKit2.LoadEvent.FINISHED and self.deadline is None:
            self.deadline = GLib.get_monotonic_time() + WAIT_MS * 1000
            GLib.timeout_add(POLL_MS, self.look)

    def look(self):
        pixels = screen_pixels()
        if pixels is None:
            return self.finish('onbekend')
        if verdict(pixels):
            return self.finish('normal')
        if GLib.get_monotonic_time() >= self.deadline:
            return self.finish('safe')
        return True

    def give_up(self):
        return self.finish('onbekend')

    def finish(self, result):
        self.result = result
        Gtk.main_quit()
        return False


def main():
    ok = Gtk.init_check(sys.argv)
    if not (ok[0] if isinstance(ok, tuple) else ok):
        print('onbekend')
        return 2
    proef = Proef()
    Gtk.main()
    print(proef.result)
    return {'normal': 0, 'safe': 1}.get(proef.result, 2)


if __name__ == '__main__':
    sys.exit(main())
