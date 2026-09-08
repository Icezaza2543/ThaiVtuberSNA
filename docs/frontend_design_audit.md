# Frontend design contract and audit

Authority: repository contract [frontend/DESIGN.md](frontend/DESIGN.md), Virtual Constellation Observatory / Prismatic Midnight. Vanilla HTML, CSS and JavaScript remain the implementation.

## Phase A: baseline

- Baseline main: `e656bcb289f8f7dc74ce1b05ed154fdd5bfbb65b`.
- Preserve the exact `AGENCY_ISLAND_COORDINATES` source bytes, expected SHA-256 `47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`.
- Preserve analytical inputs, embedded data, agency colors, node sizing, island placements, edge metrics and threshold semantics. No backend, data pipeline, security configuration or workbook changes.
- Existing DOM IDs bind search, agency/tier/metric filters, four sliders, playback and cumulative mode, physics, spotlight, inspector, methodology and temporal analytics. Keep these IDs. New controls must delegate to the same state/actions.
- Selection currently opens a metric panel; connected rows and agency legend are mouse-only divs. Modal lacks focus isolation. Mobile has no responsive rules; header and dock overflow the viewport. Selected state is absent in the renderer; playback changes the year every 1.6 seconds. Sleeping simulation still redraws each frame.
- Baseline browser evidence: desktop 1440x900 and mobile 390x844 captured with installed visual runtime under the task visualization directory (`before-desktop`, `before-mobile`). Both loaded without request failures. Mobile screenshot shows overflow beyond 390 pixels.

## Visual system before implementation

Visual thesis: a nearly black observatory with quiet translucent instruments and a luminous, agency-colored creator constellation as the primary workspace.

Content plan: compact observatory bar; full graph stage; search and broadcast chronology at the top of a 296px dock; evidence and creator connections in a 380px inspector. Research uses the same palette and typography with rules and tables.

Interaction thesis: 480ms edge evolution, 320ms sheet transitions, 180ms control feedback. Motion follows user intent, stops for reduced motion, and never animates analytical numbers.

Palette: midnight `#05060A`, surface `#0E111B`, paper `#F7F7FB`, secondary `#D6D8E3`, cyan signal `#62E7FF`, violet spectrum `#A78BFA`. Existing agency data colors stay separate. Mitr carries identity, Noto Sans Thai carries controls, JetBrains Mono carries measurements.

```
Observatory bar: identity | time context | methodology / research
┌─────────────────────────────────────────────────────────────┐
│ quiet dock      constellation workspace       creator sheet │
│ search / time   agency haze + selected path    name / metrics│
│ filters         compact scene status          overlap list  │
└─────────────────────────────────────────────────────────────┘
```

The signature is the broadcast chronology changing the constellation, not ornamental dashboard cards. On mobile the graph remains first, with filters and creator details in separate bottom sheets. No marketing hero, random layout, GSAP dependency or fabricated profile classification is introduced: those defaults in gpt-taste are overridden by the user's explicit design contract.

Skill sources installed at pinned revisions: frontend-skill from winklerbremen/codex-skills `af28efd6d134888d7d7fe30e791285e8a0eefd6d`; gpt-taste from Leonxlnx/taste-skill `ccbc15639c97057cbfcf32ecebc38ef716e4bb37`; canvas-design-codex and shared visual runtime from dachent/skills `2e133e356a11214cd9c31f479ec021625f2df571`. Runtime dependencies installed with lifecycle scripts disabled; syntax checks and live browser capture passed. Frontend-design uses the locally installed Anthropic skill. Canvas guidance applies only to graph rendering; ui-ux-pro-max is reserved for Phase G.


## Repository design authority and public boundary

The committed [frontend/DESIGN.md](frontend/DESIGN.md) is the authoritative frontend visual contract. It preserves the original contract wording, with Markdown hard breaks normalized to avoid trailing whitespace; local Downloads paths are not required. The identity remains Virtual Constellation Observatory / Prismatic Midnight. Stale design labels are absent from frontend source.

`tests/test_frontend_public_boundary.py` checks every public `web/` file for the configured private workbook identifier, direct spreadsheet URLs, private worksheet names, viewer identity fields/rows, and channel IDs absent from the independent public creator registry. Synthetic negative cases cover plain, URL-encoded, and JavaScript-escaped leaks; public creator identities and aggregate counts remain allowed. This is a static regression for shipped files, not a replacement for export-boundary controls.
