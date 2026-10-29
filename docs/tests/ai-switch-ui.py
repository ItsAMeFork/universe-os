"""Browser check: one tap switches Claude, ChatGPT, Gemini and local.

Skips when no Chromium is installed. Headroom, auto-accept and Claude in Chrome
stay on the page and still call their own commands.

Voorkeur: playwright (docs/tests/package.json). Ontbreekt dat, dan --dump-dom.
"""
import json
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
# exit 3 = playwright ontbreekt; anders {"result","detail"} als JSON op stdout
PLAYWRIGHT = '''
const url = process.argv[1], exe = process.argv[2];
let chromium;
try { ({chromium} = require('playwright')); }
catch { try { ({chromium} = require('playwright-core')); } catch { process.exit(3); } }
(async () => {
  const browser = await chromium.launch({executablePath: exe, headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']});
  const page = await browser.newPage();
  await page.goto(url, {waitUntil: 'load'});
  await page.waitForFunction(() => ['pass', 'fail'].includes(document.body.dataset.result), null, {timeout: 20000});
  const [result, detail] = await page.evaluate(() => [document.body.dataset.result, document.body.dataset.detail || '']);
  console.log(JSON.stringify({result, detail}));
  await browser.close();
})().catch(error => { console.error(error.message); process.exit(2); });
'''


def run_playwright(url):
    try:
        res = subprocess.run(['node', '-e', PLAYWRIGHT, url, BROWSER],
                             capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        return None
    if res.returncode == 3:
        return None
    if res.returncode != 0:
        raise SystemExit('FAIL: ai-switch-ui browser: %s' % res.stderr.strip()[-300:])
    got = json.loads(res.stdout.strip().splitlines()[-1])
    return got['result'], got['detail']


def run_dump_dom(url):
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
    result = 'pass' if 'data-result="pass"' in out else ('fail' if 'data-result="fail"' in out else '')
    detail = ''
    marker = 'data-detail="'
    if marker in out:
        detail = out.split(marker, 1)[1].split('"', 1)[0]
    return result, detail


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
        got = run_playwright(url) or run_dump_dom(url)
        result, detail = got
        if result != 'pass':
            if not result:
                raise SystemExit('FAIL: ai-switch-ui geen resultaat van de browser')
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
