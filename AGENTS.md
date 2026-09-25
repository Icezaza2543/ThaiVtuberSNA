# Working in ThaiVirtualCreatorRegistry (ThaiVtuberSNA)

> **Repository Status:** Backend Data Collection Worker & Pipeline Engine powering
> **[ThaiVtuberMaster](https://github.com/Icezaza2543/ThaiVtuberMaster)**.

This is a **public-persona registry**, not a census of private people. Source of
truth: `data/registry.json` (13 SQL-backed tables). Python 3.11+ stdlib is enough.
This repository acts as the **data engine**: responsible for crawlers, discovery,
first-party evidence review, SNA network overlap computation, and syncing data to
Google Sheets (`ThaiVtuber_SNA`) / CSV exports consumed by `ThaiVtuberMaster`.

This file is the shared briefing for **every agent** (Antigravity, Grok, Codex,
Claude, Gemini, GPT). Read it before editing data or claiming coverage. Full specs
stay in `docs/`; do not duplicate them — follow the pointers below.

## Read first

| If you are… | Read |
|---|---|
| Changing table semantics / IDs | `docs/data-model.md`, `schemas/registry.sql` |
| Adding or linking creators | `docs/review.md`, `docs/taxonomy.md` |
| Collecting new names / platforms | `docs/discovery.md`, `docs/provenance.md` |
| Touching YT→X→hub mapping | `docs/data-pipeline.md`, `docs/architecture.md` |
| Applying JSON to the registry | `reviews/README.md`, `reviews/pending/README.md` |

## Hard rules

- Keep **platform accounts, personas, activity, and discovery counts distinct**.
- Do **not** infer private persons or auto-link personas from similar names/handles.
- **Trusted base directory (owner decision 2026-09-26):** each talent in the
  VtuberThaiInfo archive (`https://vtuberthaiinfo-archive.pages.dev/talent`) is a
  distinct, verified Thai virtual-creator persona, and its listed YouTube/Twitch
  main channels are that persona's official accounts. Import with
  `python scripts/import_vtuberthaiinfo_base.py` (dry-run unless `--write`).
  Match to existing personas by stable account ID only; talents that hit 2+
  personas or share a channel go to owner review, not auto-merge.
- Our own discovery (Finder, crawls) adds creators beyond that base. Other
  accounts we find are attached to an existing persona via owner cross-link
  evidence; create a new persona only for a genuinely new creator.
- **Account links and continuity** outside the base still need first-party public
  evidence (owner bio, official profile cross-link, agency statement). HoloList /
  wikis / search indexes other than the trusted base are `secondary_source` only.
- Inactive or retired creators still count; activity is lifecycle, not scope.
  Thai-language video content is valid `thai_language` evidence.
- Preserve event history and exact/coarse/unknown date precision. Do not invent
  a calendar day from a month/year.
- Use **candidate intake + reviewed change files**. Validate before commit.
- API / live discovery creates **candidates**. Run live crawls only when the
  owner asks for data collection; a software-only request is not that.
- Keep tokens, chats, viewer lists, and login-only data out of the repo.
- Keep README commands aligned with tested code.
- Export snapshots to a **new** directory. Do not overwrite `dist/` snapshots.
- License stays Internal Research / All Rights Reserved unless the owner says
  otherwise.

## Verification is platform-independent

A creator may be verified with **only Twitch, only TikTok, or one account on any
supported platform**. YouTube, X, a hub, multiple accounts, and follower counts
are neither requirements nor sufficient evidence of being a virtual creator.
Use reviewed virtual presentation, Thai relation and ownership evidence instead.
One first-party owner profile may support both persona scope and ownership of
that same account; an outbound/cross-platform link is not mandatory. Cross-links
are evidence for additional account associations, not an admission criterion.

Do not conflate a resolved account or `candidates.review_status=verified` with
verified virtual-creator scope. `inspect account/candidate` exposes `verification`
separately. Use `queue --kind account_scope` to see missing scope/ownership reviews
across all accounts, including standalone creators with no legacy YouTube issue.
`needs_evidence` means unknown/pending, **not** “not a virtual creator”. These are
retained-review inventory statuses, not a claim about current control/activity.

## How identities enter the registry

1. Find a **public URL** (never a guessed handle).
2. Add a `candidate` (handle-only) or `account` (stable ID).
3. Persona stays `needs_evidence` until Thai relation + virtual presentation
   are reviewed.
4. `account_links` stay `needs_evidence` until first-party ownership evidence is
   reviewed. The account's own persona profile can suffice; another platform is not required.
5. Apply via `reviews/*.json` → dry-run → apply → `reviews/applied/`.

Stable IDs (accounts table):

| Platform | `id_namespace` | `platform_id` |
|---|---|---|
| youtube | `channel_id` | `UC` + 22 chars |
| twitch | `user_id` | numeric |
| tiktok | `web_user_id` | numeric public embed id |
| x | `handle` | handle without `@` (until user id exists) |
| facebook | `handle` or `profile_id` | page handle or numeric id |
| instagram | `handle` | handle without `@` |

Handle-only YouTube `@…`, Twitch login, and TikTok `@…` **stay candidates**.
A recycled handle is not the same account.

Thai relation values: `thai_language`, `self_declared_thai`, `thai_community`,
`thai_agency`, `multiple`, `unknown`. Do not set `verified` on a persona with
`unknown` relation or empty roles.

## Commands

```sh
python -m pytest tests/ -v
python -m thaivtubersna validate
python -m thaivtubersna run
python -m thaivtubersna worker
python -m thaivtubersna export --output dist/export/
python -m thaivtubersna queue
python -m thaivtubersna apply reviews/CHANGE.json --dry-run
python -m thaivtubersna apply reviews/CHANGE.json
python migrate.py --verify
```

`--dry-run` must pass before a real apply. Failed applies do not write
to the database. Do not overwrite an existing `dist/` snapshot.

## Creator-link pipeline (2026-09-16)

Stages write JSONL under `intake/consolidated/` (date in the filename):

| Stage | File | Meaning |
|---|---|---|
| 1 | `youtube-to-x-YYYY-MM-DD.jsonl` | YouTube → official X (first-party only) |
| 2 | `x-profile-links-YYYY-MM-DD.jsonl` | Official X → hubs + platform URLs |
| 3 | `creator-platform-links-YYYY-MM-DD.jsonl` | Hub crawl → platform URLs |
| 4 | `reviews/pending/creator-link-map-*.json` | Proposals; not applied until reviewed |

Official X requires owner cross-link (X bio/website ↔ YouTube About, or both on
the same Carrd/Linktree). Similar name/handle is not enough. Talent personal X
beats agency X when both exist. Do not substitute a successor handle for a 404
(e.g. do not replace `@TamaOniiSanCh` with `@TamaOniiSan21PM`).

Latest-wins on `youtube_account_id`. Files named `*-pass1-*` / `*-remaining-*`
are partial runs, not the canonical set. `map-creators` glob must ignore those.

The legacy Grok `batch_resolve` API path requires `XAI_API_KEY`. The owner now
uses Grok directly; do not provision a key or make API usage a prerequisite for
frontend work. Existing reviewed data is enough to build the site.

## Handoff — 2026-09-16 late evening

The 28-lead first-party review is **complete and applied**. Do not treat all 28
as unreviewed anymore.

Applied review:
`reviews/applied/2026-09-16-new-thai-vtuber-leads-first-party-review.json`

Source leads:
`intake/consolidated/new-thai-vtuber-leads-2026-09-16.jsonl`

### Current registry status after the 28-lead review

- Total personas remain 895; **853 verified**.
- Total accounts: **4,719**.
- Accounts by platform: YouTube 1,399; Twitch 845; TikTok 962; X 1,149;
  Facebook 211; Instagram 120; GankNow 28; Kick 2; Linktree 1; lit.link 2.
- Verified accounts: YouTube 673; Twitch 384; TikTok 685; X 633;
  Facebook 135; Instagram 80; GankNow 23; Kick 2; Linktree 1; lit.link 1.
- Candidates: 301 total; 255 verified/promoted state, 46 still `needs_evidence`.

### What changed in the 28-lead review

- 34 candidate resolution attempts.
- **18 candidates promoted** to stable-ID accounts:
  - YouTube 13
  - TikTok 5
  - Twitch 0
- **20 accounts added** total (includes 2 extra first-party TikTok accounts from
  official links/hubs).
- **20 persona↔account links verified**.
- **8 personas newly verified**:
  - Liyin
  - Zabrina
  - Joro Gumo
  - EMIL
  - Hakka
  - Kyoya Keiran
  - Nihr Farfalla
  - Cynthia

Strong examples used first-party evidence only: Hakka YouTube About explicitly
states `Virtual YouTuber TH`; Zabrina/Cynthia/Nihr self-identify as virtual/VTuber
on owner profiles; Joro Gumo and Kyoya use first-party TikTok/Linktree/lit.link
chains; EMIL has owner-written YouTube lore plus direct X cross-link.

### Still unresolved from this 28-lead batch

16 candidate URLs did not resolve to stable IDs and remain unpromoted:

- YouTube: 8
- Twitch: 5
- TikTok: 3

Do not force these via name/handle similarity. Retry only when the public
platform profile yields the platform stable ID.

The remaining 20 personas from the 28-lead set are **not automatically
verified**. They need first-party evidence for Thai relation + virtual
presentation and explicit account ownership.

### Pipeline status carried forward

- Stage 2 canonical: `intake/consolidated/x-profile-links-2026-09-16.jsonl`.
- Stage 3 canonical: `intake/consolidated/creator-platform-links-2026-09-16.jsonl`.
- Stage 4 classify: `reviews/pending/creator-link-map-2026-09-16.json`.
- First-party Stage 4 apply:
  `reviews/applied/creator-link-map-2026-09-16-apply-first-party.json`.
- About 944 first-party X/other accounts remain unlinked where the YouTube seed
  has no verified persona; do not auto-link by handle similarity.
- Destinesia `@DestinesiaP` was hijacked; not an official X.
- FloraVtuberTH had name-only match — leave unresolved.

### Next useful work

1. Review first-party evidence for the remaining 20 personas from the 28-lead set.
2. Retry the 16 unresolved stable-ID candidate URLs without guessing replacements.
3. Link verified personas to already-collected first-party X/hub accounts only
   where explicit cross-link evidence exists.
4. Kick/GankNow now have first-party URLs in-registry; still no census. Do not
   scrape extra creators unless asked.
5. `vtuberthai.com` previously returned Cloudflare 502; retry only if useful.

The two one-off GitHub Actions workflows used for this review were deleted after
successful apply. `.github/workflows/validate.yml` is the persistent workflow.

## File map

Use `docs/data-layout.md`. Current reports are only in `reports/current/`;
refresh them offline with `python scripts/maintenance/refresh_reports.py --as-of YYYY-MM-DD`.
Legacy raw observations remain pinned at their original paths. Old queues/partial
runs are in `intake/archive/`; historical review files are bundled losslessly in
`reviews/archive/legacy-reviews-2026-09-16.zip`.
`reviews/pending/README.md` indexes the remaining proposal sets. Do not treat a
classifier row or archived review as unfinished work without comparing it to the registry.
Utilities are grouped under `scripts/collect/`, `scripts/review/`, `scripts/maintenance/`.
Do not recreate removed one-off scripts or duplicate an applied file into pending.
The cleanup changed no registry records or evidence captures.

## Validation before every data commit

```sh
python -m unittest discover -s tests -v
python -m registry validate
python -m registry report --as-of YYYY-MM-DD
```

Inspect data applies when changing canonical records. Do not commit data lockfiles,
Playwright profiles, or `dist/sna/`. Track `web/package-lock.json` for npm ci;
it is not a temporary data lockfile.

## Master Frontend vs. Local Worker Web UI

The official public-facing master website has transitioned to **[ThaiVtuberMaster](https://github.com/Icezaza2543/ThaiVtuberMaster)**
(a lightweight, sheet-backed web application with 5 views: Home, VtuberRecord, SNA, Data Analytics, and Financial Analytics).

The local `web/` directory in this repository remains available as a local staging and
verification environment for graph mathematics and registry debugging. To feed data to
`ThaiVtuberMaster`:
- Update the shared Google Sheet (`ThaiVtuber_SNA`: `1H876HyqxkOEYJGczctP5G-ZNAZv22jzViw787h441fE`) via `scripts/maintenance/prepare_analytics_sheets.py`.
- Or generate direct CSV exports via `python scripts/maintenance/export_to_master.py --output <target_dir>` which can be ingested by `ThaiVtuberMaster` using `python scripts/manage.py sync --from-csv <target_dir>`.

Do not duplicate website UI features in this worker repository. Focus here on crawler completeness,
evidence rigor, graph accuracy, and reliable data exports for `ThaiVtuberMaster`.

