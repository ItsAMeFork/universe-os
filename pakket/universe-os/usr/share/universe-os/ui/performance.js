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
  if(now-start>=1000){label.textContent=`${(frames*1000/(now-start)).toFixed(1)} FPS · max ${worst.toFixed(0)} ms · ${innerWidth}×${innerHeight}`;frames=0;worst=0;start=now;}
  requestAnimationFrame(frame);
 }
 requestAnimationFrame(frame);
}
