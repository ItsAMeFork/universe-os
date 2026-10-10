import {call,on,applySettings,toast,h,icon} from './api.js';
// The dock: fixed programs plus every open window that is not one of them. A dot shows that a program is open;
// clicking an open program brings its window forward, otherwise it starts. The shell sizes the surface to fit.

// match: lower-case parts of the Wayland app id that belong to this program.
const PINNED=[
 {id:'space',name:'Ruimtewereld',iconName:'planet',home:true,match:[],click:()=>call('desktop.show')},
 {id:'files',name:'Bestanden',desktop:'thunar.desktop',iconName:'folder',match:['thunar'],click:()=>call('run',{tool:'files'})},
 {id:'browser',name:'Internet',iconName:'globe',match:['firefox','chrome','chromium','epiphany','brave'],click:openBrowser},
 {id:'terminal',name:'Terminal',desktop:'xfce4-terminal.desktop',iconName:'windows',match:['xfce4-terminal','terminal'],click:()=>call('run',{tool:'terminal'})},
 {id:'store',name:'Softwarewinkel',desktop:'org.gnome.Software.desktop',iconName:'store',match:['gnome.software','gnome-software'],click:()=>call('run',{tool:'software'})},
 {id:'control',name:'Controlecentrum',iconName:'gear',match:['universeos.controlcenter'],click:()=>call('run',{tool:'control'})},
];
let windows=[],icons={};
const root=h('nav',{class:'dock','aria-label':'Dock'});
document.body.append(root);

async function openBrowser(){
 const b=await call('browser.list');
 if(b.default)return call('apps.launch',{id:b.default});
 return call('world.open',{id:'chat'}); // no default yet: the Internet planet lets you choose one
}
const owns=(p,w)=>p.match.some(m=>(w.appId||'').toLowerCase().includes(m));

function button({name,img,iconName,home,open,active,onClick}){
 const b=h('button',{class:`item${home?' home':''}${open?' open':''}${active?' active':''}`,type:'button',title:name,
  'aria-label':name+(open?' (geopend)':'')},img?h('img',{src:img,alt:''}):icon(iconName),h('span',{class:'dot','aria-hidden':'true'}));
 b.addEventListener('click',()=>Promise.resolve().then(onClick).catch(e=>toast(e.message)));
 return b;
}
function render(){
 const items=PINNED.map(p=>{
  const mine=windows.filter(w=>owns(p,w));
  return button({name:p.name,img:icons[p.id],iconName:p.iconName,home:p.home,open:mine.length>0,active:mine.some(w=>w.activated),
   onClick:()=>mine.length?call('windows.activate',{id:mine[0].id}):p.click()});
 });
 const others=windows.filter(w=>!PINNED.some(p=>owns(p,w)));
 root.replaceChildren(...items,...(others.length?[h('span',{class:'sep','aria-hidden':'true'})]:[]),
  ...others.map(w=>button({name:w.title||w.appName||'Venster',img:w.icon,iconName:'grid',open:true,active:w.activated,onClick:()=>call('windows.activate',{id:w.id})})));
 call('dock.size',{width:Math.ceil(root.offsetWidth)+4}).catch(()=>{});
}

async function start(){
 const config=await call('config.get');applySettings({...config.settings,colors:config.world.colors});
 try{for(const a of await call('apps.list'))for(const p of PINNED)if(p.desktop===a.id&&a.icon)icons[p.id]=a.icon;}catch{}
 try{const b=await call('browser.list');const def=b.apps.find(a=>a.id===b.default);if(def?.icon)icons.browser=def.icon;}catch{}
 try{windows=await call('windows.list');}catch{}
 render();window.__universePageReady?.();
}
on('windows',list=>{windows=list||[];render();});
on('config',c=>applySettings({...c.settings,colors:c.world.colors}));
start();
