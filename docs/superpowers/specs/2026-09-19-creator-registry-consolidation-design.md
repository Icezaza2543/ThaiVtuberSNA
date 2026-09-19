# Creator Registry Consolidation Design

**Date:** 2026-09-19

**Status:** Design approved in chat; written specification awaiting review

**Scope:** Creator identity, account eligibility, registry storage, and registry consumers

## 1. Purpose

ThaiVtuberSNA currently represents creator identity in several overlapping files. The same 1,370 YouTube channels appear in `data/thai_vtuber_registry.json`, `data/thai_vtuber_registry.csv`, and `data/registry_vtubers.csv`; `data/master_creators.json` uses a different persona/account schema and still carries stale discovery state. Consumers read these files directly, so a metadata correction can leave the project internally inconsistent.

This refactor will establish one normalized registry in which one creator record represents one virtual persona or character form and each platform account belongs to exactly one creator. It will combine the trusted 1,370-channel baseline with all 393 accounts accepted during the 2026-09-19 screening and human-review workflow. It will also resolve identity for every accepted account using public evidence and the authorized read-only YouTube Data API before the canonical registry can be published.

The final persona count is intentionally not fixed at 1,763. Some of the 393 accepted accounts are additional platform accounts for an existing persona, and some accepted accounts may resolve to the same new persona.

## 2. Goals

1. Make `data/registry/creators.json` the only authoritative local creator registry.
2. Model creators separately from platform accounts and evidence.
3. Preserve all 1,370 trusted YouTube Channel IDs exactly once.
4. Include all 393 accepted new accounts exactly once after evidence-backed identity resolution.
5. Prevent name-only persona merges and prevent unresolved accounts from entering the canonical registry.
6. Route registry consumers through one validated `CreatorCatalog` interface.
7. Remove the obsolete registry copies after every consumer has migrated and equivalence checks pass.
8. Preserve frozen research cohorts, releases, private-data boundaries, and external control-plane state.

## 3. Non-goals

- Rebuilding the frozen 193-channel temporal target cohort.
- Rewriting frozen releases or historical research snapshots.
- Merging reincarnations, redebuts, or distinct character forms because they share a performer.
- Writing to Google Sheets, changing live-worker state, or touching quota/cursor/HMAC state.
- Inferring audience relationships for accounts that do not have a YouTube Channel ID.
- Treating an unavailable account as either a VTuber or a non-VTuber without evidence.
- Refactoring unrelated analytical, frontend, or collection modules beyond replacing their registry access.

## 4. Approved identity policy

The canonical entity is one virtual persona or character form. A creator may have multiple accounts on YouTube, Twitch, X, TikTok, Instagram, Facebook, Bluesky, Carrd, personal websites, and other platforms.

Accounts are linked to an existing creator only when at least one of these conditions is satisfied:

1. An official profile links directly to another official account belonging to that creator.
2. A stable platform identifier, especially a YouTube Channel ID, is identical.
3. The trusted registry contains a verified account-to-persona link supported by evidence.
4. Two official sources explicitly identify both accounts as belonging to the same named persona.

Display-name similarity, avatar similarity, agency membership, shared performer speculation, or an automated fuzzy score cannot establish identity on its own.

An accepted account becomes a new creator when its official material clearly identifies the represented persona and an evidence search finds no supported relationship to an existing creator. The resolution record must document the sources checked and the positive evidence that the account represents the new persona.

Reincarnations, redebuts under another character, and distinct character forms remain separate creators even if the performer is known to be the same person.

## 5. Authoritative inputs

The build consumes these inputs without modifying them:

- The trusted 1,370-row baseline currently stored in `data/thai_vtuber_registry.json`.
- `outputs/new-account-review-2026-09-19/all_884_screening_results.json`.
- `outputs/new-account-review-2026-09-19/human_review_decisions.json`.
- `data/entity_resolution/visual_identity_review.json`, used only for identity decisions that do not contradict the final eligibility review.
- Verified personas, accounts, links, and evidence in the trusted ThaiVirtualCreatorRegistry database.
- New public identity evidence collected during this refactor.

Eligibility precedence is:

1. The original 1,370 baseline is trusted as VTuber data and is not re-reviewed.
2. The 363 automated `VTUBER` decisions and 30 human `vtuber` decisions are accepted.
3. The 292 `TRUSTED_BASELINE` discovery candidates resolve to existing baseline accounts and add no duplicate account.
4. The 102 final exclusions do not enter the canonical registry.
5. The 94 unavailable accounts remain outside the canonical registry and remain explicitly unresolved.
6. Virtual-group, associated-account, organization, media, clip, and service accounts remain outside the individual creator catalog.

Raw review artifacts are immutable provenance. Compact review inputs required for reproducibility will be moved under `docs/evidence/creator-registry-review-2026-09-19/`; they are evidence, not competing registry sources.

## 6. Canonical file contract

`data/registry/creators.json` is a versioned object containing metadata and three normalized arrays.

```json
{
  "schema_version": 2,
  "dataset_name": "ThaiVtuberSNA Creator Registry",
  "identity_policy": "one virtual persona or character form per creator",
  "source_fingerprints": {},
  "counts": {},
  "creators": [],
  "accounts": [],
  "evidence": []
}
```

### 6.1 Creator record

Required fields:

```json
{
  "persona_id": "persona_stable_id",
  "canonical_name": "Display name",
  "aliases": [],
  "agency": "Independent",
  "lifecycle_status": "active",
  "eligibility": "vtuber",
  "identity_status": "verified",
  "source_class": "trusted_baseline",
  "evidence_ids": []
}
```

`persona_id` is stable across rebuilds. Existing trusted `person_id` values are retained when valid. New IDs derive deterministically from the resolved identity rather than array order or the build timestamp. A creator cannot exist without at least one account and at least one evidence reference.

### 6.2 Account record

Required fields:

```json
{
  "account_id": "account_stable_id",
  "persona_id": "persona_stable_id",
  "platform": "youtube",
  "platform_id": "UC...",
  "handle": "@handle",
  "url": "https://...",
  "display_name": "Display name",
  "account_status": "available",
  "is_primary": true,
  "eligibility_source": "trusted_baseline",
  "identity_resolution": "exact_platform_id",
  "evidence_ids": [],
  "metadata": {}
}
```

YouTube metrics from the baseline, including subscriber, video, and view counts, live inside `metadata` on the corresponding account. Platform-specific metadata may be absent; missing metrics are not converted to zero unless zero is an observed value.

Account uniqueness is enforced by stable platform identifier when available and otherwise by normalized canonical URL. An account must reference exactly one existing `persona_id`.

### 6.3 Evidence record

Required fields:

```json
{
  "evidence_id": "evidence_stable_id",
  "source_url": "https://...",
  "source_kind": "official_profile",
  "observed_at": "2026-09-19T00:00:00Z",
  "summary": "What this source establishes",
  "supports": ["account_ownership", "persona_identity"],
  "subject_ids": ["persona_stable_id", "account_stable_id"],
  "provenance": "public_web"
}
```

Evidence summaries preserve the meaning of the reviewed source without storing secrets, private viewer information, or full copyrighted pages.

## 7. Identity-resolution workflow

Identity resolution covers all 393 accepted accounts. Seventy-three already have non-conflicting legacy identity decisions; 320 require validation or new research. Existing exact local evidence currently links 27 of those 320 to a trusted persona. These figures are starting diagnostics, not final contract counts.

The resolver processes evidence in this order:

1. Exact platform ID and canonical URL matches.
2. Verified account links in the trusted registry database.
3. Official cross-links already captured in About text, Twitch panels, X profiles, TikTok evidence, Carrd, Linktree, and personal sites.
4. Read-only YouTube Data API lookups to resolve handles, Shorts/video URLs, channel ownership, descriptions, and stable Channel IDs.
5. Focused public web search and direct official-profile inspection for the remaining accounts.
6. Conflict detection across all asserted persona links.

The YouTube API client must use the existing secret-loading boundary, never print or persist the key, cache successful responses by resource ID, and record quota-unit estimates. Repeated builds reuse sanitized cached evidence. The API is not used for writes or account actions.

Each accepted account produces one resolution with:

- `existing_persona` or `new_persona`;
- resolved `persona_id`;
- the positive identity evidence;
- sources checked;
- resolution method;
- reviewer or automated rule name;
- conflict status.

The canonical build fails closed if an accepted account has no identity resolution, lacks evidence, maps to more than one persona, or references an excluded account.

## 8. Catalog access layer

`core/creator_catalog.py` provides the only runtime access to the canonical registry. It validates the schema during load and creates indexes for:

- `persona_id`;
- `(platform, platform_id)`;
- `(platform, normalized_handle)`;
- normalized canonical URL;
- YouTube Channel ID.

The public interface exposes creator lookup, account lookup, all accounts for a persona, eligible YouTube accounts, and deterministic export rows. Callers do not parse `creators.json` directly.

Collection and SNA code receives only accounts with `platform == "youtube"` and a valid Channel ID. Ecosystem and identity reporting may use all platforms. Frozen-cohort analysis continues to use the immutable target manifest and joins names or metadata through `CreatorCatalog` without changing cohort membership.

## 9. Migration and file consolidation

Migration uses a build-validate-switch-delete sequence:

1. Freeze hashes and counts of the trusted 1,370-row baseline and current registry consumers.
2. Preserve compact review evidence in the repository.
3. Complete identity research and produce a reviewed resolution ledger.
4. Build `data/registry/creators.json` deterministically.
5. Add `CreatorCatalog` and contract tests.
6. Migrate every direct reader of the old registries to `CreatorCatalog`.
7. Rebuild public web and analytical derived artifacts where required.
8. Verify baseline and accepted-account inclusion, exclusion boundaries, consumer equivalence, privacy, and deterministic rebuilds.
9. Remove `data/thai_vtuber_registry.json`, `data/thai_vtuber_registry.csv`, `data/registry_vtubers.csv`, and `data/master_creators.json` after no runtime or test consumer references them.
10. Update documentation so the canonical registry and frozen cohort have distinct roles.

The following similarly named files remain because they are separate contracts:

- `data/temporal/catalog/target_manifest.csv`: immutable 193-channel research cohort.
- `data/registry_checkpoint.json`: collection progress state.
- `data/registry_system.json`: control-plane health metadata.
- `config/seeds_vtuber.json`: discovery seeds.
- Frozen release manifests and datasets.

No Google Sheets sync or live-worker mutation occurs during migration.

## 10. Derived views

Flat CSV and public JSON outputs are generated views, never editable inputs. A deterministic exporter may produce:

- a YouTube account view for collectors and SNA;
- a public creator/account view for the web application;
- a compact compatibility view during migration only.

Generated views contain a source fingerprint referencing `creators.json`. CI rejects a committed derived view whose fingerprint or contents do not match a fresh export.

## 11. Validation and tests

Contract validation requires:

- exactly 1,370 unique baseline YouTube Channel IDs are preserved;
- exactly 393 accepted discovery accounts are represented once;
- all 292 trusted-baseline candidates resolve without adding duplicate accounts;
- none of the 102 exclusions appear;
- none of the 94 unavailable accounts appear;
- group, associated, organization, media, clip, and service accounts do not appear as individual creators;
- every account references one creator;
- every creator has at least one account and evidence record;
- every identity merge cites qualifying evidence;
- no stable account identifier or canonical URL is duplicated;
- the YouTube/SNA view contains only valid Channel IDs;
- a clean rebuild is byte-stable apart from explicitly excluded operational metadata;
- all migrated consumers produce equivalent results on the original 1,370-channel baseline;
- focused registry, collector, web-data, privacy, and release-boundary tests pass.

Before implementation, an isolated worktree will establish the branch's full-suite baseline with a temporary directory outside the repository. Completion requires no new failures relative to that baseline and all directly affected tests green. Existing unrelated branch failures are reported rather than hidden.

## 12. Error handling and auditability

The builder writes to a temporary file, validates the complete payload, and atomically replaces the canonical file. It never partially updates the registry.

Failures identify the affected discovery/account ID and evidence rule without logging credentials. Ambiguous links, missing evidence, duplicate IDs, excluded-account leakage, malformed URLs, and source-fingerprint mismatches stop the build. An identity conflict remains in the resolution ledger and cannot be silently converted into a new persona.

Every canonical build records input fingerprints, schema version, builder version, and deterministic counts. Raw public evidence remains available for audit, while the canonical file contains compact summaries and stable references.

## 13. Acceptance criteria

The refactor is accepted when:

1. Identity resolution is complete for all 393 accepted accounts.
2. `data/registry/creators.json` passes every canonical invariant.
3. Runtime and test code no longer reads the four obsolete registry files.
4. The obsolete files are removed after equivalence verification.
5. Frozen cohorts and releases remain byte-identical.
6. No private data, API key, quota state, cursor state, HMAC material, or workbook state changes.
7. Focused tests pass and the full-suite result introduces no regression from the isolated baseline.
8. Documentation names `creators.json` as the sole creator-registry source of truth.
