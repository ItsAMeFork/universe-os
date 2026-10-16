"""Connected accounts for the assistant: Google, Microsoft, IMAP/SMTP and CalDAV.

Tokens and passwords go to the system keyring (python3-keyring → Secret Service / gnome-keyring).
brein.db only keeps the name, address and scopes. Sending mail and creating events always ask
the user first; there is no parameter that skips the dialog.
"""
import base64
import hashlib
import json
import os
import secrets
import smtplib
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import brein

SERVICE = 'universe-os'
PROVIDERS = {
    'google': {
        'naam': 'Google',
        'device': 'https://oauth2.googleapis.com/device/code',
        'token': 'https://oauth2.googleapis.com/token',
        'auth': 'https://accounts.google.com/o/oauth2/v2/auth',
        'profile': 'https://www.googleapis.com/oauth2/v2/userinfo',
        'scopes': [
            'openid', 'email',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.compose',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events',
        ],
    },
    'microsoft': {
        'naam': 'Microsoft',
        'device': 'https://login.microsoftonline.com/common/oauth2/v2.0/devicecode',
        'token': 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
        'auth': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
        'profile': 'https://graph.microsoft.com/v1.0/me',
        'scopes': ['offline_access', 'User.Read', 'Mail.ReadWrite', 'Mail.Send', 'Calendars.ReadWrite'],
    },
}
SCOPE_LABELS = {
    'openid': 'Aanmelden', 'email': 'E-mailadres', 'offline_access': 'Aangemeld blijven', 'User.Read': 'Profiel',
    'https://www.googleapis.com/auth/gmail.readonly': 'Gmail lezen',
    'https://www.googleapis.com/auth/gmail.compose': 'Gmail-concepten',
    'https://www.googleapis.com/auth/gmail.send': 'Gmail versturen',
    'https://www.googleapis.com/auth/calendar.readonly': 'Agenda lezen',
    'https://www.googleapis.com/auth/calendar.events': 'Agenda bewerken',
    'Mail.ReadWrite': 'Mail lezen en concepten', 'Mail.Send': 'Mail versturen',
    'Calendars.ReadWrite': 'Agenda', 'imap': 'IMAP', 'smtp': 'SMTP', 'caldav': 'CalDAV',
}
_flows = {}
_states = {}
_servers = {}
_store = None


class MemoryKeyring:
    """In-memory stand-in for the system keyring. Tests use this; production never does."""

    def __init__(self):
        self.data = {}

    def set_password(self, service, user, password):
        self.data[(service, user)] = password

    def get_password(self, service, user):
        return self.data.get((service, user))

    def delete_password(self, service, user):
        self.data.pop((service, user), None)


class KeyringStore:
    def __init__(self, backend=None):
        self.backend = backend

    def _backend(self):
        if self.backend is not None:
            return self.backend
        try:
            import keyring
        except ImportError as error:
            raise RuntimeError('De sleutelbos ontbreekt. Installeer python3-keyring en gnome-keyring.') from error
        return keyring

    def put(self, account_id, secret):
        if not isinstance(secret, dict):
            raise ValueError('Geheim moet een object zijn')
        self._backend().set_password(SERVICE, 'koppeling:%s' % account_id, json.dumps(secret))

    def get(self, account_id):
        raw = self._backend().get_password(SERVICE, 'koppeling:%s' % account_id)
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def delete(self, account_id):
        try:
            self._backend().delete_password(SERVICE, 'koppeling:%s' % account_id)
        except Exception:
            return


def set_store(backend):
    """Points secret storage at a keyring-like object. Production leaves this unset."""
    global _store
    _store = backend if hasattr(backend, 'put') else KeyringStore(backend)


def store():
    return _store or KeyringStore()


def _config_path():
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    folder = os.path.join(base, 'universe-os')
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return os.path.join(folder, 'oauth.json')


def _read_clients():
    path = _config_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_clients(data):
    path = _config_path()
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump({key: {'client_id': (value or {}).get('client_id') or ''} for key, value in data.items()},
                  handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def client_id_for(provider):
    return str((_read_clients().get(provider) or {}).get('client_id') or '')


def clients_public():
    data = _read_clients()
    return {name: {'client_id': str((data.get(name) or {}).get('client_id') or '')} for name in PROVIDERS}


def _client_secret(provider):
    blob = store().get('oauth-client:%s' % provider) or {}
    return str(blob.get('client_secret') or '')


def save_client(provider, client_id, client_secret=None):
    if provider not in PROVIDERS:
        raise ValueError('Kies Google of Microsoft')
    client_id = str(client_id or '').strip()
    if not client_id or any(ch in client_id for ch in '\r\n '):
        raise ValueError('Client-id ontbreekt of bevat spaties')
    data = _read_clients()
    data[provider] = {'client_id': client_id}
    _write_clients(data)
    if client_secret:
        store().put('oauth-client:%s' % provider, {'client_secret': str(client_secret)})
    return {'provider': provider, 'client_id': client_id}


def _http(method, url, data=None, headers=None, timeout=25):
    headers = dict(headers or {})
    payload = None
    if isinstance(data, dict):
        if headers.get('Content-Type') == 'application/json':
            payload = json.dumps(data).encode()
        else:
            payload = urllib.parse.urlencode(data).encode()
            headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
    elif isinstance(data, bytes):
        payload = data
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw, status = response.read(), response.status
    except urllib.error.HTTPError as error:
        raw, status = error.read(), error.code
    except urllib.error.URLError as error:
        raise RuntimeError('Geen verbinding met de aanmelddienst.') from error
    try:
        parsed = json.loads(raw.decode() or '{}') if raw else {}
    except ValueError:
        parsed = {}
    return {'status': status, 'json': parsed if isinstance(parsed, dict) else {}, 'body': raw}


def _call(http, method, url, data=None, headers=None):
    fn = http or _http
    return fn(method, url, data, headers)


def _scope_label(scope):
    return SCOPE_LABELS.get(scope, scope)


def list_public():
    rows = []
    for account in brein.list_accounts():
        extra = account.get('extra') or {}
        rows.append({
            'id': account['id'], 'provider': account['provider'], 'naam': account['naam'], 'adres': account['adres'],
            'scopes': [_scope_label(item) for item in account.get('scopes') or []],
            'scope_ids': account.get('scopes') or [],
            'server': extra.get('imap_host') or extra.get('url') or '',
        })
    return rows


def _prune_flows(now):
    # Same 900 s limit as _flow(): an expired flow can never be finished, so drop it together with its state and callback server.
    for old_id in [key for key, old in _flows.items() if now - old['created'] > 900]:
        old = _flows.pop(old_id)
        _states.pop(old.get('state'), None)
        server = _servers.pop(old.get('state'), None)
        if server:
            threading.Thread(target=server.shutdown, daemon=True).start()


def _remember(**fields):
    flow_id = secrets.token_urlsafe(12)
    fields['created'] = time.time()
    _prune_flows(fields['created'])
    _flows[flow_id] = fields
    if fields.get('state'):
        _states[fields['state']] = flow_id
    return flow_id


def _flow(flow_id):
    flow = _flows.get(flow_id)
    if not flow or time.time() - flow['created'] > 900:
        _flows.pop(flow_id, None)
        raise ValueError('Aanmelden is verlopen. Begin opnieuw.')
    return flow


def _serve(state):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got = (query.get('state') or [''])[0]
            flow = _flows.get(_states.get(got))
            # The browser only finishes the flow it was given. The code stays in memory, never in a log line.
            if flow is not None and got == state:
                flow['code'] = (query.get('code') or [''])[0]
                flow['oauth_error'] = (query.get('error') or [''])[0]
            page = ('<!doctype html><meta charset="utf-8"><title>Universe OS</title>'
                    '<p>Je kunt dit venster sluiten en teruggaan naar Accounts.</p>').encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def start_oauth(provider, methode='loopback', client_id='', client_secret=None, http=None, serve=True):
    if provider not in PROVIDERS:
        raise ValueError('Kies Google of Microsoft')
    if methode not in ('device', 'loopback'):
        raise ValueError('Methode moet device of loopback zijn')
    client_id = str(client_id or '').strip() or client_id_for(provider)
    if not client_id:
        raise ValueError('Vul een OAuth-client-id in. Die staat daarna in je configuratie; een clientgeheim gaat naar de sleutelbos.')
    save_client(provider, client_id, client_secret)
    spec = PROVIDERS[provider]
    scope = ' '.join(spec['scopes'])
    if methode == 'device':
        result = _call(http, 'POST', spec['device'], {'client_id': client_id, 'scope': scope})
        body = result.get('json') or {}
        if not body.get('user_code') or not body.get('device_code'):
            raise RuntimeError('Apparaatcode aanvragen mislukt.')
        flow_id = _remember(provider=provider, methode='device', client_id=client_id, device_code=body['device_code'],
                            interval=int(body.get('interval') or 5))
        return {'flow': flow_id, 'methode': 'device', 'user_code': body['user_code'],
                'verificatie': body.get('verification_uri') or body.get('verification_url') or '',
                'interval': int(body.get('interval') or 5)}
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    state = secrets.token_urlsafe(16)
    if serve:
        server, port = _serve(state)
        _servers[state] = server
        redirect = 'http://127.0.0.1:%d/' % port
    else:
        redirect = 'http://127.0.0.1/universe-oauth'
    params = {'client_id': client_id, 'response_type': 'code', 'redirect_uri': redirect, 'scope': scope,
              'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256'}
    if provider == 'google':
        params['access_type'] = 'offline'
        params['prompt'] = 'consent'
    url = spec['auth'] + '?' + urllib.parse.urlencode(params)
    flow_id = _remember(provider=provider, methode='loopback', client_id=client_id, code_verifier=verifier,
                        redirect=redirect, state=state)
    return {'flow': flow_id, 'methode': 'loopback', 'url': url, 'verificatie': url}


def _profile_email(provider, profile):
    if provider == 'google':
        return profile.get('email') or ''
    return profile.get('mail') or profile.get('userPrincipalName') or ''


def _save_tokens(provider, client_id, tokens, profile):
    email = _profile_email(provider, profile) or client_id
    account_id = '%s-%s' % (provider, hashlib.sha256(email.encode()).hexdigest()[:12])
    secret = {
        'refresh_token': tokens.get('refresh_token') or '',
        'access_token': tokens.get('access_token') or '',
        'expires_at': time.time() + int(tokens.get('expires_in') or 3600),
        'client_id': client_id,
        'client_secret': _client_secret(provider),
        'token_url': PROVIDERS[provider]['token'],
    }
    if not secret['access_token']:
        raise RuntimeError('Geen toegangstoken ontvangen.')
    store().put(account_id, secret)
    public = brein.save_account({
        'id': account_id, 'provider': provider, 'naam': profile.get('name') or profile.get('displayName') or email,
        'adres': email, 'scopes': list(PROVIDERS[provider]['scopes']), 'extra': {},
    })
    brein.log_actie('account', 'Gekoppeld: %s' % email, 'uitgevoerd')
    return {'klaar': True, 'account': _public_one(public)}


def _public_one(account):
    return {'id': account['id'], 'provider': account['provider'], 'naam': account['naam'], 'adres': account['adres'],
            'scopes': [_scope_label(item) for item in account.get('scopes') or []]}


def poll_oauth(flow_id, http=None):
    flow = _flow(flow_id)
    spec = PROVIDERS[flow['provider']]
    if flow['methode'] == 'device':
        result = _call(http, 'POST', spec['token'], {
            'client_id': flow['client_id'], 'device_code': flow['device_code'],
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'})
        body = result.get('json') or {}
        if body.get('error') in ('authorization_pending', 'slow_down'):
            return {'klaar': False, 'wacht': 'Wacht tot je de code hebt bevestigd.'}
        if body.get('error'):
            raise RuntimeError('Aanmelden gestopt (%s).' % body.get('error'))
        tokens = body
    else:
        if flow.get('oauth_error'):
            raise RuntimeError('Aanmelden gestopt (%s).' % flow['oauth_error'])
        if not flow.get('code'):
            return {'klaar': False, 'wacht': 'Wacht tot de browser is ingelogd.'}
        form = {'client_id': flow['client_id'], 'code': flow['code'], 'code_verifier': flow['code_verifier'],
                'grant_type': 'authorization_code', 'redirect_uri': flow['redirect']}
        secret = _client_secret(flow['provider'])
        if secret:
            form['client_secret'] = secret
        result = _call(http, 'POST', spec['token'], form)
        tokens = result.get('json') or {}
        if tokens.get('error') or not tokens.get('access_token'):
            raise RuntimeError('Code omwisselen mislukt.')
    profile = _call(http, 'GET', spec['profile'], None, {'Authorization': 'Bearer %s' % tokens['access_token']})
    saved = _save_tokens(flow['provider'], flow['client_id'], tokens, profile.get('json') or {})
    server = _servers.pop(flow.get('state'), None)
    if server:
        threading.Thread(target=server.shutdown, daemon=True).start()
    _flows.pop(flow_id, None)
    return saved


def _host(value):
    host = str(value or '').strip().lower()
    if not host or any(ch in host for ch in ' \r\n/@'):
        raise ValueError('Ongeldige server')
    if not all(ch.isalnum() or ch in '.-' for ch in host):
        raise ValueError('Ongeldige server')
    return host


def _port(value, default):
    try:
        port = int(value if value not in (None, '') else default)
    except (TypeError, ValueError):
        raise ValueError('Ongeldige poort')
    if not 1 <= port <= 65535:
        raise ValueError('Ongeldige poort')
    return port


def _header(value, label):
    text = str(value or '').strip()
    if not text:
        raise ValueError('%s ontbreekt' % label)
    if any(ch in text for ch in '\r\n'):
        raise ValueError('%s mag geen nieuwe regel bevatten' % label)
    return text[:300]


def _addresses(value):
    if isinstance(value, str):
        value = [part.strip() for part in value.replace(';', ',').split(',')]
    if not isinstance(value, (list, tuple)):
        raise ValueError('Ontvangers moeten een lijst zijn')
    found = []
    for item in value:
        item = str(item).strip()
        if not item or any(ch in item for ch in '\r\n\t '):
            raise ValueError('Ongeldig adres')
        if item.count('@') != 1 or item.startswith('@') or item.endswith('@'):
            raise ValueError('Ongeldig adres')
        found.append(item)
    if not found:
        raise ValueError('Geen ontvanger')
    if len(found) > 50:
        raise ValueError('Te veel ontvangers')
    return found


def add_imap(naam, adres, imap_host, smtp_host, user, password, imap_port=993, smtp_port=465):
    if not password:
        raise ValueError('Wachtwoord ontbreekt')
    adres = _addresses([adres])[0]
    extra = {'imap_host': _host(imap_host), 'imap_port': _port(imap_port, 993), 'smtp_host': _host(smtp_host),
             'smtp_port': _port(smtp_port, 465), 'user': str(user or adres)[:200]}
    account_id = 'imap-%s' % hashlib.sha256(adres.encode()).hexdigest()[:12]
    store().put(account_id, {'password': str(password)})
    public = brein.save_account({'id': account_id, 'provider': 'imap', 'naam': str(naam or adres)[:200],
                                 'adres': adres, 'scopes': ['imap', 'smtp'], 'extra': extra})
    brein.log_actie('account', 'IMAP gekoppeld: %s' % adres, 'uitgevoerd')
    return _public_one(public)


def add_caldav(naam, adres, url, user, password):
    if not password:
        raise ValueError('Wachtwoord ontbreekt')
    adres = _addresses([adres])[0]
    clean = str(url or '').strip()
    if not clean.startswith('https://') or any(ch in clean for ch in '\r\n '):
        raise ValueError('CalDAV-adres moet met https:// beginnen')
    extra = {'url': clean[:500], 'user': str(user or adres)[:200]}
    account_id = 'caldav-%s' % hashlib.sha256(adres.encode()).hexdigest()[:12]
    store().put(account_id, {'password': str(password)})
    public = brein.save_account({'id': account_id, 'provider': 'caldav', 'naam': str(naam or adres)[:200],
                                 'adres': adres, 'scopes': ['caldav'], 'extra': extra})
    brein.log_actie('account', 'CalDAV gekoppeld: %s' % adres, 'uitgevoerd')
    return _public_one(public)


def disconnect(account_id):
    if not brein.get_account(account_id):
        raise ValueError('Account niet gevonden')
    store().delete(account_id)
    brein.delete_account(account_id)
    brein.log_actie('account', 'Ontkoppeld %s' % account_id, 'uitgevoerd')
    return {'ontkoppeld': account_id}


def _need(account_id, providers):
    rows = [row for row in brein.list_accounts() if row['provider'] in providers]
    if account_id:
        rows = [row for row in rows if row['id'] == account_id]
        if not rows:
            raise ValueError('Account niet gevonden of niet geschikt')
    if not rows:
        raise RuntimeError('Geen geschikt account. Koppel er een in Controlecentrum → Accounts.')
    return rows


def _one(rows, account_id):
    if account_id:
        return rows[0]
    if len(rows) == 1:
        return rows[0]
    raise ValueError('Meerdere accounts. Kies er een met "account".')


def _secret(account):
    blob = store().get(account['id'])
    if not blob:
        raise RuntimeError('Geen sleutel voor dit account. Koppel het opnieuw.')
    return blob


def _access(account, secret, http):
    if secret.get('access_token') and float(secret.get('expires_at') or 0) > time.time() + 30:
        return secret['access_token']
    if not secret.get('refresh_token'):
        raise RuntimeError('Aanmelding verlopen. Koppel het account opnieuw.')
    form = {'client_id': secret.get('client_id') or client_id_for(account['provider']),
            'grant_type': 'refresh_token', 'refresh_token': secret['refresh_token']}
    if secret.get('client_secret'):
        form['client_secret'] = secret['client_secret']
    result = _call(http, 'POST', secret.get('token_url') or PROVIDERS[account['provider']]['token'], form)
    token = (result.get('json') or {}).get('access_token')
    if not token:
        raise RuntimeError('Aanmelding vernieuwen mislukt. Koppel het account opnieuw.')
    secret['access_token'] = token
    secret['expires_at'] = time.time() + int((result.get('json') or {}).get('expires_in') or 3600)
    store().put(account['id'], secret)
    return token


def _auth(token):
    return {'Authorization': 'Bearer %s' % token}


def _sync_mail(account_id, rows):
    for row in rows:
        brein.upsert_mail(account_id, row.get('id') or row.get('onderwerp'), row.get('onderwerp'), row.get('van'),
                          row.get('samenvatting'), belangrijk=1)


def _gmail_headers(payload):
    headers = {}
    for item in (payload or {}).get('headers') or []:
        headers[str(item.get('name') or '').lower()] = item.get('value') or ''
    return headers


def _gmail_search(account, secret, query, limit, http):
    token = _access(account, secret, http)
    params = urllib.parse.urlencode({'q': query or 'is:important newer_than:14d', 'maxResults': str(limit)})
    listed = _call(http, 'GET', 'https://gmail.googleapis.com/gmail/v1/users/me/messages?' + params, None, _auth(token))
    found = []
    for item in ((listed.get('json') or {}).get('messages') or [])[:limit]:
        mid = urllib.parse.quote(str(item.get('id') or ''))
        detail = _call(http, 'GET', 'https://gmail.googleapis.com/gmail/v1/users/me/messages/%s?format=metadata&metadataHeaders=Subject&metadataHeaders=From' % mid,
                       None, _auth(token))
        body = detail.get('json') or {}
        headers = _gmail_headers(body.get('payload'))
        found.append({'id': item.get('id'), 'account': account['id'], 'onderwerp': headers.get('subject', ''),
                      'van': headers.get('from', ''), 'samenvatting': body.get('snippet') or ''})
    return found


def _graph_addr(value):
    email = ((value or {}).get('emailAddress') or {})
    return email.get('address') or email.get('name') or ''


def _graph_search(account, secret, query, limit, http):
    token = _access(account, secret, http)
    url = 'https://graph.microsoft.com/v1.0/me/messages?$top=%d&$select=id,subject,from,bodyPreview' % limit
    if query:
        url += '&$search=' + urllib.parse.quote('"%s"' % query.replace('"', ''))
    listed = _call(http, 'GET', url, None, _auth(token))
    found = []
    for item in ((listed.get('json') or {}).get('value') or [])[:limit]:
        found.append({'id': item.get('id'), 'account': account['id'], 'onderwerp': item.get('subject') or '',
                      'van': _graph_addr(item.get('from')), 'samenvatting': item.get('bodyPreview') or ''})
    return found


def _imap_search(account, secret, query, limit, factory):
    import imaplib
    factory = factory or imaplib.IMAP4_SSL
    extra = account.get('extra') or {}
    client = factory(extra['imap_host'], int(extra.get('imap_port') or 993))
    try:
        client.login(extra.get('user') or account['adres'], secret.get('password') or '')
        client.select('INBOX')
        criteria = ['TEXT', query] if query else ['ALL']
        _typ, data = client.search(None, *criteria)
        numbers = (data[0] or b'').split()[-limit:]
        found = []
        for number in numbers:
            _typ, fetched = client.fetch(number, '(RFC822)')
            raw = b''
            for part in fetched or []:
                if isinstance(part, tuple) and len(part) > 1:
                    raw = part[1]
            message = EmailMessage()
            if raw:
                from email import message_from_bytes
                message = message_from_bytes(raw)
            found.append({'id': number.decode() if isinstance(number, bytes) else str(number), 'account': account['id'],
                          'onderwerp': str(message.get('subject') or ''), 'van': str(message.get('from') or ''),
                          'samenvatting': _plain(message)[:240]})
        return found
    finally:
        try:
            client.logout()
        except Exception:
            pass


def _plain(message):
    if message.get_content_type() == 'text/plain':
        try:
            return message.get_content()
        except Exception:
            return ''
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == 'text/plain':
                try:
                    return part.get_content()
                except Exception:
                    continue
    return ''


def search_mail(query='', account=None, limit=8, http=None, imap_factory=None):
    limit = max(1, min(int(limit or 8), 20))
    rows = _need(account, ('google', 'microsoft', 'imap'))
    found = []
    for item in rows:
        secret = _secret(item)
        if item['provider'] == 'google':
            batch = _gmail_search(item, secret, query, limit, http)
        elif item['provider'] == 'microsoft':
            batch = _graph_search(item, secret, query, limit, http)
        else:
            batch = _imap_search(item, secret, query, limit, imap_factory)
        _sync_mail(item['id'], batch)
        found.extend(batch)
    brein.log_actie('mail_search', '%d berichten (%s)' % (len(found), (query or 'recent')[:80]), 'uitgevoerd')
    return found[:limit]


def read_mail(account, message_id, http=None, imap_factory=None):
    rows = _need(account, ('google', 'microsoft', 'imap'))
    item = _one(rows, account)
    secret = _secret(item)
    message_id = str(message_id or '').strip()
    if not message_id:
        raise ValueError('Bericht-id ontbreekt')
    if item['provider'] == 'google':
        token = _access(item, secret, http)
        detail = _call(http, 'GET', 'https://gmail.googleapis.com/gmail/v1/users/me/messages/%s?format=full' % urllib.parse.quote(message_id),
                       None, _auth(token))
        body = detail.get('json') or {}
        headers = _gmail_headers(body.get('payload'))
        text = body.get('snippet') or ''
        row = {'id': message_id, 'account': item['id'], 'onderwerp': headers.get('subject', ''),
               'van': headers.get('from', ''), 'tekst': text, 'samenvatting': text[:240]}
    elif item['provider'] == 'microsoft':
        token = _access(item, secret, http)
        detail = _call(http, 'GET', 'https://graph.microsoft.com/v1.0/me/messages/%s' % urllib.parse.quote(message_id),
                       None, _auth(token))
        body = detail.get('json') or {}
        text = ((body.get('body') or {}).get('content')) or body.get('bodyPreview') or ''
        row = {'id': message_id, 'account': item['id'], 'onderwerp': body.get('subject') or '',
               'van': _graph_addr(body.get('from')), 'tekst': text, 'samenvatting': (body.get('bodyPreview') or text)[:240]}
    else:
        matches = [row for row in _imap_search(item, secret, '', 50, imap_factory) if str(row['id']) == message_id]
        if not matches:
            raise ValueError('Bericht niet gevonden')
        row = dict(matches[0])
        row['tekst'] = row.get('samenvatting') or ''
    _sync_mail(item['id'], [row])
    brein.log_actie('mail_read', 'Gelezen: %s' % (row.get('onderwerp') or message_id)[:180], 'uitgevoerd')
    return row


def _message(account, recipients, subject, body):
    message = EmailMessage()
    message['To'] = ', '.join(recipients)
    message['Subject'] = subject
    message['From'] = account.get('adres') or ''
    message.set_content(str(body or ''))
    return message


def _raw(message):
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


def draft_mail(account=None, to=None, subject='', body='', http=None, imap_factory=None):
    recipients = _addresses(to) if to else []
    subject = _header(subject, 'Onderwerp')
    rows = _need(account, ('google', 'microsoft', 'imap'))
    item = _one(rows, account)
    secret = _secret(item)
    message = _message(item, recipients or [item['adres']], subject, body)
    if item['provider'] == 'google':
        token = _access(item, secret, http)
        _call(http, 'POST', 'https://gmail.googleapis.com/gmail/v1/users/me/drafts',
              {'message': {'raw': _raw(message)}}, {'Authorization': 'Bearer %s' % token, 'Content-Type': 'application/json'})
    elif item['provider'] == 'microsoft':
        token = _access(item, secret, http)
        _call(http, 'POST', 'https://graph.microsoft.com/v1.0/me/messages', {
            'subject': subject, 'body': {'contentType': 'Text', 'content': str(body or '')},
            'toRecipients': [{'emailAddress': {'address': addr}} for addr in recipients]},
              {'Authorization': 'Bearer %s' % token, 'Content-Type': 'application/json'})
    else:
        _imap_append(item, secret, message, imap_factory)
    brein.log_actie('mail_draft', 'Concept: %s' % subject, 'uitgevoerd')
    return {'concept': True, 'onderwerp': subject}


def _imap_append(account, secret, message, factory):
    import imaplib
    factory = factory or imaplib.IMAP4_SSL
    extra = account.get('extra') or {}
    client = factory(extra['imap_host'], int(extra.get('imap_port') or 993))
    try:
        client.login(extra.get('user') or account['adres'], secret.get('password') or '')
        client.append('Drafts', '(\\Draft)', None, message.as_bytes())
    finally:
        try:
            client.logout()
        except Exception:
            pass


def _deliver(item, recipients, subject, body, http, smtp_factory):
    secret = _secret(item)
    message = _message(item, recipients, subject, body)
    if item['provider'] == 'google':
        token = _access(item, secret, http)
        _call(http, 'POST', 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
              {'raw': _raw(message)}, {'Authorization': 'Bearer %s' % token, 'Content-Type': 'application/json'})
        return
    if item['provider'] == 'microsoft':
        token = _access(item, secret, http)
        _call(http, 'POST', 'https://graph.microsoft.com/v1.0/me/sendMail', {
            'message': {'subject': subject, 'body': {'contentType': 'Text', 'content': str(body or '')},
                        'toRecipients': [{'emailAddress': {'address': addr}} for addr in recipients]},
            'saveToSentItems': True}, {'Authorization': 'Bearer %s' % token, 'Content-Type': 'application/json'})
        return
    factory = smtp_factory or smtplib.SMTP_SSL
    extra = item.get('extra') or {}
    client = factory(extra['smtp_host'], int(extra.get('smtp_port') or 465), timeout=25)
    try:
        client.login(extra.get('user') or item['adres'], secret.get('password') or '')
        client.send_message(message)
    finally:
        try:
            client.quit()
        except Exception:
            pass


def _mail_packet(to, subject, body):
    recipients = _addresses(to)
    subject = _header(subject, 'Onderwerp')
    body = str(body or '')
    if len(body) > 100000:
        raise ValueError('Bericht is te lang')
    summary = 'Naar %s: %s' % (', '.join(recipients), subject)
    full = 'Ontvangers: %s\nOnderwerp: %s\n\n%s' % (', '.join(recipients), subject, body)
    return recipients, subject, body, summary, full


def _release_mail(recipients, subject, body, summary, full, confirmer, bijlagen, vlag, deliver):
    """Ordinary short mail to a known person can leave while auto-accept is on.

    Important mail, and every send while auto-accept is off, still needs the dialog.
    deliver is None when the message goes out through the signed-in browser instead of SMTP.
    """
    import auto_accept
    kind, reasons = auto_accept.mail_decision(recipients, subject, body, bijlagen=bijlagen, vlag=vlag)
    why = ('\n\nDit blijft een vraag: %s.' % ', '.join(reasons)) if reasons else ''
    if kind == 'automatisch':
        if deliver is not None:
            deliver()
        auto_accept.remember_addresses(recipients)
        brein.log_actie('mail_send', summary, 'automatisch', full, volledig=True)
        return {'verstuurd': deliver is not None, 'mag': True, 'automatisch': True,
                'naar': recipients, 'onderwerp': subject, 'via': 'account' if deliver else 'browser'}
    if kind == 'wacht':
        brein.log_actie('mail_send', summary, 'wacht', full + why, volledig=True)
        raise PermissionError('Uitgesteld tot je terug bent. De mail staat in het brein onder Acties.')
    preview = full[:4000] + why
    if confirmer is None or not confirmer('Claude wil een e-mail versturen', preview):
        import confirm
        if not confirm.deferred():
            brein.log_actie('mail_send', summary, 'geweigerd', full[:4000])
        raise PermissionError(confirm.refused_message('Versturen geannuleerd. Er is niets verzonden.'))
    if deliver is not None:
        deliver()
    auto_accept.remember_addresses(recipients)
    brein.log_actie('mail_send', summary, 'goedgekeurd', full, volledig=True)
    return {'verstuurd': deliver is not None, 'mag': True, 'automatisch': False,
            'naar': recipients, 'onderwerp': subject, 'via': 'account' if deliver else 'browser'}


def authorize_browser(to=None, subject='', body='', confirmer=None, bijlagen=0, vlag=False):
    """Lets Claude press Send in Chrome after the same gate. Nothing is sent from this process."""
    recipients, subject, body, summary, full = _mail_packet(to, subject, body)
    return _release_mail(recipients, subject, body, summary, full, confirmer, bijlagen, vlag, None)


def send_mail(account=None, to=None, subject='', body='', confirmer=None, http=None, smtp_factory=None, bijlagen=0, vlag=False):
    """Sends through a linked account only after the mail gate says yes. No confirmer means no send, unless auto-accept covers an ordinary reply."""
    recipients, subject, body, summary, full = _mail_packet(to, subject, body)
    item = _one(_need(account, ('google', 'microsoft', 'imap')), account)

    def deliver():
        try:
            _deliver(item, recipients, subject, body, http, smtp_factory)
        except PermissionError:
            raise
        except Exception as error:
            brein.log_actie('mail_send', summary, 'mislukt')
            raise RuntimeError('Versturen mislukt.') from error

    return _release_mail(recipients, subject, body, summary, full, confirmer, bijlagen, vlag, deliver)


def _timestamp(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value or '').strip()
    if not text:
        raise ValueError('Tijd ontbreekt')
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        import datetime
        return datetime.datetime.fromisoformat(text).timestamp()
    except ValueError:
        pass
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            return time.mktime(time.strptime(str(value).strip(), fmt))
        except ValueError:
            continue
    raise ValueError('Tijd niet begrepen. Gebruik 2026-10-14 09:00.')


def _iso(ts):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(float(ts)))


def _when_text(ts):
    return time.strftime('%Y-%m-%d %H:%M', time.localtime(float(ts)))


def _google_events(account, secret, http):
    token = _access(account, secret, http)
    params = urllib.parse.urlencode({'timeMin': _iso(time.time()), 'singleEvents': 'true', 'orderBy': 'startTime', 'maxResults': '12'})
    result = _call(http, 'GET', 'https://www.googleapis.com/calendar/v3/calendars/primary/events?' + params, None, _auth(token))
    found = []
    for item in ((result.get('json') or {}).get('items') or []):
        start = ((item.get('start') or {}).get('dateTime')) or ((item.get('start') or {}).get('date'))
        end = ((item.get('end') or {}).get('dateTime')) or ((item.get('end') or {}).get('date')) or start
        found.append({'id': item.get('id'), 'account': account['id'], 'titel': item.get('summary') or '',
                      'start': _timestamp(start), 'eind': _timestamp(end), 'plek': item.get('location') or ''})
    return found


def _graph_events(account, secret, http):
    token = _access(account, secret, http)
    start, end = _iso(time.time()), _iso(time.time() + 30 * 86400)
    url = 'https://graph.microsoft.com/v1.0/me/calendarView?startDateTime=%s&endDateTime=%s&$top=12' % (urllib.parse.quote(start), urllib.parse.quote(end))
    result = _call(http, 'GET', url, None, _auth(token))
    found = []
    for item in ((result.get('json') or {}).get('value') or []):
        start_at = ((item.get('start') or {}).get('dateTime'))
        end_at = ((item.get('end') or {}).get('dateTime')) or start_at
        found.append({'id': item.get('id'), 'account': account['id'], 'titel': item.get('subject') or '',
                      'start': _timestamp(start_at), 'eind': _timestamp(end_at), 'plek': ((item.get('location') or {}).get('displayName')) or ''})
    return found


def _ics_time(value):
    import datetime
    text = str(value or '').strip()
    if not text:
        return None
    if text.endswith('Z'):
        try:
            parsed = datetime.datetime.strptime(text, '%Y%m%dT%H%M%SZ').replace(tzinfo=datetime.timezone.utc)
            return parsed.timestamp()
        except ValueError:
            return None
    for fmt in ('%Y%m%dT%H%M%S', '%Y%m%d'):
        try:
            return time.mktime(time.strptime(text, fmt))
        except ValueError:
            continue
    return None


def _parse_ics(text):
    found = []
    for chunk in str(text or '').split('BEGIN:VEVENT')[1:]:
        body = chunk.split('END:VEVENT')[0]
        fields = {}
        for line in body.splitlines():
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            fields[key.split(';')[0].upper()] = value.strip()
        if not fields.get('SUMMARY'):
            continue
        start = _ics_time(fields.get('DTSTART')) or time.time()
        found.append({'id': fields.get('UID') or fields['SUMMARY'], 'titel': fields['SUMMARY'], 'start': start,
                      'eind': _ics_time(fields.get('DTEND')) or start + 3600, 'plek': fields.get('LOCATION') or ''})
    return found


_REPORT = '''<?xml version="1.0" encoding="utf-8" ?>
<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"><d:prop><d:getetag/><c:calendar-data/></d:prop>
<c:filter><c:comp-filter name="VCALENDAR"><c:comp-filter name="VEVENT"/></c:comp-filter></c:filter></c:calendar-query>'''


def _basic(user, password):
    token = base64.b64encode(('%s:%s' % (user, password)).encode()).decode()
    return {'Authorization': 'Basic %s' % token, 'Depth': '1', 'Content-Type': 'application/xml; charset=utf-8'}


def _urllib_opener(account, secret):
    extra = account.get('extra') or {}
    headers = _basic(extra.get('user') or account['adres'], secret.get('password') or '')

    def opener(method, url, data, extra_headers):
        merged = dict(headers)
        merged.update(extra_headers or {})
        result = _http(method, url, data.encode() if isinstance(data, str) else data, merged)
        return result['status'], (result.get('body') or b'').decode('utf-8', 'replace')
    return opener


def _caldav_library(account, secret, ics=None):
    import caldav
    extra = account.get('extra') or {}
    client = caldav.DAVClient(url=extra['url'], username=extra.get('user') or account['adres'], password=secret.get('password') or '')
    calendars = client.principal().calendars()
    if not calendars:
        return []
    if ics is not None:
        calendars[0].save_event(ics)
        return []
    import datetime
    start = datetime.datetime.now(datetime.timezone.utc)
    events = calendars[0].date_search(start, start + datetime.timedelta(days=30))
    found = []
    for event in events:
        found.extend(_parse_ics(getattr(event, 'data', '') or ''))
    return found


def _caldav_events(account, secret, opener=None):
    if opener is None:
        try:
            return _caldav_library(account, secret)
        except ImportError:
            opener = _urllib_opener(account, secret)
        except Exception:
            opener = _urllib_opener(account, secret)
    _status, text = opener('REPORT', (account.get('extra') or {})['url'], _REPORT, {'Depth': '1'})
    return _parse_ics(text)


def _sync_agenda(account_id, rows):
    for row in rows:
        brein.upsert_agenda(account_id, row.get('id') or row.get('titel'), row.get('titel'), row['start'], row['eind'], row.get('plek') or '')


def list_events(account=None, http=None, opener=None):
    rows = _need(account, ('google', 'microsoft', 'caldav'))
    found = []
    for item in rows:
        secret = _secret(item)
        if item['provider'] == 'google':
            batch = _google_events(item, secret, http)
        elif item['provider'] == 'microsoft':
            batch = _graph_events(item, secret, http)
        else:
            batch = _caldav_events(item, secret, opener)
            for event in batch:
                event['account'] = item['id']
        _sync_agenda(item['id'], batch)
        found.extend(batch)
    brein.log_actie('calendar_list', '%d afspraken' % len(found), 'uitgevoerd')
    return found


def _ics(uid, titel, start, end, plek):
    def stamp(ts):
        return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime(float(ts)))
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Universe OS//Assistent//NL', 'BEGIN:VEVENT',
             'UID:%s' % uid, 'DTSTAMP:%s' % stamp(time.time()), 'DTSTART:%s' % stamp(start), 'DTEND:%s' % stamp(end),
             'SUMMARY:%s' % titel.replace('\n', ' ')]
    if plek:
        lines.append('LOCATION:%s' % str(plek).replace('\n', ' '))
    lines += ['END:VEVENT', 'END:VCALENDAR']
    return '\r\n'.join(lines) + '\r\n'


def _create_remote(item, titel, start, end, plek, http, opener):
    secret = _secret(item)
    if item['provider'] == 'google':
        token = _access(item, secret, http)
        result = _call(http, 'POST', 'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                       {'summary': titel, 'location': plek, 'start': {'dateTime': _iso(start)}, 'end': {'dateTime': _iso(end)}},
                       {'Authorization': 'Bearer %s' % token, 'Content-Type': 'application/json'})
        return (result.get('json') or {}).get('id') or titel
    if item['provider'] == 'microsoft':
        token = _access(item, secret, http)
        result = _call(http, 'POST', 'https://graph.microsoft.com/v1.0/me/events',
                       {'subject': titel, 'location': {'displayName': plek},
                        'start': {'dateTime': _iso(start), 'timeZone': 'UTC'}, 'end': {'dateTime': _iso(end), 'timeZone': 'UTC'}},
                       {'Authorization': 'Bearer %s' % token, 'Content-Type': 'application/json'})
        return (result.get('json') or {}).get('id') or titel
    uid = 'universe-%s' % secrets.token_hex(8)
    ics = _ics(uid, titel, start, end, plek)
    if opener is None:
        try:
            _caldav_library(item, secret, ics)
            return uid
        except ImportError:
            opener = _urllib_opener(item, secret)
        except Exception:
            opener = _urllib_opener(item, secret)
    url = (item.get('extra') or {})['url'].rstrip('/') + '/' + uid + '.ics'
    opener('PUT', url, ics, {'Content-Type': 'text/calendar; charset=utf-8'})
    return uid


def create_event(account=None, titel='', start=None, eind=None, plek='', confirmer=None, http=None, opener=None):
    """Creates an event only after confirmer(title, text) returns True."""
    titel = _header(titel, 'Titel')
    start_ts = _timestamp(start)
    end_ts = _timestamp(eind) if eind not in (None, '') else start_ts + 3600
    if end_ts < start_ts:
        raise ValueError('Einde ligt voor het begin')
    plek = str(plek or '').replace('\r', '').replace('\n', ' ')[:200]
    item = _one(_need(account, ('google', 'microsoft', 'caldav')), account)
    summary = 'Afspraak: %s' % titel
    preview = 'Titel: %s\nBegin: %s\nEinde: %s\nPlek: %s' % (titel, _when_text(start_ts), _when_text(end_ts), plek or '—')
    if confirmer is None or not confirmer('Claude wil een afspraak maken', preview):
        import confirm
        if not confirm.deferred():
            brein.log_actie('calendar_create', summary, 'geweigerd')
        raise PermissionError(confirm.refused_message('Afspraak geannuleerd. Er is niets gezet.'))
    try:
        extern = _create_remote(item, titel, start_ts, end_ts, plek, http, opener)
    except PermissionError:
        raise
    except Exception as error:
        brein.log_actie('calendar_create', summary, 'mislukt')
        raise RuntimeError('Afspraak maken mislukt.') from error
    brein.upsert_agenda(item['id'], extern, titel, start_ts, end_ts, plek)
    brein.log_actie('calendar_create', summary, 'goedgekeurd')
    return {'gemaakt': True, 'titel': titel, 'id': extern}
