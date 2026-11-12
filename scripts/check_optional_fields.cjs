// Disposable localhost fixture only.
const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
try{for(const locale of ['ar','en']){
 const p=await b.newPage({locale,viewport:{width:390,height:844}});
 await p.goto('http://127.0.0.1:8000/reports/new/lost/');
 assert.equal(await p.locator('.additional-info').getAttribute('open'),null);
 assert(await p.locator('#id_description').isHidden());
 assert.equal(await p.locator('#id_description').getAttribute('required'),null);
 for(const [field,value] of Object.entries({title:'Black test laptop bag',color:'black',location:'Computing library',event_date:new Date().toISOString().slice(0,10),contact_info:'fictional@example.test'}))await p.locator('#id_'+field).fill(value);
 await p.locator('#id_category').selectOption('bags');await p.locator('#id_building').selectOption('students');await p.locator('#id_contact_method').selectOption('email');
 await p.locator('.form-footer button').click();await p.waitForURL(/\/reports\/(?:confirmation\/|[a-f0-9-]+\/manage\/)/);
 await p.goto('http://127.0.0.1:8000/reports/?q=اسود');
 assert((await p.locator('.report-card h3').allTextContents()).includes('Black test laptop bag'));
 await p.goto('http://127.0.0.1:8000/reports/');
 assert.equal(await p.locator('.additional-info').getAttribute('open'),null);
 await p.locator('.additional-info summary').focus();await p.keyboard.press('Enter');
 assert(await p.locator('#id_color').isVisible());
 await p.locator('#id_color').fill('أسود');await p.locator('.filter-panel button[type=submit]').click();await p.waitForURL(/color=/);
 assert((await p.locator('.report-card h3').allTextContents()).includes('Black test laptop bag'));
 assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await p.close();
}console.log('PASS: Arabic/English blank-description submission, collapsed extras, keyboard disclosure and bilingual color/query filters.');}finally{await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});
