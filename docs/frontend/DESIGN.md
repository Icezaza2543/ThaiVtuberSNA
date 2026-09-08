# DESIGN.md — ThaiVtuberSNA Frontend Creative Direction

> Project: Thai VTuber Audience Network / ThaiVtuberSNA\
> Scope: `web/` main interactive network visualizer + visual alignment for `web/research/`\
> Design direction: **Virtual Constellation Observatory**\
> Status: Design contract for Codex frontend implementation

---

## 0. Skill Stack

Use skills in this order. Do **not** blend every skill at once during concept generation.

### Primary creative stack

1. **`frontend-design`**
   - Owns art direction, typography, visual identity, signature elements, composition.
   - This is the primary creative director.

2. **`frontend-skill`**
   - Owns restraint, hierarchy, image-led/composition-first layout, reduced card clutter.
   - Use it to keep `frontend-design` from becoming visually noisy.

3. **`gpt-taste`**
   - Use selectively for VTuber-grade motion, expressive layout, GSAP-style interaction thinking, and anti-generic aesthetics.
   - Do not let it turn the dashboard into a marketing landing page.
   - Motion intensity target: **5/10**, not cinematic 9/10.

### Specialized skill

4. **`canvas-design-codex`**
   - Invoke only when touching the network canvas / node rendering / custom graph visuals / pixel animation.
   - Preserve graph correctness and hit-testing.

### Final QA

5. **`ui-ux-pro-max`**
   - Run after the visual implementation is substantially complete.
   - Use for accessibility, responsive behavior, motion safety, control clarity, forms/selects, empty/loading/error states.

Do not stack more visual skills unless there is a specific failure mode to fix. Too many competing design rules can blur the direction.

---

# 1. Product Identity

ThaiVtuberSNA is **not** a SaaS admin dashboard.

It is a **research observatory for a living virtual-creator ecosystem**.

The frontend should feel like a hybrid of:

- VTuber / virtual idol culture
- constellation / social graph exploration
- live broadcast UI
- Japanese digital editorial design
- research observatory / scientific instrument
- playful fandom energy without looking childish

The main emotional read should be:

> **“I am looking into a living constellation of Thai VTubers.”**

Not:

> “Generic dark analytics dashboard.”

---

# 2. Signature Visual Idea — Virtual Constellation Observatory

The network graph is the hero.

Everything else should frame the graph rather than compete with it.

### Metaphor

- VTuber node = luminous virtual star / signal orb
- Agency cluster = nebula / constellation island
- Audience overlap = light trail / signal bridge
- Strong bridge VTuber = radiant relay beacon
- Selected VTuber = focused stage spotlight
- Community = soft spectral region, not opaque container
- Timeline = broadcast chronology / constellation evolution

The interface should feel **alive even before interaction**, but motion must remain subtle.

---

# 3. Existing Architecture Constraints

Current main frontend is vanilla:

- `web/index.html`
- `web/styles.css`
- `web/app.js`
- `web/data.json`
- `web/data/*`
- `web/research/*`

Do **not** migrate the app to React/Next/Vite merely for redesign.

Preserve the existing functional architecture unless a framework migration is explicitly authorized later.

### Critical invariant

The exact manual:

`AGENCY_ISLAND_COORDINATES`

inside `web/app.js` is protected.

**Do not modify, regenerate, reorder, normalize, or replace it.**

Expected protected block SHA-256:

`47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`

All existing functional DOM IDs used by `app.js` must remain stable unless Codex updates every dependent reference and proves behavior is unchanged.

---

# 4. Current UI Problems To Correct

The current visual language is competent but still reads as:

**“premium cyber analytics dashboard”**

instead of specifically:

**“Thai VTuber ecosystem observatory.”**

Primary weaknesses to correct:

1. Too many conventional glass cards/panels.
2. Cyan/pink/purple cyber palette is generic AI-tech by itself.
3. Controls visually compete with the graph.
4. Top header behaves like an admin dashboard.
5. VTuber identity is mostly text; creator personality is underrepresented.
6. Graph lacks a strong “virtual constellation / stage” framing layer.
7. Inspector feels like a metrics card rather than a VTuber profile moment.
8. Emoji-based UI icons reduce visual cohesion.
9. Research context and creative fandom context do not feel like the same product.
10. Mobile/tablet hierarchy is secondary rather than intentionally designed.

---

# 5. Visual Language

## 5.1 Theme name

**Prismatic Midnight**

Dark, atmospheric, luminous, clean.

Not black-on-neon gamer HUD.
Not cyberpunk city.
Not pastel kawaii overload.

Use saturated color primarily for signal, identity, selection, and motion.

---

## 5.2 Base Colors

Suggested token direction:

```css
--ink-950: #05060A;
--ink-900: #090B12;
--ink-850: #0E111B;
--ink-800: #141826;

--text-100: #F7F7FB;
--text-300: #D6D8E3;
--text-500: #9298AA;
--text-650: #687084;

--prism-cyan: #62E7FF;
--prism-violet: #A78BFA;
--prism-pink: #FF7AC8;
--prism-mint: #6EF0C2;
--prism-gold: #FFD16A;
```

Do not paint every component with all accent colors.

Page-level accent ratio:

- 70% neutral dark
- 20% soft spectral tint
- 10% vivid signal color

Agency colors remain data colors and must not be confused with global UI actions.

---

## 5.3 Spectral Gradient

Use gradients only in a few signature surfaces:

- logo mark
- selected creator halo
- timeline active track
- occasional divider / spectral glow
- graph atmospheric background

Avoid gradient buttons everywhere.

Signature gradient:

```css
linear-gradient(
  110deg,
  #62E7FF 0%,
  #A78BFA 42%,
  #FF7AC8 75%,
  #FFD16A 100%
)
```

Keep saturation under control by reducing opacity when used as background.

---

# 6. Typography

The UI needs stronger VTuber/editorial personality while preserving Thai readability.

Recommended:

### Display / section titles
`Mitr`

Use for:
- product title
- large selected VTuber name
- section title
- key narrative labels

### Body / UI
`Noto Sans Thai`

Use for:
- controls
- descriptions
- explanatory copy
- Thai content

### Numeric / technical
`JetBrains Mono`

Use for:
- percentages
- centrality values
- timestamps
- technical IDs
- graph diagnostics

Do not use monospace for general navigation.

Typography must create hierarchy without relying on cards.

---

# 7. Main Page Composition

Desktop target: 1440px and above.

The graph should visually occupy at least **70–80% of perceived attention**.

## 7.1 Header

Replace the current dashboard-style stats row with a lighter **Observatory Bar**.

### Left
- compact prismatic logo
- `Thai VTuber Constellation`
- small research subtitle: `Audience Network Observatory`

### Center
Optional timeline context:
- `2020 — 2026`
- current mode / current year
- YTD indicator where relevant

### Right
Keep only high-value actions:
- Search shortcut
- Methodology / About
- Research view
- Data freshness indicator

Do not place 4–5 KPI blocks permanently in the header.

Network counts can move into a compact floating “scene status” strip.

---

## 7.2 Left Control Dock

The current 320px glass card should evolve into a **compact translucent control dock**.

Design:
- width around 288–308px desktop
- lower opacity than current
- stronger section grouping
- fewer visible controls at once
- advanced physics controls collapsed under `Advanced`
- no emoji icons

Priority order:

1. Search
2. Timeline
3. Agency / group
4. Edge metric
5. Minimum overlap
6. Bridge spotlight
7. Advanced graph physics
8. Legend

The user should understand the graph before understanding the controls.

---

## 7.3 Graph Stage

The graph is the visual centerpiece.

Background:

- almost-black base
- very subtle noise/dither
- sparse spectral haze
- soft radial “nebula” around major agency clusters
- optional faint coordinate/grid stars
- no obvious rectangular chart container

Graph edges:
- normal edges: low-alpha cool gray / spectral tint
- selected path: brighter luminous trail
- strong overlap: slightly thicker, not dramatically brighter
- bridge spotlight: localized pulse, not all-edge animation

Graph nodes:
- preserve data semantics
- visual node can have:
  - soft outer halo
  - inner agency color
  - selected white spectral ring
  - bridge creator small orbital accent

If public creator avatar/thumbnail is already available from safe public metadata, the selected inspector may show it.
Do not block implementation waiting for avatars.

---

# 8. VTuber Inspector — Make Selection Feel Special

The selected VTuber panel should feel like a **mini profile stage**, not a database row.

Desktop:
- right floating sheet
- 360–400px
- top area more visual than current

Structure:

1. Profile identity
   - avatar if safely available
   - VTuber display name large
   - handle
   - agency pill
   - subscriber tier / public status

2. Structural role
   - human-readable badge:
     - `Bridge Beacon`
     - `Community Core`
     - `Emerging Connector`
     - or existing scientifically valid classification
   - never invent classifications unsupported by data

3. Metric constellation
   - Degree
   - Betweenness / Bridge Position
   - PageRank
   - percentile band where available

4. Audience overlap
   - top connected creators
   - use horizontal mini bars or tiny spectral lines
   - creator names should dominate, not raw numbers

5. Research caveat
   - subtle footer:
     `Observed public interaction evidence · not all viewers`

No fake biography or fabricated creator lore.

---

# 9. Timeline Interaction

Timeline is one of the product’s most memorable features.

Turn it into a **broadcast evolution rail**.

States:

- 2020
- 2021
- 2022
- 2023
- 2024
- 2025
- 2026 YTD
- All-time

When year changes:

- graph transition: 350–550ms
- nodes shift with restrained spring
- previous edges fade
- new edges emerge
- current year label changes with subtle number roll/fade

Auto-play:
- slower than current dashboard animation
- user can pause instantly
- obey `prefers-reduced-motion`

Do not use full-screen cinematic transitions.

---

# 10. Agency / Community Representation

Agency clusters should not be generic colored circles.

Use a **nebula family system**:

- each agency gets a data color
- background haze uses only 5–12% opacity
- community/agency name may appear as faint map label at wider zoom
- avoid giant permanent borders around clusters

Independent creators should not be visually treated as one “agency.”
If technically grouped for rendering, label the grouping carefully.

Preserve scientific semantics:
`agency_at_selection` is selection-time metadata, not verified historical affiliation.

---

# 11. Motion System

Motion is important for VTuber identity but must remain functional.

## Motion levels

### Micro
120–220ms
- hover
- button focus
- chip activation
- subtle halo response

### UI transition
250–420ms
- panel open
- inspector switch
- filter state
- tabs

### Graph evolution
350–650ms
- timeline transitions
- cluster reflow
- selected path highlight

No infinite decorative motion except:
- extremely subtle background drift
- tiny active status pulse

Maximum simultaneous obvious animations: **3**

Respect:

```css
@media (prefers-reduced-motion: reduce)
```

---

# 12. Iconography

Remove emoji UI icons from primary controls.

Use one coherent icon system:
- Lucide-style SVG icons, or
- minimal inline SVG set

Icons:
- Search
- Clock/Timeline
- Play/Pause
- Filter
- Network
- Sparkles/Bridge
- Sliders
- Info
- External link
- Research

Do not use random filled icons mixed with emoji.

---

# 13. Cards & Surface Rules

Avoid “everything is a rounded glass card.”

Allowed floating surfaces:
- control dock
- inspector
- methodology modal
- transient tooltip

Everything else should use:
- whitespace
- separators
- typography
- subtle tint
- floating labels

Preferred radius:
- main surface: 18–22px
- controls: 10–14px
- pills: full radius only for true pills/tags

Blur:
- use sparingly
- 12–18px maximum common backdrop blur
- avoid stacking several blurred layers

---

# 14. Data Visualization Rules

This is research UI. Beauty cannot obscure meaning.

Never:
- encode two different meanings with the same color
- hide low-weight edges purely for aesthetics unless threshold control says so
- animate metric values in ways that imply causal change
- call structural centrality “influence”
- imply passive audience coverage

Use:
- `Bridge Position`
- `Structural Centrality`
- `Observed Audience Overlap`
- `Observed Interaction Evidence`

2026 must remain visibly `YTD`.

---

# 15. Research View (`web/research/`)

Research view should share the same design tokens but be calmer.

Main graph page:
- immersive
- exploratory
- expressive

Research dashboard:
- editorial
- legible
- lower motion
- higher information density
- white-space and rule lines instead of excessive cards

Use the same:
- typography
- accent spectrum
- data color semantics
- YTD badge
- privacy terminology

Do not make research view a separate unrelated brand.

---

# 16. Responsive Strategy

## Desktop ≥ 1200
Full graph stage + left control dock + right inspector.

## Tablet 768–1199
- header simplified
- controls become collapsible left drawer
- inspector becomes right drawer / bottom sheet depending width
- graph always remains visible

## Mobile < 768
- graph remains first screen
- top compact title
- filter button opens bottom sheet
- selected VTuber opens full-width bottom sheet
- stats reduced to 1–2 context values
- timeline uses horizontal scroll/segmented control

Do not squeeze desktop sidebars into mobile.

---

# 17. Accessibility

Required:

- visible keyboard focus
- every button has an accessible name
- canvas interaction has textual/search alternative where practical
- form labels remain real labels
- selected state not color-only
- contrast AA for body text
- reduced motion
- touch targets ≥ 40px
- inspector close button keyboard accessible
- modal focus trap
- Escape closes modal/drawer
- do not rely on hover for essential information

---

# 18. Performance Budget

The graph is already computation-heavy.

Frontend polish must not meaningfully reduce graph performance.

Rules:

- avoid CSS filters on large continuously animating surfaces
- no per-frame DOM layout work
- no giant animated gradients
- no full-screen backdrop blur layers stacked together
- prefer opacity/transform animations
- avoid adding heavy framework dependencies
- do not introduce GSAP unless the benefit clearly exceeds vanilla/CSS implementation cost
- if GSAP is added, document exactly why and keep its scope small

Target:
- interaction should feel responsive on common laptop hardware
- graph pan/zoom must remain smooth

---

# 19. Implementation Order For Codex

## Phase A — Audit
1. Inspect current DOM IDs and `app.js` event bindings.
2. Document protected invariants.
3. Capture screenshots of current desktop/mobile if browser tooling is available.
4. Do not code until the visual system is mapped.

## Phase B — Design tokens
1. Refactor `web/styles.css` tokens.
2. Typography.
3. surface colors.
4. spacing scale.
5. motion tokens.
6. icon treatment.

## Phase C — Main shell
1. observatory header
2. control dock
3. graph stage atmospheric layer
4. inspector

## Phase D — Interaction polish
1. timeline
2. spotlight bridge
3. tooltips
4. selected node states
5. modal

## Phase E — Responsive
1. tablet
2. mobile drawers/bottom sheets
3. keyboard states
4. reduced motion

## Phase F — Research visual alignment
Restyle `web/research/` with the same design system.

## Phase G — Visual QA
Use browser screenshots at:
- 1440×900
- 1280×800
- 1024×768
- 390×844

Check:
- overflow
- clipped controls
- graph occlusion
- inspector collision
- font fallback
- contrast
- motion
- canvas performance

---

# 20. Non-Negotiable Acceptance Criteria

The redesign is accepted only if:

- [ ] The graph remains the dominant visual feature.
- [ ] The product looks specifically related to VTubers, not generic cyber SaaS.
- [ ] Existing filters/timeline/inspector continue working.
- [ ] `AGENCY_ISLAND_COORDINATES` block is byte-identical.
- [ ] No viewer-level private data is introduced into public frontend.
- [ ] No research terminology is made more causal or stronger than the data supports.
- [ ] 2026 is clearly YTD.
- [ ] No major UI control uses emoji as its primary icon.
- [ ] Desktop layout feels premium at 1440px.
- [ ] Tablet and mobile have intentional drawer/bottom-sheet behavior.
- [ ] `prefers-reduced-motion` is supported.
- [ ] There are no console errors introduced by the redesign.
- [ ] Existing tests pass.
- [ ] `git diff --check` passes.
- [ ] protected coordinate hash matches expected value.

---

# 21. What Not To Do

Do not turn this into:

- generic purple SaaS
- Blade Runner / cyberpunk HUD
- anime wallpaper site
- pastel kawaii toy UI
- casino neon
- esports dashboard
- Apple clone
- card-grid analytics template

Do not overload the UI with:
- glow everywhere
- glass everywhere
- gradients everywhere
- meaningless particle effects
- looping animations
- oversized marketing copy

The aesthetic should be **specific, atmospheric, and controlled**.

---

# 22. Codex Execution Instruction

Use this file as the authoritative visual design contract.

Before editing frontend:

1. Read `DESIGN.md`.
2. Inspect `web/index.html`, `web/styles.css`, and relevant sections of `web/app.js`.
3. Activate:
   - `frontend-design`
   - `frontend-skill`
   - `gpt-taste`
4. Use `canvas-design-codex` only for canvas/graph rendering work.
5. Use `ui-ux-pro-max` during final QA, not as a competing art director.
6. Preserve all backend/data/security work currently on `main`.
7. Commit and push frontend changes by logical milestone.
8. Do not force push.

Suggested commits:

```text
design(web): establish prismatic constellation design system
feat(web): redesign observatory shell and control dock
feat(web): upgrade vtuber inspector and timeline interactions
feat(web): improve graph visual states without changing layout coordinates
fix(web): add responsive and reduced-motion behavior
design(research): align research dashboard with observatory identity
test(web): add visual and interaction regression checks
```

Final response must include:
- screenshots / browser QA evidence if available
- files changed
- responsive checks
- performance notes
- protected coordinate hash
- test/build results
- commit SHAs
