// Klus g1: gebruikersplaneten-rij op het inlogscherm (ui/gebruikersrij.js): indeling bij 1/2/8/20 gebruikers,
// selectie met klik en pijltjes + Enter, en slepen verandert de positie niet. Eenvoudige DOM-stub, geen browser nodig.
// node docs/tests/gebruikersrij.mjs
import {readFileSync} from 'node:fs';
const UI='../../pakket/universe-os/usr/share/universe-os/ui/';
const {indeling,gebruikersRij}=await import(UI+'gebruikersrij.js');
let fails=0;const check=(n,ok)=>{console.log((ok?'OK   ':'FOUT ')+n);if(!ok)fails++;};

class El{
 constructor(tag){this.tag=tag;this.children=[];this.parentNode=null;this.attrs={};this.props=new Map();this.handlers={};this.className='';this.classes=new Set();this.textContent='';this.tabIndex=0;
  this.style={setProperty:(k,v)=>this.props.set(k,v)};this.classList={toggle:(c,on)=>{on?this.classes.add(c):this.classes.delete(c);}};}
 setAttribute(k,v){this.attrs[k]=String(v);}
 addEventListener(t,f){(this.handlers[t]??=[]).push(f);}
 append(...k){k.forEach(c=>{c.parentNode=this;this.children.push(c);});}
 replaceChildren(){this.children=[];}
 focus(){El.fokus=this;}
 fire(type,init={}){const e={type,defaultPrevented:false,preventDefault(){this.defaultPrevented=true;},...init};(this.handlers[type]||[]).forEach(f=>f(e));return e;}
}
const doc={createElement:t=>new El(t)};
const namen=n=>Array.from({length:n},(_,i)=>'gebruiker'+(i+1));
const maak=(n,w=1100,h=240,voorkeur='')=>{
 const host=new El('nav'),log={kies:[],bevestig:[]};
 const rij=gebruikersRij(host,{doc,onKies:x=>log.kies.push(x),onBevestig:x=>log.bevestig.push(x)});
 rij.zetGebruikers(namen(n),voorkeur);const lay=rij.grootte(w,h);return{host,rij,log,lay};
};
const li=h=>h.children,knop=l=>l.children[0];

// 1. indeling bij 1, 2, 8 en 20 gebruikers (breed scherm en smal scherm)
for(const [n,w,h] of [[1,1100,240],[2,1100,240],[8,1100,240],[20,1100,240],[1,360,200],[2,360,200],[8,360,200],[20,360,200],[20,1920,260],[50,1100,240]]){
 const L=indeling(n,w,h),per=L.perRij,somt=per.reduce((a,b)=>a+b,0);
 const binnen=L.items.every(i=>i.x-L.d/2>=-.5&&i.x+L.d/2<=w+.5&&i.y-L.d/2>=-.5);
 const ruimte=L.items.every(a=>L.items.every(b=>a===b||Math.hypot(a.x-b.x,a.y-b.y)>=L.d*1.0));
 check(`${n} gebruikers in ${w}×${h}: ${L.rijen} rij(en) ${JSON.stringify(per)}, d=${L.d}px — allemaal getoond, binnen het vak, niet overlappend, hoogte ${L.hoogte}≤${h}`,somt===n&&L.items.length===n&&binnen&&ruimte&&L.hoogte<=h);
}
const een=indeling(1,1100,240),twee=indeling(2,1100,240),acht=indeling(8,1100,240),twintig=indeling(20,1100,240);
check('1 en 2 gebruikers: één rij, gecentreerd, groot',een.rijen===1&&twee.rijen===1&&Math.abs(een.items[0].x-550)<1&&Math.abs((twee.items[0].x+twee.items[1].x)/2-550)<1&&een.d>=80);
check('1 gebruiker: planeet in het midden; 2 gebruikers: symmetrisch',Math.abs(twee.items[0].x-550+(twee.items[1].x-550))<1);
check('8 gebruikers: nog één rij (breed scherm)',acht.rijen===1&&acht.d>=60);
check('20 gebruikers: verdeeld over meerdere rijen en kleiner, rijen blijven in evenwicht',twintig.rijen>1&&twintig.d<acht.d&&Math.max(...twintig.perRij)-Math.min(...twintig.perRij)<=1);
check('schaalt mee: smal scherm geeft kleinere planeten dan breed',indeling(8,360,200).d<acht.d);
check('licht gebogen: midden van een rij ligt lager dan de randen',(()=>{const r=indeling(8,1100,240).items;return r[3].y>r[0].y&&r[4].y>r[7].y&&Math.abs(r[0].y-r[7].y)<1;})());
check('geen gebruikers: lege indeling',indeling(0,1000,200).items.length===0);

// 2. DOM: knoppen zijn niet versleepbaar en de rij blijft vast
for(const n of [1,2,8,20]){
 const{host,lay}=maak(n);const rijen=li(host);
 check(`${n} gebruikers: ${rijen.length} planeten met naam, draggable=false, rol radio`,rijen.length===n&&rijen.every((l,i)=>knop(l).draggable===false&&knop(l).attrs.draggable==='false'&&knop(l).attrs.role==='radio'&&l.children[0].children[1].textContent==='gebruiker'+(i+1)));
 check(`${n} gebruikers: elke planeet staat op de berekende plek (transform) en de hoogte past`,rijen.every((l,i)=>l.style.transform.includes(`${(lay.items[i].x-lay.d/2).toFixed(1)}px`))&&host.style.height===lay.hoogte+'px');
}

// 3. slepen verandert de positie niet
{
 const{host,rij}=maak(8);const voor=li(host).map(l=>l.style.transform),hoogte=host.style.height;
 const k=knop(li(host)[2]);
 const events=['pointerdown','mousedown','touchstart','pointermove','mousemove','touchmove','pointerup','mouseup','touchend','dragstart','drag','dragend','drop','selectstart'];
 const ev=events.map(t=>k.fire(t,{clientX:10,clientY:10,movementX:300,movementY:200,buttons:1}));
 host.fire('dragstart');
 const dragstart=host.fire('dragstart'),sel=host.fire('selectstart');
 check('slepen/aanraken: transform en hoogte van alle planeten ongewijzigd',li(host).every((l,i)=>l.style.transform===voor[i])&&host.style.height===hoogte);
 check('dragstart en selectstart worden geblokkeerd',dragstart.defaultPrevented&&sel.defaultPrevented);
 check('geen pointer-/mouse-/touch-/drag-handlers op de knoppen (alleen click)',Object.keys(k.handlers).join()==='click');
 check('slepen selecteert niets',rij.gekozenNaam()===''&&li(host).every(l=>!l.classes.has('gekozen')));
 const src=readFileSync(new URL(UI+'gebruikersrij.js',import.meta.url),'utf8').replace(/^\s*\/\/.*$/mg,'');
 check('broncode: geen handlers voor pointer/mouse/touch/drag',!/addEventListener\(\s*['"](pointer|mouse|touch|drag(?!start)|drop)/.test(src));
 const css=readFileSync(new URL(UI+'login.css',import.meta.url),'utf8');
 check('CSS: user-select:none en -webkit-user-drag:none',/#users button\{[^}]*user-select:none[^}]*-webkit-user-drag:none/.test(css));
}

// 4. selectie: klik, pijltjes, Enter
{
 const{host,rij,log}=maak(8);const k=i=>knop(li(host)[i]);
 k(3).fire('click');
 check('klik selecteert en bevestigt (focus naar wachtwoord)',rij.gekozenNaam()==='gebruiker4'&&li(host)[3].classes.has('gekozen')&&k(3).attrs['aria-checked']==='true'&&log.bevestig.at(-1)==='gebruiker4'&&log.kies.at(-1)==='gebruiker4');
 check('maar één planeet tegelijk gekozen',li(host).filter(l=>l.classes.has('gekozen')).length===1);
 host.fire('keydown',{key:'ArrowRight'});check('pijl rechts → volgende',rij.gekozenNaam()==='gebruiker5'&&El.fokus===k(4));
 host.fire('keydown',{key:'ArrowLeft'});host.fire('keydown',{key:'ArrowLeft'});check('pijl links → vorige',rij.gekozenNaam()==='gebruiker3');
 rij.kies(0);host.fire('keydown',{key:'ArrowLeft'});check('pijl links vanaf de eerste → laatste (rond)',rij.gekozenNaam()==='gebruiker8');
 const n0=log.bevestig.length,e=host.fire('keydown',{key:'Enter'});check('Enter bevestigt de gekozen gebruiker',log.bevestig.length===n0+1&&log.bevestig.at(-1)==='gebruiker8'&&e.defaultPrevented);
 check('alleen de gekozen planeet is tabbaar (roving tabindex)',li(host).filter((l,i)=>k(i).tabIndex===0).length===1&&k(7).tabIndex===0);
}
{
 const{host,rij}=maak(3);const n0=0;host.fire('keydown',{key:'Enter'});
 const{log}=maak(3);check('Enter zonder keuze doet niets',log.bevestig.length===n0);
 host.fire('keydown',{key:'ArrowRight'});check('eerste pijltoets zonder keuze kiest de eerste',rij.gekozenNaam()==='gebruiker1');
}
check('één gebruiker wordt automatisch gekozen; voorkeur (select-hint) wordt gekozen bij meer',maak(1).rij.gekozenNaam()==='gebruiker1'&&maak(8,1100,240,'gebruiker6').rij.gekozenNaam()==='gebruiker6'&&maak(8).rij.gekozenNaam()==='');
check('opnieuw indelen bij andere grootte (resize) zet alle planeten opnieuw',(()=>{const{host,rij}=maak(20);const a=li(host)[0].style.transform;rij.grootte(500,200);return li(host)[0].style.transform!==a&&li(host).length===20;})());
process.exit(fails?1:0);
