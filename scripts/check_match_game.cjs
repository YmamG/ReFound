// Local fixture only: progressive search, language, ordering and keyboard checks.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base='http://127.0.0.1:8000';
const dir=process.env.REFOUND_BROWSER_ARTIFACTS || '/tmp/refound-browser-artifacts';
fs.mkdirSync(dir,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
 let checks=0; const errors=[];
 try {
 for(const lang of ['ar','en']) {
  const context=await browser.newContext({locale:lang, reducedMotion:'reduce'});
  const p=await context.newPage();p.on('pageerror',e=>errors.push(e.message));
  for(const width of [320,375,768,1024,1440]) {
   await p.setViewportSize({width,height:900});
   for(const route of ['/','/find-match/','/find-match/?item=bag&color=olive']) {
    const response=await p.goto(base+route,{waitUntil:'networkidle'});assert.equal(response.status(),200);
    assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${lang} ${width} ${route} overflow`);
    assert(!(await p.locator('main').innerText()).includes('private@example.com'));
    checks++;
   }
  }
  await p.goto(base+'/find-match/');
  assert.equal(await p.locator('input[required]').count(),2);
  assert.equal(await p.locator('.match-options').getAttribute('open'),null);
  await p.locator('.match-options summary').focus();await p.keyboard.press('Enter');
  assert.equal(await p.locator('.match-options').getAttribute('open'),'');
  await p.waitForFunction(()=>document.querySelector('[name=options_open]').value==='1');checks++;
  await p.locator('#id_item').fill(lang==='ar'?'شنطة':'bag');await p.locator('#id_color').fill('olive');
  await p.locator('.match-submit').click();await p.waitForURL(/item=/);
  assert(await p.locator('.match-card h3').first().textContent());
  assert.equal(await p.locator('.match-card:not([hidden])').count(),1);checks++;
  await p.goto(base+'/find-match/?item=canvas%20leather&color=olive');
  assert((await p.locator('.match-card').count())>=2);
  const firstTitle=await p.locator('.match-card:not([hidden]) h3').textContent();
  await p.locator('[data-next]').click();assert.equal(await p.locator('[data-card-index]').textContent(),'2');
  assert.notEqual(await p.locator('.match-card:not([hidden]) h3').textContent(),firstTitle);
  await p.keyboard.press(lang==='ar'?'ArrowRight':'ArrowLeft');
  assert.equal(await p.locator('[data-card-index]').textContent(),'1');
  assert.equal(await p.locator('.match-card:not([hidden]) h3').textContent(),firstTitle);checks++;
  await p.goto(base+'/find-match/?item=unicorn&color=blue');assert.equal(await p.locator('.match-card').count(),0);assert(await p.locator('.match-empty').isVisible());checks++;
  await p.goto(base+'/find-match/?item=bag&color=olive&event_date=invalid');assert.equal(await p.locator('.match-options').getAttribute('open'),'');assert(await p.locator('.error-summary').isVisible());checks++;
  for(const [name,width] of [['desktop',1440],['mobile',390]]) {
   await p.setViewportSize({width,height:900});
   for(const [route,label] of [['/','home'],['/find-match/?item=bag&color=olive','match']]) {
    await p.goto(base+route,{waitUntil:'networkidle'});
    await p.evaluate(async()=>{document.querySelectorAll('img').forEach(i=>i.loading='eager');await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));await document.fonts.ready;window.scrollTo(0,0)});
    await p.screenshot({path:`${dir}/refound-${label}-${lang}-${name}.png`,fullPage:true,animations:'disabled'});
   }
  }
  await context.close();
 }
 // Fixture provides bag + card holder; request 'leather' to exercise multiple title/description matches
 // where available. Plain HTML must always retain every server-ranked card.
 const plain=await browser.newContext({javaScriptEnabled:false,locale:'en'});const p=await plain.newPage();
 await p.goto(base+'/find-match/?item=canvas%20leather&color=olive');assert((await p.locator('.match-card').count())>=2);assert.equal(await p.locator('.match-card[hidden]').count(),0);assert(await p.locator('.deck-controls').isHidden());checks++;
 assert.deepEqual(errors,[]);checks++;
 console.log(`Passed ${checks} match/design checks; screenshots: ${dir}`);
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
