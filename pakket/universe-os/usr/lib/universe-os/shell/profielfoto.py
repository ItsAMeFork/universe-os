"""0.3.4 (Axel, 28 Oct): your own profile photo on your planet in the login screen.

Any photo GdkPixbuf can read (JPG, PNG, GIF, BMP, TIFF; WebP and HEIC/HEIF/AVIF through their pixbuf loaders) becomes a
square 512x512 PNG, cut out where the user placed it in the editor (Controlecentrum > Gebruikers). It is stored by
AccountsService (/var/lib/AccountsService/icons/<name>), the standard place LightDM reads user pictures from, so the
greeter can show it without reading anyone's home. Setting your own picture needs no administrator (polkit
change-own-user-data); AccountsService refuses another user's picture.
"""
import base64
import os
import tempfile

MAAT = 512                  # side of the stored picture
VOORBEELD = 1024            # longest side of the picture the editor works on (big photos stay fast)
MAX_BYTES = 2 * 1024 * 1024  # never send more than this to a page
FOUT = 'Dit bestand is geen foto die Universe OS kan lezen.'
SOORTEN = ((b'\x89PNG\r\n\x1a\n', 'image/png'), (b'\xff\xd8\xff', 'image/jpeg'), (b'GIF8', 'image/gif'))


def vierkant(x, y, maat, breedte, hoogte):
    """The crop square in pixels of the photo, kept inside it: at least 16 px, at most the short side."""
    maat = min(max(16, int(round(maat))), breedte, hoogte)
    x = max(0, min(int(round(x)), breedte - maat))
    y = max(0, min(int(round(y)), hoogte - maat))
    return x, y, maat


def data_url_bestand(pad):
    """A small picture file as data URL for a page (PNG, JPEG, GIF or WebP only), otherwise None. Never raises."""
    try:
        if not pad or os.path.getsize(pad) > MAX_BYTES:
            return None
        with open(pad, 'rb') as f:
            data = f.read(MAX_BYTES + 1)
    except OSError:
        return None
    soort = next((s for kop, s in SOORTEN if data.startswith(kop)), None)
    if not soort and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        soort = 'image/webp'
    return 'data:%s;base64,%s' % (soort, base64.b64encode(data).decode()) if soort else None


def _laad(pad):
    import gi
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import GdkPixbuf, GLib
    try:
        pb = GdkPixbuf.Pixbuf.new_from_file(pad)
    except GLib.Error:
        raise ValueError(FOUT) from None
    return pb.apply_embedded_orientation() or pb  # photos from a phone: upright, as the user sees them


def _bytes(pb, soort):
    ok, buf = pb.save_to_bufferv(soort, ['quality'] if soort == 'jpeg' else [], ['90'] if soort == 'jpeg' else [])
    if not ok:
        raise ValueError(FOUT)
    return bytes(buf)


def voorbeeld(pad):
    """The photo for the editor (at most VOORBEELD px) and the real size of the original."""
    from gi.repository import GdkPixbuf
    pb = _laad(pad)
    w, h = pb.get_width(), pb.get_height()
    k = min(1.0, VOORBEELD / max(w, h))
    klein = pb.scale_simple(max(1, round(w * k)), max(1, round(h * k)), GdkPixbuf.InterpType.BILINEAR) if k < 1 else pb
    soort = 'png' if klein.get_has_alpha() else 'jpeg'
    data = _bytes(klein, soort)
    return {'beeld': 'data:image/%s;base64,%s' % (soort, base64.b64encode(data).decode()), 'breedte': w, 'hoogte': h}


def maak(pad, x, y, maat):
    """The stored picture: the square (x, y, maat) of the original, as a MAAT x MAAT PNG."""
    from gi.repository import GdkPixbuf
    pb = _laad(pad)
    x, y, maat = vierkant(x, y, maat, pb.get_width(), pb.get_height())
    stuk = pb.new_subpixbuf(x, y, maat, maat).scale_simple(MAAT, MAAT, GdkPixbuf.InterpType.HYPER)
    return _bytes(stuk, 'png')


def _zet_icoon(pad):
    import pwd
    from gi.repository import Gio, GLib
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    naam = pwd.getpwuid(os.getuid()).pw_name
    try:
        user = bus.call_sync('org.freedesktop.Accounts', '/org/freedesktop/Accounts', 'org.freedesktop.Accounts',
                             'FindUserByName', GLib.Variant('(s)', (naam,)), GLib.VariantType('(o)'),
                             Gio.DBusCallFlags.NONE, 10000, None).unpack()[0]
        bus.call_sync('org.freedesktop.Accounts', user, 'org.freedesktop.Accounts.User', 'SetIconFile',
                      GLib.Variant('(s)', (pad,)), None, Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION, 30000, None)
    except GLib.Error as error:
        raise RuntimeError('De profielfoto kon niet worden opgeslagen (%s).' % (error.message or error)) from None


def opslaan(pad, x, y, maat):
    data = maak(pad, x, y, maat)
    map_ = os.environ.get('XDG_RUNTIME_DIR') or tempfile.gettempdir()
    fd, tijdelijk = tempfile.mkstemp(prefix='profielfoto-', suffix='.png', dir=map_)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        _zet_icoon(tijdelijk)  # AccountsService copies the file into its own folder
    finally:
        os.unlink(tijdelijk)
    return True


def verwijderen():
    _zet_icoon('')  # empty: AccountsService removes the picture; the planet gets its colour back
    return True


def huidige(naam=None):
    """Data URL of the stored picture of `naam` (default: yourself), or None."""
    import pwd
    naam = naam or pwd.getpwuid(os.getuid()).pw_name
    return data_url_bestand(os.path.join('/var/lib/AccountsService/icons', os.path.basename(naam)))
