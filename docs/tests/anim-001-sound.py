from pathlib import Path
import ast,subprocess,signal,os,time,sys
p=Path(__file__).resolve().parents[2]/'pakket/universe-os/usr/lib/universe-os/shell/backend.py'
t=ast.parse(p.read_text()); nodes=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in ('sound','stop_sound')]
class Settings:
    enabled=True
    def settings(self):return {'sounds':self.enabled}
class Timers:
    callbacks=[]
    def timeout_add(self,ms,cb):self.callbacks.append(cb)
# Real process groups are used for cancellation; replace only the external audio executable.
class Processes:
    DEVNULL=subprocess.DEVNULL
    def Popen(self,args,**kw):
        assert args==['universe-geluid','update-inslag','--wacht']
        return subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],**kw)
cfg=Settings();timers=Timers();ns=dict(os=os,signal=signal,subprocess=Processes(),config=cfg,GLib=timers,_scene_sound=None)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),ns)
children=[]
try:
    ns['sound']('update-inslag');first=ns['_scene_sound'];children.append(first)
    ns['stop_sound']('unrelated');assert first.poll() is None
    ns['stop_sound']('update-inslag');first.wait(timeout=3);assert first.returncode<0
    ns['sound']('update-inslag');second=ns['_scene_sound'];children.append(second)
    cfg.enabled=False;assert timers.callbacks[-1]() is False
    second.wait(timeout=3);assert second.returncode<0
    ns['stop_sound']('update-inslag')
    print('PASS: owned effect stopped, unrelated sound ignored, live mute stops effect, repeat stop safe')
finally:
    for child in children:
        if child.poll() is None:os.killpg(child.pid,signal.SIGTERM)
        child.wait()
