"""Standard resolution 1920x1080 (Jesse, 23 Oct): choose_mode, setting, autostart order, X fallback."""
import importlib.machinery, importlib.util, os, sys
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pakket', 'universe-os')
sys.path.insert(0, os.path.join(root, 'usr/lib/universe-os/shell'))
loader = importlib.machinery.SourceFileLoader('displays', os.path.join(root, 'usr/lib/universe-os/universe-displays'))
spec = importlib.util.spec_from_loader('displays', loader); d = importlib.util.module_from_spec(spec); loader.exec_module(d)
m = lambda w, h, r=60.0, cur=False, pref=False: {'width': w, 'height': h, 'refresh': r, 'current': cur, 'preferred': pref}
four_k = [m(3840, 2160, 60, True, True), m(1920, 1080, 50), m(1920, 1080, 60), m(1280, 720)]
assert d.choose_mode(four_k, '1920x1080')['refresh'] == 60
assert d.choose_mode([m(1920, 1080, cur=True, pref=True)], '1920x1080') is None
assert d.choose_mode([m(1366, 768, cur=True, pref=True)], '1920x1080') is None  # no 1080p: keep preferred
assert d.choose_mode(four_k, 'preferred') is None
assert d.choose_mode(four_k, '2560x1440') is None
import config
assert config.settings()['displayResolution'] == '1920x1080'
for bad in ('groot', '1920', 'x1080'):
    try: config.set_setting('displayResolution', bad); raise SystemExit('accepted ' + bad)
    except ValueError: pass
import session
a = session.AUTOSTART
assert a.index('universe-displays resolution') < a.index('universe-shell-supervisor')
conf = open(os.path.join(root, 'usr/share/lightdm/lightdm.conf.d/60-universe.conf')).read()
assert 'display-setup-script=/usr/lib/universe-os/universe-xrandr-1080' in conf
assert 'x11-xserver-utils' in open(os.path.join(root, 'DEBIAN/control')).read()
print('ok')
