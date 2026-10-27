// Update countdown with a meteorite (UOS-ANIM-001, approved by Axel 27 Oct): the Universe OS planets stand around the
// Earth, the update planet itself flies in from deep space as a meteorite and strikes the visible face of the Earth.
// The crust cracks and crumbles off during the countdown (aarde-breuk.js), bursts in the last second
// (explosie-update.js) and everything is pulled into the glowing core. Timeline T in s, 0 = departure of the update
// planet: 0-4.7 flight, 4.7 impact, 6 countdown, 15 burst, 16 zero ('Opnieuw opstarten…'), 16-17.9 implosion.
// One rAF loop, time from performance.now (a slow frame skips ahead). Everything that does not move is built once
// (sprites, gradients, fracture network); the light version (gfx=licht/soft, isLight()) draws exactly the same
// animation and only uses fewer canvas pixels. Reduced motion: still Earth, planets, ring and text.
// The shell stays in charge of the restart: this picture never starts one.
import {canvasScale} from './canvas-budget.js';
import {isLight} from './motion.js';
import {globe} from './globe.js';
import {buildFracture,drawCracking,drawDebris,disposeFracture} from './aarde-breuk.js';
import {buildBurst,drawBurst,drawClose} from './explosie-update.js';

const IMPACT=4.7,COUNT=6,BURST=15,ZERO=16,CLOSE=1.9,END=ZERO+CLOSE+.7,TAU=Math.PI*2;
const clamp=x=>x<0?0:x>1?1:x,smooth=x=>{x=clamp(x);return x*x*(3-2*x);};
const ease=k=>k<.5?4*k*k*k:1-Math.pow(-2*k+2,3)/2;
const GFX=new URLSearchParams(location.search).get('gfx');
// Fallback layout at zero specificity (:where), so world.css always wins.
const STYLE=`:where(.update-scene){position:absolute;inset:0;z-index:40;overflow:hidden;background:#02040c;color:#edf7ff;font-family:system-ui,sans-serif}
:where(.update-scene canvas){position:absolute;inset:0;width:100%;height:100%;display:block}
:where(.update-scene-count){position:absolute;left:var(--x,50%);top:var(--y,50%);transform:translate(-50%,-50%);margin:0;font-size:calc(var(--u,100vw)*.061);font-weight:400;line-height:1;color:#edfcff;text-shadow:0 0 6px #8ceaff;font-variant-numeric:tabular-nums;opacity:0;transition:opacity .7s}
:where(.update-scene.counting .update-scene-count){opacity:1}
:where(.update-scene.done .update-scene-count){opacity:0;transition-duration:1.9s}
:where(.update-scene.reduced .update-scene-count){transition:none}
:where(.update-scene-label,.update-scene-sub){position:absolute;left:4%;right:4%;margin:0;text-align:center;transform:translateY(-50%)}
:where(.update-scene-label){top:87%;font-size:max(14px,calc(var(--u,100vw)*.024));font-weight:500}
:where(.update-scene-sub){top:93.5%;font-size:max(11px,calc(var(--u,100vw)*.014));color:#a8bfce}`;

// A soft radial glow as one cached sprite per colour, drawn scaled (no gradient per frame).
function glowSprite(color,px=128){
 const c=document.createElement('canvas');c.width=c.height=px;const g=c.getContext('2d'),h=px/2;
 const a=g.createRadialGradient(h,h,0,h,h,h);a.addColorStop(0,color);a.addColorStop(1,'rgba(0,0,0,0)');g.fillStyle=a;g.fillRect(0,0,px,px);return c;
}
const GLOWS=['#373377','#07596b','#ff872f','#ffe3b5','#ffc98c','#ffb775','#9b6450','#4e4543'];

// Seeded star field (same as the approved preview): direction times distance, and depth per star.
const STARS=Array.from({length:460},(_,i)=>{const r=.08+((i*73)%457)/457;return {c:Math.cos(i*2.399963)*r,s:Math.sin(i*2.399963)*r,z:((i*113)%461)/461,big:i%7===0};});
const STAR_LEVELS=8; // stars are stroked in a few opacity groups instead of one path each
// Impact sparks grouped by colour, width and opacity: a handful of paths instead of 110.
const SPARK_GROUPS=(()=>{const m=new Map();for(let i=0;i<110;i++){const k=`${i%5}:${i%4?1:0}:${i%3}`;if(!m.has(k))m.set(k,{alpha:.3+(i%5)*.12,color:i%4?'#ffad59':'#ffe4bd',width:1+(i%3)*.5,list:[]});
 const a=-2.8+(i%37)/36*2.6;m.get(k).list.push({cos:Math.cos(a),sin:Math.sin(a),speed:.3+(i%11)*.08});}return [...m.values()];})();
// Dust clouds after the impact, the spiral of particles towards the Earth, the impact dust ring and the meteor trail.
const DUST=Array.from({length:18},(_,i)=>{const a=-2.7+(i%7)*.31;return {cos:Math.cos(a),sin:Math.sin(a),f:.5+i%4*.23,g:1+(i%3)*.16};});
const SPIRAL=Array.from({length:44},(_,i)=>({base:i/44,a:i*2.399,size:1+(i%3)*.4}));
const IMPACT_DOTS=Array.from({length:80},(_,i)=>({cos:Math.cos(i*2.399),sin:Math.sin(i*2.399),f:.7+i%7*.25}));
const TRAIL=Array.from({length:16},(_,i)=>({base:i*.137,side:Math.sin(i*7)}));
// The shock wave travelling over the visible face of the globe from the impact point.
const SHOCK=(()=>{const n=[.38,-.36,Math.sqrt(1-.38*.38-.36*.36)],u=[.921,0,-.411],v=[n[1]*u[2],n[2]*u[0]-n[0]*u[2],-n[1]*u[0]],ring=[];
 for(let i=0;i<=100;i++){const a=i/100*TAU,co=Math.cos(a),si=Math.sin(a);ring.push([u[0]*co+v[0]*si,u[1]*co+v[1]*si,u[2]*co+v[2]*si]);}return {n,ring};})();

let active=null;
/** Starts the full-screen update scene in `host`. Returns {stop()}; a second start while one runs returns the same handle.
 * runup: seconds before the countdown (the meteorite leaves 6 s before it; a shorter runup joins the flight later).
 * scale: optional max pixel ratio (number) or (w,h)=>pixel ratio; default the canvas-budget.js budget. */
export function startUpdateScene({host=document.body,seconds=10,runup=6,reduced=false,planets=[],scale}={}){
 if(active)return active;
 seconds=Math.max(1,Number(seconds)||10);runup=Math.max(0,Number.isFinite(+runup)?+runup:6);
 if(!document.getElementById('update-scene-style'))document.head.append(Object.assign(document.createElement('style'),{id:'update-scene-style',textContent:STYLE}));
 const root=document.createElement('div');root.className='update-scene'+(reduced?' reduced':'');
 const canvas=document.createElement('canvas');canvas.setAttribute('aria-hidden','true');
 const count=document.createElement('div');count.className='update-scene-count';count.setAttribute('aria-hidden','true');
 const label=document.createElement('p');label.className='update-scene-label';label.setAttribute('role','status');label.setAttribute('aria-live','polite');
 const sub=document.createElement('p');sub.className='update-scene-sub';sub.textContent='De nieuwe versie wordt na de herstart actief.';
 root.append(canvas,count,label,sub);host.append(root);
 const g=canvas.getContext('2d');
 const stats=window.__updateSceneStats={frames:0,avg:0,max:0,total:0,scale:0,width:0,height:0,reduced:!!reduced,done:false};

 // The update planet itself is the meteorite: it is not drawn among the planets (no copy left behind).
 const updateDef=(planets||[]).find(p=>p&&(p.id==='update'||p.id==='updates'))||{hue:192,rock:true};
 const orbit=(planets||[]).filter(p=>p&&p.id!=='home'&&p!==updateDef);
 const glow=new Map(GLOWS.map(c=>[c,glowSprite(c,c==='#373377'||c==='#07596b'?256:128)]));
 const starX=new Float32Array(STARS.length*4),starL=new Uint8Array(STARS.length);
 const earthImg=new Image();let earthReady=false,F=null,B=buildBurst(7);
 let W=0,H=0,U=0,S=1,ex=0,ey=0,er0=0,sprites=[],meteorSprite=null,shade=null,resized=true,lightNow=isLight(),raf=0,stopped=false;

 function layout(){
  W=Math.max(1,innerWidth);H=Math.max(1,innerHeight);U=Math.min(W,H*16/9); // composition of the 16:9 preview, fits wide screens
  const light=lightNow||GFX==='licht',dpr=light?1:devicePixelRatio||1,budget=canvasScale(W,H,dpr,GFX==='soft',light);
  S=typeof scale==='function'?scale(W,H):Number.isFinite(scale)?Math.min(scale,budget):budget;
  S=Math.max(.25,Number(S)||1);
  canvas.width=Math.round(W*S);canvas.height=Math.round(H*S);
  ex=W*.5;ey=H*.5;er0=U*.145;
  root.style.setProperty('--x',ex+'px');root.style.setProperty('--y',ey+'px');root.style.setProperty('--u',U+'px');
  // Planet sprites at the pixel size they are drawn at (globe() caches them).
  sprites=orbit.map(p=>globe(p.hue,!!p.rock,Math.ceil(U*.075*(p.size||.6)*2.192*S)));
  meteorSprite=globe(updateDef.hue,!!updateDef.rock,Math.ceil(U*.022*2.192*S));
  // Vignette and footer shade do not move: gradients made once per size.
  const v=g.createRadialGradient(W*.5,H*.47,H*.22,W*.5,H*.47,U*.68);v.addColorStop(0,'#02040c00');v.addColorStop(.65,'#02040c10');v.addColorStop(1,'#02040cba');
  const f=g.createLinearGradient(0,H*.77,0,H);f.addColorStop(0,'#02040c00');f.addColorStop(.55,'#02040cdd');f.addColorStop(1,'#02040cf5');
  shade={v,f};
  if(earthReady)fracture();
  stats.scale=S;stats.width=canvas.width;stats.height=canvas.height;resized=false;
 }
 function fracture(){if(reduced)return;if(F)disposeFracture(F);F=buildFracture(earthImg,er0*S);}
 const onResize=()=>{resized=true;};addEventListener('resize',onResize);
 earthImg.onload=()=>{if(stopped)return;earthReady=true;if(!resized)fracture();};
 // Without earth.png the plain globe stands in (same disc size within a few percent).
 earthImg.onerror=()=>{if(stopped)return;earthImg.onerror=null;earthImg.src=globe(182,true,720).toDataURL();};
 earthImg.src=new URL('./earth.png',import.meta.url).href;

 const sprite=(color,x,y,r,a)=>{if(a<=0||r<=0)return;g.globalAlpha=a>1?1:a;g.drawImage(glow.get(color),x-r,y-r,r*2,r*2);};

 function stars(T){
  const travel=reduced?0:smooth(T/5)*.8,speed=!reduced&&T<5&&T>0?Math.sin(clamp(T/5)*Math.PI)*.7*.17:0,vx=W*.49,vy=H*.36;
  for(let i=0;i<STARS.length;i++){
   const s=STARS[i],z=.12+((s.z+1-travel%1)%1),k=.25/z,x=vx+s.c*W*.7*k,y=vy+s.s*H*.8*k,o=i*4;
   starX[o]=x;starX[o+1]=y;starX[o+2]=x+(x-vx)*speed;starX[o+3]=y+(y-vy)*speed;
   starL[i]=Math.min(STAR_LEVELS-1,Math.floor((Math.min(.85,.15+.13/z)-.25)/.6*STAR_LEVELS));
  }
  g.strokeStyle='#b5dcf9';g.lineCap='round'; // round caps: a star that stands still stays a dot
  for(let big=0;big<2;big++){g.lineWidth=big?1.7:.8;
   for(let l=0;l<STAR_LEVELS;l++){g.beginPath();let any=false;
    for(let i=0;i<STARS.length;i++){if(starL[i]!==l||STARS[i].big!==(big===1))continue;const o=i*4;g.moveTo(starX[o],starX[o+1]);g.lineTo(starX[o+2],starX[o+3]);any=true;}
    if(any){g.globalAlpha=.25+(l+.5)/STAR_LEVELS*.6;g.stroke();}
   }
  }
  g.lineCap='butt';g.globalAlpha=1;
 }
 function planetsAround(T,t,close){
  const pull=reduced?0:smooth((t-7)/2),angle=pull*2.4,ca=Math.cos(angle),sa=Math.sin(angle),dist=1-pull;
  const fade=reduced?1:(1-close)*(1-.3*smooth((T-IMPACT)/1.5));
  if(pull>0&&pull<1){ // light trails of the planets spiralling inwards
   g.fillStyle='#85ffe3';const d=U*.003;
   for(let j=12;j>0;j--){const q=Math.max(0,pull-j*.014),a=q*2.4,c=Math.cos(a)*(1-q),s=Math.sin(a)*(1-q);g.globalAlpha=(1-j/13)*.25;g.beginPath();
    for(const p of orbit){const dx=(p.x-50)/100*U*.94,dy=(p.y-52)/100*U*.5625*.82,px=ex+dx*c-dy*s,py=ey+dx*s+dy*c;g.moveTo(px+d,py);g.arc(px,py,d,0,TAU);}
    g.fill();}
  }
  g.globalAlpha=fade;
  for(let i=0;i<orbit.length;i++){
   const p=orbit[i],dx=(p.x-50)/100*U*.94,dy=(p.y-52)/100*U*.5625*.82,x=ex+(dx*ca-dy*sa)*dist,y=ey+(dx*sa+dy*ca)*dist,r=U*.075*(p.size||.6)*(.12+.88*dist);
   g.drawImage(sprites[i],x-r*1.096,y-r*1.096,r*2.192,r*2.192);
   if(p.rings){g.strokeStyle='rgba(170,225,240,.55)';g.lineWidth=2;g.beginPath();g.ellipse(x,y,r*1.5,r*.35,-.3,0,TAU);g.stroke();}
  }
  g.globalAlpha=1;
 }
 function earth(T,er){
  if(!reduced&&T>=BURST){drawBurst(g,B,ex,ey,er,T-BURST,W,H);if(F)drawDebris(g,F,ex,ey,er,T);g.globalAlpha=1;return;}
  if(earthReady)g.drawImage(earthImg,ex-er/.88,ey-er/.88,er*2/.88,er*2/.88);
  if(reduced||T<=IMPACT||!F)return;
  drawCracking(g,F,ex,ey,er,T-IMPACT);drawDebris(g,F,ex,ey,er,T);g.globalAlpha=1;
 }
 function meteor(T,er){
  const hitX=ex+er*.38,hitY=ey-er*.36,sx=W*.89,sy=H*.14,q=Math.pow(clamp(T/IMPACT),3),px=sx+(hitX-sx)*q,py=sy+(hitY-sy)*q;
  const rr=U*(.014+.008*q),a=1-smooth((T-IMPACT)/.18);
  if(a>0){
   const dx=sx-hitX,dy=sy-hitY,len=Math.hypot(dx,dy)||1,ux=dx/len,uy=dy/len,tail=U*(.025+.16*q);
   const fire=g.createLinearGradient(px+ux*tail,py+uy*tail,px,py);fire.addColorStop(0,'#ff8a2900');fire.addColorStop(.65,'#ff8a2970');fire.addColorStop(.94,'#ffd19c');fire.addColorStop(1,'#fff5dd');
   g.globalAlpha=a;g.strokeStyle=fire;g.lineCap='round';g.lineWidth=rr*1.5;g.beginPath();g.moveTo(px+ux*tail,py+uy*tail);g.lineTo(px,py);g.stroke();g.lineCap='butt';
   sprite('#ff872f',px,py,rr*4,a*.65);g.globalAlpha=a;g.drawImage(meteorSprite,px-rr*1.096,py-rr*1.096,rr*2.192,rr*2.192);
   sprite('#ffe3b5',px-ux*rr*.4,py-uy*rr*.4,rr*1.3,a*.8);
   g.fillStyle='#ffcb8c';
   for(const p of TRAIL){const z=(p.base+T*1.9)%1,spread=p.side*rr*z*1.8;g.globalAlpha=a*(1-z)*.7;g.beginPath();g.arc(px+ux*tail*z-uy*spread,py+uy*tail*z+ux*spread,Math.max(.5,rr*.12*(1-z)),0,TAU);g.fill();}
  }
  if(T>IMPACT){ // impact flash, surface ring, orbit-plane shock and a ring of dust
   const wave=clamp((T-IMPACT)/1.3);
   sprite('#ffc98c',hitX,hitY,er*(1+wave*3.5),(1-wave)*.95);
   g.save();g.beginPath();g.arc(ex,ey,er,0,TAU);g.clip();g.globalAlpha=(1-wave)*.9;g.strokeStyle='rgb(255,220,159)';g.lineWidth=2;g.beginPath();g.arc(hitX,hitY,Math.max(.1,er*wave*2),0,TAU);g.stroke();g.restore();
   g.globalAlpha=(1-wave)*.65;g.strokeStyle='rgb(150,246,246)';g.lineWidth=1.5;g.beginPath();g.ellipse(ex,ey,er*(1+wave*1.7),er*(.35+wave*.65),-.25,0,TAU);g.stroke();
   if(wave<1){g.globalAlpha=(1-wave)*.7;g.fillStyle='#ffd6a1';g.beginPath();for(const d of IMPACT_DOTS){const r=er*wave*d.f,x=hitX+d.cos*r,y=hitY+d.sin*r*.65;g.moveTo(x+1.1,y);g.arc(x,y,1.1,0,TAU);}g.fill();}
  }
  g.globalAlpha=1;
 }
 function aftermath(T,er){
  const age=T-IMPACT,hx=ex+er*.38,hy=ey-er*.36;
  if(T<9){ // shock wave over the globe and rising dust
   const angle=clamp(age/2.7)*Math.PI,ca=Math.cos(angle),sa=Math.sin(angle),n=SHOCK.n;
   g.globalAlpha=(1-smooth(age/3))*.7;g.strokeStyle='rgb(255,223,177)';g.lineWidth=2;g.beginPath();let pen=false;
   for(const p of SHOCK.ring){const pz=n[2]*ca+p[2]*sa;if(pz<=0){pen=false;continue;}const x=ex+(n[0]*ca+p[0]*sa)*er,y=ey+(n[1]*ca+p[1]*sa)*er;if(pen)g.lineTo(x,y);else{g.moveTo(x,y);pen=true;}}
   g.stroke();
   const fade=1-smooth(age/4.3),color=age<.6?'#ffb775':age<1.5?'#9b6450':'#4e4543',o=fade*(age<.6?.2:.12),spread=er*(.18+age*.3),rr=er*(.1+age*.15);
   for(const d of DUST)sprite(color,hx+d.cos*spread*d.f,hy+d.sin*spread-age*er*.06,rr*d.g,o);
  }
  if(T<8){ // sparks thrown out of the crater, falling back
   const fade=1-smooth(age/3.3),fall=er*.12*age*age;
   for(const s of SPARK_GROUPS){g.globalAlpha=fade*s.alpha;g.strokeStyle=s.color;g.lineWidth=s.width;g.beginPath();
    for(const p of s.list){const speed=er*p.speed,d=speed*age,x=hx+p.cos*d,y=hy+p.sin*d+fall;g.moveTo(x,y);g.lineTo(x-p.cos*speed*.05,y-p.sin*speed*.05);}g.stroke();}
  }
  g.globalAlpha=1;
 }
 function ring(t,er,close){
  if(!reduced&&t>0&&t<10){ // a calm pulse and particles drawn in towards the Earth
   const phase=t%1;g.globalAlpha=.17*(1-phase);g.strokeStyle='rgb(133,255,227)';g.lineWidth=1;g.beginPath();g.ellipse(ex,ey,er*(1+phase*.45),er*(.38+phase*.17),-.18,0,TAU);g.stroke();
   g.fillStyle='#9ef9e7';const spin=t*(t>7?.28:.07),turn=t*.12;
   for(const p of SPIRAL){const q=(p.base+spin)%1,a=p.a+turn,rr=er*(1.12+(1-q)*1.5);g.globalAlpha=Math.sin(q*Math.PI)*.65;g.beginPath();g.arc(ex+Math.cos(a)*rr,ey+Math.sin(a)*rr*.64,p.size,0,TAU);g.fill();}
  }
  const o=(reduced?1:smooth(t/.7))*(1-close),rr=er*.76;if(o<=0){g.globalAlpha=1;return;}
  g.globalAlpha=o;g.lineWidth=2;g.strokeStyle='#a8e7e52a';g.beginPath();g.arc(ex,ey,rr,0,TAU);g.stroke();
  const left=clamp(1-t/10);if(left>0){g.strokeStyle='#a9e6de';g.beginPath();g.arc(ex,ey,rr,-Math.PI/2,-Math.PI/2+TAU*left);g.stroke();}
  g.globalAlpha=1;
 }

 // DOM text, only touched when it changes. The label is the spoken status; the big digits are decoration.
 let shownLabel='',shownCount='',phase='';
 function text(T){
  const t=T-COUNT;let l,c='',p='';
  if(t<0)l='Herstart wordt voorbereid';
  else if(t<seconds){const n=Math.ceil(seconds-t);l=`Opnieuw opstarten over ${n} ${n===1?'seconde':'seconden'}`;c=String(n);p='counting';}
  else{l='Opnieuw opstarten…';c='0';p='done';}
  if(l!==shownLabel)label.textContent=shownLabel=l;
  if(c!==shownCount)count.textContent=shownCount=c;
  if(p!==phase){root.classList.toggle('counting',p==='counting');root.classList.toggle('done',p==='done');phase=p;}
 }

 const t0=performance.now()-(COUNT-runup)*1000; // T=COUNT exactly `runup` seconds from now
 function frame(now){
  raf=0;if(stopped)return;
  const start=performance.now();
  if(isLight()!==lightNow){lightNow=isLight();resized=true;} // only the pixel budget changes, never the picture
  if(resized)layout();
  const T=(Math.max(now,t0)-t0)/1000;text(T);
  // The picture follows the 10-second rhythm of the approved preview; another countdown length is stretched to fit.
  const V=T<=COUNT?T:COUNT+(T-COUNT)*10/seconds,t=V-COUNT,close=reduced?0:ease(clamp((t-10)/CLOSE)),er=er0*(1+close*1.8);
  g.setTransform(S,0,0,S,0,0);g.globalAlpha=1;g.fillStyle='#02040c';g.fillRect(0,0,W,H);
  sprite('#373377',W*.62,H*.3,U*.42,.34);sprite('#07596b',W*.3,H*.46,U*.32,.27);
  stars(V);
  planetsAround(V,t,close);
  if(t<0)earth(V,er);
  if(!reduced&&V<COUNT)meteor(V,er);
  if(!reduced&&V>IMPACT&&V<9)aftermath(V,er);
  if(t>=0){earth(V,er);ring(t,er,close);}
  if(close>0)drawClose(g,ex,ey,er,clamp((t-10)/CLOSE),W,H);
  g.setTransform(S,0,0,S,0,0);g.globalAlpha=1;g.fillStyle=shade.v;g.fillRect(0,0,W,H);g.fillStyle=shade.f;g.fillRect(0,H*.77,W,H*.23);
  const ms=performance.now()-start;stats.frames++;stats.total+=ms;stats.avg=stats.total/stats.frames;if(ms>stats.max)stats.max=ms;
  // After the implosion (or at zero with reduced motion) the picture stands still until the shell takes over.
  if(V<(reduced?ZERO+.5:END)||!earthReady)raf=requestAnimationFrame(frame);else stats.done=true;
 }
 raf=requestAnimationFrame(frame);
 active={stop(){
  if(stopped)return;stopped=true;if(raf)cancelAnimationFrame(raf);raf=0;removeEventListener('resize',onResize);
  if(F)disposeFracture(F);F=B=null;earthImg.onload=earthImg.onerror=null;earthImg.removeAttribute('src');
  for(const c of [...glow.values(),...sprites,meteorSprite,canvas])if(c)c.width=c.height=0;
  glow.clear();sprites=[];meteorSprite=null;root.remove();active=null;
 }};
 return active;
}
