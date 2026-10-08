const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const source=fs.readFileSync('pakket/universe-os/usr/share/universe-os/ui/load-guard.js','utf8');
function page(name){
 const events={},messages=[],children=[];let timer;
 const element=()=>({style:{},children:[],setAttribute(){},append(...kids){this.children.push(...kids);},focus(){},remove(){this.removed=true;}});
 const context={document:{currentScript:{dataset:{page:name}},createElement:element,body:{append:n=>children.push(n)}},console:{error(){}},setTimeout:fn=>(timer=fn,1),clearTimeout(){timer=null;},location:{reload(){}},confirm:()=>false};
 context.window={addEventListener:(name,fn)=>events[name]=fn,webkit:{messageHandlers:{universe:{postMessage:s=>messages.push(JSON.parse(s))}}}};
 vm.runInNewContext(source,context);
 return {events,messages,children,ready:()=>context.window.__universePageReady(),timeout:()=>timer?.()};
}
let p=page('world');p.timeout();assert.equal(p.children.length,1);assert.equal(p.messages[0].cmd,'ui.error');p.ready();assert(p.children[0].removed);
p=page('world');p.ready();p.timeout();assert.equal(p.children.length,0);p.events.unhandledrejection({reason:new Error('later')});assert.equal(p.children.length,0);assert.equal(p.messages.length,1);
p=page('panel');p.events.error({message:'module syntax'});assert.equal(p.children.length,1);assert(p.messages.some(m=>m.cmd==='surface.size'));p.events.error({message:'again'});assert.equal(p.children.length,1);
p=page('world');p.timeout();const logout=p.children[0].children.at(-1);logout.onclick();assert(!p.messages.some(m=>m.cmd==='power'));logout.onclick();assert(p.messages.some(m=>m.cmd==='power'&&m.args.action==='logout'));
console.log('Load guard: timeout, early error, ready, late rejection and panel recovery OK');
