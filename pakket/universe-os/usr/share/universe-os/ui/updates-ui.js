import {call,h} from './api.js';
const ACTIVE=new Set(['checking','downloading','installing','waiting']);
export function updateText(s){
 if(s.state==='checking')return 'Updates controleren…';
 if(s.state==='downloading')return 'Updates downloaden…';
 if(s.state==='installing')return 'Updates installeren… Je kunt verder werken.';
 if(s.state==='waiting')return s.message||'Installatie wacht op internet of een andere pakketbewerking.';
 if(s.state==='current')return s.message||'Geen updates beschikbaar volgens de laatste geslaagde controle.';
 if(s.state==='available')return `${s.count} updates beschikbaar.`;
 if(s.state==='stale')return 'De pakketlijst is oud of de datum van de laatste controle is onbekend. Controleer nu.';
 return s.error||'Controle mislukt. Controleer je internetverbinding en de datum en tijd.';
}
export function updatesView(){
 const root=h('div'),message=h('p',{role:'status'},'Updatestatus laden…'),date=h('p',{class:'muted'}),reboot=h('p');
 const button=h('button',{type:'button'},'Nu controleren');
 const install=h('button',{type:'button',hidden:true},'Updates installeren');
 const policy=h('p',{class:'muted'},'Updates zijn verplicht en worden door het systeem automatisch geïnstalleerd. Een benodigde herstart wordt gemeld.');
 let busy=false,last=null,actionError='';
 function show(s){last=s;message.textContent=actionError||updateText(s);message.className=actionError||s.state==='error'?'message error':'message';
  date.textContent=s.checkedAt?`Laatste geslaagde verversing: ${new Date(s.checkedAt*1000).toLocaleString('nl-NL')}`:'Geen geslaagde verversing geregistreerd.';
  reboot.textContent=s.rebootRequired?'Herstart nodig om updates af te ronden.':'';
  install.hidden=!(s.state==='available'||ACTIVE.has(s.state)||s.count>0);
  install.textContent=s.state==='installing'?'Updates worden geïnstalleerd…':'Updates installeren';
  install.disabled=busy||ACTIVE.has(s.state);button.disabled=busy||ACTIVE.has(s.state);
 }
 async function load(command='updates.status'){if(busy)return;busy=true;button.disabled=install.disabled=true;
  if(command!=='updates.status'){actionError='';message.textContent=command==='updates.install'?'Installatie starten…':'Pakketlijst verversen en updates controleren…';}
  try{const s=await call(command);if(!s||typeof s.state!=='string')throw Error('Het systeem gaf geen bruikbare updatestatus terug.');show(s);}
  catch(e){if(command==='updates.install'){actionError='Installatie starten mislukt: '+e.message;show(last||{state:'error',error:e.message});}else show({state:'error',error:e.message});}
  finally{busy=false;if(last)show(last);else button.disabled=false;}
 }
 button.addEventListener('click',()=>load('updates.refresh'));install.addEventListener('click',()=>load('updates.install'));
 root.append(policy,message,date,reboot,h('div',{class:'row'},button,install));load();
 const poll=()=>setTimeout(async()=>{if(!root.isConnected)return;await load();poll();},5000);poll();return root;
}
