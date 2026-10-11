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
    rows = [row for row in rows if len(row) == 3 and row[0] not in
            ('loopback', 'tun', 'bridge', 'wifi-p2p', 'wireguard', 'dummy')]
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
    if any(row[1] == 'connecting' or row[1].startswith('connecting (') for row in rows):
        return {'state': 'connecting', 'reason': 'connecting', 'message': 'Bezig met verbinden…'}
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


NM_TYPES = {1: 'ethernet', 2: 'wifi', 5: 'bt', 8: 'gsm', 13: 'bridge', 16: 'tun', 22: 'dummy', 29: 'wireguard',
            30: 'wifi-p2p', 32: 'loopback'}
NM_CONNECTIVITY = {1: 'none', 2: 'portal', 3: 'limited', 4: 'full'}


def _nm_state(state):
    if state == 100:
        return 'connected'
    if 40 <= state < 100:
        return 'connecting'
    return {10: 'unmanaged', 20: 'unavailable', 30: 'disconnected'}.get(state, 'unknown')


def dbus_status():
    """The same rows as `nmcli device status`, read over D-Bus in this process. Three nmcli processes every
    refresh were a noticeable load on a quiet desktop (VM, 11 Oct)."""
    import gi
    gi.require_version('Gio', '2.0')
    from gi.repository import Gio, GLib
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)

    def prop(path, iface, name):
        value = bus.call_sync('org.freedesktop.NetworkManager', path, 'org.freedesktop.DBus.Properties', 'Get',
                              GLib.Variant('(ss)', (iface, name)), None, Gio.DBusCallFlags.NONE, 2000, None)
        return value.unpack()[0]
    nm, dev = 'org.freedesktop.NetworkManager', 'org.freedesktop.NetworkManager.Device'
    rows = []
    for path in prop('/org/freedesktop/NetworkManager', nm, 'Devices'):
        kind = NM_TYPES.get(prop(path, dev, 'DeviceType'), 'other')
        state = _nm_state(prop(path, dev, 'State'))
        name = ''
        active = prop(path, dev, 'ActiveConnection')
        if active and active != '/':
            try:
                name = prop(active, 'org.freedesktop.NetworkManager.Connection.Active', 'Id')
            except Exception:  # noqa: BLE001 - the connection went away meanwhile
                name = ''
        rows.append('%s:%s:%s' % (kind, state, name))
    radio = 'enabled' if prop('/org/freedesktop/NetworkManager', nm, 'WirelessEnabled') else 'disabled'
    connectivity = NM_CONNECTIVITY.get(prop('/org/freedesktop/NetworkManager', nm, 'Connectivity'), 'unknown')
    return classify('\n'.join(rows), radio, connectivity)


def status():
    try:
        return dbus_status()
    except Exception:  # noqa: BLE001 - fall back to nmcli (older NetworkManager, D-Bus trouble)
        pass
    try:
        devices = query('-f', 'TYPE,STATE,CONNECTION', 'device', 'status')
        radio = query('radio', 'wifi')
        connectivity = query('networking', 'connectivity')
        return classify(devices, radio, connectivity)
    except (OSError, subprocess.TimeoutExpired, RuntimeError):
        return {'state': 'unavailable', 'reason': 'manager-unavailable',
                'message': 'NetworkManager is niet bereikbaar. De netwerkstatus kan niet worden bepaald.'}
