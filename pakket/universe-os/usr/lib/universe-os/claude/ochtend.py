"""Morning briefing for the Brein page.

Read-only. Today's agenda, a short summary of important mail already stored on
this computer, and one local money tip. Sending and paying stay behind the
existing confirmation dialog; this module never calls them.
"""
import time

import brein

MAIL_WINDOW = 36 * 3600
BEVESTIGEN = 'Versturen en betalen vragen om toestemming.'
# Local advice only. No payment, no send, and none of the words the confirmation
# gate treats as an action (betalen, versturen, wachtwoord).
GELDTIPS = (
    'Noteer één bedrag dat deze maand vaker terugkomt dan je dacht, en zet dat bedrag apart.',
    'Vergelijk één abonnement met wat je er de afgelopen maand echt van gebruikte.',
    'Houd een klein bedrag op de gewone rekening en laat de rest op een aparte spaarrekening staan.',
    'Rond een gewone uitgave in je hoofd naar boven af en leg het verschil apart.',
    'Kijk of een vaste last dit jaar is gestegen, en of die stijging nog klopt.',
    'Zet een herinnering voor de dag vóór een incasso, zodat het saldo er al staat.',
    'Kies één winkel waar je deze week niets extra\'s koopt.',
    'Schrijf het bedrag van je eerstvolgende vaste last op, zodat die niet als verrassing komt.',
)


def _midnight(when):
    local = time.localtime(when)
    return time.mktime((local.tm_year, local.tm_mon, local.tm_mday, 0, 0, 0, 0, 0, -1))


def _clock(ts):
    return time.strftime('%H:%M', time.localtime(float(ts)))


def geldtip(now):
    local = time.localtime(now)
    index = local.tm_yday + local.tm_year * 366
    return GELDTIPS[index % len(GELDTIPS)]


def _agenda(now):
    start = _midnight(now)
    end = _midnight(start + 26 * 3600)
    with brein.connect() as db:
        rows = db.execute(
            'SELECT * FROM agenda_items WHERE start < ? AND eind > ? ORDER BY start LIMIT 8',
            (end, start))
        return [{
            'titel': row['titel'], 'plek': row['plek'] or '',
            'van': _clock(row['start']), 'tot': _clock(row['eind']),
        } for row in rows]


def _mail(now):
    since = float(now) - MAIL_WINDOW
    with brein.connect() as db:
        rows = db.execute(
            '''SELECT * FROM mail_items WHERE belangrijk = 1 AND wanneer >= ?
               ORDER BY wanneer DESC LIMIT 5''',
            (since,))
        return [{
            'onderwerp': row['onderwerp'], 'van': row['van'] or '',
            'samenvatting': row['samenvatting'] or '',
            'tijd': time.strftime('%Y-%m-%d %H:%M', time.localtime(float(row['wanneer']))),
        } for row in rows]


def _mail_summary(items):
    if not items:
        return 'Geen belangrijke mail.'
    if len(items) == 1:
        item = items[0]
        return '1 belangrijk bericht: %s' % (item['samenvatting'] or item['onderwerp'] or 'bericht')
    shown = [item['onderwerp'] or 'bericht' for item in items[:3]]
    text = '%d belangrijke berichten: %s' % (len(items), ', '.join(shown))
    extra = len(items) - len(shown)
    if extra:
        text += ' en %d meer' % extra
    return text + '.'


def compose(now=None):
    """Agenda for the local day, recent important mail, and exactly one tip.

    The result has no send or pay action. Callers show it; they do not act on it.
    """
    now = time.time() if now is None else float(now)
    agenda = _agenda(now)
    mail = _mail(now)
    return {
        'dag': time.strftime('%Y-%m-%d', time.localtime(now)),
        'agenda': agenda,
        'agenda_tekst': 'Niets op de agenda vandaag.' if not agenda else '',
        'mail': mail,
        'mail_samenvatting': _mail_summary(mail),
        'geldtip': geldtip(now),
        'bevestigen': BEVESTIGEN,
    }
