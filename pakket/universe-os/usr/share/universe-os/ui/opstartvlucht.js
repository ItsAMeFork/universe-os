// Start-up flight (Axel, 28 Oct, approved preview "opstart-gebruikersplaneten"): the first login screen of a boot flies
// through the universe (star streaks, nebulae, light streams), brakes smoothly at the Earth of the login screen (same
// place and size: the real planet fades in underneath) and the real user planets, with their profile photo when they
// have one, come out of the Earth with a soft light trail. Only the first time per boot (greeter.py ready: opstart,
// together with opstarten.wav); after logging out or locking the login screen still forms from the core (formPlanet).
// It starts on the glowing core (kern.png, the first picture of the login screen), so there is no jump.
// Signing in never waits for it: any key or click ends it at once, and motion.js ends it even when frames stall.
import {alpha} from './globe.js';
import {overlay} from './explode.js';
import {animate} from './motion.js';

const clamp=x=>Math.max(0,Math.min(1,x)),ease=x=>1-(1-clamp(x))**3;
const smooth=x=>{x=clamp(x);return x*x*x*(x*(x*6-15)+10);};
const rand=seed=>()=>(seed=(seed*16807)%2147483647)/2147483647;
export const AANKOMST=8.65,VLIEG=1.65,UI=8.2; // s: planets leave the Earth; flight time of one planet; buttons and clock
/** Timing for n user planets: delay between two planets (shorter with many accounts) and the end of the flight. */
export function tijden(n){const st=n>1?Math.min(.09,.9/(n-1)):0;return{st,eind:n>0?AANKOMST+(n-1)*st+VLIEG:9.4};}
/** Where planet i of n leaves the Earth (centre X,Y, disc radius R): the lower rim, fanned out, never wider than ±0.7 rad. */
export function vertrekpunt(i,n,X,Y,R){const stap=n>1?Math.min(.11,1.4/(n-1)):0,a=Math.PI/2+(i-(n-1)/2)*stap;return{x:X+Math.cos(a)*R*.85,y:Y+Math.sin(a)*R*.85};}
/** Position at progress p (0..1) from `van` to `naar`: a soft arc upwards; scale grows from 8/35 to 1 (as in the preview). */
export function baan(van,naar,p,S=1){return{x:van.x+(naar.x-van.x)*p,y:van.y+(naar.y-van.y)*p-45*S*Math.sin(p*Math.PI),s:(8+27*p)/35};}

/** planeet: #planet (its canvas is the Earth); knoppen(): the user buttons; onStart: after the first picture (remove the
 * core); onUi: once, when buttons and clock may appear. Always cleans up, also after an error or a skip. */
export async function opstartVlucht(planeet,{knoppen=()=>[],klok=null,onStart=()=>{},onUi=()=>{}}={}){
 const {canvas,c,W,H}=overlay();canvas.id='opstartvlucht';
 const rect=planeet.getBoundingClientRect(),earth=planeet.querySelector('canvas');
 const X=rect.left+rect.width/2,Y=rect.top+rect.height/2,R=rect.width*.44,S=Math.hypot(W,H)/Math.hypot(1920,1080),RC=Math.min(W,H)*.55,big=Math.max(W,H);
 const rnd=rand(11);
 const stars=Array.from({length:300},()=>({x:rnd()*W,y:rnd()*H,r:.4+rnd()*1.2,a:.15+rnd()*.55}));
 const cloud=document.createElement('canvas');cloud.width=Math.max(1,Math.round(W/2));cloud.height=Math.max(1,Math.round(H/2));
 {const n=cloud.getContext('2d'),sx=cloud.width/960,sy=cloud.height/540;
  for(let i=0;i<100;i++){const x0=rnd()*960,x=x0*sx,y=(270+Math.sin(x0/170)*100+(rnd()-.5)*180)*sy,r=(35+rnd()*100)*Math.min(sx,sy)||1,q=n.createRadialGradient(x,y,0,x,y,r);
   q.addColorStop(0,`rgba(${i%3?'55,100,170':'110,65,140'},.028)`);q.addColorStop(1,'rgba(0,0,0,0)');n.fillStyle=q;n.fillRect(x-r,y-r,r*2,r*2);}}
 const motes=Array.from({length:220},()=>({a:rnd()*Math.PI*2,d:(.5+rnd())*big*.7,end:rnd()*R,spin:(rnd()-.5)*2.5,r:.8+rnd()*2,blue:rnd()<.6}));
 const flightStars=Array.from({length:520},()=>({a:rnd()*Math.PI*2,r:(40+rnd()*1400)*S,z:rnd(),size:.5+rnd()*1.5}));
 // The real user planets: final place and size as laid out by gebruikersrij.js, measured before they move.
 const lijst=knoppen().map(knop=>{
  const bol=knop.querySelector('.kleinplaneet'),b=bol?.getBoundingClientRect(),k=knop.getBoundingClientRect();
  return b&&b.width?{knop,naam:knop.querySelector('.naam'),naar:{x:b.left+b.width/2,y:b.top+b.height/2},oy:b.top+b.height/2-k.top,
   hue:parseFloat(knop.parentNode?.style.getPropertyValue('--tint'))||200}:null;}).filter(Boolean);
 const {st,eind}=tijden(lijst.length);
 lijst.forEach((u,i)=>{u.van=vertrekpunt(i,lijst.length,X,Y,R);u.knop.style.transformOrigin=`50% ${u.oy}px`;u.knop.style.opacity='0';if(u.naam)u.naam.style.opacity='0';});
 planeet.style.transition='none';planeet.style.opacity='0';if(klok)klok.style.opacity='0';
 let ui=false;const toonUi=()=>{if(!ui){ui=true;onUi();}};
 let gestart=false;const start=()=>{if(!gestart){gestart=true;onStart();}};

 function glow(r,o){c.save();c.globalAlpha=clamp(o);const q=c.createRadialGradient(X,Y,0,X,Y,Math.max(1,r));
  for(const [p,col] of [[0,'255,247,236,1'],[.1,'255,214,160,.95'],[.3,'255,138,72,.5'],[.62,'120,84,255,.16'],[1,'60,40,160,0']])q.addColorStop(p,`rgba(${col})`);
  c.fillStyle=q;c.fillRect(0,0,W,H);c.restore();}
 function frame(t){
  // Background of the flight: it fades away on arrival, so the real sky of the login screen is underneath.
  const bg=1-smooth((t-6.6)/1.6);c.clearRect(0,0,W,H);
  if(bg>0){c.save();c.globalAlpha=bg;c.fillStyle='#050815';c.fillRect(0,0,W,H);
   const atmosphere=Math.sin(Math.PI*clamp(t/8.45));c.globalAlpha=bg*atmosphere*.85;
   if(atmosphere>.01)c.drawImage(cloud,-20*atmosphere,-10*atmosphere,W+40*atmosphere,H+20*atmosphere);
   c.globalAlpha=bg;for(const s of stars){const depth=1+.045*s.r*Math.sin(Math.PI*clamp(t/8.45)),x=X+(s.x-X)*depth,y=Y+(s.y-Y)*depth;
    c.fillStyle=`rgba(180,206,242,${s.a})`;c.beginPath();c.arc(x,y,s.r,0,Math.PI*2);c.fill();}
   c.restore();}
  // Star streaks: the flight speeds up, then brakes smoothly before the Earth.
  if(t<7.5){
   const speed=smooth((t-.3)/1.8)*(1-smooth((t-4.1)/2.8)),distance=1.55*smooth(t/6.9),fade=smooth(t/.7)*(1-smooth((t-5.5)/2));
   c.save();c.globalCompositeOperation='screen';
   for(const s of flightStars){const z=.16+((s.z-distance)%1+1)%1*2.5,scale=.52/z,dx=Math.cos(s.a)*s.r,dy=Math.sin(s.a)*s.r*.66,x=X+dx*scale,y=Y+dy*scale;
    if(x< -160||x>W+160||y< -160||y>H+160)continue;
    const tail=.52/(z+.12*speed),o=fade*Math.min(.85,.14+.25/z)*smooth((z-.16)/.15);if(o<.01)continue;
    c.strokeStyle=`rgba(170,215,255,${alpha(o)})`;c.lineWidth=s.size*Math.min(2,1/z);c.beginPath();c.moveTo(X+dx*tail,Y+dy*tail);c.lineTo(x,y);c.stroke();}
   const tunnel=c.createRadialGradient(X,Y,40*S,X,Y,1000*S);tunnel.addColorStop(0,'rgba(0,0,0,0)');tunnel.addColorStop(.48,`rgba(45,100,190,${alpha(speed*.045)})`);
   tunnel.addColorStop(.82,`rgba(90,150,255,${alpha(speed*.1)})`);tunnel.addColorStop(1,'rgba(0,0,0,0)');c.fillStyle=tunnel;c.fillRect(0,0,W,H);c.restore();
  }
  // Nebula arms and light streams pulled towards the Earth.
  if(t<8){const strength=Math.sin(Math.PI*clamp(t/8));c.save();c.globalCompositeOperation='screen';
   for(let j=0;j<9;j++){c.beginPath();for(let k=0;k<=65;k++){const u=k/65,a=j*Math.PI*2/9+u*1.8+t*.08,r=(80+u*850)*S,x=X+Math.cos(a)*r,y=Y+Math.sin(a)*r*.55+Math.sin(u*11+j)*12*u*S;
     if(k===0)c.moveTo(x,y);else c.lineTo(x,y);}c.lineWidth=2+j%3*2;c.strokeStyle=`rgba(90,155,225,${alpha(strength*.035)})`;c.stroke();}
   for(let i=0;i<90;i++){const p=clamp((t-.6-(i%15)*.14)/5.4);if(p<=0||p>=1)continue;const a=i*2.39996+.8*p*p,r=(1150*(1-p*p)+30)*S,tail=(8+70*p*p)*S,x=X+Math.cos(a)*r,y=Y+Math.sin(a)*r*.64;
    c.strokeStyle=`rgba(160,207,255,${alpha(Math.sin(p*Math.PI)*.3)})`;c.lineWidth=.6+(i%3)*.4;c.beginPath();c.moveTo(x+Math.cos(a)*tail,y+Math.sin(a)*tail*.64);c.lineTo(x,y);c.stroke();}
   c.restore();}
  // Light lines and rings that close in on the Earth (decoration, no hardware status).
  if(t<6.8){const fade=1-ease((t-5.9)/.9),rise=ease(t/1.5);c.save();c.globalCompositeOperation='screen';
   for(let i=0;i<14;i++){const a=i*Math.PI*2/14+.16,far=1200*S,near=75*S,p=clamp((t-.25-i*.075)/3.2),d=far+(near-far)*ease(p),angle=a+.14*Math.sin(p*Math.PI);
    c.strokeStyle=`rgba(60,160,255,${alpha(.09*rise*fade)})`;c.lineWidth=1;c.beginPath();c.moveTo(X+Math.cos(a)*far,Y+Math.sin(a)*far);c.quadraticCurveTo(X+Math.cos(a+.2)*500*S,Y+Math.sin(a+.2)*500*S,X,Y);c.stroke();
    if(p>0&&p<1){const l=(35+110*Math.sin(p*Math.PI))*S,x0=X+Math.cos(angle)*(d+l),y0=Y+Math.sin(angle)*(d+l),x1=X+Math.cos(angle)*d,y1=Y+Math.sin(angle)*d,g=c.createLinearGradient(x0,y0,x1,y1);
     g.addColorStop(0,'rgba(168,234,255,0)');g.addColorStop(1,`rgba(168,234,255,${alpha(fade)})`);c.strokeStyle=g;c.lineWidth=3;c.beginPath();c.moveTo(x0,y0);c.lineTo(x1,y1);c.stroke();}}
   for(let j=0;j<3;j++){const p=clamp((t-3.1-j*.45)/2.1);if(p>0&&p<1){c.strokeStyle=`rgba(104,190,255,${alpha(Math.sin(p*Math.PI)*.42*fade)})`;c.lineWidth=2;c.beginPath();c.ellipse(X,Y,(80+ease(p)*750)*S,(40+ease(p)*330)*S,-.22,0,Math.PI*2);c.stroke();}}
   const connect=Math.sin(Math.PI*clamp((t-3.25)/2.6));
   for(let j=0;j<3;j++){c.strokeStyle=`rgba(122,190,255,${alpha(connect*.23*fade)})`;c.lineWidth=1.5;c.beginPath();c.ellipse(X,Y,(150+j*36)*S,(80+j*24)*S,t*.24+j,0,Math.PI*1.65);c.stroke();}
   c.restore();}
  // One continuous stream of light: from the core (first picture) through the flight into the Earth.
  const form=smooth((t-5.4)/2.8),reveal=smooth((t-6.9)/1.75);
  if(t<8.9){const intro=Math.max(smooth(t/3),1-smooth(t/1.6)*.7),settle=smooth((t-5.4)/3.5);
   glow(RC*(.55+.45*intro)*(1-settle)+R*1.6*settle,Math.max(intro*.85,1-smooth(t/1.6))*(1-settle));
   const p=smooth((t-.3)/8.1),prev=smooth((t-.345)/8.1),o=(.18+.52*form)*smooth(t/1.8)*(1-smooth((t-7.55)/1.35));
   if(o>.005){c.lineCap='round';const blue=`rgba(140,210,255,${alpha(o)})`,warm=`rgba(255,200,140,${alpha(o)})`;
    for(const m of motes){const a=m.a+m.spin*(1-p),d=m.end+(m.d-m.end)*(1-p),a0=m.a+m.spin*(1-prev),d0=m.end+(m.d-m.end)*(1-prev);
     c.strokeStyle=m.blue?blue:warm;c.lineWidth=m.r;c.beginPath();c.moveTo(X+Math.cos(a0)*d0,Y+Math.sin(a0)*d0);c.lineTo(X+Math.cos(a)*d,Y+Math.sin(a)*d);c.stroke();}}}
  // The Earth: the real planet of the login screen fades in; while the flight background is still there, the same
  // picture is drawn on top of it, at the same place and size.
  planeet.style.opacity=String(reveal);
  if(earth&&reveal>0&&bg>0){c.save();c.globalAlpha=reveal*bg;c.drawImage(earth,rect.left,rect.top,rect.width,rect.height);c.restore();}
  if(t>=5.4&&t<9.1){const k=smooth((t-5.4)/1.8)*(1-smooth((t-7.1)/2));glow(R*1.6,k*.38);
   const q=c.createLinearGradient(0,Y,W,Y);q.addColorStop(0,'rgba(255,244,230,0)');q.addColorStop(.5,`rgba(255,244,230,${alpha(.35*k)})`);q.addColorStop(1,'rgba(255,244,230,0)');
   c.fillStyle=q;c.fillRect(0,Y-1.5-3*k,W,3+6*k);
   c.save();c.globalAlpha=k*.32;const halo=c.createRadialGradient(X,Y,R*.85,X,Y,R*1.28);halo.addColorStop(0,'rgba(130,200,255,0)');halo.addColorStop(.45,'rgba(130,200,255,.5)');halo.addColorStop(1,'rgba(130,200,255,0)');
   c.fillStyle=halo;c.fillRect(X-R*1.3,Y-R*1.3,R*2.6,R*2.6);c.restore();}
  // Clock and power buttons; then the user planets come out of the Earth, each with a soft trail.
  if(t>=UI)toonUi();if(klok)klok.style.opacity=String(smooth((t-UI)/1.2));
  lijst.forEach((u,i)=>{
   const p=smooth((t-AANKOMST-i*st)/VLIEG);if(p<=0){u.knop.style.opacity='0';return;}
   const {x,y,s}=baan(u.van,u.naar,p,S);
   u.knop.style.transform=p<1?`translate(${(x-u.naar.x).toFixed(1)}px,${(y-u.naar.y).toFixed(1)}px) scale(${s.toFixed(3)})`:'';
   u.knop.style.opacity=String(smooth(p/.25));if(u.naam)u.naam.style.opacity=String(smooth((p-.6)/.4));
   if(p<1){c.save();c.globalCompositeOperation='screen';const r=17.5*s;
    const trail=c.createLinearGradient(u.van.x,u.van.y,x,y);trail.addColorStop(0,`hsla(${u.hue},85%,75%,0)`);trail.addColorStop(1,`hsla(${u.hue},85%,75%,${alpha(.3*(1-p))})`);
    c.strokeStyle=trail;c.lineWidth=2;c.beginPath();c.moveTo(u.van.x,u.van.y);c.quadraticCurveTo((u.van.x+x)/2,y-70*S,x,y);c.stroke();
    const halo=c.createRadialGradient(x,y,r*.7,x,y,r*2);halo.addColorStop(0,`hsla(${u.hue},85%,65%,${alpha(.25*(1-p))})`);halo.addColorStop(1,`hsla(${u.hue},85%,65%,0)`);
    c.fillStyle=halo;c.fillRect(x-r*2,y-r*2,r*4,r*4);c.restore();}
  });
 }

 let klaar=false,overslaan;const overgeslagen=new Promise(r=>{overslaan=r;});
 const stop=()=>overslaan();
 addEventListener('keydown',stop,true);addEventListener('pointerdown',stop,true);
 try{
  frame(0);start();
  await Promise.race([animate(eind*1000,k=>{if(!klaar)frame(k*eind);}),overgeslagen]);
 }catch(e){console.error(e);}
 finally{
  klaar=true;removeEventListener('keydown',stop,true);removeEventListener('pointerdown',stop,true);
  for(const u of lijst){u.knop.style.transform='';u.knop.style.transformOrigin='';u.knop.style.opacity='';if(u.naam)u.naam.style.opacity='';}
  planeet.style.opacity='';planeet.style.transition='';if(klok)klok.style.opacity='';
  try{start();}catch(e){}toonUi();
  canvas.style.transition='opacity .25s ease';canvas.style.opacity='0';setTimeout(()=>canvas.remove(),300);
 }
}
