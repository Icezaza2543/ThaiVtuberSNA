# Research v2 — Phase 1 prototype

The new entry point is `web/research/index_v2.html`; it uses `research_v2.css` and `research_v2.js` plus the existing design tokens. The original Research entry point, its CSS/JS, analytical JSON, shared tokens and main graph file remain byte-identical to their pre-task baseline.

## Information architecture

1. ภาพรวมวงการ — executive question, evidence status, six empty KPIs and four industry dimensions.
2. ขอบเขตข้อมูล — research universe, observed/unobserved boundary, annual coverage and explicit partial-year note.
3. Creator Ecosystem — supply, first observation, availability, verified exits, composition and concentration.
4. Audience Behavior — behavior segments and target-audience evolution, without demographic claims.
5. Network & Communities — human-readable questions before supporting technical measures.
6. Mobility & Collab — re-observation categories, with unconnected collab windows and no causal result.
7. Market & Money — separate observed monetization, unestimated market size and empty scenario assumptions.
8. Outlook — prominent closing question, evidence scorecard and unselected structural state.
9. Methodology — 14 native disclosure sections with future artifact slots.

There are **193 unique `data-field` slots and 7 `data-chart` regions**. Dashes mean unconnected, not zero. No direction, classification, revenue, population count or plot geometry is fabricated. Timeline years, chapter numbers and 30/90-day collab window labels are structural labels, not observations.

## Validation

- 9 chapters × 4 viewports: 1440×900, 1280×800, 1024×768, 390×844.
- No horizontal page overflow, JavaScript exceptions or fetch/XHR requests.
- Navigation moves focus to the selected chapter heading; active chapter uses text weight and a border as well as color.
- Mobile menu, Escape, keyboard disclosure and expand/collapse all: passed.
- Reduced-motion mode: passed. Without JavaScript, all chapters and navigation remain accessible.
- Original Research regression: 24 tab/viewport checks, seven-year selection, search and keyboard passed.
- Public boundary regression: 19 tests passed. JavaScript syntax and diff whitespace checks passed.
- Protected coordinate SHA-256: `47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`.

Screenshots: [1440](frontend/screenshots/research-v2-1440.png), [1280](frontend/screenshots/research-v2-1280.png), [1024](frontend/screenshots/research-v2-1024.png), [390](frontend/screenshots/research-v2-390.png). Desktop overview, mobile overview, Outlook and Market were visually reviewed. [Machine-readable QA](evidence/research_v2_qa.json).

## Re-run

Serve `web/` using `python -m http.server 5500 --bind 127.0.0.1 --directory web`, then run `node tests/research_v2.mjs` with Playwright available. Set `PLAYWRIGHT_MODULE` to an installed module path if needed. `QA_URL` overrides the default `http://127.0.0.1:5500/research/index_v2.html`; `QA_OUTPUT` overrides `.tmp/research-v2-qa`.

Design uses the repository [contract](frontend/DESIGN.md) with the user's Phase 1 briefing taking priority: editorial spacing and a question-led narrative instead of a network-canvas hero. Skills: frontend-design, frontend-skill, selective gpt-taste; ui-ux-pro-max for final QA. No network canvas changes, analytical fetching, market calculations, pipeline work, or production collection. Real-data wiring awaits prototype review.
