// Shared clock for the full-screen animations (login, logout, lock, desktop start). Axel (14 Oct): every pc must run
// them smoothly, and they may never hang or stutter. The rules:
//  - an animation always ends: a timer finishes it even when no frame comes (hidden window, stalled renderer);
//  - it follows the clock: a slow frame skips ahead instead of stretching the animation;
//  - on a slow pc it switches to the light version (fewer particles, fewer pixels) instead of being skipped;
//  - only when even that is hopeless (one frame over 0.8 s) it jumps to the last picture.
// Before 14 Oct two frames over 250 ms skipped every later animation, so a VM or an old pc never saw them.
const params=new URLSearchParams(location.search);
let light=params.get('gfx')==='soft'||(navigator.hardwareConcurrency||2)<=2;
/** True on weak hardware or after slow frames: callers draw fewer particles and use fewer pixels. */
export const isLight=()=>light;
/** Runs frame(t) with t from 0 to 1 over `duration` ms; resolves after frame(1), at the latest shortly after `duration`. */
export function animate(duration,frame){
 return new Promise(resolve=>{
  const t0=performance.now();let last=0,slow=0,done=false,drawnEnd=false;
  const draw=t=>{drawnEnd=t>=1;try{frame(t);}catch(e){console.error(e);finish();}};
  const finish=()=>{if(done)return;done=true;clearTimeout(timer);if(!drawnEnd)draw(1);resolve();};
  const timer=setTimeout(finish,duration+1200);
  const step=now=>{
   if(done)return;
   // The first frame often waits for the page to settle: only gaps between our own frames count.
   if(last){const gap=now-last;if(gap>800){finish();return;}if(gap>120&&++slow>=2)light=true;}
   last=now;
   const t=Math.max(0,Math.min(1,(now-t0)/duration));draw(t);
   if(done)return;
   if(t<1)requestAnimationFrame(step);else finish();
  };
  requestAnimationFrame(step);
 });
}
