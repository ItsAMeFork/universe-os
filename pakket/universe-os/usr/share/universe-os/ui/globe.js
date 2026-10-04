// Planet globes, drawn like Space Chat's 2D universe (src/universe.js, globe()): a lit radial gradient,
// gas bands or rocky blotches, a soft terminator shadow and a thin coloured rim. Works without a GPU.
export function globe(seed,rock=false,size=320){
 const canvas=document.createElement('canvas');canvas.className='space-globe';canvas.width=canvas.height=size;canvas.setAttribute('aria-hidden','true');
 const c=canvas.getContext('2d');c.scale(size/320,size/320);
 const hue=((seed%360)+360)%360;
 const gradient=c.createRadialGradient(112,92,9,180,168,161);
 gradient.addColorStop(0,`hsl(${hue} 62% 75%)`);gradient.addColorStop(.42,`hsl(${hue} 49% 42%)`);gradient.addColorStop(.76,`hsl(${hue} 58% 18%)`);gradient.addColorStop(1,'#030714');
 c.save();c.beginPath();c.arc(160,160,146,0,Math.PI*2);c.clip();c.fillStyle=gradient;c.fillRect(0,0,320,320);
 let s=(seed*7919+13)>>>0||31;const rand=()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296;};
 if(rock){for(let i=0;i<40;i++){const x=rand()*320,y=rand()*320;c.fillStyle=i%2?'#061f4544':'#c7fce72a';c.beginPath();for(let n=0;n<10;n++){const a=n/10*Math.PI*2,r=12+rand()*40;const px=x+Math.cos(a)*r,py=y+Math.sin(a)*r;n?c.lineTo(px,py):c.moveTo(px,py);}c.closePath();c.fill();}}
 else for(let i=0;i<26;i++){c.beginPath();c.ellipse(155,-65+i*20,250,19+rand()*12,-.34,0,Math.PI*2);c.lineWidth=5+rand()*12;c.strokeStyle=i%2?'#e4eaff15':'#03071922';c.stroke();}
 const shadow=c.createLinearGradient(45,30,290,235);shadow.addColorStop(0,'#ffffff2a');shadow.addColorStop(.4,'#00000000');shadow.addColorStop(1,'#010312e8');
 c.fillStyle=shadow;c.fillRect(0,0,320,320);c.restore();
 c.beginPath();c.arc(160,160,146,0,Math.PI*2);c.strokeStyle=`hsla(${hue} 80% 85% / .35)`;c.lineWidth=1.5;c.stroke();
 return canvas;
}
/** Starfield canvas like the app's .space-stars (seeded, so it looks the same on every start). */
export function starfield(w=1600,h=1000,count=520){
 const canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;const c=canvas.getContext('2d');let s=7;
 for(let i=0;i<count;i++){s=(s*16807)%2147483647;const x=s%w;s=(s*16807)%2147483647;const y=s%h;c.fillStyle=`rgba(208,224,255,${.12+(i%8)/12})`;c.beginPath();c.arc(x,y,i%19===0?1.5:.65,0,7);c.fill();}
 return canvas;
}
