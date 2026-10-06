"""Read PackageKit metadata without silently refreshing; explicit refresh is separate."""
import json
import os
import re
import shutil
import subprocess
import threading
import time

import config

refresh_lock = threading.Lock()


def run(args, timeout=25):
    env = dict(os.environ, LC_ALL='C', LANG='C')
    return subprocess.run(['pkcon', '--plain', '--noninteractive'] + args,
                          capture_output=True, text=True, timeout=timeout, env=env)


def record():
    return config.read_json(os.path.join(config.user_dir(), 'update-check.json'), {})


def result(state, count=None, checked=None, error=None):
    return {'state': state, 'count': count, 'checkedAt': checked, 'error': error,
            'rebootRequired': os.path.exists('/run/reboot-required')}


def status():
    if not shutil.which('pkcon'):
        return result('error', error='PackageKit is niet beschikbaar.')
    saved = record()
    checked = saved.get('checkedAt')
    try:
        age = run(['get-time', 'refresh-cache'])
        # pkcon formats the age in seconds in the C locale. Unknown output
        # must never become a claim that the package list is current.
        seconds = re.search(r'(\d+)\s*(?:seconds?|s)\b', age.stdout)
        if age.returncode == 0 and seconds and 0 < int(seconds[1]) < 2**31:
            external = time.time() - int(seconds[1])
            checked = max(checked or 0, external)
        available = run(['--cache-age', '-1', 'get-updates'])
    except (OSError, subprocess.TimeoutExpired):
        return result('error', checked=checked, error='Updatecontrole is mislukt of duurde te lang.')
    if available.returncode not in (0, 5):
        return result('error', checked=checked, error='Controle mislukt. Controleer internet, datum en tijd, en probeer opnieuw.')
    count = len(re.findall(r'^(?:Normal|Security|Important|Bugfix|Enhancement|Low)\s', available.stdout, re.M | re.I))
    if available.returncode == 5 and not re.search(r'no (?:updates|packages)', available.stdout, re.I):
        return result('error', checked=checked, error='PackageKit gaf geen bruikbare updategegevens.')
    if saved.get('error') and (checked or 0) <= saved.get('errorAt', 0):
        return result('error', count, checked, saved['error'])
    if not checked or not 0 <= time.time() - checked < 86400:
        return result('stale', count, checked)
    return result('available' if count else 'current', count, checked)


def refresh():
    if not refresh_lock.acquire(blocking=False):
        raise RuntimeError('Er loopt al een updatecontrole.')
    try:
        saved = record()
        try:
            if not shutil.which('pkcon'):
                raise RuntimeError('PackageKit is niet beschikbaar.')
            completed = run(['refresh', 'force'], timeout=120)
            if completed.returncode != 0:
                raise RuntimeError('Verversen mislukt. Controleer internet, datum/tijd en eventuele beheerdersrechten.')
            saved = {'checkedAt': time.time()}
        except (OSError, subprocess.TimeoutExpired, RuntimeError) as error:
            saved.update(error=str(error) if isinstance(error, RuntimeError) else 'Updatecontrole is mislukt of duurde te lang.', errorAt=time.time())
        config.write_json(os.path.join(config.user_dir(), 'update-check.json'), saved)
        return status()
    finally:
        refresh_lock.release()
