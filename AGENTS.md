# Working in ThaiVirtualCreatorRegistry (ThaiVtuberSNA)

> **Repository Status:** Backend Data Collection Worker & Pipeline Engine powering
> **[ThaiVtuberMaster](https://github.com/Icezaza2543/ThaiVtuberMaster)**.

This is a **public-persona registry**, not a census of private people. Source of
truth: the **ThaiVtuber_DATA** Google Sheet (`1mScOlcwCt8Ewh2f53_idCv-SYsFwcC9YfdoFeHs17E8`;
tabs PERSONAS, ACCOUNTS, ACCOUNT_LINKS, ORGANIZATIONS, AFFILIATIONS, ...).
`data/registry.json` no longer exists; the local DuckDB is a derived working copy.
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

## Handoff — 2026-09-27

Canonical writes go to ThaiVtuber_DATA through scripts in `scripts/` (all dry-run
unless `--write`, append/update only, idempotent — re-running writes 0 rows):

| Script | Purpose |
|---|---|
| `import_vtuberthaiinfo_base.py` | VtuberThaiInfo talents → personas/accounts/links (trusted base) |
| `resolve_vtuberthaiinfo_review.py` | Owner decisions on the base conflicts (merges, shared channels) |
| `import_vtuberthaiinfo_affiliations.py` | VtuberThaiInfo memberships → ORGANIZATIONS/AFFILIATIONS |
| `import_easydonate_links.py <file>` | Codex EasyDonate research files → accounts/links/personas |
| `fix_slug_persona_names.py` | Replace slug display names with the linked YouTube title |
| `reconcile_884.py` | 884-account screening → FINDER_INBOX (dedupes by platform+ID/handle) |
| `sync_canonical_to_sna_sheet.py` | Append new verified accounts to ThaiVtuber_SNA (VTUBERS/TWITCH_VERIFIED/TIKTOK_VERIFIED) for Master |

State on 2026-09-27: 2,457 personas (2,425 verified); 6,261 accounts; 5,043 account links;
EasyDonate VTuber category fully reviewed (rounds 1–6, files
`intake/consolidated/easydonate-links-2026-09-2*.jsonl` / `-10-01.jsonl`);
175 organizations, 661 affiliations. New VTUBERS rows were appended with
`enabled=False` so SNA collection quota is not consumed until the owner enables them.

EasyDonate: store slug/URL only, never payment data. The official API
(`api.easydonate.app`, `read:creator`) only resolves creators with creator
profiles; most donation pages 404 there. easydonate.app pages must be browsed
normally — no Cloudflare bypass.

Master refresh: `python scripts/sync_canonical_to_sna_sheet.py --write --update-names`,
then in ThaiVtuberMaster `python scripts/manage.py sync`. Master is not deployed yet
(owner decision); do not deploy without asking.

YouTube comment census + daily metrics (`collector/yt_comment_census.py`, README
"YouTube comment census"): runs 24/7 on the owner's PC as a scheduled task, free quota
only, Shorts skipped, comment text never stored, data in `%LOCALAPPDATA%\ThaiVtuberSNA`.
Do not start a second writer on `yt_comments.duckdb`; use `... status`.
Loyal-viewer SNA computation is intentionally **not** built yet: the owner will first
review the current SNA output for thin coverage or odd behaviour.

ThaiVtuber_SNA sheet was cleaned on 2026-09-26 (9 tabs remain; private/raw tabs are in
the local `sna_archive.duckdb`, the only copy of legacy viewer data).

Verify production Finder after sheet writes:
`MSYS_NO_PATHCONV=1 railway ssh -- finder verify -config /app/config/finder.json`
(expects `canonical_invariant_ok: true`, `duplicate_inbox_rows: 0`).

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
- Append newly verified canonical accounts to the shared Google Sheet (`ThaiVtuber_SNA`: `1H876HyqxkOEYJGczctP5G-ZNAZv22jzViw787h441fE`) with `python scripts/sync_canonical_to_sna_sheet.py --write`, then run `python scripts/manage.py sync` in `ThaiVtuberMaster`.
- Or export CSVs with `python -m thaivtubersna export --output <new_dir>` (reads the local DuckDB, which may lag the canonical sheet) and ingest with `python scripts/manage.py sync --from-csv <new_dir>`.

Do not duplicate website UI features in this worker repository. Focus here on crawler completeness,
evidence rigor, graph accuracy, and reliable data exports for `ThaiVtuberMaster`.

