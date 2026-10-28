import {alpha,earth,globe,pixelSize} from './globe.js';
import {tekenNevel,tekenSterren} from './sterrenhemel.js';
import {isLight} from './motion.js';
// The space scene of the login and lock screen (Axel, 10 Oct: "the planet like the Earth, but in the universe itself").
// The same camera, stars and orbits as the 3D desktop (world.js), seen close to the Earth: after login the desktop
// starts in exactly this view and pulls back, so the two screens flow into each other.
export const FOV=900,EARTH_SIZE=380;
export const DEFAULT_CAM={yaw:-.5,pitch:.42,dist:1650,tx:0,ty:0,tz:0};
/** Camera distance at which the Earth is `px` screen pixels wide. */
export const distFor=px=>FOV*EARTH_SIZE/px;
/** Width of the Earth on the login screen, and so the end picture of logging out and locking (world.js closeView).
 * 0.3.3 (Axel, 28 Oct: "iets meer uitgezoomd"): 20 % smaller than before (was min(80vw, 78vh, 650 px)). */
export const loginEarthPx=()=>Math.min(innerWidth*.64,innerHeight*.62,520);
export function project(cam,[x,y,z],w,h){
 const dx=x-cam.tx,dy=y-cam.ty,dz=z-cam.tz,cy=Math.cos(cam.yaw),sy=Math.sin(cam.yaw),cp=Math.cos(cam.pitch),sp=Math.sin(cam.pitch);
 const x1=dx*cy-dz*sy,z1=dx*sy+dz*cy,y2=dy*cp-z1*sp,depth=dy*sp+z1*cp+cam.dist;
 if(depth<30)return null;
 const s=FOV/depth;return {x:w/2+x1*s,y:h/2+y2*s,s,depth};
}
/** Stars and the orange orbit around the Earth on a canvas of w x h CSS pixels. */
export function drawSky(canvas,cam,w=innerWidth,h=innerHeight,dpr=Math.min(devicePixelRatio||1,2)){
 canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
 const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);
 // 0.2.38: the same sky as the desktop (sterrenhemel.js): nebula, coloured stars in layers; lighter on weak pcs
 tekenNevel(c,cam,w,h,isLight(),.9);
 tekenSterren(c,cam,w,h,{licht:isLight()});
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
