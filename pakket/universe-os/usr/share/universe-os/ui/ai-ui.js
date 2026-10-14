// AI page: pick Claude Code, ChatGPT (Codex), Gemini or a local Ollama model.
// Keys go to the shell (keyring). This page never receives a key back.
import {call as shellCall, h} from './api.js';

const note=t=>h('p',{class:'muted'},t);
const card=(title,...items)=>h('section',{class:'card'},h('h3',{},title),...items);
const field=(title,input)=>h('label',{},title,input);

function button(title,action){
 const message=h('p',{class:'message',role:'status'});
 const b=h('button',{type:'button'},title);
 b.addEventListener('click',async()=>{
  b.disabled=true;message.className='message';message.textContent='Bezig…';
  try{const outcome=await action();message.textContent=typeof outcome==='string'?outcome:'Gelukt.';}
  catch(e){message.className='message error';message.textContent=e.message||'Mislukt.';}
  finally{b.disabled=false;}
 });
 return h('div',{},b,message);
}

/**
 * @param {HTMLElement} root
 * @param {{call?:Function, buddy?:Node}} api
 */
export async function mountAi(root, api={}){
 const call=api.call||shellCall;
 const status=await call('ai.status');
 let chosen=status.provider||'claude';
 const model=h('input',{type:'text',value:status.model||'',autocomplete:'off'});
 model.setAttribute('aria-label','Model');
 model.placeholder=status.providers.find(p=>p.id===chosen)?.model_leeg||'';
 const url=h('input',{type:'text',value:status.ollama_url||'http://127.0.0.1:11434',autocomplete:'off'});
 url.setAttribute('aria-label','Adres van Ollama');
 const secret=h('input',{type:'password',value:'',autocomplete:'off'});
 secret.setAttribute('aria-label','API-sleutel');
 secret.placeholder='Leeg laten als je in het paneel inlogt';
 const picks=h('div');
 function draw(){
  picks.replaceChildren();
  for(const provider of status.providers){
   const on=provider.id===chosen;
   const box=card(provider.naam,
    note(provider.uitleg),
    note(provider.geinstalleerd?'Geïnstalleerd.':'Nog niet geïnstalleerd. Universe OS levert dit programma niet mee.'),
    provider.sleutel_bewaard?note('Er staat een sleutel in de sleutelbos.'):null,
    h('label',{class:'check'},Object.assign(h('input',{type:'radio',name:'ai-provider'}),{checked:on}),'Deze gebruiken'));
   box.querySelector('input').addEventListener('change',()=>{
    chosen=provider.id;
    model.placeholder=provider.model_leeg||'';
    draw();
   });
   if(on) box.style.borderColor='var(--accent)';
   picks.append(box);
  }
 }
 draw();
 const sandbox=status.sandbox
  ? note('Afscherming aan (bubblewrap). Het programma kan de sleutelbos en de muis niet zelf pakken. Versturen vraagt nog steeds een venster.')
  : h('p',{class:'message error',role:'alert'},'Afscherming uit. Zonder bubblewrap kan een opdracht in de terminal de bevestiging omzeilen. Installeer bubblewrap.');
 root.append(
  note('Kies wie antwoordt. Het personage, de herinneringen en de vragen op het scherm blijven hetzelfde. Welke AI je ook kiest: een e-mail, een afspraak en het scherm gaan alleen door als jij op Toestaan drukt.'),
  picks,
  card('Model',
   note('Laat dit leeg voor de standaard. Bij Claude is dat Haiku, licht genoeg voor een trage computer. Bij Ollama is een klein model (qwen2.5:3b) het enige dat zo’n computer aankan.'),
   field('Model',model),
   field('Ollama-adres (alleen deze computer)',url),
   button('Keuze bewaren',async()=>{
    const saved=await call('ai.set',{provider:chosen,model:model.value.trim(),ollama_url:url.value.trim()});
    return 'Gekozen: '+(saved.naam||chosen)+'. Open daarna het paneel met Windows+C.';
   })),
  card('Sleutel',
   note('Alleen nodig als je niet in het paneel wilt aanmelden. De sleutel gaat naar de sleutelbos en komt niet in een bestand. Dit scherm krijgt hem niet terug.'),
   field('API-sleutel',secret),
   button('Sleutel bewaren',async()=>{
    const value=secret.value;
    secret.value='';
    const saved=await call('ai.key',{provider:chosen,sleutel:value});
    return saved.bewaard?'Sleutel staat in de sleutelbos.':'Sleutel gewist.';
   }),
   button('Sleutel wissen',async()=>{
    secret.value='';
    await call('ai.key',{provider:chosen,sleutel:''});
    return 'Sleutel gewist.';
   })),
  sandbox,
  api.buddy?card('Personage',api.buddy):null,
  button('AI openen',async()=>{await call('ai.open');return 'Paneel geopend. Aanmelden doe je daar, als dat nog niet is gebeurd.';}),
  button('Installatie openen',async()=>{
   await call('ai.install',{provider:chosen});
   return 'Er opent een terminal met het installatieprogramma. Universe OS downloadt de AI niet zelf in de achtergrond.';
  }));
 root.dataset.ai='ready';
}
