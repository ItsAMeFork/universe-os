"""Quiet proactive hints. Off by default.

A few moments a day, never during quiet hours, and never the same nag again
after Niet nu or Nooit (the buddy remembers those answers itself).
"""
import time

import kast


def _minutes(text, default):
    parts = str(text or '').split(':')
    if len(parts) != 2:
        return default
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        return default
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return default
    return hour * 60 + minute


def quiet(now, start='22:00', end='07:30'):
    local = time.localtime(now)
    minutes = local.tm_hour * 60 + local.tm_min
    begin = _minutes(start, 22 * 60)
    stop = _minutes(end, 7 * 60 + 30)
    if begin <= stop:
        return begin <= minutes < stop
    return minutes >= begin or minutes < stop


def state():
    row = kast.load()['ghost']
    try:
        maximum = int(row.get('max_per_dag') or 3)
    except (TypeError, ValueError):
        maximum = 3
    try:
        gap = int(row.get('minuten') or 90)
    except (TypeError, ValueError):
        gap = 90
    return {
        'aan': bool(row.get('aan')),
        'stil_van': str(row.get('stil_van') or '22:00')[:5],
        'stil_tot': str(row.get('stil_tot') or '07:30')[:5],
        'max_per_dag': max(1, min(6, maximum)),
        'minuten': max(15, min(24 * 60, gap)),
        'dag': str(row.get('dag') or ''),
        'aantal': int(row.get('aantal') or 0),
        'laatst': float(row.get('laatst') or 0),
    }


def configure(args):
    args = args if isinstance(args, dict) else {}
    fields = {}
    if 'aan' in args:
        fields['aan'] = bool(args.get('aan'))
    if 'stil_van' in args:
        fields['stil_van'] = str(args.get('stil_van') or '22:00')[:5]
    if 'stil_tot' in args:
        fields['stil_tot'] = str(args.get('stil_tot') or '07:30')[:5]
    if fields:
        kast.update('ghost', **fields)
    return public()


def allow(now=None):
    """False when ghost mode should stay silent."""
    cfg = state()
    if not cfg['aan']:
        return False
    now = time.time() if now is None else float(now)
    if quiet(now, cfg['stil_van'], cfg['stil_tot']):
        return False
    day = time.strftime('%Y-%m-%d', time.localtime(now))
    count = cfg['aantal'] if cfg['dag'] == day else 0
    if count >= cfg['max_per_dag']:
        return False
    if cfg['laatst'] and now - cfg['laatst'] < cfg['minuten'] * 60:
        return False
    return True


def mark(now=None):
    now = time.time() if now is None else float(now)
    day = time.strftime('%Y-%m-%d', time.localtime(now))
    cfg = state()
    count = cfg['aantal'] if cfg['dag'] == day else 0
    kast.update('ghost', dag=day, aantal=count + 1, laatst=now)
    return state()


def candidates(now=None):
    """A few sensible moments. Empty when the data is empty."""
    now = time.time() if now is None else float(now)
    found = []
    try:
        import brein
        for item in brein.list_agenda(6, now=now):
            start = float(item['start'])
            if 0 <= start - now <= 45 * 60:
                mins = max(1, int((start - now) / 60))
                found.append({
                    'key': 'afspraak:%s' % item['id'],
                    'tekst': 'Over %d min: %s.' % (mins, item['titel']),
                })
                break
    except Exception:
        pass
    try:
        import taken
        for task in taken.bord(8).get('taken') or []:
            if task.get('status') == 'geblokkeerd':
                found.append({
                    'key': 'taak:%s' % task['id'],
                    'tekst': 'Een stap staat geblokkeerd: %s.' % (task.get('titel') or 'taak'),
                })
                break
    except Exception:
        pass
    try:
        import doelen
        waiting = doelen.waiting()
        if waiting:
            found.append({
                'key': 'doel:%s' % waiting['id'],
                'tekst': 'Dit doel wacht op een vraag: %s.' % waiting['titel'],
            })
    except Exception:
        pass
    return found


def pick(now=None, items=None):
    now = time.time() if now is None else float(now)
    if not allow(now):
        return None
    items = candidates(now) if items is None else items
    return items[0] if items else None


def public():
    cfg = state()
    return {
        'aan': cfg['aan'],
        'tekst': 'Aan' if cfg['aan'] else 'Uit',
        'stil_van': cfg['stil_van'],
        'stil_tot': cfg['stil_tot'],
        'max_per_dag': cfg['max_per_dag'],
        'uitleg': ('Af en toe een korte suggestie, hoogstens %d per dag, met %d minuten ertussen. '
                   'Stil van %s tot %s. Nooit zeuren: Niet nu en Nooit blijven gelden.') % (
                       cfg['max_per_dag'], cfg['minuten'], cfg['stil_van'], cfg['stil_tot']),
    }
