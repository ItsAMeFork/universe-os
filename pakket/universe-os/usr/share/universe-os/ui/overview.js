import {call,on,applySettings,toast,h,icon} from './api.js';
import {SETTINGS} from './settings-index.js';
// Overview (Windows key): open programs (also minimised ones) and search for programs, files and settings.
// The page is shown as an overlay with exclusive keyboard focus; Esc or a choice hides it again.

let windows=[],config=null,searchToken=0;
const input=h('input',{type:'search',placeholder:'Zoek programma\'s, bestanden en instellingen','aria-label':'Zoeken',autocomplete:'off'});
const body=h('div',{class:'block'});
const wrap=h('div',{class:'wrap',role:'dialog','aria-label':'Overzicht en zoeken'},
 h('div',{class:'search'},icon('search'),input),body,
 h('div',{class:'foot'},h('kbd',{},'Enter'),' openen · ',h('kbd',{},'↑'),h('kbd',{},'↓'),h('kbd',{},'Tab'),' kiezen · ',h('kbd',{},'Esc'),' sluiten · ',h('kbd',{},'Windows'),'+',h('kbd',{},'D'),' ruimtewereld'));
document.body.append(wrap);

const hide=()=>call('surface.hide',{name:'overview'}).catch(()=>{});
const done=p=>p.then(hide).catch(e=>toast(e.message));

function render(){
 const q=input.value.trim();
 if(q)return search(q);
 body.replaceChildren();
 const list=h('div',{class:'windows'});
 if(!windows.length)list.append(h('p',{class:'empty'},'Er zijn geen programma\'s geopend.'));
 for(const w of windows){
  const card=h('button',{class:`win ${w.activated?'active':''}`,type:'button','aria-label':`${w.title||w.appName}${w.minimized?', geminimaliseerd':''}. Enter om te openen.`},
   w.icon?h('img',{src:w.icon,alt:''}):icon('windows'),
   h('span',{class:'t'},h('span',{class:'title'},w.title||w.appName||'Venster'),h('span',{class:'sub'},[w.appName,w.minimized?'geminimaliseerd':'',w.maximized?'gemaximaliseerd':''].filter(Boolean).join(' · '))));
  card.addEventListener('click',()=>done(call('windows.activate',{id:w.id})));
  const close=h('span',{class:'x',role:'button',tabindex:'-1','aria-label':'Venster sluiten',title:'Sluiten'},icon('close'));
  close.addEventListener('click',e=>{e.stopPropagation();call('windows.close',{id:w.id}).catch(err=>toast(err.message));});
  card.append(close);list.append(card);
 }
 body.append(h('h2',{},`Geopende programma's (${windows.length})`),list);
 if(config){
  const planets=h('div',{class:'planets'});
  const space=h('button',{type:'button'},icon('planet'),'Naar de ruimtewereld');space.addEventListener('click',()=>done(call('desktop.show')));planets.append(space);
  for(const p of config.world.planets){const b=h('button',{type:'button'},icon('planet'),p.name);b.addEventListener('click',()=>done(call('world.open',{id:p.id})));planets.append(b);}
  body.append(h('h2',{style:'margin-top:22px'},'Planeten'),planets);
 }
}
async function search(q){
 const token=++searchToken,lower=q.toLowerCase();
 const settings=SETTINGS.filter(s=>(s.name+' '+s.words).toLowerCase().includes(lower));
 let res={apps:[],files:[]};try{res=await call('search',{q});}catch(e){toast(e.message);}
 if(token!==searchToken)return;
 body.replaceChildren();
 const group=(title,items,make)=>{if(!items.length)return;const list=h('div',{class:'results'});items.forEach(i=>list.append(make(i)));body.append(h('h2',{style:'margin-top:14px'},title),list);};
 const row=(img,iconName,title,sub,action)=>{const b=h('button',{class:'res',type:'button'},img?h('img',{src:img,alt:''}):icon(iconName),h('span',{class:'t'},h('span',{},title),sub?h('span',{class:'sub'},sub):null));b.addEventListener('click',action);return b;};
 const wins=windows.filter(w=>(w.title+' '+w.appName).toLowerCase().includes(lower));
 group('Geopende programma\'s',wins,w=>row(w.icon,'windows',w.title||w.appName,'Geopend',()=>done(call('windows.activate',{id:w.id}))));
 group('Programma\'s',res.apps,a=>row(a.icon,'grid',a.name,a.comment,()=>done(call('apps.launch',{id:a.id}))));
 group('Instellingen',settings,s=>row(null,s.icon,s.name,'Controlecentrum',()=>done(call('run',{tool:'control',page:s.id}))));
 group('Bestanden',res.files,f=>row(null,f.dir?'folder':'file',f.name,f.display,()=>done(call('open.path',{path:f.path}))));
 if(!body.children.length)body.append(h('p',{class:'empty'},`Niets gevonden voor "${q}".`));
}
input.addEventListener('input',()=>render());
input.addEventListener('keydown',e=>{if(e.key==='Enter'){const first=body.querySelector('button');if(first){e.preventDefault();first.click();}}if(e.key==='ArrowDown'){e.preventDefault();body.querySelector('button')?.focus();}});
addEventListener('keydown',e=>{
 if(e.key==='Escape'){e.preventDefault();hide();return;}
 if((e.key==='ArrowDown'||e.key==='ArrowUp'||e.key==='ArrowRight'||e.key==='ArrowLeft')&&document.activeElement!==input){
  const all=[...body.querySelectorAll('button')];const i=all.indexOf(document.activeElement);if(i<0)return;e.preventDefault();
  const step=e.key==='ArrowDown'||e.key==='ArrowRight'?1:-1;const next=all[i+step];if(next)next.focus();else if(step<0)input.focus();
 }
 // Typing anywhere goes to the search field.
 if(e.key.length===1&&!e.ctrlKey&&!e.altKey&&document.activeElement!==input){input.focus();}
});
on('windows',list=>{windows=list||[];if(!input.value.trim())render();});
on('shown',()=>{input.value='';render();input.focus();});
on('config',c=>{config=c;applySettings({...c.settings,colors:c.world.colors});render();});
(async()=>{
 try{config=await call('config.get');applySettings({...config.settings,colors:config.world.colors});}catch{}
 try{windows=await call('windows.list');}catch{}
 render();input.focus();
})();
