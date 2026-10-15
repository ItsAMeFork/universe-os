#!/usr/bin/python3
"""One cheap reflection for a recorded task. No tools, no shell, no `claude -p`."""
import json
import sys
import urllib.request

import efficientie
import brein


def _post(spec, opener=None, timeout=20):
    payload = json.dumps(spec['body']).encode()
    request = urllib.request.Request(spec['url'], data=payload, headers=spec['headers'])
    open_url = opener or urllib.request.urlopen
    with open_url(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def run(row_id, poster=None, key='', ollama_url='http://127.0.0.1:11434', provider=None, model=''):
    rows = [row for row in brein.recent_efficientie(40, 'sessie') if row['id'] == int(row_id)]
    if not rows:
        return {'gelukt': False, 'reden': 'weg'}
    row = rows[0]
    provider = provider or row['provider']
    if provider != 'ollama' and not key:
        brein.mark_efficientie(row['id'], 'geen-sleutel')
        return {'gelukt': False, 'reden': 'geen-sleutel'}
    prompt = efficientie.prompt_for(row, provider)
    spec = efficientie.request_for(provider, prompt, key, ollama_url, model or row['model'] or '')
    try:
        payload = poster(spec) if poster else _post(spec)
    except Exception:
        brein.mark_efficientie(row['id'], 'reflectie-mislukt')
        return {'gelukt': False, 'reden': 'reflectie-mislukt'}
    text = efficientie.text_from_response(provider, payload)
    lesson_id = efficientie.store_lesson(text, provider)
    incoming, outgoing, guessed = efficientie.usage_from_response(provider, payload)
    brein.log_efficientie(provider, spec['body'].get('model') or row['model'], incoming, outgoing, guessed,
                          0, 0, 'reflectie', soort='reflectie')
    if lesson_id:
        brein.mark_efficientie(row['id'], '', lesson_id)
        try:
            import patronen
            patronen.attach_lesson(row.get('taak') or '', text)
        except Exception:
            pass
        return {'gelukt': True, 'les': lesson_id}
    brein.mark_efficientie(row['id'], 'geen-les')
    return {'gelukt': False, 'reden': 'geen-les'}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return 0
    try:
        row_id = int(argv[0])
    except ValueError:
        return 0
    try:
        import ai_provider
        provider = ''
        rows = [row for row in brein.recent_efficientie(40, 'sessie') if row['id'] == row_id]
        if rows:
            provider = rows[0]['provider']
        key = ai_provider.key_for(provider) if provider and provider != 'ollama' else ''
        url = ai_provider.load().get('ollama_url') or 'http://127.0.0.1:11434'
        run(row_id, key=key, ollama_url=url, provider=provider or None)
    except Exception:
        return 0
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(0)
