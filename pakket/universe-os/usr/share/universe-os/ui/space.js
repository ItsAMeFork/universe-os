import {alpha,earth,globe,pixelSize} from './globe.js';
// The space scene of the login and lock screen (Axel, 10 Oct: "the planet like the Earth, but in the universe itself").
// The same camera, stars and orbits as the 3D desktop (world.js), seen close to the Earth: after login the desktop
// starts in exactly this view and pulls back, so the two screens flow into each other.
export const FOV=900,EARTH_SIZE=380;
export const DEFAULT_CAM={yaw:-.5,pitch:.42,dist:1650,tx:0,ty:0,tz:0};
/** Camera distance at which the Earth is `px` screen pixels wide. */
export const distFor=px=>FOV*EARTH_SIZE/px;
export function project(cam,[x,y,z],w,h){
 const dx=x-cam.tx,dy=y-cam.ty,dz=z-cam.tz,cy=Math.cos(cam.yaw),sy=Math.sin(cam.yaw),cp=Math.cos(cam.pitch),sp=Math.sin(cam.pitch);
 const x1=dx*cy-dz*sy,z1=dx*sy+dz*cy,y2=dy*cp-z1*sp,depth=dy*sp+z1*cp+cam.dist;
 if(depth<30)return null;
 const s=FOV/depth;return {x:w/2+x1*s,y:h/2+y2*s,s,depth};
}
const STARS=Array.from({length:900},(_,i)=>{let s=(i*9301+49297)%233280;const r=()=>(s=(s*9301+49297)%233280)/233280;
 const u=r()*2-1,t=r()*Math.PI*2,q=Math.sqrt(1-u*u);return [q*Math.cos(t),u,q*Math.sin(t),.25+r()*.75,r()<.06];});
/** Stars and the orange orbit around the Earth on a canvas of w x h CSS pixels. */
export function drawSky(canvas,cam,w=innerWidth,h=innerHeight,dpr=Math.min(devicePixelRatio||1,2)){
 canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
 const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);
 const cy=Math.cos(cam.yaw),sy=Math.sin(cam.yaw),cp=Math.cos(cam.pitch),sp=Math.sin(cam.pitch);
 for(const [x,y,z,b,big] of STARS){
  const x1=x*cy-z*sy,z1=x*sy+z*cy,y2=y*cp-z1*sp,z2=y*sp+z1*cp;if(z2<=.05)continue;
  const px=w/2+x1/z2*FOV,py=h/2+y2/z2*FOV;if(px<0||py<0||px>w||py>h)continue;
  c.fillStyle=`rgba(208,224,255,${alpha(b)})`;c.beginPath();c.arc(px,py,big?1.5:.7,0,7);c.fill();
 }
 c.strokeStyle='rgba(255,165,82,.55)';c.lineWidth=1.5;c.beginPath();let pen=false;
 for(let i=0;i<=120;i++){const a=i/120*Math.PI*2,p=project(cam,[Math.cos(a)*420,0,Math.sin(a)*420],w,h);if(!p){pen=false;continue;}pen?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y);pen=true;}
 c.stroke();
 return canvas;
}
/** A few far planets around the Earth, like the program planets of the desktop. Returns positioned elements. */
export function farPlanets(cam,w=innerWidth,h=innerHeight){
 const list=[[1350,-80,0,32],[ -900,60,1000,140],[200,-120,-1500,262],[-1500,40,-300,318],[1100,100,1300,205],[-300,-60,1900,90]];
 return list.map(([x,y,z,hue])=>{
  const p=project(cam,[x,y,z],w,h);if(!p)return null;
  const size=Math.max(14,150*p.s);
  const el=globe(hue,hue%3===0,pixelSize(size));el.classList.add('far-planet');
  el.style.cssText=`position:absolute;left:${(p.x-size/2).toFixed(1)}px;top:${(p.y-size/2).toFixed(1)}px;width:${size.toFixed(1)}px;height:${size.toFixed(1)}px;opacity:.8`;
  return el;
 }).filter(Boolean);
}
/** The Earth for a given screen width (internal size up to 640 px for the big login planet). */
export const bigEarth=px=>earth(pixelSize(px),640);
