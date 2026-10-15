"""Morning briefing on the Brein page: today's agenda, important mail, one money tip.

Read-only. Sending and paying stay on the existing confirmation path.
"""
import importlib.util
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude'
SHELL = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'

os.environ['XDG_DATA_HOME'] = tempfile.mkdtemp(prefix='ochtend-data-')
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='ochtend-config-')
os.environ['XDG_RUNTIME_DIR'] = tempfile.mkdtemp(prefix='ochtend-run-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='ochtend-home-')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


brein = load(CLAUDE / 'brein.py', 'brein')
ochtend = load(CLAUDE / 'ochtend.py', 'ochtend')
auto_accept = load(CLAUDE / 'auto_accept.py', 'auto_accept')


def at(year, month, day, hour, minute):
    return time.mktime((year, month, day, hour, minute, 0, 0, 0, -1))


now = at(2026, 10, 15, 7, 20)
brein.upsert_agenda('thuis', 'tandarts', 'Tandarts', at(2026, 10, 15, 9, 0), at(2026, 10, 15, 9, 30), 'Centrum')
brein.upsert_agenda('thuis', 'nacht', 'Nachtdienst', at(2026, 10, 14, 22, 0), at(2026, 10, 15, 1, 0), '')
brein.upsert_agenda('thuis', 'morgen', 'Morgenoverleg', at(2026, 10, 16, 9, 0), at(2026, 10, 16, 10, 0), 'Kantoor')
brein.upsert_mail('thuis', 'school', 'Ouderavond', 'school@example.com', 'De school vraagt of je donderdag kunt.', now - 3600, 1)
brein.upsert_mail('thuis', 'nieuws', 'Nieuwsbrief', 'nieuws@example.com', 'Niet belangrijk.', now - 1800, 0)
brein.upsert_mail('thuis', 'oud', 'Oude factuur', 'oud@example.com', 'Van vorige week.', now - 40 * 3600, 1)

before = brein.list_acties()
info = ochtend.compose(now)
assert brein.list_acties() == before

assert info['dag'] == '2026-10-15'
assert [item['titel'] for item in info['agenda']] == ['Nachtdienst', 'Tandarts']
assert info['agenda'][1]['van'] == '09:00' and info['agenda'][1]['plek'] == 'Centrum'
assert info['agenda_tekst'] == ''
assert [item['onderwerp'] for item in info['mail']] == ['Ouderavond']
assert info['mail'][0]['samenvatting'] == 'De school vraagt of je donderdag kunt.'
assert info['mail_samenvatting'] == '1 belangrijk bericht: De school vraagt of je donderdag kunt.'
brein.upsert_mail('thuis', 'bank', 'Jaaropgave', 'bank@example.com', 'De bank stuurt de jaaropgave.', now - 7200, 1)
pair = ochtend.compose(now)
assert [item['onderwerp'] for item in pair['mail']] == ['Ouderavond', 'Jaaropgave']
assert pair['mail_samenvatting'] == '2 belangrijke berichten: Ouderavond, Jaaropgave.'
assert pair['geldtip'] == info['geldtip']
assert info['geldtip'] in ochtend.GELDTIPS
assert info['geldtip'] == ochtend.geldtip(now)
assert info['geldtip'] != ochtend.geldtip(at(2026, 10, 16, 7, 20))
assert info['bevestigen'] == ochtend.BEVESTIGEN == 'Versturen en betalen vragen om toestemming.'
assert 'versturen' not in info and 'betalen' not in info and 'send' not in info and 'pay' not in info

empty = ochtend.compose(at(2026, 11, 2, 8, 0))
assert empty['agenda'] == [] and empty['agenda_tekst'] == 'Niets op de agenda vandaag.'
assert empty['mail'] == [] and empty['mail_samenvatting'] == 'Geen belangrijke mail.'
assert empty['geldtip'] in ochtend.GELDTIPS

source = (CLAUDE / 'ochtend.py').read_text(encoding='utf-8')
for banned in ('send_mail', 'authorize_browser', 'mail.send', 'urllib', 'requests', 'confirm.ask'):
    assert banned not in source

shell = SHELL.read_text(encoding='utf-8')
assert "'brein.ochtend'" in shell
assert "'mail.send': lambda a: _mail_send(a)" in shell
assert 'confirmer=_confirm' in shell
for line in shell.splitlines():
    if 'brein.ochtend' in line and 'lambda' in line:
        assert 'send' not in line and 'betalen' not in line

auto_accept.set_choice(True, '30m', now)
assert auto_accept.decide('Betalen', 'Ik wil nu betalen', now) == 'wacht'
kind, reasons = auto_accept.mail_decision(
    ['bank@example.com'], 'Factuur', 'Gelieve het bedrag over te maken', vlag=True, now=now)
assert kind == 'wacht' and reasons
auto_accept.set_choice(False, '30m', now)
kind, _reasons = auto_accept.mail_decision(
    ['school@example.com'], 'Ouderavond', 'Ik kom.', now=now)
assert kind == 'vraag'

ui = (UI / 'brein-nevel.js').read_text(encoding='utf-8')
assert 'brein.ochtend' in ui and 'Ochtendbriefing' in ui and 'Geldtip' in ui
start = ui.index('function renderBriefing()')
end = ui.index('function renderList()')
body = ui[start:end]
assert "h('button'" not in body
assert 'Versturen en betalen vragen om toestemming.' in ui
css = (UI / 'world.css').read_text(encoding='utf-8')
assert '.ochtend' in css

import subprocess
checked = subprocess.run(['node', '--check', str(UI / 'brein-nevel.js')], capture_output=True, text=True)
assert checked.returncode == 0, checked.stderr

print('PASS: ochtend-briefing')
