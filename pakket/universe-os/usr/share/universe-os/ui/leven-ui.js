// Desk features: screen history, voice, morning briefing, ghost hints, goals, zen/god.
import {h} from './api.js';

const note=t=>h('p',{class:'muted'},t);

function swatch(label, on, change){
 const box=h('input',{type:'checkbox',role:'switch'});
 box.setAttribute('aria-label',label);
 box.checked=!!on;
 const state=h('span',{class:'switch-state '+(on?'aan':'uit')},on?'Aan':'Uit');
 box.addEventListener('change',async()=>{
  try{await change(box.checked,state);}
  catch(e){box.checked=!box.checked;state.textContent=e.message||'Mislukt.';}
 });
 return h('section',{class:'card token-hero'},
  h('label',{class:'switch-row'},
   h('span',{class:'switch'},box,h('span',{class:'switch-track','aria-hidden':'true'})),
   h('span',{class:'switch-copy'},h('span',{class:'switch-title'},label),state)));
}

export function fillMission(el, data){
 if(!el)return;
 const regels=(data&&data.regels)||[];
 const aftellen=data&&data.aftellen;
 if(!data||!data.aan||(!aftellen&&!regels.length)){el.hidden=true;el.replaceChildren();return;}
 el.hidden=false;
 const bits=[h('p',{class:'mission-kicker'},'Mission Control')];
 if(aftellen){
  bits.push(h('strong',{},aftellen.titel||'Agenda'),h('div',{class:'mission-count'},aftellen.tekst||''));
 }
 for(const line of regels.slice(0,4)) bits.push(h('p',{},line));
 el.replaceChildren(...bits);
}

export function fillBlik(el, data){
 if(!el)return;
 const rows=[];
 for(const task of (data&&data.taken)||[]){
  for(const row of task.acties||[]) rows.push(row);
 }
 if(!rows.length){el.hidden=true;el.replaceChildren();return;}
 el.hidden=false;
 el.replaceChildren(h('strong',{},'Wat de AI doet'),
  ...rows.slice(-5).map(row=>h('p',{},(row.hulpmiddel||'stap')+' · '+(row.samenvatting||row.status||''))));
}

/**
 * @param {HTMLElement} parent
 * @param {{call?:Function}} api
 */
export async function mountLeven(parent, api={}){
 const call=api.call||(async()=>({}));
 let data={};
 try{data=await call('leven.status')||{};}catch(e){data={};}
 const scherm=data.scherm||{};
 const stem=data.stem||{};
 const briefing=data.briefing||{};
 const ghost=data.ghost||{};
 const doelen=data.doelen||{};
 const status=h('p',{class:'message',role:'status'});

 async function save(deel, fields){
  data=data||{};
  const next=await call('leven.set',{deel,...fields});
  if(deel==='doelen') data.doelen=next;
  else if(next&&next.aan!==undefined&&deel!=='doelen') data[deel]=next;
  return next;
 }

 const dagen=h('input',{type:'number',value:String(scherm.dagen||7),min:'1',max:'90'});
 dagen.setAttribute('aria-label','Bewaardagen');
 const uitsluiten=h('textarea',{rows:'3'});
 uitsluiten.value=(scherm.uitsluiten||[]).join('\n');
 uitsluiten.setAttribute('aria-label','Extra uitgesloten programma\'s');
 const goal=h('input',{type:'text',autocomplete:'off'});
 goal.setAttribute('aria-label','Nieuw doel');
 const goals=h('div',{class:'taak-steps'});
 function paintGoals(list){
  goals.replaceChildren();
  const rows=list||[];
  if(!rows.length) goals.append(note('Nog geen doel.'));
  for(const item of rows){
   goals.append(h('div',{class:'taak-step'},h('span',{},item.titel||'Doel'),h('span',{class:'badge '+(item.status||'')},item.status||'')));
  }
 }
 paintGoals(doelen.lijst||[]);

 parent.replaceChildren(
  h('section',{class:'card'},
   h('h3',{},'Brein-tijdlijn'),
   note(scherm.uitleg||'Schermafbeeldingen en tekstherkenning blijven op deze computer. Uit tot je het aanzet.'),
   swatch('Schermgeschiedenis',scherm.aan,async(on,state)=>{
    const next=await save('scherm',{aan:on});
    state.textContent=(next&&next.tekst)||(on?'Aan':'Uit');
    state.className='switch-state '+(on?'aan':'uit');
   }),
   swatch('Pauze',scherm.pauze,async(on,state)=>{
    const next=await save('scherm',{pauze:on});
    state.textContent=on?'Pauze':'Loopt';
    state.className='switch-state '+(next&&next.pauze?'aan':'uit');
   }),
   h('label',{},'Bewaren (dagen)',dagen),
   h('label',{},'Extra uitsluiten, één per regel',uitsluiten),
   note('Wachtwoordbeheerders en bankieren blijven altijd uit, ook als deze lijst leeg is.'),
   h('div',{},
    h('button',{type:'button',onclick:async()=>{
     await save('scherm',{dagen:Number(dagen.value)||7,uitsluiten:uitsluiten.value});
     status.textContent='Tijdlijn-instellingen bewaard.';
    }},'Tijdlijn bewaren'),
    h('button',{type:'button',onclick:async()=>{
     await save('scherm',{wissen:true});
     status.textContent='Schermgeschiedenis gewist.';
    }},'Geschiedenis wissen'))),
  h('section',{class:'card'},
   h('h3',{},'Hé Buddy'),
   note(stem.waarom||stem.uitleg||'Stem blijft op deze computer. Uit tot je het aanzet.'),
   swatch('Hé Buddy',stem.aan,async(on,state)=>{
    const next=await save('stem',{aan:on});
    state.textContent=(next&&next.tekst)||(on?'Aan':'Uit');
    state.className='switch-state '+(on?'aan':'uit');
   }),
   h('button',{type:'button',onclick:async()=>{
    await call('stem.terminal');
    status.textContent='Er opent een terminal. Alleen lokale spraak, niets stilletjes.';
   }},'Spraak installeren')),
  h('section',{class:'card'},
   h('h3',{},'Ochtend-briefing'),
   note(briefing.uitleg||'Agenda, belangrijke mail, diensten en taken. Een aftelling bij de buddy.'),
   swatch('Mission Control',briefing.aan!==false,async(on,state)=>{
    const next=await save('briefing',{aan:on});
    state.textContent=(next&&next.tekst)||(on?'Aan':'Uit');
    state.className='switch-state '+(on?'aan':'uit');
   })),
  h('section',{class:'card'},
   h('h3',{},'Ghost-modus'),
   note(ghost.uitleg||'Korte suggesties, met een limiet en stille uren. Uit tot je het aanzet.'),
   swatch('Ghost-modus',ghost.aan,async(on,state)=>{
    const next=await save('ghost',{aan:on});
    state.textContent=(next&&next.tekst)||(on?'Aan':'Uit');
    state.className='switch-state '+(on?'aan':'uit');
   })),
  h('section',{class:'card'},
   h('h3',{},'Doelen'),
   note(doelen.uitleg||'Een doel wordt stappen op het taakbord. Betalen, wissen, wachtwoorden en belangrijke mail blijven een vraag.'),
   h('label',{},'Doel',goal),
   h('button',{type:'button',onclick:async()=>{
    const titel=goal.value.trim();
    if(!titel)throw Error('Schrijf eerst een doel.');
    const next=await save('doelen',{titel});
    goal.value='';
    paintGoals((next&&next.lijst)||[]);
    status.textContent='Doel staat op het taakbord.';
   }},'Doel zetten'),
   swatch('Op de achtergrond',doelen.achtergrond,async(on,state)=>{
    const next=await save('doelen',{achtergrond:on});
    state.textContent=(next&&next.tekst)||(on?'Achtergrond aan':'Alleen op het bord');
    state.className='switch-state '+(on?'aan':'uit');
    paintGoals((next&&next.lijst)||doelen.lijst||[]);
   }),
   goals),
  status);
}
