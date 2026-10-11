const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const code=fs.readFileSync('pakket/universe-os/usr/share/universe-os/ui/claude-install-status.js','utf8').replace('export ','');
const ctx={setTimeout,Date};vm.createContext(ctx);vm.runInContext(code,ctx);
(async()=>{
 let t=0,n=0,installed=0,messages=[];
 const opts={now:()=>t,delay:async ms=>{t+=ms;},status:async()=>({installed:++n===3,version:'test'}),onInstalled:()=>installed++,onMessage:s=>messages.push(s)};
 assert.equal(await ctx.waitForClaude(opts),'installed');assert.equal(installed,1);assert.equal(n,3);
 t=0;n=0;installed=0;assert.equal(await ctx.waitForClaude({...opts,limit:6000,status:async()=>({installed:false})}),'timeout');assert.equal(installed,0);
 t=0;let active=true;assert.equal(await ctx.waitForClaude({...opts,alive:()=>active,delay:async()=>{active=false;}}),'closed');
 t=0;n=0;assert.equal(await ctx.waitForClaude({...opts,status:async()=>{if(++n===1)throw Error('offline');return {installed:true};}}),'installed');assert(messages.some(s=>s.includes('Statuscontrole mislukt')));
 console.log('Claude installation polling: installed/timeout/closed/retry OK');
})().catch(e=>{console.error(e);process.exitCode=1;});
