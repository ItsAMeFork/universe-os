import {updatesView} from './updates-ui.js';
import {call,on,applySettings,motionAllowed,toast,h,icon} from './api.js';
import {globe,earth,starfield,pixelSize} from './globe.js';
import {debugFPS,afterPaint} from './performance.js';
import {SETTINGS} from './settings-index.js';
import {keepTab} from './focus.js';
// The space world. Every planet is a real button (mouse, Tab, arrows, Enter, digits). Landing on a planet opens its
// room; the travel animation is optional (setting "travel") and is skipped with digits, reduced motion or "off".

const KIND={local:['local','Werkt lokaal'],online:['online','Internet nodig'],mixed:['mixed','Lokaal + online']};
let config=null,settings={},user={},planets=[],current=null,lastFocus=null,appsCache=null;
let initialFocus=true;
let travelToken=0;
let backgroundBusy=false;
const setBackgroundBusy=value=>{backgroundBusy=!!value;document.documentElement.classList.toggle('background-busy',backgroundBusy);orbitStart();};
on('background-busy',setBackgroundBusy);
const root=h('main',{class:'universe','aria-label':'Ruimtewereld van Universe OS'});
const scene=h('div',{class:'scene'});
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
 settings=config.settings;user=config.user||{};applySettings({...settings,colors:config.world.colors});
 await afterPaint();build();debugFPS();await afterPaint();
 call('background.busy').then(setBackgroundBusy).catch(()=>{});
 call('world.ready',{milliseconds:performance.now()}).catch(()=>{});
 window.__universePageReady?.();
}
function build(){
 root.replaceChildren(Object.assign(starfield(),{className:'space-stars'}),scene,room);
 scene.replaceChildren();
 const home=config.world.planets.find(p=>p.id==='home');
 if(home){const paths=h('div',{class:'space-paths'},h('i'),h('i'),h('i'));paths.style.left=home.x+'%';paths.style.top=home.y+'%';scene.append(paths);}
 planets=config.world.planets.map((p,index)=>{
  const [kind,kindText]=KIND[p.kind]||KIND.local;
  const button=h('button',{class:`planet ${p.id==='home'?'home':''} ${p.rock&&p.style!=='earth'?'rock':''}`,type:'button','data-id':p.id,
   'aria-label':`${p.name}: ${p.description}. ${kindText}. Sneltoets ${index+1}.`});
  button.style.cssText=`left:${p.x}%;top:${p.y}%;--size:${p.size||.6};--hue:${p.hue};--delay:${-index*1.7}s`;
  const diameter=Math.max(96,Math.min(innerWidth/100,innerHeight*.016)*26*(p.size||.6));
  const float=h('div',{class:'float'},planetGlobe(p,diameter),p.rings?h('span',{class:'rings'}):null);
  const label=h('div',{class:'label'},h('span',{class:'name'},p.name,h('span',{class:'key'},String(index+1))),h('span',{class:`badge ${kind}`},kindText));
  button.append(h('span',{class:'halo','aria-hidden':'true'}),float,label);
  button.addEventListener('click',()=>land(p,{travel:true}));
  scene.append(button);return {p,button};
 });
 buildFolderOrbit(home);
 if(user.live){
  const install=h('button',{class:'installer',type:'button','aria-label':'Universe OS installeren op deze computer'},icon('rocket'),'Universe OS installeren');
  install.addEventListener('click',()=>call('run',{tool:'installer'}).catch(e=>toast(e.message)));
  scene.append(install);
 }
 root.append(h('div',{class:'hint'},'Klik op een planeet of druk ',h('kbd',{},'1'),'–',h('kbd',{},String(planets.length)),' · ',h('kbd',{},'Windows'),' zoeken en open programma\'s · ',h('kbd',{},'Windows'),'+',h('kbd',{},'D'),' ruimtewereld · ',h('kbd',{},'Windows'),'+',h('kbd',{},'A'),' bedieningspaneel'));
 parallax();
 if(initialFocus){initialFocus=false;planets[0]?.button.focus({preventScroll:true});}
}

// Gentle parallax with the mouse (like the app's --parallax-x/y), only with full animations.
let parallaxFrame=0,mouse=null;
function parallax(){
 if(parallaxFrame)cancelAnimationFrame(parallaxFrame);parallaxFrame=0;
 root.style.setProperty('--px','0px');root.style.setProperty('--py','0px');
 root.onmousemove=e=>{
  if(backgroundBusy||!motionAllowed(settings))return;mouse=[e.clientX,e.clientY];
  if(parallaxFrame)return;
  parallaxFrame=requestAnimationFrame(()=>{parallaxFrame=0;if(backgroundBusy||!motionAllowed(settings))return;
   root.style.setProperty('--px',((mouse[0]/innerWidth-.5)*-14).toFixed(1)+'px');
   root.style.setProperty('--py',((mouse[1]/innerHeight-.5)*-10).toFixed(1)+'px');
  });
 };
}

const planetGlobe=(p,diameter)=>p.style==='earth'?earth(pixelSize(diameter)):globe(p.hue,!!p.rock,pixelSize(diameter));

// Folder orbit (concept 10 Oct): the personal folders circle the home world on a tilted orange orbit and pass in
// front of and behind the planet. Every folder is a real button. It only moves with full animations, no visible
// program windows and no open room; ~30 frames per second is plenty for this slow orbit.
const ORBIT_SECONDS=120;
let orbit=null,orbitToken=0,orbitAngle=0,orbitFrame=0,orbitLast=0,folderIds=0;
function folderIcon(){
 const id='folder-grad-'+(++folderIds);
 return h('span',{class:'folder-icon','aria-hidden':'true',html:`<svg viewBox="0 0 64 52"><defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffc07a"/><stop offset="1" stop-color="#f07a2a"/></linearGradient></defs><path d="M4 8a4 4 0 0 1 4-4h16l6 6h26a4 4 0 0 1 4 4v4H4z" fill="#c95d1c"/><path d="M4 16h56v28a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4z" fill="url(#${id})"/><path d="M4 16h56v3H4z" fill="#ffffff40"/></svg>`});
}
async function buildFolderOrbit(home){
 orbit=null;
 if(!home||home.style!=='earth')return;
 const token=++orbitToken;
 let places=[];try{places=(await call('files.places')).filter(pl=>pl.exists&&pl.id!=='trash'&&pl.id!=='home');}catch{return;}
 if(token!==orbitToken||!places.length)return;
 const back=h('div',{class:'folder-orbit back','aria-hidden':'true'}),front=h('div',{class:'folder-orbit front','aria-hidden':'true'});
 const items=places.map(pl=>{
  const b=h('button',{class:'orbit-folder',type:'button','aria-label':`Map ${pl.name} openen`},folderIcon(),h('span',{class:'folder-name'},pl.name));
  b.addEventListener('click',()=>call('open.path',{path:pl.path}).catch(e=>toast(e.message)));
  return b;
 });
 for(const el of [back,front,...items]){el.style.left=home.x+'%';el.style.top=home.y+'%';}
 scene.append(back,front,...items);
 orbit={home,items,back,front};
 orbitPlace();orbitStart();
}
function orbitPlace(){
 if(!orbit)return;
 const planet=planets.find(x=>x.p===orbit.home)?.button;if(!planet)return;
 const D=planet.offsetWidth,rx=D*.98,ry=D*.3,tilt=-10*Math.PI/180,ct=Math.cos(tilt),st=Math.sin(tilt);
 for(const ring of [orbit.back,orbit.front]){ring.style.width=2*rx+'px';ring.style.height=2*ry+'px';}
 orbit.items.forEach((b,i)=>{
  const a=orbitAngle+i/orbit.items.length*Math.PI*2,ex=Math.cos(a)*rx,ey=Math.sin(a)*ry,depth=Math.sin(a);
  const x=ex*ct-ey*st,y=ex*st+ey*ct;
  b.style.transform=`translate(calc(-50% + ${x.toFixed(1)}px + var(--px)),calc(-50% + ${y.toFixed(1)}px + var(--py))) scale(${(.86+.14*depth).toFixed(3)})`;
  b.classList.toggle('behind',depth<0);
 });
}
function orbitStart(){if(!orbitFrame&&orbit)orbitFrame=requestAnimationFrame(orbitTick);}
function orbitTick(time){
 orbitFrame=0;
 if(!orbit||!orbit.items[0].isConnected||current||backgroundBusy||document.hidden||!motionAllowed(settings)){orbitLast=0;return;}
 if(!orbitLast||time-orbitLast>=33){
  if(orbitLast)orbitAngle=(orbitAngle+(time-orbitLast)/1000/ORBIT_SECONDS*Math.PI*2)%(Math.PI*2);
  orbitLast=time;orbitPlace();
 }
 orbitFrame=requestAnimationFrame(orbitTick);
}
document.addEventListener('visibilitychange',orbitStart);
addEventListener('resize',orbitPlace);

async function land(p,{travel,chooseBrowser=false}){
 if(p.id==='chat'&&!chooseBrowser){try{const b=await call('browser.list');if(b.default){await launch(b.default);return;}}catch(e){toast('Browserkeuze ophalen mislukt: '+e.message);}}
 if(current)return;current=p;lastFocus=document.activeElement;scene.inert=true;
 const token=++travelToken;
 const planet=planets.find(x=>x.p===p)?.button;
 const animate=travel&&settings.travel!==false&&motionAllowed(settings)&&planet;
 if(animate){
  // Fly towards the planet: the scene zooms in on it and dissolves, then the room opens.
  const r=planet.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2;
  scene.style.transformOrigin=`${cx}px ${cy}px`;scene.style.transform=`translate(${innerWidth/2-cx}px,${innerHeight/2-cy}px) scale(3.2)`;scene.classList.add('travelling');
  await new Promise(r=>setTimeout(r,650));
 }else scene.style.visibility='hidden';
 if(token===travelToken&&current===p)openRoom(p);
}
function leave(){
 if(!current)return;travelToken++;current=null;room.hidden=true;room.replaceChildren();scene.inert=false;
 scene.style.visibility='';scene.classList.remove('travelling');scene.style.transform='';
 (lastFocus&&lastFocus.isConnected?lastFocus:planets[0]?.button)?.focus({preventScroll:true});
 orbitStart();
}

function openRoom(p){
 room.style.setProperty('--hue',p.hue);room.setAttribute('aria-label',p.name);
 const [kind,kindText]=KIND[p.kind]||KIND.local;
 const back=h('button',{class:'room-back',type:'button'},icon('back'),'Terug naar de ruimte');back.addEventListener('click',leave);
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
 for(const a of list)grid.append(tile({name:a.name,sub:a.comment,img:a.icon,iconName:'grid',onClick:()=>launch(a.id)}));
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

// Keyboard: digits land directly (no travel), arrows move between planets, Esc goes back to space.
addEventListener('keydown',e=>{
 if(current)keepTab(e,room);
 if(e.key==='Escape'&&current){e.preventDefault();leave();return;}
 if(current||e.ctrlKey||e.altKey||e.metaKey)return;
 const n=Number(e.key);if(n>=1&&n<=planets.length){e.preventDefault();land(planets[n-1].p,{travel:false});return;}
 const dirs={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]};const d=dirs[e.key];if(!d)return;
 e.preventDefault();
 const from=planets.find(x=>x.button===document.activeElement)||planets[0];if(!from)return;
 const fr=from.button.getBoundingClientRect(),fx=fr.left+fr.width/2,fy=fr.top+fr.height/2;let best=null,score=1e9;
 for(const x of planets){if(x===from)continue;const r=x.button.getBoundingClientRect(),dx=r.left+r.width/2-fx,dy=r.top+r.height/2-fy;const along=dx*d[0]+dy*d[1];if(along<=10)continue;const s=along+Math.abs(dx*d[1]+dy*d[0])*2;if(s<score){score=s;best=x;}}
 (best||from).button.focus();
});
// Commands from the shell: open a planet directly (search results, universe-ctl), settings changed, back to space.
on('open-planet',({id})=>{const p=config?.world.planets.find(x=>x.id===id);if(!p)return;if(current)leave();land(p,{travel:false});});
on('show-space',()=>leave());
on('config',c=>{if(current)leave();config=c;settings=c.settings;user=c.user||user;applySettings({...settings,colors:c.world.colors});build();});
start();
