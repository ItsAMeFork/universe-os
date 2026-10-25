"""Echte venstergrootte en -inhoud voor de bloem-animatie (0.2.36).

labwc 0.8.3 geeft de positie en grootte van vensters niet door: wlr-foreign-toplevel kent alleen titel en staat, labwc
heeft geen IPC en ext-image-copy-capture voor losse vensters komt pas met labwc 0.9 (wlroots 0.19). Wat wel kan:
labwc ondersteunt wlr-screencopy (grim). Het actieve venster heeft een rand van precies 2 px in #85ffe3 (themerc,
window.active.border.color) met daarbinnen de titelbalk in #162335. Die zoeken we in één schermopname terug: dat
geeft de exacte rechthoek, en hetzelfde stuk van de opname is de echte inhoud voor de bloem.

Werkt voor alle vensters met de Universe-rand, ook X11/Xwayland (Wine/.exe-programma's). Vensters zonder rand
(splash-schermen, launchers, volledig scherm) worden niet gevonden: dan geen animatie, nooit iets geks.
"""
import subprocess

RAND = b'\x85\xff\xe3'
TITEL = b'\x16\x23\x35'
MIN_BREEDTE = 120
MIN_HOOGTE = 60


def opname(timeout=None):
    """Screenshot of the whole layout as binary PPM via grim (wlr-screencopy). (w, h, rgb-bytes) or None."""
    if timeout is None:
        import flits
        timeout = 0.8 * flits.traag()  # the slow test mode (VM) waits longer as well
    try:
        out = subprocess.run(['grim', '-t', 'ppm', '-'], capture_output=True, timeout=timeout, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return lees_ppm(out)


def lees_ppm(data):
    try:
        parts, pos = [], 0
        while len(parts) < 4:
            while data[pos:pos + 1].isspace():
                pos += 1
            if data[pos:pos + 1] == b'#':
                pos = data.index(b'\n', pos) + 1
                continue
            end = pos
            while not data[end:end + 1].isspace():
                end += 1
            parts.append(data[pos:end])
            pos = end
        pos += 1
        if parts[0] != b'P6' or int(parts[3]) != 255:
            return None
        w, h = int(parts[1]), int(parts[2])
        pixels = data[pos:pos + w * h * 3]
        return (w, h, pixels) if len(pixels) == w * h * 3 else None
    except (ValueError, IndexError):
        return None


def _px(data, w, x, y):
    i = (y * w + x) * 3
    return data[i:i + 3]


def vind_actief(w, h, data, stap=2):
    """Rectangle (x, y, w, h) of the active window: a horizontal run of the mint border of at least MIN_BREEDTE px,
    with the title bar colour right below it and a mint border running down on the left. None when not found."""
    rij = w * 3
    patroon = RAND * 48
    for y in range(0, h - MIN_HOOGTE, stap):
        start = y * rij
        regel = data[start:start + rij]
        i = regel.find(patroon)
        while i != -1:
            if i % 3 == 0:
                x0 = i // 3
                x1 = x0
                while x1 + 1 < w and regel[(x1 + 1) * 3:(x1 + 2) * 3] == RAND:
                    x1 += 1
                gevonden = _controleer(w, h, data, x0, x1, y)
                if gevonden:
                    return gevonden
                i = regel.find(patroon, (x1 + 1) * 3)
            else:
                i = regel.find(patroon, i + 1)
    return None


def _controleer(w, h, data, x0, x1, y):
    if x1 - x0 + 1 < MIN_BREEDTE:
        return None
    # the true top border row (we may have hit it at the second of its 2 px rows)
    while y > 0 and _px(data, w, (x0 + x1) // 2, y - 1) == RAND:
        y -= 1
    # title bar colour just below the border (a few rows, somewhere in the middle third)
    midden = (x0 + x1) // 2
    if not any(_px(data, w, mx, y + dy) == TITEL for dy in range(2, 8) for mx in (midden - (x1 - x0) // 6, midden)):
        return None
    # left border: rounded corners (radius 10) make the top run shorter; find the mint column left of x0
    links = None
    for lx in range(x0, max(-1, x0 - 14), -1):
        if _px(data, w, lx, min(h - 1, y + 16)) == RAND:
            links = lx
    if links is None:
        return None
    while links > 0 and _px(data, w, links - 1, min(h - 1, y + 16)) == RAND:
        links -= 1
    rij = min(h - 1, y + 16)
    rechts = x1
    for rx in range(x1, min(w, x1 + 15)):
        if _px(data, w, rx, rij) == RAND:
            rechts = rx
    onder = rij
    while onder + 1 < h and _px(data, w, links, onder + 1) == RAND:
        onder += 1
    hoogte = onder - y + 1  # labwc rounds only the top corners (title bar); the border runs straight to the bottom
    if hoogte < MIN_HOOGTE or onder - y < 30:
        return None
    return (links, y, min(w, rechts + 1) - links, min(h - y, hoogte))


def inhoud(w, h, data, rect, max_breedte=720):
    """The window content (GdkPixbuf) of rect, scaled down to at most max_breedte for cheap drawing."""
    from gi.repository import GdkPixbuf, GLib
    pix = GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(data), GdkPixbuf.Colorspace.RGB, False, 8, w, h, w * 3)
    x, y, rw, rh = (int(v) for v in rect)
    sub = pix.new_subpixbuf(x, y, max(1, min(rw, w - x)), max(1, min(rh, h - y)))
    if sub.get_width() > max_breedte:
        k = max_breedte / sub.get_width()
        return sub.scale_simple(max_breedte, max(1, int(sub.get_height() * k)), GdkPixbuf.InterpType.BILINEAR)
    return sub.copy()
