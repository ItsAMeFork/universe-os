import {call,on,applySettings,toast,h} from './api.js';
// The simple world (0.2.28): every program as a plain button. Only things that cannot fail to draw.
const list=document.getElementById('apps');
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
 try{const c=await call('config.get');applySettings({...c.settings,colors:c.world?.colors});}catch{}
 await load();
 window.__universePageReady?.();
 call('world.ready',{milliseconds:performance.now(),lite:true}).catch(()=>{});
})();
on('apps-changed',load);
