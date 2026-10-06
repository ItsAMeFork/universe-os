import {call,h} from './api.js';
export function channelView(){
 const root=h('div'),status=h('p',{role:'status'},'Updatekanaal laden…');
 const toggle=h('input',{type:'checkbox'}),label=h('label',{class:'check'},toggle,'Testupdates ontvangen');
 toggle.disabled=true;let state=null,busy=false;
 function show(value){state=value;toggle.checked=value.channel==='test';toggle.disabled=busy||!value.active;
  status.textContent=value.active?`Universe OS-kanaal: ${value.channel==='test'?'test':'stable'}.`:'De eigen updatebron is nog niet actief.';
 }
 toggle.addEventListener('change',async()=>{
  if(busy)return;busy=true;const channel=toggle.checked?'test':'stable';toggle.disabled=true;
  if(channel==='test'&&!window.confirm('Testupdates kunnen nog fouten bevatten. Wil je testupdates ontvangen?')){busy=false;show(state);return;}
  status.textContent='Updatekanaal wijzigen…';
  try{const value=await call('updates.channel.set',{channel});show(value);
   if(!value.changed){status.textContent=value.message||'Niet gewijzigd.';return;}
   status.textContent='Kanaal gewijzigd. Pakketlijst verversen…';
   try{const refreshed=await call('updates.refresh');status.textContent=refreshed.state==='error'?`Kanaal gewijzigd; verversen mislukt: ${refreshed.error||'controleer de verbinding'}`:'Kanaal gewijzigd en pakketlijst ververst. Open Nu controleren voor de actuele lijst.';}
   catch(e){status.textContent='Kanaal gewijzigd; verversen mislukt: '+e.message;}
  }catch(e){if(state)show(state);status.textContent=e.message;}
  finally{busy=false;toggle.disabled=!state?.active;}
 });
 root.append(status,label,h('p',{class:'muted'},'Stable bevat vrijgegeven updates. Test ontvangt ook testversies. Terug naar stable zet geïnstalleerde testversies niet automatisch terug.'));
 call('updates.channel.get').then(show).catch(e=>{status.textContent=e.message;});return root;
}
