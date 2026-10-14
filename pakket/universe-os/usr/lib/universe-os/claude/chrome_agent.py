"""Google Chrome plus the official Claude in Chrome extension.

Claude Code reaches the user's signed-in browser with `claude --chrome`. There is
no OAuth client for Gmail or Outlook: the person logs in in Chrome. Reading,
drafting, sorting, research and form filling are ordinary browser work. Sending,
paying, deleting and passwords stay behind a confirmation.
"""
import glob
import json
import os
import re
import shutil

EXTENSION_ID = 'fcoeoabgfenejglbffodgkkbkcdhcgfn'
STORE_URL = 'https://chromewebstore.google.com/detail/claude/' + EXTENSION_ID
HOST_FILE = 'com.anthropic.claude_code_browser_extension.json'
APT_LINE = 'deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux.gpg] https://dl.google.com/linux/chrome/deb/ stable main'


def binary(which=None):
    which = which or shutil.which
    for name in ('google-chrome-stable', 'google-chrome'):
        found = which(name)
        if found and 'openclaude' not in found.lower():
            return found
    return None


def _config_root(home=None):
    home = home or os.path.expanduser('~')
    return os.path.join(home, '.config', 'google-chrome')


def extension_installed(home=None):
    root = _config_root(home)
    pattern = os.path.join(root, '*', 'Extensions', EXTENSION_ID)
    return bool(glob.glob(pattern))


def host_installed(home=None):
    path = os.path.join(_config_root(home), 'NativeMessagingHosts', HOST_FILE)
    return os.path.isfile(path)


def status(home=None, which=None):
    """What the AI page can show without starting a session."""
    chrome = binary(which) is not None
    extension = extension_installed(home) if chrome or True else False
    if not chrome:
        extension = extension_installed(home)
    host = host_installed(home)
    connected = bool(chrome and extension and host)
    if connected:
        tekst = 'Verbonden. Claude gebruikt jouw aangemelde Chrome. Log gewoon in in Gmail of Outlook.'
    elif chrome and extension:
        tekst = 'De extensie staat er. Open het AI-paneel; Claude maakt de verbinding met --chrome.'
    elif chrome:
        tekst = 'Chrome staat er. Voeg de officiële Claude-extensie toe en log in met je Claude-account.'
    else:
        tekst = 'Chrome ontbreekt nog. De knop installeert het uit de officiële bron van Google en opent de extensie.'
    return {
        'chrome': chrome, 'extensie': bool(extension), 'host': bool(host), 'verbonden': connected,
        'tekst': tekst, 'winkel': STORE_URL, 'extensie_id': EXTENSION_ID,
    }


def install_script():
    """Official Google apt repository, then the extension page. Shown in a terminal after confirmation."""
    url = STORE_URL
    return (
        'set -e\n'
        'echo "Chrome komt van de officiële apt-bron van Google (dl.google.com)."\n'
        'curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor | sudo tee /usr/share/keyrings/google-linux.gpg >/dev/null\n'
        'echo "%s" | sudo tee /etc/apt/sources.list.d/google-chrome.list\n'
        'sudo apt-get update\n'
        'sudo apt-get install -y google-chrome-stable\n'
        'echo "Klaar. De pagina van Claude in Chrome opent zo."\n'
        'google-chrome-stable %s || xdg-open %s\n'
        'echo "Druk op Enter om dit venster te sluiten."\n'
        'read -r _\n'
    ) % (APT_LINE, url, url)


def plan_setup(chrome_present):
    """What the confirmed button runs. No apt and no browser until the caller spawns it."""
    if chrome_present:
        return {'script': '', 'open': [binary() or 'google-chrome', STORE_URL], 'url': STORE_URL}
    return {'script': install_script(), 'open': [], 'url': STORE_URL}


def judge_browser(tool, payload):
    """uitgevoerd, automatisch, or wacht. Sending still needs a fresh mail_send approval."""
    name = str(tool or '')
    if name.startswith('mcp__universe__'):
        return 'vraag', name, ''
    low = name.lower()
    if 'chrome' not in low and 'claude-in-chrome' not in low and not low.startswith('browser'):
        return 'vraag', name, ''
    text = payload if isinstance(payload, str) else json.dumps(payload or {}, ensure_ascii=False)
    if re.search(r'wachtwoord|password|\bpin\b', text, re.I):
        return 'wacht', name[:180], 'Tekst niet opgeslagen.'
    if re.search(r'betalen|betaal|payment|purchase|aankoop|verwijder|delete|\bwissen\b|prullenbak', text, re.I):
        return 'wacht', name[:180], text[:500]
    if re.search(r'versturen|verstuur|verzend|verzenden|\bsend\b', text, re.I):
        import auto_accept
        if auto_accept.recent_mail_ok():
            return 'automatisch', name[:180], text[:500]
        return 'wacht', name[:180], 'Versturen in de browser vraagt eerst mail_send, zodat de tekst in Acties staat.'
    return 'uitgevoerd', name[:180], text[:500]
