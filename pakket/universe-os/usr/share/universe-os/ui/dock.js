import {call,on,applySettings,toast,h,icon} from './api.js';
// Taskbar with start menu (Axel, 10 Oct: "a menu like Windows, in the style of the concept photos").
// Left the start button (Universe planet), then the user's own buttons (layout.dock) and every open window that is
// not one of them. A dot shows that a program is open; clicking an open program brings its window forward.
// Everything except the start button is optional: drag to reorder, right click to remove.
// The start menu (start button or Windows key) has a search field, pinned programs, all programs, places, the user
// and the power actions. The surface grows upwards while a menu is open; the shell gives it the keyboard then.

const DOCK_HEIGHT=64,START_W=640;
// match: lower-case parts of the Wayland app id that belong to this program.
const BUILTIN={
 space:{name:'Bureaublad tonen',iconName:'display',match:[],click:()=>call('desktop.show')},
 files:{name:'Bestanden',desktop:'thunar.desktop',iconName:'folder',match:['thunar'],click:()=>call('run',{tool:'files'})},
 browser:{name:'Internet',iconName:'globe',match:['firefox','chrome','chromium','epiphany','brave'],click:openBrowser},
 terminal:{name:'Terminal',desktop:'xfce4-terminal.desktop',iconName:'windows',match:['xfce4-terminal','terminal'],click:()=>call('run',{tool:'terminal'})},
 store:{name:'Softwarewinkel',desktop:'org.gnome.Software.desktop',iconName:'store',match:['gnome.software','gnome-software'],click:()=>call('run',{tool:'software'})},
 control:{name:'Controlecentrum',iconName:'gear',match:['universeos.controlcenter'],click:()=>call('run',{tool:'control'})},
};
const DEFAULT_PINS=['firefox-esr.desktop','google-chrome.desktop','thunar.desktop','org.gnome.Software.desktop','xfce4-terminal.desktop',
 'mousepad.desktop','org.gnome.Calculator.desktop','atril.desktop','io.github.celluloid_player.Celluloid.desktop','org.gnome.SystemMonitor.desktop',
 'universe-windows-apps.desktop','file-roller.desktop'];
let windows=[],apps=[],browserIcon=null,user={},layout={dock:Object.keys(BUILTIN),start:null,items:[]},popup=null,start=null;
const bar=h('nav',{class:'dock','aria-label':'Taakbalk'});
document.body.append(bar);

async function openBrowser(){
 const b=await call('browser.list');
 if(b.default)return call('apps.launch',{id:b.default});
 return call('world.open',{id:'chat'}); // no default yet: the Internet room lets you choose one
}
/** The program behind a taskbar entry ('files', or 'app:org.gnome.Calculator.desktop'). */
function entry(key){
 if(BUILTIN[key]){
  const b=BUILTIN[key],a=b.desktop&&apps.find(x=>x.id===b.desktop);
  return {key,...b,img:key==='browser'?browserIcon:a?.icon};
 }
 const id=key.slice(4),a=apps.find(x=>x.id===id),base=id.replace(/\.desktop$/,'').toLowerCase();
 return {key,name:a?.name||base,img:a?.icon,iconName:'grid',match:[base,base.split('.').pop()],click:()=>call('apps.launch',{id})};
}
const owns=(e,w)=>e.match.some(m=>m&&(w.appId||'').toLowerCase().includes(m));
const act=(fn)=>Promise.resolve().then(fn).catch(e=>toast(e.message));

function button({name,img,iconName,cls='',open,active,onClick}){
 const b=h('button',{class:`item ${cls}${open?' open':''}${active?' active':''}`,type:'button',title:name,
  'aria-label':name+(open?' (geopend)':'')},img?h('img',{src:img,alt:''}):icon(iconName),h('span',{class:'dot','aria-hidden':'true'}));
 b.addEventListener('click',()=>{if(b.dataset.dragged){delete b.dataset.dragged;return;}act(onClick);});
 return b;
}
function render(){
 const startButton=h('button',{class:'item start-button'+(start?' active':''),type:'button',title:'Start','aria-label':'Start','aria-expanded':String(!!start),
  html:'<svg viewBox="0 0 32 32" aria-hidden="true"><defs><radialGradient id="sb" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#ffd2a0"/><stop offset=".55" stop-color="#ff8a3d"/><stop offset="1" stop-color="#a33c10"/></radialGradient></defs><circle cx="16" cy="16" r="8.5" fill="url(#sb)"/><ellipse cx="16" cy="16" rx="14" ry="5" fill="none" stroke="#85ffe3" stroke-width="1.6" transform="rotate(-18 16 16)"/></svg>'});
 startButton.addEventListener('click',()=>toggleStart());
 const entries=layout.dock.map(entry);
 const pinned=entries.map(e=>{
  const mine=windows.filter(w=>owns(e,w));
  const b=button({name:e.name,img:e.img,iconName:e.iconName,open:mine.length>0,active:mine.some(w=>w.activated),
   onClick:()=>mine.length?call('windows.activate',{id:mine[0].id}):e.click()});
  reorderable(b,e.key);
  b.addEventListener('contextmenu',ev=>{ev.preventDefault();openPopup(b,[
   {label:mine.length?'Naar voren halen':'Openen',run:()=>mine.length?call('windows.activate',{id:mine[0].id}):e.click()},
   {label:'Losmaken van de taakbalk',run:()=>saveDock(layout.dock.filter(k=>k!==e.key))}]);});
  return b;
 });
 const others=windows.filter(w=>!entries.some(e=>owns(e,w)));
 bar.replaceChildren(startButton,h('span',{class:'sep','aria-hidden':'true'}),...pinned,...(others.length?[h('span',{class:'sep','aria-hidden':'true'})]:[]),
  ...others.map(w=>button({name:w.title||w.appName||'Venster',img:w.icon,iconName:'grid',open:true,active:w.activated,onClick:()=>call('windows.activate',{id:w.id})})));
 resize();
}
/** Surface size: the bar, plus room above it for the start menu or a popup. */
function resize(){
 const over=start||popup;
 const width=Math.max(Math.ceil(bar.offsetWidth)+4,start?START_W+8:0,popup?Math.ceil(popup.offsetWidth)+8:0);
 const height=DOCK_HEIGHT+(over?Math.ceil(over.offsetHeight)+12:0);
 return call('dock.size',{width,height}).catch(()=>{});
}
function saveLayout(){return call('layout.set',{layout}).then(l=>{layout=l;}).catch(e=>toast('Opslaan mislukt: '+e.message));}
function saveDock(dock){layout={...layout,dock};render();saveLayout();}

/** Drag a taskbar button sideways to give it another place. Followed on the whole page (no pointer capture in WebKitGTK). */
function reorderable(b,key){
 let x0=null,dragging=false;b.dataset.key=key;
 const moveTo=e=>{
  if(x0==null)return;const dx=e.clientX-x0;
  if(!dragging){if(Math.abs(dx)<6)return;dragging=true;b.classList.add('dragging');}
  b.style.translate=dx+'px 0';
 };
 const end=e=>{
  removeEventListener('pointermove',moveTo);removeEventListener('pointerup',end);removeEventListener('pointercancel',end);
  if(x0==null)return;x0=null;if(!dragging)return;dragging=false;b.dataset.dragged='1';b.classList.remove('dragging');b.style.translate='';
  const others=[...bar.querySelectorAll('.item[data-key]')].filter(x=>x!==b);
  const keys=layout.dock.filter(k=>k!==key);let at=keys.length;
  others.forEach((x,i)=>{const r=x.getBoundingClientRect();if(at===keys.length&&e.clientX<r.left+r.width/2)at=i;});
  keys.splice(at,0,key);if(keys.join()!==layout.dock.join())saveDock(keys);
 };
 b.addEventListener('pointerdown',e=>{if(e.button!==0)return;x0=e.clientX;addEventListener('pointermove',moveTo);addEventListener('pointerup',end);addEventListener('pointercancel',end);});
}

// ----- popup menu (taskbar buttons and programs in the start menu) -----
function closePopup(){if(!popup)return;popup.remove();popup=null;resize();}
function openPopup(anchor,entries,at){
 if(popup)popup.remove();
 popup=h('div',{class:'ctx',role:'menu'});
 for(const e of entries){const m=h('button',{type:'button',role:'menuitem'},e.label);m.addEventListener('click',()=>{closePopup();act(e.run);});popup.append(m);}
 document.body.append(popup);
 const grow=resize();
 // Position after the surface has grown: above the anchor, inside the surface.
 grow.then(()=>requestAnimationFrame(()=>{
  if(!popup)return;const r=anchor.getBoundingClientRect(),w=popup.offsetWidth,hgt=popup.offsetHeight;
  const x=at?at[0]:r.left+r.width/2-w/2,y=at?at[1]:r.top-hgt-8;
  popup.style.left=Math.max(4,Math.min(x,innerWidth-w-4))+'px';popup.style.top=Math.max(4,Math.min(y,innerHeight-hgt-4))+'px';
  popup.querySelector('button')?.focus();
 }));
}

// ----- start menu -----
const pins=()=>(layout.start||DEFAULT_PINS).map(id=>apps.find(a=>a.id===id)).filter(Boolean);
function appButton(a,cls){
 const b=h('button',{class:cls,type:'button',title:a.comment||a.name},a.icon?h('img',{src:a.icon,alt:''}):icon('grid'),h('span',{},a.name));
 b.addEventListener('click',()=>{toggleStart(false);act(()=>call('apps.launch',{id:a.id}));});
 b.addEventListener('contextmenu',ev=>{ev.preventDefault();ev.stopPropagation();appMenu(a,b,[ev.clientX,ev.clientY]);});
 return b;
}
function appMenu(a,anchor,at){
 const pinned=(layout.start||DEFAULT_PINS).includes(a.id);
 const dockKey={'thunar.desktop':'files','xfce4-terminal.desktop':'terminal','org.gnome.Software.desktop':'store'}[a.id]||'app:'+a.id;
 const onBar=layout.dock.includes(dockKey);
 openPopup(anchor,[
  {label:'Openen',run:()=>{toggleStart(false);return call('apps.launch',{id:a.id});}},
  {label:pinned?'Losmaken van Start':'Vastmaken aan Start',run:()=>{const list=(layout.start||DEFAULT_PINS.filter(id=>apps.some(x=>x.id===id))).filter(id=>id!==a.id);layout={...layout,start:pinned?list:[...list,a.id]};saveLayout().then(()=>start&&showStart());}},
  {label:onBar?'Losmaken van de taakbalk':'Aan de taakbalk vastmaken',run:()=>saveDock(onBar?layout.dock.filter(k=>k!==dockKey):[...layout.dock,dockKey])},
  {label:'Op het bureaublad zetten',run:()=>{layout={...layout,items:[...(layout.items||[]),{id:'i'+Date.now().toString(36),kind:'app',target:a.id,name:a.name}]};saveLayout().then(()=>toast(a.name+' staat op het bureaublad.'));}},
 ],at);
}
function toggleStart(open=!start){
 if(!open){if(!start)return;start.remove();start=null;closePopup();render();call('start.toggle',{open:false}).catch(()=>{});return;}
 if(start)return;
 start=h('section',{class:'start-menu',role:'dialog','aria-label':'Start'});
 // Height from the screen, not from 100vh: this surface is only as high as the bar until it grows.
 start.style.setProperty('--start-max',Math.max(320,Math.min(680,(screen.height||900)-120))+'px');
 document.body.append(start);showStart();
 call('start.toggle',{open:true}).catch(()=>{});
 render();
}
function showStart(view='pinned'){
 if(!start)return;
 const search=h('input',{type:'search',class:'start-search',placeholder:'Zoek naar programma\'s','aria-label':'Zoek naar programma\'s'});
 const body=h('div',{class:'start-body'});
 const allBtn=h('button',{type:'button',class:'link'},view==='all'?'‹ Terug':'Alle apps ›');
 allBtn.addEventListener('click',()=>showStart(view==='all'?'pinned':'all'));
 const fill=()=>{
  const q=search.value.trim().toLowerCase();
  if(q){
   const found=apps.filter(a=>(a.name+' '+a.comment+' '+a.keywords).toLowerCase().includes(q)).slice(0,24);
   body.replaceChildren(h('h2',{},'Beste resultaten'),found.length?h('div',{class:'start-list'},...found.map(a=>appButton(a,'start-row'))):h('p',{class:'muted'},'Niets gevonden.'));
   return;
  }
  if(view==='all'){
   const groups=new Map();for(const a of apps){const L=(a.name[0]||'#').toUpperCase();if(!groups.has(L))groups.set(L,[]);groups.get(L).push(a);}
   body.replaceChildren(h('div',{class:'start-head'},h('h2',{},'Alle apps'),allBtn),h('div',{class:'start-list all'},...[...groups].flatMap(([L,list])=>[h('div',{class:'letter'},L),...list.map(a=>appButton(a,'start-row'))])));
   return;
  }
  const p=pins();
  body.replaceChildren(h('div',{class:'start-head'},h('h2',{},'Vastgemaakt'),allBtn),
   p.length?h('div',{class:'start-grid'},...p.map(a=>appButton(a,'start-tile'))):h('p',{class:'muted'},'Rechtsklik op een programma in Alle apps om het hier vast te maken.'),
   h('div',{class:'start-head'},h('h2',{},'Snel naar')),
   h('div',{class:'start-places'},...[['Documenten','documents'],['Downloads','downloads'],['Afbeeldingen','pictures'],['Muziek','music']].map(([name,id])=>{
    const b=h('button',{type:'button',class:'start-place'},icon('folder'),h('span',{},name));
    b.addEventListener('click',async()=>{toggleStart(false);const pl=(await call('files.places')).find(x=>x.id===id);if(pl)act(()=>call('open.path',{path:pl.path}));});return b;})));
 };
 search.addEventListener('input',fill);
 search.addEventListener('keydown',e=>{if(e.key==='Enter'){const first=body.querySelector('.start-row,.start-tile');if(first)first.click();}});
 const userBtn=h('button',{type:'button',class:'start-user'},h('span',{class:'avatar','aria-hidden':'true'},(user.fullName||user.name||'?').slice(0,1).toUpperCase()),h('span',{},user.fullName||user.name||'Account'));
 userBtn.addEventListener('click',()=>{toggleStart(false);act(()=>call('run',{tool:'control',page:'users'}));});
 const settingsBtn=h('button',{type:'button',class:'start-icon',title:'Instellingen','aria-label':'Instellingen'},icon('gear'));
 settingsBtn.addEventListener('click',()=>{toggleStart(false);act(()=>call('run',{tool:'control'}));});
 const powerBtn=h('button',{type:'button',class:'start-icon',title:'Aan/uit','aria-label':'Aan/uit'},icon('power'));
 powerBtn.addEventListener('click',()=>powerMenu(powerBtn));
 start.replaceChildren(h('div',{class:'start-glow','aria-hidden':'true'}),search,body,h('footer',{class:'start-foot'},userBtn,h('span',{class:'grow'}),settingsBtn,powerBtn));
 fill();resize();search.focus();
}
function powerMenu(anchor){
 const ask=(label,action)=>openPopup(anchor,[{label:`Ja, ${label.toLowerCase()} (niet-opgeslagen werk kan verloren gaan)`,run:()=>{toggleStart(false);return call('power',{action});}},{label:'Annuleren',run:()=>{}}]);
 openPopup(anchor,[
  {label:'Vergrendelen',run:()=>{toggleStart(false);return call('power',{action:'lock'});}},
  {label:'Afmelden',run:()=>ask('Afmelden','logout')},
  {label:'Opnieuw opstarten',run:()=>ask('Opnieuw opstarten','reboot')},
  {label:'Afsluiten',run:()=>ask('Afsluiten','poweroff')},
 ]);
}

addEventListener('keydown',e=>{
 if(e.key==='Escape'){if(popup){e.preventDefault();closePopup();return;}if(start){e.preventDefault();toggleStart(false);return;}}
 if(!popup&&!start&&(e.key==='ContextMenu'||(e.shiftKey&&e.key==='F10'))&&document.activeElement?.classList.contains('item')){e.preventDefault();document.activeElement.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true}));}
});
addEventListener('pointerdown',e=>{
 if(popup&&!popup.contains(e.target)){closePopup();}
 else if(start&&!start.contains(e.target)&&!e.target.closest?.('.start-button'))toggleStart(false);
},true);
addEventListener('blur',()=>{closePopup();if(start)toggleStart(false);});

async function loadApps(){
 try{apps=await call('apps.list');}catch{}
 try{const b=await call('browser.list');browserIcon=b.apps.find(a=>a.id===b.default)?.icon||null;}catch{}
}
async function init(){
 const config=await call('config.get');applySettings({...config.settings,colors:config.world.colors});
 if(config.layout)layout=config.layout;user=config.user||{};
 await loadApps();
 try{windows=await call('windows.list');}catch{}
 render();window.__universePageReady?.();
}
on('windows',list=>{windows=list||[];render();});
on('layout',l=>{if(l){layout=l;render();}});
on('apps-changed',()=>loadApps().then(()=>{render();if(start)showStart();}));
on('start-toggle',()=>toggleStart());
on('config',c=>{applySettings({...c.settings,colors:c.world.colors});user=c.user||user;});
init();
