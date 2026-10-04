import {call,on,h,applySettings,available} from './api.js';

const $=id=>document.getElementById(id);
let file=null,checked=false,busy=false,removing=null,generation=0;
const installLabels={bezig:'Bezig',geslaagd:'Geslaagd',mislukt:'Mislukt','geen-snelkoppeling':'Geen snelkoppeling'};
const runLabels={'niet-getest':'Niet getest',gestart:'Gestart',fout:'Fout','start-mislukt':'Start mislukt'};
function message(text,error=false){$('message').textContent=text;$('message').classList.toggle('error',error);}
function controls(){
 $('choose').disabled=busy;$('install').disabled=busy||!file||!checked||!$('trust').checked;
 $('cancel').disabled=busy;$('trust').disabled=busy;
 for(const el of $('apps').querySelectorAll('button,select'))el.disabled=busy;
}
async function action(cmd,args={},button=null){
 if(button)button.disabled=true;
 try{return await call(cmd,args);}catch(error){message(error.message,true);throw error;}
 finally{if(button)button.disabled=busy;}
}
function button(text,fn,cls=''){
 const el=h('button',{class:cls},text);
 el.addEventListener('click',()=>Promise.resolve(fn(el)).catch(()=>{}));return el;
}
async function refresh(){
 const apps=await call('wine.list');$('apps').replaceChildren();
 if(!apps.length)$('apps').append(h('p',{class:'muted'},'Er zijn nog geen Windows-programma’s geïnstalleerd.'));
 for(const app of apps){
  const run=app.run||{},installed=app.install||{};
  const verdict=run.verdict==='werkt'?'Werkt volgens gebruiker':run.verdict==='problemen'?'Problemen volgens gebruiker':null;
  const card=h('article',{},h('h3',{},app.name),h('div',{class:'status'},
   h('p',{},'Installatie: ',installLabels[installed.status]||'Onbekend'),
   h('p',{},'Werking: ',runLabels[run.status]||'Onbekend')),
   verdict?h('p',{},verdict):null,h('p',{class:'muted'},installed.reden||''));
  const actions=h('div',{class:'actions'});
  for(const [index,entry] of (app.entries||[]).entries())actions.append(button('Start '+entry.name,async el=>{
   await action('wine.start',{slug:app.slug,index},el);message('Startverzoek verstuurd. Vernieuw na afsluiten voor het resultaat.');
  }));
  actions.append(button('Logboeken',el=>action('wine.logs',{slug:app.slug},el)),
   button('Wine-instellingen',el=>action('wine.winecfg',{slug:app.slug},el)),
   button('Wine Mono inschakelen',async el=>{
    if(!window.confirm('Wine Mono / Gecko toestaan? Wine kan daarna vragen onderdelen te downloaden. Internet is nodig.'))return;
    await action('wine.mono',{slug:app.slug},el);message('Wine Mono toegestaan. Volg eventuele Wine-vensters.');await refresh();
   }),button('Verwijderen',()=>{removing=app;$('wipe').checked=false;$('remove-name').textContent=app.name;$('remove-dialog').showModal();},'danger'));
  card.append(actions);
  const verdictSelect=h('select',{'aria-label':'Werking beoordelen van '+app.name},
   h('option',{value:''},'Nog geen oordeel'),h('option',{value:'werkt'},'Werkt volgens mij'),h('option',{value:'problemen'},'Ik ervaar problemen'));
  verdictSelect.value=run.verdict||'';
  verdictSelect.addEventListener('change',async()=>{
   try{await action('wine.verdict',{slug:app.slug,verdict:verdictSelect.value||null},verdictSelect);await refresh();}
   catch{verdictSelect.value=run.verdict||'';}
  });card.append(h('label',{},'Mijn beoordeling ',verdictSelect));
  if(app.candidates?.length){
   const select=h('select',{'aria-label':'Programmabestand voor '+app.name},...app.candidates.map(path=>h('option',{value:path},path)));
   card.append(h('label',{},'Kies een programmabestand binnen deze Wine-omgeving ',select),button('Snelkoppeling toevoegen',async el=>{
    await action('wine.exe',{slug:app.slug,path:select.value},el);await refresh();
   }));
  }
  card.append(h('details',{},h('summary',{},'Wine-omgeving en installatiebestand'),
   h('dl',{},h('dt',{},'Omgeving'),h('dd',{},app.slug),h('dt',{},'Architectuur'),h('dd',{},app.winearch||'Onbekend'),
    h('dt',{},'Wine-versie'),h('dd',{},app.wine||'Onbekend'),h('dt',{},'Bestand'),h('dd',{},app.installer?.path||'Onbekend'))));
  $('apps').append(card);
 }
 controls();
}
async function inspect(path){
 if(busy){message('Er loopt al een installatie. Wacht tot die klaar is.');return;}
 const request=++generation;file=null;checked=false;controls();$('confirmation').hidden=true;
 try{
  const info=await call('wine.info',{path});if(request!==generation)return;
  file=info;$('trust').checked=false;$('app-name').value=info.name.replace(/\.(exe|msi)$/i,'');
  $('check-error').textContent='Ondersteuning controleren…';$('file-info').replaceChildren();
  for(const [label,value] of [['Bestand',info.name],['Map',info.folder],['Grootte',new Intl.NumberFormat('nl-NL').format(info.size)+' bytes'],['Type',info.kind],['Architectuur',info.archText],['SHA-256',info.sha256]])
   $('file-info').append(h('dt',{},label),h('dd',{},value));
  $('download-warning').hidden=!info.downloaded;$('confirmation').hidden=false;$('trust').focus();
  try{await call('wine.check',{path:info.path});if(request===generation){checked=true;$('check-error').textContent='';}}
  catch(error){if(request===generation)$('check-error').textContent=error.message;}
 }catch(error){if(request===generation)message(error.message,true);}
 controls();
}
$('choose').addEventListener('click',async()=>{
 try{const path=await action('wine.choose',{},$('choose'));if(path)await inspect(path);}catch{}
});
$('trust').addEventListener('change',controls);
$('cancel').addEventListener('click',()=>{generation++;file=null;checked=false;$('confirmation').hidden=true;controls();$('choose').focus();});
$('refresh').addEventListener('click',()=>refresh().catch(error=>message(error.message,true)));
$('install').addEventListener('click',async()=>{
 if(busy||!checked||!file||!$('trust').checked)return;
 busy=true;controls();$('progress-section').hidden=false;$('progress-text').textContent='Installatie starten…';
 try{await call('wine.install',{path:file.path,sha256:file.sha256,name:$('app-name').value,confirmed:true});}
 catch(error){finish(error.message,true);}
});
function finish(text,error=false){busy=false;file=null;checked=false;generation++;$('confirmation').hidden=true;$('progress-section').hidden=true;message(text,error);controls();refresh().catch(e=>message(e.message,true));}
on('confirm',path=>inspect(path));
on('progress',data=>{$('progress-text').textContent=data.tekst||'Installatie bezig…';});
on('installed',app=>finish(app.install?.reden||'Installatie afgerond.',app.install?.status==='mislukt'));
on('install-error',error=>finish(String(error),true));
on('install-busy',()=>message('De installatie loopt nog. Rond het installatieprogramma af voordat je dit venster sluit.'));
$('remove-cancel').addEventListener('click',()=>{$('remove-dialog').close();removing=null;});
$('remove-confirm').addEventListener('click',async()=>{
 if(!removing||busy)return;
 const wipe=$('wipe').checked;
 if(wipe&&!window.confirm('Ook alle opgeslagen gegevens en logboeken van '+removing.name+' definitief wissen? Dit kan niet ongedaan worden gemaakt.'))return;
 busy=true;controls();$('remove-confirm').disabled=true;
 try{const result=await action('wine.remove',{slug:removing.slug,wipe});$('remove-dialog').close();removing=null;message(result.kept?'Programma verwijderd. Gegevens bewaard in: '+result.kept:'Programma verwijderd.');}
 catch{}finally{busy=false;$('remove-confirm').disabled=false;controls();await refresh().catch(error=>message(error.message,true));}
});
async function init(){
 if(!available){message('Geen verbinding met de Universe-shell. Open dit scherm vanuit Universe OS.',true);$('apps').textContent='Programma’s kunnen niet worden opgehaald.';$('support').textContent='Ondersteuning kan niet worden gecontroleerd.';$('choose').disabled=true;$('refresh').disabled=true;return;}
 try{
  const config=await call('config.get');applySettings(config.settings);
  const support=await call('wine.support');$('sandbox').textContent=support.sandbox;
  $('support').replaceChildren(h('p',{},support.wine||'Wine ontbreekt'),h('ul',{},...support.notes.map(note=>h('li',{},note))));
  await refresh();const path=await call('window.pending');if(path&&!file)await inspect(path);
 }catch(error){message(error.message,true);}
}
init();
