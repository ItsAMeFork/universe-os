// AI-activiteit and Taakbord. Both read the local action log. Replay only highlights stored rows.
import {h} from './api.js';

const STATUS={
 goedgekeurd:'Goedgekeurd',geweigerd:'Geweigerd',uitgevoerd:'Uitgevoerd',mislukt:'Mislukt',
 automatisch:'Automatisch',wacht:'Wacht',ongedaan:'Ongedaan',
 todo:'Te doen',bezig:'Bezig',klaar:'Klaar',geblokkeerd:'Geblokkeerd',
};

function badge(status){
 return h('span',{class:'badge '+(status||'')},STATUS[status]||status||'');
}

function motionOn(){
 const root=document.documentElement;
 if(root.classList.contains('reduce-motion')||root.classList.contains('no-motion'))return false;
 if(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches)return false;
 return true;
}

/**
 * @param {HTMLElement} parent
 * @param {{call?:Function,alive?:Function}} api
 */
export function mountActiviteit(parent,api={}){
 const call=api.call||(async()=>({}));
 const still=api.alive||(()=>true);
 let timer=0;
 const status=h('p',{class:'nebula-status',role:'status'});
 const list=h('div');
 parent.replaceChildren(
  h('h2',{},'AI-activiteit'),
  h('p',{class:'muted'},'Per taak: hulpmiddelen, vragen, automatisch toestaan en mislukkingen. Terugkijken voert niets opnieuw uit.'),
  status, list);
 async function load(){
  let data={taken:[],los:[]};
  try{data=await call('brein.activiteit')||data;}
  catch(e){if(still())status.textContent=e.message||'De activiteit kon niet worden gelezen.';}
  if(!still())return;
  list.replaceChildren();
  const tasks=data.taken||[];
  if(!tasks.length) list.append(h('p',{class:'muted'},'Nog geen taak. Na een sessie staat hier wat de AI deed.'));
  for(const task of tasks){
   const actions=h('div',{class:'taak-steps'});
   const rows=task.acties||[];
   if(!rows.length) actions.append(h('p',{class:'muted'},'Geen stappen in het log.'));
   for(const row of rows){
    actions.append(h('article',{},
     h('div',{class:'kind'},(row.tijd||'')+' · '+(row.hulpmiddel||'')),
     h('strong',{},row.samenvatting||row.hulpmiddel||'Stap'),
     badge(row.status)));
   }
   const replay=h('button',{type:'button'},'Terugkijken');
   const exp=h('button',{type:'button'},'Exporteren');
   replay.addEventListener('click',()=>play(actions));
   exp.addEventListener('click',async()=>{
    try{
     const saved=await call('brein.activiteit.export',{id:task.id});
     status.textContent='Opgeslagen: '+((saved&&saved.pad)||'');
    }catch(e){status.textContent=e.message||'Exporteren mislukt.';}
   });
   list.append(h('article',{},
    h('div',{class:'kind'},task.tijd||''),
    h('strong',{},task.titel||'Taak'),
    badge(task.status),
    actions,
    h('div',{},replay,exp)));
  }
  if((data.los||[]).length){
   list.append(h('h3',{},'Zonder taak'));
   for(const row of data.los){
    list.append(h('article',{},
     h('div',{class:'kind'},(row.tijd||'')+' · '+(row.hulpmiddel||'')),
     h('p',{},row.samenvatting||''),
     badge(row.status)));
   }
  }
  parent.dataset.activiteit='ready';
 }
 function play(box){
  const items=[...box.querySelectorAll('article')];
  items.forEach(item=>item.classList.remove('replay-on'));
  clearTimeout(timer);
  if(!items.length)return;
  if(!motionOn()){items.forEach(item=>item.classList.add('replay-on'));return;}
  let index=0;
  const step=()=>{
   if(!still())return;
   items.forEach(item=>item.classList.remove('replay-on'));
   items[index].classList.add('replay-on');
   items[index].scrollIntoView({block:'nearest'});
   index+=1;
   if(index<items.length)timer=setTimeout(step,700);
  };
  step();
 }
 load();
 return ()=>{clearTimeout(timer);};
}

/**
 * @param {HTMLElement} parent
 * @param {{call?:Function,alive?:Function}} api
 */
export function mountTaakbord(parent,api={}){
 const call=api.call||(async()=>({}));
 const still=api.alive||(()=>true);
 const status=h('p',{class:'nebula-status',role:'status'});
 const list=h('div');
 parent.replaceChildren(
  h('h2',{},'Taakbord'),
  h('p',{class:'muted'},'Grote taken, opgeknipt in stappen en subagents. De hooks vullen de status.'),
  status, list);
 async function load(){
  let data={taken:[]};
  try{data=await call('brein.taakbord')||data;}
  catch(e){if(still())status.textContent=e.message||'Het taakbord kon niet worden gelezen.';}
  if(!still())return;
  list.replaceChildren();
  const tasks=data.taken||[];
  if(!tasks.length) list.append(h('p',{class:'muted'},'Nog geen taak. /bouw, /onderzoek, /opruimen en /mail-ochtend zetten hier stappen.'));
  for(const task of tasks){
   const steps=h('div',{class:'taak-steps'});
   for(const step of task.stappen||[]){
    steps.append(h('div',{class:'taak-step'},
     h('span',{},(step.titel||'Stap')+(step.agent?' · '+step.agent:'')),
     badge(step.status)));
   }
   list.append(h('article',{},
    h('div',{class:'kind'},(task.soort||'taak')+' · '+(task.tijd||'')),
    h('strong',{},task.titel||'Taak'),
    badge(task.status),
    steps));
  }
  parent.dataset.taakbord='ready';
 }
 load();
 return ()=>{};
}
