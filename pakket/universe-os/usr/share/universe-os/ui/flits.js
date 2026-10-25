import {on} from './api.js';
// Venster-animatie (0.2.35). Event 'venster-flits': {soort:'open'|'sluit'|'min', van:'dock'|'midden', max:bool, snel:bool}
// open: groeit vanuit het dock-icoon (of het midden) met schaal + vervagen, mint-gloed en een scanline, ~300 ms ease-out.
// sluit/min: andersom en sneller (~180 ms) terug naar het dock. Meerdere tegelijk mogen: elk bericht is een eigen element.
export const DUUR={open:300,sluit:180,min:220};
export function vak(max,w,h){
 if(max)return {x:0,y:0,w,h:h-80};
 const vw=Math.round(w*.55),vh=Math.round(h*.55);
 return {x:Math.round((w-vw)/2),y:Math.round((h-vh)/2.4),w:vw,h:vh};
}
export function plan(d,w,h){
 const v=vak(!!d.max,w,h),soort=d.soort in DUUR?d.soort:'open';
 const ox=d.van==='dock'?(w/2-v.x)+'px':'50%',oy=d.van==='dock'?(h-40-v.y)+'px':'50%';
 const snel=!!d.snel,duur=snel?Math.min(160,DUUR[soort]):DUUR[soort];
 const klein='scale(.08)',groot='scale(1)';
 const frames=soort==='open'
  ?(snel?[{opacity:0,transform:'scale(.96)'},{opacity:.6,transform:groot,offset:.6},{opacity:0,transform:groot}]
        :[{opacity:0,transform:klein},{opacity:1,transform:'scale(1.015)',offset:.55},{opacity:.85,transform:groot,offset:.7},{opacity:1,transform:groot,offset:.8},{opacity:0,transform:groot}])
  :(snel?[{opacity:.5,transform:groot},{opacity:0,transform:'scale(.96)'}]
        :[{opacity:.9,transform:groot},{opacity:0,transform:klein}]);
 return {v,ox,oy,duur,frames,easing:soort==='open'?'cubic-bezier(.16,1,.3,1)':'cubic-bezier(.5,0,.75,0)',snel,lijnen:!snel&&soort==='open'};
}
if(typeof document!=='undefined')on('venster-flits',d=>{
 const p=plan(d||{},innerWidth,innerHeight);
 const el=document.createElement('div');
 el.className='holo'+(p.snel?' snel':'')+(p.lijnen?' lijnen':'');
 Object.assign(el.style,{left:p.v.x+'px',top:p.v.y+'px',width:p.v.w+'px',height:p.v.h+'px'});
 el.style.setProperty('--ox',p.ox);el.style.setProperty('--oy',p.oy);el.style.setProperty('--d',p.duur+'ms');
 document.body.append(el);
 el.animate(p.frames,{duration:p.duur,easing:p.easing,fill:'forwards'}).finished.finally(()=>el.remove());
});
