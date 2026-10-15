// Preferred browser route on the Internet planet: one button.
// The shell confirms, installs Chrome from Google's apt source when it is missing,
// and opens the official Claude extension. Reading, drafts, sorting and forms go
// through. Sending, paying, deleting, passwords and important mail stay a question.
import {h} from './api.js';

/**
 * @param {HTMLElement} parent
 * @param {Function} call
 */
export function mountClaudeRoute(parent, call){
 const state=h('p',{class:'switch-state uit',role:'status'},'Nog niet gecontroleerd.');
 const message=h('p',{class:'muted',role:'status'});
 const button=h('button',{class:'primary',type:'button'},'Claude in Chrome installeren');
 function paint(info){
  const connected=!!(info&&info.verbonden);
  const hasChrome=!!(info&&info.chrome);
  state.textContent=(info&&info.tekst)||state.textContent;
  state.className='switch-state '+(connected?'aan':'uit');
  button.textContent=connected?'Extensiepagina openen':hasChrome?'Claude in Chrome aanzetten':'Claude in Chrome installeren';
 }
 button.addEventListener('click',async()=>{
  button.disabled=true;
  message.textContent='Bezig…';
  try{
   const next=await call('browser.claude.setup');
   paint(next);
   message.textContent='';
  }catch(e){
   message.textContent=e.message||'Mislukt.';
  }finally{
   button.disabled=false;
  }
 });
 parent.append(h('section',{class:'notice ok claude-route','aria-label':'Claude in Chrome'},
  h('h2',{},'Claude in Chrome'),
  h('p',{},'De voorkeursroute voor de browser. Claude werkt in jouw eigen Chrome, waar je al bent ingelogd. Lezen, concepten, sorteren en formulieren gaan door. Versturen, betalen, wissen, wachtwoorden en belangrijke mail blijven een vraag met Toestaan.'),
  state,button,message));
 call('browser.claude').then(paint).catch(()=>{
  state.textContent='De knop installeert Chrome uit de officiële bron van Google en opent de extensie.';
 });
}
