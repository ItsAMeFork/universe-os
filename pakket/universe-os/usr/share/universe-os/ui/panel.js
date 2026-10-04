import {call,on,applySettings,toast,h,icon} from './api.js';
// Compact control panel: a small pill at the top (above all windows, top layer). Clicking it (or Windows+A) opens
// the full panel with volume, network, battery, notifications and the power actions. No taskbar, no app list.

let status={},open=false,config=null;
const fmtTime=d=>d.toLocaleTimeString('nl-NL',{hour:'2-digit',minute:'2-digit'});
const fmtDate=d=>d.toLocaleDateString('nl-NL',{weekday:'long',day:'numeric',month:'long'});
const pill=h('button',{class:'pill',type:'button','aria-label':'Bedieningspaneel openen','aria-expanded':'false'});
const panel=h('section',{class:'panel glass',hidden:true,role:'dialog','aria-label':'Bedieningspaneel'});
document.body.append(pill,panel);
pill.addEventListener('click',()=>toggle(true));

function netIcon(n){return !n||n.state!=='connected'?'offline':n.type==='wifi'?'wifi':'wired';}
function netText(n){if(!n||n.state==='unavailable')return 'Netwerkbeheer niet beschikbaar';if(n.state!=='connected')return 'Geen verbinding (offline)';return `${n.type==='wifi'?'Wifi':'Kabel'}: ${n.name||'verbonden'}`;}
function renderPill(){
 const now=new Date(),v=status.volume,b=status.battery,count=status.notifications?.length||0;
 pill.replaceChildren(
  h('span',{class:'item'},fmtTime(now)),
  h('span',{class:'item',title:netText(status.network)},icon(netIcon(status.network))),
  v?h('span',{class:'item',title:`Volume ${v.level}%`},icon(v.muted?'mute':'volume')):null,
  b?.present?h('span',{class:'item',title:'Batterij'},icon('battery'),`${b.percent}%${b.charging?' ⚡':''}`):null,
  h('span',{class:'item',title:'Meldingen'},icon('bell'),count?h('span',{class:'count'},String(count)):null));
 pill.setAttribute('aria-label',`Bedieningspaneel openen. ${fmtTime(now)}. ${netText(status.network)}.${count?` ${count} meldingen.`:''}`);
}
function renderPanel(){
 const now=new Date(),v=status.volume||{level:0,muted:false},b=status.battery,n=status.network;
 const close=h('button',{type:'button','aria-label':'Paneel sluiten'},icon('close'));close.addEventListener('click',()=>toggle(false));
 const slider=h('input',{type:'range',min:'0',max:'100',value:String(v.level),'aria-label':'Volume'});
 slider.addEventListener('input',()=>call('volume.set',{level:Number(slider.value)}).catch(e=>toast(e.message)));
 const mute=h('button',{type:'button','aria-pressed':String(!!v.muted)},icon(v.muted?'mute':'volume'),v.muted?'Gedempt':'Dempen');
 mute.addEventListener('click',()=>call('volume.mute').then(refresh).catch(e=>toast(e.message)));
 const act=(label,iconName,fn,cls='')=>{const b=h('button',{type:'button',class:cls},icon(iconName),label);b.addEventListener('click',fn);return b;};
 const tool=(label,iconName,tool,args={})=>act(label,iconName,()=>{call('run',{tool,...args}).catch(e=>toast(e.message));toggle(false);});
 const notes=h('div',{class:'notes'});
 const list=status.notifications||[];
 if(!list.length)notes.append(h('div',{class:'small'},'Geen meldingen.'));
 for(const m of list.slice(0,6))notes.append(h('div',{class:'note'},h('b',{},m.summary||m.app||'Melding'),m.body||''));
 const confirmBox=h('div',{class:'confirm'});
 const ask=(label,action)=>{confirmBox.replaceChildren(h('div',{},`${label}? Niet-opgeslagen werk in open programma's kan verloren gaan.`),h('div',{class:'power'},act('Ja, '+label.toLowerCase(),'power',()=>call('power',{action}).catch(e=>toast(e.message)),'danger'),act('Annuleren','close',()=>confirmBox.replaceChildren())));confirmBox.querySelector('button').focus();};
 panel.replaceChildren(
  h('div',{class:'top'},h('div',{},h('div',{class:'clock'},fmtTime(now)),h('div',{class:'date'},fmtDate(now))),close),
  h('div',{class:'card'},h('div',{class:'line'},h('span',{},icon(v.muted?'mute':'volume'),`Geluid ${v.level}%`),mute),status.volume?slider:h('div',{class:'small'},'Geen geluidsapparaat gevonden.')),
  h('div',{class:'card'},h('div',{class:'line'},h('span',{},icon(netIcon(n)),netText(n))),h('div',{class:'quick'},tool('Netwerk','wifi','control',{page:'network'}),tool('Geluid','volume','control',{page:'sound'}))),
  b?.present?h('div',{class:'card'},h('div',{class:'line'},h('span',{},icon('battery'),`Batterij ${b.percent}%`),h('span',{class:'small'},b.charging?'Wordt opgeladen':b.state||''))):null,
  status.rebootRequired?h('div',{class:'card'},h('div',{},'Herstart nodig om updates af te ronden.')):null,
  h('div',{class:'card'},h('div',{class:'line'},h('span',{},icon('bell'),'Meldingen'),list.length?act('Wissen','close',()=>call('notifications.clear').then(refresh)):null),notes),
  h('div',{class:'quick'},act('Ruimtewereld','planet',()=>{call('desktop.show');toggle(false);}),act('Overzicht','windows',()=>{call('surface.show',{name:'overview'});toggle(false);}),tool('Instellingen','gear','control'),tool('Bestanden','folder','files')),
  h('div',{class:'power'},act('Vergrendelen','lock',()=>{toggle(false);call('power',{action:'lock'});}),act('Afmelden','logout',()=>ask('Afmelden','logout')),act('Opnieuw opstarten','restart',()=>ask('Opnieuw opstarten','reboot')),act('Afsluiten','power',()=>ask('Afsluiten','poweroff')),
   status.canSuspend?act('Slaapstand','sleep',()=>{toggle(false);call('power',{action:'suspend'});}):null),
  confirmBox);
}
async function toggle(value){
 open=value;pill.setAttribute('aria-expanded',String(open));
 await call('surface.size',{name:'panel',open}).catch(()=>{});
 pill.hidden=open;panel.hidden=!open;
 if(open){await refresh();panel.querySelector('button,input')?.focus();}else pill.blur();
}
async function refresh(){try{status=await call('status');}catch(e){status={};}renderPill();if(open)renderPanel();}
addEventListener('keydown',e=>{if(e.key==='Escape'&&open){e.preventDefault();toggle(false);}});
on('status',s=>{status=s;renderPill();});
on('panel-toggle',()=>toggle(!open));
on('panel-close',()=>{if(open)toggle(false);});
on('config',c=>{config=c;applySettings({...c.settings,colors:c.world.colors});});
setInterval(()=>{renderPill();},15000);
(async()=>{try{config=await call('config.get');applySettings({...config.settings,colors:config.world.colors});}catch{}refresh();})();
