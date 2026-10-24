"""Screenshots of the Accounts page and the Brein list, with mocked data.

Exits 0 without a browser (the contract test does not need pixels). When Chromium
is installed it writes PNGs next to this script and under /opt/cursor/artifacts.
Headless Chrome on this image often keeps running after --screenshot; the script
stops it once the PNG is written.
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PREVIEWS = {
    'accounts': OUT / 'preview' / 'accounts.html',
    'brein': OUT / 'preview' / 'brein.html',
    'ai': OUT / 'preview' / 'ai.html',
    'internet': OUT / 'preview' / 'internet.html',
}
BROWSER = next((shutil.which(name) for name in (
    'chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable')
    if shutil.which(name)), None)
ARTIFACTS = Path('/opt/cursor/artifacts/screenshots')


def _shot(browser, url, dest, profile):
    dest.unlink(missing_ok=True)
    proc = subprocess.Popen(
        [browser, '--headless=new', '--disable-gpu', '--hide-scrollbars',
         '--no-sandbox', '--disable-dev-shm-usage', '--no-first-run',
         '--no-default-browser-check', '--force-device-scale-factor=1',
         '--window-size=1280,800', '--virtual-time-budget=5000',
         '--user-data-dir=' + str(profile), '--screenshot=' + str(dest), url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    deadline = time.time() + 25
    stable = 0
    last = -1
    try:
        while time.time() < deadline:
            if dest.is_file():
                size = dest.stat().st_size
                if size > 8000 and size == last:
                    stable += 1
                    if stable >= 2:
                        return
                else:
                    stable = 0
                last = size
            if proc.poll() is not None:
                if dest.is_file() and dest.stat().st_size > 8000:
                    return
                raise RuntimeError('browser stopte zonder schermafbeelding: %s' % dest.name)
            time.sleep(0.4)
        raise RuntimeError('timeout op schermafbeelding: %s' % dest.name)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(5)


def main():
    if not BROWSER:
        print('SKIP: geen headless browser, schermafbeeldingen niet gemaakt')
        return 0
    shots = OUT / 'screenshots'
    shots.mkdir(exist_ok=True)
    try:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        mirror = True
    except OSError:
        mirror = False
    server = subprocess.Popen(
        [sys.executable, '-m', 'http.server', '8765', '--bind', '127.0.0.1'],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            probe = subprocess.run(
                ['python3', '-c',
                 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8765/", timeout=1)'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if probe.returncode == 0:
                break
            time.sleep(0.1)
        with tempfile.TemporaryDirectory(prefix='universe-shot-') as profile:
            for name, page in PREVIEWS.items():
                dest = shots / ('%s.png' % name)
                url = 'http://127.0.0.1:8765/%s' % page.relative_to(ROOT).as_posix()
                # Eerst naar een tijdelijk bestand: een mislukte run laat zo de
                # bestaande, in git vastgelegde schermafbeelding intact.
                tmp = Path(profile) / dest.name
                _shot(BROWSER, url, tmp, Path(profile) / name)
                shutil.copy2(tmp, dest)
                if mirror:
                    shutil.copy2(dest, ARTIFACTS / dest.name)
                print(dest)
    finally:
        server.terminate()
        try:
            server.wait(5)
        except subprocess.TimeoutExpired:
            server.kill()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
