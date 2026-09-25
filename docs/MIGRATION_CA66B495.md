# ThaiVtuber_DATA migration from ca66b495

Source: `Icezaza2543/ThaiVtuberSNA` commit `ca66b495f53538c1cfa4d6126440f12bce26e63f`, file `data/bootstrap.json`.

Target: spreadsheet `ThaiVtuber_DATA` (`1mScOlcwCt8Ewh2f53_idCv-SYsFwcC9YfdoFeHs17E8`).

Writer: `scripts/migrate_canonical_sheet.py`. Rerun is an upsert by stable ID. A second run appended 0 rows on every core tab.

## Counts

| Entity | Source bootstrap | Sheet after migration | Missing source IDs | Duplicate IDs |
| --- | ---: | ---: | ---: | ---: |
| Personas | 895 (873 verified) | 895 | 0 | 0 |
| Accounts | 4721 | 4721 | 0 | 0 |
| Account links | 2692 | 2692 | 0 | 0 |
| Affiliations | 14 | 14 | 0 | 0 |
| Organizations | 0 table; 8 distinct affiliation names | 8 | n/a | 0 |
| Lifecycle events | 34 | 34 | 0 | 0 |
| Aliases | no table | 0 | 0 | 0 |
| Continuity links | 0 | 0 | 0 | 0 |
| Review queue | 1402 | 2271 | 0 source ids | 0 |
| Discovery runs | 2035 | not a canonical tab | — | — |
| Discovery hits | 6362 | not a canonical tab | — | — |
| Candidates | 1205 | 857 without a canonical account are review rows | — | — |

Orphan account links, affiliations, and lifecycle events: 0.

Regenerated IDs for entities that already had an ID: 0.

## Baseline differences (source wins)

The older sanity baseline does not match this snapshot on discovery:

- discovery rows 2238 and batches 284 are not tables in this bootstrap. The snapshot has 6362 `discovery_hits` and 2035 `discovery_runs`.
- exact-match 959 is not a column or table here.
- discovery-only unique accounts 884 versus 857 candidates queued. The writer skips a candidate when `account_id` is already canonical or the candidate URL already belongs to a canonical account. Those rows are not merged into new personas.

Personas 895, verified 873, accounts 4721, affiliations 14, and lifecycle events 34 match the baseline.

## ID rules

- `persona_id`, `account_id`, `link_id`, `affiliation_id`, `lifecycle event id`, and source `review_queue.id` are copied.
- Organization IDs are new because the source stores a name only: `org_` + SHA-256 of the casefolded, whitespace-collapsed name, first 20 hex chars.
- Discovery review IDs are `rq_` + `candidate_id`.
- Multi-persona and platform exceptions use `rq_multipersona_` / `rq_dupplat_` / `rq_plat_` plus a hash of the source reason.

## Mapping exceptions

- `needs_evidence` review status is stored as `pending`. Source queue status `resolved` is stored as `closed` (21 rows). Original status remains in notes.
- Platforms outside the sheet enum (`litlink`, `kick`, `linktree`; 5 accounts) are `other`, with the source platform in `REVIEW_QUEUE`.
- `id_namespace=handle` (1461 accounts): `platform_id` is left blank so a handle is not stored as a stable platform ID. The handle and canonical URL are kept. Finder also matches `platform + canonical_url`.
- No duplicate non-empty `(platform, platform_id)` groups.
- 7 accounts have more than one non-rejected open persona link. All links were kept. They are `P1` review rows. No persona was merged.
- Link type is `former` when `valid_to` is set, otherwise `official`.
- Alias rows were not invented. `canonical_name` equals `name` for every persona.
- Continuity stays empty. There is no continuity edge to cycle-check.

## Finder

`FINDER_INBOX` headers match ThaiVtuberFinder inbox v2 (20 columns). Existing inbox rows were not modified (1353 candidate ids at inspect time). Finder reads `PERSONAS`, `ACCOUNTS`, and `ACCOUNT_LINKS` by header name and writes only `FINDER_INBOX`.

## Still legacy

Do not delete `data/bootstrap.json`, the DuckDB registry, or the older workbook `ThaiVtuber_SNA` (`1H876HyqxkOEYJGczctP5G-ZNAZv22jzViw787h441fE`). Network edges, evidence bodies, discovery hits, and legacy claims are not canonical tabs in `ThaiVtuber_DATA`.

`SYSTEM.migration_core_complete=true`. `migration_parity_status=pass_with_documented_exceptions`.
