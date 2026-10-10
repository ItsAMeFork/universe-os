import {updatesView} from './updates-ui.js';
import {call,on,applySettings,motionAllowed,toast,h,icon} from './api.js';
import {globe,earth,paintEarths,starfield,pixelSize} from './globe.js';
import {debugFPS,afterPaint} from './performance.js';
import {SETTINGS} from './settings-index.js';
import {keepTab} from './focus.js';
// The desktop (Axel, 10 Oct: "like a normal desktop, the planets as background, desktop icons and a menu like Windows,
// in the style of the concept photos"). Two layers:
//  - background: a 3D space scene (planets at different depths, the Earth with an orange orbit, nebula). Decoration
//    only, like a wallpaper; it moves a little with the mouse (parallax by depth) when animations are on.
//  - desktop: icons in a grid like Windows (fixed icons, the Bureaublad folder, own shortcuts). Click selects,
//    double click or Enter opens, drag snaps to the grid, F2 renames, Delete moves to the trash, right click/Menu key
//    opens the context menu. Positions and choices live in layout.json.
// The planet rooms still exist for search results and the start menu (open-planet).

const KIND={local:['local','Werkt lokaal'],online:['online','Internet nodig'],mixed:['mixed','Lokaal + online']};
let config=null,settings={},user={},current=null,lastFocus=null,appsCache=null;
let layout={planets:{},items:[],orbit:true,dock:[],icons:{},hiddenIcons:[],start:null};
let travelToken=0,backgroundBusy=false,initialFocus=true;
const setBackgroundBusy=value=>{backgroundBusy=!!value;document.documentElement.classList.toggle('background-busy',backgroundBusy);};
on('background-busy',setBackgroundBusy);
const root=h('main',{class:'universe','aria-label':'Bureaublad van Universe OS'});
const scene=h('div',{class:'scene','aria-hidden':'true'});
const desk=h('div',{class:'desktop',role:'listbox','aria-label':'Bureaubladpictogrammen','aria-multiselectable':'false'});
const room=h('section',{class:'room glass',hidden:true,role:'dialog','aria-modal':'true'});
let logoutOverlay=null;
on('logout-begin',async()=>{
 if(logoutOverlay)return;
 const planet=h('div',{class:'logout-planet'},globe(182,true,pixelSize(Math.min(innerWidth*.8,650))));
 logoutOverlay=h('div',{class:'logout-overlay',role:'status'},starfield(),planet,h('p',{},'Afmelden…'));
 document.body.append(logoutOverlay);root.inert=true;
 await afterPaint();logoutOverlay.classList.add('forming');
 await new Promise(resolve=>setTimeout(resolve,motionAllowed(settings)?1250:30));
 call('logout.finish').catch(e=>toast(e.message));
});
on('logout-error',message=>{logoutOverlay?.remove();logoutOverlay=null;root.inert=false;toast('Afmelden mislukt: '+message);});
document.body.append(root);

async function start(){
 config=await call('config.get');
 if(!config?.world?.planets?.length)throw new Error('De wereldindeling ontbreekt.');
 settings=config.settings;user=config.user||{};layout=config.layout||layout;applySettings({...settings,colors:config.world.colors});
 await afterPaint();build();debugFPS();await afterPaint();
 call('background.busy').then(setBackgroundBusy).catch(()=>{});
 call('world.ready',{milliseconds:performance.now()}).catch(()=>{});
 window.__universePageReady?.();
 setTimeout(paintEarths,1500);
}

// ----- background: 3D space scene -----
const planetGlobe=(p,diameter)=>p.style==='earth'?earth(pixelSize(diameter)):globe(p.hue,!!p.rock,pixelSize(diameter));
/** Depth 0 (far) .. 1 (near): far planets are smaller, dimmer and move less with the mouse. */
function build(){
 root.replaceChildren(Object.assign(starfield(),{className:'space-stars'}),h('div',{class:'nebula','aria-hidden':'true'}),scene,desk,room);
 scene.replaceChildren();
 for(const p of config.world.planets){
  const isEarth=p.style==='earth',depth=isEarth?1:Math.min(.85,.25+(p.size||.6)*.6);
  const unit=Math.min(innerWidth/100,innerHeight*.016);
  // The Earth is the centrepiece (right of the icons, like the concept); the others float around it as decoration.
  const size=isEarth?unit*34:unit*26*(p.size||.6)*(.55+depth*.5);
  const x=isEarth?58:p.x,y=isEarth?50:p.y;
  const el=h('div',{class:`bg-planet${isEarth?' earth-planet':''}`});
  el.style.cssText=`left:${x}%;top:${y}%;width:${size}px;height:${size}px;--depth:${depth};--delay:${-(p.hue%9)*1.3}s;opacity:${(.55+depth*.45).toFixed(2)}`;
  el.append(h('div',{class:'float'},planetGlobe(p,size),p.rings?h('span',{class:'rings'}):null));
  if(isEarth)el.append(h('span',{class:'earth-orbit back'}),h('span',{class:'earth-orbit front'}));
  scene.append(el);
 }
 buildDesktop();
 parallax();
}
// Parallax: every planet moves with its own depth, which gives the 3D feeling. Throttled to one frame.
let parallaxFrame=0,mouse=null;
function parallax(){
 root.style.setProperty('--px','0px');root.style.setProperty('--py','0px');
 root.onmousemove=e=>{
  if(backgroundBusy||!motionAllowed(settings))return;mouse=[e.clientX,e.clientY];
  if(parallaxFrame)return;
  parallaxFrame=requestAnimationFrame(()=>{parallaxFrame=0;if(backgroundBusy||!motionAllowed(settings))return;
   root.style.setProperty('--px',((mouse[0]/innerWidth-.5)*-28).toFixed(1)+'px');
   root.style.setProperty('--py',((mouse[1]/innerHeight-.5)*-18).toFixed(1)+'px');
  });
 };
}
let resizeTimer=0;
addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(config)build();},250);});

// ----- layout storage -----
const sorted=v=>Array.isArray(v)?v.map(sorted):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,sorted(v[k])])):v;
const same=(a,b)=>JSON.stringify(sorted(a))===JSON.stringify(sorted(b));
function saveLayout(){return call('layout.set',{layout}).then(clean=>{layout=clean;}).catch(e=>toast('Indeling opslaan mislukt: '+e.message));}
on('layout',l=>{if(!l||same(l,layout))return;const iconsOnly=same({...l,icons:{}},{...layout,icons:{}});layout=l;if(!iconsOnly)refreshDesktop();});

// ----- desktop icons -----
const CELL_W=100,CELL_H=108,MARGIN=14,BOTTOM=96; // CSS pixels; BOTTOM keeps the icons above the dock
let entries=[],cells=new Map(),selected=null,deskToken=0,renaming=false,refreshPending=false;
const gridSize=()=>({cols:Math.max(1,Math.floor((innerWidth-MARGIN*2)/CELL_W)),rows:Math.max(1,Math.floor((innerHeight-MARGIN-BOTTOM)/CELL_H))});
async function refreshDesktop(){
 // While a name is typed the folder watcher must not rebuild the icons (that removed the name field, VM 10 Oct).
 if(renaming){refreshPending=true;return;}
 const token=++deskToken;
 try{const d=await call('desktop.list');if(token!==deskToken)return;entries=d.entries;deskDir=d.dir;}catch(e){toast('Bureaublad laden mislukt: '+e.message);}
 placeIcons();
}
let deskDir='';
function buildDesktop(){desk.replaceChildren();refreshDesktop();}
on('desktop-changed',refreshDesktop);
/** Puts every icon in a cell: its saved place when free, otherwise the first free cell top to bottom, left to right. */
function placeIcons(){
 const {cols,rows}=gridSize(),taken=new Set(),pos=new Map(),queue=[];
 for(const e of entries){
  const p=layout.icons[e.key];
  if(p&&p[0]<cols&&p[1]<rows&&!taken.has(p+'')){taken.add(p+'');pos.set(e.key,p);}else queue.push(e);
 }
 let c=0,r=0;
 for(const e of queue){
  while(taken.has([c,r]+'')&&c<cols){r++;if(r>=rows){r=0;c++;}}
  const p=[Math.min(c,cols-1),r];taken.add(p+'');pos.set(e.key,p);
 }
 cells=pos;
 // Forget places of things that are no longer on the desktop (saved with the next change).
 for(const k of Object.keys(layout.icons||{}))if(!pos.has(k))delete layout.icons[k];
 renderIcons();
}
function renderIcons(){
 // Keep the keyboard on the same icon after a refresh (also after renaming, when the focus was in the name field).
 const active=document.activeElement,inDesk=active?.closest?.('.desk-icon');
 const focusKey=inDesk?.dataset.key&&!active.matches('input')?inDesk.dataset.key:(inDesk||!active||active===document.body)?selected:null;
 desk.replaceChildren(...entries.map(deskIcon));
 const again=focusKey&&desk.querySelector(`[data-key="${CSS.escape(focusKey)}"]`);
 if(again){selected=focusKey;again.classList.add('selected');again.focus({preventScroll:true});}
 else if(initialFocus&&desk.firstChild){initialFocus=false;desk.firstChild.focus({preventScroll:true});}
}
const cellXY=([c,r])=>[MARGIN+c*CELL_W,MARGIN+r*CELL_H];
function deskIcon(e){
 const [x,y]=cellXY(cells.get(e.key)||[0,0]);
 const pic=e.icon?h('img',{src:e.icon,alt:''}):icon(e.kind==='folder'?'folder':e.kind==='app'?'grid':'file');
 const b=h('button',{class:'desk-icon'+(selected===e.key?' selected':''),type:'button',role:'option','aria-selected':String(selected===e.key),
  'data-key':e.key,title:e.name,'aria-label':e.name},pic,h('span',{class:'desk-label'},e.name));
 b.style.left=x+'px';b.style.top=y+'px';
 b.addEventListener('click',()=>{if(wasDragged(b))return;select(e.key);});
 b.addEventListener('dblclick',()=>openEntry(e));
 b.addEventListener('focus',()=>select(e.key,false));
 b._entry=e;
 dragToGrid(b,e);
 b.addEventListener('contextmenu',ev=>{ev.preventDefault();ev.stopPropagation();select(e.key);openMenu(ev.clientX,ev.clientY,iconMenu(e));});
 return b;
}
function select(key,focus=true){
 selected=key;
 for(const b of desk.children){const on=b.dataset.key===key;b.classList.toggle('selected',on);b.setAttribute('aria-selected',String(on));if(on&&focus&&document.activeElement!==b)b.focus({preventScroll:true});}
}
function openEntry(e){
 const fail=err=>toast(err.message);
 if(e.kind==='app')return launch(e.target);
 if(e.kind==='launcher')return call('desktop.launch',{path:e.target}).catch(fail);
 if(e.kind==='install')return call('run',{tool:'installer'}).catch(fail);
 return call('open.path',{path:e.target}).catch(fail);
}
/** Drag an icon; on release it snaps to the nearest free cell. Followed on the whole page (no pointer capture in WebKitGTK). */
function dragToGrid(b,e){
 let start=null,dragging=false,offset=[0,0];
 const moveTo=ev=>{
  if(!start)return;
  if(!dragging){if(Math.hypot(ev.clientX-start[0],ev.clientY-start[1])<6)return;dragging=true;b.classList.add('dragging');select(e.key,false);}
  b.style.left=(ev.clientX-offset[0])+'px';b.style.top=(ev.clientY-offset[1])+'px';
 };
 const end=ev=>{
  removeEventListener('pointermove',moveTo);removeEventListener('pointerup',end);removeEventListener('pointercancel',end);
  if(!start)return;start=null;if(!dragging)return;dragging=false;b.classList.remove('dragging');b.dataset.dragged='1';
  const {cols,rows}=gridSize();
  const want=[Math.max(0,Math.min(cols-1,Math.round((ev.clientX-offset[0]-MARGIN)/CELL_W))),Math.max(0,Math.min(rows-1,Math.round((ev.clientY-offset[1]-MARGIN)/CELL_H)))];
  moveIcon(e.key,want);
 };
 b.addEventListener('pointerdown',ev=>{
  if(ev.button!==0)return;start=[ev.clientX,ev.clientY];dragging=false;delete b.dataset.dragged;
  const r=b.getBoundingClientRect();offset=[ev.clientX-r.left,ev.clientY-r.top];
  addEventListener('pointermove',moveTo);addEventListener('pointerup',end);addEventListener('pointercancel',end);
 });
}
const wasDragged=el=>{if(!el.dataset.dragged)return false;delete el.dataset.dragged;return true;};
/** Moves an icon to a cell (or the nearest free one) and remembers the places of all icons, like Windows does. */
function moveIcon(key,want){
 const {cols,rows}=gridSize(),used=new Set([...cells].filter(([k])=>k!==key).map(([,p])=>p+''));
 let best=want,dist=1e9;
 if(used.has(want+''))for(let c=0;c<cols;c++)for(let r=0;r<rows;r++){if(used.has([c,r]+''))continue;const d=Math.hypot(c-want[0],r-want[1]);if(d<dist){dist=d;best=[c,r];}}
 cells.set(key,best);
 layout.icons=Object.fromEntries([...cells].map(([k,p])=>[k,p]));
 renderIcons();select(key);saveLayout();
}
/** The free cell nearest to a screen point (for new things: they appear where you right clicked, like Windows). */
function cellAt(x,y){
 const {cols,rows}=gridSize(),used=new Set([...cells.values()].map(p=>p+''));
 const want=[Math.max(0,Math.min(cols-1,Math.round((x-MARGIN-CELL_W/2)/CELL_W))),Math.max(0,Math.min(rows-1,Math.round((y-MARGIN-CELL_H/2)/CELL_H)))];
 let best=want,dist=used.has(want+'')?1e9:0;
 if(dist)for(let c=0;c<cols;c++)for(let r=0;r<rows;r++){if(used.has([c,r]+''))continue;const d=Math.hypot(c-want[0],r-want[1]);if(d<dist){dist=d;best=[c,r];}}
 return best;
}
function arrangeIcons(){layout.icons={};placeIcons();saveLayout();}

// Rename in place (F2 or the menu), like Windows: an input over the label; Enter saves, Escape cancels.
function rename(e){
 if(e.source!=='desktop')return toast('Alleen bestanden en mappen op het bureaublad kun je hier een andere naam geven.');
 const b=desk.querySelector(`[data-key="${CSS.escape(e.key)}"]`);if(!b)return;
 const input=h('input',{type:'text',class:'desk-rename','aria-label':'Nieuwe naam voor '+e.name,value:e.name});
 b.querySelector('.desk-label').replaceWith(input);input.focus();renaming=true;
 const dot=e.kind==='file'?e.name.lastIndexOf('.'):-1;input.setSelectionRange(0,dot>0?dot:e.name.length);
 let done=false;
 const finish=async save=>{
  if(done)return;done=true;renaming=false;refreshPending=false;
  const name=input.value.trim();
  if(save&&name&&name!==e.name){
   try{const res=await call('desktop.rename',{path:e.target,name});selected=res.key;if(cells.has(e.key)){layout.icons[res.key]=cells.get(e.key);delete layout.icons[e.key];saveLayout();}}
   catch(err){toast(err.message);}
  }
  refreshDesktop();
 };
 input.addEventListener('keydown',ev=>{ev.stopPropagation();if(ev.key==='Enter'){ev.preventDefault();finish(true);}if(ev.key==='Escape'){ev.preventDefault();finish(false);}});
 input.addEventListener('blur',()=>finish(true));
 input.addEventListener('pointerdown',ev=>ev.stopPropagation());
}
async function removeEntry(e){
 if(e.source==='desktop'){await call('desktop.trash',{path:e.target});toast(e.name+' staat in de prullenbak.');return;}
 if(e.source==='shortcut'){layout.items=layout.items.filter(i=>i.id!==e.key);await saveLayout();refreshDesktop();return;}
 if(e.key==='sys:home'||e.key==='sys:trash'){layout.hiddenIcons=[...layout.hiddenIcons,e.key];await saveLayout();refreshDesktop();}
}

// ----- context menus (Windows-like) -----
let menu=null;
function closeMenu(){menu?.remove();menu=null;}
/** entries: {label,run,keys?} or '-' for a line. Opens at the pointer, or at the focused item for the Menu key. */
function openMenu(x,y,entries){
 closeMenu();
 const items=entries.filter(Boolean);if(!items.length)return;
 menu=h('div',{class:'ctx glass',role:'menu'});
 for(const e of items){
  if(e==='-'){menu.append(h('hr',{'aria-hidden':'true'}));continue;}
  const b=h('button',{type:'button',role:'menuitem'},h('span',{},e.label),e.keys?h('kbd',{},e.keys):null);
  b.addEventListener('click',()=>{closeMenu();Promise.resolve().then(e.run).catch(err=>toast(err.message));});
  menu.append(b);
 }
 document.body.append(menu);
 const r=menu.getBoundingClientRect();
 menu.style.left=Math.max(8,Math.min(x,innerWidth-r.width-8))+'px';menu.style.top=Math.max(8,Math.min(y,innerHeight-r.height-8))+'px';
 menu.querySelector('button')?.focus();
}
addEventListener('pointerdown',e=>{if(menu&&!menu.contains(e.target))closeMenu();},true);
addEventListener('blur',closeMenu);
// A click on the desktop closes the start menu, like Windows.
let startOpen=false;
on('start-state',open=>{startOpen=!!open;});
addEventListener('pointerdown',()=>{if(startOpen)call('surface.hide',{name:'start'}).catch(()=>{});},true);

// Programs that already have a fixed taskbar button use that button instead of a second one.
const DOCK_BUILTIN_APPS={'thunar.desktop':'files','xfce4-terminal.desktop':'terminal','org.gnome.Software.desktop':'store'};
const dockKey=id=>DOCK_BUILTIN_APPS[id]||'app:'+id;
const inDock=id=>layout.dock.includes(dockKey(id));
function toggleDock(id){
 const key=dockKey(id);
 layout.dock=inDock(id)?layout.dock.filter(d=>d!==key):[...layout.dock,key];
 saveLayout();
}
const DOCK_NAMES={space:'Bureaublad tonen',files:'Bestanden',browser:'Internet',terminal:'Terminal',store:'Softwarewinkel',control:'Controlecentrum'};
function iconMenu(e){
 const app=e.kind==='app'?e.target:null;
 return [
  {label:'Openen',run:()=>openEntry(e),keys:'Enter'},
  ...(e.kind==='folder'&&e.source!=='system'?[{label:'Openen in Bestanden',run:()=>call('run',{tool:'files',path:e.target})}]:[]),
  ...(app?[{label:inDock(app)?'Losmaken van de taakbalk':'Aan de taakbalk vastmaken',run:()=>toggleDock(app)}]:[]),
  '-',
  ...(e.source==='desktop'?[{label:'Naam wijzigen',run:()=>rename(e),keys:'F2'},{label:'Naar de prullenbak',run:()=>removeEntry(e),keys:'Delete'}]:[]),
  ...(e.source==='shortcut'?[{label:'Van het bureaublad verwijderen',run:()=>removeEntry(e),keys:'Delete'}]:[]),
  ...(e.key==='sys:home'||e.key==='sys:trash'?[{label:'Van het bureaublad verbergen',run:()=>removeEntry(e)}]:[]),
 ];
}
function desktopMenu(ev){
 const at=ev?cellAt(ev.clientX,ev.clientY):null;
 const hidden=layout.hiddenIcons||[],missingDock=Object.keys(DOCK_NAMES).filter(d=>!layout.dock.includes(d));
 return [
  {label:'Nieuwe map',run:async()=>{const res=await call('desktop.mkdir');if(at){layout.icons={...layout.icons,[res.key]:at};saveLayout();}await refreshDesktop();const e=entries.find(x=>x.key===res.key);if(e){select(e.key);rename(e);}}},
  {label:'Programma op het bureaublad…',run:()=>addProgram(at)},
  {label:'Snelkoppeling naar een map…',run:()=>addPath('folder',at)},
  {label:'Snelkoppeling naar een bestand…',run:()=>addPath('file',at)},
  '-',
  {label:'Pictogrammen automatisch schikken',run:arrangeIcons},
  ...hidden.map(k=>({label:(k==='sys:home'?'Persoonlijke map':'Prullenbak')+' weer tonen',run:async()=>{layout.hiddenIcons=hidden.filter(x=>x!==k);await saveLayout();refreshDesktop();}})),
  ...missingDock.map(d=>({label:'Op de taakbalk zetten: '+DOCK_NAMES[d],run:()=>{layout.dock=[...layout.dock,d];saveLayout();}})),
  '-',
  {label:'Bureaubladmap openen',run:()=>call('open.path',{path:deskDir})},
  {label:'Persoonlijke instellingen',run:()=>run('control',{page:'appearance'})},
 ];
}
desk.addEventListener('contextmenu',e=>{if(e.target!==desk)return;e.preventDefault();openMenu(e.clientX,e.clientY,desktopMenu(e));});
desk.addEventListener('pointerdown',e=>{if(e.target===desk)select(null,false);});

const newId=()=>'i'+Date.now().toString(36)+Math.random().toString(36).slice(2,6);
async function addItem(item,at){
 const id=newId();
 layout.items.push({id,...item});if(at)layout.icons={...layout.icons,[id]:at};
 await saveLayout();await refreshDesktop();toast(item.name+' staat nu op het bureaublad.');
}
async function addPath(kind,at){
 const picked=await call('pick.path',{kind});
 if(picked)addItem({kind,target:picked.path,name:picked.name},at);
}
async function addProgram(at){
 const list=await apps();
 const search=h('input',{type:'search',class:'room-search',placeholder:'Zoek een programma','aria-label':'Zoek een programma'});
 const grid=h('div',{class:'tiles'});
 const close=h('button',{class:'room-back',type:'button'},icon('back'),'Annuleren');
 const box=h('section',{class:'picker glass',role:'dialog','aria-modal':'true','aria-label':'Programma op het bureaublad'},
  h('h2',{},'Programma op het bureaublad zetten'),search,grid,close);
 const done=()=>{box.remove();desk.inert=false;};
 const show=()=>{const q=search.value.trim().toLowerCase();grid.replaceChildren(...list.filter(a=>!q||(a.name+' '+a.keywords).toLowerCase().includes(q)).slice(0,60)
  .map(a=>tile({name:a.name,sub:a.comment,img:a.icon,iconName:'grid',onClick:()=>{done();addItem({kind:'app',target:a.id,name:a.name},at);}})));};
 search.addEventListener('input',show);close.addEventListener('click',done);
 box.addEventListener('keydown',e=>{keepTab(e,box);if(e.key==='Escape'){e.stopPropagation();done();}});
 show();root.append(box);desk.inert=true;search.focus();
}

async function land(p,{chooseBrowser=false}={}){
 if(p.id==='chat'&&!chooseBrowser){try{const b=await call('browser.list');if(b.default){await launch(b.default);return;}}catch(e){toast('Browserkeuze ophalen mislukt: '+e.message);}}
 if(current)return;current=p;lastFocus=document.activeElement;desk.inert=true;
 ++travelToken;openRoom(p);
}
function leave(){
 if(!current)return;travelToken++;current=null;room.hidden=true;room.replaceChildren();desk.inert=false;
 (lastFocus&&lastFocus.isConnected?lastFocus:desk.firstChild)?.focus({preventScroll:true});
}
function withMenu(el,entries){
 el._menu=entries;
 el.addEventListener('contextmenu',e=>{e.preventDefault();e.stopPropagation();openMenu(e.clientX,e.clientY,el._menu(e));});
}

function openRoom(p){
 room.style.setProperty('--hue',p.hue);room.setAttribute('aria-label',p.name);
 const [kind,kindText]=KIND[p.kind]||KIND.local;
 const back=h('button',{class:'room-back',type:'button'},icon('back'),'Terug naar het bureaublad');back.addEventListener('click',leave);
 const side=h('aside',{class:'room-side'},back,planetGlobe(p,Math.min(220,innerWidth*.2)),h('h1',{},p.name),h('span',{class:`badge ${kind}`},kindText),h('p',{},p.description));
 const main=h('div',{class:'room-main'});
 room.replaceChildren(side,main);room.hidden=false;
 Promise.resolve().then(()=>(ROOMS[p.id]||(m=>m.append(h('p',{class:'empty'},'Deze planeet heeft nog geen inhoud.'))))(main))
  .catch(e=>{if(main.isConnected)main.append(h('p',{role:'alert'},'Deze kamer kon niet worden geladen: '+e.message));});
 (main.querySelector('input,button')||back).focus({preventScroll:true});
}

const launch=id=>call('apps.launch',{id}).catch(e=>toast('Kan het programma niet openen: '+e.message));
const run=(tool,args={})=>call('run',{tool,...args}).catch(e=>toast(e.message));
function tile({name,sub,iconName,img,onClick,wide}){
 const pic=img?h('img',{class:'app-icon',src:img,alt:''}):icon(iconName||'planet');
 const b=h('button',{class:`tile ${wide?'wide':''}`,type:'button'},pic,wide?h('span',{class:'t-text'},h('span',{class:'t-name'},name),sub?h('span',{class:'t-sub'},sub):null):[h('span',{class:'t-name'},name),sub?h('span',{class:'t-sub'},sub):null]);
 b.addEventListener('click',onClick);return b;
}
function section(title,...kids){return h('section',{},h('h2',{},title),...kids);}
async function apps(){if(!appsCache)appsCache=await call('apps.list');return appsCache;}
on('apps-changed',()=>{appsCache=null;if(current&&['apps','chat','games'].includes(current.id))openRoom(current);});

function appGrid(list,empty){
 const grid=h('div',{class:'tiles'});
 if(!list.length)grid.append(h('p',{class:'empty'},empty));
 for(const a of list){
  const t=tile({name:a.name,sub:a.comment,img:a.icon,iconName:'grid',onClick:()=>launch(a.id)});
  withMenu(t,()=>[{label:'Openen',run:()=>launch(a.id)},{label:'Op het bureaublad zetten',run:()=>addItem({kind:'app',target:a.id,name:a.name})},
   {label:inDock(a.id)?'Losmaken van de taakbalk':'Aan de taakbalk vastmaken',run:()=>toggleDock(a.id)}]);
  grid.append(t);
 }
 return grid;
}
const CATEGORIES=[['Internet','Network'],['Kantoor en tekst','Office'],['Afbeeldingen','Graphics'],['Geluid en video','AudioVideo'],['Hulpprogramma\'s','Utility'],['Ontwikkeling','Development'],['Systeem','System'],['Instellingen','Settings']];

const ROOMS={
 async home(main){
  const card=h('div',{class:'user-card'},h('div',{class:'avatar','aria-hidden':'true'},(user.fullName||user.name||'?').slice(0,1).toUpperCase()),
   h('div',{},h('div',{style:'font-weight:600;font-size:1.1em'},user.fullName||user.name),h('div',{class:'muted'},`${user.name} · ${user.admin?'Beheerder':'Standaardaccount'}${user.live?' · tijdelijk live-account':''}`)));
  main.append(card);
  main.append(tile({name:'Browser kiezen',sub:'Standaardbrowser instellen of veranderen',iconName:'grid',onClick:()=>{leave();const p=config.world.planets.find(p=>p.id==='chat');if(p)land(p,{travel:false,chooseBrowser:true});}}));
  const places=h('div',{class:'tiles'});main.append(section('Persoonlijke bestanden',places));
  try{for(const pl of await call('files.places'))places.append(tile({name:pl.name,sub:pl.exists?'':'(nog niet aangemaakt)',iconName:pl.id==='trash'?'close':'folder',onClick:()=>call('open.path',{path:pl.path}).catch(e=>toast(e.message))}));}
  catch(e){places.append(h('p',{class:'empty'},e.message));}
  main.append(section('Persoonlijk',h('div',{class:'tiles'},
   tile({name:'Persoonlijke instellingen',sub:'Weergave, animaties, tekstgrootte',iconName:'display',onClick:()=>run('control',{page:'appearance'})}),
   tile({name:'Account',sub:'Wachtwoord en accountgegevens',iconName:'user',onClick:()=>run('control',{page:'users'})}),
   tile({name:'Taal en toetsenbord',sub:'Ook het testveld voor tekens',iconName:'keyboard',onClick:()=>run('control',{page:'keyboard'})}),
   tile({name:'Bestandsbeheer',sub:'Windows + E',iconName:'folder',onClick:()=>run('files')}))));
 },
 async apps(main){
  const search=h('input',{type:'search',class:'room-search',placeholder:'Zoek in programma\'s…','aria-label':'Zoek in programma\'s'});
  const list=h('div',{});main.append(search,list);
  let all=[];try{all=(await apps()).filter(a=>!a.game);}catch(e){list.append(h('p',{class:'empty'},e.message));return;}
  const render=()=>{
   const q=search.value.trim().toLowerCase();list.replaceChildren();
   if(q){list.append(appGrid(all.filter(a=>(a.name+' '+a.comment+' '+a.keywords).toLowerCase().includes(q)),'Geen programma gevonden.'));return;}
   const used=new Set();
   const windows=all.filter(a=>a.id.startsWith('universe-wine-'));
   windows.forEach(a=>used.add(a.id));used.add('universe-windows-apps.desktop');
   const windowsGrid=appGrid(windows,'Nog geen Windows-programma’s geïnstalleerd.');
   windowsGrid.prepend(tile({name:'Windows-programma’s beheren',sub:'Installeren, starten, logboeken en verwijderen',iconName:'grid',onClick:()=>launch('universe-windows-apps.desktop')}));
   list.append(section('Windows-programma’s',windowsGrid));
   for(const [title,cat] of CATEGORIES){const part=all.filter(a=>!used.has(a.id)&&a.categories.includes(cat));part.forEach(a=>used.add(a.id));if(part.length)list.append(section(title,appGrid(part)));}
   const rest=all.filter(a=>!used.has(a.id));if(rest.length)list.append(section('Overig',appGrid(rest)));
  };
  search.addEventListener('input',render);render();
 },
 async store(main){
  main.append(h('div',{class:'notice'},'Zoeken in de lijst en verwijderen werken lokaal. Installeren en bijwerken downloadt pakketten uit de officiële Debian-pakketbronnen en heeft internet nodig. Voor wijzigingen wordt om je wachtwoord gevraagd (alleen beheerders).'));
  main.append(section('Software',h('div',{class:'tiles'},
   tile({name:'Softwarewinkel openen',sub:'Zoeken, installeren en verwijderen',iconName:'store',onClick:()=>run('software')}),
   tile({name:'Updates',sub:'Systeem- en beveiligingsupdates',iconName:'update',onClick:()=>run('software',{mode:'updates'})}),
   tile({name:'Geïnstalleerde software',sub:'Overzicht en verwijderen',iconName:'grid',onClick:()=>run('software',{mode:'installed'})}),
   tile({name:'Lokaal .deb-bestand',sub:'Een gedownload pakket installeren',iconName:'download',onClick:()=>run('deb')}))));
  main.append(section('Status',updatesView()));
 },
 control(main){
  const grid=h('div',{class:'tiles'});
  for(const s of SETTINGS)grid.append(tile({name:s.name,iconName:s.icon,onClick:()=>run('control',{page:s.id})}));
  main.append(section('Instellingen',grid));
 },
 async chat(main){
  main.append(h('p',{},'Kies een browser. Je keuze wordt opgeslagen voor jouw account; de Internet-planeet opent die browser daarna direct.'));
  const choices=h('div',{class:'tiles'});main.append(section('Browsers',choices));
  try{const b=await call('browser.list');for(const a of b.apps){const button=tile({name:a.name,sub:a.id===b.default?'Standaardbrowser':'Als standaardbrowser gebruiken',img:a.icon,onClick:async()=>{button.disabled=true;try{await call('browser.select',{id:a.id});await launch(a.id);leave();}catch(e){toast(e.message);}finally{button.disabled=false;}}});choices.append(button);}if(!b.apps.length)choices.append(h('p',{},'Nog geen browser beschikbaar. De downloadstatus van Chrome staat hieronder.'));}
  catch(e){choices.append(h('p',{role:'alert'},e.message));}
  const chrome=tile({name:'Google Chrome',sub:'Downloadstatus controleren…',iconName:'grid',onClick:()=>launch('google-chrome.desktop')});
  chrome.disabled=true;const chromeMessage=h('p',{role:'status'});
  const chromeRefresh=h('button',{type:'button'},'Downloadstatus vernieuwen');
  main.append(section('Chrome-download',h('div',{class:'tiles'},chrome),chromeMessage,chromeRefresh));
  let chromeBusy=false;
  const refreshChrome=async()=>{if(chromeBusy)return;chromeBusy=true;chromeRefresh.disabled=true;
   try{const s=await call('chrome.status');chrome.disabled=!s.available;chrome.querySelector('.t-sub').textContent=s.available?'Open de internetbrowser':s.state==='installing'?'Wordt gedownload en geïnstalleerd':'Nog niet beschikbaar';chromeMessage.textContent=s.message;}
   catch(e){chrome.disabled=true;chromeMessage.textContent=e.message;}
   finally{chromeBusy=false;chromeRefresh.disabled=false;}
  };
  chromeRefresh.addEventListener('click',refreshChrome);await refreshChrome();
  const poll=()=>setTimeout(async()=>{if(!chrome.isConnected)return;await refreshChrome();poll();},5000);poll();
  let list=[];try{list=(await apps()).filter(a=>a.categories.includes('InstantMessaging')||a.categories.includes('Chat')||a.categories.includes('Email'));}catch(e){main.append(h('p',{role:'alert'},'Communicatieprogramma’s konden niet worden opgehaald: '+e.message));return;}
  main.append(section('Geïnstalleerde communicatieprogramma\'s',appGrid(list,'Geen communicatieprogramma\'s geïnstalleerd.')));
  main.append(section('Meer',h('div',{class:'tiles'},tile({name:'Chatprogramma zoeken',sub:'In de softwarewinkel (internet nodig)',iconName:'store',onClick:()=>run('software',{search:'chat'})}))));
 },
 async games(main){
  let list=[];try{list=(await apps()).filter(a=>a.game);}catch(e){main.append(h('p',{class:'empty'},e.message));return;}
  main.append(section('Geïnstalleerde games',appGrid(list,'Er zijn nog geen games geïnstalleerd.')));
  main.append(section('Meer games',h('div',{class:'tiles'},tile({name:'Games zoeken',sub:'In de softwarewinkel (internet nodig)',iconName:'store',onClick:()=>run('software',{search:'game'})}))));
 }
};


// Keyboard like a Windows desktop: arrows move between icons, Enter opens, F2 renames, Delete removes,
// Menu key / Shift+F10 opens the context menu, Escape closes menus and rooms.
addEventListener('keydown',e=>{
 if(menu){
  if(e.key==='Escape'){e.preventDefault();closeMenu();return;}
  if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();const bs=[...menu.querySelectorAll('button')],i=bs.indexOf(document.activeElement);bs[(i+(e.key==='ArrowDown'?1:-1)+bs.length)%bs.length]?.focus();return;}
  if(e.key==='Tab'){e.preventDefault();return;}
  return;
 }
 if(current){keepTab(e,room);if(e.key==='Escape'){e.preventDefault();leave();}return;}
 const focused=document.activeElement?.closest?.('.desk-icon'),entry=focused?._entry;
 if(e.key==='ContextMenu'||(e.shiftKey&&e.key==='F10')){
  e.preventDefault();
  if(entry){const r=focused.getBoundingClientRect();openMenu(r.left+r.width/2,r.top+r.height/2,iconMenu(entry));}
  else{const t=document.activeElement?.closest?.('.tile');if(t?._menu){const r=t.getBoundingClientRect();openMenu(r.left+r.width/2,r.top+r.height/2,t._menu());}else openMenu(MARGIN+40,MARGIN+40,desktopMenu());}
  return;
 }
 if(!entry||e.ctrlKey||e.altKey||e.metaKey)return;
 if(e.key==='Enter'){e.preventDefault();openEntry(entry);return;}
 if(e.key==='F2'){e.preventDefault();rename(entry);return;}
 if(e.key==='Delete'){e.preventDefault();removeEntry(entry).catch(err=>toast(err.message));return;}
 const d={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key];if(!d)return;
 e.preventDefault();
 const [c,r]=cells.get(entry.key)||[0,0];let best=null,score=1e9;
 for(const [k,[c2,r2]] of cells){if(k===entry.key)continue;const dc=c2-c,dr=r2-r,along=dc*d[0]+dr*d[1];if(along<=0)continue;const s=along+Math.abs(dc*d[1]+dr*d[0])*3;if(s<score){score=s;best=k;}}
 if(best)select(best);
});
// Commands from the shell: open a planet room (search results, start menu), settings changed, back to the desktop.
on('open-planet',({id})=>{const p=config?.world.planets.find(x=>x.id===id);if(!p)return;if(current)leave();land(p);});
on('show-space',()=>leave());
on('config',c=>{if(current)leave();config=c;settings=c.settings;user=c.user||user;if(c.layout)layout=c.layout;applySettings({...settings,colors:c.world.colors});build();});
start();
