// Classic script: must run even when the module graph cannot be parsed or loaded.
// Timeout 30 s: a first start without GPU took ~14 s on real hardware (B16 test), 5 s showed a false alarm.
(()=>{
 const page=document.currentScript.dataset.page||'world';
 let ready=false,notice=null,reported=0;
 const report=message=>{
  console.error('[Universe UI '+page+'] '+message);
  if(reported++>=5)return;
  try{window.webkit.messageHandlers.universe.postMessage(JSON.stringify({id:-1,cmd:'ui.error',args:{page,message:String(message).slice(0,1500)}}));}catch{}
 };
 const show=()=>{
  if(notice)return;
  notice=document.createElement('section');notice.setAttribute('role','alert');notice.tabIndex=-1;
  notice.style.cssText='position:fixed;inset:8px;z-index:2147483647;background:#0b1021;color:#e2e6fa;border:2px solid #85ffe3;border-radius:12px;padding:16px;overflow:auto;font:16px sans-serif';
  const title=document.createElement('h1');title.textContent=page==='panel'?'Het bedieningspaneel kon niet laden':'De ruimtewereld kon niet laden';
  const help=document.createElement('p');help.textContent='Druk op Ctrl+Alt+T om een terminal te openen en voer universe-ctl reload uit. Of meld je hieronder af; niet-opgeslagen werk kan verloren gaan.';
  const retry=document.createElement('button');retry.textContent='Opnieuw proberen';retry.onclick=()=>location.reload();
  let confirmLogout=false;
  const logout=document.createElement('button');logout.textContent='Afmelden';logout.onclick=()=>{if(!confirmLogout){confirmLogout=true;logout.textContent='Ja, afmelden';help.textContent='Niet-opgeslagen werk kan verloren gaan. Klik nogmaals om af te melden.';return;}try{window.webkit.messageHandlers.universe.postMessage(JSON.stringify({id:-3,cmd:'power',args:{action:'logout'}}));}catch{help.textContent='Afmelden lukt niet. Open een terminal met Ctrl+Alt+T.';}};
  notice.append(title,help,retry,logout);document.body.append(notice);notice.focus();
  if(page==='panel')try{window.webkit.messageHandlers.universe.postMessage(JSON.stringify({id:-2,cmd:'surface.size',args:{name:'panel',open:true}}));}catch{}
 };
 window.__universePageReady=()=>{ready=true;clearTimeout(timer);notice?.remove();notice=null;};
 window.addEventListener('error',event=>{report(event.message||'Een scriptbestand kon niet laden');if(!ready)show();},true);
 window.addEventListener('unhandledrejection',event=>{report(event.reason?.message||String(event.reason));if(!ready)show();});
 const timer=setTimeout(()=>{if(!ready){report('Geen gereedmelding binnen 30 seconden');show();}},30000);
})();
