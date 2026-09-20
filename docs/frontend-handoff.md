# Frontend handoff for Antigravity

## Scope
Build a luxurious Thai-first creator directory in web/ and host it through GitHub
Pages from Icezaza2543/ThaiVirtualCreatorRegistry. Do not modify ThaiVtuberSNA.
Read AGENTS.md, DESIGN.md and .agents/README.md. This preparation installs skills
and a real-data exporter; it does not claim the UI or a live deployment exists.

## Data contract
Run from repo root:
```sh
python scripts/maintenance/export_frontend.py
```
Output: web/public/data/registry.json (generated, gitignored). The exporter
loads and validates the canonical source in memory and never saves it. It emits
an explicit allowlist, not original tables or a review payload.

| Field | Meaning |
|---|---|
| schema_version | Frontend projection v1 |
| generated_at | Export time, not a profile refresh |
| source_registry_sha256 | Source fingerprint |
| inventory | All catalog counts, including records not cleared for identity display |
| published | Reviewed personas, accounts and distinct persona-account pairs |
| creators[] | Reviewed personas with reviewed safe account URLs |
| accounts[].ownership_evidence[] | Sources/observation times and preserved date intervals |
| affiliations[] / events[] | Reviewed organization/date facts only |

IDs are strings; never turn large platform IDs into JavaScript numbers. Render
labels as text, not HTML. No avatars, rankings, live status, raw bios, private
identities, reviewer names, internal notes, captures, viewer IDs, overlap or chats
are in this payload. Missing means unknown. A reviewed account association can
be historical or undated; do not imply current ownership or recent activity.
Do not require YouTube or three-platform membership for directory inclusion.
Use published counts for directory results and separately label inventory counts.
Unresolved identity/stable-ID leads remain unresolved; do not auto-verify them
or invent data to fill UI panels.

## Execute sequentially without repeated approval gates
1. Reuse an existing web/ if present; otherwise Vite + React + TypeScript, small
   CSS-token/component set and hash routes. Preserve the Python project.
2. Export real data; implement search, filters, creator detail, platform presence,
   reviewed timeline when present, and methodology. Not just a landing page.
3. Apply DESIGN.md: ivory/muted-gold/deep-forest luxury editorial style, readable
   Thai, deliberate English display and tabular numbers. No fake profile artwork.
4. Build and browser-check at 390/768/1440 px under /ThaiVirtualCreatorRegistry/.
   Exercise keyboard, search/filter/detail/back, deep-link reload and empty/error.
5. Configure GitHub Pages in the same repo; export/build in CI; upload web/dist
   only. Verify the actual returned URL and a creator-detail route.

Track web/package-lock.json for reproducible npm ci. Ignore node_modules, dist,
.vite, generated JSON, screenshots and browser state. Do not create scratch scripts
or run the full Python suite after every visual edit. Use build/browser checks.

## Hosting boundary
At preparation this repo is private and has_pages is false. GitHub Pages supports
private sources on eligible Pro/Team/Enterprise plans; account plan eligibility
has NOT been checked here. Inspect with authorized local tools/settings. Do not
change visibility or purchase/upgrade a plan. Finish the UI/build if publication
is blocked and report the exact setting or permission needed.

Vite base: /ThaiVirtualCreatorRegistry/. JSON path:
`${import.meta.env.BASE_URL}data/registry.json`. Use hash routes (no server rewrites).
No browser calls to private GitHub endpoints or embedded tokens.
Use current official configure-pages/upload-pages-artifact/deploy-pages actions,
minimal permissions, github-pages environment and deployment concurrency.
Never publish repository root, data/, intake/, reviews/ or .agents/.

Official references:
https://antigravity.google/docs/skills
https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

## Completion report
Report build/browser/deployment separately, actual commit/URL only when verified,
export counts from the run and any hosting blocker. Update the existing handoff
or AGENTS.md instead of creating a new pile of status reports.

## Verified preparation snapshot

Source commit: `deed13910e0e2d8a6aef2988e5918c974154ab3d`. Registry and retained capture bytes unchanged.

```json
{
  "inventory": {
    "personas": 895,
    "verified_personas": 853,
    "accounts": 4719,
    "accounts_by_platform": {
      "facebook": 211,
      "ganknow": 28,
      "instagram": 120,
      "kick": 2,
      "linktree": 1,
      "litlink": 2,
      "tiktok": 962,
      "twitch": 845,
      "x": 1149,
      "youtube": 1399
    }
  },
  "published": {
    "personas": 853,
    "accounts": 2617,
    "persona_account_pairs": 2648,
    "reviewed_link_records": 2648,
    "excluded_unsafe_url_pairs": 0,
    "accounts_by_platform": {
      "facebook": 135,
      "ganknow": 23,
      "instagram": 80,
      "kick": 2,
      "linktree": 1,
      "litlink": 1,
      "tiktok": 685,
      "twitch": 384,
      "x": 633,
      "youtube": 673
    }
  },
  "export_bytes": 1371483
}
```

## Frontend implementation & validation status (2026-09-17)

- **Frontend Tech Stack**: Vite + React 19 + TypeScript in `web/` with Luxury VTuber Editorial CSS design tokens (`#F5F3EE` canvas, `#1A221F` forest, `#A28143` gold, `#FBFAF7` surface).
- **Typography**: Noto Sans Thai for Thai, Cormorant Garamond for display accents, Inter for UI & lining numbers.
- **Routing & Base**: Hash routing (`#/`, `#/creator/:id`, `#/presence`, `#/methodology`) with Vite base `/ThaiVirtualCreatorRegistry/`.
- **Pages & Features Implemented**:
  - Directory: Real-time search across Thai/Latin names and account handles, filter chips for platform, role, format, and Thai relation, clear filters, sort dropdown, and empty states.
  - Creator Detail: Shareable hash route, bespoke monogram seal, verification proofs, stable IDs (retained as strings), external official profile links, ownership validity intervals, affiliations, and lifecycle timeline.
  - Platform Presence: Explicitly separated inventory catalog (4,719 accounts, 895 personas) from published verified accounts (2,617 accounts, 853 personas), platform breakdown table with percentage ratios.
  - Methodology & Limitations: 5-part guide explaining public-persona scope, first-party cross-link requirements, stable ID namespaces, provenance timestamp and SHA256 checksum, explicit non-features (no popularity ranking, no live tracking, no audience graph), and correction submission path via GitHub issues and JSON change reviews.
- **Build & Lint Checks**:
  - `npm run build` succeeds (281.9 kB JS, 14.3 kB CSS).
  - `oxlint` passes with 0 errors and 0 warnings.
  - Full Python suite (`python -m unittest discover -s tests -v`) passes 105/105 tests.
  - Registry validator (`python -m registry validate`) passes with `valid: true`.
- **Browser Validation**:
  - Verified in Chromium subagent at Desktop (1440x900), Tablet (768x1024), and Mobile (390x844).
  - Tested search ("Kaen" / "คาเอ็น"), platform filter ("YouTube"), clear filters, creator detail navigation, browser back/forward, deep-link reload (`#/creator/persona_1ca6fdc18136ed417ae2`), empty query fallback, and responsive compact header labels at 390px.
- **GitHub Pages Workflow & Deployment Constraint**:
  - CI workflow configured at `.github/workflows/pages.yml` with official Pages actions.
  - Hosting constraint: The repository `Icezaza2543/ThaiVirtualCreatorRegistry` is currently `visibility: PRIVATE`. GitHub API returns HTTP 422: `Your current plan does not support GitHub Pages for this repository` (private GitHub Pages requires GitHub Pro/Team/Enterprise or public repository visibility). As instructed, repository visibility and billing were not modified. The frontend build and CI workflow are ready to deploy automatically as soon as Pages is enabled on the repository.
