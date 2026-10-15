"""Morning overview from agenda, important mail, shifts and open tasks.

Read-only. The countdown is the next appointment on this computer.
"""
import re
import time

import brein
import kast

_DIENST = re.compile(r'(dienst|shift|ploeg|rooster)', re.I)


def enabled():
    return bool(kast.load()['briefing'].get('aan'))


def configure(args):
    args = args if isinstance(args, dict) else {}
    if 'aan' in args:
        kast.update('briefing', aan=bool(args.get('aan')))
    return public()


def countdown_text(seconds):
    seconds = max(0, int(seconds or 0))
    if seconds < 60:
        return 'nu'
    minutes = seconds // 60
    if minutes < 60:
        return 'over %d min' % minutes
    hours, rest = divmod(minutes, 60)
    if rest:
        return 'over %d uur %d min' % (hours, rest)
    return 'over %d uur' % hours


def _tasks():
    try:
        import taken
        board = taken.bord(12)
    except Exception:
        return []
    rows = []
    for task in board.get('taken') or []:
        if task.get('status') in ('bezig', 'geblokkeerd', 'todo'):
            rows.append({'titel': task.get('titel') or 'Taak', 'status': task.get('status') or ''})
    return rows[:6]


def compose(now=None):
    now = time.time() if now is None else float(now)
    if not enabled():
        return {'aan': False, 'regels': [], 'aftellen': None, 'mail': [], 'agenda': [], 'diensten': [], 'taken': []}
    agenda = brein.list_agenda(8, now=now)
    mail = brein.list_mail(5)
    tasks = _tasks()
    coming = [item for item in agenda if float(item['start']) >= now - 60]
    diensten = [item for item in coming if _DIENST.search(item.get('titel') or '')]
    nxt = coming[0] if coming else None
    aftellen = None
    if nxt:
        seconds = max(0, int(float(nxt['start']) - now))
        aftellen = {
            'titel': nxt['titel'], 'plek': nxt.get('plek') or '',
            'seconden': seconds, 'tekst': countdown_text(seconds),
            'dienst': bool(_DIENST.search(nxt.get('titel') or '')),
        }
    regels = []
    if aftellen:
        regels.append('%s %s' % (aftellen['titel'], aftellen['tekst']))
    for item in mail[:3]:
        regels.append('Mail: %s' % (item.get('onderwerp') or 'bericht'))
    for item in diensten[:2]:
        if not aftellen or item['titel'] != aftellen['titel']:
            regels.append('Dienst: %s' % item['titel'])
    for item in tasks[:3]:
        regels.append('Taak: %s' % item['titel'])
    return {
        'aan': True, 'regels': regels[:8], 'aftellen': aftellen,
        'mail': [{'onderwerp': item.get('onderwerp') or '', 'van': item.get('van') or ''} for item in mail[:5]],
        'agenda': [{'titel': item.get('titel') or '', 'van': item.get('van') or '', 'plek': item.get('plek') or ''} for item in coming[:6]],
        'diensten': [{'titel': item.get('titel') or '', 'van': item.get('van') or ''} for item in diensten[:4]],
        'taken': tasks,
    }


def due(now=None):
    """Once in the morning, when there is something to say."""
    now = time.time() if now is None else float(now)
    if not enabled():
        return None
    local = time.localtime(now)
    if not (6 <= local.tm_hour < 11):
        return None
    day = time.strftime('%Y-%m-%d', local)
    if kast.load()['briefing'].get('gezien') == day:
        return None
    info = compose(now)
    if not info['regels']:
        return None
    info['dag'] = day
    return info


def mark_seen(now=None):
    now = time.time() if now is None else float(now)
    day = time.strftime('%Y-%m-%d', time.localtime(now))
    kast.update('briefing', gezien=day)
    return day


def public():
    info = compose()
    return {
        'aan': enabled(),
        'tekst': 'Aan' if enabled() else 'Uit',
        'aftellen': info.get('aftellen'),
        'regels': info.get('regels') or [],
        'uitleg': 'Ochtendoverzicht van agenda, belangrijke mail, diensten en taken. Alleen wat al op deze computer staat.',
    }
