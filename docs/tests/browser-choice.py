"""Contract test without GTK; native Gio/launch behavior still needs a VM test."""
import ast
from pathlib import Path
from types import SimpleNamespace

source = Path('pakket/universe-os/usr/lib/universe-os/shell/backend.py').read_text(encoding='utf-8')
tree = ast.parse(source)
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('browsers', 'browser_select')]

class App:
    def __init__(self, name, category):
        self.name, self.category, self.saved = name, category, []
    def get_id(self): return self.name + '.desktop'
    def should_show(self): return True
    def get_categories(self): return self.category
    def get_supported_types(self): return []
    def get_display_name(self): return self.name
    def get_icon(self): return None
    def set_as_default_for_type(self, mime):
        self.saved.append(mime)
        AppInfo.default = self
        return True

chrome, firefox, editor = App('Chrome', 'WebBrowser;Network;'), App('Firefox', 'WebBrowser;'), App('Editor', 'Utility;')
class AppInfo:
    default = None
    @classmethod
    def get_default_for_type(cls, mime, must_support_uris): return cls.default
    @staticmethod
    def get_all(): return [chrome, firefox, editor]
App.new = staticmethod(lambda key: next(a for a in AppInfo.get_all() if a.get_id() == key))
ns = {'Gio': SimpleNamespace(AppInfo=AppInfo, DesktopAppInfo=App), 'icon_uri': lambda icon: None}
exec(compile(ast.Module(body=functions, type_ignores=[]), '<backend>', 'exec'), ns)
assert ns['browsers']()['default'] is None
assert len(ns['browsers']()['apps']) == 2
assert ns['browser_select']('Firefox.desktop')['default'] == 'Firefox.desktop'
assert firefox.saved == ['x-scheme-handler/http', 'x-scheme-handler/https', 'text/html']
try:
    ns['browser_select']('Editor.desktop')
except ValueError:
    pass
else:
    raise AssertionError('Non-browser accepted')
AppInfo.default = editor
assert ns['browsers']()['default'] is None
print('Browser choice contract OK')
