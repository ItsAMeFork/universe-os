// 0.2.38 sterrenhemel.js: één pad met kwaliteitsparameter; lichte modus = dezelfde hemel, minder detail.
// node docs/tests/sterrenhemel.mjs
const rec=()=>{const calls={};return new Proxy({calls},{get(t,k){if(k==='calls')return calls;if(k==='createRadialGradient'||k==='createLinearGradient')return()=>({addColorStop(){}});return(...a)=>{calls[k]=(calls[k]||0)+1;};},set(){return true;}});};
const canvas=(w=0,h=0)=>{const c={width:w,height:h,ctx:rec(),getContext(){return this.ctx;}};return c;};
globalThis.location={search:''};globalThis.navigator={hardwareConcurrency:8};globalThis.devicePixelRatio=1;
globalThis.document={createElement:()=>canvas(),hidden:false,documentElement:{classList:{add(){}}}};
globalThis.innerWidth=1280;globalThis.innerHeight=720;globalThis.performance={now:()=>0};
const S=await import('../../pakket/universe-os/usr/share/universe-os/ui/sterrenhemel.js');
let fails=0;const check=(n,ok)=>{console.log((ok?'OK   ':'FOUT ')+n);if(!ok)fails++;};
const vol=S.sterrenVoor(false),licht=S.sterrenVoor(true);
check(`veel sterren (${vol.length}), licht een derde (${licht.length})`,vol.length>=9000&&Math.abs(licht.length-vol.length/3)<2);
check('lichte modus: dezelfde sterren (deelverzameling, zelfde plek/kleur)',licht.every(s=>vol.includes(s)));
check('drie dieptelagen en vijf temperatuurkleuren',new Set(vol.map(s=>s[5])).size===3&&new Set(vol.map(s=>s[4])).size===5);
const zwak=vol.filter(s=>s[3]<.4).length,fel=vol.filter(s=>s[3]>.8).length;
check(`echt: veel zwakke (${zwak}), weinig felle sterren (${fel})`,zwak>fel*5);
const cam={yaw:-.5,pitch:.42,dist:1650,tx:0,ty:0,tz:0},s0=vol.find(s=>s[5]===2&&S.sterPunt(s,cam,1280,720)),f0=vol.find(s=>s[5]===0&&S.sterPunt(s,cam,1280,720));
const moved={...cam,tx:400},a=S.sterPunt(s0,cam,1280,720),b=S.sterPunt(s0,moved,1280,720),c=S.sterPunt(f0,cam,1280,720),d=S.sterPunt(f0,moved,1280,720);
check('parallax: nabije laag schuift mee, verre laag niet',Math.hypot(a.x-b.x,a.y-b.y)>2&&Math.hypot(c.x-d.x,c.y-d.y)<1e-9);
check('twinkelen: nooit helemaal donker, wel variatie',[...Array(200)].every((_,i)=>S.twinkel(i%30,i*.1)>.2)&&new Set([...Array(50)].map((_,i)=>S.twinkel(3,i*.3).toFixed(2))).size>10);
check('lichte modus: minder twinkelsterren en lagere fps',S.KWALITEIT.licht.twinkel<S.KWALITEIT.vol.twinkel&&S.KWALITEIT.licht.fps<S.KWALITEIT.vol.fps&&S.KWALITEIT.licht.fps>0);
const nv=S.nevelTextuur(false),nl=S.nevelTextuur(true);
check('nevel: lichte modus kleinere textuur, zelfde opbouw',nl.width<nv.width&&nl.width/nl.height===nv.width/nv.height);
const c1=rec();S.tekenSterren(c1,cam,1280,720,{licht:false});const c2=rec();S.tekenSterren(c2,cam,1280,720,{licht:true});
check('tekenen: licht minder werk',c2.calls.arc<c1.calls.arc&&c2.calls.arc>100);
const c3=rec();S.tekenSterren(c3,cam,1280,720,{licht:true,warp:.8});
check('warp: sterren worden lichtstrepen (ook licht)',(c3.calls.lineTo||0)>100&&!c3.calls.arc);
const src=(await import('node:fs')).readFileSync(new URL('../../pakket/universe-os/usr/share/universe-os/ui/sterrenhemel.js',import.meta.url),'utf8');
check('geen filters/blur',!/\.filter\s*=|blur/i.test(src.replace(/^\/\/.*$/mg,'')));
process.exit(fails?1:0);
