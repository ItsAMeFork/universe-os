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
