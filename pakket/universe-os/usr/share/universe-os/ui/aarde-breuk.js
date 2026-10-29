// The Earth's crust breaking up during the update countdown (UOS-ANIM-001, approved preview of 27 Oct).
// Times are seconds: age = T-4.7 since the meteorite hit, T since the update planet left (15 = crust bursts).
//  buildFracture: once. An irregular fracture network (Voronoi cells around seeded points, denser near the impact)
//                 whose borders are jagged polylines shared by both neighbouring plates; per plate its centroid
//                 (r = 1), release time, Path2D and a sprite of the real Earth texture plus a scorched sprite.
//  drawCracking:  glowing core, intact plates (one clip, so no seams), scorching, growing cracks, crater, glow.
//  drawDebris:    released plates drift off, tumble and char; the same formula carries them through the burst
//                 (T 15+) and the inward collapse, so the explosion continues with the very same fragments.
// A plate only comes loose when every crack around it is complete. Geometry never depends on the pixel size, so
// the light version (smaller pxRadius) shows exactly the same animation with fewer pixels.

const TAU=Math.PI*2,IMPACT_X=.38,IMPACT_Y=-.36,EDGE=1.0006; // impact point on the visible face; disk polygon radius
const clamp=x=>Math.max(0,Math.min(1,x)),smooth=x=>{x=clamp(x);return x*x*(3-2*x);};
const rand=seed=>()=>{seed=(Math.imul(seed,1664525)+1013904223)|0;return (seed>>>0)/4294967296;};

// Seeded points in the unit disk: small plates near the impact, large ones on the far side.
function seeds(){
 const rnd=rand(4711),pts=[];
 for(let tries=0;tries<6000&&pts.length<90;tries++){
  const a=rnd()*TAU,d=Math.sqrt(rnd())*1.04,x=Math.cos(a)*d,y=Math.sin(a)*d;
  const gap=.12+.13*Math.min(1,Math.hypot(x-IMPACT_X,y-IMPACT_Y)/1.5);
  let ok=true;for(const p of pts)if(Math.hypot(p[0]-x,p[1]-y)<gap){ok=false;break;}
  if(ok)pts.push([x,y]);
 }
 return pts;
}
// Voronoi cell of seed i: the disk polygon clipped by the bisector with every other seed. Each polygon edge keeps a
// tag: the neighbouring seed it borders, or -1 for the limb of the Earth.
function cell(i,pts){
 let P=[],T=[];
 for(let k=0;k<96;k++){const a=k/96*TAU;P.push([Math.cos(a)*EDGE,Math.sin(a)*EDGE]);T.push(-1);}
 const [sx,sy]=pts[i];
 for(let j=0;j<pts.length;j++){
  if(j===i)continue;
  const nx=pts[j][0]-sx,ny=pts[j][1]-sy,c=(nx*(pts[j][0]+sx)+ny*(pts[j][1]+sy))/2,f=p=>p[0]*nx+p[1]*ny-c;
  const Q=[],U=[];
  for(let k=0;k<P.length;k++){
   const A=P[k],B=P[(k+1)%P.length],da=f(A),db=f(B),cut=()=>{const t=da/(da-db);return [A[0]+(B[0]-A[0])*t,A[1]+(B[1]-A[1])*t];};
   if(da<=0){Q.push(A);U.push(T[k]);if(db>0){Q.push(cut());U.push(j);}}
   else if(db<=0){Q.push(cut());U.push(T[k]);}
  }
  P=Q;T=U;if(P.length<3)return null;
 }
 return {P,T};
}
// A crack between two shared vertices: midpoint displacement, seeded per edge, so both plates get the same line.
function jagged(a,b,seed){
 const rnd=rand(seed*7919+17);let line=[a,b];
 while(Math.hypot(line[1][0]-line[0][0],line[1][1]-line[0][1])>.035&&line.length<33){
  const next=[line[0]];
  for(let k=1;k<line.length;k++){
   const p=line[k-1],q=line[k],dx=q[0]-p[0],dy=q[1]-p[1],o=(rnd()-.5)*.5;
   let mx=(p[0]+q[0])/2-dy*o,my=(p[1]+q[1])/2+dx*o;const d=Math.hypot(mx,my);
   if(d>EDGE){mx*=EDGE/d;my*=EDGE/d;}
   next.push([mx,my],q);
  }
  line=next;
 }
 return line;
}
const tracePath=(path,pts,ox=0,oy=0,s=1)=>{
 path.moveTo((pts[0]-ox)*s,(pts[1]-oy)*s);for(let k=2;k<pts.length;k+=2)path.lineTo((pts[k]-ox)*s,(pts[k+1]-oy)*s);path.closePath();
};

export function buildFracture(earthImg,pxRadius){
 const pts=seeds(),verts=[],vertex=(x,y)=>{
  for(let k=0;k<verts.length;k++)if(Math.abs(verts[k].x-x)<1e-7&&Math.abs(verts[k].y-y)<1e-7)return k;
  verts.push({x,y,hit:0});return verts.length-1;
 };
 const cells=pts.map((_,i)=>cell(i,pts)),edges=new Map(),plates=[];
 for(let i=0;i<cells.length;i++){
  const c=cells[i];if(!c)continue;
  c.V=c.P.map(p=>vertex(p[0],p[1]));
  for(let k=0;k<c.V.length;k++){
   const j=c.T[k];if(j<0)continue;
   const key=Math.min(i,j)*1000+Math.max(i,j);
   if(!edges.has(key)){const a=c.V[k],b=c.V[(k+1)%c.V.length];edges.set(key,{a,b,line:jagged([verts[a].x,verts[a].y],[verts[b].x,verts[b].y],key),cells:[i,j]});}
  }
 }
 // The fracture wave: every vertex cracks open later the farther it is from the impact (same rhythm as the preview).
 let far=0;for(const e of edges.values())for(const k of [e.a,e.b])far=Math.max(far,Math.hypot(verts[k].x-IMPACT_X,verts[k].y-IMPACT_Y));
 for(const v of verts)v.hit=.22+Math.hypot(v.x-IMPACT_X,v.y-IMPACT_Y)/far*7.5;
 for(const e of edges.values()){
  const ha=verts[e.a].hit,hb=verts[e.b].hit;
  e.t0=Math.min(ha,hb);e.dur=Math.max(.25,Math.abs(ha-hb));e.done=e.t0+e.dur;e.fromA=ha<=hb;e.last=Math.max(ha,hb);
 }
 const byCell=new Map();
 for(let i=0;i<cells.length;i++){
  const c=cells[i];if(!c)continue;
  const out=[];let done=0;
  for(let k=0;k<c.V.length;k++){
   const j=c.T[k];
   if(j<0){out.push(verts[c.V[k]].x,verts[c.V[k]].y);continue;}
   const e=edges.get(Math.min(i,j)*1000+Math.max(i,j)),forward=e.a===c.V[k],line=e.line;
   for(let n=0;n<line.length-1;n++){const p=line[forward?n:line.length-1-n];out.push(p[0],p[1]);}
   done=Math.max(done,e.done);
  }
  // Area centroid, bounding box (unit radius) and release: all cracks around the plate are closed by then. Every
  // plate is loose before the burst at T 15, so no intact crust ever appears in the explosion.
  let A=0,cx=0,cy=0,x0=9,y0=9,x1=-9,y1=-9;
  for(let k=0;k<out.length;k+=2){
   const x=out[k],y=out[k+1],nx=out[(k+2)%out.length],ny=out[(k+3)%out.length],w=x*ny-nx*y;
   A+=w;cx+=(x+nx)*w;cy+=(y+ny)*w;x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);
  }
  const px=cx/(3*A),py=cy/(3*A),pts=new Float32Array(out),path=new Path2D(),norm=Math.hypot(px,py)||1;
  tracePath(path,pts,px,py);
  const plate={px,py,pts,path,release:Math.min(done+.28,10.2),x0,y0,x1,y1,
   dirX:px/norm,dirY:py/norm,spin:Math.sin(px*33+py*13)*.21,sx:0,sy:0,sw:0,sh:0,ux:0,uy:0,uw:0,uh:0};
  plates.push(plate);byCell.set(i,plate);
 }
 // Cracks stay on screen until both plates beside them are gone; per crack a cumulative length for growing.
 const cracks=[];
 for(const e of edges.values()){
  const line=e.fromA?e.line:e.line.slice().reverse(),xy=new Float32Array(line.length*2),cum=new Float32Array(line.length);
  for(let n=0;n<line.length;n++){xy[n*2]=line[n][0];xy[n*2+1]=line[n][1];if(n)cum[n]=cum[n-1]+Math.hypot(line[n][0]-line[n-1][0],line[n][1]-line[n-1][1]);}
  const a=byCell.get(e.cells[0]),b=byCell.get(e.cells[1]);
  cracks.push({xy,cum,t0:e.t0,dur:e.dur,last:e.last,until:Math.max(a?a.release:0,b?b.release:0)});
 }
 cracks.sort((p,q)=>p.t0-q.t0);
 plates.sort((p,q)=>p.release-q.release);
 const F={plates,cracks,img:earthImg,px:Math.max(16,Math.min(600,Math.ceil(pxRadius)||200)),
  earth:null,tex:null,scorch:null,painted:false,cut:-1,union:null,ctx:null,paint:null,crater:makeCrater()};
 paint(F);
 return F;
}

// Crater outline and cooling fractures in crater units (radius 1), once.
function makeCrater(){
 const bowl=new Path2D(),hot=new Path2D();
 for(let i=0;i<=64;i++){const a=i/64*TAU,rr=1+.045*Math.sin(a*5+1)+.025*Math.cos(a*9);i?bowl.lineTo(Math.cos(a)*rr,Math.sin(a)*rr):bowl.moveTo(Math.cos(a)*rr,Math.sin(a)*rr);}
 bowl.closePath();
 for(let i=0;i<9;i++){const a=i*2.399,rr=1.1+(i%3)*.22;hot.moveTo(Math.cos(a)*.35,Math.sin(a)*.35);hot.lineTo(Math.cos(a+.1)*.8,Math.sin(a+.1)*.8);hot.lineTo(Math.cos(a)*rr,Math.sin(a)*rr);}
 return {bowl,hot};
}

// Earth canvas (with its thin atmosphere), plus two atlases: every plate cut from the texture, and the same plates
// scorched with a hot rim. Waits for the image when it is not loaded yet.
function paint(F){
 const img=F.img;
 if(!img||img.complete===false||!(img.naturalWidth||img.width))return false;
 const s=F.px,size=Math.ceil(s*2/.88),pad=2;
 const earth=document.createElement('canvas');earth.width=earth.height=size;earth.getContext('2d').drawImage(img,0,0,size,size);
 // Shelf packing, tallest first.
 const order=F.plates.slice().sort((p,q)=>(q.y1-q.y0)-(p.y1-p.y0));let area=0,W=0;
 for(const p of order){p.sw=Math.ceil((p.x1-p.x0)*s)+pad*2;p.sh=Math.ceil((p.y1-p.y0)*s)+pad*2;area+=p.sw*p.sh;W=Math.max(W,p.sw);}
 W=Math.max(W,Math.ceil(Math.sqrt(area)*1.12));let x=0,y=0,row=0;
 for(const p of order){if(x+p.sw>W){x=0;y+=row;row=0;}p.sx=x;p.sy=y;x+=p.sw;row=Math.max(row,p.sh);}
 const tex=document.createElement('canvas'),scorch=document.createElement('canvas');
 tex.width=scorch.width=W;tex.height=scorch.height=y+row;
 const a=tex.getContext('2d'),b=scorch.getContext('2d');
 for(const p of order){
  const clip=new Path2D(),ox=p.sx+pad-p.x0*s,oy=p.sy+pad-p.y0*s;
  tracePath(clip,p.pts,-ox/s,-oy/s,s);
  for(const c of [a,b]){c.save();c.clip(clip);c.drawImage(earth,ox-s/.88,oy-s/.88,size,size);c.restore();}
  b.save();b.clip(clip);b.globalCompositeOperation='source-atop';b.fillStyle='rgba(66,34,18,.56)';b.fillRect(p.sx,p.sy,p.sw,p.sh);
  b.strokeStyle='rgba(255,118,40,.55)';b.lineWidth=Math.max(1.5,s*.012);b.stroke(clip);b.restore();
  // Sprite rectangle in unit radius, relative to the Earth centre.
  p.ux=p.x0-pad/s;p.uy=p.y0-pad/s;p.uw=p.sw/s;p.uh=p.sh/s;
 }
 Object.assign(F,{earth,tex,scorch,painted:true});
 return true;
}

// Gradients in unit space, made once per drawing context.
function styles(F,g){
 if(F.ctx===g&&F.paint)return F.paint;
 const radial=(x0,y0,r0,x1,y1,r1,stops)=>{const q=g.createRadialGradient(x0,y0,r0,x1,y1,r1);for(const [at,col] of stops)q.addColorStop(at,col);return q;};
 const glow=(x,y,r,col)=>radial(x,y,0,x,y,r,[[0,col],[1,'rgba(0,0,0,0)']]);
 F.ctx=g;F.paint={
  core:radial(.08,0,0,0,0,1,[[0,'#ffe6a0'],[.3,'#ffad39'],[.7,'#c64a1e'],[1,'#52261d']]),
  bowl:radial(-.22,-.25,0,0,0,1,[[0,'#0b1017'],[.65,'#201c1c'],[.88,'#64594b'],[1,'#b6a28a']]),
  ejecta:radial(0,0,.6,0,0,2.3,[[0,'#403327aa'],[.6,'#a4916e55'],[1,'#766d5800']]),
  heat:glow(0,0,1.4,'#ff8c35'),inner:glow(.1,-.1,1.5,'#ffc178'),outer:glow(.22,-.22,1.25,'#ff9c4b')};
 return F.paint;
}

/** Earth after the impact (age = T-4.7 > 0): draws the whole Earth itself, also the thin atmosphere at the limb. */
export function drawCracking(g,F,x,y,r,age){
 if(!F||!(age>0)||!(r>0))return;
 if(!F.painted&&!paint(F))return;
 const S=styles(F,g),plates=F.plates,n=plates.length;
 g.save();g.translate(x,y);g.scale(r,r);
 g.drawImage(F.earth,-1/.88,-1/.88,2/.88,2/.88);
 g.save();g.beginPath();g.arc(0,0,.995,0,TAU);g.clip();
 // Intact plates: one clip with all of them, so the texture shows no seams where no crack has run yet. The clip is
 // rebuilt only when a plate comes loose (plates are sorted by release). While none is loose, the Earth drawn above
 // already is the intact crust and the core is hidden: no clip, no core.
 let cut=F.cut<0?0:F.cut;
 while(cut<n&&plates[cut].release<=age)cut++;
 while(cut>0&&plates[cut-1].release>age)cut--;
 if(cut!==F.cut){F.cut=cut;F.union=new Path2D();for(let k=cut;k<n;k++)tracePath(F.union,plates[k].pts);}
 if(cut){g.globalAlpha=smooth(age/.6);g.fillStyle=S.core;g.fillRect(-1,-1,2,2);g.globalAlpha=1;}
 if(cut<n){
  g.save();
  if(cut){g.clip(F.union);g.drawImage(F.earth,-1/.88,-1/.88,2/.88,2/.88);}
  for(let k=cut;k<n;k++){
   const p=plates[k],burn=smooth((age-p.release+.9)/1.3);if(!burn)continue;
   g.globalAlpha=burn;g.drawImage(F.scorch,p.sx,p.sy,p.sw,p.sh,p.ux,p.uy,p.uw,p.uh);
  }
  g.globalAlpha=1;
  // A recessed bowl, raised sunlit rim and cooling fractures; they leave together with the plates they sit on.
  const grow=smooth(age/.65),cr=.3*grow,heat=Math.exp(-age*.48);
  if(cr>.001){
   const px=1/(r*cr);
   g.save();g.translate(IMPACT_X,IMPACT_Y);g.rotate(-.35);g.scale(cr,cr*.73);
   g.globalAlpha=.7;g.fillStyle=S.ejecta;g.beginPath();g.arc(0,0,2.3,0,TAU);g.fill();g.globalAlpha=1;
   g.fillStyle=S.bowl;g.fill(F.crater.bowl);
   g.strokeStyle='#dfccb4';g.globalAlpha=.65*grow;g.lineWidth=Math.max(px,.012/cr);g.beginPath();g.ellipse(-.025,-.02,.94,.94,0,Math.PI*.92,Math.PI*1.83);g.stroke();
   g.globalAlpha=heat*.7;g.strokeStyle='#ff8f41';g.lineWidth=px;g.stroke(F.crater.hot);
   g.globalAlpha=heat*.3;g.fillStyle=S.heat;g.fillRect(-1.4,-1.4,2.8,2.8);g.restore();
  }
  g.restore();
 }
 // Cracks run from the vertex the wave reaches first to the other one, and widen once they are complete.
 g.lineCap='round';g.lineJoin='round';
 for(const c of F.cracks){
  if(c.t0>=age)break; // sorted by start
  if(age>=c.until)continue;
  const xy=c.xy,cum=c.cum,m=cum.length,target=clamp((age-c.t0)/c.dur)*cum[m-1];
  g.beginPath();g.moveTo(xy[0],xy[1]);
  let k=1;
  for(;k<m&&cum[k]<=target;k++)g.lineTo(xy[k*2],xy[k*2+1]);
  if(k<m){const f=(target-cum[k-1])/((cum[k]-cum[k-1])||1);g.lineTo(xy[k*2-2]+(xy[k*2]-xy[k*2-2])*f,xy[k*2-1]+(xy[k*2+1]-xy[k*2-1])*f);}
  g.strokeStyle='#21150f';g.lineWidth=.004+.006*smooth((age-c.last)/1.5);g.stroke();
  g.strokeStyle='rgba(255,132,48,.65)';g.lineWidth=.0018;g.stroke();
 }
 g.restore();
 // The interior glows stronger and stronger until the burst.
 const charge=smooth(age/1.2)*(.3+.48*smooth((age-1.3)/8.8));
 g.save();g.beginPath();g.arc(0,0,1,0,TAU);g.clip();g.globalAlpha=charge;g.fillStyle=S.inner;g.fillRect(-1,-1,2,2);g.restore();
 g.globalAlpha=charge*.55;g.fillStyle=S.outer;g.fillRect(-1.03,-1.47,2.5,2.5);
 g.restore();
}

/** Loose plates, T in seconds since departure. The same state continues through the burst (T 15) and collapse. */
export function drawDebris(g,F,x,y,r,T){
 if(!F||!(r>0)||T<=4.7)return;
 if(!F.painted&&!paint(F))return;
 const burst=Math.max(0,T-15),collapse=smooth((burst-.9)/2),push=.34*(1-Math.exp(-burst*1.5)),end=1-smooth((burst-2.35)/.6);
 if(end<=0)return;
 const plates=F.plates,keep=1-collapse,shrink=(1-collapse*.94)*r;
 for(let k=0;k<plates.length;k++){
  const p=plates[k],life=T-4.7-p.release;
  if(life<0)break; // sorted by release
  const fade=(1-smooth((life-6.8)/5))*end;
  if(fade<=0)continue;
  const travel=life*.065+life*life*.004+push,scale=Math.max(.12,1-life*.035)*shrink;
  g.save();g.translate(x+(p.px+p.dirX*travel)*r*keep,y+(p.py+p.dirY*travel+life*life*.006)*r*keep);g.rotate(life*p.spin);g.scale(scale,scale);
  const ux=p.ux-p.px,uy=p.uy-p.py;
  // Scorching continues from the intact plate, so nothing jumps at the release; fully scorched is one sprite.
  const burn=smooth((life+.9)/1.3);
  if(burn<1){g.globalAlpha=fade;g.drawImage(F.tex,p.sx,p.sy,p.sw,p.sh,ux,uy,p.uw,p.uh);}
  g.globalAlpha=fade*burn;g.drawImage(F.scorch,p.sx,p.sy,p.sw,p.sh,ux,uy,p.uw,p.uh);
  g.restore();
 }
}

/** Frees the sprites and paths; the object can no longer be drawn. */
export function disposeFracture(F){
 if(!F)return;
 for(const c of [F.earth,F.tex,F.scorch])if(c)c.width=c.height=0;
 Object.assign(F,{earth:null,tex:null,scorch:null,union:null,img:null,ctx:null,paint:null,painted:false,plates:[],cracks:[]});
}
