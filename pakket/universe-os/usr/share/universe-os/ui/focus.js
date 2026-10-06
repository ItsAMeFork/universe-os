// Trap Tab only inside an open dialog; native arrows/text editing remain untouched.
export function nextBoundary(list,current,backwards){
 if(!list.length)return null;
 if(!list.includes(current))return backwards?list.at(-1):list[0];
 if(backwards&&current===list[0])return list.at(-1);
 if(!backwards&&current===list.at(-1))return list[0];
 return null;
}
export function keepTab(event,container){
 if(event.key!=='Tab'||container.hidden)return;
 const list=[...container.querySelectorAll('button,input,select,textarea,a[href],[tabindex]')]
  .filter(el=>!el.disabled&&el.tabIndex>=0&&!el.closest('[hidden],[inert]')&&el.getClientRects().length);
 const next=nextBoundary(list,document.activeElement,event.shiftKey);
 if(next){event.preventDefault();next.focus();}
}
