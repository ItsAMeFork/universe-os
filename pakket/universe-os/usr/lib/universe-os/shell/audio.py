"""Available PipeWire sinks; WirePlumber owns default-device persistence."""
import json
import shutil
import subprocess
import time


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError('Het geluidssysteem is niet bereikbaar.') from None
    if result.returncode:
        raise RuntimeError('De geluidsactie is mislukt. Controleer het apparaat en het geluidssysteem.')
    return result.stdout


def parse(objects):
    active = None
    devices = {o.get('id'): o.get('info', {}).get('props', {}) for o in objects}
    for obj in objects:
        for entry in obj.get('metadata', obj.get('info', {}).get('metadata', [])):
            if entry.get('key') == 'default.audio.sink':
                value = entry.get('value')
                try:
                    if isinstance(value, str):
                        value = json.loads(value)
                    active = value.get('name') if isinstance(value, dict) else None
                except ValueError:
                    pass
    outputs = []
    for obj in objects:
        props = obj.get('info', {}).get('props', {})
        if props.get('media.class') != 'Audio/Sink':
            continue
        name = props.get('node.name')
        if not name or not isinstance(obj.get('id'), int):
            continue
        try:
            parent = devices.get(int(props.get('device.id', -1)), {})
        except (TypeError, ValueError):
            parent = {}
        combined = dict(parent, **props)
        description = props.get('node.description') or props.get('node.nick') or name
        identity = ' '.join(str(v) for v in combined.values()).lower()
        kind = ('bluetooth' if combined.get('device.api') == 'bluez5' or 'bluez_output' in name
                else 'usb' if combined.get('device.bus') == 'usb'
                else 'hdmi' if 'hdmi' in identity or 'displayport' in identity
                else 'analog' if 'analog' in identity
                else 'other')
        outputs.append({'id': obj['id'], 'name': name, 'description': description,
                        'kind': kind, 'active': name == active})
    return {'outputs': sorted(outputs, key=lambda o: (not o['active'], o['description'].lower())),
            'active': active}


def outputs():
    if not shutil.which('pw-dump') or not shutil.which('wpctl'):
        raise RuntimeError('PipeWire/WirePlumber is niet beschikbaar.')
    try:
        data = json.loads(command(['pw-dump', '--no-colors']))
        if not isinstance(data, list):
            raise ValueError()
        return parse(data)
    except (ValueError, TypeError):
        raise RuntimeError('De geluidsapparaten konden niet worden gelezen.') from None


def select(args):
    try:
        target_id = int(args['id'])
        target_name = str(args['name'])
    except (KeyError, ValueError, TypeError):
        raise ValueError('Ongeldige geluidsuitgang') from None
    target = next((o for o in outputs()['outputs'] if o['id'] == target_id and o['name'] == target_name), None)
    if not target:
        raise RuntimeError('Dit apparaat is verdwenen of gewijzigd. Vernieuw de lijst.')
    command(['wpctl', 'set-default', str(target_id)])
    for _ in range(5):
        state = outputs()
        if state['active'] == target_name:
            return state
        time.sleep(.1)
    raise RuntimeError('De nieuwe uitgang is nog niet bevestigd. Vernieuw de lijst.')
