import './login-power.js';
import {call,on,available,applySettings} from './api.js';
import {paintEarths} from './globe.js';
import {afterPaint,debugFPS} from './performance.js';
import {DEFAULT_CAM,distFor,drawSky,farPlanets,bigEarth} from './space.js';
import {explode} from './explode.js';
const $=id=>document.getElementById(id);
// The Earth in space, seen with the camera of the 3D desktop (space.js); after login the desktop starts in this view.
const planetPx=()=>Math.min(innerWidth*.8,innerHeight*.78,650);
function scene(){
 const cam={...DEFAULT_CAM,dist:distFor(planetPx())};
 $('stars').replaceChildren(drawSky(document.createElement('canvas'),cam),...farPlanets(cam));
 $('planet').style.width=planetPx()+'px';
}
afterPaint().then(()=>{scene();$('planet').append(bigEarth(planetPx()));debugFPS();setTimeout(paintEarths,300);});
addEventListener('resize',()=>{if(!leaving)scene();});
let prompt=false,busy=false,leaving=false,cancelling=false,attempt=0,animations='full';
function error(text){leaving=false;busy=false;prompt=false;cancelling=false;document.body.classList.remove('depart');$('response').value='';$('prompt-label').hidden=true;$('user').disabled=false;$('submit').disabled=false;$('submit').textContent='Verder';$('other-user').hidden=!text;$('other-user').disabled=false;$('message').textContent=text;$('user').focus();}
function showPrompt(data){const text=(data.text||'').trim();prompt=true;busy=false;$('message').textContent='';$('other-user').hidden=false;$('prompt-label').hidden=false;$('prompt-text').textContent=({'Password:':'Wachtwoord','Username:':'Gebruikersnaam'}[text]||text||'Wachtwoord');$('response').type=data.secret?'password':'text';$('response').value='';$('submit').disabled=false;$('submit').textContent='Inloggen';$('response').focus();}
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
on('login-cancelled',()=>{error('');$('user').value='';$('user').focus();});
on('login-prompt',showPrompt);on('login-message',data=>{$('message').textContent=data.text;});on('login-error',text=>{const cancelled=cancelling;error(text);if(cancelled)$('other-user').hidden=false;});
on('login-success',async()=>{
 if(leaving)return;leaving=true;$('response').value='';$('message').textContent='Welkom. Universe OS wordt geopend…';document.body.classList.add('depart');
 const reduced=animations!=='full'||matchMedia('(prefers-reduced-motion: reduce)').matches;
 // The planet explodes; the desktop then starts in the same view and its planets burst out of the centre.
 const planet=$('planet'),canvas=planet.querySelector('canvas');
 await explode(canvas,planet.getBoundingClientRect(),{reduced,onStart:()=>{planet.style.visibility='hidden';}});
 planet.style.visibility='hidden';
 try{await call('login.start');}catch(e){error(e.message);}
});
(async()=>{if(!available){error('Open dit scherm via de Universe OS-inlogomgeving.');$('submit').disabled=true;return;}try{const state=await call('login.ready');animations=state.animations||'full';applySettings({animations});$('user').value=state.user;if(state.prompt)showPrompt(state.prompt);}catch(e){error(e.message);$('submit').disabled=true;}})();
