// Planet animations of the login screen (Axel, 10 Oct: "much better"). Everything is drawn on one full-screen canvas
// with plain 2D drawing (no CSS filters), so it stays light without a GPU. Instant with reduced motion.
//  explodePlanet: the planet charges up (glow, light cracks, shaking), then explodes: flash, shards with light trails,
//                 sparks, two shock waves and a glowing cloud that fades into space.
//  formPlanet:    the reverse feeling when the login screen appears: light streams together and the planet forms.

import {alpha} from './globe.js';

function overlay(){
 const dpr=Math.min(devicePixelRatio||1,2),W=innerWidth,H=innerHeight;
 const canvas=document.createElement('canvas');canvas.width=Math.round(W*dpr);canvas.height=Math.round(H*dpr);
 canvas.setAttribute('aria-hidden','true');
 canvas.style.cssText='position:fixed;inset:0;width:100%;height:100%;z-index:50;pointer-events:none';
 document.body.append(canvas);
 const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);
 return {canvas,c,W,H};
}
const rand=seed=>()=>(seed=(seed*16807)%2147483647)/2147483647;
const ease=t=>1-Math.pow(1-t,3);
// Without a GPU (a VM, an old pc) one frame can take seconds: the 2 s explosion then held up the login for a minute
// (11 Oct, test VM). After two frames slower than 250 ms the animations stop and the rest is skipped.
let slow=false,slowFrames=0;
function run(duration,frame){
 return new Promise(resolve=>{
  if(slow){resolve();return;}
  const t0=performance.now();let last=t0;
  const step=now=>{
   if(now-last>250&&++slowFrames>=2)slow=true;
   last=now;if(slow){resolve();return;}
   const t=Math.max(0,Math.min(1,(now-t0)/duration));frame(t);if(t<1)requestAnimationFrame(step);else resolve();};
  requestAnimationFrame(step);
 });
}
/** Jagged light cracks across the disc, growing with `k` (0..1). */
function cracks(c,cx,cy,R,k,rnd){
 const lines=[];for(let i=0;i<9;i++){const pts=[[cx+(rnd()-.5)*R*.3,cy+(rnd()-.5)*R*.3]];let a=rnd()*Math.PI*2;
  for(let j=0;j<7;j++){a+=(rnd()-.5)*1.1;const [x,y]=pts[pts.length-1],l=R*(.12+rnd()*.16);pts.push([x+Math.cos(a)*l,y+Math.sin(a)*l]);}lines.push(pts);}
 return k=>{
  c.save();c.beginPath();c.arc(cx,cy,R*.98,0,Math.PI*2);c.clip();
  for(const pts of lines){const n=Math.max(1,Math.floor(pts.length*k));
   for(const [w,col] of [[7,'rgba(255,150,60,.35)'],[2.2,'rgba(255,240,210,.95)']]){
    c.strokeStyle=col;c.lineWidth=w;c.lineCap='round';c.beginPath();c.moveTo(...pts[0]);for(let i=1;i<n;i++)c.lineTo(...pts[i]);c.stroke();}}
  c.restore();
 };
}

export async function explodePlanet(source,rect,{reduced=false,onStart}={}){
 if(reduced||!source||!rect.width)return;
 const {canvas,c,W,H}=overlay(),rnd=rand(7);
 const cx=rect.left+rect.width/2,cy=rect.top+rect.height/2,R=rect.width*.44; // the disc inside the planet picture
 onStart?.();
 // 1. charge up (0.7 s): the planet swells a little, glows hotter, cracks of light spread, it shakes harder
 const drawCracks=cracks(c,cx,cy,R,0,rnd);
 await run(700,t=>{
  const e=t*t,shake=e*6,sx=(rnd()-.5)*shake,sy=(rnd()-.5)*shake,s=1+e*.06;
  c.clearRect(0,0,W,H);
  const g=c.createRadialGradient(cx,cy,R*.8,cx,cy,R*(1.5+e));g.addColorStop(0,`rgba(255,170,90,${alpha(.5*e)})`);g.addColorStop(1,'rgba(255,120,40,0)');
  c.fillStyle=g;c.fillRect(0,0,W,H);
  c.save();c.translate(cx+sx,cy+sy);c.scale(s,s);c.drawImage(source,-rect.width/2,-rect.height/2,rect.width,rect.height);c.restore();
  c.save();c.translate(sx,sy);drawCracks(e);c.restore();
  c.fillStyle=`rgba(255,200,140,${alpha(e*.35)})`;c.beginPath();c.arc(cx+sx,cy+sy,R*s,0,Math.PI*2);c.fill();
 });
 if(slow){canvas.remove();return;}
 // 2. explosion (1.6 s)
 const n=18,cell=rect.width/n,sw=source.width/n,sh=source.height/n,shards=[],big=Math.max(W,H);
 for(let i=0;i<n;i++)for(let j=0;j<n;j++){
  const x=rect.left+i*cell+cell/2,y=rect.top+j*cell+cell/2,dx=x-cx,dy=y-cy,d=Math.hypot(dx,dy);
  if(d>R)continue;
  const a=Math.atan2(dy,dx)+(rnd()-.5)*.5,speed=(.35+rnd()*.9)*big*(.5+d/R*.7);
  shards.push({sx:i*sw,sy:j*sh,x,y,vx:Math.cos(a)*speed,vy:Math.sin(a)*speed,spin:(rnd()-.5)*10,size:cell*(.9+rnd()*.6)});
 }
 const sparks=Array.from({length:260},()=>{const a=rnd()*Math.PI*2,s=(.15+rnd()*1.1)*big;
  return {vx:Math.cos(a)*s,vy:Math.sin(a)*s,r:.8+rnd()*2.2,hot:rnd()<.5};});
 await run(1600,t=>{
  const e=ease(t),shake=t<.25?(1-t/.25)*14:0,ox=(rnd()-.5)*shake,oy=(rnd()-.5)*shake;
  c.clearRect(0,0,W,H);c.save();c.translate(ox,oy);
  // glowing cloud: orange core turning purple, growing and fading
  const cloud=c.createRadialGradient(cx,cy,0,cx,cy,R*(1+e*5));
  cloud.addColorStop(0,`rgba(255,220,170,${alpha(.8*(1-t))})`);cloud.addColorStop(.3,`rgba(255,130,60,${alpha(.45*(1-t))})`);
  cloud.addColorStop(.7,`rgba(120,80,255,${alpha(.18*(1-t))})`);cloud.addColorStop(1,'rgba(60,40,160,0)');
  c.fillStyle=cloud;c.fillRect(-20,-20,W+40,H+40);
  // two shock waves in the plane of the orbit
  for(const [delay,col] of [[0,'255,190,120'],[.12,'133,255,227']]){
   const k=Math.max(0,(t-delay)/(1-delay));if(!k)continue;const r=R*(1+ease(k)*6);
   c.strokeStyle=`rgba(${col},${alpha(.85*(1-k))})`;c.lineWidth=1.5+7*(1-k);c.beginPath();c.ellipse(cx,cy,r,r*.38,-.17,0,Math.PI*2);c.stroke();
  }
  // sparks with light trails
  for(const s of sparks){
   const x=cx+s.vx*e,y=cy+s.vy*e,x0=cx+s.vx*ease(Math.max(0,t-.06)),y0=cy+s.vy*ease(Math.max(0,t-.06));
   c.strokeStyle=s.hot?`rgba(255,220,170,${alpha(1-t)})`:`rgba(150,230,255,${alpha(.9*(1-t))})`;c.lineWidth=s.r;c.lineCap='round';
   c.beginPath();c.moveTo(x0,y0);c.lineTo(x,y);c.stroke();
  }
  // shards of the planet, tumbling outwards with a hot edge
  c.globalAlpha=Math.max(0,1-t*1.1);
  for(const s of shards){
   const x=s.x+s.vx*e,y=s.y+s.vy*e,k=1-e*.45;
   c.save();c.translate(x,y);c.rotate(s.spin*e);
   c.drawImage(source,s.sx,s.sy,sw,sh,-s.size*k/2,-s.size*k/2,s.size*k,s.size*k);
   c.strokeStyle=`rgba(255,170,90,${alpha(.7*(1-t))})`;c.lineWidth=1.5;c.strokeRect(-s.size*k/2,-s.size*k/2,s.size*k,s.size*k);
   c.restore();
  }
  c.globalAlpha=1;
  // white flash at the start
  if(t<.18){c.fillStyle=`rgba(255,250,240,${alpha((1-t/.18)*.9)})`;c.fillRect(-20,-20,W+40,H+40);}
  c.restore();
 });
 canvas.remove();
}

export async function formPlanet(rect,{reduced=false}={}){
 if(reduced||!rect.width)return;
 const {canvas,c,W,H}=overlay(),rnd=rand(11);
 const cx=rect.left+rect.width/2,cy=rect.top+rect.height/2,R=rect.width*.44,big=Math.max(W,H);
 const motes=Array.from({length:220},()=>{const a=rnd()*Math.PI*2,d=(.5+rnd())*big*.7,end=rnd()*R;
  return {a,d,end,spin:(rnd()-.5)*2.5,r:.8+rnd()*2,blue:rnd()<.6};});
 await run(1300,t=>{
  const e=ease(t);c.clearRect(0,0,W,H);
  for(const m of motes){
   const a=m.a+m.spin*(1-e),d=m.end+(m.d-m.end)*(1-e),a0=m.a+m.spin*(1-ease(Math.max(0,t-.07))),d0=m.end+(m.d-m.end)*(1-ease(Math.max(0,t-.07)));
   c.strokeStyle=m.blue?`rgba(140,210,255,${alpha(.9*e)})`:`rgba(255,200,140,${alpha(.9*e)})`;c.lineWidth=m.r;c.lineCap='round';
   c.beginPath();c.moveTo(cx+Math.cos(a0)*d0,cy+Math.sin(a0)*d0);c.lineTo(cx+Math.cos(a)*d,cy+Math.sin(a)*d);c.stroke();
  }
  const g=c.createRadialGradient(cx,cy,0,cx,cy,R*1.4);g.addColorStop(0,`rgba(200,235,255,${alpha(.7*e*e)})`);g.addColorStop(1,'rgba(110,180,255,0)');
  c.fillStyle=g;c.fillRect(0,0,W,H);
 });
 // final flash while the real planet appears underneath
 await run(450,t=>{
  c.clearRect(0,0,W,H);const g=c.createRadialGradient(cx,cy,0,cx,cy,R*1.6);
  g.addColorStop(0,`rgba(220,240,255,${alpha(.75*(1-t))})`);g.addColorStop(1,'rgba(110,180,255,0)');c.fillStyle=g;c.fillRect(0,0,W,H);
 });
 canvas.remove();
}
