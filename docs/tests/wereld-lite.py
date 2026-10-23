"""0.2.28 (23 Oct, H310M: only the glowing core, no planets): the simple 2D world, its triggers and universe-diagnose."""
import os, re, subprocess, sys, tempfile
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pakket', 'universe-os')
shell = os.path.join(root, 'usr/lib/universe-os/shell')
ui = os.path.join(root, 'usr/share/universe-os/ui')
sys.path.insert(0, shell)
import grafisch
# forced by the safe boot options and by nouveau drawn by the processor; universe.world decides by hand
assert grafisch.world_lite('quiet universe.gfx=safe', 'safe', ['virtio-pci'])
assert grafisch.world_lite('universe.gpu=veilig', 'normal', ['nvidia'])
assert grafisch.world_lite('quiet', 'safe', ['nouveau'])
assert grafisch.world_lite('quiet', 'safe', ['virtio-pci']) is None  # probe-only safe mode keeps the space world
assert grafisch.world_lite('quiet', 'normal', ['nouveau']) is None
assert grafisch.world_lite('universe.gfx=safe universe.world=full', 'safe', ['nouveau']) is None
assert grafisch.world_lite('universe.world=lite', 'normal', ['i915'])
# webview: repeated crashes of the world go to the simple page
wv = open(os.path.join(shell, 'webview.py')).read()
assert "FALLBACK = {'world.html': 'world-lite.html'}" in wv and 'surface.fallback(' in wv and 'def page_uri(' in wv
# shell: watchdogs, world.failed / world.ok, starts lite when chosen
sh = open(os.path.join(shell, 'universe_shell.py')).read()
for needle in ("'world.failed'", "'world.ok'", 'def world_lite', 'WORLD_READY_TIMEOUT', 'WORLD_OK_TIMEOUT', "'world-lite.html' if self.lite"):
    assert needle in sh, needle
# world.js reports failures and forces the end state of a stuck intro (the photo)
w = open(os.path.join(ui, 'world.js')).read()
assert "call('world.failed'" in w and 'checkVisible' in w and "start().catch(" in w and "call('world.ok'" in w
lite = open(os.path.join(ui, 'world-lite.js')).read()
assert "call('apps.list')" in lite and "call('apps.launch'" in lite and "call('world.ready'" in lite
assert '<canvas' not in open(os.path.join(ui, 'world-lite.html')).read().lower()
# the simple world shows the programs in a real browser (fake shell bridge)
chrome = '/usr/bin/google-chrome'
if os.path.exists(chrome):
    stub = """<script>window.__calls=[];window.webkit={messageHandlers:{universe:{postMessage(m){m=JSON.parse(m);__calls.push(m.cmd);
    const r={'apps.list':[{id:'firefox.desktop',name:'Firefox',icon:''},{id:'org.gnome.Nautilus.desktop',name:'Bestanden',icon:''}],'config.get':{settings:{}}}[m.cmd]??null;
    setTimeout(()=>__universeReply(m.id,true,r),0);}}}};setTimeout(()=>document.title='calls:'+__calls.join(','),1500);</script>"""
    html = open(os.path.join(ui, 'world-lite.html')).read().replace('<head>', '<head>' + stub, 1)
    with tempfile.NamedTemporaryFile('w', suffix='.html', dir=ui, delete=False) as f:
        f.write(html)
    try:
        out = subprocess.run([chrome, '--headless=new', '--no-sandbox', '--allow-file-access-from-files', '--virtual-time-budget=4000',
                              '--dump-dom', 'file://' + f.name], capture_output=True, text=True, timeout=60).stdout
    finally:
        os.unlink(f.name)
    assert out.count('class="app"') == 2 and 'Bestanden' in out, out[-2000:]
    assert re.search(r'calls:[^<]*world\.ready', out), out[-500:]
# universe-diagnose collects the logs into one file and prints the path
diag = os.path.join(root, 'usr/bin/universe-diagnose')
assert os.access(diag, os.X_OK)
with tempfile.TemporaryDirectory() as d:
    res = subprocess.run(['sh', diag, d], capture_output=True, text=True, timeout=120)
    path = res.stdout.strip().split(': ', 1)[1]
    text = open(path).read()
    for part in ('lspci -k', 'glxinfo -B', 'eglinfo -B', 'journalctl -b', 'dmesg', 'gpu.json', 'cpuinfo flags', 'shell.log'):
        assert '===== ' + part in text or part in text, part
desk = open(os.path.join(root, 'usr/share/applications/universe-diagnose.desktop')).read()
assert 'universe-diagnose' in desk and 'NoDisplay' not in desk
assert 'mesa-utils' in open(os.path.join(root, '..', '..', 'live/config/package-lists/stuurprogrammas.list.chroot')).read()
print('ok')
