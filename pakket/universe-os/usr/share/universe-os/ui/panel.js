import {audioView} from './audio-ui.js';
import {updatesView} from './updates-ui.js';
import {keepTab} from './focus.js';
import {latestValue} from './requests.js';
import {call,on,applySettings,toast,h,icon} from './api.js';
// Compact control panel: a small pill at the top (above all windows, top layer). Clicking it (or Windows+A) opens
// the full panel with volume, network, battery, notifications and the power actions. No taskbar, no app list.

let status={},open=false,config=null,toggleToken=0,refreshPromise=null;
const fmtTime=d=>d.toLocaleTimeString('nl-NL',{hour:'2-digit',minute:'2-digit'});
const fmtDate=d=>d.toLocaleDateString('nl-NL',{weekday:'long',day:'numeric',month:'long'});
const pill=h('button',{class:'pill',type:'button','aria-label':'Bedieningspaneel openen','aria-expanded':'false'});
const panel=h('section',{class:'panel glass',hidden:true,role:'dialog','aria-label':'Bedieningspaneel'});
const banner=h('div',{class:'scherm-banner',hidden:true,role:'status'});
document.body.append(pill,panel,banner);
let scherm={},auto={aan:false,duur:'30m',tekst:'Uit'},modes={zen:false,god:false};
pill.addEventListener('click',()=>toggle(true));

function netIcon(n){return !n||n.state!=='connected'?'offline':n.type==='wifi'?'wifi':'wired';}
function netText(n){if(!n)return 'Netwerkstatus onbekend';const name=n.state==='connected'?`${n.type==='wifi'?'Wifi':n.type==='ethernet'?'Kabel':'Netwerk'}: ${n.name||'verbonden'}. `:'';return name+(n.message||'Netwerkstatus onbekend');}
let pillKey='';
function renderPill(){
 const now=new Date(),v=status.volume,b=status.battery,count=status.notifications?.length||0;
 // Status arrives every 10 s and the clock ticks every 15 s: only rebuild when something visible changed.
 const key=[fmtTime(now),JSON.stringify(status.network),v?.level,v?.muted,b?.present,b?.percent,b?.charging,count,scherm.toegestaan?'1':'0',scherm.bezig?'1':'0',auto.aan?'1':'0',auto.tekst||'',modes.zen?'1':'0',modes.god?'1':'0'].join('|');
 if(key===pillKey)return;
 pillKey=key;
 pill.replaceChildren(...[
  h('span',{class:'item'},fmtTime(now)),
  h('span',{class:'item',title:netText(status.network)},icon(netIcon(status.network))),
  v?h('span',{class:'item',title:`Volume ${v.level}%`},icon(v.muted?'mute':'volume')):null,
  b?.present?h('span',{class:'item',title:'Batterij'},icon('battery'),`${b.percent}%${b.charging?' ⚡':''}`):null,
  h('span',{class:'item',title:'Meldingen'},icon('bell'),count?h('span',{class:'count'},String(count)):null),
  scherm.toegestaan?h('span',{class:'item',title:'AI mag het scherm bedienen. Super+Escape stopt.'},'AI'):null,
  auto.aan?h('span',{class:'item',title:auto.tekst||'Automatisch toestaan staat aan'},'Auto'):null,
  modes.god?h('span',{class:'item',title:'God-modus. Versturen, betalen, wissen en wachtwoorden blijven een vraag. Super+Escape zet het uit.'},'God'):null].filter(child=>child!=null));
 pill.classList.toggle('scherm-aan',!!(scherm.toegestaan||scherm.bezig));
 pill.setAttribute('aria-label',`Bedieningspaneel openen. ${fmtTime(now)}. ${netText(status.network)}.${count?` ${count} meldingen.`:''}`);
 window.__universePageReady?.();
}
function renderPanel(){
 const focused=panel.contains(document.activeElement)?document.activeElement:null;
 const focusKey=focused&&(focused.getAttribute('aria-label')||focused.textContent);
 const scroll=panel.scrollTop;
 const expanded=[...panel.querySelectorAll('details[open]')].map(d=>d.querySelector('summary').textContent);
 const deferred=(title,create)=>{const details=h('details',{},h('summary',{},title));let loaded=false;details.addEventListener('toggle',()=>{if(details.open&&!loaded){loaded=true;details.append(create());}});return details;};
 const now=new Date(),v=status.volume||{level:0,muted:false},b=status.battery,n=status.network;
 const close=h('button',{type:'button','aria-label':'Paneel sluiten'},icon('close'));close.addEventListener('click',()=>toggle(false));
 const slider=h('input',{type:'range',min:'0',max:'100',value:String(v.level),'aria-label':'Volume'});
 const setVolume=latestValue(level=>call('volume.set',{level}),e=>toast(e.message));
 const volumeLabel=h('span',{},icon(v.muted?'mute':'volume'),`Geluid ${v.level}%`);
 slider.addEventListener('input',()=>{volumeLabel.replaceChildren(icon(v.muted?'mute':'volume'),`Geluid ${slider.value}%`);setVolume(Number(slider.value));});
 slider.addEventListener('change',()=>setTimeout(()=>call('volume.ping').catch(()=>{}),120)); // the tune at the new volume, on release
 const mute=h('button',{type:'button','aria-pressed':String(!!v.muted)},icon(v.muted?'mute':'volume'),v.muted?'Gedempt':'Dempen');
 mute.addEventListener('click',()=>call('volume.mute').then(refresh).catch(e=>toast(e.message)));
 mute.disabled=!status.volume;
 const act=(label,iconName,fn,cls='')=>{const b=h('button',{type:'button',class:cls},icon(iconName),label);b.addEventListener('click',fn);return b;};
 const tool=(label,iconName,tool,args={})=>act(label,iconName,()=>{call('run',{tool,...args}).catch(e=>toast(e.message));toggle(false);});
 const notes=h('div',{class:'notes'});
 const list=status.notifications||[];
 if(!list.length)notes.append(h('div',{class:'small'},'Geen meldingen.'));
 for(const m of list.slice(0,6))notes.append(h('div',{class:'note'},h('b',{},m.summary||m.app||'Melding'),m.body||''));
 const confirmBox=h('div',{class:'confirm'});
 const ask=(label,action)=>{confirmBox.replaceChildren(h('div',{},`${label}? Niet-opgeslagen werk in open programma's kan verloren gaan.`),h('div',{class:'power'},act('Ja, '+label.toLowerCase(),'power',()=>call('power',{action}).catch(e=>toast(e.message)),'danger'),act('Annuleren','close',()=>confirmBox.replaceChildren())));confirmBox.querySelector('button').focus();};
 const awayBox=h('input',{type:'checkbox',role:'switch'});
 awayBox.checked=!!auto.aan;
 awayBox.setAttribute('aria-label','Automatisch toestaan');
 const awayState=h('span',{class:'switch-state '+(auto.aan?'aan':'uit')},auto.aan?'Aan':'Uit');
 const awayDuur=h('select',{'aria-label':'Duur automatisch toestaan'});
 for(const [id,label] of [['30m','30 minuten'],['1u','1 uur'],['2u','2 uur'],['tot-uit','Tot je het uitzet']]) awayDuur.append(h('option',{value:id},label));
 awayDuur.value=auto.duur||'30m';
 awayBox.addEventListener('change',()=>call('auto.set',{aan:awayBox.checked,duur:awayDuur.value}).then(applyAuto).catch(e=>{awayBox.checked=!awayBox.checked;toast(e.message);}));
 awayDuur.addEventListener('change',()=>{if(awayBox.checked)call('auto.set',{aan:true,duur:awayDuur.value}).then(applyAuto).catch(e=>toast(e.message));});
 const modeSwitch=(title,key,copy)=>{
  const box=h('input',{type:'checkbox',role:'switch'});
  box.checked=!!modes[key];
  box.setAttribute('aria-label',title);
  const state=h('span',{class:'switch-state '+(modes[key]?'aan':'uit')},modes[key]?'Aan':'Uit');
  box.addEventListener('change',()=>call('config.set',{key,value:box.checked}).catch(e=>{box.checked=!box.checked;toast(e.message);}));
  return h('section',{class:'card token-hero'},
   h('label',{class:'switch-row'},h('span',{class:'switch'},box,h('span',{class:'switch-track','aria-hidden':'true'})),h('span',{class:'switch-copy'},h('span',{class:'switch-title'},title),state)),
   h('p',{class:'small'},copy));
 };
 panel.replaceChildren(...[
  h('div',{class:'top'},h('div',{},h('div',{class:'clock'},fmtTime(now)),h('div',{class:'date'},fmtDate(now))),close),
  h('section',{class:'card token-hero'},
   h('label',{class:'switch-row'},h('span',{class:'switch'},awayBox,h('span',{class:'switch-track','aria-hidden':'true'})),h('span',{class:'switch-copy'},h('span',{class:'switch-title'},'Automatisch toestaan'),awayState)),
   h('p',{class:'small'},'Gewone stappen gaan door, en een kort antwoord naar een bekende ook. Belangrijke mail, betalen, wissen en wachtwoorden blijven wachten.'),
   awayDuur),
  modeSwitch('Zen','zen','Rustig bureaublad: geen taakbalk en geen planeten. Het personage blijft.'),
  modeSwitch('God','god','Gewone stappen gaan zelf door. Versturen, betalen, wissen en wachtwoorden blijven een vraag. Super+Escape zet God uit.'),
  h('h2',{class:'panel-heading'},'Geluid en verbinding'),
  h('div',{class:'card'},h('div',{class:'line'},volumeLabel,mute),status.volume?slider:h('div',{class:'small'},'Geen geluidsapparaat gevonden.'),deferred('Geluidsuitgang kiezen',audioView)),
  h('div',{class:'card'},h('div',{class:'line'},h('span',{},icon(netIcon(n)),netText(n))),h('div',{class:'quick'},tool('Netwerk','wifi','control',{page:'network'}),tool('Geluid','volume','control',{page:'sound'}))),
  b?.present?h('div',{class:'card'},h('div',{class:'line'},h('span',{},icon('battery'),`Batterij ${b.percent}%`),h('span',{class:'small'},b.charging?'Wordt opgeladen':b.state||''))):null,
  h('h2',{class:'panel-heading'},'Updates en meldingen'),
  h('div',{class:'card'},deferred('Updatestatus en controleren',updatesView)),
  h('div',{class:'card'},h('div',{class:'line'},h('span',{},icon('bell'),'Meldingen'),list.length?act('Wissen','close',()=>call('notifications.clear').then(refresh)):null),notes),
  h('h2',{class:'panel-heading'},'Navigatie'),
  h('div',{class:'quick'},act('Ruimtewereld','planet',()=>{call('desktop.show').catch(e=>toast(e.message));toggle(false);}),act('Overzicht','windows',()=>{call('surface.show',{name:'overview'}).catch(e=>toast(e.message));toggle(false);}),tool('Instellingen','gear','control'),tool('Bestanden','folder','files')),
  h('h2',{class:'panel-heading'},'Sessie en energie'),
  h('div',{class:'power'},act('Vergrendelen','lock',()=>{toggle(false);call('power',{action:'lock'});}),act('Afmelden','logout',()=>ask('Afmelden','logout')),act('Opnieuw opstarten','restart',()=>ask('Opnieuw opstarten','reboot')),act('Afsluiten','power',()=>ask('Afsluiten','poweroff')),
   status.canSuspend?act('Slaapstand','sleep',()=>{toggle(false);call('power',{action:'suspend'});}):null),
  confirmBox].filter(child=>child!=null));
 for(const details of panel.querySelectorAll('details'))if(expanded.includes(details.querySelector('summary').textContent))details.open=true;
 if(focusKey){const replacement=[...panel.querySelectorAll('button,input,select,summary')].find(el=>(el.getAttribute('aria-label')||el.textContent)===focusKey);replacement?.focus({preventScroll:true});}
 panel.scrollTop=scroll;
}
async function toggle(value){
 const token=++toggleToken;open=value;pill.setAttribute('aria-expanded',String(open));
 pill.hidden=open;panel.hidden=!open;if(open){renderPanel();panel.querySelector('button,input')?.focus();}
 await call('surface.size',{name:'panel',open}).catch(()=>{});
 if(token!==toggleToken)return;
 if(open)await refresh();else pill.blur();
}
async function refresh(){if(refreshPromise)return refreshPromise;refreshPromise=(async()=>{try{status=await call('status');}catch(e){toast('Status ophalen mislukt: '+e.message);}renderPill();if(open)renderPanel();})();try{await refreshPromise;}finally{refreshPromise=null;}}
addEventListener('keydown',e=>{if(open)keepTab(e,panel);if(e.key==='Escape'&&open){e.preventDefault();toggle(false);}});
on('status',s=>{status=s;renderPill();});
on('panel-toggle',()=>toggle(!open));
on('panel-close',()=>{if(open)toggle(false);});
on('config',c=>{config=c;modes={zen:!!c.settings?.zen,god:!!c.settings?.god};applySettings({...c.settings,colors:c.world.colors});paintBanner();renderPill();if(open)renderPanel();});
function paintBanner(){
 const parts=[];
 if(auto.aan) parts.push(auto.tekst&&auto.tekst!=='Uit'?auto.tekst:'Automatisch toestaan staat aan. Super+Escape zet het direct uit.');
 if(modes.god) parts.push('God-modus: gewone stappen gaan door. Versturen, betalen, wissen en wachtwoorden blijven een vraag. Super+Escape zet God uit.');
 if(scherm.bezig) parts.push('De assistent bedient het scherm. Super+Escape stopt dit.');
 banner.hidden=!parts.length;
 banner.textContent=parts.join(' ');
}
function applyAuto(next){auto=next||{aan:false,tekst:'Uit'};paintBanner();renderPill();if(open)renderPanel();}
function applyScherm(s){scherm=s||{};paintBanner();renderPill();}
on('scherm',applyScherm);
on('auto',applyAuto);
setInterval(()=>{renderPill();},15000);
(async()=>{try{config=await call('config.get');modes={zen:!!config.settings?.zen,god:!!config.settings?.god};applySettings({...config.settings,colors:config.world.colors});paintBanner();}catch{}call('scherm.status').then(applyScherm).catch(()=>{});call('auto.status').then(applyAuto).catch(()=>{});refresh();})();
