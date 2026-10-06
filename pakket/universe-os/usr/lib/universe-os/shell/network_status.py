"""NetworkManager observations, without guessing Internet access or missing drivers."""
import os
import subprocess


def query(*args):
    result = subprocess.run(['nmcli', '-t', '--escape', 'no', *args],
                            capture_output=True, text=True, timeout=5,
                            env=dict(os.environ, LC_ALL='C'))
    if result.returncode:
        raise RuntimeError('NetworkManager is niet bereikbaar.')
    return result.stdout.strip()


def classify(devices, radio, connectivity):
    rows = [line.split(':', 2) for line in devices.splitlines()]
    rows = [row for row in rows if len(row) == 3 and row[0] not in ('loopback', 'tun', 'bridge')]
    connected = [row for row in rows if row[1] in ('connected', 'connected (externally)')]
    if connected:
        row = next((row for row in connected if row[0] == 'ethernet'), connected[0])
        messages = {'full': 'Verbonden met internet.', 'portal': 'Verbonden; aanmelden bij het netwerk is nodig.',
                    'limited': 'Verbonden met het netwerk, maar geen internet bevestigd.',
                    'none': 'Verbonden met het netwerk, maar geen internet.',
                    'unknown': 'Verbonden; internettoegang is nog onbekend.'}
        return {'state': 'connected', 'type': row[0], 'name': row[2],
                'reason': connectivity if connectivity in messages else 'unknown',
                'message': messages.get(connectivity, messages['unknown'])}
    if not rows:
        reason, message = 'no-device', 'Geen netwerkapparaat herkend. Controleer de aansluiting, driver en firmware.'
    elif any(row[0] == 'wifi' for row in rows) and radio == 'disabled':
        reason, message = 'wifi-off', 'Wifi staat uit. Er is geen andere netwerkverbinding actief.'
    elif all(row[1] == 'unmanaged' for row in rows):
        reason, message = 'unmanaged', 'De netwerkapparaten worden niet door NetworkManager beheerd.'
    elif all(row[1] == 'unavailable' for row in rows):
        reason, message = 'device-unavailable', 'Netwerkapparaat niet beschikbaar. Controleer kabel, radio, driver en firmware.'
    else:
        reason, message = 'disconnected', 'Niet verbonden met een netwerk.'
    return {'state': 'disconnected', 'reason': reason, 'message': message}


def status():
    try:
        devices = query('-f', 'TYPE,STATE,CONNECTION', 'device', 'status')
        radio = query('radio', 'wifi')
        connectivity = query('networking', 'connectivity')
        return classify(devices, radio, connectivity)
    except (OSError, subprocess.TimeoutExpired, RuntimeError):
        return {'state': 'unavailable', 'reason': 'manager-unavailable',
                'message': 'NetworkManager is niet bereikbaar. De netwerkstatus kan niet worden bepaald.'}
