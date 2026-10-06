import {call,h,icon} from './api.js';
const actions=[['shutdown','Afsluiten','power'],['suspend','Slaapstand','sleep'],['restart','Herstarten','restart']];
const panel=h('aside',{class:'login-power','aria-label':'Computer bedienen'});
const message=h('p',{class:'power-message',role:'status'}),buttons=new Map(),reasons=new Map();
let pending=false;
function confirmation(label){
 return new Promise(resolve=>{
  const dialog=h('dialog',{class:'power-confirm','aria-label':`${label} bevestigen`});
  const cancel=h('button',{type:'button'},'Annuleren'),yes=h('button',{type:'button',class:'primary'},`Ja, ${label.toLowerCase()}`);
  function finish(value){dialog.close();dialog.remove();resolve(value);}
  cancel.addEventListener('click',()=>finish(false));yes.addEventListener('click',()=>finish(true));
  dialog.addEventListener('cancel',e=>{e.preventDefault();finish(false);});
  dialog.append(h('h2',{},`${label}?`),h('p',{},'Andere aangemelde gebruikers kunnen niet-opgeslagen werk verliezen.'),cancel,yes);
  document.body.append(dialog);dialog.showModal();cancel.focus();
 });
}
async function capabilities(){
 try{
  const state=await call('power.get');
  for(const [id] of actions){const allowed=state[id]===true;buttons.get(id).disabled=pending||!allowed;reasons.get(id).textContent=allowed?'': 'Niet beschikbaar volgens het systeem.';}
 }catch(e){for(const [id] of actions){buttons.get(id).disabled=true;reasons.get(id).textContent='Beschikbaarheid kon niet worden gecontroleerd.';}message.textContent=e.message;}
}
for(const [id,label,name] of actions){
 const b=h('button',{type:'button',disabled:true,'aria-describedby':`power-reason-${id}`},icon(name),label);
 const reason=h('small',{id:`power-reason-${id}`},'Beschikbaarheid controleren…');buttons.set(id,b);reasons.set(id,reason);
 b.addEventListener('click',async()=>{
  if(pending||b.disabled)return;pending=true;for(const v of buttons.values())v.disabled=true;
  try{if(id!=='suspend'&&!await confirmation(label))return;message.textContent=`${label} wordt aangevraagd…`;await call(`power.${id}`);message.textContent=id==='suspend'?'Slaapstand aangevraagd.':`${label} aangevraagd.`;}
  catch(e){message.textContent=e.message;}
  finally{pending=false;await capabilities();}
 });
 panel.append(h('div',{class:'power-option'},b,reason));
}
panel.append(message);document.body.append(panel);capabilities();
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!pending)capabilities();});
