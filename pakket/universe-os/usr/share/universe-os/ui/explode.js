// The planet explodes (login succeeded, Axel 10 Oct): the planet picture breaks into shards that fly outwards with a
// flash and an orange shock wave. One full-screen canvas, ~1.1 s, no CSS filters: light enough without a GPU.
// source: the planet canvas; rect: where it is on screen. Resolves when done. Instant with reduced motion.
export function explode(source,rect,{reduced=false,duration=1100,onStart}={}){
 if(reduced||!source||!rect.width)return Promise.resolve();
 const dpr=Math.min(devicePixelRatio||1,2),W=innerWidth,H=innerHeight;
 const canvas=document.createElement('canvas');canvas.width=Math.round(W*dpr);canvas.height=Math.round(H*dpr);
 canvas.setAttribute('aria-hidden','true');
 canvas.style.cssText='position:fixed;inset:0;width:100%;height:100%;z-index:50;pointer-events:none';
 document.body.append(canvas);
 const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);
 const cx=rect.left+rect.width/2,cy=rect.top+rect.height/2,R=rect.width/2;
 // Shards: cells of a grid inside the disc, each with its own outward speed and spin.
 const n=14,cell=rect.width/n,sw=source.width/n,sh=source.height/n,shards=[];
 let seed=7;const rnd=()=>(seed=(seed*16807)%2147483647)/2147483647;
 for(let i=0;i<n;i++)for(let j=0;j<n;j++){
  const x=rect.left+i*cell+cell/2,y=rect.top+j*cell+cell/2,dx=x-cx,dy=y-cy,d=Math.hypot(dx,dy);
  if(d>R*.98)continue;
  const a=Math.atan2(dy,dx)+(rnd()-.5)*.6,speed=(.5+rnd())*Math.max(W,H)*.9*(.4+d/R*.6);
  shards.push({sx:i*sw,sy:j*sh,x,y,vx:Math.cos(a)*speed,vy:Math.sin(a)*speed,spin:(rnd()-.5)*8,size:cell*(.9+rnd()*.5)});
 }
 const sparks=Array.from({length:120},()=>{const a=rnd()*Math.PI*2,s=(.3+rnd())*Math.max(W,H);return {vx:Math.cos(a)*s,vy:Math.sin(a)*s,r:1+rnd()*2.5};});
 return new Promise(resolve=>{
  const t0=performance.now();let started=false;
  const frame=now=>{
   const t=Math.min(1,(now-t0)/duration),e=1-Math.pow(1-t,3);
   c.clearRect(0,0,W,H);if(!started){started=true;onStart?.();}
   // flash: white core turning orange, fast in, slow out
   const flash=t<.12?t/.12:Math.max(0,1-(t-.12)/.5);
   if(flash>0){const g=c.createRadialGradient(cx,cy,0,cx,cy,R*(1.2+e*2));
    g.addColorStop(0,`rgba(255,250,235,${.95*flash})`);g.addColorStop(.35,`rgba(255,170,90,${.55*flash})`);g.addColorStop(1,'rgba(255,120,40,0)');
    c.fillStyle=g;c.fillRect(0,0,W,H);}
   // shock wave
   const wave=R*(.9+e*4.5);c.strokeStyle=`rgba(255,165,82,${.8*(1-t)})`;c.lineWidth=2+6*(1-t);
   c.beginPath();c.ellipse(cx,cy,wave,wave*.42,-.17,0,Math.PI*2);c.stroke();
   // sparks
   c.fillStyle=`rgba(255,214,160,${1-t})`;
   for(const s of sparks){c.beginPath();c.arc(cx+s.vx*e,cy+s.vy*e,s.r,0,7);c.fill();}
   // shards
   c.globalAlpha=Math.max(0,1-t*1.15);
   for(const s of shards){
    c.save();c.translate(s.x+s.vx*e,s.y+s.vy*e);c.rotate(s.spin*e);const k=1-e*.5;
    c.drawImage(source,s.sx,s.sy,sw,sh,-s.size*k/2,-s.size*k/2,s.size*k,s.size*k);c.restore();
   }
   c.globalAlpha=1;
   if(t<1)requestAnimationFrame(frame);else{canvas.remove();resolve();}
  };
  requestAnimationFrame(frame);
 });
}
