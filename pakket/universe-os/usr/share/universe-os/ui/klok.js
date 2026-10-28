// 0.3.3 (Axel, 28 Oct): the clock on the Earth of the login screen, time big and the date small below it. Since 0.3.3
// locking also shows the login screen, so this is the clock of the lock screen too.
// Names written out: the greeter's WebKit must not depend on locale data being installed.
const DAGEN=['zondag','maandag','dinsdag','woensdag','donderdag','vrijdag','zaterdag'];
const MAANDEN=['januari','februari','maart','april','mei','juni','juli','augustus','september','oktober','november','december'];
const twee=n=>String(n).padStart(2,'0');

export function klokTekst(d){
 return {tijd:twee(d.getHours())+':'+twee(d.getMinutes()),datum:DAGEN[d.getDay()]+' '+d.getDate()+' '+MAANDEN[d.getMonth()]};
}

/** Shows the time in `tijdEl` and the date in `datumEl`. Checks every second instead of waiting for the next minute:
 * a timer does not run during sleep, so after waking up the clock is right within a second. Writes only on change.
 * Returns stop(). */
export function startKlok(tijdEl,datumEl,{now=()=>new Date(),every=setInterval,clear=clearInterval}={}){
 const zet=(el,tekst)=>{if(el&&el.textContent!==tekst)el.textContent=tekst;};
 const tik=()=>{const {tijd,datum}=klokTekst(now());zet(tijdEl,tijd);zet(datumEl,datum);};
 tik();
 const id=every(tik,1000);
 return ()=>clear(id);
}
