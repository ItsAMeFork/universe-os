// Two frames let the dark page paint before procedural artwork is generated.
export const afterPaint=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
export function debugFPS(){
 if(new URLSearchParams(location.search).get('fps')!=='1')return;
 const label=document.createElement('output');label.className='fps-debug';
 label.style.cssText='position:fixed;bottom:8px;right:8px;z-index:1000;background:#050815;color:#85ffe3;padding:8px;font:13px monospace;pointer-events:none';
 document.body.append(label);let start=performance.now(),frames=0,worst=0,last=start;
 function frame(now){
  if(document.hidden){start=last=now;frames=0;worst=0;requestAnimationFrame(frame);return;}
  worst=Math.max(worst,now-last);last=now;frames++;
  if(now-start>=1000){
   // Where the time goes (fps=1 only): the biggest JS costs measured with perfMark, per second as max/sum ms.
   const parts=Object.entries(PERF).map(([k,v])=>`${k} ${v.max.toFixed(0)}/${v.sum.toFixed(0)}`).join(' · ');
   label.textContent=`${(frames*1000/(now-start)).toFixed(1)} FPS · max ${worst.toFixed(0)} ms · ${innerWidth}×${innerHeight}${parts?' · '+parts:''}`;
   for(const v of Object.values(PERF)){v.max=0;v.sum=0;}frames=0;worst=0;start=now;}
  requestAnimationFrame(frame);
 }
 requestAnimationFrame(frame);
}

// Cost meter for the fps=1 overlay: perfMark('render',ms) per piece of work; nothing is kept without fps=1.
const PERF={},MEASURE=new URLSearchParams(location.search).get('fps')==='1';
export function perfMark(name,ms){if(!MEASURE)return;const v=PERF[name]||(PERF[name]={max:0,sum:0});v.max=Math.max(v.max,ms);v.sum+=ms;}
export const measuring=()=>MEASURE;
