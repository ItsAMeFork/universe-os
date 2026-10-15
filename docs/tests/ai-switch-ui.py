"""Browser check: one tap switches Claude, ChatGPT, Gemini and local.

Skips when no Chromium is installed. Headroom, auto-accept and Claude in Chrome
stay on the page and still call their own commands.
"""
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / 'docs/tests/preview/ai-switch-check.html'
BROWSER = next((shutil.which(name) for name in (
    'chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable')
    if shutil.which(name)), None)


def main():
    if not BROWSER:
        print('SKIP: geen browser, ai-switch-ui niet gedraaid')
        return 0
    server = subprocess.Popen(
        [sys.executable, '-m', 'http.server', '8771', '--bind', '127.0.0.1'],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            probe = subprocess.run(
                ['python3', '-c',
                 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8771/", timeout=1)'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if probe.returncode == 0:
                break
            time.sleep(0.1)
        else:
            raise SystemExit('server startte niet')
        url = 'http://127.0.0.1:8771/' + PAGE.relative_to(ROOT).as_posix()
        with tempfile.TemporaryDirectory(prefix='ai-switch-') as profile:
            proc = subprocess.Popen(
                [BROWSER, '--headless=new', '--disable-gpu', '--no-sandbox',
                 '--disable-dev-shm-usage', '--no-first-run', '--virtual-time-budget=8000',
                 '--user-data-dir=' + profile, '--dump-dom', url],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
            chunks = []
            deadline = time.time() + 25
            while time.time() < deadline:
                ready, _, _ = select.select([proc.stdout], [], [], 0.4)
                if ready:
                    block = os.read(proc.stdout.fileno(), 65536)
                    if not block:
                        break
                    chunks.append(block)
                    blob = b''.join(chunks)
                    if b'data-result="pass"' in blob or b'data-result="fail"' in blob:
                        break
                elif proc.poll() is not None:
                    break
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(5)
            out = b''.join(chunks).decode('utf-8', 'replace')
        if 'data-result="pass"' not in out:
            detail = ''
            marker = 'data-detail="'
            if marker in out:
                detail = out.split(marker, 1)[1].split('"', 1)[0]
            raise SystemExit('FAIL: ai-switch-ui %s' % detail)
    finally:
        server.terminate()
        try:
            server.wait(5)
        except subprocess.TimeoutExpired:
            server.kill()
    print('PASS: ai-switch-ui')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
