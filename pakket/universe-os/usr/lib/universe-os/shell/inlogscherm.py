"""0.3.4 (Axel, 28 Oct: "de scherm mag niet uit als er geen gebruiker ingelogd is"): the screen of the login screen,
which since 0.3.3 is also the lock screen, stays on. An administrator can choose a time after which it goes off
(Controlecentrum > Energie; 0 = never, at most 120 minutes). One system-wide setting, readable by the greeter
(user lightdm), written only by universe-admin-helper (root, administrators only).

The greeter runs on an X server, whose defaults blank the screen after 10 minutes (screen saver + DPMS); the greeter
sets X to this setting each time it starts (greeter.py).
"""
import json
import os
import subprocess
import tempfile

PAD = '/etc/universe-os/inlogscherm.json'
MAX = 120


def scherm_uit_minuten(pad=PAD):
    """Minutes until the screen of the login/lock screen goes off; 0 = never. Anything unreadable counts as 0."""
    try:
        with open(pad) as f:
            waarde = json.load(f).get('schermUitMinuten', 0)
    except (OSError, ValueError, AttributeError):
        return 0
    if isinstance(waarde, bool) or not isinstance(waarde, int):
        return 0
    return max(0, min(MAX, waarde))


def zet(minuten, pad=PAD):
    """Stores the setting (root: universe-admin-helper). Only whole minutes 0..MAX."""
    if isinstance(minuten, bool) or not isinstance(minuten, int) or not 0 <= minuten <= MAX:
        raise ValueError('Kies 0 (nooit) tot en met %d minuten.' % MAX)
    map_ = os.path.dirname(pad)
    os.makedirs(map_, exist_ok=True)
    fd, tijdelijk = tempfile.mkstemp(dir=map_, prefix='.inlogscherm-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump({'schermUitMinuten': minuten}, f)
        os.chmod(tijdelijk, 0o644)
        os.replace(tijdelijk, pad)
    except BaseException:
        if os.path.exists(tijdelijk):
            os.unlink(tijdelijk)
        raise


def xset_opdrachten(minuten):
    """X never blanks by itself (screen saver off); DPMS only turns the screen off when a time is set."""
    opdrachten = [['xset', 's', 'off'], ['xset', 's', 'noblank']]
    if minuten <= 0:
        return opdrachten + [['xset', '-dpms']]
    return opdrachten + [['xset', '+dpms'], ['xset', 'dpms', '0', '0', str(minuten * 60)]]


def toepassen():
    """For the greeter: set X to the setting. Never fails (no X, no xset: nothing happens)."""
    if not os.environ.get('DISPLAY'):
        return False
    for opdracht in xset_opdrachten(scherm_uit_minuten()):
        try:
            subprocess.run(opdracht, capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return False
    return True
