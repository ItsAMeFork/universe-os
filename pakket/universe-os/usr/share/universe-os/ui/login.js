import {call,on,available} from './api.js';
import {globe,starfield} from './globe.js';
const $=id=>document.getElementById(id);
$('planet').append(globe(182,true,640));$('stars').append(starfield());
let prompt=false,busy=false,leaving=false;
function error(text){leaving=false;busy=false;prompt=false;document.body.classList.remove('depart');$('response').value='';$('prompt-label').hidden=true;$('user').disabled=false;$('submit').disabled=false;$('submit').textContent='Verder';$('message').textContent=text;$('user').focus();}
function showPrompt(data){prompt=true;busy=false;$('prompt-label').hidden=false;$('prompt-text').textContent=data.text||'Wachtwoord';$('response').type=data.secret?'password':'text';$('response').value='';$('submit').disabled=false;$('submit').textContent='Inloggen';$('response').focus();}
$('login').addEventListener('submit',async event=>{
 event.preventDefault();if(busy||leaving)return;busy=true;$('submit').disabled=true;$('message').textContent='Aanmelding controleren…';
 try{
  if(prompt){const response=$('response').value;$('response').value='';prompt=false;await call('login.respond',{response});}
  else{$('user').disabled=true;await call('login.authenticate',{user:$('user').value});}
 }catch(e){error(e.message);}
});
on('login-prompt',showPrompt);on('login-message',data=>{$('message').textContent=data.text;});on('login-error',error);
on('login-success',async()=>{
 if(leaving)return;leaving=true;$('response').value='';$('message').textContent='Welkom. Universe OS wordt geopend…';document.body.classList.add('depart');
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 await new Promise(resolve=>setTimeout(resolve,reduced?30:1250));
 try{await call('login.start');}catch(e){error(e.message);}
});
(async()=>{if(!available){error('Open dit scherm via de Universe OS-inlogomgeving.');$('submit').disabled=true;return;}try{const state=await call('login.ready');$('user').value=state.user;if(state.prompt)showPrompt(state.prompt);}catch(e){error(e.message);$('submit').disabled=true;}})();
