const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const code=fs.readFileSync('pakket/universe-os/usr/share/universe-os/ui/updates-ui.js','utf8').replace(/^import .*\n/,'').replaceAll('export function','function');
const nodes=[],calls=[];let state={state:'available',count:4},failure=false;
const h=(tag,attrs={},...kids)=>{const n={tag,...attrs,kids,textContent:kids.filter(x=>typeof x==='string').join(''),events:{},isConnected:true,append(...items){this.kids.push(...items);},addEventListener(k,fn){this.events[k]=fn;}};nodes.push(n);return n;};
const context={h,Date,Set,setTimeout(){},call:async cmd=>{calls.push(cmd);if(cmd==='updates.install'&&failure)throw Error('Geen installatieservice');return state;}};
vm.createContext(context);vm.runInContext(code,context);
const settle=()=>new Promise(r=>setImmediate(r));
(async()=>{
 context.updatesView();await settle();
 const install=nodes.find(n=>n.textContent==='Updates installeren');
 assert.equal(install.hidden,false);assert.equal(install.disabled,false);
 state={state:'installing',count:4};await install.events.click();assert(calls.includes('updates.install'));assert.equal(install.disabled,true);
 state={state:'available',count:4};const check=nodes.find(n=>n.textContent==='Nu controleren');await check.events.click();failure=true;await install.events.click();assert(nodes.some(n=>String(n.textContent).includes('Installatie starten mislukt')));
 assert.equal(context.updateText({state:'current'}),'Geen updates beschikbaar volgens de laatste geslaagde controle.');
 assert(context.updateText({state:'waiting'}).includes('wacht'));
 console.log('Update UI: available/installing/error/current/waiting OK');
})().catch(e=>{console.error(e);process.exitCode=1;});
