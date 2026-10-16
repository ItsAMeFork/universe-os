// Sharp, realistic planets for the 3D desktop (Axel, 12 Oct: "it still looks like a drawing, make it sharper on a
// real pc"). The quick globe() of globe.js shows at once; afterwards every visible planet is painted pixel by pixel
// with light and shadow (gas giants with turbulent bands and a storm, rocky planets with terrain and craters, an
// atmosphere at the edge) at the resolution it is shown on screen. Painting happens in short slices between frames,
// largest planet first, so the desktop never waits for it.
import {noise3,remember,cached,earthRows,MEMORY_GB} from './globe.js';
import {perfMark} from './performance.js';

const clamp=v=>v<0?0:v>1?1:v;
const ss=(a,b,v)=>{const t=clamp((v-a)/(b-a));return t*t*(3-2*t);};
function hsl(h,s,l){ // -> [r,g,b] 0..255
 h=((h%360)+360)%360/360;s/=100;l/=100;
 const q=l<.5?l*(1+s):l+s-l*s,p=2*l-q,f=t=>{t=(t+1)%1;return t<1/6?p+(q-p)*6*t:t<.5?q:t<2/3?p+(q-p)*(2/3-t)*6:p;};
 return [f(h+1/3)*255,f(h)*255,f(h-1/3)*255];
}
const L=(()=>{const v=[-.62,-.48,.62],n=Math.hypot(...v);return v.map(x=>x/n);})(); // light from the top left, as globe()

/** Rows of a planet into image data `d` (px*px*4). Yields per row so it can be painted in slices. */
export function* planetRows(seed,rock,px,d){
 if(!Number.isFinite(seed))seed=165;
 const hue=((Math.round(seed)%360)+360)%360;
 let s=(seed*7919+13)>>>0||31;const rand=()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296;};
 const n1=noise3(1000+hue*7+(rock?1:0)),n2=noise3(5000+hue*13);
 const R=px*.456,cx=px/2,cy=px/2,halo=rock?1.04:1.09;
 const tilt=(rand()-.5)*.6,ct=Math.cos(tilt),st=Math.sin(tilt),spin=rand()*6.28,cs=Math.cos(spin),sn=Math.sin(spin);
 // palette
 const light=hsl(hue+18,rock?28:55,rock?62:70),mid=hsl(hue,rock?24:52,rock?40:46),dark=hsl(hue-14,rock?30:58,rock?20:22);
 const accent=hsl(hue+150,40,60),atmo=hsl(hue,85,72),bands=4+Math.floor(rand()*5),phase=rand()*6.28;
 // a storm on gas giants, craters on rocky planets (as directions on the sphere)
 const dir=()=>{const u=rand()*2-1,t=rand()*6.28,q=Math.sqrt(1-u*u);return [q*Math.cos(t),u*.8,q*Math.sin(t)];};
 const storm=!rock&&rand()<.7?{c:dir(),r:.12+rand()*.1}:null;
 const craters=rock?Array.from({length:14},()=>({c:dir(),r:.05+Math.pow(rand(),2)*.22})):[];
 const mixc=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];
 for(let y=0;y<px;y++){
  for(let x=0;x<px;x++){
   const dx=(x+.5-cx)/R,dy=(y+.5-cy)/R,r=Math.sqrt(dx*dx+dy*dy),i=(y*px+x)*4;
   if(r>halo){d[i+3]=0;continue;}
   if(r>1){ // thin atmosphere halo, brighter on the lit side
    const lit=.3+.7*clamp(-(dx*L[0]+dy*L[1])/r*.9+.35),a=Math.pow(1-(r-1)/(halo-1),2.4)*(rock?.25:.5)*lit;
    d[i]=atmo[0];d[i+1]=atmo[1];d[i+2]=atmo[2];d[i+3]=a*255;continue;
   }
   const nz=Math.sqrt(1-r*r);
   // surface coordinates: spin around the vertical axis, then the axial tilt
   const ax=dx*cs+nz*sn,az=-dx*sn+nz*cs,bx=ax*ct-dy*st,by=ax*st+dy*ct,bz=az;
   let c;
   if(rock){
    const e=n1(bx*2.2+7,by*2.2+7,bz*2.2+7,5),fine=n2(bx*9,by*9,bz*9,2);
    c=e<.47?mixc(dark,mid,ss(.3,.47,e)):mixc(mid,light,ss(.47,.68,e));
    c=mixc(c,accent,ss(.62,.75,n2(bx*1.5+3,by*1.5,bz*1.5,2))*.18);
    let k=.9+.2*fine;
    for(const cr of craters){
     const dist=Math.acos(Math.max(-1,Math.min(1,bx*cr.c[0]+by*cr.c[1]+bz*cr.c[2])));
     if(dist<cr.r*1.25){const q=dist/cr.r;k*=q<1?.72+.18*q*q:1+.35*(1-(q-1)/.25);}
    }
    c=[c[0]*k,c[1]*k,c[2]*k];
   }else{
    const t=n1(bx*1.6+11,by*4+11,bz*1.6+11,4),w=n2(bx*5,by*14,bz*5,3);
    const lat=by+(t-.5)*.3;
    const v=(Math.sin(lat*bands*Math.PI+phase)*.62+Math.sin(lat*bands*2.7*Math.PI+phase*1.7)*.25+(w-.5)*.5)*.5+.5;
    c=mixc(dark,light,ss(.1,.9,v));c=mixc(c,mid,.35);
    if(storm){
     // an oval storm: latitude counts double, so it is wider than high
     const ex=bx-storm.c[0],ey=(by-storm.c[1])*1.8,ez=bz-storm.c[2],dist=Math.sqrt(ex*ex+ey*ey+ez*ez);
     if(dist<storm.r){const q=1-dist/storm.r;c=mixc(c,accent,ss(0,.6,q)*.75);c=mixc(c,light,ss(.75,1,q)*.5);}
    }
    // limb darkening of a thick atmosphere
    const limb=.62+.38*Math.pow(nz,.6);c=[c[0]*limb,c[1]*limb,c[2]*limb];
   }
   const lam=dx*L[0]+dy*L[1]+nz*L[2],day=ss(-.18,.42,lam),amb=.035;
   let R0=c[0]*(amb+(1-amb)*day),G0=c[1]*(amb+(1-amb)*day),B0=c[2]*(amb+(1-amb)*day);
   if(!rock){const spec=Math.pow(clamp(2*lam*nz-L[2]),24)*.18*day;R0+=spec*255;G0+=spec*255;B0+=spec*255;}
   const rim=Math.pow(1-nz,3)*(.2+.8*day)*(rock?.35:.7); // atmosphere seen through the edge
   R0=R0*(1-rim)+atmo[0]*rim;G0=G0*(1-rim)+atmo[1]*rim;B0=B0*(1-rim)+atmo[2]*rim;
   d[i]=R0;d[i+1]=G0;d[i+2]=B0;d[i+3]=clamp((1-r)*R+.5)*255;
  }
  yield y;
 }
}

// ----- painting queue: biggest planets first, in slices between frames -----
const queue=new Map(); // key -> job
let running=false;
// Weak: few cores, or the processor also draws the screen (gfx=soft: NVIDIA/unknown graphics, webview.py).
const weak=(navigator.hardwareConcurrency||2)<=2||new URLSearchParams(location.search).get('gfx')==='soft'||(MEMORY_GB>0&&MEMORY_GB<=4);
const SLICE=weak?5:9;

/** Planet picture `key` at `px`, painted into `canvas` when done (it may be painted already: cached). */
export function sharpenPlanet(canvas,seed,rock,px,priority){
 enqueue(canvas,`hq:${seed}:${!!rock}:${px}`,px,priority,d=>planetRows(seed,rock,px,d));
}
/** The Earth painted at `px` (the shipped earth.png is 720 px: blurry when you zoom in close). */
export function sharpenEarth(canvas,px,priority){
 enqueue(canvas,`hq-earth:${px}`,px,priority,d=>earthRows(px,d));
}
function enqueue(canvas,key,px,priority,rows){
 const hit=cached(key);
 if(hit){draw(canvas,hit,px);return;}
 const job=queue.get(key);
 if(job){job.targets.add(canvas);job.priority=Math.max(job.priority,priority);}
 else queue.set(key,{key,px,priority,rows,targets:new Set([canvas])});
 if(!running){running=true;requestAnimationFrame(work);}
}
function draw(canvas,src,px){
 if(!canvas.isConnected)return;
 if(canvas.width!==px){canvas.width=canvas.height=px;}
 const g=canvas.getContext('2d');g.clearRect(0,0,px,px);g.drawImage(src,0,0);
 if(canvas.classList.contains('earth'))try{g.getImageData(0,0,1,1);}catch{} // make WebKit show it (globe.js showNow)
 canvas.dataset.tier=String(px);
}
let current=null;
function work(){
 const t0=performance.now();try{workSlice(t0);}finally{perfMark('paint',performance.now()-t0);}
}
function workSlice(t0){
 const end=t0+SLICE;
 while(performance.now()<end){
  if(!current){
   let best=null;for(const j of queue.values()){for(const t of j.targets)if(!t.isConnected)j.targets.delete(t);if(!j.targets.size){queue.delete(j.key);continue;}if(!best||j.priority>best.priority)best=j;}
   if(!best){running=false;current=null;return;}
   queue.delete(best.key);
   const cv=document.createElement('canvas');cv.width=cv.height=best.px;
   const ctx=cv.getContext('2d'),image=ctx.createImageData(best.px,best.px);
   current={...best,cv,ctx,image,rows:best.rows(image.data)};
  }
  if(current.rows.next().done){
   current.ctx.putImageData(current.image,0,0);remember(current.key,current.cv);
   for(const t of current.targets)draw(t,current.cv,current.px);
   current=null;
  }
 }
 requestAnimationFrame(work);
}
