"""Desk features the AI page turns on and off: screen history, voice, briefing, ghost, goals."""
import briefing
import doelen
import ghost
import schermgeschiedenis
import stem


def public():
    return {
        'scherm': schermgeschiedenis.public(),
        'stem': stem.public(),
        'briefing': briefing.public(),
        'ghost': ghost.public(),
        'doelen': doelen.public(),
    }


def apply(args):
    args = args if isinstance(args, dict) else {}
    deel = str(args.get('deel') or '')
    if deel == 'scherm':
        if args.get('wissen'):
            return schermgeschiedenis.clear()
        return schermgeschiedenis.configure(args)
    if deel == 'stem':
        return stem.configure(args)
    if deel == 'briefing':
        return briefing.configure(args)
    if deel == 'ghost':
        return ghost.configure(args)
    if deel == 'doelen':
        if 'achtergrond' in args:
            doelen.set_background(args.get('achtergrond'))
        if str(args.get('titel') or '').strip():
            doelen.add(args.get('titel'))
        return doelen.public()
    raise ValueError('Kies scherm, stem, briefing, ghost of doelen.')
