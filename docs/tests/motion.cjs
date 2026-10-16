// motion.js: animations always end, follow the clock and turn light on slow frames (Axel, 14 Oct: never hang or stutter).
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync('pakket/universe-os/usr/share/universe-os/ui/motion.js','utf8').replace(/export /g,'');
function load({cores=4,soft=false,frames}){
 let now=0;const queue=[];
 const ctx={URLSearchParams,setTimeout,clearTimeout,console:{error(){}},Promise,Math,
  location:{search:soft?'?gfx=soft':''},navigator:{hardwareConcurrency:cores},performance:{now:()=>now},
  // frames: list of frame gaps in ms; undefined = the renderer never draws a frame
  requestAnimationFrame:cb=>{if(!frames)return;const gap=frames.shift();if(gap===undefined)return;queue.push(()=>{now+=gap;cb(now);});setImmediate(()=>queue.shift()?.());}};
 vm.createContext(ctx);vm.runInContext(src+';this.animate=animate;this.isLight=isLight;',ctx);return ctx;
}
(async()=>{
 // Weak hardware starts light; a normal pc does not.
 assert.equal(load({cores:2}).isLight(),true);assert.equal(load({soft:true}).isLight(),true);assert.equal(load({cores:8}).isLight(),false);

 // Smooth frames: t runs from 0 to 1 and ends exactly on 1.
 let m=load({frames:Array(40).fill(16)}),seen=[];
 await m.animate(300,t=>seen.push(t));
 assert.equal(seen.at(-1),1);assert(seen.length>15);assert.equal(m.isLight(),false);

 // Slow frames (200 ms): the animation keeps the clock (few frames, still ends on 1) and switches to light.
 m=load({frames:Array(40).fill(200)});seen=[];
 await m.animate(1000,t=>seen.push(t));
 assert.equal(seen.at(-1),1);assert(seen.length<=8);assert.equal(m.isLight(),true);

 // Hopeless frames (a second each): jump to the last picture after the first gap.
 m=load({frames:[16,1000,1000,1000]});seen=[];
 await m.animate(2000,t=>seen.push(t));
 assert.equal(seen.at(-1),1);assert(seen.length<=3);

 // No frames at all (hidden window): a timer still finishes the animation with the last picture.
 m=load({frames:undefined});seen=[];const t0=Date.now();
 await m.animate(100,t=>seen.push(t));
 assert.deepEqual(seen,[1]);assert(Date.now()-t0<3000);

 // A drawing error never leaves a promise hanging.
 m=load({frames:Array(10).fill(16)});
 await m.animate(200,()=>{throw new Error('kapot');});

 console.log('motion.js: eindigt altijd, volgt de klok, lichte versie bij trage beelden');
})().catch(e=>{console.error(e);process.exitCode=1;});
