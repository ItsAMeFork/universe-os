const {chromium}=require('playwright'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1920,height:1080}});
  const css=fs.readFileSync('pakket/universe-os/usr/share/universe-os/ui/common.css','utf8')+'\n'+fs.readFileSync('pakket/universe-os/usr/share/universe-os/ui/world.css','utf8');
  const markup='<label class="switch-row"><span class="switch"><input type="checkbox" role="switch"><span class="switch-track"></span></span><span>Automatisch toestaan</span></label><button class="sp-obj">Planeet</button>';
  const measure=()=>page.evaluate(()=>{const sw=document.querySelector('.switch'),track=document.querySelector('.switch-track');return {width:sw.getBoundingClientRect().width,height:sw.getBoundingClientRect().height,track:track.getBoundingClientRect().width,transition:getComputedStyle(document.querySelector('.sp-obj')).transitionDuration};});
  // Reproduce the original panel context: no flex display on label/span.
  const old=css.replace('label.switch-row{display:flex;','label.switch-row{').replace('.switch{display:inline-block;','.switch{').replace('will-change:auto;transition:none','will-change:auto');
  const motionError=()=>page.evaluate(async()=>{
   const el=document.querySelector('.sp-obj');el.style.transform='translateX(0px)';
   await new Promise(resolve=>setTimeout(resolve,200));
   let total=0;
   for(let i=1;i<=12;i++){
    const target=i*15;el.style.transform=`translateX(${target}px)`;
    await new Promise(requestAnimationFrame);
    total+=Math.abs(el.getBoundingClientRect().left-target);
   }
   return total/12;
  });
  await page.setContent('<style>'+old+'</style>'+markup);console.log('Before:',await measure());
  const oldLag=await motionError();
  await page.setContent('<style>'+css+'</style>'+markup);const after=await measure();console.log('After:',after);
  const newLag=await motionError();console.log('Mean position lag (CSS px):',{before:oldLag,after:newLag});assert(oldLag>10);assert(newLag<1);
  assert.equal(after.width,76);assert.equal(after.height,42);assert.equal(after.track,76);assert.equal(after.transition,'0s');
  await page.getByRole('switch').check({force:true});assert(await page.getByRole('switch').isChecked());
  await page.setViewportSize({width:400,height:700});assert.equal((await measure()).width,76);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
