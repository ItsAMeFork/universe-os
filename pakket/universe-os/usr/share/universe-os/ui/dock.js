import {call,on,applySettings,toast,h,icon} from './api.js';
// Taskbar (Axel, 10 Oct: "like Windows, in the style of the concept photos"). The start menu is its own surface
// (start.html); the start button only asks the shell to show or hide it.
// Left the start button (Universe planet), then the user's own buttons (layout.dock) and every open window that is
// not one of them. A dot shows that a program is open; clicking an open program brings its window forward.
// Everything except the start button is optional: drag to reorder, right click to remove.
// The surface grows upwards while a small popup menu is open.

const DOCK_HEIGHT=64;
// match: lower-case parts of the Wayland app id that belong to this program.
const BUILTIN={
 space:{name:'Bureaublad tonen',iconName:'display',match:[],click:()=>call('desktop.show')},
 files:{name:'Bestanden',desktop:'thunar.desktop',iconName:'folder',match:['thunar'],click:()=>call('run',{tool:'files'})},
 browser:{name:'Internet',iconName:'globe',match:['firefox','chrome','chromium','epiphany','brave'],click:openBrowser},
 terminal:{name:'Terminal',desktop:'xfce4-terminal.desktop',iconName:'windows',match:['xfce4-terminal','terminal'],click:()=>call('run',{tool:'terminal'})},
 store:{name:'Softwarewinkel',desktop:'org.gnome.Software.desktop',iconName:'store',match:['gnome.software','gnome-software'],click:()=>call('run',{tool:'software'})},
 control:{name:'Controlecentrum',iconName:'gear',match:['universeos.controlcenter'],click:()=>call('run',{tool:'control'})},
};
let windows=[],apps=[],browserIcon=null,layout={dock:Object.keys(BUILTIN)},popup=null,startOpen=false;
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
 const startButton=h('button',{class:'item start-button'+(startOpen?' active':''),type:'button',title:'Start','aria-label':'Start','aria-expanded':String(startOpen),
  html:'<svg viewBox="0 0 32 32" aria-hidden="true"><defs><radialGradient id="sb" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#ffd2a0"/><stop offset=".55" stop-color="#ff8a3d"/><stop offset="1" stop-color="#a33c10"/></radialGradient></defs><circle cx="16" cy="16" r="8.5" fill="url(#sb)"/><ellipse cx="16" cy="16" rx="14" ry="5" fill="none" stroke="#85ffe3" stroke-width="1.6" transform="rotate(-18 16 16)"/></svg>'});
 startButton.addEventListener('click',()=>call('start.toggle').catch(e=>toast(e.message)));
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
/** Surface size: the bar, plus room above it for a popup. */
function resize(){
 const width=Math.max(Math.ceil(bar.offsetWidth)+4,popup?Math.ceil(popup.offsetWidth)+8:0);
 const height=DOCK_HEIGHT+(popup?Math.ceil(popup.offsetHeight)+12:0);
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

// ----- popup menu (right click on a taskbar button) -----
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

addEventListener('keydown',e=>{
 if(e.key==='Escape'&&popup){e.preventDefault();closePopup();return;}
 if(!popup&&(e.key==='ContextMenu'||(e.shiftKey&&e.key==='F10'))&&document.activeElement?.classList.contains('item')){e.preventDefault();document.activeElement.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true}));}
});
addEventListener('pointerdown',e=>{
 if(popup&&!popup.contains(e.target))closePopup();
 if(startOpen&&!e.target.closest?.('.start-button'))call('surface.hide',{name:'start'}).catch(()=>{});
},true);
addEventListener('blur',closePopup);

async function loadApps(){
 try{apps=await call('apps.list');}catch{}
 try{const b=await call('browser.list');browserIcon=b.apps.find(a=>a.id===b.default)?.icon||null;}catch{}
}
async function init(){
 const config=await call('config.get');applySettings({...config.settings,colors:config.world.colors});
 if(config.layout)layout=config.layout;
 await loadApps();
 try{windows=await call('windows.list');}catch{}
 render();window.__universePageReady?.();
}
on('windows',list=>{windows=list||[];render();});
on('layout',l=>{if(l){layout=l;render();}});
on('apps-changed',()=>loadApps().then(render));
on('start-state',open=>{startOpen=!!open;render();});
on('config',c=>applySettings({...c.settings,colors:c.world.colors}));
init();
