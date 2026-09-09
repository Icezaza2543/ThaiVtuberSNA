import assert from 'node:assert/strict';
import {mkdir, writeFile, readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
const {chromium} = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base=process.env.QA_URL || 'http://127.0.0.1:5537';
const output=process.env.QA_OUTPUT || '.tmp/expanded-browser';
await mkdir(output,{recursive:true});
const fixturePath = `${output}/expanded-v1/synthetic-${Date.now()}.json`;
execFileSync(process.env.PYTHON || 'python', ['-m','tests.expanded_fixture',fixturePath]);
const bundle = JSON.parse(await readFile(fixturePath,'utf8'));
const browser=await chromium.launch();
const results=[];
try {
 for (const viewport of [{width:1440,height:900},{width:390,height:844}]) {
  const context=await browser.newContext({viewport,reducedMotion:'reduce'});
  const page=await context.newPage(); const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/data/expanded-v1/synthetic.json',r=>r.fulfill({json:bundle}));
  await page.goto(`${base}/?snapshot=data/expanded-v1/synthetic.json&synthetic=1`);
  await page.waitForFunction(()=>selectedSnapshot?.snapshot_id==='all_time');
  assert.equal(await page.locator('#statEdges').textContent(),'1');
  await page.evaluate(()=>{selectedEdgeType='production_credit';applyFilters();openInspector(nodeMap.get('synthetic-start-2023'),false);});
  assert.equal(await page.locator('#statEdges').textContent(),'1');
  assert.match(await page.locator('#inspConnectionsList').textContent(),/production_credit.*outgoing/);
  assert.equal(await page.evaluate(()=>graphEdges.filter(e=>e.visible)[0].shared_any),undefined);
  await page.evaluate(()=>{selectedEdgeType='audience_overlap';closeInspector(false);});
  await page.evaluate(()=>updateTimelineSlice(0));
  assert.equal(await page.locator('#statVtubers').textContent(),'2');
  assert.deepEqual(await page.evaluate(()=>graphNodes.filter(n=>n.visible).map(n=>n.id)),['synthetic-discovered-2026','synthetic-isolated']);
  assert.equal(await page.locator('#statEdges').textContent(),'0');
  await page.evaluate(()=>openInspector(nodeMap.get('synthetic-isolated'),false));
  assert.match(await page.locator('#inspSubs').textContent(),/Unknown/);
  assert.match(await page.locator('#inspAgency').textContent(),/unknown/);
  assert.match(await page.locator('#inspDegree').textContent(),/Unknown/);
  await page.evaluate(()=>updateTimelineSlice(1));
  assert.equal(await page.locator('#inspectorPanel').evaluate(e=>e.inert),false);
  assert.equal(await page.locator('#statVtubers').textContent(),'3');
  await page.evaluate(()=>{isCumulativeTimeline=false;updateTimelineSlice(1);});
  assert.equal(await page.locator('#inspectorPanel').evaluate(e=>e.inert),true);
  assert.equal(await page.locator('#statVtubers').textContent(),'1');
  await page.evaluate(()=>{searchQuery='synthetic-discovered';applyFilters();});
  assert.match(await page.locator('#searchResults').textContent(),/No matching/);
  await page.evaluate(()=>{searchQuery='';isCumulativeTimeline=true;updateTimelineSlice(2);});
  assert.equal(await page.locator('#statVtubers').textContent(),'0'); // missing cumulative_2027
  assert.match(await page.locator('#graphMessage').textContent(),/snapshot/);
  await page.evaluate(()=>{isCumulativeTimeline=false;updateTimelineSlice(2);});
  assert.equal(await page.locator('#statVtubers').textContent(),'1');
  assert.equal(await page.locator('#timeSlider').getAttribute('max'),'3');
  await page.evaluate(()=>updateTimelineSlice(99));
  assert.equal(await page.locator('#statVtubers').textContent(),'0');
  await page.evaluate(()=>updateTimelineSlice(0));
  await page.screenshot({path:`${output}/temporal-${viewport.width}.png`});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.deepEqual(errors,[]);
  // Synthetic bundles cannot enter the default public view or load without opt-in.
  await page.goto(`${base}/?snapshot=data/expanded-v1/synthetic.json`);
  await page.waitForFunction(()=>selectedSnapshot?.coverage_state==='NO_SNAPSHOT');
  results.push({viewport,checks:['typed edges','dated membership','isolated nodes','unknown attributes','inspector refresh','search','missing mode','future period','dynamic years','synthetic opt-in'],errors}); await context.close();
 }
 await writeFile(`${output}/results.json`,JSON.stringify(results,null,2));
 console.log(JSON.stringify(results));
} finally {await browser.close();}
