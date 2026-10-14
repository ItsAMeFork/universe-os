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
 const learn=h('input',{type:'checkbox'});
 learn.checked=status.leren!==false;
 learn.setAttribute('aria-label','Leren van taken');
 const saveTokens=h('input',{type:'checkbox'});
 saveTokens.setAttribute('aria-label','Tokens besparen');
 const route=h('input',{type:'checkbox'});
 route.setAttribute('aria-label','Verkeer via OmniRoute');
 const squeeze=h('input',{type:'checkbox'});
 squeeze.setAttribute('aria-label','Comprimeren via OmniRoute');
 const upstreams=h('div');
 const upstreamName=h('input',{type:'text',autocomplete:'off'});
 upstreamName.setAttribute('aria-label','Naam van de aanbieder');
 upstreamName.placeholder='Naam, geen adres';
 function paintCompress(next){
  const modus=next.compressie||'geen';
  const providers=next.omniroute_providers||[];
  saveTokens.checked=modus==='headroom';
  squeeze.checked=modus==='omniroute';
  route.checked=!!next.omniroute_router;
  const locked=!providers.length;
  route.disabled=locked;
  squeeze.disabled=locked;
  upstreams.replaceChildren();
  if(!providers.length) upstreams.append(note('Nog geen aanbieder. De router en de compressie blijven uit.'));
  for(const item of providers){
   const drop=h('button',{type:'button'},'Weg');
   drop.addEventListener('click',async()=>{
    try{paintCompress(await call('ai.omniroute.remove',{naam:item}));}
    catch(e){upstreams.append(note(e.message||'Mislukt.'));}
   });
   upstreams.append(h('p',{},item+' ',drop));
  }
 }
 saveTokens.addEventListener('change',async()=>{
  try{paintCompress(await call('ai.compressie',{modus:saveTokens.checked?'headroom':'geen'}));}
  catch(e){saveTokens.checked=!saveTokens.checked;}
 });
 route.addEventListener('change',async()=>{
  try{paintCompress(await call('ai.omniroute.router',{aan:route.checked}));}
  catch(e){route.checked=!route.checked;}
 });
 squeeze.addEventListener('change',async()=>{
  try{paintCompress(await call('ai.compressie',{modus:squeeze.checked?'omniroute':'geen'}));}
  catch(e){squeeze.checked=!squeeze.checked;}
 });
 paintCompress(status);
 const trend=h('div');
 for(const row of (status.trend||[]).slice(0,6)){
  const tokens=Number(row.tokens)||0;
  trend.append(note((row.schatting?'ongeveer ':'')+tokens+' tokens · '+(row.gereedschap||0)+' stappen'+(row.taak?' · '+row.taak:'')));
 }
 if(!(status.trend||[]).length) trend.append(note('Nog geen afgeronde taak. Het gebruik verschijnt hier na een sessie.'));
 const plugins=h('div');
 function drawPlugins(list){
  plugins.replaceChildren();
  for(const item of list||[]){
   const box=h('input',{type:'checkbox'});
   box.checked=!!item.aan;
   box.setAttribute('aria-label',item.naam);
   box.addEventListener('change',async()=>{
    try{const next=await call('ai.plugins.set',{id:item.id,aan:box.checked});drawPlugins(next);}
    catch(e){box.checked=!box.checked;}
   });
   const row=h('div',{},h('label',{class:'check'},box,item.naam+' · '+item.licentie+' · '+(item.status||'nog')),note(item.review||''));
   if(item.installeren){
    row.append(button('Installeren',async()=>{
     await call('ai.plugins.terminal',{id:item.id});
     return 'Er opent een terminal. Universe OS installeert dit niet stilletjes.';
    }));
   }
   plugins.append(row);
  }
 }
 drawPlugins(status.plugins||[]);
 root.append(
  note('Kies wie antwoordt. Het personage, de herinneringen en de vragen op het scherm blijven hetzelfde. Welke AI je ook kiest: een e-mail, een afspraak en het scherm gaan alleen door als jij op Toestaan drukt.'),
  card('Gebruik',
   h('label',{class:'check'},learn,'Leren van taken (korte les, alleen als die minder kost dan de taak)'),
   button('Leervoorkeur bewaren',async()=>{
    await call('ai.leren',{aan:learn.checked});
    return learn.checked?'Leren staat aan.':'Leren staat uit. Cijfers blijven wel bewaard.';
   }),
   h('label',{class:'check'},saveTokens,'Tokens besparen (Headroom, alleen Claude, uit tot je dit aanzet)'),
   note('Headroom start via universe-ai-headroom, met het baken uit. Niet tegelijk met de compressie van OmniRoute.'),
   trend),
  card('OmniRoute',
   note(status.omniroute_waarschuwing||'Gratis aanbieders kunnen je vragen lezen. Zet OmniRoute alleen aan als je dat wilt.'),
   note('Lokale router op http://127.0.0.1:20128. Blijft uit tot je zelf een aanbieder toevoegt. Gemini en Ollama gaan hier niet heen.'),
   field('Aanbieder',upstreamName),
   button('Aanbieder toevoegen',async()=>{
    const fresh=await call('ai.omniroute.add',{naam:upstreamName.value.trim()});
    upstreamName.value='';
    paintCompress(fresh);
    return 'Aanbieder toegevoegd. Gratis aanbieders kunnen je vragen lezen.';
   }),
   upstreams,
   h('label',{class:'check'},route,'Verkeer via OmniRoute sturen'),
   h('label',{class:'check'},squeeze,'Comprimeren via OmniRoute (niet tegelijk met Headroom)')),
  card('Plugins',
   note('Vaste, bekeken set. Hooks en regels van derden gaan niet aan. Zonder netwerk probeert Universe OS het later opnieuw. Installeren opent een terminal; dat gebeurt niet vanzelf.'),
   plugins,
   button('Plugins ophalen',async()=>{
    const outcome=await call('ai.plugins.install');
    const fresh=await call('ai.status');
    drawPlugins(fresh.plugins||[]);
    return outcome.tekst||'Klaar.';
   })),
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
