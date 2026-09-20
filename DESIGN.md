# Luxury VTuber Editorial

## Purpose and visual direction
A Thai-first public virtual-creator directory, not an audience-overlap product or
popularity ranking. Keep it distinct from ThaiVtuberSNA; build in this repo's web/.
Ivory paper, deep forest panels and muted gold details. Refined and welcoming,
not a generic SaaS dashboard or black-and-gold casino. Make search useful first.
One signature element: an editorial creator composition and an elegant platform rail.

| Token | Value | Role |
|---|---|---|
| canvas | #F5F3EE | Main background |
| surface | #FBFAF7 | Reading surface |
| surface-muted | #EEEAE1 | Grouped content |
| forest | #1A221F | Navigation and selected states |
| ink | #181A18 | Body text |
| muted-ink | #68655D | Secondary text |
| gold | #A28143 | Decorative accent, not automatic small-text color |
| gold-soft | #E9DEC7 | Soft highlight |
| border | #D5D0C5 | Separators |

Use dark ink/forest for small text; check actual contrast. Typography: Noto Sans
Thai for Thai, Cormorant Garamond for selected English display headings, Inter for
Latin UI and tabular/lining numbers. These are deliberate project choices and
override generic font prohibitions in skills. Do not letter-space Thai. Provide
fallbacks and appropriate Thai line height. No font binaries are installed here.

Use a restrained editorial grid, generous hero spacing and denser useful results.
Avoid identical cards around every paragraph, decorative labels, noisy gradients,
scroll hijacking and perpetual motion. Respect reduced-motion and keyboard focus.

## Functional surfaces
- Directory: Thai/English name and handle search, platform/role/format filters,
  result count, clear filters, loading/error/empty states.
- Creator detail: shareable hash route, reviewed account links and sources,
  observation dates, reviewed affiliations and events when available.
- Platform coverage: separate all catalog records from reviewed published identities.
  Platform combinations mean presence, not shared audience.
- Methodology: review meaning, data timestamp, limitations and a correction path
  only when a real destination is configured.

No invented images, subscribers, live state, lore, agency labels or debut dates.
The export has no licensed avatar field: use elegant initials/geometric fallbacks,
not photos scraped from guessed handles. Unknown dates stay unknown.

## Implementation and visual check
Reuse existing frontend technology if present. Otherwise use Vite, React,
TypeScript and a small CSS-token/component set in web/. Do not add Next.js,
a backend, authentication, a database, or a large UI generator by default.
Track web/package-lock.json for npm ci; ignore builds, dependencies and generated data.
Use hash routing and Vite base /ThaiVirtualCreatorRegistry/. All asset/JSON paths
must respect the base. Render data as text, never arbitrary HTML.
Check real screens at 390, 768 and 1440 px: search, filter, detail, back, route reload,
keyboard use, long Thai names, empty results and JSON failure. Fix material issues,
not endless cosmetic variants or hundreds of micro-tests.
