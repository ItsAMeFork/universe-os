// UOS-ANIM-001: the burst of the Earth in the last second of the update countdown and the close into the glowing core.
// Approved preview: uitvoer/UOS-ANIM-001-goedgekeurd.html (officialExplosion and the close of draw()).
//  buildBurst(seed):  once; the 260 sparks (same seeded sequence as the preview), bucketed for few strokes per frame.
//  drawBurst(...):    the exposed core dissolves into the glow cloud, two shock waves, sparks with light trails, a short
//                     white flash and a screen shake. No new Earth or fragments: the crust debris comes from
//                     aarde-breuk.js (pass its draw call as `debris` so it shakes along and sits under the flash).
//  drawClose(...):    glow and then the full-screen glowing core; it ends exactly on the logout picture (explode.js CORE,
//                     .world-core in world.css, kern.png), so the shutdown that follows starts from the same picture.
// Gradients are made once per context at unit size and drawn through a transform: nothing is created per frame except
// a handful of colour strings. Light mode draws exactly the same; only the caller's canvas has fewer pixels.

import {alpha} from './globe.js';
import {CORE} from './explode.js';

const TAU=Math.PI*2;
const clamp=x=>Math.max(0,Math.min(1,x)),smooth=x=>{x=clamp(x);return x*x*(3-2*x);},ease=t=>1-Math.pow(1-t,3);

/** Sparks of the burst. The preview drew them from the seeded generator after its 18x18 image cells; those cells are
 *  skipped here (aarde-breuk.js has the debris) but their draws are, so the sparks fly in the approved directions. */
export function buildBurst(seed=7){
 let s=seed>>>0||7;const rnd=()=>(s=(s*16807)%2147483647)/2147483647;
 for(let i=0;i<18;i++)for(let j=0;j<18;j++)if(Math.hypot((i+.5)/18-.5,(j+.5)/18-.5)<=.44)for(let n=0;n<4;n++)rnd();
 // Grouped by colour and line width (steps of .25 px): about 18 strokes per frame instead of 260.
 const buckets=new Map();
 for(let i=0;i<260;i++){
  const a=rnd()*TAU,speed=.15+rnd()*1.1,w=Math.round((.8+rnd()*2.2)*4)/4,hot=rnd()<.5,key=(hot?1000:0)+w*4;
  let b=buckets.get(key);if(!b)buckets.set(key,b={hot,w,v:[]});
  b.v.push(Math.cos(a)*speed,Math.sin(a)*speed);
 }
 return {sparks:[...buckets.values()].map(b=>({hot:b.hot,w:b.w,v:Float32Array.from(b.v)}))};
}

// Unit gradients per context (a CanvasGradient belongs to the context that made it).
const cache=new WeakMap();
function grads(g){
 let c=cache.get(g);if(c)return c;
 const core=g.createRadialGradient(.08,0,0,0,0,1); // the exposed core, lit a little from the impact side
 core.addColorStop(0,'#ffe6a0');core.addColorStop(.3,'#ffad39');core.addColorStop(.7,'#c64a1e');core.addColorStop(1,'#52261d');
 const cloud=g.createRadialGradient(0,0,0,0,0,1); // orange core turning purple; faded as a whole with globalAlpha
 cloud.addColorStop(0,'rgba(255,220,170,.8)');cloud.addColorStop(.3,'rgba(255,130,60,.45)');
 cloud.addColorStop(.7,'rgba(120,80,255,.18)');cloud.addColorStop(1,'rgba(60,40,160,0)');
 const glow=g.createRadialGradient(0,0,0,0,0,1);glow.addColorStop(0,'#ffb568');glow.addColorStop(1,'rgba(0,0,0,0)');
 const end=g.createRadialGradient(0,0,0,0,0,1);for(const [o,rgb,a] of CORE)end.addColorStop(o,`rgba(${rgb},${a})`);
 cache.set(g,c={core,cloud,glow,end});return c;
}
// Fills the screen rectangle (x0,y0,w,h) with a unit gradient centred on (x,y) with radius r.
function fillUnit(g,grad,x,y,r,x0,y0,w,h){
 if(w<=0||h<=0)return;
 g.save();g.translate(x,y);g.scale(r,r);g.fillStyle=grad;g.fillRect((x0-x)/r,(y0-y)/r,w/r,h/r);g.restore();
}

/** One frame of the burst, age = seconds since the crust broke (T-15). debris(g) is drawn inside the shake, under the
 *  flash, like the crust plates in the preview. Draws nothing of its own after 1.6 s. */
export function drawBurst(g,B,cx,cy,R,age,W,H,debris){
 if(!(R>0)||age<0)return;
 const t=clamp(age/1.6),collapse=smooth((age-.75)/2.1),e=ease(clamp(age/.75))*(1-collapse)*.5,big=Math.max(W,H);
 // Screen shake: up to 14 px, gone after 0.4 s; from the clock, so the same at every frame rate and in light mode.
 const shake=t<.25?(1-t/.25)*14:0,ox=Math.sin(age*91)*.5*shake,oy=Math.cos(age*67)*.5*shake;
 const G=grads(g);
 g.save();g.translate(ox,oy);
 if(t<1){
  // The exposed core dissolves into the blast while the same crust plates continue.
  if(age<.8){g.save();g.globalAlpha=1-smooth(age/.8);g.translate(cx,cy);g.scale(R,R);g.fillStyle=G.core;g.beginPath();g.arc(0,0,1,0,TAU);g.fill();g.restore();}
  // The glowing cloud grows and fades (only its own square, clipped to the screen; outside it is transparent).
  const rc=R*(1+e*5),x0=Math.max(-20,cx-rc),y0=Math.max(-20,cy-rc);
  g.globalAlpha=1-t;fillUnit(g,G.cloud,cx,cy,rc,x0,y0,Math.min(W+20,cx+rc)-x0,Math.min(H+20,cy+rc)-y0);g.globalAlpha=1;
  // Two shock waves in the plane of the orbit.
  for(let i=0;i<2;i++){
   const delay=i?.12:0,k=Math.max(0,(t-delay)/(1-delay));if(!k)continue;const r=R*(1+ease(k)*6);
   g.strokeStyle=`rgba(${i?'133,255,227':'255,190,120'},${alpha(.85*(1-k))})`;g.lineWidth=1.5+7*(1-k);
   g.beginPath();g.ellipse(cx,cy,r,r*.38,-.17,0,TAU);g.stroke();
  }
  // Sparks with light trails (the tail follows the uncollapsed path, as approved).
  const hot=`rgba(255,220,170,${alpha(1-t)})`,cool=`rgba(150,230,255,${alpha(.9*(1-t))})`,head=e*big,tail=ease(Math.max(0,t-.06))*big;
  g.lineCap='round';
  for(const b of B.sparks){
   const v=b.v;g.strokeStyle=b.hot?hot:cool;g.lineWidth=b.w;g.beginPath();
   for(let i=0;i<v.length;i+=2){g.moveTo(cx+v[i]*tail,cy+v[i+1]*tail);g.lineTo(cx+v[i]*head,cy+v[i+1]*head);}
   g.stroke();
  }
 }
 if(debris)debris(g);
 // White flash at the start.
 if(age<.18){g.globalAlpha=(1-age/.18)*.28;g.fillStyle='#fffaf0';g.fillRect(-20,-20,W+40,H+40);g.globalAlpha=1;}
 g.restore();
}

/** The close, k = 0..1 over the 1.9 s after zero (linear; the caller eases its own zoom). A warm glow swells and calms,
 *  then from k = .62 the full-screen core fades in and shrinks onto the logout picture: at k = 1 it is exactly
 *  drawCore(W,H) of explode.js (= .world-core, kern.png), with the timing of world.js animateWorld('out',{core:true}). */
export function drawClose(g,ex,ey,er,k,w,h){
 k=clamp(k);const G=grads(g),glow=Math.sin(Math.min(1,k*1.1)*Math.PI)*.65;
 if(glow>0&&er>0){g.save();g.globalAlpha=glow;fillUnit(g,G.glow,ex,ey,er*2,ex-er*2,ey-er*2,er*4,er*4);g.restore();}
 const c=Math.max(0,(k-.62)/.38),opacity=c*c*(3-2*c);if(opacity<=0)return;
 const scale=2.4-1.4*(1-Math.pow(1-c,2)),r=Math.min(w,h)*.55*scale;
 g.save();g.globalAlpha=opacity;g.fillStyle='#050815';g.fillRect(0,0,w,h);fillUnit(g,G.end,ex,ey,r,0,0,w,h);g.restore();
}
