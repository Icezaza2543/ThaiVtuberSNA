import assert from 'node:assert/strict';
import {mkdir, writeFile} from 'node:fs/promises';
const {chromium} = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base=process.env.QA_URL || 'http://127.0.0.1:5537';
const output=process.env.QA_OUTPUT || '.tmp/expanded-browser';
await mkdir(output,{recursive:true});
const n=(id)=>({id,label:id,visibility_state:'EVIDENCED',membership_evidence_refs:['synthetic:e'],subscribers:null,agency:null});
const slice=(id,nodes,edges=[])=>({snapshot_id:id,dataset_version:'expanded-v1',nodes,edges,coverage_state:'PARTIAL',unknown_history:['synthetic-unknown'],collected_through:'2027-03-01T00:00:00Z'});
const bundle={dataset_version:'expanded-v1',synthetic:true,snapshots:[
  slice('yearly_2020',[n('synthetic-discovered-2026'),n('synthetic-isolated')]),
  slice('cumulative_2020',[n('synthetic-discovered-2026'),n('synthetic-isolated')]),
  slice('yearly_2023',[n('synthetic-start-2023')]),
  slice('cumulative_2023',[n('synthetic-start-2023')]),
  slice('yearly_2027',[n('synthetic-latest')]),
  slice('all_time',[n('synthetic-start-2023'),n('synthetic-discovered-2026'),n('synthetic-isolated')],
    ['audience_overlap','collaboration','production_credit'].map(edge_type=>({
      source:'synthetic-start-2023',target:'synthetic-discovered-2026',edge_type,
      ...(edge_type==='audience_overlap'?{shared_any:9,jaccard_comments:.2}:{credit_role:'rigger'})})))
]};
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
  assert.equal(await page.locator('#inspectorPanel').evaluate(e=>e.inert),true);
  assert.equal(await page.locator('#statVtubers').textContent(),'1');
  await page.evaluate(()=>{searchQuery='synthetic-discovered';applyFilters();});
  assert.match(await page.locator('#searchResults').textContent(),/No matching/);
  await page.evaluate(()=>{searchQuery='';updateTimelineSlice(2);});
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
  results.push({viewport,checks:16,errors}); await context.close();
 }
 await writeFile(`${output}/results.json`,JSON.stringify(results,null,2));
 console.log(JSON.stringify(results));
} finally {await browser.close();}
