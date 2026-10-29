const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const file=path.resolve(__dirname,'../../pakket/universe-os/usr/share/universe-os/ui/world-lite.js');
let handlers={},calls=[],started=[],stopped=0,now=1000,timers=[];
const elem=()=>({addEventListener(){},replaceChildren(){}});
const context={on:(n,f)=>handlers[n]=f,call:async(n,a)=>{calls.push(n);return n==='config.get'?{settings:{animations:'reduced'},world:{planets:[{id:'home'}]}}:[]},applySettings(){},toast(){},h:elem,document:{getElementById:elem,body:{style:{}}},window:{},performance:{now:()=>now},setTimeout:(f,ms)=>timers.push([f,ms]),motionAllowed:s=>s.animations!=='reduced',startUpdateScene:opts=>{started.push(opts);return {stop(){stopped++}}},console};
const text=fs.readFileSync(file,'utf8');
// meteoriet.js loads lazily: a broken scene module must not take the simple desktop down.
assert(!/^import .*meteoriet/m.test(text),'meteoriet.js must load lazily');
assert(text.includes("await import('./meteoriet.js')"));
const src=text.replace(/^import .*;\r?\n/gm,'').split("await import('./meteoriet.js')").join('({startUpdateScene:globalThis.startUpdateScene})');
vm.runInNewContext(src,context);
(async()=>{await new Promise(setImmediate);assert.equal(typeof handlers['launch-countdown'],'function','lite desktop must receive countdown');
await handlers['launch-countdown']({seconds:10,runup:6,elapsed:8});assert.equal(started.length,1);assert(Math.abs(started[0].elapsed-8)<.01);assert.equal(started[0].reduced,true);assert.equal(started[0].planets[0].id,'home');
await handlers['launch-countdown']({seconds:10,runup:6});assert.equal(started.length,1,'no duplicate');
handlers['logout-error']('test');assert.equal(stopped,1);
await handlers['launch-countdown']({seconds:10,runup:6});handlers['logout-begin']({action:'logout'});assert.equal(stopped,2);assert(calls.includes('logout.finish'));
console.log('PASS lite countdown, settings, late join, duplicate, cancellation, lazy scene module');})().catch(e=>{console.error(e);process.exitCode=1});
