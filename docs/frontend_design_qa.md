# Observatory frontend implementation and QA

Implemented DESIGN.md phases A–G on main. Design authority and skill provenance are recorded in [frontend_design_audit.md](frontend_design_audit.md).

## Scope and changes

- `web/design-tokens.css`: Prismatic Midnight palette, Mitr / Noto Sans Thai / JetBrains Mono, spacing and motion tokens.
- `web/index.html`, `web/styles.css`: Observatory bar, SVG icons, compact control dock with Advanced disclosure, broadcast chronology, floating creator profile, methodology dialog, responsive drawers and bottom sheets.
- `web/observatory-ui.js`: search result buttons, focus management, keyboard controls, zoom/fit controls, reduced-motion behavior and snapshot labeling.
- `web/app.js`: selected rings and paths, restrained agency haze, label collision avoidance, pointer/touch interaction, 480ms edge transitions and event-driven rendering when settled. Agency coordinate values and ordering are unchanged.
- `web/research/index.html`, `research_dashboard.css`, `research_dashboard.js`: shared typography and surfaces, calmer rules/tables, accessible tabs, resize handling and stable canvas dimensions at DPR 2.
- `tests/frontend_observatory.mjs`: browser regressions using the real public files and separately routed aggregate fixtures.
- Release manifest and release notes: refreshed using the existing generator solely because its checksums cover the three Research frontend files. All other artifact checksums are unchanged; analytical data was not regenerated.

No backend, data-plane or security architecture changes were made for this work. Concurrent private-data maintenance files in the shared checkout were not included in frontend commits.

## Correctness findings addressed during visual QA

The old frontend expected `shared_viewers` and `jaccard`, while current temporal exports provide `shared_any` and `jaccard_comments`. That mismatch produced zero displayed edges and undefined profile counts. A frontend-only adapter now uses the published intersection count and labels comment Jaccard explicitly. It does not infer an all-source Jaccard metric. Real all-time data now displays 2,929 qualifying connections at the unchanged default count threshold of 5.

The count slider can also reach 1, and percentage thresholds can reach 0, so small observed overlaps can be explored deliberately. Missing metrics do not pass a threshold as invented zeroes. The profile connection list follows the current time slice and explicitly includes recorded connections below the graph threshold. Dataset-level centrality is labeled separately.

Other fixes: focus trapping and return, hidden panels made inert, user-agent reduced-motion changes stop autoplay and simulation, mobile agency labels avoid collisions, visible counts reflect active filters, and research charts redraw after a hidden tab becomes visible without multiplying their height at high DPR.

## Verification

- Full existing Python suite: **286 passed**, 120 existing NetworkX assortativity warnings, 110.29 seconds.
- Release suite repeated after final Research CSS/checksum update: **7 passed**.
- `node --check`: app, UI helpers, Research JavaScript and browser regression script pass. No build step or frontend framework was introduced.
- Browser regression: **PASS** at 1440×900, 1280×800, 1024×768 and 390×844 (mobile DPR 2).
- Actual public data counts, search/empty states, creator profiles, selected-period refresh, filters, playback/pause, YTD, cumulative/yearly mode, modal focus/Escape, keyboard pan, touch selection, reduced motion, fallback labeling and all six research tabs verified.
- Controlled fixtures separately verify the current temporal schema, single-viewer edges, count/Jaccard thresholds and stale inspector prevention. These fixtures never replace checked-in datasets or the real-data screenshots.
- All three fonts loaded at all four viewport sizes. No page or console errors in the real-data browser runs. No horizontal document overflow.
- Visual lint found no remaining text-contrast or tiny-text findings in the checked main desktop / Research mobile views. Its remaining overflow flags are intentional scroll regions: the control dock, research tab rail and research table. They have keyboard/touch access; the table is a named focusable region.
- Fourteen screenshots have valid image bounds and nonzero sizes. Screenshots were inspected for graph framing, label overlap, sheet boundaries and chart visibility.
- Protected coordinate SHA-256: **47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc**, matching the design contract and existing project validator.
- `git diff --check` passes for the frontend changes.

Performance measurement in headless Chromium on this machine: 1,370 nodes, 30 explicit render samples, roughly **2.0ms median / 2.7ms p95**, and **zero redraws during a 150ms idle window**. These are local measurements, not a guarantee for every device. CSS and vanilla JavaScript handle the motion; no runtime framework or animation library was added.

## Evidence and reproduction

Committed machine-readable results: [frontend_observatory_qa.json](evidence/frontend_observatory_qa.json).

Screenshots and the contact sheet live in the task's persistent visualization folder:

`C:/Users/Icezaza/.codex/visualizations/2026/09/06/01a0771c-d222-7172-8a18-992302eb0696/final/`

Key files: `main-1440.png`, `main-1280.png`, `main-1024.png`, `main-390.png`, `inspector-1440.png`, `inspector-390.png`, `filters-1024.png`, `filters-390.png`, `research-1440.png`, `research-390.png`, `contact-sheet.html`, `qa-report.json`, `image-bounds.json`, and visual-lint JSON reports. Baseline screenshots are in sibling `before-desktop` and `before-mobile` folders.

Run a local static server for `web/`, then run the browser test with an installed Playwright module:

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory web
# In another terminal:
$env:PLAYWRIGHT_MODULE='file:///C:/Users/Icezaza/.codex/skills/.shared/visual-runtime/node_modules/playwright/index.mjs'
$env:QA_OUTPUT='.tmp/frontend-qa'
node tests/frontend_observatory.mjs
```

Milestones pushed before final QA: `e4be79a` (tokens/audit), `b76197e` (shell and accessible sheets), `a70ac24` (canvas/motion), `f38dac4` (Research). The final QA/correctness commit contains this report and reproducible browser checks.

The verification scope is frontend rendering and interaction. It does not certify collection completeness, analytical input reproducibility, or continuous collector operation.
