import {updatesView} from './updates-ui.js';
import {call,on,applySettings,motionAllowed,toast,h,icon} from './api.js';
import {globe,earth,paintEarths,starfield,pixelSize} from './globe.js';
import {debugFPS,afterPaint} from './performance.js';
import {SETTINGS} from './settings-index.js';
import {keepTab} from './focus.js';
// The 3D desktop (Axel, 10 Oct: "the desktop in 3D, every program a planet somewhere that you arrange yourself,
// zoom in and out, also turn in 3D"). The Earth in the middle is the personal folder; folders and files from the
// Bureaublad circle it; every program is a planet in a galaxy, grouped by kind. Wheel = zoom, drag empty space = move,
// right drag = turn, drag a planet = place it, double click / Enter = open, right click = menu. Nothing animates while
// you do nothing: the 3D projection is computed here and only redrawn on input, which keeps it light without a GPU
// (floating background planets cost 60-70% of a core in the VM). Positions, hidden planets and the view are saved
// in layout.json (space). The planet rooms still exist for search results and the start menu (open-planet).

const KIND={local:['local','Werkt lokaal'],online:['online','Internet nodig'],mixed:['mixed','Lokaal + online']};
let config=null,settings={},user={},current=null,lastFocus=null,appsCache=null;
let layout={planets:{},items:[],orbit:true,dock:[],icons:{},hiddenIcons:[],start:null,space:{pos:{},hidden:[],camera:null}};
let travelToken=0,backgroundBusy=false,initialFocus=true;
on('background-busy',v=>{backgroundBusy=!!v;});
const root=h('main',{class:'universe','aria-label':'Bureaublad van Universe OS'});
const sky=h('canvas',{class:'space-canvas','aria-hidden':'true'});
const layer=h('div',{class:'space-layer',role:'listbox','aria-label':'Ruimte met programma\'s, mappen en bestanden'});
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
 if(layout.space?.camera)cam={...cam,...layout.space.camera};
 await afterPaint();build();debugFPS();await afterPaint();
 call('world.ready',{milliseconds:performance.now()}).catch(()=>{});
 window.__universePageReady?.();
 setTimeout(paintEarths,1500);
}
const planetGlobe=(p,diameter)=>p.style==='earth'?earth(pixelSize(diameter)):globe(p.hue,!!p.rock,pixelSize(diameter));
function build(){
 root.replaceChildren(h('div',{class:'nebula','aria-hidden':'true'}),sky,layer,room);
 refreshSpace();
}

// ----- camera and projection -----
const FOV=900,BASE=128;
const DEFAULT_CAM={yaw:-.5,pitch:.42,dist:1650,tx:0,ty:0,tz:0};
let cam={...DEFAULT_CAM};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
function project([x,y,z]){
 const dx=x-cam.tx,dy=y-cam.ty,dz=z-cam.tz,cy=Math.cos(cam.yaw),sy=Math.sin(cam.yaw),cp=Math.cos(cam.pitch),sp=Math.sin(cam.pitch);
 const x1=dx*cy-dz*sy,z1=dx*sy+dz*cy,y2=dy*cp-z1*sp,depth=dy*sp+z1*cp+cam.dist;
 if(depth<30)return null;
 const s=FOV/depth;
 return {x:innerWidth/2+x1*s,y:innerHeight/2+y2*s,s,depth};
}
/** A vector in camera space (right, down, forward) back to world space. */
function unrotate(X,Y,Z){
 const cy=Math.cos(cam.yaw),sy=Math.sin(cam.yaw),cp=Math.cos(cam.pitch),sp=Math.sin(cam.pitch);
 const dy=Y*cp+Z*sp,z1=-Y*sp+Z*cp;
 return [X*cy+z1*sy,dy,-X*sy+z1*cy];
}
/** The world point under a screen point, in the plane through the camera target. */
function worldAt(sx,sy){
 const s=FOV/cam.dist,v=unrotate((sx-innerWidth/2)/s,(sy-innerHeight/2)/s,0);
 return [cam.tx+v[0],cam.ty+v[1],cam.tz+v[2]];
}

// ----- stars and orbits on one canvas (redrawn only when the view changes) -----
const STARS=Array.from({length:900},(_,i)=>{let s=(i*9301+49297)%233280;const r=()=>(s=(s*9301+49297)%233280)/233280;
 const u=r()*2-1,t=r()*Math.PI*2,q=Math.sqrt(1-u*u);return [q*Math.cos(t),u,q*Math.sin(t),.25+r()*.75,r()<.06];});
function drawSky(){
 const dpr=Math.min(devicePixelRatio||1,2),w=innerWidth,hgt=innerHeight;
 if(sky.width!==Math.round(w*dpr)||sky.height!==Math.round(hgt*dpr)){sky.width=Math.round(w*dpr);sky.height=Math.round(hgt*dpr);}
 const c=sky.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,hgt);
 const cy=Math.cos(cam.yaw),sy=Math.sin(cam.yaw),cp=Math.cos(cam.pitch),sp=Math.sin(cam.pitch);
 for(const [x,y,z,b,big] of STARS){ // stars are far away: they only turn with the camera
  const x1=x*cy-z*sy,z1=x*sy+z*cy,y2=y*cp-z1*sp,z2=y*sp+z1*cp;if(z2<=.05)continue;
  const px=w/2+x1/z2*FOV,py=hgt/2+y2/z2*FOV;if(px<0||py<0||px>w||py>hgt)continue;
  c.fillStyle=`rgba(208,224,255,${b})`;c.beginPath();c.arc(px,py,big?1.5:.7,0,7);c.fill();
 }
 // Orbits around the Earth (folders) and the galaxy ring of the programs, as real 3D circles.
 ring(c,420,'rgba(255,165,82,.55)',1.5);ring(c,1350,'rgba(133,255,227,.10)',1);ring(c,1900,'rgba(133,255,227,.06)',1);
}
function ring(c,r,color,width){
 c.strokeStyle=color;c.lineWidth=width;c.beginPath();let pen=false;
 for(let i=0;i<=96;i++){const a=i/96*Math.PI*2,p=project([Math.cos(a)*r,0,Math.sin(a)*r]);if(!p){pen=false;continue;}pen?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y);pen=true;}
 c.stroke();
}

// ----- objects: the Earth, desktop items and programs -----
let objects=[],selected=null,spaceToken=0,deskDir='';
const hash=s=>{let x=2166136261;for(const ch of s)x=Math.imul(x^ch.charCodeAt(0),16777619);return x>>>0;};
const CATS=['Network','Office','Graphics','AudioVideo','Game','Development','Utility','System','Settings'];
const mainCat=a=>a.game?'Game':CATS.find(c=>a.categories.includes(c))||'Other';
/** Default places: desktop items on the orange orbit, programs in clusters per kind on the galaxy ring. */
function defaultPos(o,index,count,clusterIndex,clusterCount,inCluster){
 if(o.kind==='earth')return [0,0,0];
 if(o.ring==='desk'){const a=index/Math.max(1,count)*Math.PI*2;return [Math.cos(a)*420,((hash(o.key)%60)-30),Math.sin(a)*420];}
 const ca=clusterIndex/Math.max(1,clusterCount)*Math.PI*2,R=1350+(clusterIndex%2)*550;
 const g=inCluster*2.39996,rr=200*Math.sqrt(inCluster+.5);
 return [Math.cos(ca)*R+Math.cos(g)*rr,((hash(o.key)%240)-120),Math.sin(ca)*R+Math.sin(g)*rr];
}
async function refreshSpace(){
 const token=++spaceToken;
 let desk={entries:[],dir:''},list=[];
 try{[desk,list]=await Promise.all([call('desktop.list'),apps()]);}catch(e){toast('Bureaublad laden mislukt: '+e.message);}
 if(token!==spaceToken)return;
 deskDir=desk.dir;
 const hidden=new Set(layout.space?.hidden||[]),saved=layout.space?.pos||{};
 const deskObjs=desk.entries.filter(e=>e.key!=='sys:home').map(e=>({...e,ring:'desk',size:e.kind==='folder'?130:110}));
 const home=desk.entries.find(e=>e.key==='sys:home');
 const earthObj={key:'sys:home',kind:'earth',name:'Persoonlijke map',target:home?.target||'',source:'system',size:380};
 const clusters=new Map();for(const a of list){const c=mainCat(a);if(!clusters.has(c))clusters.set(c,[]);clusters.get(c).push(a);}
 const clusterNames=[...clusters.keys()];
 const appObjs=[];
 clusterNames.forEach((c,ci)=>clusters.get(c).forEach((a,i)=>appObjs.push({key:'app:'+a.id,kind:'app',name:a.name,target:a.id,icon:a.icon,source:'app',
  size:a.game?160:150,hue:hash(a.id)%360,cluster:[ci,clusterNames.length,i]})));
 const all=[earthObj,...deskObjs,...appObjs].filter(o=>!hidden.has(o.key));
 all.forEach(o=>{
  const d=o.ring==='desk'?defaultPos(o,deskObjs.indexOf(o),deskObjs.length):o.kind==='app'?defaultPos(o,0,0,...o.cluster):defaultPos(o);
  o.pos=saved[o.key]||d;
 });
 objects=all;renderObjects();
}
function renderObjects(){
 const focusKey=document.activeElement?.closest?.('.sp-obj')?.dataset.key;
 layer.replaceChildren(...objects.map(objectEl));
 const again=(focusKey||(initialFocus?'sys:home':null));
 if(again){const el=layer.querySelector(`[data-key="${CSS.escape(again)}"]`);if(el){initialFocus=false;el.focus({preventScroll:true});}}
 requestRender();
}
function objectEl(o){
 let pic;
 if(o.kind==='earth')pic=earth(pixelSize(260));
 else if(o.kind==='app'){pic=globe(o.hue,o.hue%3===0,pixelSize(BASE));}
 else pic=null;
 const iconEl=o.kind==='earth'?null:o.icon?h('img',{class:'sp-icon',src:o.icon,alt:''}):icon(o.kind==='folder'?'folder':o.kind==='app'?'grid':'file','icon sp-icon');
 const b=h('button',{class:`sp-obj sp-${o.kind}${o.kind!=='app'&&o.kind!=='earth'?' sp-small':''}${selected===o.key?' selected':''}`,type:'button',role:'option',
  'data-key':o.key,'aria-label':o.name+(o.kind==='app'?', programma':o.kind==='folder'||o.kind==='earth'?', map':', bestand'),title:o.name},
  pic?h('span',{class:'sp-planet'},pic):null,iconEl,h('span',{class:'sp-label'},o.name));
 b._obj=o;o.el=b;
 b.addEventListener('click',()=>{if(wasDragged(b))return;select(o.key);});
 b.addEventListener('dblclick',()=>openObj(o));
 b.addEventListener('focus',()=>select(o.key,false));
 return b;
}
let frame=0;
function requestRender(){if(!frame)frame=requestAnimationFrame(render);}
function render(){
 frame=0;drawSky();
 for(const o of objects){
  const el=o.el;if(!el)continue;
  const p=project(o.pos),px=p?p.s*o.size:0;
  if(!p||px<3||p.x<-px||p.y<-px||p.x>innerWidth+px||p.y>innerHeight+px){el.style.display='none';continue;}
  el.style.display='';
  const k=px/BASE;
  el.style.transform=`translate(${(p.x-BASE/2).toFixed(1)}px,${(p.y-BASE/2).toFixed(1)}px) scale(${k.toFixed(4)})`;
  el.style.zIndex=String(Math.max(1,Math.round(100000-p.depth)));
  el.style.setProperty('--k',k.toFixed(4));
  el.classList.toggle('far',px<26);
  el.style.opacity=p.depth>9000?Math.max(.25,1-(p.depth-9000)/9000).toFixed(2):'';
 }
}
addEventListener('resize',requestRender);
function select(key,focus=true){
 selected=key;
 for(const el of layer.children){const on=el.dataset.key===key;el.classList.toggle('selected',on);el.setAttribute('aria-selected',String(on));if(on&&focus&&document.activeElement!==el)el.focus({preventScroll:true});}
}
function openObj(o){
 const fail=e=>toast(e.message);
 if(o.kind==='app')return launch(o.target);
 if(o.kind==='launcher')return call('desktop.launch',{path:o.target}).catch(fail);
 if(o.kind==='install')return call('run',{tool:'installer'}).catch(fail);
 return call('open.path',{path:o.target}).catch(fail);
}

// ----- saving -----
const sorted=v=>Array.isArray(v)?v.map(sorted):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,sorted(v[k])])):v;
const same=(a,b)=>JSON.stringify(sorted(a))===JSON.stringify(sorted(b));
function saveLayout(){return call('layout.set',{layout}).then(clean=>{layout=clean;}).catch(e=>toast('Indeling opslaan mislukt: '+e.message));}
on('layout',l=>{
 if(!l||same(l,layout))return;
 const before=layout;layout=l;
 // Only rebuild when what is in space changed (not when the view or a position was saved).
 if(!same({...l,space:{...l.space,camera:null,pos:{}}},{...before,space:{...before.space,camera:null,pos:{}}}))refreshSpace();
});
const space=()=>(layout.space=layout.space||{pos:{},hidden:[],camera:null});
function savePos(o){space().pos={...space().pos,[o.key]:o.pos.map(v=>Math.round(v*100)/100)};saveLayout();}
let camTimer=0;
function saveCamera(){clearTimeout(camTimer);camTimer=setTimeout(()=>{space().camera={...cam};saveLayout();},800);}

// ----- input: wheel zoom, drag to move, right drag to turn, drag a planet to place it -----
const wasDragged=el=>{if(!el?.dataset.dragged)return false;delete el.dataset.dragged;return true;};
let drag=null;
layer.addEventListener('pointerdown',e=>{
 if(current||(e.button!==0&&e.button!==2))return;
 const el=e.target.closest('.sp-obj');
 if(el&&e.target.closest('input'))return;
 drag={button:e.button,x:e.clientX,y:e.clientY,lastX:e.clientX,lastY:e.clientY,el,moved:false};
 if(el)delete el.dataset.dragged;
 addEventListener('pointermove',onDragMove);addEventListener('pointerup',onDragEnd);addEventListener('pointercancel',onDragEnd);
});
function onDragMove(e){
 if(!drag)return;
 const dx=e.clientX-drag.lastX,dy=e.clientY-drag.lastY;
 if(!drag.moved){if(Math.hypot(e.clientX-drag.x,e.clientY-drag.y)<6)return;drag.moved=true;root.classList.add('dragging');}
 drag.lastX=e.clientX;drag.lastY=e.clientY;
 if(drag.button===2){cam.yaw+=dx*.005;cam.pitch=clamp(cam.pitch+dy*.005,-1.45,1.45);}
 else if(drag.el){ // move the planet in the plane facing the camera, at its own depth
  const o=drag.el._obj,p=project(o.pos);if(p){const v=unrotate(dx/p.s,dy/p.s,0);o.pos=[o.pos[0]+v[0],o.pos[1]+v[1],o.pos[2]+v[2]];}
 }else{const s=FOV/cam.dist,v=unrotate(-dx/s,-dy/s,0);cam.tx+=v[0];cam.ty+=v[1];cam.tz+=v[2];}
 requestRender();
}
function onDragEnd(e){
 removeEventListener('pointermove',onDragMove);removeEventListener('pointerup',onDragEnd);removeEventListener('pointercancel',onDragEnd);
 if(!drag)return;const d=drag;drag=null;root.classList.remove('dragging');
 if(!d.moved){
  if(d.button===2){ // a right click without moving: the context menu
   if(d.el){select(d.el.dataset.key);openMenu(e.clientX,e.clientY,objectMenu(d.el._obj));}
   else openMenu(e.clientX,e.clientY,spaceMenu(e.clientX,e.clientY));
  }else if(!d.el)select(null,false);
  return;
 }
 if(d.el){d.el.dataset.dragged='1';savePos(d.el._obj);}else saveCamera();
}
layer.addEventListener('contextmenu',e=>e.preventDefault());
layer.addEventListener('wheel',e=>{
 if(current)return;e.preventDefault();
 const before=cam.dist;cam.dist=clamp(cam.dist*Math.exp(e.deltaY*(e.deltaMode===1?.06:.0015)),180,12000);
 // zoom towards the pointer, like a map
 const s=FOV/before,f=1-cam.dist/before,v=unrotate((e.clientX-innerWidth/2)/s*f,(e.clientY-innerHeight/2)/s*f,0);
 cam.tx+=v[0];cam.ty+=v[1];cam.tz+=v[2];
 requestRender();saveCamera();
},{passive:false});
/** Flies the camera to look at a point (instant with reduced motion). */
function flyTo(target,dist){
 const from={...cam},to={...cam,tx:target[0],ty:target[1],tz:target[2],dist:dist??cam.dist};
 if(!motionAllowed(settings)){cam=to;requestRender();saveCamera();return;}
 const t0=performance.now();
 const step=t=>{const k=Math.min(1,(t-t0)/450),e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;
  for(const key of Object.keys(to))cam[key]=from[key]+(to[key]-from[key])*e;requestRender();if(k<1)requestAnimationFrame(step);else saveCamera();};
 requestAnimationFrame(step);
}
function overview(){flyTo([0,0,0],DEFAULT_CAM.dist);setTimeout(()=>{if(motionAllowed(settings))return;cam.yaw=DEFAULT_CAM.yaw;cam.pitch=DEFAULT_CAM.pitch;},0);}
function pushAlongView(o,amount){const v=unrotate(0,0,amount);o.pos=[o.pos[0]+v[0],o.pos[1]+v[1],o.pos[2]+v[2]];requestRender();savePos(o);}

// ----- rename and remove (files on the desktop) -----
let renaming=false;
on('desktop-changed',()=>{if(!renaming)refreshSpace();});
function rename(o){
 if(o.source!=='desktop')return toast('Alleen bestanden en mappen op het bureaublad kun je hier een andere naam geven.');
 const el=layer.querySelector(`[data-key="${CSS.escape(o.key)}"]`);if(!el)return;
 const input=h('input',{type:'text',class:'sp-rename','aria-label':'Nieuwe naam voor '+o.name,value:o.name});
 el.querySelector('.sp-label').replaceWith(input);input.focus();renaming=true;
 const dot=o.kind==='file'?o.name.lastIndexOf('.'):-1;input.setSelectionRange(0,dot>0?dot:o.name.length);
 let done=false;
 const finish=async save=>{
  if(done)return;done=true;renaming=false;
  const name=input.value.trim();
  if(save&&name&&name!==o.name){
   try{const res=await call('desktop.rename',{path:o.target,name});selected=res.key;space().pos={...space().pos,[res.key]:o.pos};delete space().pos[o.key];saveLayout();}
   catch(err){toast(err.message);}
  }
  refreshSpace();
 };
 input.addEventListener('keydown',ev=>{ev.stopPropagation();if(ev.key==='Enter'){ev.preventDefault();finish(true);}if(ev.key==='Escape'){ev.preventDefault();finish(false);}});
 input.addEventListener('blur',()=>finish(true));
 input.addEventListener('pointerdown',ev=>ev.stopPropagation());
}
async function removeObj(o){
 if(o.source==='desktop'){await call('desktop.trash',{path:o.target});toast(o.name+' staat in de prullenbak.');return;}
 if(o.source==='shortcut'){layout.items=layout.items.filter(i=>i.id!==o.key);await saveLayout();refreshSpace();return;}
 hideObj(o);
}
function hideObj(o){space().hidden=[...(space().hidden||[]),o.key];saveLayout();objects=objects.filter(x=>x!==o);o.el?.remove();toast(o.name+' is verborgen. Rechtsklik op de lege ruimte om het terug te zetten.');}

// ----- context menus -----
let menu=null;
function closeMenu(){menu?.remove();menu=null;}
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
let startOpen=false;
on('start-state',open=>{startOpen=!!open;});
addEventListener('pointerdown',()=>{if(startOpen)call('surface.hide',{name:'start'}).catch(()=>{});},true);

// Programs that already have a fixed taskbar button use that button instead of a second one.
const DOCK_BUILTIN_APPS={'thunar.desktop':'files','xfce4-terminal.desktop':'terminal','org.gnome.Software.desktop':'store'};
const dockKey=id=>DOCK_BUILTIN_APPS[id]||'app:'+id;
const inDock=id=>layout.dock.includes(dockKey(id));
function toggleDock(id){const key=dockKey(id);layout.dock=inDock(id)?layout.dock.filter(d=>d!==key):[...layout.dock,key];saveLayout();}
function objectMenu(o){
 const app=o.kind==='app'?o.target:null;
 return [
  {label:'Openen',run:()=>openObj(o),keys:'Enter'},
  ...(o.kind==='folder'&&o.source!=='system'?[{label:'Openen in Bestanden',run:()=>call('run',{tool:'files',path:o.target})}]:[]),
  ...(app?[{label:inDock(app)?'Losmaken van de taakbalk':'Aan de taakbalk vastmaken',run:()=>toggleDock(app)}]:[]),
  '-',
  {label:'Inzoomen',run:()=>flyTo(o.pos,Math.max(260,o.size*5))},
  {label:'Dichterbij halen',run:()=>pushAlongView(o,-260)},
  {label:'Verder weg zetten',run:()=>pushAlongView(o,260)},
  '-',
  ...(o.source==='desktop'?[{label:'Naam wijzigen',run:()=>rename(o),keys:'F2'},{label:'Naar de prullenbak',run:()=>removeObj(o),keys:'Delete'}]:[]),
  ...(o.source==='shortcut'?[{label:'Van het bureaublad verwijderen',run:()=>removeObj(o),keys:'Delete'}]:[]),
  ...(o.kind==='app'||o.key==='sys:trash'||o.key==='sys:home'?[{label:'Verbergen',run:()=>hideObj(o),keys:'Delete'}]:[]),
 ];
}
function spaceMenu(x,y){
 const at=worldAt(x,y),hidden=layout.space?.hidden||[];
 return [
  {label:'Nieuwe map',run:async()=>{const res=await call('desktop.mkdir');space().pos={...space().pos,[res.key]:at};await saveLayout();await refreshSpace();const o=objects.find(x=>x.key===res.key);if(o){select(o.key);rename(o);}}},
  {label:'Snelkoppeling naar een map…',run:()=>addPath('folder',at)},
  {label:'Snelkoppeling naar een bestand…',run:()=>addPath('file',at)},
  '-',
  {label:'Overzicht (alles in beeld)',run:overview,keys:'Home'},
  {label:'Alles opnieuw ordenen',run:async()=>{space().pos={};await saveLayout();refreshSpace();}},
  ...(hidden.length?[{label:`Verborgen planeten weer tonen (${hidden.length})`,run:async()=>{space().hidden=[];await saveLayout();refreshSpace();}}]:[]),
  '-',
  {label:'Bureaubladmap openen',run:()=>call('open.path',{path:deskDir})},
  {label:'Persoonlijke instellingen',run:()=>run('control',{page:'appearance'})},
 ];
}
const newId=()=>'i'+Date.now().toString(36)+Math.random().toString(36).slice(2,6);
async function addItem(item,at){
 const id=newId();layout.items.push({id,...item});if(at)space().pos={...space().pos,[id]:at};
 await saveLayout();await refreshSpace();toast(item.name+' staat nu in de ruimte.');
}
async function addPath(kind,at){const picked=await call('pick.path',{kind});if(picked)addItem({kind,target:picked.path,name:picked.name},at);}

async function land(p,{chooseBrowser=false}={}){
 if(p.id==='chat'&&!chooseBrowser){try{const b=await call('browser.list');if(b.default){await launch(b.default);return;}}catch(e){toast('Browserkeuze ophalen mislukt: '+e.message);}}
 if(current)return;current=p;lastFocus=document.activeElement;layer.inert=true;
 ++travelToken;openRoom(p);
}
function leave(){
 if(!current)return;travelToken++;current=null;room.hidden=true;room.replaceChildren();layer.inert=false;
 (lastFocus&&lastFocus.isConnected?lastFocus:layer.firstChild)?.focus({preventScroll:true});
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



// Keyboard: Tab/arrows between planets is not useful in 3D, so: arrows turn the view, +/- zoom, Home = overview,
// Enter opens the focused planet, F2 renames, Delete removes/hides, Menu key / Shift+F10 opens the menu.
addEventListener('keydown',e=>{
 if(menu){
  if(e.key==='Escape'){e.preventDefault();closeMenu();return;}
  if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();const bs=[...menu.querySelectorAll('button')],i=bs.indexOf(document.activeElement);bs[(i+(e.key==='ArrowDown'?1:-1)+bs.length)%bs.length]?.focus();return;}
  if(e.key==='Tab'){e.preventDefault();return;}
  return;
 }
 if(current){keepTab(e,room);if(e.key==='Escape'){e.preventDefault();leave();}return;}
 if(e.target.matches?.('input'))return;
 const el=document.activeElement?.closest?.('.sp-obj'),o=el?._obj;
 if(e.key==='ContextMenu'||(e.shiftKey&&e.key==='F10')){
  e.preventDefault();
  if(o){const r=el.getBoundingClientRect();openMenu(r.left+r.width/2,r.top+r.height/2,objectMenu(o));}
  else{const t=document.activeElement?.closest?.('.tile');if(t?._menu){const r=t.getBoundingClientRect();openMenu(r.left+r.width/2,r.top+r.height/2,t._menu());}else openMenu(innerWidth/2,innerHeight/2,spaceMenu(innerWidth/2,innerHeight/2));}
  return;
 }
 if(e.ctrlKey||e.altKey||e.metaKey)return;
 if(o&&e.key==='Enter'){e.preventDefault();openObj(o);return;}
 if(o&&e.key==='F2'){e.preventDefault();rename(o);return;}
 if(o&&e.key==='Delete'){e.preventDefault();removeObj(o).catch(err=>toast(err.message));return;}
 if(e.key==='Home'){e.preventDefault();overview();return;}
 if(e.key==='+'||e.key==='='||e.key==='-'){e.preventDefault();cam.dist=clamp(cam.dist*(e.key==='-'?1.2:1/1.2),180,12000);requestRender();saveCamera();return;}
 const d={ArrowLeft:[-.12,0],ArrowRight:[.12,0],ArrowUp:[0,-.08],ArrowDown:[0,.08]}[e.key];
 if(d){e.preventDefault();cam.yaw+=d[0];cam.pitch=clamp(cam.pitch+d[1],-1.45,1.45);requestRender();saveCamera();}
});
// Commands from the shell: open a planet room (search results, start menu), settings changed, back to the desktop.
on('open-planet',({id})=>{const p=config?.world.planets.find(x=>x.id===id);if(!p)return;if(current)leave();land(p);});
on('show-space',()=>leave());
on('apps-changed',()=>{appsCache=null;refreshSpace();});
on('config',c=>{if(current)leave();config=c;settings=c.settings;user=c.user||user;if(c.layout)layout=c.layout;applySettings({...settings,colors:c.world.colors});build();});
start();
