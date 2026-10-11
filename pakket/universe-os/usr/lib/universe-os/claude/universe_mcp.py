#!/usr/bin/python3
"""universe-mcp: Universe OS tools for Claude Code (MCP over stdio, standard library only).

Claude Code starts this server itself (universe-claude passes --mcp-config). Every OS action goes through the running
Universe shell (`universe-ctl call`, an allow-list in universe_shell.CLAUDE_CALLS), so Claude gets no access that the
user's own desktop does not already have. The second brain (brein.py) is read and written directly.
"""
import base64
import json
import os
import socket
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brein  # noqa: E402
import recoll_index  # noqa: E402

SOCKET = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), 'universe-shell.sock')
PROTOCOL = '2025-06-18'
PLANETS = {'home': 'Thuiswereld (persoonlijke map)', 'apps': 'Applicaties', 'store': 'Softwarewinkel',
           'control': 'Controlecentrum', 'chat': 'Internet', 'games': 'Gamehal'}
TOOLS_FOR_RUN = ('files', 'terminal', 'monitor', 'software', 'control', 'pavucontrol', 'wdisplays', 'blueman-manager', 'network-editor')


class ToolError(Exception):
    pass


class MethodNotFound(Exception):
    pass


def shell(name, args=None, timeout=20):
    """Runs a page handler in the Universe shell and returns its result."""
    line = 'call %s %s\n' % (name, json.dumps(args or {}, ensure_ascii=False))
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(SOCKET)
            s.sendall(line.encode())
            answer = s.makefile(encoding='utf-8').readline().strip()
    except OSError as error:
        raise ToolError('De Universe-shell is niet bereikbaar (%s).' % error)
    if answer.startswith('ok '):
        return json.loads(answer[3:])
    if answer == 'ok':
        return True
    raise ToolError(answer[len('fout: '):] if answer.startswith('fout: ') else answer or 'Geen antwoord van de shell')


def slim_app(a):
    return {'id': a['id'], 'naam': a['name'], 'omschrijving': a.get('comment', '')[:120]}


# ----- tools: name -> (description, input schema, function, read-only) -----
def t_overview(a):
    data = shell('config.get')
    planets = [{'id': p.get('id'), 'naam': p.get('name')} for p in (data.get('world') or {}).get('planets', [])] \
        or [{'id': k, 'naam': v} for k, v in PLANETS.items()]
    windows = [{'id': w.get('id'), 'titel': w.get('title'), 'programma': w.get('appName'), 'actief': w.get('activated'),
                'geminimaliseerd': w.get('minimized')} for w in shell('windows.list')]
    return {'gebruiker': data.get('user'), 'planeten': planets, 'vensters': windows,
            'instellingen': data.get('settings'), 'status': shell('status')}


def t_status(a):
    return shell('status')


def t_apps(a):
    q = (a.get('zoek') or '').strip().lower()
    apps = [slim_app(x) for x in shell('apps.list')]
    if q:
        apps = [x for x in apps if q in (x['naam'] + ' ' + x['omschrijving'] + ' ' + x['id']).lower()]
    return apps[:80]


def t_open_app(a):
    app_id = str(a.get('id') or '')
    if not app_id.endswith('.desktop'):
        hits = [x for x in shell('apps.list') if app_id.lower() in (x['name'] + ' ' + x['id']).lower()]
        if not hits:
            raise ToolError('Geen programma gevonden voor "%s". Gebruik apps_lijst.' % app_id)
        app_id = hits[0]['id']
    shell('apps.launch', {'id': app_id})
    return 'Gestart: %s' % app_id


def t_windows(a):
    return [{'id': w.get('id'), 'titel': w.get('title'), 'programma': w.get('appName'), 'actief': w.get('activated'),
             'geminimaliseerd': w.get('minimized')} for w in shell('windows.list')]


def t_window(a):
    action = a.get('actie')
    if action not in ('activeren', 'minimaliseren', 'sluiten'):
        raise ToolError('actie moet activeren, minimaliseren of sluiten zijn')
    name = {'activeren': 'windows.activate', 'minimaliseren': 'windows.minimize', 'sluiten': 'windows.close'}[action]
    shell(name, {'id': str(a.get('id'))})
    return 'Venster %s: %s' % (a.get('id'), action)


def t_desktop(a):
    shell('desktop.show')
    return 'Bureaublad getoond'


def t_planet(a):
    pid = a.get('id')
    if pid not in PLANETS:
        raise ToolError('Onbekende planeet; kies uit %s' % ', '.join(PLANETS))
    shell('world.open', {'id': pid})
    return 'Planeet geopend: %s' % PLANETS[pid]


def t_search(a):
    data = shell('search', {'q': str(a.get('zoek') or '')})
    return {'programmas': [slim_app(x) for x in data.get('apps', [])], 'bestanden': data.get('files', [])}


def t_open_path(a):
    path = os.path.expanduser(str(a.get('pad') or ''))
    if not os.path.exists(path):
        raise ToolError('Bestaat niet: %s' % path)
    shell('open.path', {'path': path})
    return 'Geopend: %s' % path


def t_tool(a):
    tool = a.get('hulpmiddel')
    if tool not in TOOLS_FOR_RUN:
        raise ToolError('Kies uit %s' % ', '.join(TOOLS_FOR_RUN))
    args = {'tool': tool}
    for key in ('page', 'path', 'search'):
        if a.get(key):
            args[key] = str(a[key])
    shell('run', args)
    return 'Geopend: %s' % tool


def t_volume(a):
    if a.get('dempen'):
        shell('volume.mute')
        return 'Geluid gedempt of weer aan'
    level = max(0, min(100, int(a.get('niveau', 50))))
    shell('volume.set', {'level': level})
    return 'Volume: %d%%' % level


def t_setting(a):
    shell('config.set', {'key': a.get('sleutel'), 'value': a.get('waarde')})
    return 'Instelling %s = %s' % (a.get('sleutel'), json.dumps(a.get('waarde')))


def t_screenshot(a):
    """A small JPEG of the whole screen, so Claude can see what the user sees."""
    try:
        png = subprocess.run(['grim', '-s', '0.5', '-l', '1', '-'], capture_output=True, timeout=10, check=True).stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise ToolError('Schermafbeelding mislukt: %s' % error)
    # Debian's grim has no JPEG support; GdkPixbuf makes a JPEG that is several times smaller than the PNG.
    try:
        import gi
        gi.require_version('GdkPixbuf', '2.0')
        from gi.repository import GdkPixbuf
        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        loader.write(png)
        loader.close()
        ok, jpeg = loader.get_pixbuf().save_to_bufferv('jpeg', ['quality'], ['75'])
        if ok:
            return {'_image': base64.b64encode(jpeg).decode(), '_mime': 'image/jpeg'}
    except Exception:  # noqa: BLE001 - the PNG still works
        pass
    return {'_image': base64.b64encode(png).decode(), '_mime': 'image/png'}


def t_notify(a):
    subprocess.run(['notify-send', '-a', 'Claude', str(a.get('titel') or 'Claude')[:120], str(a.get('tekst') or '')[:500]], timeout=5)
    return 'Melding getoond'


def t_find_files(a):
    found = recoll_index.search(a.get('zoek') or '', a.get('max') or 20)
    if found is None:  # no Recoll: the quick name search of the shell
        return {'bron': 'bestandsnamen', 'resultaten': shell('search.files', {'q': str(a.get('zoek') or '')})}
    return {'bron': 'recoll (inhoud van bestanden)', 'resultaten': found}


def t_timeline(a):
    return brein.timeline(a.get('dagen') or 7, a.get('soort'), a.get('max') or 100)


def t_desktop_files(a):
    return shell('desktop.list')


def t_remember(a):
    return {'id': brein.remember(a.get('tekst'), a.get('soort') or 'notitie', a.get('labels') or '')}


def t_recall(a):
    return brein.recall(a.get('zoek') or '', a.get('soort'), a.get('max') or 20)


def t_brain_update(a):
    return brein.update(a.get('id'), a.get('tekst'))


def t_forget(a):
    return brein.forget(a.get('id'))


S = lambda props, req=(): {'type': 'object', 'properties': props, 'required': list(req)}  # noqa: E731
STR = {'type': 'string'}

TOOLS = {
    'overzicht': ('What the user sees now: planets of the space world, open windows, settings and system status. '
                  'Call this first when a request is about the screen.', S({}), t_overview, True),
    'status': ('Network, volume, battery and notifications.', S({}), t_status, True),
    'apps_lijst': ('Installed programs (id, name, description). Optional filter "zoek".', S({'zoek': STR}), t_apps, True),
    'app_openen': ('Start a program by its .desktop id (from apps_lijst) or by (part of) its name.', S({'id': STR}, ['id']), t_open_app, False),
    'vensters': ('Open windows with their id.', S({}), t_windows, True),
    'venster': ('Activate, minimize or close a window (id from vensters).',
                S({'id': STR, 'actie': {'type': 'string', 'enum': ['activeren', 'minimaliseren', 'sluiten']}}, ['id', 'actie']), t_window, False),
    'bureaublad_tonen': ('Minimize all windows to show the 3D desktop (the space world).', S({}), t_desktop, False),
    'planeet_openen': ('Fly to a planet in the space world: ' + ', '.join('%s = %s' % kv for kv in PLANETS.items()) + '.',
                       S({'id': {'type': 'string', 'enum': list(PLANETS)}}, ['id']), t_planet, False),
    'zoeken': ('Search programs and files (like the start menu search).', S({'zoek': STR}, ['zoek']), t_search, True),
    'pad_openen': ('Open a file or folder with its default program (~ allowed).', S({'pad': STR}, ['pad']), t_open_path, False),
    'hulpmiddel_openen': ('Open a system tool: ' + ', '.join(TOOLS_FOR_RUN) + '. For control, "page" picks a page; '
                          'for files, "path"; for software, "search".',
                          S({'hulpmiddel': {'type': 'string', 'enum': list(TOOLS_FOR_RUN)}, 'page': STR, 'path': STR, 'search': STR},
                            ['hulpmiddel']), t_tool, False),
    'volume': ('Set the volume (niveau 0-100) or toggle mute (dempen: true).',
               S({'niveau': {'type': 'integer', 'minimum': 0, 'maximum': 100}, 'dempen': {'type': 'boolean'}}), t_volume, False),
    'instelling': ('Change a Universe setting. Keys: animations (full/reduced/off), uiScale (50-300), textScale (75-250), '
                   'lockMinutes, screenOffMinutes (0-240), naturalScroll, tapToClick, buddy (true/false), pointerSpeed (-1..1).',
                   S({'sleutel': STR, 'waarde': {}}, ['sleutel', 'waarde']), t_setting, False),
    'schermafbeelding': ('Look at the screen: returns a half-size image of what the user sees now.', S({}), t_screenshot, True),
    'melding': ('Show a desktop notification.', S({'titel': STR, 'tekst': STR}, ['titel']), t_notify, False),
    'bureaublad_bestanden': ('Files and shortcuts on the desktop (Bureaublad folder).', S({}), t_desktop_files, True),
    'bestanden_doorzoeken': ('Second brain: full-text search INSIDE the documents of the user (PDF, office, text) with Recoll; '
                             'query syntax like a web search. Returns paths with a short excerpt.',
                             S({'zoek': STR, 'max': {'type': 'integer'}}, ['zoek']), t_find_files, True),
    'tijdlijn': ('Second brain: what the user opened recently (programs and files), newest first.',
                 S({'dagen': {'type': 'integer'}, 'soort': {'type': 'string', 'enum': ['app', 'file']}, 'max': {'type': 'integer'}}), t_timeline, True),
    'brein_onthouden': ('Second brain (local, private): remember something for later conversations. soort: voorkeur '
                        '(how the user likes things), feit (about the user or computer) or notitie.',
                        S({'tekst': STR, 'soort': {'type': 'string', 'enum': list(brein.KINDS)}, 'labels': STR}, ['tekst']), t_remember, False),
    'brein_zoeken': ('Second brain: search memories (empty "zoek" = most recent). Check preferences at the start of a task.',
                     S({'zoek': STR, 'soort': {'type': 'string', 'enum': list(brein.KINDS)}, 'max': {'type': 'integer'}}), t_recall, True),
    'brein_bijwerken': ('Second brain: replace the text of a memory.', S({'id': {'type': 'integer'}, 'tekst': STR}, ['id', 'tekst']), t_brain_update, False),
    'brein_vergeten': ('Second brain: delete a memory.', S({'id': {'type': 'integer'}}, ['id']), t_forget, False),
}


def content(result):
    if isinstance(result, dict) and '_image' in result:
        return [{'type': 'image', 'data': result['_image'], 'mimeType': result['_mime']}]
    text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=1)
    return [{'type': 'text', 'text': text}]


def handle(msg):
    method, params = msg.get('method'), msg.get('params') or {}
    if method == 'initialize':
        return {'protocolVersion': params.get('protocolVersion') or PROTOCOL, 'capabilities': {'tools': {}},
                'serverInfo': {'name': 'universe', 'version': '1.0'},
                'instructions': 'Tools to operate Universe OS (the user\'s desktop) and a private local second brain.'}
    if method == 'ping':
        return {}
    if method == 'tools/list':
        return {'tools': [{'name': name, 'description': d, 'inputSchema': schema,
                           'annotations': {'readOnlyHint': ro}} for name, (d, schema, fn, ro) in TOOLS.items()]}
    if method == 'tools/call':
        tool = TOOLS.get(params.get('name'))
        if not tool:
            return {'content': [{'type': 'text', 'text': 'Onbekend hulpmiddel'}], 'isError': True}
        try:
            return {'content': content(tool[2](params.get('arguments') or {}))}
        except Exception as error:  # every failure is a tool result Claude can read, not a protocol error
            return {'content': [{'type': 'text', 'text': str(error) or error.__class__.__name__}], 'isError': True}
    raise MethodNotFound(method)


def main():
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except ValueError:
            continue
        if 'id' not in msg:
            continue  # notifications (initialized, cancelled) need no answer
        try:
            reply = {'jsonrpc': '2.0', 'id': msg['id'], 'result': handle(msg)}
        except MethodNotFound:
            reply = {'jsonrpc': '2.0', 'id': msg['id'], 'error': {'code': -32601, 'message': 'Method not found'}}
        except Exception as error:  # never crash: Claude Code would lose all tools
            reply = {'jsonrpc': '2.0', 'id': msg['id'], 'error': {'code': -32603, 'message': str(error)}}
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + '\n')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
