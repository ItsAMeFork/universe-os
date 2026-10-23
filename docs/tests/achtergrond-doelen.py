"""Headless: goals in the Brein can move in the background.

Routine steps may proceed. Paying, deleting, passwords and important mail always
open the question, also while auto-accept is on. Those dialogs stay in place.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / 'pakket/universe-os/usr/lib/universe-os/claude'
UI = ROOT / 'pakket/universe-os/usr/share/universe-os/ui'
SHELL = ROOT / 'pakket/universe-os/usr/lib/universe-os/shell/universe_shell.py'
os.environ['XDG_DATA_HOME'] = tempfile.mkdtemp(prefix='doelen-data-')
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='doelen-config-')
os.environ['HOME'] = tempfile.mkdtemp(prefix='doelen-home-')
sys.path.insert(0, str(CLAUDE))

import auto_accept  # noqa: E402
import brein  # noqa: E402
import confirm  # noqa: E402
import doelen  # noqa: E402

auto_accept.set_choice(True, 'tot-uit', now=5_000)


def boom(*_args):
    raise AssertionError('venster terwijl een veilige stap geen vraag is')


assert doelen.background() is False
made = doelen.add('vat de notities samen')
assert made['lijst'][0]['status'] == 'bezig'
assert doelen.tick(boom, now=5_000)['reden'] == 'uit'
assert doelen.public()['lijst'][0]['status'] == 'bezig'

doelen.set_background(True)
first = doelen.tick(boom, now=5_100)
assert first['starten'] is True and first['stap'] == 'vat de notities samen'
assert doelen.public()['lijst'][0]['status'] == 'klaar'
notes = brein.recall('notities')
assert notes and 'Stap gedaan' in notes[0]['tekst']
assert not any(row['status'] == 'automatisch' and 'betalen' in row['samenvatting'].lower()
               for row in brein.list_acties())

paid = doelen.add('betaal de rekening\nzet de planten op een rij')
asked = []


def refuse(title, text):
    asked.append((title, text))
    return False


waiting = doelen.tick(refuse, now=5_200)
assert waiting['starten'] is False and waiting['wacht'] is True
assert asked and 'betalen' in asked[0][0].lower()
assert 'rekening' in asked[0][1]
again = doelen.tick(boom, now=5_300)
assert again['reden'] == 'wacht'
assert doelen.public()['lijst'][0]['status'] == 'wacht'
assert all(row['status'] != 'automatisch' for row in brein.list_acties() if 'betaal' in row['samenvatting'].lower())

doelen.opnieuw(paid['lijst'][0]['id'])


def allow(title, text):
    asked.append((title, text))
    return True


allowed = doelen.tick(allow, now=5_400)
assert allowed['starten'] is False and allowed.get('goedgekeurd') is True
assert doelen.public()['lijst'][0]['status'] == 'bezig'
approved = [row for row in brein.list_acties() if row['hulpmiddel'] == 'doel' and row['status'] == 'goedgekeurd']
assert approved and 'niet uitgevoerd' in approved[0]['detail'].lower()
followed = doelen.tick(boom, now=5_500)
assert followed['starten'] is True and followed['stap'] == 'zet de planten op een rij'

for titel in ('verwijder de oude map', 'vul het wachtwoord Sup3rGeheim! in',
              'verstuur belangrijke mail naar de bank'):
    doelen.add(titel)
    seen = []

    def capture(title, text, box=seen):
        box.append((title, text))
        return False

    outcome = doelen.tick(capture, now=6_000)
    assert outcome['wacht'] is True, titel
    assert seen, titel
    blob = (seen[0][0] + '\n' + seen[0][1]).lower()
    assert 'sup3rgeheim' not in blob
    assert 'automatisch toestaan' in blob

assert confirm.ask('Betaling', 'Nu betalen', runner=boom) is False
assert confirm.deferred() is True
dialog = []
assert confirm.ask_always('Betaling', 'Nu betalen', runner=lambda title, text: dialog.append(title) or False) is False
assert dialog == ['Betaling']
assert confirm.ask_always('Wachtwoord', 'veld', runner=lambda *_a: True) is True

confirm_src = (CLAUDE / 'confirm.py').read_text(encoding='utf-8')
assert "['zenity', '--question'" in confirm_src
assert "'--ok-label', 'Toestaan'" in confirm_src and "'--cancel-label', 'Weigeren'" in confirm_src
accounts = (CLAUDE / 'accounts.py').read_text(encoding='utf-8')
screen = (CLAUDE / 'screen.py').read_text(encoding='utf-8')
assert 'Claude wil een e-mail versturen' in accounts
assert 'Klik op:' in screen and 'verwijder' in screen.lower()
doelen_src = (CLAUDE / 'doelen.py').read_text(encoding='utf-8')
assert 'send_mail' not in doelen_src and 'desktop.trash' not in doelen_src

shell = SHELL.read_text(encoding='utf-8')
assert 'doelen.tick' in shell and 'ask_always' in shell
assert "'doelen.achtergrond'" in shell
assert "'doelen.achtergrond'" not in shell.split('CLAUDE_CALLS', 1)[1].split('CLAUDE_RUN', 1)[0]

ui = (UI / 'brein-nevel.js').read_text(encoding='utf-8')
assert 'Op de achtergrond' in ui and 'doelen.achtergrond' in ui and 'doelen.add' in ui
assert 'Belangrijke mail' in ui or 'belangrijke mail' in ui
css = (UI / 'world.css').read_text(encoding='utf-8')
assert 'nebula-goal' in css

brein.forget_all('alles vergeten')
assert doelen.public()['lijst'] == []
print('PASS: doelen')
