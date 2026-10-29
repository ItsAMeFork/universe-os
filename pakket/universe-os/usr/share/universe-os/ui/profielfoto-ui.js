// 0.3.4 (Axel, 28 Oct): your own profile photo (Controlecentrum > Gebruikers > your account). Any photo file; the
// shell (profielfoto.py) reads it, here you place it in the circle of your planet: drag to move, slider or mouse wheel
// to zoom. The crop is computed in pixels of the original, so saving cuts from the full-quality photo.

// ----- the editor's arithmetic (also used by docs/tests/profielfoto-ui.mjs) -----
// State: w,h = size of the original; zoom >= 1 (1 = the short side fills the circle); cx,cy = middle of the crop.
const MAX_ZOOM=8;
const zijde=s=>Math.min(s.w,s.h)/s.zoom;
function binnen(s){const z=zijde(s),k=(v,max)=>Math.min(Math.max(v,z/2),max-z/2);return {...s,cx:k(s.cx,s.w),cy:k(s.cy,s.h)};}
export const beginBeeld=(w,h)=>({w,h,zoom:1,cx:w/2,cy:h/2});
/** Dragging by dx,dy screen pixels over a circle of `diameter` pixels moves the photo along with the pointer. */
export const verschuif=(s,dx,dy,diameter)=>{const k=zijde(s)/diameter;return binnen({...s,cx:s.cx-dx*k,cy:s.cy-dy*k});};
export const zoom=(s,z)=>binnen({...s,zoom:Math.min(MAX_ZOOM,Math.max(1,Number(z)||1))});
export function uitsnede(s){const z=zijde(s);return {x:Math.round(s.cx-z/2),y:Math.round(s.cy-z/2),size:Math.round(z)};}

// ----- the card -----
/** @param {{call:Function,h:Function,photo:string|null,orb:string,onChange:Function}} o */
export function fotoKaart({call,h,photo,orb,onChange}){
 const message=h('p',{class:'message',role:'status'});
 const say=(t,error=false)=>{message.className=error?'message error':'message';message.textContent=t||'';};
 const voorbeeld=photo?h('img',{class:'orb profielfoto',src:photo,alt:''}):h('span',{class:'orb',style:orb});
 const kies=h('button',{type:'button'},'Foto kiezen…');
 const weg=h('button',{type:'button',hidden:!photo},'Foto verwijderen');
 const D=260,canvas=h('canvas',{class:'profielfoto-editor',width:D*2,height:D*2,style:`width:${D}px;height:${D}px;touch-action:none;cursor:grab`,
  tabindex:'0','aria-label':'Voorbeeld van je profielfoto. Sleep of gebruik de pijltjes om te verschuiven, plus en min om te zoomen.'});
 const schuif=h('input',{type:'range',min:'1',max:String(MAX_ZOOM),step:'0.01',value:'1','aria-label':'Zoomen'});
 const opslaan=h('button',{type:'button',class:'primary'},'Opslaan'),annuleer=h('button',{type:'button'},'Annuleren');
 const editor=h('div',{class:'profielfoto-bewerk',hidden:true},canvas,
  h('label',{},'Zoomen',schuif),h('p',{class:'muted'},'Sleep de foto (of gebruik de pijltjes) om hem te verschuiven; zoom met de schuifbalk, het muiswiel of + en −.'),
  h('div',{class:'row'},opslaan,annuleer));
 let pad='',s=null,img=null;
 const ctx=canvas.getContext?.('2d');
 function teken(){
  if(!ctx||!img||!s)return;
  const z=zijde(s),k=canvas.width/z;
  ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.drawImage(img,-(s.cx-z/2)*k,-(s.cy-z/2)*k,s.w*k,s.h*k);
  const r=canvas.width/2;ctx.fillStyle='#050815b0';ctx.beginPath();ctx.rect(0,0,canvas.width,canvas.height);ctx.arc(r,r,r-2,0,Math.PI*2);ctx.fill('evenodd');
  ctx.strokeStyle='#85ffe3';ctx.lineWidth=3;ctx.beginPath();ctx.arc(r,r,r-2,0,Math.PI*2);ctx.stroke();
 }
 const bezig=b=>{for(const x of [kies,weg,opslaan,annuleer])x.disabled=b;};
 kies.addEventListener('click',async()=>{
  bezig(true);say('');
  try{
   const gekozen=await call('account.photo.choose');if(!gekozen)return;
   say('Foto openen…');
   const v=await call('account.photo.preview',{path:gekozen});
   img=await new Promise((ok,fout)=>{const i=new Image();i.onload=()=>ok(i);i.onerror=()=>fout(Error('Dit bestand is geen foto die Universe OS kan lezen.'));i.src=v.beeld;});
   pad=gekozen;s=beginBeeld(v.breedte,v.hoogte);schuif.value='1';editor.hidden=false;say('');teken();
  }catch(e){say(e.message||'Openen mislukt.',true);}
  finally{bezig(false);}
 });
 let sleep=null;
 canvas.addEventListener('pointerdown',e=>{if(!s)return;sleep={x:e.clientX,y:e.clientY};canvas.setPointerCapture?.(e.pointerId);canvas.style.cursor='grabbing';});
 canvas.addEventListener('pointermove',e=>{if(!sleep)return;s=verschuif(s,e.clientX-sleep.x,e.clientY-sleep.y,canvas.clientWidth||D);sleep={x:e.clientX,y:e.clientY};teken();});
 const los=()=>{sleep=null;canvas.style.cursor='grab';};
 canvas.addEventListener('pointerup',los);canvas.addEventListener('pointercancel',los);
 canvas.addEventListener('wheel',e=>{if(!s)return;e.preventDefault();s=zoom(s,s.zoom*(e.deltaY<0?1.1:1/1.1));schuif.value=String(s.zoom);teken();},{passive:false});
 schuif.addEventListener('input',()=>{if(!s)return;s=zoom(s,schuif.value);teken();});
 // Keyboard too: arrows move the photo (as dragging does), + and - zoom.
 canvas.addEventListener('keydown',e=>{
  if(!s)return;const stap=(canvas.clientWidth||D)*.05,pijl={ArrowLeft:[-stap,0],ArrowRight:[stap,0],ArrowUp:[0,-stap],ArrowDown:[0,stap]}[e.key];
  if(pijl)s=verschuif(s,pijl[0],pijl[1],canvas.clientWidth||D);
  else if(e.key==='+'||e.key==='=')s=zoom(s,s.zoom*1.1);else if(e.key==='-')s=zoom(s,s.zoom/1.1);else return;
  e.preventDefault();schuif.value=String(s.zoom);teken();
 });
 const sluit=()=>{editor.hidden=true;s=null;img=null;pad='';};
 annuleer.addEventListener('click',()=>{sluit();say('');});
 opslaan.addEventListener('click',async()=>{
  if(!s)return;bezig(true);say('Opslaan…');
  try{await call('account.photo.save',{path:pad,...uitsnede(s)});sluit();say('Profielfoto opgeslagen.');await onChange?.();}
  catch(e){say(e.message||'Opslaan mislukt.',true);}
  finally{bezig(false);}
 });
 weg.addEventListener('click',async()=>{
  bezig(true);say('Verwijderen…');
  try{await call('account.photo.remove');say('Profielfoto verwijderd.');await onChange?.();}
  catch(e){say(e.message||'Verwijderen mislukt.',true);}
  finally{bezig(false);}
 });
 return h('section',{class:'card'},h('h3',{},'Profielfoto'),
  h('p',{class:'muted'},'Je foto verschijnt op je planeet in het inlogscherm. Elk soort foto kan; je kiest zelf welk deel in de cirkel staat.'),
  h('div',{class:'row profielfoto-rij'},voorbeeld,kies,weg),editor,message);
}
