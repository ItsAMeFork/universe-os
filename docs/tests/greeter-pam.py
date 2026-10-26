#!/usr/bin/env python3
"""Klus g2: PAM-loginflow van greeter.py, getest met een nagebootste LightDM-module (geen gi/GTK nodig).
Flows: goed wachtwoord, fout wachtwoord (geen toegang, opnieuw klaar), wisselen van gebruiker (cancel_authentication),
al aangemeld (logged_in), en: er wordt nooit een wachtwoord gelogd of bewaard."""
import importlib.util
import os
import sys
import types
import unittest
from unittest import mock

SHELL = os.path.join(os.path.dirname(__file__), '..', '..', 'pakket', 'universe-os', 'usr', 'lib', 'universe-os', 'shell')
GREETER = os.path.join(SHELL, 'greeter.py')
SECRET = 'geheim-wachtwoord-123'


class FakeGLibError(Exception):
    pass


class FakeGreeter:
    """Minimal LightDM.Greeter: password 'goed' is correct for every user except 'bestaatniet'."""
    def __init__(self):
        self.handlers = {}
        self.in_auth = False
        self.user = None
        self.authenticated = False
        self.calls = []
        self.started = []
        self.session_ok = True

    def connect(self, name, cb):
        self.handlers[name] = cb

    def connect_to_daemon_sync(self):
        return True

    def get_select_user_hint(self):
        return ''

    def get_in_authentication(self):
        return self.in_auth

    def get_is_authenticated(self):
        return self.authenticated

    def get_authentication_user(self):
        return self.user

    def authenticate(self, user):
        self.calls.append(('authenticate', user))
        self.in_auth, self.user, self.authenticated = True, user, False
        self.handlers['show-prompt'](self, 'Password:', 1)

    def cancel_authentication(self):
        self.calls.append(('cancel_authentication',))
        self.in_auth, self.user, self.authenticated = False, None, False

    def respond(self, text):
        self.calls.append(('respond',))  # the secret itself is never recorded here
        self.authenticated = text == 'goed' and self.user != 'bestaatniet'
        self.in_auth = False
        self.handlers['authentication-complete'](self)

    def start_session_sync(self, session):
        self.calls.append(('start_session_sync', session))
        self.started.append(self.user)
        return self.session_ok


class FakeUser:
    def __init__(self, name, logged_in):
        self.name, self.logged_in = name, logged_in

    def get_name(self):
        return self.name

    def get_logged_in(self):
        return self.logged_in


def load_greeter(sessions):
    lightdm = types.SimpleNamespace(
        Greeter=FakeGreeter,
        PromptType=types.SimpleNamespace(SECRET=1, QUESTION=0),
        UserList=types.SimpleNamespace(get_instance=lambda: types.SimpleNamespace(
            get_users=lambda: [FakeUser(n, s) for n, s in sessions.items()])),
        get_can_shutdown=lambda: True, get_can_suspend=lambda: True, get_can_restart=lambda: True)
    events = []
    glib = types.SimpleNamespace(Error=FakeGLibError, timeout_add=lambda ms, cb: 42,
                                 source_remove=lambda i: None)
    gtk = mock.MagicMock()
    repo = types.SimpleNamespace(Gtk=gtk, Gdk=mock.MagicMock(), GLib=glib, LightDM=lightdm)
    gi = types.ModuleType('gi')
    gi.require_version = lambda *a: None
    gi.repository = repo
    webview = types.ModuleType('webview')
    webview.Bridge = lambda handlers, log=None: types.SimpleNamespace(handlers=handlers)
    webview.make_view = lambda page, bridge: mock.MagicMock()
    webview.emit = lambda view, name, data=None: events.append((name, data))
    config = types.ModuleType('config')
    config.settings = lambda: {'animations': 'full'}
    mods = {'gi': gi, 'gi.repository': repo, 'config': config, 'webview': webview}
    with mock.patch.dict(sys.modules, mods):
        spec = importlib.util.spec_from_file_location('greeter_under_test', GREETER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, events


class GreeterFlow(unittest.TestCase):
    def make(self, sessions=None):
        module, self.events = load_greeter(sessions or {'anna': False, 'bram': True})
        with mock.patch.object(module.PlanetGreeter, '__init__', lambda s: None):
            g = module.PlanetGreeter()
        g.dm = FakeGreeter()
        for name in ('show-prompt', 'show-message', 'authentication-complete'):
            g.dm.connect(name, {'show-prompt': g.show_prompt, 'show-message': g.show_message,
                                'authentication-complete': g.authentication_complete}[name])
        g.view = object()
        g.prompt, g.authorized, g.starting, g.timeout = None, False, False, None
        g.cancelling, g.cancel_timeout, g.attempt_active, g.user = False, None, False, ''
        self.g, self.module = g, module
        return g

    def names(self):
        return [e[0] for e in self.events]

    def test_goed_wachtwoord(self):
        g = self.make()
        g.authenticate({'user': 'anna'})
        self.assertIn('login-prompt', self.names())
        g.respond({'response': 'goed'})
        success = [d for n, d in self.events if n == 'login-success']
        self.assertEqual(success, [{'logged_in': False}])
        self.assertTrue(g.start_session({}))
        self.assertEqual(g.dm.started, ['anna'])

    def test_fout_wachtwoord_geen_toegang_en_opnieuw_klaar(self):
        g = self.make()
        g.authenticate({'user': 'anna'})
        g.respond({'response': 'fout'})
        failed = [d for n, d in self.events if n == 'login-failed']
        self.assertEqual(len(failed), 1)
        self.assertIn('Onjuist wachtwoord', failed[0]['text'])
        self.assertEqual(failed[0]['user'], 'anna')
        self.assertNotIn('login-success', self.names())
        self.assertFalse(g.authorized)
        with self.assertRaises(PermissionError):
            g.start_session({})
        self.assertEqual(g.dm.started, [])
        # the page asks again for the same user: the field is ready
        self.events.clear()
        g.authenticate({'user': 'anna'})
        self.assertIn('login-prompt', self.names())
        g.respond({'response': 'goed'})
        self.assertIn('login-success', self.names())

    def test_nooit_toegang_zonder_authenticatie(self):
        g = self.make()
        with self.assertRaises(PermissionError):
            g.start_session({})
        g.authenticate({'user': 'anna'})  # prompt open, not answered
        with self.assertRaises(PermissionError):
            g.start_session({})
        self.assertEqual(g.dm.started, [])

    def test_wisselen_annuleert_lopende_authenticatie(self):
        g = self.make()
        g.authenticate({'user': 'anna'})
        g.authenticate({'user': 'bram'})
        calls = g.dm.calls
        self.assertEqual(calls[:3], [('authenticate', 'anna'), ('cancel_authentication',), ('authenticate', 'bram')])
        self.assertEqual(g.user, 'bram')
        # answering now belongs to bram
        g.respond({'response': 'goed'})
        g.start_session({})
        self.assertEqual(g.dm.started, ['bram'])

    def test_sessie_van_andere_gebruiker_kan_niet_worden_gestart(self):
        g = self.make()
        g.authenticate({'user': 'anna'})
        g.respond({'response': 'goed'})
        g.user = 'bram'  # a different user than the authenticated one
        with self.assertRaises(PermissionError):
            g.start_session({})
        self.assertEqual(g.dm.started, [])

    def test_annuleren_via_andere_gebruiker(self):
        g = self.make()
        g.authenticate({'user': 'anna'})
        g.cancel({})
        self.assertIn(('cancel_authentication',), g.dm.calls)
        self.assertIn('login-cancelled', self.names())
        self.events.clear()
        g.dm.handlers['authentication-complete'](g.dm)  # a late result of the old attempt is ignored
        self.assertEqual(self.events, [])

    def test_al_aangemeld_gaat_terug_naar_bestaande_sessie(self):
        g = self.make({'anna': False, 'bram': True})
        g.authenticate({'user': 'bram'})
        g.respond({'response': 'goed'})
        success = [d for n, d in self.events if n == 'login-success']
        self.assertEqual(success, [{'logged_in': True}])
        self.assertTrue(g.start_session({}))  # LightDM switches to the existing session itself
        self.assertEqual(g.dm.calls[-1], ('start_session_sync', 'universe'))

    def test_sessie_start_mislukt_geeft_melding_en_geen_toegang(self):
        g = self.make()
        g.authenticate({'user': 'anna'})
        g.respond({'response': 'goed'})
        g.dm.session_ok = False
        self.assertFalse(g.start_session({}))
        self.assertFalse(g.authorized)
        self.assertIn('login-error', self.names())

    def test_wachtwoord_wordt_nooit_gelogd_of_bewaard(self):
        g = self.make()
        out = []
        with mock.patch('builtins.print', side_effect=lambda *a, **k: out.append(a)), \
                mock.patch('logging.Logger._log', side_effect=lambda *a, **k: out.append(a)):
            g.authenticate({'user': 'anna'})
            g.respond({'response': SECRET})
        self.assertEqual(out, [])
        self.assertNotIn(SECRET, repr(self.events))
        self.assertNotIn(SECRET, repr(g.dm.calls))
        self.assertNotIn(SECRET, repr(vars(g)))

    def test_broncode_logt_geen_wachtwoord(self):
        with open(GREETER) as f:
            src = f.read()
        self.assertNotIn('print(', src)
        self.assertNotIn('import logging', src)


if __name__ == '__main__':
    unittest.main(verbosity=2)
