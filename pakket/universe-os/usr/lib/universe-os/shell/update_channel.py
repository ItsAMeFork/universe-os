"""Read/update Universe's channel through the dedicated polkit helper."""
import os
import subprocess

BASE = '/etc/apt/sources.list.d/universe-os.sources'
TEST = '/etc/apt/sources.list.d/universe-os-test.sources'


def get():
    if not os.path.exists(BASE):
        return {'active': False}
    return {'active': True, 'channel': 'test' if os.path.exists(TEST) else 'stable'}


def set_channel(args):
    channel = args.get('channel')
    if channel not in ('stable', 'test'):
        raise ValueError('Onbekend updatekanaal.')
    if not get()['active']:
        raise RuntimeError('De eigen updatebron is nog niet actief.')
    try:
        result = subprocess.run(['pkexec', '/usr/lib/universe-os/universe-updates-helper', 'kanaal', channel],
                                capture_output=True, text=True)
    except OSError:
        raise RuntimeError('Het updatekanaal kon niet worden gewijzigd.') from None
    if result.returncode == 126:
        return dict(get(), changed=False, message='Niet gewijzigd.')
    if result.returncode == 127:
        raise PermissionError('Geen toestemming om het updatekanaal te wijzigen.')
    if result.returncode or result.stdout.strip() != 'ok':
        raise RuntimeError(result.stderr.strip() or 'Het updatekanaal kon niet worden gewijzigd.')
    state = get()
    if state.get('channel') != channel:
        raise RuntimeError('Het nieuwe updatekanaal kon niet worden bevestigd.')
    return dict(state, changed=True)
