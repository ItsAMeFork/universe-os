// Opstartvlucht (28 okt): eerste inlogscherm van een boot vliegt door het universum naar de aarde, daarna komen de
// echte gebruikersplaneten (met profielfoto) uit de aarde. Headless browser met een nagebootste greeter-bridge (zoals
// inlog-planeten.mjs). ENG=webkit draait hetzelfde in WebKit (zoals de greeter). FOTO=map: schermafbeeldingen per fase.
import http from 'node:http';import {readFileSync,existsSync,mkdirSync} from 'node:fs';import {extname,join,normalize} from 'node:path';import {fileURLToPath} from 'node:url';
const ROOT=fileURLToPath(new URL('../../pakket/universe-os/usr/share/universe-os/',import.meta.url));
let fails=0;const check=(n,ok)=>{console.log((ok?'OK   ':'FOUT ')+n);if(!ok)fails++;};

let chromium;try{({chromium}=await import('playwright').then(m=>({chromium:process.env.ENG==='webkit'?m.webkit:m.chromium})));}catch{console.log('OVERGESLAGEN (browserdeel): playwright ontbreekt');process.exit(fails?1:0);}
const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.svg':'image/svg+xml','.json':'application/json'};
const srv=http.createServer((q,r)=>{const p=normalize(join(ROOT,decodeURIComponent(q.url.split('?')[0])));if(!p.startsWith(ROOT)||!existsSync(p)){r.writeHead(404);return r.end();}r.writeHead(200,{'content-type':types[extname(p)]||'application/octet-stream'});r.end(readFileSync(p));});
await new Promise(r=>srv.listen(0,'127.0.0.1',r));const URL_=`http://127.0.0.1:${srv.address().port}/ui/login.html`;
// Playwright's eigen browser, anders (Windows zonder 'playwright install') de geïnstalleerde Chrome.
let browser;try{browser=await chromium.launch();}catch{try{browser=await chromium.launch({channel:'chrome'});}catch(e){console.log('OVERGESLAGEN: browser ontbreekt');srv.close();process.exit(0);}}
const FOTO=process.env.FOTO;if(FOTO)mkdirSync(FOTO,{recursive:true});
const PNG='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
const mock=(users,{opstart=true,animations='full'}={})=>`(()=>{const U=${JSON.stringify(users)},log=window.__log=[];let wie='';
 const ev=(n,d)=>setTimeout(()=>window.__universeEvent(n,d),20);
 const h={'login.ready':()=>({user:'',prompt:null,users:U,animations:${JSON.stringify(animations)},opstart:${opstart}}),
  'login.authenticate':a=>{wie=a.user;ev('login-prompt',{text:'Password:',secret:true});return true;},
  'login.respond':a=>{log.push(['respond',wie,a.response]);if(a.response===wie+'-goed')ev('login-success',{logged_in:false});else ev('login-failed',{user:wie,text:'Onjuist wachtwoord. Probeer het opnieuw.'});return true;},
  'login.start':()=>{log.push(['start',wie]);return true;},'login.cancel':()=>{ev('login-cancelled');return true;},
  'power.get':()=>({shutdown:true,suspend:true,restart:true})};
 window.webkit={messageHandlers:{universe:{postMessage:s=>{const m=JSON.parse(s);setTimeout(()=>{try{const f=h[m.cmd];window.__universeReply(m.id,!!f,f?f(m.args):'onbekend');}catch(e){window.__universeReply(m.id,false,e.message);}},5);}}}};
})()`;
const SIZE={width:1920,height:1080};

// 1. Rekenwerk (in de pagina: de module hoort bij de browser)
{
 const p=await browser.newPage();await p.goto(URL_.replace('login.html','common.css'));
 const r=await p.evaluate(async u=>{const {tijden,vertrekpunt,baan,AANKOMST,VLIEG}=await import(u);
  const v=Array.from({length:40},(_,i)=>vertrekpunt(i,40,960,540,228.8)),b0=baan({x:0,y:0},{x:100,y:200},0),b1=baan({x:0,y:0},{x:100,y:200},1);
  return{een:Math.abs(tijden(1).eind-(AANKOMST+VLIEG))<1e-9,veel:tijden(40).eind<=11.3&&tijden(6).eind<=11.3,
   rand:v.every(p=>Math.abs(Math.hypot(p.x-960,p.y-540)-228.8*.85)<1e-6&&p.y>540),
   baan:b0.x===0&&b0.y===0&&b1.x===100&&Math.abs(b1.y-200)<1e-9&&b1.s===1&&b0.s<.3};},URL_.replace('login.html','opstartvlucht.js'));
 check('1 account: vlucht klaar na aankomst + één planeetvlucht',r.een);
 check('veel accounts (40): vlucht nooit langer dan 11,3 s',r.veel);
 check('vertrekpunten liggen op de onderrand van de aarde',r.rand);
 check('baan begint bij de aarde (klein) en eindigt precies op de plek van de rij (schaal 1)',r.baan);
 await p.close();
}
async function open(users,opts={},media){const p=await browser.newPage({viewport:SIZE,reducedMotion:media||'no-preference'});await p.addInitScript(mock(users,opts));await p.goto(URL_);return p;}
const G=(n,foto=[])=>Array.from({length:n},(_,i)=>({naam:'gebruiker'+(i+1),weergave:'Gebruiker '+(i+1),foto:foto.includes(i)?PNG:''}));
const klaar=p=>p.waitForFunction(()=>document.body.classList.contains('formed')&&!document.body.classList.contains('vlucht')&&!document.getElementById('opstartvlucht'),null,{timeout:20000});
const planeet=p=>p.evaluate(()=>{const r=document.getElementById('planet').getBoundingClientRect();return [r.x,r.y,r.width,r.height].map(Math.round).join(',');});
const plekken=p=>p.evaluate(()=>[...document.querySelectorAll('#users .kleinplaneet')].map(e=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width].map(v=>Math.round(v)).join(',');}).join(' '));
const foto=async(p,naam)=>{if(FOTO)await p.screenshot({path:join(FOTO,naam+'.png')});};

// 2. Zonder vlucht (na afmelden): referentie voor plek en schaal van de aarde en de rij
const ref=await open(G(3,[1]),{opstart:false});await klaar(ref);
const refPlaneet=await planeet(ref),refPlekken=await plekken(ref);
check('na afmelden geen opstartvlucht (formPlanet uit de kern)',await ref.evaluate(()=>!document.getElementById('opstartvlucht')));
await ref.close();

// 3. Opstartvlucht met 3 accounts, één met profielfoto
{
 const p=await open(G(3,[1]));
 await p.waitForFunction(()=>!!document.getElementById('opstartvlucht'),null,{timeout:5000});
 const start=await p.evaluate(()=>({kern:!!document.getElementById('core'),vlucht:document.body.classList.contains('vlucht')}));
 check('vlucht begint en de kern is vervangen door de vlucht (geen zwart tussenscherm)',!start.kern&&start.vlucht);
 const midden=await p.evaluate(()=>{const c=document.getElementById('opstartvlucht'),x=c.getContext('2d').getImageData(c.width/2,c.height/2,1,1).data;return [...x];});
 check('eerste beeld van de vlucht is de gloeiende kern (licht in het midden)',midden[3]>200&&midden[0]>200);
 const t0=Date.now();for(const [ms,naam] of [[300,'0-kern'],[1500,'1-vlucht'],[4000,'2-vlucht-remt'],[7200,'3-aarde'],[9300,'4-planeten-komen']]){await p.waitForTimeout(Math.max(0,ms-(Date.now()-t0)));await foto(p,naam);}
 const tijdens=await p.evaluate(()=>{const f=document.querySelector('#users .kleinplaneet.met-foto');return !!f&&getComputedStyle(f).backgroundImage.includes('data:image/png');});
 check('profielfoto zichtbaar tijdens het uitvliegen',tijdens);
 await klaar(p);await p.waitForTimeout(400);await foto(p,'5-klaar');
 check('aarde na de vlucht op dezelfde plek en schaal als zonder vlucht ('+refPlaneet+')',await planeet(p)===refPlaneet);
 check('gebruikersplaneten na de vlucht precies op hun plek in de rij',await plekken(p)===refPlekken);
 check('profielfoto blijft na de vlucht',await p.evaluate(()=>document.querySelectorAll('#users .kleinplaneet.met-foto').length===1));
 check('geen achtergebleven inline-stijlen op de knoppen',await p.evaluate(()=>[...document.querySelectorAll('#users button')].every(b=>!b.style.transform&&!b.style.opacity)));
 check('aan/uit/slaap-knoppen zichtbaar',await p.evaluate(()=>{const e=document.querySelector('.login-power');return !!e&&+getComputedStyle(e).opacity>.9;}));
 // aanmelden: fout, dan goed
 await p.click('#users .gebruiker:nth-child(2) button');await p.waitForTimeout(500);
 await p.fill('#response','fout');await p.keyboard.press('Enter');await p.waitForTimeout(400);
 check('fout wachtwoord: melding bij de planeet',await p.evaluate(()=>document.getElementById('message').textContent.includes('Onjuist')));
 await p.fill('#response','gebruiker2-goed');await p.keyboard.press('Enter');
 await p.waitForFunction(()=>window.__log.some(l=>l[0]==='start'),null,{timeout:10000}).catch(()=>{});
 check('goed wachtwoord: sessie start',await p.evaluate(()=>window.__log.some(l=>l[0]==='start'&&l[1]==='gebruiker2')));
 await p.close();
}

// 4. Aanmelden wacht nooit: 1 account, meteen typen tijdens de vlucht
{
 const p=await open(G(1));
 await p.waitForFunction(()=>!!document.getElementById('opstartvlucht'),null,{timeout:5000});await p.waitForTimeout(1200);
 const t0=Date.now();await p.keyboard.type('gebruiker1-goed');
 await p.waitForFunction(()=>!document.body.classList.contains('vlucht'),null,{timeout:3000}).catch(()=>{});
 check('een toets beëindigt de vlucht direct (< 1 s)',Date.now()-t0<1000);
 check('getypte tekens komen in het wachtwoordveld',await p.evaluate(()=>document.getElementById('response').value==='gebruiker1-goed'));
 await p.keyboard.press('Enter');await p.waitForFunction(()=>window.__log.some(l=>l[0]==='start'),null,{timeout:10000}).catch(()=>{});
 check('meteen aanmelden tijdens de vlucht lukt',await p.evaluate(()=>window.__log.some(l=>l[0]==='start')));
 await p.close();
}

// 5. Veel accounts: allemaal bereikbaar
{
 const p=await open(G(30,[0,7,29]));await klaar(p);await foto(p,'6-dertig-accounts');
 const ok=await p.evaluate(()=>[...document.querySelectorAll('#users button')].every(b=>{const r=b.querySelector('.kleinplaneet').getBoundingClientRect();return r.width>=14&&r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight&&document.elementFromPoint(r.left+r.width/2,r.top+r.height/2)?.closest('button')===b;}));
 check('30 accounts: alle planeten in beeld en klikbaar',ok);
 await p.close();
}

// 6. Minder beweging (systeem en instelling): geen vlucht, alles meteen
for(const [naam,media,animations] of [['systeem: minder beweging','reduce','full'],['instelling: animaties beperkt','no-preference','reduced']]){
 const p=await open(G(2),{animations},media);await p.waitForTimeout(600);
 check(naam+': geen vlucht, scherm meteen klaar',await p.evaluate(()=>!document.getElementById('opstartvlucht')&&document.body.classList.contains('formed')));
 await p.close();
}

await browser.close();srv.close();
console.log(fails?`${fails} FOUT`:'alles OK');process.exit(fails?1:0);
