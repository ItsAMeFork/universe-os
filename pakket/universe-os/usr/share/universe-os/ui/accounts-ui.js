// Accounts hub: Google, Microsoft, IMAP/SMTP and CalDAV. Secrets never come back from the shell.
import {call as shellCall, h} from './api.js';

const note=t=>h('p',{class:'muted'},t);
const card=(title,...items)=>h('section',{class:'card'},h('h3',{},title),...items);
const field=(title,input)=>h('label',{},title,input);
const input=(type='text',value='')=>h('input',{type,value,autocomplete:'off'});

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
 * @param {{call?:Function}} api
 */
export async function mountAccounts(root, api={}){
 const call=api.call||shellCall;
 const live=h('div');
 const flowBox=h('div');
 let flow=null;

 async function reload(){
  const [accounts, screen]=await Promise.all([call('accounts.list'),call('scherm.status')]);
  live.replaceChildren();
  if(!accounts.length) live.append(note('Nog geen account gekoppeld. Je wachtwoorden en tokens blijven in de sleutelbos van deze computer.'));
  for(const account of accounts){
   const scopes=(account.scopes||[]).join(' · ')||'Geen rechten getoond';
   live.append(card(account.naam||account.adres||account.provider,
    note(`${account.provider} · ${account.adres||'geen adres'}${account.server?' · '+account.server:''}`),
    note(scopes),
    button('Ontkoppelen',async()=>{await call('accounts.disconnect',{id:account.id});await reload();return 'Ontkoppeld.';})));
  }
  const on=!!screen.toegestaan;
  const toggle=h('input',{type:'checkbox'});
  toggle.checked=on;
  const label=h('label',{class:'check'},toggle,'AI mag scherm bedienen');
  live.append(card('Scherm',
   note(on?'Aan voor deze aanmelding. Super+Escape zet het direct uit.':'Uit. De assistent kan het scherm niet sturen tot je dit aanzet. Het geldt tot je afmeldt. Aanzetten vraagt nog een venster; een bestand aanmaken is niet genoeg.'),
   note(`Compositor: ${screen.compositor||'onbekend'}. Invoer: ${screen.backend||'geen'}. Paniektoets: ${screen.paniek||'Super+Escape'}.`),
   label,
   button('Opslaan',async()=>{
    await call(toggle.checked?'scherm.toestaan':'scherm.intrekken');
    await reload();
    return toggle.checked?'Als je zojuist op Toestaan drukte, mag de assistent het scherm bedienen tot je afmeldt of Super+Escape drukt.':'Schermbediening uit.';
   })));
 }

 function providerCard(provider, naam){
  const client=input('text');
  client.placeholder='Client-id (publiek)';
  client.setAttribute('aria-label',naam+' client-id');
  const secret=input('password');
  secret.placeholder='Clientgeheim, als de app er een heeft';
  secret.setAttribute('aria-label',naam+' clientgeheim');
  const show=async(methode)=>{
   const started=await call('accounts.oauth_start',{provider,methode,client_id:client.value.trim(),client_secret:secret.value});
   secret.value='';
   flow=started.flow;
   const code=h('p',{style:'font-size:1.4em;letter-spacing:2px;color:var(--accent)'},started.user_code||'');
   flowBox.replaceChildren(card(naam+' koppelen',
    note(methode==='device'?'Vul deze code in op de geopende pagina.':'De browser opent om aan te melden. Kom daarna hier terug.'),
    started.verificatie?note(started.verificatie):null,
    code,
    button('Controleer',async()=>{
     const done=await call('accounts.oauth_poll',{flow});
     if(!done.klaar) return done.wacht||'Nog niet bevestigd.';
     flow=null;flowBox.replaceChildren();await reload();
     return 'Gekoppeld: '+(done.account?.adres||naam);
    })));
  };
  return card(naam+' (optioneel)',
   note('Alleen als je geen browserweg wilt. OAuth op deze computer of een apparaatcode. Het token gaat naar de sleutelbos, niet naar een bestand.'),
   field('Client-id',client),field('Clientgeheim (optioneel)',secret),
   button('Koppelen via browser',()=>show('loopback')),
   button('Koppelen met apparaatcode',()=>show('device')));
 }

 const imapName=input(),imapMail=input(),imapHost=input(),imapPort=input('number','993'),smtpHost=input(),smtpPort=input('number','465'),imapUser=input(),imapPw=input('password');
 const davName=input(),davMail=input(),davUrl=input(),davUser=input(),davPw=input('password');
 let browser = {tekst:'Log gewoon in in Chrome. Gmail en Outlook hebben geen OAuth-client nodig.'};
 try{browser=await call('chrome.status');}catch(e){}
 const browserState=h('p',{class:'switch-state '+(browser.verbonden?'aan':'uit')},browser.tekst||'Log gewoon in in Chrome.');
 root.append(
  card('Mail via de browser',
   note('Log gewoon in in Chrome. Gmail en Outlook Web werken in de browser waar jij al bent aangemeld. Er is geen OAuth-client en geen app-controle bij Google nodig.'),
   note('Lezen, sorteren, concepten en formulieren gaan door. Een kort antwoord naar iemand die je al schrijft mag mee als automatisch toestaan aan staat. Belangrijke mail, betalen, wissen en wachtwoorden blijven een vraag.'),
   browserState,
   button('Claude in Chrome openen',async()=>{
    const next=await call('chrome.setup');
    browserState.textContent=(next&&next.tekst)||'De extensiepagina opent.';
    return browserState.textContent;
   })),
  note('IMAP en OAuth hieronder zijn een extra weg, voor een eigen server of als je de browser niet wilt gebruiken. Ze zijn niet nodig voor Gmail of Outlook in Chrome.'),
  live, flowBox,
  providerCard('google','Google'),
  providerCard('microsoft','Microsoft'),
  card('IMAP en SMTP (optioneel)',
   note('Voor een eigen server, als je de browserweg niet gebruikt. Het wachtwoord gaat alleen naar de sleutelbos.'),
   field('Naam',imapName),field('E-mailadres',imapMail),field('IMAP-server',imapHost),field('IMAP-poort',imapPort),
   field('SMTP-server',smtpHost),field('SMTP-poort',smtpPort),field('Gebruikersnaam',imapUser),field('Wachtwoord',imapPw),
   button('IMAP koppelen',async()=>{
    const password=imapPw.value;imapPw.value='';
    await call('accounts.imap',{naam:imapName.value,adres:imapMail.value,imap_host:imapHost.value,imap_port:Number(imapPort.value)||993,
     smtp_host:smtpHost.value,smtp_port:Number(smtpPort.value)||465,user:imapUser.value||imapMail.value,password});
    await reload();return 'IMAP gekoppeld.';
   })),
  card('CalDAV',
   note('Agenda via een https-adres. Het wachtwoord gaat alleen naar de sleutelbos.'),
   field('Naam',davName),field('E-mailadres',davMail),field('CalDAV-adres',davUrl),field('Gebruikersnaam',davUser),field('Wachtwoord',davPw),
   button('CalDAV koppelen',async()=>{
    const password=davPw.value;davPw.value='';
    await call('accounts.caldav',{naam:davName.value,adres:davMail.value,url:davUrl.value,user:davUser.value||davMail.value,password});
    await reload();return 'CalDAV gekoppeld.';
   })));
 await reload();
 root.dataset.accounts='ready';
}
