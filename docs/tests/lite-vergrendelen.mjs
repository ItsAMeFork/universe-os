// 0.3.6: vergrendelen/ontgrendelen in de eenvoudige wereld (world-lite.html), net als in de ruimtewereld: het scherm gaat
// op in de gloeiende kern en komt er weer uit; lock.ready en unlock.done komen altijd (anders wachtte universe-lock 6 s
// en bleef de wereld 4 s boven de vensters). Headless browser met een nagebootste shell-bridge.
import http from 'node:http';import {readFileSync,existsSync} from 'node:fs';import {extname,join,normalize} from 'node:path';import {fileURLToPath} from 'node:url';
let chromium;try{({chromium}=await import('playwright').then(m=>({chromium:process.env.ENG==='webkit'?m.webkit:m.chromium})));}catch{console.log('OVERGESLAGEN: playwright ontbreekt');process.exit(0);}
const ROOT=fileURLToPath(new URL('../../pakket/universe-os/usr/share/universe-os/',import.meta.url));
const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.svg':'image/svg+xml','.json':'application/json'};
const srv=http.createServer((q,r)=>{const p=normalize(join(ROOT,decodeURIComponent(q.url.split('?')[0])));if(!p.startsWith(ROOT)||!existsSync(p)){r.writeHead(404);return r.end();}r.writeHead(200,{'content-type':types[extname(p)]||'application/octet-stream'});r.end(readFileSync(p));});
await new Promise(r=>srv.listen(0,'127.0.0.1',r));const URL_=`http://127.0.0.1:${srv.address().port}/ui/world-lite.html`;
let browser;try{browser=await chromium.launch();}catch{try{browser=await chromium.launch({channel:'chrome'});}catch{console.log('OVERGESLAGEN: browser ontbreekt');srv.close();process.exit(0);}}
let fails=0;const check=(n,ok)=>{console.log((ok?'OK   ':'FOUT ')+n);if(!ok)fails++;};
const mock=animations=>`(()=>{const log=window.__log=[];
 const h={'config.get':()=>({settings:{animations:${JSON.stringify(animations)}},world:{}}),'apps.list':()=>[],'world.ready':()=>true,
  'lock.ready':()=>{log.push(['lock.ready',performance.now()]);return true;},'unlock.done':()=>{log.push(['unlock.done',performance.now()]);return true;}};
 window.webkit={messageHandlers:{universe:{postMessage:s=>{const m=JSON.parse(s);setTimeout(()=>{const f=h[m.cmd];window.__universeReply(m.id,!!f,f?f(m.args):'onbekend');},5);}}}};
})()`;
for(const animations of ['full','reduced']){
 const p=await browser.newPage({viewport:{width:1920,height:1080}});await p.addInitScript(mock(animations));await p.goto(URL_);await p.waitForTimeout(500);
 const t0=await p.evaluate(()=>{window.__universeEvent('lock-begin');return performance.now();});
 await p.waitForFunction(()=>window.__log.some(l=>l[0]==='lock.ready'),null,{timeout:5000}).catch(()=>{});
 const slot=await p.evaluate(t0=>{const l=window.__log.find(l=>l[0]==='lock.ready'),c=document.querySelector('canvas');let px=[0,0,0,0];
  if(c)px=[...c.getContext('2d').getImageData(c.width/2,c.height/2,1,1).data];return{ms:l?l[1]-t0:-1,px};},t0);
 check(`${animations}: vergrendelen meldt lock.ready (na ${Math.round(slot.ms)} ms, < 3 s)`,slot.ms>=0&&slot.ms<3000);
 check(`${animations}: eindbeeld is de gloeiende kern (licht in het midden)`,slot.px[3]>200&&slot.px[0]>200);
 const t1=await p.evaluate(()=>{window.__universeEvent('unlock');return performance.now();});
 await p.waitForFunction(()=>window.__log.some(l=>l[0]==='unlock.done'),null,{timeout:5000}).catch(()=>{});
 const los=await p.evaluate(t1=>{const l=window.__log.find(l=>l[0]==='unlock.done');return{ms:l?l[1]-t1:-1,canvas:!!document.querySelector('canvas')};},t1);
 check(`${animations}: ontgrendelen meldt unlock.done (na ${Math.round(los.ms)} ms, < 3 s) en de kern is weg`,los.ms>=0&&los.ms<3000&&!los.canvas);
 await p.close();
}
await browser.close();srv.close();console.log(fails?`${fails} FOUT`:'alles OK');process.exit(fails?1:0);
