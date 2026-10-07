// A slider sends the newest value, with at most one system call in flight.
export function latestValue(work,onError,delay=80){
 let next,active=false,timer;
 async function send(){
  if(active||next===undefined)return;
  const value=next;next=undefined;active=true;
  try{await work(value);}catch(e){onError(e);}
  finally{active=false;if(next!==undefined){clearTimeout(timer);timer=setTimeout(send,delay);}}
 }
 return value=>{next=value;clearTimeout(timer);timer=setTimeout(send,delay);};
}
