import {call,on,applySettings,toast,h,icon} from './api.js';
// The dock: the user's own list (layout.dock) plus every open window that is not in it. A dot shows that a program
// is open; clicking an open program brings its window forward, otherwise it starts. Everything is optional: drag a
// button to reorder, right click to remove it; programs are added from the Applications planet or own items in
// space ("Aan het dock vastmaken"). The shell sizes the surface to fit; with no buttons left the dock disappears.

const DOCK_HEIGHT=64;
// match: lower-case parts of the Wayland app id that belong to this program.
const BUILTIN={
 space:{name:'Ruimtewereld',iconName:'planet',home:true,match:[],click:()=>call('desktop.show')},
 files:{name:'Bestanden',desktop:'thunar.desktop',iconName:'folder',match:['thunar'],click:()=>call('run',{tool:'files'})},
 browser:{name:'Internet',iconName:'globe',match:['firefox','chrome','chromium','epiphany','brave'],click:openBrowser},
 terminal:{name:'Terminal',desktop:'xfce4-terminal.desktop',iconName:'windows',match:['xfce4-terminal','terminal'],click:()=>call('run',{tool:'terminal'})},
 store:{name:'Softwarewinkel',desktop:'org.gnome.Software.desktop',iconName:'store',match:['gnome.software','gnome-software'],click:()=>call('run',{tool:'software'})},
 control:{name:'Controlecentrum',iconName:'gear',match:['universeos.controlcenter'],click:()=>call('run',{tool:'control'})},
};
let windows=[],apps=[],browserIcon=null,layout={dock:Object.keys(BUILTIN)},menu=null;
const root=h('nav',{class:'dock','aria-label':'Dock'});
document.body.append(root);

async function openBrowser(){
 const b=await call('browser.list');
 if(b.default)return call('apps.launch',{id:b.default});
 return call('world.open',{id:'chat'}); // no default yet: the Internet planet lets you choose one
}
/** The program behind a dock entry ('files', or 'app:org.gnome.Calculator.desktop'). */
function entry(key){
 if(BUILTIN[key]){
  const b=BUILTIN[key],a=b.desktop&&apps.find(x=>x.id===b.desktop);
  return {key,...b,img:key==='browser'?browserIcon:a?.icon};
 }
 const id=key.slice(4),a=apps.find(x=>x.id===id),base=id.replace(/\.desktop$/,'').toLowerCase();
 return {key,name:a?.name||base,img:a?.icon,iconName:'grid',match:[base,base.split('.').pop()],click:()=>call('apps.launch',{id})};
}
const owns=(e,w)=>e.match.some(m=>m&&(w.appId||'').toLowerCase().includes(m));

function button({name,img,iconName,home,open,active,onClick}){
 const b=h('button',{class:`item${home?' home':''}${open?' open':''}${active?' active':''}`,type:'button',title:name,
  'aria-label':name+(open?' (geopend)':'')},img?h('img',{src:img,alt:''}):icon(iconName),h('span',{class:'dot','aria-hidden':'true'}));
 b.addEventListener('click',()=>{if(b.dataset.dragged){delete b.dataset.dragged;return;}Promise.resolve().then(onClick).catch(e=>toast(e.message));});
 return b;
}
function render(){
 closeMenu(false);
 const entries=layout.dock.map(entry);
 const pinned=entries.map(e=>{
  const mine=windows.filter(w=>owns(e,w));
  const b=button({name:e.name,img:e.img,iconName:e.iconName,home:e.home,open:mine.length>0,active:mine.some(w=>w.activated),
   onClick:()=>mine.length?call('windows.activate',{id:mine[0].id}):e.click()});
  reorderable(b,e.key);
  b.addEventListener('contextmenu',ev=>{ev.preventDefault();openMenu(b,[
   {label:mine.length?'Naar voren halen':'Openen',run:()=>mine.length?call('windows.activate',{id:mine[0].id}):e.click()},
   {label:'Uit het dock halen',run:()=>save(layout.dock.filter(k=>k!==e.key))}]);});
  return b;
 });
 const others=windows.filter(w=>!entries.some(e=>owns(e,w)));
 root.replaceChildren(...pinned,...(others.length&&pinned.length?[h('span',{class:'sep','aria-hidden':'true'})]:[]),
  ...others.map(w=>button({name:w.title||w.appName||'Venster',img:w.icon,iconName:'grid',open:true,active:w.activated,onClick:()=>call('windows.activate',{id:w.id})})));
 resize();
}
const resize=(height)=>call('dock.size',{width:root.children.length?Math.ceil(root.offsetWidth)+4:0,height:height||DOCK_HEIGHT}).catch(()=>{});
function save(dock){layout={...layout,dock};render();call('layout.set',{layout}).then(l=>{layout=l;}).catch(e=>toast('Dock opslaan mislukt: '+e.message));}

/** Drag a dock button sideways to give it another place. */
function reorderable(b,key){
 let start=null,dragging=false;b.dataset.key=key;
 // Followed on the whole page: WebKitGTK does not keep mouse pointer capture.
 const moveTo=e=>{
  if(start==null)return;const dx=e.clientX-start;
  if(!dragging){if(Math.abs(dx)<6)return;dragging=true;b.classList.add('dragging');}
  b.style.translate=dx+'px 0';
 };
 b.addEventListener('pointerdown',e=>{if(e.button!==0)return;start=e.clientX;addEventListener('pointermove',moveTo);addEventListener('pointerup',end);addEventListener('pointercancel',end);});
 const end=e=>{
  removeEventListener('pointermove',moveTo);removeEventListener('pointerup',end);removeEventListener('pointercancel',end);
  if(start==null)return;start=null;if(!dragging)return;dragging=false;b.dataset.dragged='1';b.classList.remove('dragging');b.style.translate='';
  const others=[...root.querySelectorAll('.item[data-key]')].filter(x=>x!==b);
  const keys=layout.dock.filter(k=>k!==key);let at=keys.length;
  others.slice(0,keys.length).forEach((x,i)=>{const r=x.getBoundingClientRect();if(at===keys.length&&e.clientX<r.left+r.width/2)at=i;});
  keys.splice(at,0,key);if(keys.join()!==layout.dock.join())save(keys);
 };
 b.addEventListener('pointerup',end);b.addEventListener('pointercancel',end);
}

function closeMenu(shrink=true){if(!menu)return;menu.remove();menu=null;if(shrink)resize();}
/** The surface is only as high as the dock; it grows upwards while a menu is open. */
function openMenu(anchor,entries){
 closeMenu(false);
 menu=h('div',{class:'ctx',role:'menu'});
 for(const e of entries){const m=h('button',{type:'button',role:'menuitem'},e.label);m.addEventListener('click',()=>{closeMenu();Promise.resolve().then(e.run).catch(err=>toast(err.message));});menu.append(m);}
 document.body.append(menu);
 const r=anchor.getBoundingClientRect(),mw=menu.offsetWidth;
 menu.style.left=Math.max(4,Math.min(r.left+r.width/2-mw/2,innerWidth-mw-4))+'px';
 resize(DOCK_HEIGHT+menu.offsetHeight+10);
 menu.querySelector('button')?.focus();
}
addEventListener('keydown',e=>{
 if(menu&&e.key==='Escape'){e.preventDefault();closeMenu();}
 if(!menu&&(e.key==='ContextMenu'||(e.shiftKey&&e.key==='F10'))&&document.activeElement?.classList.contains('item')){e.preventDefault();document.activeElement.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true}));}
});
addEventListener('pointerdown',e=>{if(menu&&!menu.contains(e.target))closeMenu();},true);
addEventListener('blur',()=>closeMenu());

async function loadIcons(){
 try{apps=await call('apps.list');}catch{}
 try{const b=await call('browser.list');browserIcon=b.apps.find(a=>a.id===b.default)?.icon||null;}catch{}
}
async function start(){
 const config=await call('config.get');applySettings({...config.settings,colors:config.world.colors});
 if(config.layout)layout=config.layout;
 await loadIcons();
 try{windows=await call('windows.list');}catch{}
 render();window.__universePageReady?.();
}
on('windows',list=>{windows=list||[];render();});
on('layout',l=>{if(l){layout=l;render();}});
on('apps-changed',()=>loadIcons().then(render));
on('config',c=>applySettings({...c.settings,colors:c.world.colors}));
start();
