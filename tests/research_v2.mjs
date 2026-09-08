import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const url=process.env.QA_URL || 'http://127.0.0.1:5500/research/index_v2.html';
const out=process.env.QA_OUTPUT || '.tmp/research-v2-qa';await mkdir(out,{recursive:true});
const browser=await chromium.launch();const report={viewports:[],errors:[],dataRequests:[]};
try {for(const [width,height] of [[1440,900],[1280,800],[1024,768],[390,844]]){
 const page=await browser.newPage({viewport:{width,height},reducedMotion:'reduce'});
 page.on('pageerror',e=>report.errors.push(e.message));page.on('request',r=>{if(r.resourceType()==='fetch'||r.resourceType()==='xhr')report.dataRequests.push(r.url());});
 await page.goto(url);await page.evaluate(()=>document.fonts.ready);
 const fields=await page.locator('[data-field]').count(),charts=await page.locator('[data-chart]').count();
 assert.equal(await page.locator('main>section').count(),9);
 assert.equal(await page.locator('h1').count(),1);
 const keys=await page.locator('[data-field]').evaluateAll(ns=>ns.map(n=>n.dataset.field));assert.equal(keys.length,new Set(keys).size);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:out+'/research-v2-'+width+'.png'});
 const ids=await page.locator('main>section').evaluateAll(ns=>ns.map(n=>n.id));
 for(const id of ids){if(width<768)await page.locator('#menuToggle').click();await page.locator('#chapterNav a[href="#'+id+'"]').click();
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,id+' overflow');
 assert.equal(await page.evaluate(()=>document.activeElement.closest('section').id),id);
 if(['market','outlook'].includes(id))await page.screenshot({path:out+'/research-v2-'+width+'-'+id+'.png'});
 }
 await page.locator('#expandMethods').click();assert.equal(await page.locator('.methods details[open]').count(),14);
 await page.locator('#collapseMethods').click();assert.equal(await page.locator('.methods details[open]').count(),0);
 const first=page.locator('.methods summary').first();await first.focus();await page.keyboard.press('Enter');assert.equal(await page.locator('.methods details[open]').count(),1);
 if(width<768){await page.locator('#menuToggle').click();await page.locator('#chapterNav a').first().focus();await page.keyboard.press('Escape');assert.equal(await page.locator('#menuToggle').getAttribute('aria-expanded'),'false');}
 report.viewports.push({width,height,fields,charts,sections:9,status:'PASS'});await page.close();
}
assert.deepEqual(report.errors,[]);assert.deepEqual(report.dataRequests,[]);
const nojs=await browser.newPage({javaScriptEnabled:false,viewport:{width:390,height:844}});await nojs.goto(url);assert.equal(await nojs.locator('#chapterNav a:visible').count(),9);await nojs.close();report.noJavaScript='Navigation and all chapters remain available';
await writeFile(out+'/qa.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
}finally{await browser.close();}
