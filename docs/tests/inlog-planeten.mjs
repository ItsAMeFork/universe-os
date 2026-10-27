// 0.3.1 (t155u): inlogscherm zonder kaart. Headless Chromium met een nagebootste greeter-bridge (geen LightDM):
// geen kaart, wachtwoordveld bij de gekozen planeet, goed/fout wachtwoord, toetsenbord, 'Andere gebruiker' alleen bij
// een vergrendelde sessie, terugkeren naar die sessie, veel gebruikers, en de grote planeet staat op dezelfde plek.
import http from 'node:http';import {readFileSync,existsSync} from 'node:fs';import {extname,join,normalize} from 'node:path';import {fileURLToPath} from 'node:url';
let chromium;try{({chromium}=await import('playwright'));}catch{console.log('OVERGESLAGEN: playwright ontbreekt (npm install in docs/tests)');process.exit(0);}
const ROOT=fileURLToPath(new URL('../../pakket/universe-os/usr/share/universe-os/',import.meta.url));
const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.svg':'image/svg+xml','.json':'application/json'};
const srv=http.createServer((q,r)=>{const p=normalize(join(ROOT,decodeURIComponent(q.url.split('?')[0])));if(!p.startsWith(ROOT)||!existsSync(p)){r.writeHead(404);return r.end();}r.writeHead(200,{'content-type':types[extname(p)]||'application/octet-stream'});r.end(readFileSync(p));});
await new Promise(r=>srv.listen(0,'127.0.0.1',r));const URL_=`http://127.0.0.1:${srv.address().port}/ui/login.html`;
let browser;try{browser=await chromium.launch();}catch(e){console.log('OVERGESLAGEN: chromium ontbreekt');srv.close();process.exit(0);}
let fails=0;const check=(n,ok)=>{console.log((ok?'OK   ':'FOUT ')+n);if(!ok)fails++;};
const mock=(users,hint)=>`(()=>{const U=${JSON.stringify(users)},log=window.__log=[];let wie='';
 const ev=(n,d)=>setTimeout(()=>window.__universeEvent(n,d),20);
 const h={'login.ready':()=>({user:${JSON.stringify(hint||'')},prompt:null,users:U,animations:'off'}),
  'login.authenticate':a=>{wie=a.user;ev('login-prompt',{text:'Password:',secret:true});return true;},
  'login.respond':a=>{log.push(['respond',wie,a.response===wie+'-goed']);if(a.response===wie+'-goed')ev('login-success',{logged_in:!!(U.find(g=>g.naam===wie)||{}).ingelogd});else ev('login-failed',{user:wie,text:'Onjuist wachtwoord. Probeer het opnieuw.'});return true;},
  'login.start':()=>{log.push(['start',wie]);return true;},'login.cancel':()=>{ev('login-cancelled');return true;},
  'power.get':()=>({shutdown:true,suspend:true,restart:true})};
 window.webkit={messageHandlers:{universe:{postMessage:s=>{const m=JSON.parse(s);setTimeout(()=>{try{const f=h[m.cmd];window.__universeReply(m.id,!!f,f?f(m.args):'onbekend');}catch(e){window.__universeReply(m.id,false,e.message);}},5);}}}};
 matchMedia=(q=>()=>({matches:true,addEventListener(){},removeEventListener(){}}))();})()`;
async function open(users,hint,size={width:1600,height:900}){const p=await browser.newPage({viewport:size});await p.addInitScript(mock(users,hint));await p.goto(URL_);await p.waitForFunction(()=>document.body.classList.contains('formed'),null,{timeout:15000});await p.waitForTimeout(400);return p;}
const G=n=>Array.from({length:n},(_,i)=>({naam:'gebruiker'+(i+1),weergave:'Gebruiker '+(i+1)}));
const vis=(p,s)=>p.evaluate(s=>{const e=document.querySelector(s);if(!e)return false;const r=e.getBoundingClientRect(),c=getComputedStyle(e);return !e.hidden&&c.display!=='none'&&r.width>0&&+c.opacity>0;},s);
const planeet=p=>p.evaluate(()=>{const r=document.getElementById('planet').getBoundingClientRect();return [r.x,r.y,r.width,r.height].map(Math.round).join(',');});

// 1. geen kaart; 2 gebruikers; klik -> veld bij die planeet; fout -> melding bij die planeet; goed -> start
{
 const p=await open(G(2));
 check('geen inlogkaart: geen #login, geen titel/ondertitel/gebruikersnaamveld',await p.evaluate(()=>!document.getElementById('login')&&!document.getElementById('user')&&!document.body.innerText.includes('Jouw toegang')&&!document.querySelector('h1')));
 check('geen wachtwoordveld vóór een keuze (meerdere gebruikers)',!(await vis(p,'#kluis')));
 check("'Andere gebruiker' onzichtbaar zonder vergrendelde sessie",!(await vis(p,'#other-user')));
 await p.click('#users .gebruiker:nth-child(2) button');await p.waitForTimeout(600);
 check('klik: planeet uitgelicht en wachtwoordveld zichtbaar met focus',await vis(p,'#kluis')&&await p.evaluate(()=>document.querySelector('#users .gebruiker:nth-child(2)').classList.contains('gekozen')&&document.activeElement.id==='response'));
 const bij=await p.evaluate(()=>{const k=document.getElementById('kluis').getBoundingClientRect(),b=document.querySelector('#users .gekozen button').getBoundingClientRect();return Math.abs((k.left+k.right)/2-(b.left+b.right)/2)<2&&k.top>=b.bottom-1&&k.top-b.bottom<30;});
 check('wachtwoordveld staat direct bij (onder) die planeet',bij);
 await p.fill('#response','fout');await p.keyboard.press('Enter');await p.waitForTimeout(400);
 check('fout wachtwoord: melding bij de planeet, veld leeg en weer klaar',await p.evaluate(()=>document.getElementById('message').textContent.includes('Onjuist')&&document.getElementById('kluis').classList.contains('fout')&&document.getElementById('response').value===''&&!document.getElementById('kluis').hidden));
 await p.fill('#response','gebruiker2-goed');await p.click('#submit');await p.waitForTimeout(1500);
 const log=await p.evaluate(()=>window.__log);
 check('goed wachtwoord via het pijltje: sessie start voor gebruiker2',log.some(l=>l[0]==='start'&&l[1]==='gebruiker2'));
 check('wachtwoord nergens in de pagina bewaard',await p.evaluate(()=>!document.body.innerHTML.includes('gebruiker2-goed')&&document.getElementById('response').value===''));
 await p.close();
}
// 2. één gebruiker: meteen gekozen, veld klaar; Escape sluit; toetsenbord
{
 const p=await open(G(1));
 check('1 gebruiker: meteen gekozen en wachtwoordveld met focus',await vis(p,'#kluis')&&await p.evaluate(()=>document.activeElement.id==='response'));
 await p.keyboard.press('Escape');await p.waitForTimeout(300);
 check('Escape sluit het veld, focus terug op de planeet',!(await vis(p,'#kluis'))&&await p.evaluate(()=>document.activeElement.closest('#users')!==null));
 await p.keyboard.press('Enter');await p.waitForTimeout(100);
 await p.close();
}
{
 const p=await open(G(5));
 check('toetsenbord: focus start op de eerste planeet',await p.evaluate(()=>document.activeElement.closest('#users')!==null));
 await p.keyboard.press('ArrowRight');await p.keyboard.press('ArrowRight');await p.waitForTimeout(500);
 check('pijltjes kiezen een planeet en openen het veld daar',await vis(p,'#kluis')&&await p.evaluate(()=>document.querySelector('#users .gekozen .naam').textContent==='Gebruiker 2'));
 await p.keyboard.press('Enter');await p.waitForTimeout(200);
 check('Enter op de planeet zet de focus in het wachtwoordveld',await p.evaluate(()=>document.activeElement.id==='response'));
 await p.keyboard.type('gebruiker2-goed');await p.keyboard.press('Enter');await p.waitForTimeout(1500);
 check('Enter logt in',(await p.evaluate(()=>window.__log)).some(l=>l[0]==='start'&&l[1]==='gebruiker2'));
 await p.close();
}
// 3. vergrendelde sessie: alleen die planeet + 'Andere gebruiker'; terugkeren met één wachtwoord; overzicht
{
 const U=G(4);U[2].ingelogd=true;const p=await open(U,'gebruiker3');
 check("vergrendelde sessie: 'Andere gebruiker' zichtbaar",await vis(p,'#other-user'));
 check('alleen de vergrendelde planeet getoond, gekozen, met markering en veld',await p.evaluate(()=>{const l=[...document.querySelectorAll('#users .gebruiker')];return l.length===1&&l[0].classList.contains('gekozen')&&l[0].classList.contains('ingelogd');})&&await vis(p,'#kluis'));
 await p.click('#other-user');await p.waitForTimeout(500);
 check("'Andere gebruiker' toont het overzicht met alle planeten en verdwijnt",await p.evaluate(()=>document.querySelectorAll('#users .gebruiker').length===4)&&!(await vis(p,'#other-user')));
 await p.click('#users .gebruiker:nth-child(3) button');await p.waitForTimeout(500);
 await p.fill('#response','gebruiker3-goed');await p.keyboard.press('Enter');await p.waitForTimeout(800);
 check('terugkeren naar de vergrendelde sessie met één wachtwoord (login.start, "Welkom terug")',(await p.evaluate(()=>window.__log)).some(l=>l[0]==='start'&&l[1]==='gebruiker3')&&await p.evaluate(()=>document.getElementById('message').textContent.includes('terug')));
 await p.close();
}
// 4. veel gebruikers: alles binnen beeld, niets overlapt, planeten niet versleepbaar; grote planeet op dezelfde plek
{
 const ref=await open(G(1));const voor=await planeet(ref);await ref.close();
 for(const[n,sz]of[[2,{width:1600,height:900}],[12,{width:1600,height:900}],[40,{width:1280,height:720}]]){
  const p=await open(G(n),'',sz);
  const r=await p.evaluate(()=>{const b=[...document.querySelectorAll('#users button')].map(e=>e.getBoundingClientRect());const inb=b.every(x=>x.left>=0&&x.right<=innerWidth&&x.top>=0&&x.bottom<=innerHeight);let ov=false;for(let i=0;i<b.length;i++)for(let j=i+1;j<b.length;j++){const a=b[i],c=b[j];if(a.left<c.right-1&&c.left<a.right-1&&a.top<c.bottom-1&&c.top<a.bottom-1)ov=true;}return{n:b.length,inb,ov};});
  check(`${n} gebruikers (${sz.width}×${sz.height}): alle planeten zichtbaar, binnen beeld, geen overlap`,r.n===n&&r.inb&&!r.ov);
  const b=await p.$('#users .gebruiker:nth-child(1) button'),bb=await b.boundingBox(),t0=await p.evaluate(()=>document.querySelector('#users .gebruiker').style.transform);
  await p.mouse.move(bb.x+bb.width/2,bb.y+bb.height/2);await p.mouse.down();await p.mouse.move(bb.x+300,bb.y-200,{steps:8});await p.mouse.up();await p.waitForTimeout(300);
  check(`${n} gebruikers: slepen verplaatst geen planeet`,await p.evaluate(()=>document.querySelector('#users .gebruiker').style.transform)===t0);
  if(sz.width===1600)check(`${n} gebruikers: grote planeet op dezelfde plek en grootte (${voor})`,await planeet(p)===voor);
  await p.close();
 }
}
await browser.close();srv.close();process.exit(fails?1:0);
