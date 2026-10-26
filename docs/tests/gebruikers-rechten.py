"""Rechtencontroles van universe-admin-helper en control_center.users()/user_detail() met nagebootste pwd/grp/subprocess."""
import ast
import io
import json
import os
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2] / 'pakket/universe-os/usr/lib/universe-os'

# Nagebootste accountdatabase: tester (admin), anna en bram (normaal), root, gedeactiveerde 'daemon'.
USERS = {
    'root': (0, 0, 'root', '/bin/bash'),
    'tester': (1000, 1000, 'Tester,,,', '/bin/bash'),
    'anna': (1001, 1001, 'Anna,,,', '/bin/bash'),
    'bram': (1002, 1002, 'Bram,,,', '/bin/bash'),
    'spook': (1003, 1003, 'Spook', '/usr/sbin/nologin'),
}
SUDO = {'members': ['tester', 'root'], 'gid': 27}


def entry(name):
    uid, gid, gecos, shell = USERS[name]
    return SimpleNamespace(pw_name=name, pw_uid=uid, pw_gid=gid, pw_gecos=gecos, pw_dir='/home/' + name, pw_shell=shell)


class FakePwd:
    @staticmethod
    def getpwnam(name):
        if name not in USERS:
            raise KeyError(name)
        return entry(name)

    @staticmethod
    def getpwuid(uid):
        for name, data in USERS.items():
            if data[0] == uid:
                return entry(name)
        raise KeyError(uid)

    @staticmethod
    def getpwall():
        return [entry(n) for n in USERS]


class FakeGrp:
    @staticmethod
    def getgrnam(name):
        if name != 'sudo':
            raise KeyError(name)
        return SimpleNamespace(gr_name='sudo', gr_gid=SUDO['gid'], gr_mem=list(SUDO['members']))


def load_helper():
    mod = SourceFileLoader('universe_admin_helper', str(ROOT / 'universe-admin-helper')).load_module()
    mod.pwd, mod.grp = FakePwd, FakeGrp
    return mod


helper = load_helper()
calls = []
logged_in = set()


def fake_run(cmd, **kw):
    calls.append((cmd, kw.get('input')))
    if cmd[0] == 'adduser' and '--disabled-password' in cmd:
        USERS[cmd[-1]] = (1010, 1010, cmd[-2], '/bin/bash')
    if cmd[:2] == ['loginctl', 'show-user']:
        return SimpleNamespace(returncode=0 if cmd[2] in logged_in else 1, stdout='', stderr='')
    return SimpleNamespace(returncode=0, stdout='', stderr='')


def run(caller, *args, stdin=''):
    """Roept helper.main aan als `caller` (PKEXEC_UID). Geeft (afgesloten?, exitcode, stderr) terug."""
    calls.clear()
    env = {} if caller is None else {'PKEXEC_UID': str(USERS[caller][0])}
    err = io.StringIO()
    with patch.dict(os.environ, env, clear=False), patch.object(helper.os, 'geteuid', return_value=0), \
            patch.object(helper.subprocess, 'run', fake_run), patch.object(sys, 'stdin', io.StringIO(stdin)), \
            patch.object(sys, 'stderr', err), patch.object(sys, 'stdout', io.StringIO()), patch.object(helper.os, 'chmod', Mock()):
        if caller is None:
            os.environ.pop('PKEXEC_UID', None)
        try:
            helper.main(list(args))
            return False, 0, err.getvalue()
        except SystemExit as exit_:
            return True, exit_.code, err.getvalue()


def changed(cmds=None):
    mutating = ('adduser', 'deluser', 'chpasswd', 'usermod')
    return [c for c, _ in calls if c[0] in mutating]


# --- aanroeper onbekend of ongeldig: alles geweigerd ---
for bad in (None,):
    stopped, code, _ = run(bad, 'set-password', 'anna', stdin='geheim123\n')
    assert stopped and code == 126 and not changed(), 'zonder PKEXEC_UID moet alles geweigerd worden'
calls.clear()
with patch.dict(os.environ, {'PKEXEC_UID': '4242'}), patch.object(helper.os, 'geteuid', return_value=0), \
        patch.object(helper.subprocess, 'run', fake_run), patch.object(sys, 'stdin', io.StringIO('geheim123\n')), patch.object(sys, 'stderr', io.StringIO()):
    try:
        helper.main(['set-password', 'anna'])
        raise AssertionError('onbekende uid had geweigerd moeten worden')
    except SystemExit as e:
        assert e.code == 126 and not changed()

# --- normale gebruiker ---
for cmd in (('add-user', 'nieuw', 'Nieuw', 'standard'), ('remove-user', 'bram', 'keep-home'), ('set-admin', 'anna', 'yes'),
            ('set-admin', 'bram', 'yes'), ('remove-user', 'anna', 'keep-home'), ('set-admin', 'tester', 'no')):
    stopped, code, _ = run('anna', *cmd, stdin='geheim123\n')
    assert stopped and code == 126 and not changed(), f'normale gebruiker mag {cmd} niet'
stopped, code, _ = run('anna', 'set-password', 'bram', stdin='geheim123\n')
assert stopped and code == 126 and not changed(), 'normale gebruiker mag andermans wachtwoord niet zetten'
stopped, code, _ = run('anna', 'set-fullname', 'bram', 'Bram X')
assert stopped and code == 126 and not changed()
# zichzelf mag wel
stopped, code, _ = run('anna', 'set-password', 'anna', stdin='geheim123\n')
assert not stopped and [c for c in changed() if c[0] == 'chpasswd']
stopped, code, _ = run('anna', 'set-fullname', 'anna', 'Anna de Vries')
assert not stopped and ['usermod', '-c', 'Anna de Vries', 'anna'] in changed()

# --- beheerder mag alles ---
stopped, code, _ = run('tester', 'set-password', 'bram', stdin='geheim123\n')
assert not stopped and [c for c in changed() if c[0] == 'chpasswd']
stopped, code, _ = run('tester', 'set-admin', 'anna', 'yes')
assert not stopped and ['adduser', 'anna', 'sudo'] in changed()
stopped, code, _ = run('tester', 'set-fullname', 'bram', 'Bram B')
assert not stopped and ['usermod', '-c', 'Bram B', 'bram'] in changed()
stopped, code, _ = run('tester', 'remove-user', 'bram', 'keep-home')
assert not stopped and ['deluser', 'bram'] in changed()
stopped, code, _ = run('tester', 'add-user', 'carla', 'Carla', 'standard', stdin='geheim123\n')
assert not stopped and any(c[0] == 'adduser' and 'carla' in c for c in changed())
USERS.pop('carla', None)

# --- wachtwoord nooit in argumenten of logging ---
run('tester', 'set-password', 'bram', stdin='geheim123\n')
assert all('geheim123' not in ' '.join(c) for c, _ in calls), 'wachtwoord mag niet in argumenten staan'
assert any(i and 'geheim123' in i for c, i in calls if c[0] == 'chpasswd'), 'chpasswd krijgt het wachtwoord via stdin'
stopped, code, err = run('tester', 'set-password', 'bram', stdin='geheim123:x\n')
assert stopped and 'geheim123' not in err
stopped, code, err = run('tester', 'set-password', 'bram', stdin='kort\n')
assert stopped and 'geheim' not in err and not changed()

# --- laatste beheerder en zelf verwijderen ---
SUDO['members'] = ['tester', 'root']  # root telt niet mee als normaal account
stopped, code, err = run('tester', 'set-admin', 'tester', 'no')
assert stopped and not changed(), 'eigen/laatste beheerder niet degraderen'
stopped, code, err = run('tester', 'remove-user', 'tester', 'keep-home')
assert stopped and not changed(), 'jezelf niet verwijderen'
SUDO['members'] = ['tester', 'anna']
stopped, code, err = run('anna', 'set-admin', 'tester', 'no')
assert not stopped and ['deluser', 'tester', 'sudo'] in changed(), 'met twee beheerders mag een beheerder een andere degraderen'
SUDO['members'] = ['tester']
stopped, code, err = run('tester', 'remove-user', 'tester', 'keep-home')
assert stopped and not changed()
# een tweede beheerder die de enige andere is, kan niet door de laatste worden weggehaald zodat niemand overblijft:
# anna (beheerder) degradeert tester terwijl zij de enige andere is -> toegestaan; tester laatste -> geweigerd
SUDO['members'] = ['tester']
stopped, code, err = run('tester', 'remove-user', 'anna', 'keep-home')
assert not stopped, 'normaal account verwijderen door de enige beheerder mag'
# laatste beheerder wordt door een andere (niet-beheerder) niet verwijderd: onmogelijk want niet bevoegd
stopped, code, _ = run('anna', 'remove-user', 'tester', 'keep-home')
assert stopped and code == 126 and not changed()
# set-admin no op de laatste beheerder via een tweede beheerder die intussen weg is -> geweigerd
SUDO['members'] = ['tester']
logged_in.add('bram')
stopped, code, err = run('tester', 'remove-user', 'bram', 'keep-home')
assert stopped and 'aangemeld' in err and not changed(), 'aangemelde gebruiker niet verwijderen'
logged_in.clear()
# ongeldige waarde voor accounttype
stopped, code, _ = run('tester', 'set-admin', 'anna', 'misschien')
assert stopped and not changed()
# systeemaccount (uid < 1000) niet aanraken
stopped, code, _ = run('tester', 'set-password', 'root', stdin='geheim123\n')
assert stopped and not changed()
# lid van sudo maar ook als hoofdgroep telt als beheerder
USERS['bram'] = (1002, SUDO['gid'], 'Bram,,,', '/bin/bash')
SUDO['members'] = ['tester']
assert helper.admins() == {'tester', 'bram'}
stopped, code, _ = run('bram', 'set-admin', 'anna', 'yes')
assert not stopped, 'hoofdgroep sudo geeft beheerdersrechten'
USERS['bram'] = (1002, 1002, 'Bram,,,', '/bin/bash')
SUDO['members'] = ['tester', 'root']

# --- control_center: users()/user_detail() zonder GTK laden ---
path = ROOT / 'shell/control_center.py'
tree = ast.parse(path.read_text(encoding='utf-8'))
wanted_funcs = {'is_admin', 'default_planet', 'own_profile', 'profile_path', 'users', 'user_detail', 'require_admin',
                'set_user_password', 'set_user_fullname', 'set_own_planet', 'admin_call'}
body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in wanted_funcs)
        or (isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'PLANETS' for t in n.targets))]
ns = {'pwd': FakePwd, 'grp': FakeGrp, 'os': os, 'pkexec_helper': Mock(return_value=True)}
tmp = tempfile.mkdtemp()
real_config = SimpleNamespace(
    user_dir=lambda: tmp,
    read_json=lambda p, f: json.load(open(p)) if os.path.exists(p) else f,
    write_json=lambda p, d: json.dump(d, open(p, 'w')))
ns['config'] = real_config
exec(compile(ast.Module(body=body, type_ignores=[]), str(path), 'exec'), ns)


def as_user(name):
    return patch.object(ns['os'], 'getuid', return_value=USERS[name][0])


SUDO['members'] = ['tester']
with as_user('anna'):
    lst = ns['users']()
    assert [u['name'] for u in lst] == ['anna', 'bram', 'tester'], 'nologin/systeemaccounts verborgen'
    for u in lst:
        assert set(u) == {'name', 'fullName', 'planet', 'me', 'canManage'}, 'overzicht toont geen uitgebreide gegevens'
        assert u['planet'] in ns['PLANETS']
    assert {u['name']: u['canManage'] for u in lst} == {'anna': True, 'bram': False, 'tester': False}
    try:
        ns['user_detail']('bram')
        raise AssertionError('normale gebruiker mag andermans instellingen niet openen')
    except PermissionError:
        pass
    assert ns['user_detail']('anna')['admin'] is False
    for fn, args in ((ns['require_admin'], ()), (ns['admin_call'], (['set-admin', 'anna', 'yes'],)),
                     (ns['set_user_password'], ('bram', 'geheim123')), (ns['set_user_fullname'], ('bram', 'X'))):
        try:
            fn(*args)
            raise AssertionError(f'{fn.__name__} had geweigerd moeten worden')
        except PermissionError:
            pass
    assert not ns['pkexec_helper'].called, 'bij afwijzing wordt pkexec niet eens gestart'
    # eigen planeet/weergavenaam: alleen in de eigen home
    ns['set_own_planet']('mars')
    ns['set_user_fullname']('anna', ' Anna de Vries ')
    me = next(u for u in ns['users']() if u['me'])
    assert me['planet'] == 'mars' and me['fullName'] == 'Anna de Vries'
    assert not ns['pkexec_helper'].called
    try:
        ns['set_own_planet']('pluto')
        raise AssertionError
    except ValueError:
        pass
    # wachtwoord van jezelf mag via pkexec-helper alleen als bevoegd door de helper; hier niet nodig
    ns['set_user_password']('anna', 'geheim123')
    ns['pkexec_helper'].assert_called_with(['set-password', 'anna'], 'geheim123\n')

ns['pkexec_helper'].reset_mock()
with as_user('tester'):
    lst = ns['users']()
    assert all(u['canManage'] for u in lst)
    assert ns['user_detail']('bram')['name'] == 'bram'
    assert ns['user_detail']('tester')['admin'] is True
    ns['admin_call'](['set-admin', 'anna', 'yes'])
    ns['set_user_password']('bram', 'geheim123')
    ns['set_user_fullname']('bram', 'Bram B')
    assert ns['pkexec_helper'].call_count == 3
    try:
        ns['user_detail']('onbekend')
        raise AssertionError
    except ValueError:
        pass
assert ns['default_planet']('anna') == ns['default_planet']('anna')
print('PASS: helper-rechten (admin/zelf/normaal, laatste beheerder, aangemeld, wachtwoord via stdin) en users()/user_detail()')
