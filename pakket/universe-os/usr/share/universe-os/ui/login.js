import './login-power.js';
import {call,on,available,applySettings} from './api.js';
import {paintEarths} from './globe.js';
import {afterPaint,debugFPS} from './performance.js';
import {DEFAULT_CAM,distFor,drawSky,bigEarth,loginEarthPx} from './space.js';
import {startKlok} from './klok.js';
import {chargeToCore,formPlanet} from './explode.js';
import {opstartVlucht} from './opstartvlucht.js';
import {gebruikersRij} from './gebruikersrij.js';
const $=id=>document.getElementById(id);
// The Earth in space, seen with the camera of the 3D desktop (space.js); after login the desktop starts in this view.
const planetPx=loginEarthPx;
function scene(){
 const cam={...DEFAULT_CAM,dist:distFor(planetPx())};
 $('stars').replaceChildren(drawSky(document.createElement('canvas'),cam)); // no other planets: after logout they are all inside the Earth
 $('planet').style.width=planetPx()+'px';
 $('planet').style.setProperty('--p',planetPx()+'px'); // the clock on the Earth scales with it
}
startKlok($('klok-tijd'),$('klok-datum'));
const reducedMotion=()=>animations!=='full'||matchMedia('(prefers-reduced-motion: reduce)').matches;
// The login screen appears: light streams together and the planet forms, then the form slides in.
afterPaint().then(async()=>{
 scene();$('planet').append(bigEarth(planetPx()));debugFPS();paintEarths();
 await settingsKnown;
 // The screen starts on the glowing core (where logging out ended, and the same picture as kern.png); light streams
 // together and the planet forms out of it, then the form slides in.
 const kernWeg=()=>{$('core')?.remove();document.documentElement.style.background='#050815';}; // the core was also the first paint
 const gevormd=()=>{kernWeg();document.body.classList.remove('forming');document.body.classList.add('formed');};
 if(!reducedMotion()&&opstart){
  // First login screen of this boot: the start-up flight (opstartvlucht.js) from the core to the Earth; the user
  // planets come out of the Earth. The password bubble stays invisible (but works) until the planets have landed.
  document.body.classList.add('forming','vlucht');
  await opstartVlucht($('planet'),{knoppen:()=>[...$('users').querySelectorAll('button')],klok:$('klok'),onStart:kernWeg,onUi:gevormd});
  document.body.classList.remove('vlucht');plaatsKluis();
 }else if(!reducedMotion()){
  document.body.classList.add('forming');
  $('core').classList.add('fading');
  await formPlanet($('planet').getBoundingClientRect());
  // After logging out or locking (Axel, 28 Oct): the user planets come out of the Earth here too, as at start-up.
  document.body.classList.add('vlucht');
  await opstartVlucht($('planet'),{knoppen:()=>[...$('users').querySelectorAll('button')],onStart:kernWeg,onUi:gevormd,alleenPlaneten:true});
  document.body.classList.remove('vlucht');plaatsKluis();
 }
 gevormd();
});
addEventListener('resize',()=>{if(!leaving){scene();rijMaat();}});
// 0.3.1 (Jesse, t155u): geen inlogkaart meer. Inloggen gaat alleen via de kleine gebruikersplaneten: kies een planeet,
// direct bij die planeet verschijnt het wachtwoordveld (#kluis) met een pijltje; Enter of het pijltje logt in. Het
// inloggen zelf blijft login.authenticate/respond/start (LightDM/PAM). De grote planeet wordt niet aangeraakt.
const rij=gebruikersRij($('users'),{onKies:naam=>{if(!leaving&&!cancelling&&naam!==gekozen)kiesGebruiker(naam);},onBevestig:()=>{if(prompt)$('response').focus();}});
const RIJ_MARGE=36,PLANEET_VRIJ=.3; // the row stays below the middle of the screen: never higher than 30% of the big planet below the centre
function rijMaat(){const box=$('users');if(box.hidden)return;const onder=parseFloat(getComputedStyle(box).bottom)||96,vrij=innerHeight/2-onder-planetPx()*PLANEET_VRIJ-RIJ_MARGE;rij.grootte(Math.min(innerWidth-40,1100),Math.max(60,Math.min(innerHeight*.3,260,vrij)));plaatsKluis();}
let alleGebruikers=[],overzicht=false; // overzicht: all planets; otherwise, while a locked session exists, only the locked ones
const vergrendeld=()=>alleGebruikers.filter(g=>g.ingelogd);
on('login-users',d=>{d=d||{};if(Array.isArray(d.users)&&d.users.length)toonRij(d.users,gekozen||hint);});
function toonRij(users,voorkeur){
 if(!Array.isArray(users)||!users.length)return;alleGebruikers=users;
 const v=vergrendeld();if(!v.length)overzicht=true;
 const zicht=overzicht?users:v;
 $('other-user').hidden=overzicht; // only when a locked session exists, and until the overview is open
 $('users').hidden=false;const vorige=gekozen;gekozen='';
 rij.zetGebruikers(zicht,zicht.some(g=>g.naam===voorkeur)?voorkeur:(zicht.length===1?zicht[0].naam:''));
 if(!rij.gekozenNaam()&&vorige){annuleer();}
 rijMaat();
}
// The password bubble sits right below the chosen planet's name (or above the planet when the power panel is in the way).
function plaatsKluis(){
 const k=$('kluis'),knop=rij.gekozenKnop();if(k.hidden)return;
 if(!knop){k.style.left='50%';k.style.top='auto';k.style.bottom='24px';k.classList.remove('boven');return;}
 const r=knop.getBoundingClientRect(),w=k.offsetWidth,h=k.offsetHeight,x=Math.max(w/2+10,Math.min(innerWidth-w/2-10,r.left+r.width/2));
 let y=r.bottom+10;k.style.bottom='auto';k.style.left=x+'px';k.style.top=y+'px';k.classList.remove('boven');
 const p=document.querySelector('.login-power')?.getBoundingClientRect(),raakt=p&&y<p.bottom&&y+h>p.top&&x+w/2>p.left&&x-w/2<p.right;
 if(raakt||y+h>innerHeight-4){y=r.top-h-10;k.style.top=y+'px';k.classList.add('boven');}
}
if(typeof ResizeObserver==='function')new ResizeObserver(()=>plaatsKluis()).observe($('kluis'));
$('users').addEventListener('transitionend',()=>plaatsKluis());
let opstart=false,prompt=false,busy=false,leaving=false,cancelling=false,attempt=0,animations='full',pendingMessage='',gekozen='',hint='';
function toonKluis(veld){const k=$('kluis');k.hidden=false;$('prompt-label').hidden=!veld;$('submit').hidden=!veld;k.classList.toggle('alleen-melding',!veld);plaatsKluis();requestAnimationFrame(()=>{plaatsKluis();k.classList.add('open');});}
function verbergKluis(){const k=$('kluis');k.classList.remove('open');k.hidden=true;$('response').value='';$('message').textContent='';}
function error(text){leaving=false;busy=false;prompt=false;cancelling=false;document.body.classList.remove('depart');$('response').value='';$('submit').disabled=false;$('message').textContent=text;$('response').disabled=false;if(text)toonKluis(false);else verbergKluis();}
function showPrompt(data){const text=(data.text||'').trim(),label=({'Password:':'Wachtwoord','Username:':'Gebruikersnaam'}[text]||text||'Wachtwoord');prompt=true;busy=false;$('prompt-text').textContent=label;$('response').placeholder=label;$('response').type=data.secret?'password':'text';$('response').value='';$('response').disabled=false;$('message').textContent=pendingMessage;$('kluis').classList.toggle('fout',!!pendingMessage);pendingMessage='';$('submit').disabled=false;toonKluis(true);$('response').focus();}
$('kluis').addEventListener('submit',async event=>{
 event.preventDefault();if(busy||leaving||cancelling||!prompt)return;const request=attempt;busy=true;$('submit').disabled=true;$('kluis').classList.remove('fout');$('message').textContent='Aanmelding controleren…';
 try{const response=$('response').value;$('response').value='';prompt=false;await call('login.respond',{response});}
 catch(e){if(request===attempt)error(e.message);}
});
// Escape closes the bubble and goes back to the planet (the attempt is cancelled; nothing is kept).
$('kluis').addEventListener('keydown',e=>{if(e.key==='Escape'&&!leaving){e.preventDefault();const knop=rij.gekozenKnop();annuleer();knop?.focus();}});
async function annuleer(){attempt++;prompt=false;busy=false;verbergKluis();try{await call('login.cancel');}catch(e){}}
// 'Andere gebruiker' (only with a locked session): show the overview with all planets.
$('other-user').addEventListener('click',()=>{
 if(cancelling||leaving)return;overzicht=true;const wie=gekozen;toonRij(alleGebruikers,wie);
 ($('users').querySelector('button[tabindex="0"]'))?.focus();
});
// Wrong password: the message appears at that planet; a fresh PAM conversation for the same user makes the field ready again.
on('login-failed',async data=>{
 if(leaving)return;prompt=false;busy=true;$('response').value='';$('submit').disabled=true;pendingMessage=data.text;$('message').textContent=data.text;$('kluis').classList.add('fout');
 try{await call('login.authenticate',{user:data.user});}catch(e){pendingMessage='';error(e.message);}
});
// Choosing a planet cancels a running authentication and starts again for that user.
async function kiesGebruiker(naam){
 naam=String(naam||'').trim();if(!naam||leaving||cancelling)return;
 gekozen=naam;attempt++;const request=attempt;prompt=false;busy=true;pendingMessage='';$('response').value='';$('submit').disabled=true;$('message').textContent='';$('kluis').classList.remove('fout');
 try{await call('login.authenticate',{user:naam});}catch(e){if(request===attempt)error(e.message);}
}
on('login-cancelled',()=>{if(!prompt&&!busy)verbergKluis();});
on('login-prompt',showPrompt);on('login-message',data=>{$('message').textContent=data.text;toonKluis(prompt);});on('login-error',text=>{error(text);});
on('login-success',async data=>{
 if(leaving)return;leaving=true;$('response').value='';$('response').disabled=true;$('submit').disabled=true;$('kluis').classList.remove('fout');document.body.classList.add('depart');
 // The user already has a session: LightDM switches back to it, so no new desktop is started and no explosion.
 if(data&&data.logged_in){$('message').textContent='Welkom terug…';toonKluis(false);try{await call('login.start');}catch(e){error(e.message);}return;}
 $('message').textContent='Welkom…';toonKluis(false);
 // The planet charges up and collapses into the glowing core; the desktop starts from that same picture and
 // continues with the explosion (world.js), so the two are one animation.
 const planet=$('planet'),canvas=planet.querySelector('canvas');
 await chargeToCore(canvas,planet.getBoundingClientRect(),{reduced:reducedMotion(),onStart:()=>{planet.style.visibility='hidden';}});
 planet.style.visibility='hidden';
 try{await call('login.start');}catch(e){error(e.message);}
});
let settingsReady;const settingsKnown=new Promise(r=>{settingsReady=r;});setTimeout(()=>settingsReady(),3000);
(async()=>{if(!available){settingsReady();error('Open dit scherm via de Universe OS-inlogomgeving.');return;}try{const state=await call('login.ready');animations=state.animations||'full';opstart=!!state.opstart;applySettings({animations});settingsReady();hint=state.user||'';toonRij(state.users,hint);if(state.prompt&&gekozen)showPrompt(state.prompt);if(!gekozen)$('users').querySelector('button[tabindex="0"]')?.focus();}catch(e){error(e.message);}})();
