// Bridge between the web interface and the Universe shell (Python, universe_shell.py).
// Every system action goes through call(); the shell answers with __universeReply and pushes events with __universeEvent.
const pending=new Map();let next=1;
window.__universeReply=(id,ok,data)=>{const p=pending.get(id);if(!p)return;pending.delete(id);ok?p.resolve(data):p.reject(new Error(data||'Onbekende fout'));};
window.__universeEvent=(name,data)=>dispatchEvent(new CustomEvent('universe:'+name,{detail:data}));
export const available=!!window.webkit?.messageHandlers?.universe;
export function call(cmd,args={}){
 if(!available)return Promise.reject(new Error('Geen verbinding met de Universe-shell'));
 return new Promise((resolve,reject)=>{const id=next++;pending.set(id,{resolve,reject});window.webkit.messageHandlers.universe.postMessage(JSON.stringify({id,cmd,args}));});
}
export const on=(name,fn)=>addEventListener('universe:'+name,e=>fn(e.detail));

/** Applies the user's display settings (animations, text size, colours) to this page. */
export function applySettings(s){
 const root=document.documentElement;
 root.classList.toggle('reduce-motion',s.animations==='reduced');
 root.classList.toggle('no-motion',s.animations==='off');
 root.style.setProperty('--text-scale',String((s.textScale||100)/100));
 if(s.colors)for(const [k,v] of Object.entries(s.colors))root.style.setProperty('--'+k.replace(/[A-Z]/g,c=>'-'+c.toLowerCase()),v);
}
export const motionAllowed=s=>s.animations==='full'&&!matchMedia('(prefers-reduced-motion: reduce)').matches;

export function toast(text,ms=3500){
 const el=document.createElement('div');el.className='toast glass';el.setAttribute('role','status');el.textContent=text;document.body.append(el);setTimeout(()=>el.remove(),ms);
}
export const h=(tag,props={},...kids)=>{
 const el=document.createElement(tag);
 for(const [k,v] of Object.entries(props||{})){
  if(v==null||v===false)continue;
  if(k==='class')el.className=v;else if(k.startsWith('on'))el.addEventListener(k.slice(2),v);else if(k==='html')el.innerHTML=v;else el.setAttribute(k,v===true?'':v);
 }
 for(const kid of kids.flat())if(kid!=null&&kid!==false)el.append(kid instanceof Node?kid:document.createTextNode(String(kid)));
 return el;
};
/** Small line icons (own drawings, so nothing has to be downloaded). */
const PATHS={
 wifi:'<path d="M5 12.5a10 10 0 0 1 14 0"/><path d="M8.5 16a5 5 0 0 1 7 0"/><circle cx="12" cy="19.5" r=".8"/><path d="M1.5 9a15 15 0 0 1 21 0"/>',
 wired:'<rect x="9" y="3" width="6" height="5" rx="1"/><path d="M12 8v4M5 12h14M5 12v4M19 12v4M12 12v4"/><rect x="3" y="16" width="4" height="4"/><rect x="10" y="16" width="4" height="4"/><rect x="17" y="16" width="4" height="4"/>',
 offline:'<path d="M2 2l20 20"/><path d="M8.5 16a5 5 0 0 1 7 0"/><path d="M5 12.5a10 10 0 0 1 4-2.3"/><path d="M14.5 10.3A10 10 0 0 1 19 12.5"/>',
 volume:'<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a10 10 0 0 1 0 14"/>',
 mute:'<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M22 9l-6 6M16 9l6 6"/>',
 battery:'<rect x="2" y="7" width="18" height="10" rx="2"/><path d="M22 11v2"/>',
 bell:'<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/>',
 lock:'<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
 logout:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5M21 12H9"/>',
 restart:'<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
 power:'<path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.8 0"/>',
 sleep:'<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
 search:'<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
 close:'<path d="M18 6 6 18M6 6l12 12"/>',
 minimize:'<path d="M5 12h14"/>',
 back:'<path d="M15 18l-6-6 6-6"/>',
 planet:'<circle cx="12" cy="12" r="6"/><path d="M3 15c3 3 15-3 18-6"/>',
 folder:'<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
 file:'<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
 gear:'<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"/>',
 user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
 windows:'<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M3 8h18"/>',
 download:'<path d="M12 3v12M7 10l5 5 5-5"/><path d="M5 21h14"/>',
 rocket:'<path d="M5 15c-1.5 1.3-2 5-2 5s3.7-.5 5-2c.7-.8.7-2.1-.1-2.9a2.2 2.2 0 0 0-2.9-.1z"/><path d="M12 15l-3-3a22 22 0 0 1 2-4A12.9 12.9 0 0 1 22 2c0 2.7-.8 7.5-6 11a22.4 22.4 0 0 1-4 2z"/>',
 chat:'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
 game:'<rect x="2" y="7" width="20" height="11" rx="5"/><path d="M7 11v3M5.5 12.5h3"/><circle cx="16" cy="11.5" r=".8"/><circle cx="18" cy="13.5" r=".8"/>',
 store:'<path d="M4 7h16l-1.5 12a2 2 0 0 1-2 1.8h-9A2 2 0 0 1 5.5 19z"/><path d="M9 7a3 3 0 0 1 6 0"/>',
 grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
 keyboard:'<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
 display:'<rect x="2" y="4" width="20" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
 bluetooth:'<path d="M7 7l10 10-5 5V2l5 5L7 17"/>',
 globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 shield:'<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
 info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/>',
 update:'<path d="M21 12a9 9 0 0 1-15.4 6.4L3 16"/><path d="M3 12a9 9 0 0 1 15.4-6.4L21 8"/><path d="M21 3v5h-5M3 21v-5h5"/>',
 mouse:'<rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 7v4"/>'
};
export function icon(name,cls='icon'){const s=document.createElementNS('http://www.w3.org/2000/svg','svg');s.setAttribute('viewBox','0 0 24 24');s.setAttribute('class',cls);s.setAttribute('aria-hidden','true');s.innerHTML=PATHS[name]||PATHS.planet;return s;}
