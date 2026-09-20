---
name: registry-pages
description: Use when connecting registry data to a public static frontend, exporting reviewed creator records, or deploying this repository to GitHub Pages.
---

# Registry frontend and Pages
Read AGENTS.md and docs/frontend-handoff.md. Generate data with
`python scripts/maintenance/export_frontend.py`; never import the original tables,
intake, reviews, environment files or browser profiles into the frontend.

Separate inventory, reviewed personas, published account pairs and dated activity.
Reviewed association is not platform certification, current control or live status.
Keep unknown dates, intervals and shared-account semantics. No audience graph or
popularity ranking without a separate approved dataset supporting those claims.

Build web/ as a static app in THIS repo. For Vite, use base
/ThaiVirtualCreatorRegistry/, base-aware paths and hash routes. No server runtime,
API key, Grok client, private GitHub fetch in the browser, or Vercel deployment.

Inspect repository visibility and Pages settings using authorized GitHub tools.
Private sources require an eligible GitHub plan; public Pages exposes uploaded
files even when the source repo is private. Never change visibility, billing or
permissions as a workaround. If blocked, finish the build and state the exact
hosting blocker instead of inventing a URL or switching providers.

CI: checkout -> Python export -> npm ci in web -> build -> upload ONLY web/dist
using official Pages actions -> deploy-pages. Use contents:read for build,
pages:write/id-token:write for deployment, github-pages environment and deployment
concurrency. Use current official action versions; preserve existing validation.
Never upload repository root. Avoid recurring one-off workflows and generated
JSON commits. Browser-check search, filters, detail/reload under the repository
base, inspect published artifacts, then verify the actual deployment URL.

References:
https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
