"""0.2.39 safety net: windows may never stay hidden when the shell is not running.

New windows start minimised (labwc window rule Iconify, session.VERBORGEN_OPENEN) and the shell shows them after
their portal. This watchdog (started by universe-shell-supervisor, independent of the shell process) checks the
shell heartbeat ($XDG_RUNTIME_DIR/universe-shell-hartslag, written every second by a living shell). When it is
older than session.HARTSLAG_MAX (shell crashed, hangs or is stopped):
  1. rc.xml is rewritten without the Iconify rule and labwc reconfigured, so new windows appear normally;
  2. every minimised window that the user did not minimise himself is shown again.
When the heartbeat is back, the rule is put back. Usage: vensterwacht.py [wacht|vrijgeven]
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import session  # noqa: E402


def log(msg):
    print('[vensterwacht] %s' % msg, flush=True)


def regel_actief():
    try:
        with open(os.path.join(session.config.user_dir(), 'labwc', 'rc.xml'), encoding='utf-8') as f:
            return 'windowRule identifier="*"' in f.read()
    except OSError:
        return False


def zet_regel(aan):
    session.write(verbergen=aan)
    subprocess.run(['labwc', '--reconfigure'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def gebruiker():
    path = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), 'universe-geminimaliseerd.json')
    try:
        with open(path) as f:
            return set(json.load(f))
    except (OSError, ValueError):
        return set()


def toon_verborgen():
    from toplevels import Toplevels
    t = Toplevels(lambda *a: None, log)
    if not t.start():
        return 0
    time.sleep(0.3)
    eigen = gebruiker()
    n = 0
    for w in t.list():
        if w.get('minimized') and '%s\t%s' % (w.get('appId') or '', w.get('title') or '') not in eigen:
            try:
                t.activate(w['id'])
                n += 1
            except Exception as error:  # noqa: BLE001
                log('tonen mislukt: %s' % error)
    time.sleep(0.2)
    return n


def vrijgeven():
    zet_regel(False)
    n = toon_verborgen()
    log('shell draait niet: nieuwe vensters niet meer verborgen, %d verborgen venster(s) getoond' % n)


def wacht():
    """Applies the state itself (write + labwc --reconfigure) on every change: rc.xml may also be written by the
    shell or universe-ctl without a reconfigure, so the file alone does not tell what labwc is using."""
    labwc = os.environ.get('LABWC_PID')
    toegepast = None
    while True:
        if labwc and not os.path.exists('/proc/%s' % labwc):
            return
        leeft = session.shell_leeft()
        if leeft != toegepast or (not leeft and regel_actief()):
            if leeft:
                zet_regel(True)
                log('shell draait: nieuwe vensters wachten op hun portaal')
            else:
                vrijgeven()
            toegepast = leeft
        time.sleep(1)


if __name__ == '__main__':
    {'vrijgeven': vrijgeven}.get(sys.argv[1] if len(sys.argv) > 1 else 'wacht', wacht)()
