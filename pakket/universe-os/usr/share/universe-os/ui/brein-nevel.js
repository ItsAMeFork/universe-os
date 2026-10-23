// Brein-nevel: the second brain as a canvas. One star per memory (capped), lines from shared
// tags and words, the timeline as a comet, file hits as moons. No libraries, no shadows, no
// per-frame gradients except the comet head. The loop sleeps unless motion is allowed.
import {h,icon} from './api.js';

export const STAR_CAP=160;
const TRAIL_CAP=36;
const MOON_CAP=10;
const KIND={
 voorkeur:{naam:'Voorkeur',kleur:'#85ffe3'},
 notitie:{naam:'Notitie',kleur:'#c9b6ff'},
 feit:{naam:'Feit',kleur:'#ffc98a'},
 les:{naam:'Les',kleur:'#d6ff9a'},
 mail:{naam:'Mail',kleur:'#9ecbff'},
 agenda:{naam:'Agenda',kleur:'#ffe08a'},
 actie:{naam:'Actie',kleur:'#ff9ec8'},
};
const STATUS={goedgekeurd:'Goedgekeurd',geweigerd:'Geweigerd',uitgevoerd:'Uitgevoerd',mislukt:'Mislukt',automatisch:'Automatisch',wacht:'Wacht',ongedaan:'Ongedaan'};
const FILTERS=[['alles','Alles'],['herinneringen','Herinneringen'],['lessen','Lessen'],['mail','Mail'],['agenda','Agenda'],['acties','Acties']];

const hash=n=>{let x=(2166136261^n)>>>0;x=Math.imul(x^(n&255),16777619);x=Math.imul(x^((n>>>8)&255),16777619);return x>>>0;};
const clip=(t,n)=>{const s=String(t||'').replace(/\s+/g,' ').trim();return s.length>n?s.slice(0,n-1)+'…':s;};

/** Stable place in the cloud: kind picks a lobe, the id picks the spot inside it. */
export function layoutPoint(star,w,h){
 const lobe={voorkeur:-0.9,notitie:2.25,feit:4.75,les:1.6,mail:0.35,agenda:3.5,actie:5.4}[star.soort]??1.2;
 const n=hash(Number(star.id)||0);
 const ang=lobe+((n%1000)/1000)*1.2;
 const rad=0.2+(((n>>>10)%1000)/1000)*0.8;
 const span=Math.min(w,h)*0.3*rad;
 const ox=Math.cos(lobe)*Math.min(w,h)*0.1;
 const oy=Math.sin(lobe)*Math.min(w,h)*0.04;
 const x=w*0.5+ox+Math.cos(ang)*span;
 const y=h*0.48+oy+Math.sin(ang)*span*0.74;
 return {x:Math.max(28,Math.min(w-28,x)),y:Math.max(86,Math.min(h-48,y))};
}

function motionOn(){
 const root=document.documentElement;
 if(root.classList.contains('reduce-motion')||root.classList.contains('no-motion')||root.classList.contains('background-busy'))return false;
 if(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches)return false;
 if(document.hidden)return false;
 return true;
}

function drawBackdrop(c,w,h){
 c.fillStyle='#050815';c.fillRect(0,0,w,h);
 const span=Math.min(w,h);
 const clouds=[[.28,.42,.46,'rgba(133,255,227,.14)'],[.52,.5,.5,'rgba(158,140,255,.17)'],[.76,.4,.38,'rgba(255,165,82,.13)']];
 for(const [px,py,pr,color] of clouds){
  const x=w*px,y=h*py,r=span*pr;
  const g=c.createRadialGradient(x,y,0,x,y,r);
  g.addColorStop(0,color);g.addColorStop(1,'rgba(5,8,21,0)');
  c.fillStyle=g;c.fillRect(0,0,w,h);
 }
 let s=9001;const rnd=()=>(s=(s*9301+49297)%233280)/233280;
 c.fillStyle='#d2dcff';
 for(let i=0;i<40;i++){c.globalAlpha=.12+rnd()*.28;c.fillRect(rnd()*w,rnd()*h,rnd()<.08?1.5:1,1);}
 c.globalAlpha=1;
}

function glyph(c,kind,x,y){
 c.save();c.translate(x,y);c.lineWidth=1.15;c.strokeStyle='rgba(226,230,250,.9)';c.fillStyle='rgba(8,12,28,.85)';
 c.beginPath();
 if(kind==='file'||kind==='bestand'){
  c.moveTo(-4.5,-6);c.lineTo(1.5,-6);c.lineTo(5,-2.5);c.lineTo(5,6);c.lineTo(-4.5,6);c.closePath();c.fill();c.stroke();
 }else{
  c.rect(-5.5,-5,11,10);c.fill();c.stroke();
  c.fillStyle='#85ffe3';c.fillRect(-1.4,-1.2,2.8,2.8);
 }
 c.restore();
}

function crescent(c,x,y,r){
 c.beginPath();c.arc(x,y,r,0,7);c.fillStyle='#e4e9fb';c.fill();
 c.beginPath();c.arc(x+r*.38,y-r*.12,r*.78,0,7);c.fillStyle='#050815';c.fill();
}

/**
 * @param {HTMLElement} parent room element
 * @param {{call?:Function,leave?:Function,alive?:Function,data?:object,focus?:boolean}} api
 * @returns {() => void} dispose
 */
export function mountNebula(parent,api={}){
 const call=api.call||(async()=>({}));
 const still=api.alive||(()=>true);
 const canvas=h('canvas',{class:'nebula-canvas','aria-hidden':'true'});
 const search=h('input',{type:'search',class:'nebula-search',placeholder:'Zoek in je brein…','aria-label':'Zoek in herinneringen'});
 const legend=h('div',{class:'nebula-legend','aria-hidden':'true'});
 for(const k of Object.values(KIND))legend.append(h('span',{},h('i',{style:'background:'+k.kleur}),k.naam));
 const back=h('button',{class:'room-back',type:'button'},icon('back'),'Terug');
 back.addEventListener('click',()=>api.leave?.());
 const privacy=h('button',{type:'button'},'Privacy');
 privacy.addEventListener('click',()=>call('run',{tool:'control',page:'security'}).catch(e=>{status.textContent=e.message;}));
 const title=h('div',{class:'nebula-title'},h('strong',{},'Brein'),h('span',{},'Herinneringen in de nevel'));
 const listBtn=h('button',{type:'button','aria-pressed':'true'},'Lijst');
 const hud=h('div',{class:'nebula-hud'},back,title,search,legend,listBtn,privacy);
 const chips=h('div',{class:'nebula-chips'});
 const ochtend=h('section',{class:'ochtend','aria-label':'Ochtendbriefing'});
 const list=h('aside',{class:'nebula-list','aria-label':'Lijst van mail, agenda en acties'});
 const caption=h('p',{class:'nebula-caption'},'Komeetspoor · programma’s en bestanden die je opende');
 const hover=h('div',{class:'nebula-hover',hidden:true});
 const card=h('article',{class:'nebula-card',hidden:true,'aria-live':'polite'});
 const status=h('p',{class:'nebula-status',role:'alert'});
 parent.replaceChildren(canvas,hud,chips,list,caption,hover,card,status);

 const state={stars:[],lines:[],trail:[],moons:[],rows:[],filter:'alles',match:null,hover:null,flash:null,selected:null,ochtend:null};
 const hits={stars:[],moons:[]};
 let plate=null,spots=null,timer=0,alive=true,searchTimer=0,searchToken=0,view={w:0,h:0,dpr:1};

 function applyData(data){
  state.stars=(data.sterren||[]).slice(0,STAR_CAP);
  state.lines=data.lijnen||[];
  state.trail=(data.spoor||[]).slice(-TRAIL_CAP);
  state.moons=(data.manen||[]).slice(0,MOON_CAP);
  state.match=data.treffers?new Set(data.treffers):null;
  if(data.zoek)search.value=data.zoek;
  drawChips();
 }

 function renderBriefing(){
  const data=state.ochtend;
  ochtend.replaceChildren(h('h2',{},'Ochtendbriefing'));
  if(!data){
   ochtend.append(h('p',{class:'muted'},'De briefing wordt gelezen…'));
   return;
  }
  if(data.fout){
   ochtend.append(h('p',{role:'alert'},data.fout));
   return;
  }
  ochtend.append(h('h3',{},'Agenda vandaag'));
  const agenda=data.agenda||[];
  if(!agenda.length) ochtend.append(h('p',{},data.agenda_tekst||'Niets op de agenda vandaag.'));
  else{
   const ul=h('ul',{});
   for(const item of agenda){
    const plek=item.plek?' · '+item.plek:'';
    ul.append(h('li',{},(item.van?item.van+' · ':'')+(item.titel||'Afspraak')+plek));
   }
   ochtend.append(ul);
  }
  ochtend.append(h('h3',{},'Belangrijke mail'));
  ochtend.append(h('p',{},data.mail_samenvatting||'Geen belangrijke mail.'));
  const mail=data.mail||[];
  if(mail.length){
   const ul=h('ul',{});
   for(const item of mail){
    const from=item.van?' — '+item.van:'';
    ul.append(h('li',{},(item.onderwerp||'Bericht')+from+(item.samenvatting?' '+item.samenvatting:'')));
   }
   ochtend.append(ul);
  }
  ochtend.append(h('h3',{},'Geldtip'));
  ochtend.append(h('p',{},data.geldtip||''));
  ochtend.append(h('p',{class:'muted'},data.bevestigen||'Versturen en betalen vragen om toestemming.'));
 }
 function renderList(){
  list.replaceChildren(ochtend);
  const bar=h('div',{class:'nebula-filters'});
  for(const [id,naam] of FILTERS){
   const b=h('button',{type:'button','aria-pressed':state.filter===id?'true':'false'},naam);
   b.addEventListener('click',()=>{state.filter=id;loadList();});
   bar.append(b);
  }
  list.append(h('h2',{},'Lijst'),bar);
  const rows=state.rows||[];
  if(!rows.length) list.append(h('p',{class:'muted'},'Niets in deze lijst.'));
  for(const row of rows){
   const kind=row.soort==='herinnering'?'herinnering':row.soort;
   const label={mail:'Mail',agenda:'Agenda',actie:'Actie',herinnering:'Herinnering',les:'Les'}[kind]||kind;
   const article=h('article',{});
   article.append(h('div',{class:'kind'},label+(row.tijd?' · '+row.tijd:'')),h('strong',{},row.titel||label),h('p',{},row.tekst||''));
   if(row.soort==='les'&&row.id){
    const edit=h('button',{type:'button'},'Bewerken');
    const drop=h('button',{type:'button'},'Verwijderen');
    edit.addEventListener('click',async()=>{
     const next=window.prompt('Les',row.tekst||'');
     if(!next||!next.trim())return;
     try{await call('brein.update',{id:row.id,tekst:next.trim()});await loadList();}
     catch(e){status.textContent=e.message||'Bewerken mislukt.';}
    });
    drop.addEventListener('click',async()=>{
     try{await call('brein.forget',{id:row.id});await load();}
     catch(e){status.textContent=e.message||'Verwijderen mislukt.';}
    });
    article.append(h('div',{class:'row'},edit,drop));
   }
   if(row.van) article.append(h('p',{class:'muted'},row.van));
   if(row.status) article.append(h('span',{class:'badge'},STATUS[row.status]||row.status));
   if(row.soort==='actie'&&row.ongedaan&&row.status!=='ongedaan'){
    const undo=h('button',{type:'button'},'Ongedaan maken');
    undo.addEventListener('click',async()=>{
     try{await call('brein.ongedaan',{id:row.id});await loadList();}
     catch(e){status.textContent=e.message||'Ongedaan maken mislukt.';}
    });
    article.append(undo);
   }
   list.append(article);
  }
 }
 async function loadList(){
  try{
   const data=await call('brein.lijst',{soort:state.filter,q:search.value.trim()});
   if(!alive||!still())return;
   state.rows=data?.rijen||[];
   if(state.filter==='alles'&&!search.value.trim()){
    const extra=(data?.sterren||[]).slice(0,36);
    const memories=state.stars.filter(s=>!s.bron);
    state.stars=extra.concat(memories).slice(0,STAR_CAP);
   }
  }catch(e){if(alive)status.textContent=e.message||'De lijst kon niet worden gelezen.';}
  renderList();paint();
 }
 async function load(){
  const briefing=call('brein.ochtend').then(data=>{state.ochtend=data||{};}).catch(e=>{
   state.ochtend={fout:e.message||'De ochtendbriefing kon niet worden gelezen.'};
  });
  try{
   const [mem,lines,trail]=await Promise.all([call('brein.list'),call('brein.links'),call('brein.timeline'),briefing]);
   if(!alive||!still())return;
   state.stars=(mem?.sterren||[]).filter(s=>!s.bron).slice(0,STAR_CAP);
   state.lines=lines?.lijnen||[];
   state.trail=(trail?.spoor||[]).slice(-TRAIL_CAP);
   status.textContent='';
  }catch(e){if(alive)status.textContent=e.message||'Het brein kon niet worden gelezen.';}
  if(alive){await briefing;renderBriefing();}
  await loadList();
  paint();arm();
  if(alive)parent.dataset.nebula='ready';
 }

 function drawChips(){
  chips.replaceChildren();
  if(!state.match)return;
  for(const star of state.stars.filter(s=>state.match.has(s.id)).slice(0,6)){
   const b=h('button',{type:'button'},clip(star.tekst,48)||KIND[star.soort]?.naam||'Ster');
   b.addEventListener('click',()=>openStar(star));
   chips.append(b);
  }
 }

 function placeTrail(i,n){
  const t=n<=1?0.5:i/(n-1);
  return {x:view.w*.08+t*view.w*.84,y:view.h*.8-Math.sin(t*Math.PI)*view.h*.065};
 }
 function placeMoon(i,n,t,motion){
  const ang=(motion?t*.00015:.6)+i/Math.max(1,n)*Math.PI*2;
  const rx=Math.min(view.w,view.h)*.2,ry=rx*.6;
  return {x:view.w*.5+Math.cos(ang)*rx,y:view.h*.46+Math.sin(ang)*ry};
 }

 function paint(now){
  const {w,h,dpr}=view;
  if(w<2||h<2)return;
  if(!plate||plate.w!==w||plate.h!==h){
   const off=document.createElement('canvas');off.width=w;off.height=h;
   drawBackdrop(off.getContext('2d'),w,h);plate={c:off,w,h};
  }
  const c=canvas.getContext('2d');
  c.setTransform(dpr,0,0,dpr,0,0);
  c.clearRect(0,0,w,h);
  c.drawImage(plate.c,0,0);
  // One motion check per frame (it reads three classes and a media query), and a star's spot only depends on its id,
  // kind and the canvas size, so it is worked out once per size.
  const motion=motionOn();
  if(!spots||spots.w!==w||spots.h!==h)spots={w,h,at:new Map()};
  const pos=new Map();
  for(const star of state.stars){
   let spot=spots.at.get(star.id);
   if(!spot||spot.soort!==star.soort){spot={soort:star.soort,point:layoutPoint(star,w,h)};spots.at.set(star.id,spot);}
   pos.set(star.id,spot.point);
  }
  const match=state.match;
  c.lineWidth=1;
  for(const line of state.lines){
   const a=pos.get(line.van),b=pos.get(line.naar);
   if(!a||!b)continue;
   const lit=!match||(match.has(line.van)&&match.has(line.naar));
   c.strokeStyle=lit?'rgba(186,247,232,.72)':'rgba(226,230,250,.16)';
   c.lineWidth=lit?1.35:1;
   c.beginPath();c.moveTo(a.x,a.y);c.lineTo(b.x,b.y);c.stroke();
  }
  const t=now||performance.now();
  const pts=state.trail.map((_,i)=>placeTrail(i,state.trail.length));
  for(let i=1;i<pts.length;i++){
   const a=i/(pts.length-1);
   c.strokeStyle=`rgba(255,214,170,${(.08+a*.5).toFixed(3)})`;
   c.lineWidth=1+a*1.3;
   c.beginPath();c.moveTo(pts[i-1].x,pts[i-1].y);c.lineTo(pts[i].x,pts[i].y);c.stroke();
  }
  hits.stars=[];hits.moons=[];
  if(pts.length){
   const head=pts[pts.length-1];
   const g=c.createRadialGradient(head.x,head.y,0,head.x,head.y,16);
   g.addColorStop(0,'rgba(255,236,214,.9)');g.addColorStop(1,'rgba(255,236,214,0)');
   c.fillStyle=g;c.beginPath();c.arc(head.x,head.y,16,0,7);c.fill();
  }
  state.trail.forEach((ev,i)=>{
   if(i!==state.trail.length-1&&i%Math.ceil(state.trail.length/10)!==0)return;
   const p=pts[i];glyph(c,ev.soort,p.x,p.y);
   hits.moons.push({x:p.x,y:p.y,r:12,trail:ev});
  });
  for(const star of state.stars){
   const p=pos.get(star.id);if(!p)continue;
   const kind=KIND[star.soort]||KIND.notitie;
   const lit=!match||match.has(star.id);
   let bright=Number(star.helderheid);if(!Number.isFinite(bright))bright=.6;
   if(motion)bright*=.92+.08*Math.sin(t/700+(star.id||0));
   const dim=lit?1:.24;
   const r=1.15+bright*2.3;
   c.globalAlpha=Math.max(.08,bright*dim);
   c.fillStyle=kind.kleur;
   c.beginPath();c.arc(p.x,p.y,r*3.1,0,7);c.fill();
   c.globalAlpha=Math.max(.2,Math.min(1,bright))*dim;
   c.beginPath();c.arc(p.x,p.y,r,0,7);c.fill();
   if(bright>.84&&lit){
    c.globalAlpha=.55*dim;c.strokeStyle=kind.kleur;c.lineWidth=1;
    c.beginPath();c.moveTo(p.x-r*2.4,p.y);c.lineTo(p.x+r*2.4,p.y);c.moveTo(p.x,p.y-r*2.4);c.lineTo(p.x,p.y+r*2.4);c.stroke();
   }
   c.globalAlpha=1;
   if(state.selected===star.id||(state.flash&&state.flash.id===star.id&&motion)){
    const age=state.flash&&state.flash.id===star.id?(t-state.flash.t0)/1400:0;
    const ring=state.selected===star.id?r+5:r+4+age*28;
    c.strokeStyle=kind.kleur;c.globalAlpha=state.selected===star.id?0.85:Math.max(0,0.8-age);c.lineWidth=1.4;
    c.beginPath();c.arc(p.x,p.y,ring,0,7);c.stroke();c.globalAlpha=1;
   }
   hits.stars.push({x:p.x,y:p.y,r:Math.max(12,r+8),star});
  }
  state.moons.forEach((moon,i)=>{
   const p=placeMoon(i,state.moons.length,t,motion);
   crescent(c,p.x,p.y,6.5);
   hits.moons.push({x:p.x,y:p.y,r:14,moon});
  });
  if(!state.stars.length){
   c.fillStyle='#869cae';c.font='15px "Noto Sans","DejaVu Sans",sans-serif';c.textAlign='center';
   c.fillText('Nog niets onthouden. Herinneringen verschijnen hier als sterren.',w/2,h/2);
  }
 }

 function nearest(list,x,y){
  let best=null,dist=1e9;
  for(const item of list){
   const d=(item.x-x)**2+(item.y-y)**2;
   if(d<dist&&d<item.r*item.r){dist=d;best=item;}
  }
  return best;
 }
 function local(e){
  const r=canvas.getBoundingClientRect();
  return {x:e.clientX-r.left,y:e.clientY-r.top};
 }
 function showHover(text,x,y){
  if(!text){hover.hidden=true;return;}
  hover.hidden=false;hover.textContent=text;
  hover.style.left=Math.min(view.w-250,x+12)+'px';
  hover.style.top=Math.max(80,y-32)+'px';
 }

 function openStar(star){
  state.selected=star.id;card.hidden=false;hover.hidden=true;
  const kind=KIND[star.soort]||KIND.notitie;
  if(star.bron){
   const close=h('button',{type:'button'},'Sluiten');
   close.addEventListener('click',()=>{state.selected=null;card.hidden=true;paint();});
   card.replaceChildren(h('div',{class:'kind',style:'color:'+kind.kleur},kind.naam),h('h2',{},clip(star.tekst,72)||kind.naam),h('p',{},star.tekst||''),star.labels?h('p',{class:'muted'},star.labels):null,h('div',{class:'row'},close));
   paint();close.focus();return;
  }
  const when=star.bijgewerkt?new Date(star.bijgewerkt*1000).toLocaleDateString('nl-NL',{day:'numeric',month:'long',year:'numeric'}):'';
  const body=h('p',{},star.tekst||'');
  const row=h('div',{class:'row'});
  const edit=h('button',{type:'button'},'Bewerken');
  const forget=h('button',{type:'button',class:'danger'},'Vergeten');
  const close=h('button',{type:'button'},'Sluiten');
  close.addEventListener('click',()=>{state.selected=null;card.hidden=true;paint();});
  edit.addEventListener('click',()=>{
   const area=h('textarea',{rows:5,'aria-label':'Tekst van de herinnering'});area.value=star.tekst||'';
   const save=h('button',{type:'button',class:'primary'},'Opslaan');
   const cancel=h('button',{type:'button'},'Annuleren');
   const msg=h('p',{class:'nebula-status',role:'alert'});
   save.addEventListener('click',async()=>{
    save.disabled=true;
    try{
     const updated=await call('brein.update',{id:star.id,tekst:area.value});
     if(!alive)return;
     const next=updated&&updated.id?updated:{...star,tekst:area.value.trim(),bijgewerkt:Date.now()/1000,helderheid:1};
     const i=state.stars.findIndex(s=>s.id===star.id);
     if(i>=0)state.stars[i]=next;
     openStar(next);
    }catch(e){msg.textContent=e.message;save.disabled=false;}
   });
   cancel.addEventListener('click',()=>openStar(star));
   card.replaceChildren(h('div',{class:'kind',style:'color:'+kind.kleur},kind.naam),h('h2',{},'Bewerken'),area,h('div',{class:'row'},save,cancel),msg);
   area.focus();
  });
  forget.addEventListener('click',()=>{
   const yes=h('button',{type:'button',class:'danger'},'Ja, deze ster vergeten');
   const no=h('button',{type:'button'},'Annuleren');
   const msg=h('p',{class:'nebula-status',role:'alert'});
   yes.addEventListener('click',async()=>{
    yes.disabled=true;
    try{
     await call('brein.forget',{id:star.id});
     if(!alive)return;
     state.stars=state.stars.filter(s=>s.id!==star.id);
     state.lines=state.lines.filter(l=>l.van!==star.id&&l.naar!==star.id);
     state.selected=null;card.hidden=true;drawChips();paint();
    }catch(e){msg.textContent=e.message;yes.disabled=false;}
   });
   no.addEventListener('click',()=>openStar(star));
   card.replaceChildren(h('div',{class:'kind',style:'color:'+kind.kleur},kind.naam),h('p',{},'Deze herinnering verdwijnt van deze computer.'),h('div',{class:'row'},yes,no),msg);
   yes.focus();
  });
  const labels=String(star.labels||'').split(',').map(s=>s.trim()).filter(Boolean);
  card.replaceChildren(
   h('div',{class:'kind',style:'color:'+kind.kleur},kind.naam+(when?' · '+when:'')),
   h('h2',{},clip(star.tekst,72)||kind.naam),
   body,
   labels.length?h('p',{class:'muted'},labels.join(' · ')):null,
   row);
  row.append(edit,forget,close);
  paint();
  edit.focus();
 }

 function openMoon(moon){
  state.selected=null;card.hidden=false;
  const open=h('button',{type:'button',class:'primary'},'Openen');
  const close=h('button',{type:'button'},'Sluiten');
  const msg=h('p',{class:'nebula-status',role:'alert'});
  open.addEventListener('click',async()=>{
   try{await call('open.path',{path:moon.pad});}catch(e){msg.textContent=e.message;}
  });
  close.addEventListener('click',()=>{card.hidden=true;});
  card.replaceChildren(h('div',{class:'kind',style:'color:#ffc98a'},'Bestand'),h('h2',{},moon.naam||moon.pad||'Bestand'),
   h('p',{class:'muted'},moon.pad||''),h('div',{class:'row'},open,close),msg);
  open.focus();
 }

 canvas.addEventListener('mousemove',e=>{
  const p=local(e);
  const star=nearest(hits.stars,p.x,p.y);
  const moon=nearest(hits.moons,p.x,p.y);
  canvas.classList.toggle('point',!!(star||moon));
  if(star)showHover(clip(star.star.tekst,90),star.x,star.y);
  else if(moon?.moon)showHover(moon.moon.naam||moon.moon.pad,moon.x,moon.y);
  else if(moon?.trail)showHover((moon.trail.naam||moon.trail.wat||'')+'',moon.x,moon.y);
  else showHover('');
 });
 canvas.addEventListener('mouseleave',()=>{canvas.classList.remove('point');showHover('');});
 canvas.addEventListener('click',e=>{
  const p=local(e);
  const star=nearest(hits.stars,p.x,p.y);
  if(star){openStar(star.star);return;}
  const moon=nearest(hits.moons,p.x,p.y);
  if(moon?.moon){openMoon(moon.moon);return;}
  if(moon?.trail){showHover((moon.trail.naam||moon.trail.wat||''),moon.x,moon.y);return;}
  state.selected=null;card.hidden=true;paint();
 });

 search.addEventListener('input',()=>{
  clearTimeout(searchTimer);
  searchTimer=setTimeout(async()=>{
   const q=search.value.trim();
   const token=++searchToken;
   if(!q){state.match=null;state.moons=[];drawChips();loadList();return;}
   try{
    const res=await call('brein.search',{q});
    if(!alive||token!==searchToken)return;
    state.match=new Set([...(res?.sterren||[]).map(s=>s.id),...(res?.extra||[]).map(s=>s.id)]);
    state.moons=(res?.bestanden||[]).slice(0,MOON_CAP);
    status.textContent='';
    drawChips();loadList();paint();arm();
   }catch(e){if(alive)status.textContent=e.message;}
  },220);
 });

 function resize(){
  const w=parent.clientWidth,hgt=parent.clientHeight;
  if(w<2||hgt<2)return;
  const weak=(navigator.hardwareConcurrency||2)<=2;
  const dpr=Math.min(window.devicePixelRatio||1,weak?1:1.35);
  if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(hgt*dpr)){
   canvas.width=Math.round(w*dpr);canvas.height=Math.round(hgt*dpr);
   plate=null;
  }
  view={w,h:hgt,dpr};
  paint(performance.now());
  if(alive)parent.dataset.nebula='ready';
 }
 const ro=new ResizeObserver(()=>resize());
 ro.observe(parent);

 function arm(){
  if(timer)return;
  const step=()=>{
   timer=0;
   if(!alive)return;
   const now=performance.now();
   paint(now);
   const flashing=state.flash&&motionOn()&&now-state.flash.t0<1400;
   if(motionOn()||flashing)timer=setTimeout(step,100);
  };
  timer=setTimeout(step,motionOn()?100:0);
 }
 function onFlash(e){
  if(!alive||!still())return;
  const data=e.detail||{};
  if(!data.id){load();return;}
  const star={...data,id:data.id,soort:data.soort||'notitie',helderheid:data.helderheid??1,bijgewerkt:data.bijgewerkt||Date.now()/1000};
  const i=state.stars.findIndex(s=>s.id===star.id);
  if(i>=0)state.stars[i]=star;else state.stars.unshift(star);
  state.stars.sort((a,b)=>(b.bijgewerkt||0)-(a.bijgewerkt||0));
  if(state.stars.length>STAR_CAP)state.stars.length=STAR_CAP;
  state.flash={id:star.id,t0:performance.now()};
  call('brein.links').then(r=>{if(alive&&r)state.lines=r.lijnen||state.lines;paint();}).catch(()=>{});
  paint();arm();
 }
 addEventListener('universe:brein-flash',onFlash);
 const onVis=()=>arm();
 document.addEventListener('visibilitychange',onVis);
 const mo=new MutationObserver(()=>arm());
 mo.observe(document.documentElement,{attributes:true,attributeFilter:['class']});

 if(api.data){applyData(api.data);resize();if(alive)parent.dataset.nebula='ready';}
 else load();
 resize();
 listBtn.addEventListener('click',()=>{
  const open=list.hasAttribute('hidden');
  list.toggleAttribute('hidden',!open);
  listBtn.setAttribute('aria-pressed',open?'true':'false');
  listBtn.textContent=open?'Lijst':'Nevel';
 });
 if(api.focus!==false)search.focus({preventScroll:true});
 arm();

 return ()=>{
  alive=false;clearTimeout(timer);clearTimeout(searchTimer);
  removeEventListener('universe:brein-flash',onFlash);
  document.removeEventListener('visibilitychange',onVis);
  ro.disconnect();mo.disconnect();
 };
}
