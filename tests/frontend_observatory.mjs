// Browser regression suite. Serve web/ locally, then set PLAYWRIGHT_MODULE and QA_OUTPUT.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.QA_URL || 'http://127.0.0.1:8765';
const output = path.resolve(process.env.QA_OUTPUT || '.tmp/frontend-qa');
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const report = { viewports: [], checks: [], errors: [], performance: null };
async function ready(page) {
  await page.goto(base);
  await page.waitForFunction(() => graphNodes.length > 0 && isSleeping);
  await page.evaluate(() => document.fonts.ready);
}
async function settleUI(page) {
  await page.evaluate(() => Promise.all(document.getAnimations().map(animation => animation.finished.catch(() => {}))));
}
async function screenshot(page, name) {
  await settleUI(page);
  await page.screenshot({ path: path.join(output, name + '.png') });
}
async function overflow(page) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Horizontal page overflow');
}
try {
  for (const [width, height] of [[1440,900],[1280,800],[1024,768],[390,844]]) {
    const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: width === 390 ? 2 : 1, hasTouch: width === 390 });
    const page = await context.newPage();
    page.on('pageerror', error => report.errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') report.errors.push(message.text()); });
    await ready(page);
    assert.equal(await page.locator('#scenePeriod').textContent(), 'Legacy roster · identity history unverified');
    if (width < 1200) await page.locator('#btnControls').click();
    await page.locator('#btnToggleTimeMode').click();
    assert.equal(await page.locator('#scenePeriod').textContent(), 'Legacy roster · identity history unverified');
    await page.locator('#btnToggleTimeMode').click();
    if (width < 1200) await page.locator('#btnCloseControls').click();
    await overflow(page);
    const expectedEdges = await page.evaluate(() => temporalSnapshotsData.slices.all_time.edges.filter(edge => nodeMap.has(edge.source) && nodeMap.has(edge.target) && (edge.shared_any ?? edge.shared_viewers) >= 5).length);
    assert.ok(expectedEdges > 0, 'Real aggregate fixture unexpectedly has no edges');
    assert.equal(await page.locator('#statEdges').textContent(), expectedEdges.toLocaleString());
    await screenshot(page, `main-${width}`);
    const fontStatus = await page.evaluate(() => ({
      display: document.fonts.check('400 14px "Mitr"'),
      body: document.fonts.check('400 14px "Noto Sans Thai"'),
      mono: document.fonts.check('400 14px "JetBrains Mono"')
    }));
    assert.ok(Object.values(fontStatus).every(Boolean), 'Expected fonts did not load');
    if (width < 1200) {
      assert.ok(await page.locator('#controlDock').evaluate(el => el.inert));
      await page.locator('#btnControls').click();
      assert.equal(await page.locator('#btnControls').getAttribute('aria-expanded'), 'true');
      await screenshot(page, `filters-${width}`);
    }
    await page.locator('#searchInput').fill('Aisha');
    await page.locator('#searchInput').press('ArrowDown');
    await page.keyboard.press('Enter');
    assert.match(await page.locator('#inspName').textContent(), /Aisha/);
    assert.ok(!(await page.locator('#inspConnectionsList').textContent()).includes('undefined'));
    assert.equal(await page.locator('#inspectorPanel').evaluate(el => el.inert), false);
    assert.equal(await page.evaluate(() => document.activeElement.id), 'btnCloseInspector');
    await settleUI(page);
    const rect = await page.locator('#inspectorPanel').boundingBox();
    assert.ok(rect.x >= 0 && rect.x + rect.width <= width && rect.y >= 0 && rect.y + rect.height <= height + 1);
    await screenshot(page, `inspector-${width}`);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#inspectorPanel').evaluate(el => el.inert), true);
    await page.locator('#btnInfoModal').click();
    for (let index = 0; index < 6; index++) {
      await page.keyboard.press(index % 2 ? 'Shift+Tab' : 'Tab');
      assert.ok(await page.evaluate(() => infoModal.contains(document.activeElement)), 'Modal focus escaped');
    }
    await page.keyboard.press('Escape');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'btnInfoModal');
    await page.locator('#btnSearch').click();
    await page.locator('#searchInput').fill('does-not-exist-qa');
    assert.match(await page.locator('#searchResults').textContent(), /No matching/);
    await page.locator('#searchInput').fill('');
    await page.locator('[data-step="6"]').click();
    assert.match(await page.locator('#temporalCurrentLabel').textContent(), /2026/);
    assert.match(await page.locator('#scenePeriod').textContent(), /2026 · cumulative/);
    await page.locator('#btnPlayTimeline').click();
    await page.locator('#btnPlayTimeline').click();
    assert.equal(await page.evaluate(() => isPlayingTimeline), false);
    await page.locator('#btnToggleTimeMode').click();
    assert.equal(await page.evaluate(() => isCumulativeTimeline), false);
    assert.match(await page.locator('#scenePeriod').textContent(), /202[0-6]( YTD)? · yearly/);
    assert.equal(await page.locator('#statVtubers').textContent(), '0');
    assert.match(await page.locator('#graphMessage').textContent(), /review|ทบทวน/);
    await page.locator('[data-step="7"]').click();
    await page.locator('#agencyFilter').selectOption('Algorhythm Project');
    assert.ok(await page.evaluate(() => graphNodes.filter(node => node.visible).every(node => node.agency === 'Algorhythm Project')));
    if (width < 1200) await page.locator('#btnCloseControls').click();
    if (width === 390) {
      const target = await page.evaluate(() => {
        const node = graphNodes.find(n => n.visible);
        const box = canvas.getBoundingClientRect();
        return { x: box.left + node.x * zoom + panX, y: box.top + node.y * zoom + panY, id: node.id };
      });
      await page.touchscreen.tap(target.x, target.y);
      assert.equal(await page.evaluate(() => selectedNode?.id), target.id, 'Touch selection failed');
      await page.keyboard.press('Escape');
    }
    const panBefore = await page.evaluate(() => panX);
    await page.locator('#networkCanvas').focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.evaluate(() => panX), panBefore - 40);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.waitForFunction(() => document.getElementById('btnPlayTimeline').disabled);
    assert.equal(await page.locator('#btnPlayTimeline').isDisabled(), true);
    assert.equal(await page.evaluate(() => isSleeping && !isPlayingTimeline && previousEdges.length === 0), true);
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    if (width === 1440) {
      await ready(page);
      report.performance = await page.evaluate(async () => {
        const timings = [];
        for (let i = 0; i < 30; i++) {
          await new Promise(requestAnimationFrame);
          const start = performance.now(); renderCanvas(); timings.push(performance.now() - start);
        }
        let idleDraws = 0;
        const original = ctx.clearRect;
        ctx.clearRect = function(...args) { idleDraws++; return original.apply(this, args); };
        await new Promise(resolve => setTimeout(resolve, 150));
        ctx.clearRect = original;
        timings.sort((a,b) => a-b);
        return { nodes: graphNodes.length, samples: timings.length, medianMs: timings[15], p95Ms: timings[28], idleDraws };
      });
      assert.equal(report.performance.idleDraws, 0, 'Sleeping graph still draws frames');
    }
    await page.goto(base + '/research/');
    await page.waitForFunction(() => document.querySelector('#kpiStrip').children.length > 0);
    await overflow(page);
    await screenshot(page, `research-${width}`);
    for (const tab of ['ecosystem','lineage','cohorts','centrality','quality','overview']) {
      await page.locator(`[data-tab="${tab}"]`).click();
      const dimensions = await page.locator('.tab-panel.active canvas').evaluateAll(canvases => canvases.map(c => ({ width: c.width, height: c.height, css: c.clientHeight, dpr: devicePixelRatio })));
      assert.ok(dimensions.every(c => c.width > 0 && Math.abs(c.height - c.css * c.dpr) < 2), 'Blank or growing canvas');
      await overflow(page);
    }
    await page.locator('[data-tab="overview"]').focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.locator('[data-tab="ecosystem"]').getAttribute('aria-selected'), 'true');
    report.viewports.push({ width, height, fontStatus, main: 'PASS', inspector: 'PASS', research: 'PASS' });
    await context.close();
  }
  // Controlled public aggregate fixture proves period/metric/threshold wiring without changing files.
  const page = await browser.newPage();
  await ready(page);
  const ids = await page.evaluate(() => graphNodes.slice(0, 3).map(n => n.id));
  const edges = [
    { source: ids[0], target: ids[1], shared_any: 10, jaccard_comments: .2, overlap_coefficient: .5 },
    { source: ids[1], target: ids[2], shared_any: 30, jaccard_comments: .6, overlap_coefficient: .8 },
    { source: ids[0], target: ids[2], shared_any: 1, jaccard_comments: .01, overlap_coefficient: .02 }
  ];
  const nodes = ids.map(id => ({id,label:id,visibility_state:'EVIDENCED',membership_evidence_refs:['synthetic:review']}));
  const slice = (snapshot_id, edges) => ({snapshot_id, nodes, edges, coverage_state:'PARTIAL'});
  await page.route('**/data/temporal_snapshots.json', route => route.fulfill({ json: {
    dataset_version:'expanded-v1', snapshots:[slice('all_time',edges),slice('cumulative_2026',edges),
      slice('yearly_2026',edges.slice(0,1)),slice('cumulative_2020',[])]
  } }));
  await ready(page);
  assert.equal(await page.locator('#statEdges').textContent(), '2');
  await page.locator('#thresholdSlider').fill('1');
  assert.equal(await page.locator('#statEdges').textContent(), '3', 'Single shared viewer edge cannot be explored');
  await page.locator('#thresholdSlider').fill('20');
  assert.equal(await page.locator('#statEdges').textContent(), '1');
  await page.locator('#metricSelect').selectOption('jaccard');
  await page.locator('#thresholdSlider').fill('40');
  assert.equal(await page.locator('#statEdges').textContent(), '1');
  await page.locator('[data-step="1"]').click();
  await page.locator('#btnToggleTimeMode').click();
  assert.equal(await page.locator('#statEdges').textContent(), '0');
  await page.locator('#thresholdSlider').fill('5');
  assert.equal(await page.locator('#statEdges').textContent(), '1');
  await page.evaluate(id => openInspector(nodeMap.get(id)), ids[0]);
  assert.equal(await page.locator('#inspConnectionsList button').count(), 1);
  await page.locator('[data-step="0"]').click();
  assert.equal(await page.locator('#inspConnectionsList button').count(), 0, 'Inspector retained stale period edges');
  await page.route('**/data.json', route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await ready(page);
  assert.match(await page.locator('#dataFreshness').textContent(), /Embedded snapshot|Collection cutoff/);
  report.checks.push('touch selection', 'embedded fallback labeling', 'single-viewer threshold', 'period, metric and threshold fixture', 'inspector refresh', 'search and empty state', 'modal focus and Escape', 'reduced motion', 'idle rendering', 'research tabs and DPR');
  assert.deepEqual(report.errors, []);
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL'; report.failure = error.stack; throw error;
} finally {
  await writeFile(path.join(output, 'qa-report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report));
  await browser.close();
}
