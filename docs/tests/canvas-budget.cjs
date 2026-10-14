const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context={};vm.createContext(context);vm.runInContext(fs.readFileSync('pakket/universe-os/usr/share/universe-os/ui/canvas-budget.js','utf8').replace('export ',''),context);
for(const [w,h,dpr,soft] of [[1920,1080,1,true],[1920,1080,2,true],[3840,2160,2,true],[3840,2160,2,false],[1024,768,1,true]]){
 const scale=context.canvasScale(w,h,dpr,soft),pixels=w*h*scale*scale;
 assert(pixels<=(soft?1920*1080:3840*2160)+1);
 assert(scale>0&&scale<=2);
 if(w===1920&&dpr===2&&soft)assert.equal(scale,1);
 console.log(`${w}x${h} dpr${dpr} soft=${soft}: ${Math.round(pixels)} pixels (was ${w*h*Math.min(dpr,2)**2})`);
}
