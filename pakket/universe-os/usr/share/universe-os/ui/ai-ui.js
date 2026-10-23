// AI page: one tap switches Claude, ChatGPT, Gemini or a local model.
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
 let modes={zen:false,god:false};
 try{const cfg=await call('config.get');if(cfg&&cfg.settings)modes={zen:!!cfg.settings.zen,god:!!cfg.settings.god};}catch(e){}
 function modeSwitch(title,key,copy){
  const box=h('input',{type:'checkbox',role:'switch'});
  box.setAttribute('aria-label',title);
  box.checked=!!modes[key];
  const state=h('span',{class:'switch-state '+(box.checked?'aan':'uit')},box.checked?'Aan':'Uit');
  function paint(next){
   const on=!!(next&&next.settings&&next.settings[key]);
   modes[key]=on;
   box.checked=on;
   state.textContent=on?'Aan':'Uit';
   state.className='switch-state '+(on?'aan':'uit');
  }
  box.addEventListener('change',async()=>{
   try{paint(await call('config.set',{key,value:box.checked}));}
   catch(e){box.checked=!box.checked;state.textContent=e.message||'Mislukt.';}
  });
  return h('section',{class:'card token-hero','data-mode':key},
   h('label',{class:'switch-row'},
    h('span',{class:'switch'},box,h('span',{class:'switch-track','aria-hidden':'true'})),
    h('span',{class:'switch-copy'},h('span',{class:'switch-title'},title),state)),
   note(copy));
 }
 const zenSwitch=modeSwitch('Zen','zen','Rustig bureaublad. De taakbalk en de planeten verdwijnen. Het personage en dit invoerveld blijven. De vraag gaat het paneel in; Enter verstuurt.');
 const godSwitch=modeSwitch('God','god','De assistent doet gewone stappen zelf. Versturen, betalen, wissen en wachtwoorden blijven een vraag. Super+Escape zet God uit.');
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
 const QUICK=[
  ['claude','Claude','Account'],
  ['codex','ChatGPT','Codex'],
  ['gemini','Gemini','Google'],
  ['ollama','Lokaal','Op deze computer'],
 ];
 function labelFor(id){
  const quick=QUICK.find(row=>row[0]===id);
  if(quick) return quick[1];
  const row=status.providers.find(item=>item.id===id);
  return row?row.naam:id;
 }
 function draw(){
  picks.replaceChildren();
  for(const provider of status.providers){
   if(QUICK.some(row=>row[0]===provider.id)) continue;
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
 const saveTokens=h('input',{type:'checkbox',role:'switch'});
 saveTokens.setAttribute('aria-label','Tokens besparen (Headroom)');
 const saveState=h('span',{class:'switch-state uit'},'Uit');
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
  const saving=modus==='headroom';
  saveTokens.checked=saving;
  saveState.textContent=saving?'Aan':'Uit';
  saveState.className='switch-state '+(saving?'aan':'uit');
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
 const lessons=h('div');
 function drawLessons(list){
  lessons.replaceChildren();
  if(!(list||[]).length){
   lessons.append(note('Nog geen les. Na een afgeronde taak verschijnt die hier.'));
   return;
  }
  for(const item of list){
   const box=h('input',{type:'checkbox'});
   box.checked=item.aan!==false;
   box.setAttribute('aria-label','Les meenemen');
   box.addEventListener('change',async()=>{
    try{await call('brein.les',{id:item.id,aan:box.checked});}
    catch(e){box.checked=!box.checked;}
   });
   lessons.append(h('label',{class:'check'},box,item.tekst||''));
  }
 }
 drawLessons(status.lessen||[]);
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
 const autoBox=h('input',{type:'checkbox',role:'switch'});
 autoBox.setAttribute('aria-label','Automatisch toestaan');
 const autoState=h('span',{class:'switch-state uit'},'Uit');
 const autoDuur=h('select',{'aria-label':'Duur automatisch toestaan'});
 for(const [id,label] of [['30m','30 minuten'],['1u','1 uur'],['2u','2 uur'],['tot-uit','Tot je het uitzet']]){
  autoDuur.append(h('option',{value:id},label));
 }
 autoDuur.value='30m';
 const regels=h('textarea',{rows:'4'});
 regels.setAttribute('aria-label','Belangrijke domeinen en woorden');
 function paintAuto(next){
  const on=!!(next&&next.aan);
  autoBox.checked=on;
  autoState.textContent=on?(next.tekst||'Aan'):'Uit';
  autoState.className='switch-state '+(on?'aan':'uit');
  if(next&&next.duur) autoDuur.value=next.duur;
  if(next&&Array.isArray(next.regels)&&document.activeElement!==regels) regels.value=next.regels.join('\n');
 }
 autoBox.addEventListener('change',async()=>{
  try{paintAuto(await call('auto.set',{aan:autoBox.checked,duur:autoDuur.value}));}
  catch(e){autoBox.checked=!autoBox.checked;}
 });
 autoDuur.addEventListener('change',async()=>{
  if(!autoBox.checked) return;
  try{paintAuto(await call('auto.set',{aan:true,duur:autoDuur.value}));}
  catch(e){autoState.textContent=e.message||'Mislukt.';}
 });
 const routeName=h('input',{type:'text',value:status.litellm_url||'http://127.0.0.1:4000',autocomplete:'off'});
 routeName.setAttribute('aria-label','Adres van LiteLLM');
 const routeState=h('p',{class:'switch-state uit'});
 function paintRoute(next){
  const route=next.sessie_route||'claude';
  routeState.textContent=route==='claude'?'Claude':route==='omniroute'?'OmniRoute':'LiteLLM';
  routeState.className='switch-state '+(route==='claude'?'uit':'aan');
  for(const input of root.querySelectorAll('input[name=ai-route]')) input.checked=input.value===route;
 }
 const tokenSwitch=h('section',{class:'card token-hero'},
  h('label',{class:'switch-row'},
   h('span',{class:'switch'},saveTokens,h('span',{class:'switch-track','aria-hidden':'true'})),
   h('span',{class:'switch-copy'},
    h('span',{class:'switch-title'},'Tokens besparen (Headroom)'),
    saveState)),
  note('Minder tokens en goedkoper; de AI kan af en toe een detail missen.'));
 const autoSwitch=h('section',{class:'card token-hero'},
  h('label',{class:'switch-row'},
   h('span',{class:'switch'},autoBox,h('span',{class:'switch-track','aria-hidden':'true'})),
   h('span',{class:'switch-copy'},
    h('span',{class:'switch-title'},'Automatisch toestaan'),
    autoState)),
  note('Voor als je weg bent. Gewone stappen gaan door, en een kort antwoord naar iemand die je al schrijft ook. Belangrijke mail, betalen, wissen en wachtwoorden blijven wachten.'),
  field('Duur',autoDuur),
  field('Belangrijke domeinen en woorden',regels),
  note('Eén per regel. Mail die zo’n woord bevat, of een nieuwe ontvanger, een bijlage of meer dan drie ontvangers, gaat nooit automatisch weg.'),
  button('Regels bewaren',async()=>{
   const saved=await call('auto.regels',{regels:regels.value});
   paintAuto(saved);
   return 'Regels bewaard.';
  }));
 const routes=h('div');
 for(const item of [
  ['claude','Claude (direct)'],
  ['omniroute','OmniRoute op deze computer'],
  ['litellm','LiteLLM op deze computer']]){
  const input=h('input',{type:'radio',name:'ai-route',value:item[0]});
  input.checked=item[0]===(status.sessie_route||'claude');
  if(item[0]==='omniroute'&&!(status.omniroute_providers||[]).length) input.disabled=true;
  input.addEventListener('change',async()=>{
   if(!input.checked) return;
   try{paintRoute(await call('ai.sessie',{route:item[0]}));}
   catch(e){paintRoute(status); routeState.textContent=e.message||'Mislukt.';}
  });
  routes.append(h('label',{class:'check'},input,item[1]));
 }
 const quickRow=h('div',{class:'ai-switch',role:'group','aria-label':'Wissel van AI'});
 const quickState=h('p',{class:'switch-state aan',role:'status'});
 const quickNote=h('p',{class:'message',role:'status'});
 function paintQuick(){
  const active=status.provider||chosen;
  quickState.textContent='Antwoordt nu: '+labelFor(active);
  quickRow.replaceChildren();
  for(const [id,name,sub] of QUICK){
   const spec=status.providers.find(item=>item.id===id);
   const missing=spec&&spec.geinstalleerd===false;
   const pressed=active===id;
   const b=h('button',{type:'button','aria-pressed':pressed?'true':'false'},
    h('strong',{},name),h('small',{},missing?sub+' · nog niet geïnstalleerd':sub));
   b.addEventListener('click',async()=>{
    const buttons=[...quickRow.querySelectorAll('button')];
    buttons.forEach(item=>{item.disabled=true;});
    quickNote.className='message';
    quickNote.textContent='Bezig…';
    if(id===(status.provider||chosen)){
     buttons.forEach(item=>{item.disabled=false;});
     quickNote.textContent=name+' antwoordt al.';
     return;
    }
    try{
     const saved=await call('ai.set',{provider:id,model:'',ollama_url:url.value.trim()});
     status.provider=(saved&&saved.provider)||id;
     status.model=(saved&&'model' in saved)?saved.model:'';
     chosen=status.provider;
     model.value=status.model||'';
     model.placeholder=status.providers.find(item=>item.id===chosen)?.model_leeg||'';
     draw();
     paintQuick();
     quickNote.textContent='Antwoordt nu: '+name+'. Open het paneel met Windows+C.';
    }catch(e){
     buttons.forEach(item=>{item.disabled=false;});
     quickNote.className='message error';
     quickNote.textContent=e.message||'Mislukt.';
    }
   });
   quickRow.append(b);
  }
 }
 paintQuick();
 const switchCard=h('section',{class:'card token-hero'},
  h('h3',{},'Wie antwoordt'),
  note('Eén tik wisselt meteen tussen Claude, ChatGPT, Gemini en lokaal. Lezen, concepten en formulieren gaan door. Belangrijke mail, betalen, wissen en wachtwoorden blijven een vraag met Toestaan.'),
  quickRow,quickState,quickNote);
 const modelCard=h('section',{class:'card'},
  h('h3',{},'Route van deze sessie'),
  note('Geen OpenClaude. Dat is een ongeautoriseerde afgeleide, met standaard een betaalde gateway en zoeken via Exa.'),
  note('Deze sessie wijst Claude naar OmniRoute of LiteLLM. Terug naar Claude haalt dat adres weer weg. Een andere agent, als je die wilt, is OpenCode (MIT) of Goose (Apache-2.0).'),
  routes,
  routeState,
  field('LiteLLM-adres (alleen deze computer)',routeName),
  button('LiteLLM-adres bewaren',async()=>{
   const saved=await call('ai.litellm',{url:routeName.value.trim()});
   paintRoute(saved);
   return 'Adres bewaard.';
  }),
  button('Terug naar Claude',async()=>{
   const saved=await call('ai.sessie',{route:'claude'});
   paintRoute(saved);
   return 'Deze sessie gaat weer naar Claude.';
  }));
 const chromeState=h('p',{class:'switch-state uit'},'Nog niet gecontroleerd.');
 const chromeCard=h('section',{class:'card token-hero'},
  h('h3',{},'Claude in Chrome'),
  note('De officiële extensie in jouw Chrome. Gmail en Outlook werken zo, zonder OAuth-client. Log gewoon in.'),
  chromeState,
  button('Chrome en de extensie klaarzetten',async()=>{
   const next=await call('chrome.setup');
   chromeState.textContent=(next&&next.tekst)||'Klaar.';
   chromeState.className='switch-state '+((next&&next.verbonden)?'aan':'uit');
   return next&&next.tekst||'De pagina van de extensie opent.';
  }));
 root.append(
  zenSwitch,
  godSwitch,
  switchCard,
  chromeCard,
  autoSwitch,
  tokenSwitch,
  modelCard,
  note('Een eigen modelnaam, of OpenCode of Goose, stel je hieronder in. Daarna Keuze bewaren. Het personage en de herinneringen blijven hetzelfde.'),
  card('Gebruik',
   h('label',{class:'check'},learn,'Leren van taken (korte les in het brein na een taak)'),
   button('Leervoorkeur bewaren',async()=>{
    await call('ai.leren',{aan:learn.checked});
    return learn.checked?'Leren staat aan.':'Leren staat uit. Cijfers blijven wel bewaard.';
   }),
   trend,
   lessons),
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
    const typed=model.value.trim();
    const saved=await call('ai.set',{provider:chosen,model:typed,ollama_url:url.value.trim()});
    status.provider=(saved&&saved.provider)||chosen;
    status.model=(saved&&'model' in saved)?saved.model:typed;
    chosen=status.provider;
    model.value=status.model||'';
    model.placeholder=status.providers.find(item=>item.id===chosen)?.model_leeg||'';
    draw();
    paintQuick();
    quickNote.className='message';
    quickNote.textContent='';
    return 'Gekozen: '+(saved.naam||labelFor(chosen))+'. Open daarna het paneel met Windows+C.';
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
 paintRoute(status);
 try{paintAuto(await call('auto.status'));}catch(e){paintAuto({aan:false,tekst:'Uit'});}
 try{
  const chrome=await call('chrome.status');
  chromeState.textContent=(chrome&&chrome.tekst)||chromeState.textContent;
  chromeState.className='switch-state '+((chrome&&chrome.verbonden)?'aan':'uit');
 }catch(e){}
 root.dataset.ai='ready';
}
