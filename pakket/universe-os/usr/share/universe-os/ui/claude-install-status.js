export async function waitForClaude({status,onInstalled,onMessage,alive=()=>true,delay=ms=>new Promise(r=>setTimeout(r,ms)),now=()=>Date.now(),limit=600000}){
 const until=now()+limit;
 while(alive()&&now()<until){
  await delay(Math.min(3000,until-now()));
  if(!alive())return 'closed';
  if(now()>=until)break;
  try{const s=await status();if(!alive())return 'closed';if(s?.installed===true){onInstalled(s);return 'installed';}onMessage('Installatie wordt gecontroleerd… Volg de stappen in de terminal.');}
  catch(e){if(!alive())return 'closed';onMessage('Statuscontrole mislukt: '+e.message+' Er wordt opnieuw geprobeerd.');}
 }
 if(alive())onMessage('Na 10 minuten is de installatie nog niet bevestigd. Controleer de terminal en open deze pagina opnieuw.');
 return alive()?'timeout':'closed';
}
