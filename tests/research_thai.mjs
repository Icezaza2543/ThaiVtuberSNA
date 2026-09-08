import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const output=process.env.QA_OUTPUT || '.tmp/research-thai';await mkdir(output,{recursive:true});
const browser=await chromium.launch();const errors=[];const report=[];
try {
for(const width of [1440,1280,1024,390]) {
 const page=await browser.newPage({viewport:{width,height:900},deviceScaleFactor:width===390?2:1});page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.QA_URL || 'http://127.0.0.1:5500/web/research/index.html');await page.waitForSelector('#kpiStrip .kpi-value');
 assert.match(await page.locator('#kpiStrip').innerText(),/1,997/);assert.match(await page.locator('#periodNote').innerText(),/ยังไม่ครบปี/);
 const source=await page.evaluate(()=>fetch('dashboard_data.json').then(r=>r.json()));
 for(const y of source.meta.years){await page.selectOption('#summaryYear',String(y));const row=source.ecosystem.yearly_metrics.find(r=>r.year===y);assert.equal(await page.locator('.kpi-value').first().innerText(),row.active_channels.toLocaleString('th-TH'));}
 await page.selectOption('#summaryYear','2026');
 for(const tab of ['overview','ecosystem','lineage','cohorts','centrality','quality']){
 await page.locator('[data-tab="'+tab+'"]').click();
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Overflow '+width+' '+tab);
 const panel=page.locator('#panel-'+tab);assert.doesNotMatch(await panel.innerText(),/undefined|NaN|Infinity|YTD|COMPLETED/);
 assert.ok(await panel.locator('canvas[role="img"]').count()>0);
 assert.equal(await panel.locator('canvas').count(),await panel.locator('.chart-support').count());
 await page.screenshot({path:output+'/'+width+'-'+tab+'.png'});
 report.push({width,tab,passed:true});
 }
 await page.locator('[data-tab="centrality"]').click();await page.fill('#bridgeSearch','no-such-channel-1234');assert.match(await page.locator('#bridgeCount').innerText(),/พบ 0 ช่อง/);
 await page.locator('[data-tab="overview"]').focus();await page.keyboard.press('ArrowRight');assert.equal(await page.locator('[data-tab="ecosystem"]').getAttribute('aria-selected'),'true');
 await page.close();
}
assert.deepEqual(errors,[]);await writeFile(output+'/results.json',JSON.stringify({report,errors},null,2));console.log('24 viewport/tab checks, seven-year KPI checks, search, keyboard, chart tables: passed');
}finally{await browser.close();}
