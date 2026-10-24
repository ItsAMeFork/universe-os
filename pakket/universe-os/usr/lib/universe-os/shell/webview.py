"""A WebKit view that shows a Universe page and connects its JavaScript (api.js) to Python handlers."""
import json
import os
import threading
import traceback

import grafisch  # noqa: E402

# Before Gtk/WebKit load: normal drawing as in 0.2.12, the safe mode only when asked for (see grafisch.py).
WEBKIT_GRAPHICS = grafisch.apply()


def _memory_gb():
    """Memory of this pc in whole GB (MemTotal), 0 when unknown. The pages use it to balance memory against
    processor work: with 4 GB or less they keep fewer and smaller planet pictures (16 Oct)."""
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    return max(1, round(int(line.split()[1]) / 1024 / 1024))
    except (OSError, ValueError, IndexError):
        pass
    return 0


MEMORY_GB = _memory_gb()

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gdk, GLib, WebKit2  # noqa: E402

UI_DIR = '/usr/share/universe-os/ui'


class Bridge:
    """Handlers: name -> fn(args) returning JSON-able data. Names in `threaded` run off the GTK thread."""

    def __init__(self, handlers, threaded=(), log=print):
        self.handlers = handlers
        self.threaded = set(threaded)
        self.log = log

    def handle(self, view, raw):
        try:
            msg = json.loads(raw)
            mid, cmd, args = msg['id'], msg['cmd'], msg.get('args') or {}
        except (ValueError, KeyError, TypeError):
            return
        fn = self.handlers.get(cmd)
        if not fn:
            return reply(view, mid, False, 'Onbekende opdracht: %s' % cmd)

        def work():
            try:
                result = fn(args)
                ok = True
            except Exception as error:  # every failure becomes a readable message in the interface
                ok, result = False, str(error) or error.__class__.__name__
                if not isinstance(error, (ValueError, RuntimeError, PermissionError)):
                    self.log('Fout in %s: %s' % (cmd, traceback.format_exc()))
            GLib.idle_add(reply, view, mid, ok, result)

        if cmd in self.threaded:
            threading.Thread(target=work, daemon=True).start()
        else:
            work()


def _js(view, code):
    try:
        view.evaluate_javascript(code, -1, None, None, None, None, None)
    except (AttributeError, TypeError):
        view.run_javascript(code, None, None, None)
    return False


# json.dumps(..., ensure_ascii=False) builds a new encoder on every call; one shared encoder gives identical text.
_encode = json.JSONEncoder(ensure_ascii=False).encode


def reply(view, mid, ok, data):
    # Classic load-guard messages are fire-and-forget, even if api.js never loaded.
    if mid < 0:
        return False
    return _js(view, 'window.__universeReply(%d,%s,%s)' % (mid, 'true' if ok else 'false', _encode(data)))


def event_code(name, data=None):
    """The JavaScript for one event; build it once to send the same event to several views."""
    return 'window.__universeEvent&&window.__universeEvent(%s,%s)' % (json.dumps(name), _encode(data))


def emit_code(view, code):
    _js(view, code)


def emit(view, name, data=None):
    _js(view, event_code(name, data))


def make_view(page, bridge, transparent=False, zoom=1.0):
    manager = WebKit2.UserContentManager()
    manager.register_script_message_handler('universe')
    view = WebKit2.WebView.new_with_user_content_manager(manager)

    def received(_manager, result):
        try:
            raw = result.get_js_value().to_string()
        except AttributeError:
            raw = result.to_string()
        bridge.handle(view, raw)

    manager.connect('script-message-received::universe', received)

    # Without these a crashed or failed page is a dark window with no trace; shell.log is the only place to see why.
    def crashed(_view):
        bridge.log('Pagina %s: WebKit-proces is gecrasht' % page)
        return False

    def failed(_view, _event, uri, error):
        bridge.log('Pagina %s niet geladen (%s): %s' % (page, uri, error.message))
        return False

    view.connect('web-process-crashed', crashed)
    view.connect('load-failed', failed)
    settings = view.get_settings()
    settings.set_allow_file_access_from_file_urls(True)
    settings.set_enable_developer_extras(False)
    settings.set_enable_write_console_messages_to_stdout(True)
    settings.set_enable_webgl(True)
    settings.set_javascript_can_access_clipboard(False)
    settings.set_enable_back_forward_navigation_gestures(False)
    settings.set_default_font_family('Noto Sans')
    view.set_zoom_level(zoom)
    if transparent:
        view.set_background_color(Gdk.RGBA(0, 0, 0, 0))
    else:
        # Native clear colour applies before HTML/CSS and WebKit's first frame.
        view.set_background_color(Gdk.RGBA(5 / 255, 8 / 255, 21 / 255, 1))
    # Only our own pages: links to the web open in the browser, never inside the shell.
    view.connect('decide-policy', _policy)
    view.connect('context-menu', lambda *a: True)
    uri = page_uri(page)
    view.load_uri(uri)
    view.connect('web-process-terminated', _restart_page, page, uri)
    return view


def page_uri(page):
    uri = GLib.filename_to_uri('%s/%s' % (UI_DIR, page))
    params = []
    if os.environ.get('UNIVERSE_DEBUG_FPS') == '1':
        params.append('fps=1')
    if os.environ.get('LIBGL_ALWAYS_SOFTWARE') == '1':
        params.append('gfx=soft')
    elif grafisch.light_active():
        params.append('gfx=licht')  # 0.2.31: oude/zwakke videokaart: lichtere wereld (grafisch.py lichte modus)  # the processor draws (grafisch.py safe mode): the pages keep their work light
    if MEMORY_GB:
        params.append('mem=%d' % MEMORY_GB)  # little memory: smaller planet pictures and picture cache (globe.js)
    if params:
        uri += '?' + '&'.join(params)
    return uri


_restarts = {}
# A page that keeps stopping gets its simple version (0.2.28): the world becomes plain icons instead of a dark screen.
FALLBACK = {'world.html': 'world-lite.html'}



def cpu_lacks_jit_features(cpuinfo='/proc/cpuinfo'):
    """23 Oct (VM, TCG 'QEMU Virtual CPU', no SSE4): the JavaScript JIT in the page processes stopped on an invalid
    instruction ('trap invalid opcode' in dmesg) about 10 s after the world loaded, again and again. Without SSE4.2
    the pages run without JIT: slower JavaScript, but they keep running."""
    try:
        with open(cpuinfo) as f:
            for line in f:
                if line.startswith('flags'):
                    return 'sse4_2' not in line.split()
    except OSError:
        pass
    return False


def no_jit(reason):
    if os.environ.get('JSC_useJIT') != '0':
        os.environ['JSC_useJIT'] = '0'  # new page processes inherit it
        import sys
        print('[universe-shell] JavaScript-JIT uit: %s' % reason, file=sys.stderr, flush=True)


if cpu_lacks_jit_features():
    no_jit('processor zonder SSE4.2')


def surface_of(view):
    return getattr(view, 'surface', None)


def _restart_page(view, reason, page, uri):
    """23 Oct: on the H310M and in the VM the world page's process stopped (the desktop froze in the intro or turned
    into the plain GTK grey when the start menu opened) and nothing brought it back. Log it and load the page again;
    after 3 stops within a minute wait 10 s so a page that keeps failing cannot spin."""
    import sys
    import time
    name = getattr(reason, 'value_nick', None) or str(reason)
    now = time.monotonic()
    recent = [t for t in _restarts.get(page, []) if now - t < 60] + [now]
    _restarts[page] = recent
    print('[universe-shell] paginaproces %s gestopt (%s); opnieuw laden (%d keer deze minuut)' % (page, name, len(recent)),
          file=sys.stderr, flush=True)
    if page in FALLBACK and not getattr(surface_of(view), 'uri', None) and grafisch.to_light(WEBKIT_GRAPHICS[0]):
        # 0.2.31: first step after a crash: the light hardware mode (processor paints, GPU only composites, lighter
        # world), remembered for the next login. Only if that crashes too: processor drawing, then 2D.
        print('[universe-shell] %s gecrasht: verder in de lichte hardware-modus' % page, file=sys.stderr, flush=True)
        _restarts[page] = []
        light_uri = page_uri(page)
        GLib.timeout_add(500, lambda: view.load_uri(light_uri) and False)
        return
    if page in FALLBACK and not getattr(surface_of(view), 'uri', None) and grafisch.to_processor(WEBKIT_GRAPHICS[0]):
        # 0.2.30 (GT 710 on nouveau): GPU drawing crashes the world; the processor draws it instead (gfx=soft), before
        # the 2D fallback. The count starts again for the processor-drawn page.
        print('[universe-shell] %s gecrasht op nouveau: verder met processor-tekenen' % page, file=sys.stderr, flush=True)
        _restarts[page] = []
        soft_uri = page_uri(page)
        GLib.timeout_add(500, lambda: view.load_uri(soft_uri) and False)
        return
    if len(recent) >= 2:
        no_jit('%s stopte %d keer binnen een minuut' % (page, len(recent)))  # the next process starts without JIT
    surface = getattr(view, 'surface', None)
    if len(recent) >= 3 and page in FALLBACK and hasattr(surface, 'fallback') and not getattr(surface, 'uri', None):
        GLib.timeout_add(500, lambda: surface.fallback('%s stopte %d keer binnen een minuut' % (page, len(recent))) and False)
        return
    uri = getattr(surface, 'uri', None) or uri  # after the fallback: reload the simple page
    GLib.timeout_add(10000 if len(recent) > 3 else 500, lambda: view.load_uri(uri) and False)


def _policy(view, decision, kind):
    if kind == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
        uri = decision.get_navigation_action().get_request().get_uri()
        if not uri.startswith('file://' + UI_DIR):
            decision.ignore()
            if uri.startswith(('http://', 'https://')):
                GLib.spawn_async(['xdg-open', uri], flags=GLib.SpawnFlags.SEARCH_PATH)
            return True
    return False
