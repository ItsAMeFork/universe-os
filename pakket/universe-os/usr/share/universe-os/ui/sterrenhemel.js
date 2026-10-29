// 0.2.38 De sterrenhemel van de wereld en het inlogscherm (Jesse: 'maak de space nog beter dus nog mooier en echter').
// Eén tekenpad met een kwaliteitsparameter (Jesse: 'de lichte modus moet het zelfde zijn maar dan lichter dus minder
// kwaliteit'): de lichte modus tekent dezelfde hemel met dezelfde beweging, alleen met minder sterren, een nevel op
// lagere resolutie en minder twinkelbeelden per seconde. Geen CSS-filters of vervaging, alles plain 2D canvas.
//  - sterren in drie dieptelagen (parallax als de camera schuift of zoomt), met kleur naar temperatuur
//    (blauwwit, wit, geel, oranje) en veel zwakke, weinig heldere sterren, zoals echt;
//  - de helderste sterren twinkelen (eigen klein canvas, eigen klok) en hebben een zachte gloed met kruisje;
//  - een melkwegband met gekleurde nevels en donkere stofbanen, eenmaal gemaakt en daarna alleen verschoven;
//  - warp: bij inloggen/uitloggen/opstarten rekken de sterren uit tot lichtstrepen (snelheid van de camera).
const alpha=v=>Math.max(0,Math.min(1,v)).toFixed(3); // same as globe.js (no import: works without the page)

export const FOV=900;
export const KWALITEIT={
 vol:{elke:1,nevel:[1024,512],twinkel:90,fps:24,gloed:true},
 licht:{elke:3,nevel:[384,192],twinkel:30,fps:8,gloed:false},
};
export const kwaliteit=licht=>KWALITEIT[licht?'licht':'vol'];

// Temperatuurkleuren (RGB) en hoe vaak ze voorkomen.
export const KLEUREN=[[170,195,255],[210,224,255],[255,250,240],[255,226,170],[255,190,140]];
const KANS=[.12,.38,.28,.14,.08];
function rnd(seed){return ()=>(seed=(seed*16807)%2147483647)/2147483647;}
/** All stars: [x,y,z on the unit sphere, brightness .15..1, colour index, layer 0..2]. Fixed seed: always the same sky. */
export const STERREN=(()=>{
 const r=rnd(20251025),out=[];
 for(let i=0;i<9000;i++){
  const u=r()*2-1,t=r()*Math.PI*2,q=Math.sqrt(1-u*u);
  const b=.15+.85*Math.pow(r(),3.2); // power law: many faint stars, few bright ones
  let k=r(),ci=0;while(ci<KANS.length-1&&k>KANS[ci]){k-=KANS[ci];ci++;}
  out.push([q*Math.cos(t),u,q*Math.sin(t),b,ci,i%3]);
 }
 return out;
})();
/** The stars a quality draws: the light version takes every n-th star (same sky, fewer stars). */
const cache=new Map();
const memo=(key,make)=>{if(!cache.has(key))cache.set(key,make());return cache.get(key);};
export const sterrenVoor=licht=>memo('s'+licht,()=>STERREN.filter((_,i)=>i%kwaliteit(licht).elke===0));
export const helderste=(licht,n=kwaliteit(licht).twinkel)=>memo('h'+licht+n,()=>sterrenVoor(licht).slice().sort((a,b)=>b[3]-a[3]).slice(0,n));
const helderSet=licht=>memo('hs'+licht,()=>new Set(helderste(licht)));

/** Screen position of a star (or null) for camera cam; parallax per layer when the camera moves or zooms. */
export function sterPunt(s,cam,w,h){
 const cy=Math.cos(cam.yaw),sy=Math.sin(cam.yaw),cp=Math.cos(cam.pitch),sp=Math.sin(cam.pitch);
 const [x,y,z,,,laag]=s;
 const x1=x*cy-z*sy,z1=x*sy+z*cy,y2=y*cp-z1*sp,z2=y*sp+z1*cp;if(z2<=.05)return null;
 const k=[0,.004,.011][laag],zoom=1+[0,.02,.06][laag]*(1650-(cam.dist||1650))/1650;
 const ox=-((cam.tx||0)*cy-(cam.tz||0)*sy)*k,oy=-(cam.ty||0)*k;
 return {x:w/2+(x1/z2*FOV)*zoom+ox,y:h/2+(y2/z2*FOV)*zoom+oy};
}

const sprites=new Map();
/** Soft glow sprite of a bright star (with a faint diffraction cross in the full version). */
export function sterSprite(ci,gloed){
 const key=ci+':'+gloed;if(sprites.has(key))return sprites.get(key);
 const S=gloed?32:12,cv=typeof OffscreenCanvas!=='undefined'?new OffscreenCanvas(S,S):Object.assign(document.createElement('canvas'),{width:S,height:S});
 const c=cv.getContext('2d'),[R,G,B]=KLEUREN[ci],m=S/2;
 const g=c.createRadialGradient(m,m,0,m,m,m);g.addColorStop(0,'rgba(255,255,255,1)');g.addColorStop(.18,`rgba(${R},${G},${B},.9)`);g.addColorStop(.45,`rgba(${R},${G},${B},.22)`);g.addColorStop(1,`rgba(${R},${G},${B},0)`);
 c.fillStyle=g;c.fillRect(0,0,S,S);
 if(gloed){c.strokeStyle=`rgba(${R},${G},${B},.35)`;c.lineWidth=1;c.beginPath();c.moveTo(m,1);c.lineTo(m,S-1);c.moveTo(1,m);c.lineTo(S-1,m);c.stroke();}
 sprites.set(key,cv);return cv;
}

const nevels=new Map();
/** The Milky Way band with coloured nebulae and dark dust, as a panorama (made once per quality). */
export function nevelTextuur(licht){
 const key=licht?'l':'v';if(nevels.has(key))return nevels.get(key);
 const [TW,TH]=kwaliteit(licht).nevel,r=rnd(777);
 const cv=typeof OffscreenCanvas!=='undefined'?new OffscreenCanvas(TW,TH):Object.assign(document.createElement('canvas'),{width:TW,height:TH});
 const c=cv.getContext('2d');
 const band=x=>TH*.5+Math.sin(x/TW*Math.PI*2)*TH*.16;
 const blob=(x,y,rad,col,a)=>{for(const dx of [-TW,0,TW]){const g=c.createRadialGradient(x+dx,y,0,x+dx,y,rad);g.addColorStop(0,`rgba(${col},${a})`);g.addColorStop(1,`rgba(${col},0)`);c.fillStyle=g;c.fillRect(x+dx-rad,y-rad,rad*2,rad*2);}};
 // the band: many soft clouds of starlight (same seed = same clouds in both qualities, only the resolution differs)
 for(let i=0;i<320;i++){const x=r()*TW,y=band(x)+(r()-.5)*TH*.14;blob(x,y,TH*(.03+r()*.08),r()<.6?'170,190,255':r()<.5?'255,225,195':'200,170,255',.03+r()*.035);}
 // coloured emission nebulae (red/magenta hydrogen, teal oxygen, violet)
 const kleur=['255,90,140','120,90,255','80,220,210','255,140,90'];
 for(let i=0;i<30;i++){const x=r()*TW,y=band(x)+(r()-.5)*TH*.3;blob(x,y,TH*(.05+r()*.12),kleur[i%4],.05+r()*.08);}
 // dark dust lanes along the band
 c.globalCompositeOperation='destination-out';
 for(let i=0;i<160;i++){const x=r()*TW,y=band(x)+(r()-.5)*TH*.04;blob(x,y,TH*(.01+r()*.025),'0,0,0',.12+r()*.16);}
 c.globalCompositeOperation='source-over';
 nevels.set(key,cv);return cv;
}
/** Draws the nebula panorama, turning with the camera (yaw shifts it sideways, pitch up/down). */
export function tekenNevel(c,cam,w,h,licht,sterkte=1){
 const tex=nevelTextuur(licht),SW=w*2.6,SH=h*1.8;
 const x0=-(((cam.yaw%(2*Math.PI))+2*Math.PI)%(2*Math.PI))/(2*Math.PI)*SW,y0=(h-SH)/2+Math.sin(cam.pitch-.42)*h*.6;
 c.globalAlpha=Math.max(0,Math.min(1,sterkte));
 for(let x=x0;x<w;x+=SW)c.drawImage(tex,x,y0,SW,SH);
 c.globalAlpha=1;
}
/** Draws the stars. warp (0..1) stretches them into light streaks away from the middle (login/logout/start). The
 *  brightest stars are left to the twinkle layer when `zonderHelder` is set. */
export function tekenSterren(c,cam,w,h,{licht=false,warp=0,zonderHelder=false}={}){
 const lijst=sterrenVoor(licht),helder=zonderHelder?helderSet(licht):null;
 const groepen=new Map();
 for(const s of lijst){
  if(helder&&helder.has(s))continue;
  const p=sterPunt(s,cam,w,h);if(!p||p.x<-40||p.y<-40||p.x>w+40||p.y>h+40)continue;
  const key=s[4]*10+Math.min(9,Math.floor(s[3]*10));
  let g=groepen.get(key);if(!g){g=[];groepen.set(key,g);}g.push([p,s]);
 }
 c.lineCap='round';
 for(const [key,g] of groepen){
  const [R,G,B]=KLEUREN[Math.floor(key/10)],b=(key%10+.5)/10;
  if(warp>.02){
   c.strokeStyle=`rgba(${R},${G},${B},${alpha(b*(.6+.4*warp))})`;c.lineWidth=.6+b*1.4;c.beginPath();
   for(const [p,s] of g){const dx=p.x-w/2,dy=p.y-h/2,l=warp*.35*(1+s[5]*.6);c.moveTo(p.x,p.y);c.lineTo(p.x+dx*l,p.y+dy*l);}
   c.stroke();
  }else{
   c.fillStyle=`rgba(${R},${G},${B},${alpha(b)})`;c.beginPath();
   for(const [p,s] of g){const r=.45+s[3]*1.1+(s[5]===2?.2:0);c.moveTo(p.x+r,p.y);c.arc(p.x,p.y,r,0,7);}
   c.fill();
  }
 }
}
/** Twinkle factor of star i at time t (s): slow, irregular, never fully dark. */
export const twinkel=(i,t)=>.62+.38*(.6*Math.sin(t*(1.3+(i%7)*.37)+i)+.4*Math.sin(t*(3.1+(i%5)*.53)+i*2.3));
/** The brightest stars on their own small canvas, twinkling at kwaliteit.fps (8 in the light version). */
export function twinkelLaag(canvas,getCam,{licht=false,scale=()=>1,actief=()=>true}={}){
 const q=kwaliteit(licht),lijst=helderste(licht);let timer=0,warp=0;
 function draw(t=performance.now()/1000){
  const w=innerWidth,h=innerHeight,dpr=scale(w,h);
  if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
  const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);
  const cam=getCam();
  lijst.forEach((s,i)=>{
   const p=sterPunt(s,cam,w,h);if(!p)return;
   const f=warp>.02?1:twinkel(i,t),size=(q.gloed?9:5)+s[3]*(q.gloed?12:6);
   c.globalAlpha=Math.min(1,s[3]*f*1.15);
   if(warp>.02){const [R,G,B]=KLEUREN[s[4]],dx=p.x-w/2,dy=p.y-h/2,l=warp*.45;c.strokeStyle=`rgb(${R},${G},${B})`;c.lineWidth=1.6;c.beginPath();c.moveTo(p.x,p.y);c.lineTo(p.x+dx*l,p.y+dy*l);c.stroke();}
   else c.drawImage(sterSprite(s[4],q.gloed),p.x-size/2,p.y-size/2,size,size);
  });
  c.globalAlpha=1;
 }
 function tick(){timer=setTimeout(tick,1000/q.fps);if(!document.hidden&&actief())draw();}
 return {draw,start(){if(!timer)tick();},stop(){clearTimeout(timer);timer=0;},setWarp(v){warp=v;},fps:q.fps,aantal:lijst.length};
}
