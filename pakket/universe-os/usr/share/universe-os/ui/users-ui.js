// Gebruikers: overzicht (alleen naam + planeet) en accountinstellingen voor wie bevoegd is.
// Beheerder: iedereen; normale gebruiker: alleen zichzelf. De helper controleert dit zelf nog eens.
import {call as shellCall, h} from './api.js';
import {fotoKaart} from './profielfoto-ui.js';

const COLORS={aarde:'#2f7fd8,#1d8f5a',mars:'#e07a4f,#8a2f1c',jupiter:'#e3c08c,#a8643a',saturnus:'#f0dca0,#b89a58',
 neptunus:'#6aa0ff,#2a3d9e',venus:'#f3d88a,#c98a3a',maan:'#e6e6ea,#8a8a94',zon:'#ffe27a,#e8731a'};
export const planetStyle=id=>`background:radial-gradient(circle at 35% 30%,${(COLORS[id]||COLORS.aarde).split(',')[0]},${(COLORS[id]||COLORS.aarde).split(',')[1]});`;

const note=t=>h('p',{class:'muted'},t);
const card=(title,...items)=>h('section',{class:'card'},h('h3',{},title),...items);
const field=(title,input)=>h('label',{},title,input);
const input=(type='text',value='')=>h('input',{type,value,autocomplete:type==='password'?'off':undefined});
const check=title=>{const i=input('checkbox');return {node:h('label',{class:'check'},i,title),i};};

function button(title,action){
 const message=h('p',{class:'message',role:'status'}),b=h('button',{type:'button'},title);
 b.addEventListener('click',async()=>{
  b.disabled=true;message.className='message';message.textContent='Bezig…';
  try{const outcome=await action();message.textContent=typeof outcome==='string'?outcome:'Gelukt.';}
  catch(e){message.className='message error';message.textContent=e.message||'Mislukt.';}
  finally{b.disabled=false;}
 });
 return h('div',{},b,message);
}

function passwordCard(call,title,own,name){
 const old=input('password'),pw=input('password'),repeat=input('password');
 return card(title,...(own?[field('Huidig wachtwoord',old)]:[]),field('Nieuw wachtwoord',pw),field('Herhaal nieuw wachtwoord',repeat),
  button('Wachtwoord wijzigen',async()=>{
   if(pw.value.length<6||pw.value!==repeat.value)throw Error('Gebruik minstens 6 tekens en twee gelijke wachtwoorden.');
   const payload=own?{current:old.value,new:pw.value}:{name,password:pw.value};
   old.value=pw.value=repeat.value='';
   await call(own?'account.password':'users.password',payload);
   return 'Wachtwoord gewijzigd.';
  }));
}

/**
 * @param {HTMLElement} root
 * @param {{call?:Function, isAdmin?:boolean, reload?:Function}} api
 */
export async function mountUsers(root, api={}){
 const call=api.call||shellCall;
 const overview=h('div',{class:'user-planets',role:'list'});
 const settings=h('div');
 const status=h('p',{class:'message',role:'status'});
 let list=[];

 async function open(name){
  status.className='message';status.textContent='';
  let d;
  try{d=await call('users.detail',{name});}
  catch(e){settings.replaceChildren();status.className='message error';status.textContent=e.message||'Geen toestemming om dit account te beheren.';return;}
  const cards=[];
  const full=input('text',d.fullName||'');
  cards.push(card(`Account van ${d.name}`,
   note(`${d.name} · ${d.admin?'Beheerder':'Standaardaccount'}${d.me?' · Jij':''}`),
   field('Weergavenaam',full),
   button('Naam opslaan',async()=>{await call('users.fullname',{name:d.name,fullName:full.value});await refresh(d.name);return 'Naam opgeslagen.';})));
  if(d.me){
   const picker=h('div',{class:'user-planets'});
   for(const id of d.planets||[]){
    const b=h('button',{type:'button',class:'user-planet'+(id===d.planet?' selected':''),'aria-label':'Planeet '+id,'aria-pressed':String(id===d.planet),draggable:'false'},
     h('span',{class:'orb',style:planetStyle(id)}),h('span',{},id));
    b.addEventListener('click',async()=>{await call('users.planet',{planet:id});await refresh(d.name);});
    picker.append(b);
   }
   cards.push(card('Mijn planeet',note('Je persoonlijke planeet. Die verschijnt in het gebruikersoverzicht.'),picker));
   cards.push(fotoKaart({call,h,photo:d.photo||null,orb:planetStyle(d.planet),onChange:()=>refresh(d.name)})); // 0.3.4
   cards.push(passwordCard(call,'Eigen wachtwoord',true,d.name));
  }else{
   cards.push(passwordCard(call,`Wachtwoord van ${d.name}`,false,d.name));
  }
  if(api.isAdmin){
   const verify=input('text'),removeHome=check('Persoonlijke bestanden ook verwijderen (onomkeerbaar)');
   cards.push(card(`Beheer ${d.name}`,
    button(d.admin?'Standaardaccount maken':'Beheerder maken',async()=>{await call('users.admin',{name:d.name,admin:!d.admin});await refresh(d.name);return 'Accounttype gewijzigd.';}),
    ...(d.me?[note('Je kunt je eigen account niet verwijderen of je eigen beheerdersrechten intrekken.')]:[
     field(`Typ ${d.name} om verwijderen te bevestigen`,verify),removeHome.node,
     button('Account verwijderen',async()=>{
      if(verify.value!==d.name)throw Error('Bevestig de exacte accountnaam.');
      await call('users.remove',{name:d.name,deleteHome:removeHome.i.checked});
      settings.replaceChildren();await refresh();return 'Account verwijderd.';
     })])));
  }
  settings.replaceChildren(...cards);
 }

 async function refresh(keep){
  list=await call('users.list');
  overview.replaceChildren();
  for(const u of list){
   const b=h('button',{type:'button',class:'user-planet'+(u.me?' me':''),role:'listitem','aria-label':`${u.fullName||u.name}${u.me?' (jij)':''}`,draggable:'false'},
    h('span',{class:'orb',style:planetStyle(u.planet)}),h('span',{class:'user-name'},u.fullName||u.name));
   b.addEventListener('click',()=>open(u.name));
   overview.append(b);
  }
  if(keep) await open(keep);
 }

 root.append(card('Gebruikers',note('Kies een planeet om de instellingen van dat account te openen. Een beheerder beheert iedereen, een standaardaccount alleen zichzelf.'),overview,status),settings);

 if(api.isAdmin){
  const name=input(),full=input(),pw=input('password'),repeat=input('password'),admin=check('Beheerder');
  root.append(card('Nieuw account',field('Gebruikersnaam',name),field('Volledige naam',full),field('Wachtwoord',pw),field('Herhaal wachtwoord',repeat),admin.node,
   button('Account toevoegen',async()=>{
    if(!/^[a-z_][a-z0-9_-]{0,31}$/.test(name.value))throw Error('Gebruik een geldige gebruikersnaam in kleine letters.');
    if(pw.value.length<6||pw.value!==repeat.value)throw Error('Gebruik minstens 6 tekens en twee gelijke wachtwoorden.');
    const password=pw.value;pw.value=repeat.value='';
    await call('users.add',{name:name.value,fullName:full.value,password,admin:admin.i.checked});
    await refresh();return 'Account toegevoegd.';
   })));
 }else root.append(note('Nieuwe accounts maken en andere accounts beheren vereist een beheerder.'));
 await refresh();
 root.dataset.users='ready';
}
