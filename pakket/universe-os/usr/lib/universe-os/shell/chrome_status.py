"""Read the installer-owned Chrome state; desktop presence decides launchability."""
import json

DEFAULT = 'Chrome wordt na de installatie gedownload zodra er internet is.'


def read(available, path='/var/lib/universe-os/chrome.json'):
    try:
        with open(path, encoding='utf-8') as stream:
            data = json.load(stream)
        if not isinstance(data, dict) or data.get('state') not in ('offline', 'installing', 'installed', 'error'):
            raise ValueError()
        state = data['state']
        message = data.get('message')
        if not isinstance(message, str) or not message.strip():
            message = {'offline': DEFAULT, 'installing': 'Chrome wordt gedownload en geïnstalleerd.',
                       'installed': 'Chrome is geïnstalleerd.', 'error': 'Chrome installeren is mislukt.'}[state]
    except FileNotFoundError:
        state, message = 'pending', DEFAULT
    except (OSError, ValueError):
        state, message = 'error', 'De downloadstatus van Chrome kon niet worden gelezen.'
    if available:
        state, message = 'installed', 'Chrome is geïnstalleerd en klaar om te openen.'
    elif state == 'installed':
        state, message = 'error', 'Chrome is nog niet beschikbaar als programma. Controleer de installatie.'
    return {'state': state, 'message': message, 'available': bool(available)}
