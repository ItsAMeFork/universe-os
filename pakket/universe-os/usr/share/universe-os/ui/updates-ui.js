import {call,h} from './api.js';
export function updateText(s){
 if(s.state==='current')return 'Geen updates beschikbaar volgens de laatste geslaagde controle.';
 if(s.state==='available')return `${s.count} updates beschikbaar.`;
 if(s.state==='stale')return 'De pakketlijst is oud of de datum van de laatste controle is onbekend. Controleer nu.';
 return s.error||'Controle mislukt. Controleer je internetverbinding en de datum en tijd.';
}
export function updatesView(){
 const root=h('div'),message=h('p',{role:'status'},'Updatestatus laden…'),date=h('p',{class:'muted'}),reboot=h('p');
 const button=h('button',{type:'button'},'Nu controleren');let busy=false;
 function show(s){message.textContent=updateText(s);message.className=s.state==='error'?'message error':'message';
  date.textContent=s.checkedAt?`Laatste geslaagde verversing: ${new Date(s.checkedAt*1000).toLocaleString('nl-NL')}`:'Geen geslaagde verversing geregistreerd.';
  reboot.textContent=s.rebootRequired?'Herstart nodig om updates af te ronden.':'';
 }
 async function load(refresh){if(busy)return;busy=true;button.disabled=true;if(refresh)message.textContent='Pakketlijst verversen en updates controleren…';
  try{show(await call(refresh?'updates.refresh':'updates.status'));}catch(e){show({state:'error',error:e.message});}
  finally{busy=false;button.disabled=false;}
 }
 button.addEventListener('click',()=>load(true));root.append(message,date,reboot,button);load(false);return root;
}
