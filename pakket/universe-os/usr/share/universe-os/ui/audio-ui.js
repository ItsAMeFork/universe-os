import {call,h} from './api.js';
const kinds={hdmi:'HDMI/DisplayPort',analog:'Luidsprekers / audioaansluiting',usb:'USB',bluetooth:'Bluetooth',other:'Geluidsuitgang'};
export function audioView(){
 const root=h('div'),label=h('label',{},'Geluidsuitgang'),select=h('select',{'aria-label':'Geluidsuitgang'}),message=h('p',{role:'status'});
 const apply=h('button',{type:'button'},'Deze uitgang gebruiken'),refresh=h('button',{type:'button'},'Uitgangen vernieuwen');
 let outputs=[],busy=false;
 function show(state){outputs=state.outputs||[];select.replaceChildren();for(const o of outputs)select.append(h('option',{value:String(o.id)},`${o.active?'Actief · ':''}${o.description} · ${kinds[o.kind]||kinds.other}`));
  const active=outputs.find(o=>o.active);select.value=active?String(active.id):'';
  message.textContent=!outputs.length?'Geen geluidsapparaat gevonden.':active?`Actief: ${active.description}`:'Geen actieve standaarduitgang gevonden. Kies een uitgang.';
 }
 async function work(action){if(busy)return;busy=true;apply.disabled=refresh.disabled=select.disabled=true;message.textContent='Geluidsuitgangen controleren…';
  try{show(await action());}catch(e){message.textContent=e.message;}
  finally{busy=false;refresh.disabled=false;select.disabled=!outputs.length;apply.disabled=!outputs.length;}
 }
 refresh.addEventListener('click',()=>work(()=>call('audio.outputs')));
 apply.addEventListener('click',()=>{const target=outputs.find(o=>String(o.id)===select.value);if(!target){message.textContent='Kies een geluidsuitgang.';return;}work(()=>call('audio.select',{id:target.id,name:target.name}));});
 label.append(select);root.append(label,apply,refresh,message,h('p',{class:'small muted'},'De keuze wordt door WirePlumber bewaard. Ontbreekt een uitgang? Controleer het kaartprofiel bij Apparaten beheren.'));work(()=>call('audio.outputs'));return root;
}
