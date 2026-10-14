import {call,on,applySettings,toast,h,icon} from './api.js';
// Start menu (Axel, 10 Oct: "a menu like Windows, in the style of the concept photos"). Its own fixed-size layer
// surface above the taskbar (resizing the taskbar surface did not reliably resize the page, VM 10 Oct). Opened by the
// start button or the Windows key; closes with Escape, a click elsewhere, or after starting something.
// Search, pinned programs (layout.start), all programs, places, the user and the power actions.

const DEFAULT_PINS=['firefox-esr.desktop','google-chrome.desktop','thunar.desktop','org.gnome.Software.desktop','xfce4-terminal.desktop',
 'mousepad.desktop','org.gnome.Calculator.desktop','atril.desktop','io.github.celluloid_player.Celluloid.desktop','org.gnome.SystemMonitor.desktop',
 'universe-windows-apps.desktop','file-roller.desktop'];
const DOCK_BUILTIN_APPS={'thunar.desktop':'files','xfce4-terminal.desktop':'terminal','org.gnome.Software.desktop':'store'};
let apps=[],user={},layout={dock:[],start:null,items:[]},popup=null,view='pinned';
const menu=h('section',{class:'start-menu',role:'dialog','aria-label':'Start'});
document.body.append(menu);

const act=fn=>Promise.resolve().then(fn).catch(e=>toast(e.message));
const hide=()=>call('surface.hide',{name:'start'}).catch(()=>{});
const launch=id=>{hide();act(()=>call('apps.launch',{id}));};
function saveLayout(){return call('layout.set',{layout}).then(l=>{layout=l;}).catch(e=>toast('Opslaan mislukt: '+e.message));}

// ----- small popup menu (right click on a program, power button) -----
function closePopup(){popup?.remove();popup=null;}
function openPopup(x,y,entries){
 closePopup();
 popup=h('div',{class:'ctx',role:'menu'});
 for(const e of entries){const m=h('button',{type:'button',role:'menuitem'},e.label);m.addEventListener('click',()=>{closePopup();act(e.run);});popup.append(m);}
 document.body.append(popup);
 const w=popup.offsetWidth,hgt=popup.offsetHeight;
 popup.style.left=Math.max(4,Math.min(x,innerWidth-w-4))+'px';popup.style.top=Math.max(4,Math.min(y,innerHeight-hgt-4))+'px';
 popup.querySelector('button')?.focus();
}

const pins=()=>(layout.start||DEFAULT_PINS).map(id=>apps.find(a=>a.id===id)).filter(Boolean);
function appButton(a,cls){
 const b=h('button',{class:cls,type:'button',title:a.comment||a.name},a.icon?h('img',{src:a.icon,alt:''}):icon('grid'),h('span',{},a.name));
 b.addEventListener('click',()=>launch(a.id));
 b.addEventListener('contextmenu',ev=>{ev.preventDefault();appMenu(a,ev.clientX,ev.clientY);});
 b._menu=()=>{const r=b.getBoundingClientRect();appMenu(a,r.left+r.width/2,r.top+r.height/2);};
 return b;
}
function appMenu(a,x,y){
 const pinned=(layout.start||DEFAULT_PINS).includes(a.id);
 const dockKey=DOCK_BUILTIN_APPS[a.id]||'app:'+a.id,onBar=layout.dock.includes(dockKey);
 openPopup(x,y,[
  {label:'Openen',run:()=>launch(a.id)},
  {label:pinned?'Losmaken van Start':'Vastmaken aan Start',run:async()=>{
   const list=(layout.start||DEFAULT_PINS.filter(id=>apps.some(x=>x.id===id))).filter(id=>id!==a.id);
   layout={...layout,start:pinned?list:[...list,a.id]};await saveLayout();show();}},
  {label:onBar?'Losmaken van de taakbalk':'Aan de taakbalk vastmaken',run:()=>{layout={...layout,dock:onBar?layout.dock.filter(k=>k!==dockKey):[...layout.dock,dockKey]};return saveLayout();}},
  {label:'Op het bureaublad zetten',run:async()=>{layout={...layout,items:[...(layout.items||[]),{id:'i'+Date.now().toString(36),kind:'app',target:a.id,name:a.name}]};await saveLayout();toast(a.name+' staat op het bureaublad.');}},
 ]);
}
function powerMenu(anchor){
 const r=anchor.getBoundingClientRect(),x=r.right-230,y=r.top-180;
 const ask=(label,action)=>openPopup(x,y+90,[{label:`Ja, ${label.toLowerCase()} (niet-opgeslagen werk kan verloren gaan)`,run:()=>{hide();return call('power',{action});}},{label:'Annuleren',run:()=>{}}]);
 openPopup(x,y,[
  {label:'Vergrendelen',run:()=>{hide();return call('power',{action:'lock'});}},
  {label:'Afmelden',run:()=>ask('Afmelden','logout')},
  {label:'Opnieuw opstarten',run:()=>ask('Opnieuw opstarten','reboot')},
  {label:'Afsluiten',run:()=>ask('Afsluiten','poweroff')},
 ]);
}

function show(){
 closePopup();
 const search=h('input',{type:'search',class:'start-search',placeholder:'Zoek naar programma\'s','aria-label':'Zoek naar programma\'s'});
 const body=h('div',{class:'start-body'});
 const fill=()=>{
  const q=search.value.trim().toLowerCase();
  if(q){
   const found=apps.filter(a=>(a.name+' '+a.comment+' '+a.keywords).toLowerCase().includes(q)).slice(0,24);
   body.replaceChildren(h('h2',{},'Beste resultaten'),found.length?h('div',{class:'start-list'},...found.map(a=>appButton(a,'start-row'))):h('p',{class:'muted'},'Niets gevonden.'));
   return;
  }
  const toggle=h('button',{type:'button',class:'link'},view==='all'?'‹ Terug':'Alle apps ›');
  toggle.addEventListener('click',()=>{view=view==='all'?'pinned':'all';fill();});
  if(view==='all'){
   const groups=new Map();for(const a of apps){const L=(a.name[0]||'#').toUpperCase();if(!groups.has(L))groups.set(L,[]);groups.get(L).push(a);}
   body.replaceChildren(h('div',{class:'start-head'},h('h2',{},'Alle apps'),toggle),h('div',{class:'start-list all'},...[...groups].flatMap(([L,list])=>[h('div',{class:'letter'},L),...list.map(a=>appButton(a,'start-row'))])));
   return;
  }
  const p=pins();
  body.replaceChildren(h('div',{class:'start-head'},h('h2',{},'Vastgemaakt'),toggle),
   p.length?h('div',{class:'start-grid'},...p.map(a=>appButton(a,'start-tile'))):h('p',{class:'muted'},'Rechtsklik op een programma in Alle apps om het hier vast te maken.'),
   h('div',{class:'start-head'},h('h2',{},'Snel naar')),
   h('div',{class:'start-places'},...[['Documenten','documents'],['Downloads','downloads'],['Afbeeldingen','pictures'],['Muziek','music']].map(([name,id])=>{
    const b=h('button',{type:'button',class:'start-place'},icon('folder'),h('span',{},name));
    b.addEventListener('click',async()=>{hide();const pl=(await call('files.places')).find(x=>x.id===id);if(pl)act(()=>call('open.path',{path:pl.path}));});return b;})));
 };
 search.addEventListener('input',fill);
 search.addEventListener('keydown',e=>{if(e.key==='Enter'){const first=body.querySelector('.start-row,.start-tile');if(first)first.click();}});
 const userBtn=h('button',{type:'button',class:'start-user'},h('span',{class:'avatar','aria-hidden':'true'},(user.fullName||user.name||'?').slice(0,1).toUpperCase()),h('span',{},user.fullName||user.name||'Account'));
 userBtn.addEventListener('click',()=>{hide();act(()=>call('run',{tool:'control',page:'users'}));});
 const settingsBtn=h('button',{type:'button',class:'start-icon',title:'Instellingen','aria-label':'Instellingen'},icon('gear'));
 settingsBtn.addEventListener('click',()=>{hide();act(()=>call('run',{tool:'control'}));});
 const powerBtn=h('button',{type:'button',class:'start-icon',title:'Aan/uit','aria-label':'Aan/uit'},icon('power'));
 powerBtn.addEventListener('click',()=>powerMenu(powerBtn));
 menu.replaceChildren(h('div',{class:'start-glow','aria-hidden':'true'}),search,body,h('footer',{class:'start-foot'},userBtn,h('span',{class:'grow'}),settingsBtn,powerBtn));
 fill();search.focus();
}

addEventListener('keydown',e=>{
 if(e.key==='Escape'){e.preventDefault();if(popup)closePopup();else hide();return;}
 if(popup&&(e.key==='ArrowDown'||e.key==='ArrowUp')){e.preventDefault();const bs=[...popup.querySelectorAll('button')],i=bs.indexOf(document.activeElement);bs[(i+(e.key==='ArrowDown'?1:-1)+bs.length)%bs.length]?.focus();return;}
 if(e.key==='ContextMenu'||(e.shiftKey&&e.key==='F10')){const b=document.activeElement;if(b?._menu){e.preventDefault();b._menu();}}
});
addEventListener('pointerdown',e=>{if(popup&&!popup.contains(e.target))closePopup();},true);
// A click on the empty, transparent part of this surface counts as "elsewhere".
document.body.addEventListener('pointerdown',e=>{if(e.target===document.body||e.target===document.documentElement)hide();});

async function load(){
 try{apps=await call('apps.list');}catch{}
 try{const c=await call('config.get');applySettings({...c.settings,colors:c.world.colors});user=c.user||{};if(c.layout)layout=c.layout;}catch{}
}
on('start-shown',async()=>{view='pinned';show();await load();show();});
on('layout',l=>{if(l)layout=l;});
on('apps-changed',()=>{apps=[];});
on('config',c=>{applySettings({...c.settings,colors:c.world.colors});user=c.user||user;});
load().then(()=>{show();window.__universePageReady?.();});
