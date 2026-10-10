// Planet globes, drawn like Space Chat's 2D universe (src/universe.js, globe()): a lit radial gradient,
// gas bands or rocky blotches, a soft terminator shadow and a thin coloured rim. Works without a GPU.
const bitmaps=new Map();
function remember(key,canvas){
 let pixels=canvas.width*canvas.height;
 for(const image of bitmaps.values())pixels+=image.width*image.height;
 while(bitmaps.size&&(bitmaps.size>=32||pixels>8_000_000)){
  const oldest=bitmaps.keys().next().value,image=bitmaps.get(oldest);
  pixels-=image.width*image.height;bitmaps.delete(oldest);
 }
 bitmaps.set(key,canvas);
}
function copy(canvas,className=''){
 const result=document.createElement('canvas');result.width=canvas.width;result.height=canvas.height;
 result.className=className;result.setAttribute('aria-hidden','true');result.getContext('2d').drawImage(canvas,0,0);return result;
}
export const pixelSize=css=>Math.max(32,Math.min(1280,Math.ceil(css*Math.min(devicePixelRatio||1,2))));
export function globe(seed,rock=false,size=320){
 size=Math.max(32,Math.min(1280,Math.ceil(size)));
 const key=`globe:${seed}:${rock}:${size}`;
 if(bitmaps.has(key))return copy(bitmaps.get(key),'space-globe');
 const canvas=document.createElement('canvas');canvas.className='space-globe';canvas.width=canvas.height=size;canvas.setAttribute('aria-hidden','true');
 const c=canvas.getContext('2d');c.scale(size/320,size/320);
 const hue=((seed%360)+360)%360;
 const gradient=c.createRadialGradient(112,92,9,180,168,161);
 gradient.addColorStop(0,`hsl(${hue} 62% 75%)`);gradient.addColorStop(.42,`hsl(${hue} 49% 42%)`);gradient.addColorStop(.76,`hsl(${hue} 58% 18%)`);gradient.addColorStop(1,'#030714');
 c.save();c.beginPath();c.arc(160,160,146,0,Math.PI*2);c.clip();c.fillStyle=gradient;c.fillRect(0,0,320,320);
 let s=(seed*7919+13)>>>0||31;const rand=()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296;};
 if(rock){for(let i=0;i<40;i++){const x=rand()*320,y=rand()*320;c.fillStyle=i%2?'#061f4544':'#c7fce72a';c.beginPath();for(let n=0;n<10;n++){const a=n/10*Math.PI*2,r=12+rand()*40;const px=x+Math.cos(a)*r,py=y+Math.sin(a)*r;n?c.lineTo(px,py):c.moveTo(px,py);}c.closePath();c.fill();}}
 else for(let i=0;i<26;i++){c.beginPath();c.ellipse(155,-65+i*20,250,19+rand()*12,-.34,0,Math.PI*2);c.lineWidth=5+rand()*12;c.strokeStyle=i%2?'#e4eaff15':'#03071922';c.stroke();}
 const shadow=c.createLinearGradient(45,30,290,235);shadow.addColorStop(0,'#ffffff2a');shadow.addColorStop(.4,'#00000000');shadow.addColorStop(1,'#010312e8');
 c.fillStyle=shadow;c.fillRect(0,0,320,320);c.restore();
 c.beginPath();c.arc(160,160,146,0,Math.PI*2);c.strokeStyle=`hsla(${hue} 80% 85% / .35)`;c.lineWidth=1.5;c.stroke();
 remember(key,canvas);return copy(canvas,'space-globe');
}
/** Starfield canvas like the app's .space-stars (seeded, so it looks the same on every start). */
export function starfield(w=1600,h=1000,count=520){
 const key=`stars:${w}:${h}:${count}`;
 if(bitmaps.has(key))return copy(bitmaps.get(key));
 const canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;const c=canvas.getContext('2d');let s=7;
 for(let i=0;i<count;i++){s=(s*16807)%2147483647;const x=s%w;s=(s*16807)%2147483647;const y=s%h;c.fillStyle=`rgba(208,224,255,${.12+(i%8)/12})`;c.beginPath();c.arc(x,y,i%19===0?1.5:.65,0,7);c.fill();}
 remember(key,canvas);return copy(canvas);
}

// The home world as a real-looking Earth (concept 10 Oct): oceans, continents, ice caps, clouds, city lights on the
// night side and a thin blue atmosphere. Drawn once per pixel on the CPU (no GPU, no image files) and cached.
// Internal resolution is capped at 720 px; CSS scales it up, which keeps the first start fast on weak hardware.
function noise3(seed){
 const hash=(x,y,z)=>{let n=(Math.imul(x,374761393)+Math.imul(y,668265263)+Math.imul(z,1274126177)+seed)|0;
  n=Math.imul(n^(n>>>13),1274126177);return ((n^(n>>>16))>>>0)/4294967296;};
 const smooth=t=>t*t*(3-2*t),mix=(a,b,t)=>a+(b-a)*t;
 const noise=(x,y,z)=>{
  const xi=Math.floor(x),yi=Math.floor(y),zi=Math.floor(z),u=smooth(x-xi),v=smooth(y-yi),w=smooth(z-zi);
  return mix(mix(mix(hash(xi,yi,zi),hash(xi+1,yi,zi),u),mix(hash(xi,yi+1,zi),hash(xi+1,yi+1,zi),u),v),
   mix(mix(hash(xi,yi,zi+1),hash(xi+1,yi,zi+1),u),mix(hash(xi,yi+1,zi+1),hash(xi+1,yi+1,zi+1),u),v),w);
 };
 return (x,y,z,octaves)=>{let sum=0,amp=.5,norm=0;for(let i=0;i<octaves;i++){sum+=noise(x,y,z)*amp;norm+=amp;x*=2.03;y*=2.03;z*=2.03;amp*=.5;}return sum/norm;};
}
function* earthRows(px,d){
 const land=noise3(1013),cloud=noise3(7717),city=noise3(4243);
 const R=px*.44,cx=px/2,cy=px/2,glow=1.13;
 const L=[-.83,-.36,.43],tilt=.41,ct=Math.cos(tilt),st=Math.sin(tilt),lon=2.1,cl=Math.cos(lon),sl=Math.sin(lon);
 const clamp=v=>v<0?0:v>1?1:v,ss=(a,b,v)=>{const t=clamp((v-a)/(b-a));return t*t*(3-2*t);};
 for(let y=0;y<px;y++){
  for(let x=0;x<px;x++){
   const dx=(x+.5-cx)/R,dy=(y+.5-cy)/R,r=Math.sqrt(dx*dx+dy*dy),i=(y*px+x)*4;
   if(r>glow)continue;
   if(r>1){ // Atmosphere halo outside the disk, brighter on the lit side.
    const lit=.35+.65*clamp(-(dx*L[0]+dy*L[1])/r*.8+.4),a=Math.pow(1-(r-1)/(glow-1),2.2)*.55*lit;
    d[i]=110;d[i+1]=175;d[i+2]=255;d[i+3]=a*255;continue;
   }
   const nz=Math.sqrt(1-r*r);
   // Rotate the surface: longitude around the vertical axis, then the axial tilt.
   const ax=dx*cl+nz*sl,az=-dx*sl+nz*cl,bx=ax*ct-dy*st,by=ax*st+dy*ct,bz=az;
   const e=land(bx*1.7+5,by*1.7+5,bz*1.7+5,4),polar=Math.abs(by),isLand=e>.53;
   let R0,G0,B0;
   if(isLand){
    const h=ss(.53,.72,e),dry=ss(.5,.7,land(bx*3+21,by*3,bz*3,2))*ss(.55,.2,polar);
    R0=46+h*70+dry*85;G0=86+h*30+dry*35;B0=38+h*20+dry*25; // forest to mountains, deserts near the equator
   }else{const sh=ss(.38,.53,e);R0=8+sh*20;G0=32+sh*60;B0=82+sh*80;}
   const ice=ss(.8,.9,polar+(cloud(bx*7,by*7,bz*7,2)-.5)*.3+(isLand?.04:0));
   R0+=(228-R0)*ice;G0+=(236-G0)*ice;B0+=(246-B0)*ice;
   const lam=dx*L[0]+dy*L[1]+nz*L[2],day=ss(-.15,.3,lam);
   let Rc=R0*(.04+.96*day),Gc=G0*(.04+.96*day),Bc=B0*(.04+.96*day);
   if(!isLand){const spec=Math.pow(clamp(2*lam*nz-L[2]),38)*.55*day*(1-ice);Rc+=spec*255;Gc+=spec*240;Bc+=spec*220;}
   if(isLand&&ice<.5&&day<.6){ // City lights on the night side: fine points, clustered around populated regions.
    const area=city(bx*5,by*5,bz*5,2),spark=city(bx*70+50,by*70,bz*70,1);
    const k=ss(.45,.65,area)*ss(.62,.8,spark)*(1-day/.6)*1.6;
    Rc+=255*k;Gc+=175*k;Bc+=80*k;
   }
   const cv=ss(.52,.72,cloud(bx*2.6+9,by*5+9,bz*2.6+9,3))*.88,cb=34+215*day;
   Rc=Rc*(1-cv)+cb*cv;Gc=Gc*(1-cv)+cb*cv;Bc=Bc*(1-cv)+(cb+10*day)*cv;
   const rim=Math.pow(1-nz,2.5)*(.25+.6*day); // atmosphere seen through the limb
   Rc=Rc*(1-rim)+90*rim;Gc=Gc*(1-rim)+160*rim;Bc=Bc*(1-rim)+255*rim;
   d[i]=Rc;d[i+1]=Gc;d[i+2]=Bc;d[i+3]=clamp((1-r)*R+.5)*255;
  }
  yield y;
 }
}
/** Earth canvas. The plain globe shows at once; the Earth is painted later (see paintEarths) in short slices that
 * follow the display refresh, so the world never waits for it (VM 10 Oct: a setTimeout chain kept WebKit from painting
 * and the world only appeared after 186 s). Internal size is capped at 320 px; CSS scales it up. */
const earthQueue=[];let earthStarted=false,earthBusy=false;
export function earth(size=320){
 const px=Math.min(320,Math.max(32,Math.ceil(size))),key=`earth:${px}`;
 if(bitmaps.has(key))return copy(bitmaps.get(key),'space-globe earth');
 const shown=globe(208,false,px);shown.classList.add('earth');
 earthQueue.push({px,key,shown});if(earthStarted)paintNext();
 return shown;
}
/** Starts painting queued Earths; call once the page is ready. */
export function paintEarths(){earthStarted=true;paintNext();}
function paintNext(){
 if(earthBusy)return;
 const job=earthQueue.shift();if(!job)return;
 const done=()=>{const g=job.shown.getContext('2d');g.clearRect(0,0,job.px,job.px);g.drawImage(bitmaps.get(job.key),0,0);earthBusy=false;paintNext();};
 if(bitmaps.has(job.key)){done();return;}
 earthBusy=true;
 const canvas=document.createElement('canvas');canvas.width=canvas.height=job.px;
 const c=canvas.getContext('2d'),image=c.createImageData(job.px,job.px),rows=earthRows(job.px,image.data);
 const slice=()=>{
  const end=performance.now()+6;
  while(performance.now()<end)if(rows.next().done){c.putImageData(image,0,0);remember(job.key,canvas);done();return;}
  requestAnimationFrame(slice);
 };
 requestAnimationFrame(slice);
}
