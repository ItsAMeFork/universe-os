import {call,on,applySettings,motionAllowed,toast,h} from './api.js';
// The simple world (0.2.28): every program as a plain button. Only things that cannot fail to draw.
const list=document.getElementById('apps');
let config={},scene=null,sceneEnd=0,closing=false,epoch=0;
async function load(){
 let apps=[];
 try{apps=await call('apps.list');}catch(e){toast('Programma\'s laden mislukt: '+e.message);}
 apps=[...apps].sort((a,b)=>String(a.name).localeCompare(String(b.name),'nl'));
 list.replaceChildren(...apps.map(a=>{
  const b=h('button',{class:'app',type:'button',role:'listitem',title:a.name},a.icon?h('img',{src:a.icon,alt:''}):h('span',{class:'ph','aria-hidden':'true'}),h('span',{},a.name));
  b.addEventListener('click',()=>call('apps.launch',{id:a.id}).catch(e=>toast(e.message)));
  return b;
 }));
}
document.getElementById('diag').addEventListener('click',()=>call('apps.launch',{id:'universe-diagnose.desktop'}).then(()=>toast('Diagnose wordt gemaakt; het pad verschijnt in het venster.')).catch(e=>toast(e.message)));
(async()=>{
 try{const c=await call('config.get');config=c;applySettings({...c.settings,colors:c.world?.colors});}catch{}
 await load();
 window.__universePageReady?.();
 call('world.ready',{milliseconds:performance.now(),lite:true}).catch(()=>{});
})();
on('apps-changed',load);

// The fallback desktop uses the same scene, original planets and shell-owned deadline. Loaded only when needed: a
// broken scene module must never take the simple desktop down with it.
on('launch-countdown',async({seconds=10,runup=0,elapsed=0,version=''}={})=>{
 if(scene||closing)return;
 const received=performance.now();
 sceneEnd=received+(runup+seconds-elapsed)*1000;
 scene={stop(){}}; // claimed at once: a second message while the module loads starts nothing
 try{
  const {startUpdateScene}=await import('./meteoriet.js');
  if(!scene)return; // stopped while loading
  scene=startUpdateScene({host:document.body,seconds,runup,elapsed:elapsed+(performance.now()-received)/1000,version,
   reduced:!motionAllowed(config.settings||{}),planets:config.world?.planets||[]});
 }catch(e){scene=null;console.error('update-scene',e);toast('Opnieuw opstarten over '+seconds+' seconden.');}
});
on('logout-begin',async({action='logout'}={})=>{
 if(closing)return;
 closing=true;const token=++epoch;
 if(scene&&action==='reboot'&&performance.now()>=sceneEnd-1000){
  await new Promise(r=>setTimeout(r,Math.max(0,sceneEnd+1900-performance.now())));
 }else{scene?.stop();scene=null;}
 if(token===epoch)call('logout.finish').catch(e=>toast(e.message));
});
on('logout-error',message=>{epoch++;scene?.stop();scene=null;closing=false;toast('Afmelden mislukt: '+message);});

// Lock / unlock (0.3.6, Axel 29 Oct: "zorg ervoor dat dit altijd werkt, zowel de lichte modus als de normale"): as in
// the space world (world.js), the screen goes into the glowing core when locking (kern.png, the first picture of the
// login screen) and comes out of it after unlocking. Before, this page ignored both: universe-lock waited 6 s for
// lock.ready and the world stayed above the windows for 4 s after unlocking. Loaded only when needed, like the scene.
let kern=null,locked=false;
async function kernBeweging(uit){
 try{
  const [{drawCore,lensStreak},{animate}]=await Promise.all([import('./explode.js'),import('./motion.js')]);
  const W=innerWidth,H=innerHeight;
  if(!kern){kern=document.createElement('canvas');kern.setAttribute('aria-hidden','true');kern.style.cssText='position:fixed;inset:0;width:100%;height:100%;z-index:100;pointer-events:none';document.body.append(kern);}
  kern.width=Math.round(W/2);kern.height=Math.round(H/2); // soft light: half resolution is enough
  const c=kern.getContext('2d');c.setTransform(.5,0,0,.5,0,0);
  const teken=t=>{const k=t*t*(3-2*t);c.clearRect(0,0,W,H);drawCore(c,W,H,.25+.75*k,k);lensStreak(c,W,H/2,Math.sin(Math.PI*t)*.8);};
  if(motionAllowed(config.settings||{}))await animate(uit?1400:1200,t=>teken(uit?t:1-t));
  teken(uit?1:0);
 }catch(e){console.error('vergrendelen',e);}
 if(!uit){kern?.remove();kern=null;}
}
on('lock-begin',async()=>{if(locked)return;locked=true;await kernBeweging(true);call('lock.ready').catch(()=>{});});
on('unlock',async()=>{if(!locked)return;locked=false;await kernBeweging(false);call('unlock.done').catch(()=>{});});
