import './login-power.js';
import {call,on,available,applySettings} from './api.js';
import {paintEarths} from './globe.js';
import {afterPaint,debugFPS} from './performance.js';
import {DEFAULT_CAM,distFor,drawSky,bigEarth} from './space.js';
import {chargeToCore,formPlanet} from './explode.js';
import {gebruikersRij} from './gebruikersrij.js';
const $=id=>document.getElementById(id);
// The Earth in space, seen with the camera of the 3D desktop (space.js); after login the desktop starts in this view.
const planetPx=()=>Math.min(innerWidth*.8,innerHeight*.78,650);
function scene(){
 const cam={...DEFAULT_CAM,dist:distFor(planetPx())};
 $('stars').replaceChildren(drawSky(document.createElement('canvas'),cam)); // no other planets: after logout they are all inside the Earth
 $('planet').style.width=planetPx()+'px';
}
const reducedMotion=()=>animations!=='full'||matchMedia('(prefers-reduced-motion: reduce)').matches;
// The login screen appears: light streams together and the planet forms, then the form slides in.
afterPaint().then(async()=>{
 scene();$('planet').append(bigEarth(planetPx()));debugFPS();paintEarths();
 await settingsKnown;
 // The screen starts on the glowing core (where logging out ended, and the same picture as kern.png); light streams
 // together and the planet forms out of it, then the form slides in.
 if(!reducedMotion()){
  document.body.classList.add('forming');
  $('core').classList.add('fading');
  await formPlanet($('planet').getBoundingClientRect());
 }
 $('core').remove();document.documentElement.style.background='#050815'; // the core was also the first paint
 document.body.classList.remove('forming');document.body.classList.add('formed');
});
addEventListener('resize',()=>{if(!leaving){scene();rijMaat();}});
// Gebruikersplaneten-rij: selecteren vult alleen de gebruikersnaam in (het inloggen zelf blijft login.authenticate/respond/start).
const rij=gebruikersRij($('users'),{onKies:naam=>{if(!leaving&&!cancelling)document.dispatchEvent(new CustomEvent('universe-select-user',{detail:naam}));},onBevestig:()=>{(prompt?$('response'):$('submit')).focus();}});
const RIJ_MARGE=36,KAART_GROEI=70; // the card grows ~62 px downwards when the password field shows: reserve it, so the rows do not jump
// The rows must never touch the login card (Jesse, 26 Oct: with 11+ users the top row grazed it): the height is the
// free space between the card and the row's bottom edge, minus room for the chosen planet's lift and a margin.
function rijMaat(){const box=$('users');if(box.hidden)return;const kaart=$('login').getBoundingClientRect(),onder=parseFloat(getComputedStyle(box).bottom)||96,groei=$('response').offsetParent===null?KAART_GROEI:0,vrij=innerHeight-onder-kaart.bottom-groei-RIJ_MARGE;rij.grootte(Math.min(innerWidth-40,1100),Math.max(60,Math.min(innerHeight*.3,260,vrij)));}
if(typeof ResizeObserver==='function')new ResizeObserver(()=>rijMaat()).observe($('login')); // the card grows with the password field and messages
on('login-users',d=>{d=d||{};if(Array.isArray(d.users)&&d.users.length)toonRij(d.users,$('user').value);});
function toonRij(users,hint){if(!Array.isArray(users)||!users.length)return;$('users').hidden=false;rij.zetGebruikers(users,hint);rijMaat();}
let prompt=false,busy=false,leaving=false,cancelling=false,attempt=0,animations='full',pendingMessage='';
function error(text){leaving=false;busy=false;prompt=false;cancelling=false;document.body.classList.remove('depart');$('response').value='';$('prompt-label').hidden=true;$('user').disabled=false;$('submit').disabled=false;$('submit').textContent='Verder';$('other-user').hidden=!text;$('other-user').disabled=false;$('message').textContent=text;$('user').focus();}
function showPrompt(data){const text=(data.text||'').trim();prompt=true;busy=false;$('other-user').hidden=false;$('prompt-label').hidden=false;$('prompt-text').textContent=({'Password:':'Wachtwoord','Username:':'Gebruikersnaam'}[text]||text||'Wachtwoord');$('response').type=data.secret?'password':'text';$('response').value='';$('message').textContent=pendingMessage;pendingMessage='';$('submit').disabled=false;$('submit').textContent='Inloggen';$('response').focus();}
$('login').addEventListener('submit',async event=>{
 event.preventDefault();if(busy||leaving||cancelling)return;const request=attempt;busy=true;$('submit').disabled=true;$('other-user').hidden=false;$('message').textContent='Aanmelding controleren…';
 try{
  if(prompt){const response=$('response').value;$('response').value='';prompt=false;await call('login.respond',{response});}
  else{$('user').disabled=true;await call('login.authenticate',{user:$('user').value});}
 }catch(e){if(request===attempt)error(e.message);}
});
$('other-user').addEventListener('click',async()=>{
 if(cancelling||leaving)return;attempt++;cancelling=true;busy=true;$('response').value='';$('submit').disabled=true;$('other-user').disabled=true;$('message').textContent='Aanmelding annuleren…';
 try{await call('login.cancel');}catch(e){error(e.message);$('other-user').hidden=false;}
});
// Wrong password: stay on this screen, empty the field and start a fresh PAM conversation for the same user, so the
// field is ready again. The password itself is never kept.
on('login-failed',async data=>{
 if(leaving)return;prompt=false;busy=true;$('response').value='';$('submit').disabled=true;pendingMessage=data.text;$('message').textContent=data.text;
 try{await call('login.authenticate',{user:data.user});}catch(e){pendingMessage='';error(e.message);}
});
// Selecting a user (the planet row dispatches this) cancels a running authentication and starts again for that user.
document.addEventListener('universe-select-user',async event=>{
 if(leaving||cancelling)return;const name=String(event.detail||'').trim();if(!name)return;
 attempt++;prompt=false;busy=true;pendingMessage='';$('response').value='';$('user').value=name;$('submit').disabled=true;$('message').textContent='';$('other-user').hidden=false;
 try{await call('login.authenticate',{user:name});}catch(e){error(e.message);}
});
on('login-cancelled',()=>{error('');$('user').value='';$('user').focus();});
on('login-prompt',showPrompt);on('login-message',data=>{$('message').textContent=data.text;});on('login-error',text=>{const cancelled=cancelling;error(text);if(cancelled)$('other-user').hidden=false;});
on('login-success',async data=>{
 if(leaving)return;leaving=true;$('response').value='';document.body.classList.add('depart');
 // The user already has a session: LightDM switches back to it, so no new desktop is started and no explosion.
 if(data&&data.logged_in){$('message').textContent='Welkom terug. Je sessie wordt geopend…';try{await call('login.start');}catch(e){error(e.message);}return;}
 $('message').textContent='Welkom. Universe OS wordt geopend…';
 // The planet charges up and collapses into the glowing core; the desktop starts from that same picture and
 // continues with the explosion (world.js), so the two are one animation.
 const planet=$('planet'),canvas=planet.querySelector('canvas');
 await chargeToCore(canvas,planet.getBoundingClientRect(),{reduced:reducedMotion(),onStart:()=>{planet.style.visibility='hidden';}});
 planet.style.visibility='hidden';
 try{await call('login.start');}catch(e){error(e.message);}
});
let settingsReady;const settingsKnown=new Promise(r=>{settingsReady=r;});setTimeout(()=>settingsReady(),3000);
(async()=>{if(!available){settingsReady();error('Open dit scherm via de Universe OS-inlogomgeving.');$('submit').disabled=true;return;}try{const state=await call('login.ready');animations=state.animations||'full';applySettings({animations});settingsReady();$('user').value=state.user;toonRij(state.users,state.user);if(state.prompt)showPrompt(state.prompt);}catch(e){error(e.message);$('submit').disabled=true;}})();
// A user name never contains \ or spaces. Some keyboards send an extra key (the one next to left Shift, "\" in the US
// layout) with the first keystroke after power-on, also in the BIOS (Axel's Gigabyte pc, 13 Oct): drop such characters
// so the name is not wrong. Letters, digits and . _ - stay; capitals are kept as typed (PAM decides).
$('user').addEventListener('input',e=>{const el=e.target,clean=el.value.replace(/[^A-Za-z0-9._-]/g,'');if(clean!==el.value){const at=Math.max(0,(el.selectionStart||0)-(el.value.length-clean.length));el.value=clean;el.setSelectionRange(at,at);}});
