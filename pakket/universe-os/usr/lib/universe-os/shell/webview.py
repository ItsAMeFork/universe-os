"""A WebKit view that shows a Universe page and connects its JavaScript (api.js) to Python handlers."""
import json
import os
import threading
import traceback

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


def reply(view, mid, ok, data):
    return _js(view, 'window.__universeReply(%d,%s,%s)' % (mid, 'true' if ok else 'false', json.dumps(data, ensure_ascii=False)))


def emit(view, name, data=None):
    _js(view, 'window.__universeEvent&&window.__universeEvent(%s,%s)' % (json.dumps(name), json.dumps(data, ensure_ascii=False)))


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
    uri = GLib.filename_to_uri('%s/%s' % (UI_DIR, page))
    if os.environ.get('UNIVERSE_DEBUG_FPS') == '1':
        uri += '?fps=1'
    view.load_uri(uri)
    return view


def _policy(view, decision, kind):
    if kind == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
        uri = decision.get_navigation_action().get_request().get_uri()
        if not uri.startswith('file://' + UI_DIR):
            decision.ignore()
            if uri.startswith(('http://', 'https://')):
                GLib.spawn_async(['xdg-open', uri], flags=GLib.SpawnFlags.SEARCH_PATH)
            return True
    return False
