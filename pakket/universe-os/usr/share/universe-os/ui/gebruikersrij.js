// Gebruikersplaneten-rij op het inlogscherm: kleine planeten met de naam eronder, vast en nooit versleepbaar.
// indeling() is puur rekenwerk (testbaar zonder DOM); gebruikersRij() bouwt de knoppen en regelt selectie en toetsen.
const LABEL=26,GAP=10;
// n planeten in een vak van w×h px: kies het aantal rijen waarbij de planeten het grootst blijven (1 rij bij weinig,
// meerdere rijen bij veel gebruikers), centreer elke rij en buig een rij licht (midden iets lager dan de randen).
export function indeling(n,w,h,{maxD=88,minD=14}={}){
 n=Math.max(0,n|0);w=Math.max(1,w);h=Math.max(1,h);
 if(!n)return{d:0,rijen:0,perRij:[],items:[],hoogte:0};
 const reserve=Math.min(h*.2,maxD*.2);
 let best=null;
 for(let r=1;r<=n;r++){
  const per=Math.ceil(n/r),d=Math.max(minD,Math.min(maxD,Math.floor(w/per*.8),Math.floor((h-reserve)/r-LABEL-GAP)));
  if(!best||d>best.d)best={d,r,per};
  if(per===1)break;
 }
 const{d,r,per}=best,rijHoogte=d+LABEL+GAP,arc=r===1?d*.18:d*.1,stapX=Math.min(w/per,d*1.6),basis=Math.floor(n/r),extra=n%r;
 const perRij=[],items=[];let index=0;
 for(let k=0;k<r;k++){
  const aantal=basis+(k<extra?1:0);perRij.push(aantal);
  for(let i=0;i<aantal;i++){
   const dx=(i-(aantal-1)/2)*stapX,t=Math.min(1,Math.abs(dx)/(w/2));
   items.push({index:index++,rij:k,x:Math.round((w/2+dx)*10)/10,y:Math.round((k*rijHoogte+d/2+arc*(1-t*t))*10)/10});
  }
 }
 return{d,rijen:r,perRij,items,hoogte:Math.ceil(r*rijHoogte+arc)};
}
const tint=naam=>{let h=7;for(const c of naam)h=(h*31+c.charCodeAt(0))>>>0;return h%360;};
// host: lege container; opties.onKies(naam), opties.onBevestig(naam), opties.doc (standaard document).
// Alleen click en toetsen: geen pointer-/mouse-/touchhandlers voor slepen, geen drag; selectie loopt alleen via kies().
export function gebruikersRij(host,{onKies=()=>{},onBevestig=()=>{},doc=globalThis.document}={}){
 let lijst=[],gekozen=-1,maat={w:0,h:0};
 const knoppen=[];
 host.setAttribute('role','radiogroup');host.setAttribute('aria-label','Gebruikers');
 host.addEventListener('dragstart',e=>e.preventDefault());
 host.addEventListener('selectstart',e=>e.preventDefault());
 host.addEventListener('keydown',e=>{
  const sleutel=e.key;
  if(sleutel==='Enter'){if(gekozen>=0){e.preventDefault();onBevestig(lijst[gekozen].naam);}return;}
  const stap={ArrowRight:1,ArrowDown:1,ArrowLeft:-1,ArrowUp:-1}[sleutel];
  if(!stap||!lijst.length)return;
  e.preventDefault();kies(gekozen<0?(stap>0?0:lijst.length-1):(gekozen+stap+lijst.length)%lijst.length,true);
 });
 function kies(i,focus=false){
  if(i<0||i>=lijst.length)return;
  gekozen=i;
  knoppen.forEach((k,j)=>{const aan=j===i;k.setAttribute('aria-checked',String(aan));k.tabIndex=aan?0:-1;k.parentNode.classList.toggle('gekozen',aan);});
  if(focus)knoppen[i].focus();
  onKies(lijst[i].naam);
 }
 function plaats(){
  const lay=indeling(lijst.length,maat.w,maat.h);
  host.style.setProperty('--d',lay.d+'px');host.style.height=lay.hoogte+'px';
  lay.items.forEach(it=>{const li=knoppen[it.index].parentNode;li.style.width=lay.d+'px';li.style.transform=`translate(${(it.x-lay.d/2).toFixed(1)}px,${(it.y-lay.d/2).toFixed(1)}px)`;});
  return lay;
 }
 return{
  zetGebruikers(nieuw,voorkeur=''){
   lijst=nieuw.map(g=>typeof g==='string'?{naam:g,weergave:g}:{naam:g.naam,weergave:g.weergave||g.naam});
   knoppen.length=0;host.replaceChildren();gekozen=-1;
   lijst.forEach((g,i)=>{
    const li=doc.createElement('div'),knop=doc.createElement('button'),planeet=doc.createElement('span'),naam=doc.createElement('span');
    li.className='gebruiker';li.style.setProperty('--tint',tint(g.naam));
    knop.type='button';knop.draggable=false;knop.setAttribute('draggable','false');knop.setAttribute('role','radio');knop.setAttribute('aria-checked','false');knop.tabIndex=i===0?0:-1;
    knop.setAttribute('aria-label',g.weergave);
    planeet.className='kleinplaneet';planeet.setAttribute('aria-hidden','true');naam.className='naam';naam.textContent=g.weergave;
    knop.addEventListener('click',()=>{kies(i);onBevestig(g.naam);});
    knop.append(planeet,naam);li.append(knop);host.append(li);knoppen.push(knop);
   });
   if(maat.w)plaats();
   const start=lijst.findIndex(g=>g.naam===voorkeur);
   if(start>=0)kies(start);else if(lijst.length===1)kies(0);
   return lijst.length;
  },
  grootte(w,h){maat={w,h};return lijst.length?plaats():null;},
  kies:i=>kies(i),
  gekozenNaam:()=>gekozen>=0?lijst[gekozen].naam:'',
  aantal:()=>lijst.length,
 };
}
