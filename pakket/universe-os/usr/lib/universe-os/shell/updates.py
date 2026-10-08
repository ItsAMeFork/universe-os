"""Updates: status lezen en de systeemtaak universe-updates.service starten (controleren + verplicht installeren).

De systeemtaak (/usr/lib/universe-os/universe-updates-run, als root) schrijft zijn voortgang naar STATUS. Starten mag
zonder wachtwoord via een polkit-regel die alleen deze unit toestaat. Knop, inloggen en timer gebruiken dezelfde taak;
loopt hij al, dan start systemd geen tweede.
Contract met de interface: {state, count, checkedAt, installedAt, installed, rebootRequired, message, error},
state: checking | waiting | downloading | installing | current | available | stale | error.
"""
import json
import os
import subprocess
import time

STATUS = '/var/lib/universe-os/updates/status.json'
UNIT = 'universe-updates.service'
BUSY = ('checking', 'waiting', 'downloading', 'installing')
STALE_AFTER = 26 * 3600   # geen geslaagde controle in ruim een dag: "verouderd"
LOGIN_AFTER = 20 * 3600   # bij inloggen opnieuw controleren als de laatste controle ouder is


def _read():
    try:
        with open(STATUS) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _running():
    """True alleen als de taak nu echt bezig is. Wacht hij op een nieuwe poging (RestartSec, SubState auto-restart),
    dan telt dat niet als bezig: een klik moet dan meteen een nieuwe poging starten."""
    try:
        out = subprocess.run(['systemctl', 'show', UNIT, '-p', 'ActiveState', '-p', 'SubState'],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    props = dict(line.split('=', 1) for line in out.splitlines() if '=' in line)
    return props.get('ActiveState') in ('active', 'activating', 'reloading') and props.get('SubState') != 'auto-restart'


def status():
    data = _read()
    state = data.get('state')
    checked = data.get('checkedAt')
    result = {'state': state or 'stale', 'count': data.get('count'), 'checkedAt': checked,
              'installedAt': data.get('installedAt'), 'installed': data.get('installed'),
              'rebootRequired': os.path.exists('/run/reboot-required'),
              'message': data.get('message'), 'error': data.get('error')}
    running = _running()
    if running and state not in BUSY:
        # Net gestart; de taak heeft zijn eerste status nog niet geschreven.
        result.update(state='checking', message='Controleren op updates…', error=None)
    elif state in BUSY and not running:
        # De taak is gestopt zonder eindstatus (bijv. computer uitgezet): niet blijven hangen op "bezig".
        result.update(state='error', error='De vorige updatepoging is onderbroken. Probeer het opnieuw.',
                      message='De vorige updatepoging is onderbroken. Probeer het opnieuw.')
    elif state not in BUSY and state != 'error' and (not checked or not 0 <= time.time() - checked < STALE_AFTER):
        result['state'] = 'stale'
        result['message'] = 'Nog niet gecontroleerd op updates.' if not checked else 'De laatste controle is meer dan een dag oud.'
    return result


def install():
    """Start controleren + installeren (idempotent) en geef meteen de status terug."""
    if not _running():
        try:
            done = subprocess.run(['systemctl', 'start', '--no-block', UNIT], capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            raise RuntimeError('De updatetaak kon niet worden gestart.') from None
        if done.returncode != 0:
            raise PermissionError('Geen toestemming om updates te installeren.' if 'auth' in done.stderr.lower()
                                  else 'De updatetaak kon niet worden gestart.')
    result = status()
    if result['state'] not in BUSY:
        result.update(state='checking', message='Controleren op updates…', error=None)
    return result


def refresh():
    # "Nu controleren" is dezelfde taak: wat gevonden wordt, wordt ook geïnstalleerd (verplichte updates).
    return install()


def check_at_login():
    """Bij inloggen: echte controle als de laatste geslaagde controle ouder is dan LOGIN_AFTER. Fouten alleen loggen."""
    checked = _read().get('checkedAt')
    if checked and 0 <= time.time() - checked < LOGIN_AFTER:
        return False
    try:
        install()
    except (RuntimeError, PermissionError):
        return False
    return True
