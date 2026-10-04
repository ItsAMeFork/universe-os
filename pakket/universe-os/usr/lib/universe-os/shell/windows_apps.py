"""Beheerscherm Windows-programma's: confirm and install .exe/.msi files, start, inspect and remove programs.

Opened from the file manager with --installeer FILE (the file is only shown; nothing runs until the user clicks
"Installeren"), from the Applicaties planet, or from search.
"""
import json
import os
import subprocess
import sys
import threading

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import wine  # noqa: E402
from webview import Bridge, emit, make_view  # noqa: E402


def choose_file(_):
    r = subprocess.run(['zenity', '--file-selection', '--title=Kies een Windows-installatiebestand',
                        '--file-filter=Windows-programma\'s (.exe, .msi) | *.exe *.EXE *.msi *.MSI', '--file-filter=Alle bestanden | *'],
                       capture_output=True, text=True)
    return r.stdout.strip() or None


def open_logs(slug):
    subprocess.Popen(['thunar', wine.log_dir(slug)], start_new_session=True)


def start_detached(slug, index):
    subprocess.Popen(['universe-wine', 'start', slug, str(int(index))], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class WindowsApps(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='nl.universeos.WindowsApps', flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None
        self.view = None
        self.pending = None
        self.installing = False

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        if '--installeer' in args and args.index('--installeer') + 1 < len(args):
            target = args[args.index('--installeer') + 1]
            if target.startswith('file://'):
                target = Gio.File.new_for_uri(target).get_path()
            self.pending = target
        self.activate()
        if self.view and self.pending:
            emit(self.view, 'confirm', self.pending)
        return 0

    def handlers(self):
        def install(a):
            if self.installing:
                raise wine.WineError('Er loopt al een installatie. Wacht tot die klaar is.')
            if not a.get('confirmed'):
                raise wine.WineError('De installatie is niet bevestigd.')
            path, name = a['path'], a.get('name', '')
            info = wine.file_info(path)
            if info['sha256'] != a.get('sha256'):
                raise wine.WineError('Het bestand is gewijzigd nadat je het bekeek. Open het opnieuw.')
            self.installing = True

            def work():
                try:
                    app = wine.install(path, name, progress=lambda p: GLib.idle_add(emit, self.view, 'progress', p))
                    GLib.idle_add(emit, self.view, 'installed', app)
                except wine.WineError as error:
                    GLib.idle_add(emit, self.view, 'install-error', str(error))
                except Exception as error:  # unexpected: still a readable message
                    GLib.idle_add(emit, self.view, 'install-error', 'Onverwachte fout tijdens installeren: %s' % error)
                finally:
                    self.installing = False
            threading.Thread(target=work, daemon=True).start()
            return True

        return {
            'config.get': lambda a: {'settings': config.settings(), 'world': config.world()},
            'wine.support': lambda a: wine.support(),
            'wine.list': lambda a: wine.list_apps(),
            'wine.info': lambda a: wine.file_info(a['path']),
            'wine.check': lambda a: wine.check_supported(wine.file_info(a['path'])) or True,
            'wine.choose': choose_file,
            'wine.install': install,
            'wine.start': lambda a: start_detached(a['slug'], a.get('index', 0)),
            'wine.remove': lambda a: wine.remove(a['slug'], wipe_data=bool(a.get('wipe'))),
            'wine.verdict': lambda a: wine.set_verdict(a['slug'], a.get('verdict')),
            'wine.exe': lambda a: wine.choose_executable(a['slug'], a['path']),
            'wine.logs': lambda a: open_logs(a['slug']),
            'wine.winecfg': lambda a: wine.winecfg(a['slug']),
            'wine.mono': lambda a: wine.enable_mono(a['slug']),
            'window.pending': lambda a: self.pending,
        }

    def do_activate(self):
        if self.window:
            self.window.present()
            return
        try:
            wine.refuse_root()
        except wine.WineError as error:
            print(error, file=sys.stderr)
            self.quit()
            return
        bridge = Bridge(self.handlers(), threaded={'wine.support', 'wine.info', 'wine.check', 'wine.choose', 'wine.remove', 'wine.mono'})
        self.window = Gtk.ApplicationWindow(application=self, title='Windows-programma\'s')
        self.window.set_default_size(980, 700)
        self.window.set_icon_name('wine')
        self.view = make_view('windows.html', bridge, zoom=config.settings()['uiScale'] / 100)
        self.window.add(self.view)
        self.window.connect('delete-event', self.on_close)
        self.window.show_all()

    def on_close(self, *a):
        if self.installing:
            emit(self.view, 'install-busy')
            return True  # an installation is running: keep the window (the installer window stays usable)
        return False


if __name__ == '__main__':
    GLib.set_prgname('nl.universeos.WindowsApps')
    sys.exit(WindowsApps().run(sys.argv))
