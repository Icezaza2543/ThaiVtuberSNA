# Creator Registry Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace four overlapping creator registries with one evidence-backed persona/account catalog containing the trusted 1,370-channel baseline and the 392 accounts that remain accepted after evidence-backed eligibility correction. The review workflow initially accepted 393; one PLAVE group account was subsequently reclassified out of the individual-persona catalog.

**Architecture:** A deterministic builder produces `data/registry/creators.json` with normalized creator, account, and evidence tables. `CreatorCatalog` validates and indexes that file, all consumers use its API, and identity-resolution tooling combines trusted links, official public sources, and read-only YouTube Data API evidence before publication.

**Tech Stack:** Python 3.13, standard-library dataclasses/JSON/CSV/hashlib/urllib, google-api-python-client already used by the project, pytest, public web evidence, YouTube Data API v3.

**Spec:** `docs/superpowers/specs/2026-09-19-creator-registry-consolidation-design.md`

## Global Constraints

- Preserve all 1,370 baseline YouTube Channel IDs exactly once and do not re-review their VTuber eligibility.
- Include exactly 363 automated `VTUBER` accounts and 30 human `vtuber` accounts after identity resolution.
- Resolve one virtual persona or character form per creator; reincarnations and distinct character forms remain separate.
- Never merge identities from display-name similarity, avatar similarity, agency, or fuzzy score alone.
- Exclude the 102 final exclusions, 94 unavailable accounts, virtual groups, associated accounts, organizations, media, clip channels, and services from individual creators.
- Use YouTube Data API only for read-only identity evidence; never log or persist its key.
- Do not write Google Sheets or touch live-worker, workbook, quota-state, cursor-state, HMAC, checkpoint, frozen cohort, or frozen release files.
- `data/temporal/catalog/target_manifest.csv` remains byte-identical.
- Canonical writes are temporary-file, validate, then atomic replace.
- Work in an isolated worktree created at execution time with `superpowers:using-git-worktrees`.

## Review Focus

1. A Shorts or watch URL must resolve to its owning Channel ID through API evidence, and a conflicting owner must stop the build; covered in Task 4.
2. The same handle text on two platforms must not merge personas without an official cross-link; covered in Task 5.
3. An excluded or unavailable discovery must remain excluded even when legacy visual review says `new_persona`; covered in Task 2 and Task 8.
4. A duplicated account or one account linked to two personas must fail validation before replacing the canonical file; covered in Task 3 and Task 8.
5. Missing API key, exhausted quota, and cached evidence must produce explicit safe behavior without exposing credentials; covered in Task 4.

---

## File Structure

### New production modules

- `core/creator_registry_contract.py` — schema constants, normalization, stable IDs, and complete-payload validation.
- `core/creator_catalog.py` — read-only catalog interface and indexes used by every consumer.
- `collector/youtube_identity_client.py` — cached, read-only YouTube identity lookups.
- `scripts/package_creator_review_evidence.py` — converts the review outputs into a compact immutable evidence bundle.
- `scripts/resolve_creator_identities.py` — combines exact IDs, trusted links, official cross-links, API results, and reviewed research records.
- `scripts/build_creator_registry.py` — deterministic canonical builder and atomic writer.

### New versioned data and evidence

- `docs/evidence/creator-registry-review-2026-09-19/review_bundle.json` — compact final eligibility decisions and evidence URLs for all 884 candidates.
- `docs/evidence/creator-registry-review-2026-09-19/trusted_baseline_1370.json` — immutable byte-for-byte snapshot of the accepted 1,370-channel source data; provenance input only, never a runtime registry.
- `docs/evidence/creator-registry-review-2026-09-19/legacy_visual_identity_review.json` — immutable snapshot of the completed earlier identity decisions used only when consistent with final eligibility.
- `docs/evidence/creator-registry-review-2026-09-19/pre_refactor_baseline.json` — hashes, row counts, and protected-file fingerprints.
- `data/registry/identity_resolutions.json` — reviewed mapping for all 392 final accepted individual-persona accounts.
- `data/registry/creators.json` — sole creator-registry source of truth.

### New tests and fixtures

- `tests/fixtures/creator_registry/baseline.json`
- `tests/fixtures/creator_registry/review_bundle.json`
- `tests/fixtures/creator_registry/identity_resolutions.json`
- `tests/test_creator_review_evidence.py`
- `tests/test_creator_registry_contract.py`
- `tests/test_creator_catalog.py`
- `tests/test_youtube_identity_client.py`
- `tests/test_creator_identity_resolution.py`
- `tests/test_creator_registry_build.py`
- `tests/test_registry_consumer_migration.py`

### Existing consumers to modify

- `config/settings.py`
- `core/registry.py`
- `collector/thai_vtuber_registry_builder.py`
- `collector/balanced_video_collector.py`
- `collector/video_catalog_builder.py`
- `scripts/audit_creator_identity_mapping.py`
- `scripts/audit_research_v2_consistency.py`
- `scripts/audit_sheets_privacy.py`
- `scripts/build_collab_registries.py`
- `scripts/build_creator_ecosystem_data.py`
- `scripts/build_creator_lifecycle_evidence.py`
- `scripts/build_discovery_candidates_new.py`
- `scripts/build_discovery_universe.py`
- `scripts/build_historical_lifecycle.py`
- `scripts/build_research_v2_data.py`
- `scripts/build_web_data.py`
- `scripts/compact_campaign_review.py`
- `scripts/create_target_manifest.py`
- `scripts/run_batch_network_350.py`
- `scripts/run_hybrid_crawler_30.py`
- `scripts/update_web_with_real_data.py`
- `tests/test_frontend_public_boundary.py`

### Obsolete files to remove after migration

- `data/thai_vtuber_registry.json`
- `data/thai_vtuber_registry.csv`
- `data/registry_vtubers.csv`
- `data/master_creators.json`
- `scripts/reconstruct_master_creators.py`
- `scripts/update_master_with_review_and_dedup.py`
- `scripts/validate_master_creators.py`
- `data/entity_resolution/visual_identity_review.json`
- Root `index.html`
- `tools/visual_identity_review/index.html`
- `tools/visual_identity_review/server.py`
- `scripts/test_review_server.py`

---

### Task 1: Isolated Baseline and Protected-File Manifest

**Files:**
- Create: `docs/evidence/creator-registry-review-2026-09-19/pre_refactor_baseline.json`
- Create: `docs/evidence/creator-registry-review-2026-09-19/trusted_baseline_1370.json`
- Test: `tests/test_creator_registry_baseline.py`

**Interfaces:**
- Consumes: current tracked branch, `data/thai_vtuber_registry.json`, the four legacy registry files, frozen target manifest, frozen release directory.
- Produces: immutable SHA-256/count manifest and immutable baseline provenance snapshot consumed by Tasks 8–13.

- [ ] **Step 1: Create the isolated worktree**

Use `superpowers:using-git-worktrees`, starting from the approved-plan branch HEAD that contains this plan and spec commit `051c645`. Record the actual worktree base with `git rev-parse HEAD`. Copy only these untracked source inputs from the original checkout into the same relative paths in the worktree:

```text
outputs/new-account-review-2026-09-19/all_884_screening_results.json
outputs/new-account-review-2026-09-19/human_review_decisions.json
outputs/new-account-review-2026-09-19/non_vtuber_new_accounts_final.txt
```

Do not copy `.tmp`, credentials, cache, review-server state, or any saved API key.

- [ ] **Step 2: Write the failing baseline test**

```python
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def test_pre_refactor_baseline_records_real_registry_and_protected_files():
    baseline = json.loads((ROOT / 'docs/evidence/creator-registry-review-2026-09-19/pre_refactor_baseline.json').read_text())
    snapshot_path = ROOT / 'docs/evidence/creator-registry-review-2026-09-19/trusted_baseline_1370.json'
    registry = json.loads(snapshot_path.read_text(encoding='utf-8'))
    assert baseline['trusted_youtube_channels'] == 1370
    assert baseline['trusted_unique_channel_ids'] == 1370
    assert baseline['files']['data/temporal/catalog/target_manifest.csv'] == sha(ROOT / 'data/temporal/catalog/target_manifest.csv')
    assert baseline['files']['data/thai_vtuber_registry.json'] == sha(snapshot_path)
    assert len(registry) == 1370
```

- [ ] **Step 3: Run the test and record the expected failure**

Run: `python -m pytest tests/test_creator_registry_baseline.py -q --basetemp C:/Users/Icezaza/AppData/Local/Temp/thaivtubersna-registry-tests/baseline-red`

Expected: FAIL because `pre_refactor_baseline.json` does not exist.

- [ ] **Step 4: Generate the baseline manifest**

Copy `data/thai_vtuber_registry.json` byte-for-byte to `trusted_baseline_1370.json`, then generate the manifest with a short standard-library Python command. Assert the snapshot SHA-256 equals the source SHA-256 before proceeding. The manifest must contain the actual `git rev-parse HEAD`, SHA-256 for the four legacy registry files, `target_manifest.csv`, every file under `data/temporal/release/`, and counts for baseline rows and unique Channel IDs. Serialize with `sort_keys=True`, `ensure_ascii=False`, and a final newline.

Build the dynamic fields directly from the checkout and bytes:

```python
payload = {
    'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'trusted_youtube_channels': len(registry),
    'trusted_unique_channel_ids': len({row['channel_id'] for row in registry}),
    'files': {relative_path: sha(ROOT / relative_path) for relative_path in protected_paths},
}
```

- [ ] **Step 5: Establish the test baseline outside the repository**

Run focused current tests first, then the full suite with `--basetemp` in the OS temporary directory:

```powershell
python -m pytest tests/test_refactor_equivalence.py tests/test_frontend_public_boundary.py -q --basetemp C:/Users/Icezaza/AppData/Local/Temp/thaivtubersna-registry-tests/pre-refactor-focused
python -m pytest -q --basetemp C:/Users/Icezaza/AppData/Local/Temp/thaivtubersna-registry-tests/pre-refactor-full 2>&1 | Tee-Object docs/evidence/creator-registry-review-2026-09-19/pre_refactor_pytest.txt
```

Save the complete result summary beside the manifest. Do not change production code to hide unrelated failures.

- [ ] **Step 6: Verify and commit**

Run: `python -m pytest tests/test_creator_registry_baseline.py -q --basetemp C:/Users/Icezaza/AppData/Local/Temp/thaivtubersna-registry-tests/baseline-green`

Expected: PASS.

```bash
git add docs/evidence/creator-registry-review-2026-09-19/pre_refactor_baseline.json docs/evidence/creator-registry-review-2026-09-19/pre_refactor_pytest.txt docs/evidence/creator-registry-review-2026-09-19/trusted_baseline_1370.json tests/test_creator_registry_baseline.py
git commit -m "test(registry): freeze consolidation baseline"
```

### Task 2: Compact Review Evidence and Eligibility Precedence

**Files:**
- Create: `scripts/package_creator_review_evidence.py`
- Create: `tests/test_creator_review_evidence.py`
- Create: `docs/evidence/creator-registry-review-2026-09-19/review_bundle.json`
- Create: `docs/evidence/creator-registry-review-2026-09-19/legacy_visual_identity_review.json`

**Interfaces:**
- Consumes: `package_review_evidence(screening_path: Path, human_path: Path) -> dict`.
- Produces: `review_bundle.json` with exactly 884 unique rows and final `eligibility` values used by Tasks 5 and 8.

- [ ] **Step 1: Write failing precedence and sanitization tests**

```python
def test_final_human_decision_overrides_unresolved_and_paths_are_sanitized(tmp_path):
    bundle = package_review_evidence(SCREENING, HUMAN)
    rows = {row['discovery_id']: row for row in bundle['rows']}
    assert rows['human-vtuber']['eligibility'] == 'vtuber'
    assert rows['human-unrelated']['eligibility'] == 'exclude_unrelated'
    assert rows['human-unavailable']['eligibility'] == 'unavailable'
    assert 'raw_review_file' not in json.dumps(bundle)
    assert 'C:\\Users\\' not in json.dumps(bundle)

def test_excluded_legacy_new_persona_cannot_reenter_catalog():
    bundle = package_review_evidence(SCREENING_WITH_EXCLUDED_LEGACY_ID, HUMAN)
    row = next(r for r in bundle['rows'] if r['discovery_id'] == 'excluded')
    assert row['eligibility'].startswith('exclude_')
```

Fixture rows must include one automated VTuber, one human VTuber, one trusted-baseline duplicate, one excluded row whose old identity decision says `new_persona`, and one unavailable row.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_creator_review_evidence.py -q`

Expected: import failure for `scripts.package_creator_review_evidence`.

- [ ] **Step 3: Implement exact final-status mapping**

```python
AUTO_MAP = {
    'TRUSTED_BASELINE': 'trusted_baseline',
    'VTUBER': 'vtuber',
    'NON_VTUBER': 'exclude_non_vtuber',
    'NON_PERSONA_ACCOUNT': 'exclude_non_persona',
    'INVALID_ACCOUNT_URL': 'exclude_invalid_account',
    'VIRTUAL_GROUP': 'exclude_virtual_group',
    'VTUBER_ASSOCIATED_ACCOUNT': 'exclude_associated_account',
    'UNRESOLVED': 'unresolved',
}
HUMAN_MAP = {
    'vtuber': 'vtuber',
    'unrelated': 'exclude_unrelated',
    'non_persona': 'exclude_non_persona',
    'unavailable': 'unavailable',
    'unsure': 'unresolved',
}
```

Keep only stable source fields: discovery ID, platform, display/original names, URL, Channel ID, final eligibility, reason, evidence URLs, decision provenance, and reviewed timestamp. Reject duplicate IDs, unknown decisions, or a human decision for a non-`UNRESOLVED` row.

- [ ] **Step 4: Generate and validate the real review bundle**

Run:

```text
python scripts/package_creator_review_evidence.py --screening outputs/new-account-review-2026-09-19/all_884_screening_results.json --human outputs/new-account-review-2026-09-19/human_review_decisions.json --output docs/evidence/creator-registry-review-2026-09-19/review_bundle.json
```

Expected production counts after the reviewed eligibility correction: 884 total, 292 trusted baseline, 392 VTuber, 106 exclusions, and 94 unavailable. The exclusions include the evidence-backed reclassification of `candidate_e75fe4be2e942a6f1d0d` to `exclude_virtual_group`. The command must print its exact category table and fail if the total differs.

Copy `data/entity_resolution/visual_identity_review.json` byte-for-byte to `docs/evidence/creator-registry-review-2026-09-19/legacy_visual_identity_review.json`. Record both hashes in `pre_refactor_baseline.json` and assert equality. This preserves the accepted evidence while allowing Task 12 to remove the old runtime path.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_creator_review_evidence.py -q`

```bash
git add scripts/package_creator_review_evidence.py tests/test_creator_review_evidence.py docs/evidence/creator-registry-review-2026-09-19/review_bundle.json docs/evidence/creator-registry-review-2026-09-19/legacy_visual_identity_review.json docs/evidence/creator-registry-review-2026-09-19/pre_refactor_baseline.json
git commit -m "data(registry): package final creator review evidence"
```

### Task 3: Canonical Contract and Read-only Catalog

**Files:**
- Create: `core/creator_registry_contract.py`
- Create: `core/creator_catalog.py`
- Create: `tests/test_creator_registry_contract.py`
- Create: `tests/test_creator_catalog.py`
- Create: `tests/fixtures/creator_registry/baseline.json`

**Interfaces:**
- Produces: `validate_registry(payload: dict) -> None`, `stable_account_id(platform: str, platform_id: str | None, url: str) -> str`, `stable_persona_id(seed: str) -> str`.
- Produces: `CreatorCatalog.from_path(path: Path)`, `.source_fingerprint()`, `.creators()`, `.accounts()`, `.creator(persona_id)`, `.accounts_for(persona_id)`, `.account_by_platform_id(platform, platform_id)`, `.youtube_accounts()`, `.youtube_rows()`.

- [ ] **Step 1: Write failing validation tests**

```python
def test_valid_registry_indexes_personas_accounts_and_youtube():
    catalog = CreatorCatalog.from_path(FIXTURE)
    assert catalog.creator('vtuber_alpha')['canonical_name'] == 'Alpha'
    assert catalog.account_by_platform_id('youtube', 'UC' + 'A' * 22)['persona_id'] == 'vtuber_alpha'
    assert [row['channel_id'] for row in catalog.youtube_rows()] == ['UC' + 'A' * 22]

@pytest.mark.parametrize('mutation,message', [
    ('duplicate_account', 'duplicate account'),
    ('missing_persona', 'unknown persona'),
    ('two_personas', 'conflicting persona'),
    ('missing_evidence', 'evidence'),
    ('bad_youtube_id', 'Channel ID'),
])
def test_invalid_registry_fails_closed(mutation, message):
    payload = mutate_fixture(load_fixture(), mutation)
    with pytest.raises(ValueError, match=message):
        validate_registry(payload)
```

Add a mutation where identical handle text exists on Twitch and X under different personas; it must validate because handles are platform-scoped.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_creator_registry_contract.py tests/test_creator_catalog.py -q`

Expected: module import failures.

- [ ] **Step 3: Implement contract constants and normalization**

```python
SCHEMA_VERSION = 2
PLATFORMS = {'youtube', 'twitch', 'x', 'tiktok', 'instagram', 'facebook', 'bluesky', 'website', 'ganknow'}
PLATFORM_ALIASES = {'twitter': 'x', 'carrd': 'website', 'linktree': 'website'}
YOUTUBE_CHANNEL_ID = re.compile(r'^UC[A-Za-z0-9_-]{22}$')

def stable_account_id(platform, platform_id, url):
    key = f'{platform}:{platform_id or normalize_url(url)}'
    return 'account_' + hashlib.sha256(key.encode()).hexdigest()[:20]
```

Validation must enforce unique persona IDs, account IDs, `(platform, platform_id)`, and normalized URLs; one known persona per account; evidence references exist; each creator has an account and evidence; each account has evidence; eligibility equals `vtuber`; and the counted values equal actual array lengths.

- [ ] **Step 4: Implement immutable catalog indexes**

Load and validate once. Return tuples or defensive copies so callers cannot mutate the loaded payload. `source_fingerprint()` returns the lowercase SHA-256 of the exact canonical bytes. Sort exports by Channel ID for deterministic output. `youtube_rows()` must expose the legacy field names needed by existing consumers while sourcing values from creator/account records.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_creator_registry_contract.py tests/test_creator_catalog.py -q`

```bash
git add core/creator_registry_contract.py core/creator_catalog.py tests/test_creator_registry_contract.py tests/test_creator_catalog.py tests/fixtures/creator_registry/baseline.json
git commit -m "feat(registry): add canonical contract and catalog"
```

### Task 4: Cached Read-only YouTube Identity Client

**Files:**
- Create: `collector/youtube_identity_client.py`
- Create: `tests/test_youtube_identity_client.py`
- Modify: `config/settings.py`

**Interfaces:**
- Consumes: `YOUTUBE_API_KEY` and an injected YouTube API service in tests.
- Produces: `YouTubeIdentityClient.resolve(url: str) -> ChannelEvidence` where `ChannelEvidence` contains `channel_id`, `canonical_url`, `title`, `description`, `source_resource`, and `quota_units`.

- [ ] **Step 1: Write failing URL-owner, cache, and secret tests**

```python
def test_short_url_resolves_video_owner(fake_service, tmp_path):
    client = YouTubeIdentityClient('secret-test-key', cache_dir=tmp_path, service=fake_service)
    result = client.resolve('https://youtube.com/shorts/abcdefghijk')
    assert result.channel_id == 'UC' + 'A' * 22
    assert fake_service.calls == [('videos.list', 'abcdefghijk'), ('channels.list', 'UC' + 'A' * 22)]

def test_cache_avoids_second_api_call(fake_service, tmp_path):
    client = YouTubeIdentityClient('secret-test-key', cache_dir=tmp_path, service=fake_service)
    assert client.resolve(YOUTUBE_URL) == client.resolve(YOUTUBE_URL)
    assert fake_service.execute_count == 2

def test_missing_key_without_cache_fails_safely(tmp_path):
    with pytest.raises(RuntimeError, match='YOUTUBE_API_KEY'):
        YouTubeIdentityClient('', cache_dir=tmp_path).resolve(YOUTUBE_URL)

def test_error_never_contains_api_key(tmp_path):
    with pytest.raises(RuntimeError) as error:
        YouTubeIdentityClient('secret-test-key', cache_dir=tmp_path, service=FailingService()).resolve(YOUTUBE_URL)
    assert 'secret-test-key' not in str(error.value)
```

Add tests for `/channel/UC...`, `/@handle`, `/watch?v=...`, conflicting cached owner, invalid URL, and quota error. A cached successful record must remain usable when no key is configured.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_youtube_identity_client.py -q`

Expected: module import failure.

- [ ] **Step 3: Implement URL parsing and API calls**

Use `channels.list(part='snippet', id=...)`, `channels.list(part='snippet', forHandle=...)`, and `videos.list(part='snippet', id=...)`. Build the service with `cache_discovery=False`. Store sanitized responses under `.tmp/creator_identity/youtube/` using the resource ID hash; never store request headers or the key.

```python
@dataclass(frozen=True)
class ChannelEvidence:
    channel_id: str
    canonical_url: str
    title: str
    description: str
    source_resource: str
    quota_units: int
```

- [ ] **Step 4: Add configuration without changing quota state**

Add `CREATOR_REGISTRY_PATH = DATA_DIR / 'registry' / 'creators.json'` and `CREATOR_IDENTITY_CACHE_DIR = BASE_DIR / '.tmp' / 'creator_identity'` to `config/settings.py`. Reuse `YOUTUBE_API_KEY`; do not add another credential loader.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_youtube_identity_client.py -q`

```bash
git add collector/youtube_identity_client.py config/settings.py tests/test_youtube_identity_client.py
git commit -m "feat(registry): add cached YouTube identity lookup"
```

### Task 5: Evidence-backed Identity Resolver

**Files:**
- Create: `scripts/resolve_creator_identities.py`
- Create: `tests/test_creator_identity_resolution.py`
- Create: `tests/fixtures/creator_registry/review_bundle.json`
- Create: `tests/fixtures/creator_registry/identity_resolutions.json`

**Interfaces:**
- Consumes: `resolve_accounts(baseline: list[dict], review_bundle: dict, trusted_registry: dict, legacy_decisions: dict, researched: dict, youtube_client=None) -> dict`.
- Produces: resolution ledger schema version 1 with one row for every accepted discovery ID.

- [ ] **Step 1: Write failing identity-rule tests**

```python
def test_verified_official_crosslink_attaches_existing_persona():
    ledger = resolve_accounts(BASELINE, REVIEW, TRUSTED, LEGACY, RESEARCHED_CROSSLINK)
    assert ledger['resolutions'][0]['outcome'] == 'existing_persona'
    assert ledger['resolutions'][0]['persona_id'] == 'vtuber_alpha'
    assert ledger['resolutions'][0]['method'] == 'official_crosslink'

def test_same_handle_on_two_platforms_does_not_merge_without_crosslink():
    ledger = resolve_accounts(BASELINE, TWO_PLATFORM_SAME_HANDLE, TRUSTED, {}, RESEARCHED_SEPARATE)
    assert len({row['persona_id'] for row in ledger['resolutions']}) == 2

def test_conflicting_official_links_fail_closed():
    with pytest.raises(ValueError, match='conflicting persona'):
        resolve_accounts(BASELINE, REVIEW, TRUSTED, {}, RESEARCHED_CONFLICT)

def test_every_accepted_account_requires_positive_evidence():
    with pytest.raises(ValueError, match='missing identity evidence'):
        resolve_accounts(BASELINE, REVIEW, TRUSTED, {}, {})
```

Also test exact Channel ID, trusted verified link, a legacy decision contradicted by final exclusion, deterministic new-persona ID, and evidence URL deduplication.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_creator_identity_resolution.py -q`

Expected: import failure.

- [ ] **Step 3: Implement resolution precedence**

```python
METHOD_PRIORITY = (
    'exact_platform_id',
    'verified_registry_link',
    'official_crosslink',
    'explicit_official_identity',
)

def new_persona_id(discovery_id, canonical_name):
    seed = f'{discovery_id}:{normalize_name(canonical_name)}'
    return 'persona_' + hashlib.sha256(seed.encode()).hexdigest()[:20]
```

Only rows with `eligibility == 'vtuber'` enter resolution. `trusted_baseline` rows verify deduplication but do not add a resolution row. Record `checked_urls`, `evidence_urls`, `method`, `outcome`, `persona_id`, canonical name, and the official account URLs found.

- [ ] **Step 4: Implement command-line validation**

Support:

```text
python scripts/resolve_creator_identities.py --review-bundle docs/evidence/creator-registry-review-2026-09-19/review_bundle.json --baseline docs/evidence/creator-registry-review-2026-09-19/trusted_baseline_1370.json --trusted-registry C:/Users/Icezaza/Documents/GitHub/ThaiVirtualCreatorRegistry/data/registry.json --legacy-decisions docs/evidence/creator-registry-review-2026-09-19/legacy_visual_identity_review.json --researched docs/evidence/creator-registry-review-2026-09-19/identity_research_linked.json --researched docs/evidence/creator-registry-review-2026-09-19/identity_research_x.json --researched docs/evidence/creator-registry-review-2026-09-19/identity_research_twitch.json --output data/registry/identity_resolutions.json --validate-only
```

`--validate-only` must print totals by platform, existing/new outcomes, evidence method, unresolved count, and conflict count; for the production review bundle it exits nonzero unless accepted=392, unresolved=0, conflicts=0.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_creator_identity_resolution.py -q`

```bash
git add scripts/resolve_creator_identities.py tests/test_creator_identity_resolution.py tests/fixtures/creator_registry/review_bundle.json tests/fixtures/creator_registry/identity_resolutions.json
git commit -m "feat(registry): enforce evidence-backed identity resolution"
```

### Task 6: Resolve YouTube and Linked-platform Accounts

**Files:**
- Create: `docs/evidence/creator-registry-review-2026-09-19/identity_research_linked.json`
- Modify: `data/registry/identity_resolutions.json`
- Test: `tests/test_creator_identity_resolution.py`

**Interfaces:**
- Consumes: the 26 YouTube, 58 TikTok, 17 website, 7 Instagram, 6 Facebook, and 3 Ganknow accepted accounts from `review_bundle.json`.
- Produces: 117 evidence-backed resolution rows merged by discovery ID.

- [ ] **Step 1: Generate the exact platform queue**

Run the resolver in queue mode for `youtube,tiktok,website,instagram,facebook,ganknow`. Assert the queue contains exactly 117 unique accepted IDs. Resolve all YouTube watch and Shorts URLs to owning Channel IDs through `YouTubeIdentityClient`.

- [ ] **Step 2: Resolve trusted and official cross-links**

Use exact IDs, the trusted account-link database, and official links already captured in `evidence_urls` and profile excerpts. For each existing-persona resolution, store the URL that joins the candidate account to a known account. For each new persona, store an official profile that explicitly identifies the persona and the official account being added.

- [ ] **Step 3: Search remaining official sources**

For any row still lacking identity, search the supplied handle/name plus platform, open the strongest official profile, and record only official or owner-controlled sources. Do not use fan pages, scraper profiles, or name similarity as identity proof.

- [ ] **Step 4: Validate the platform batch**

Run:

```text
python scripts/resolve_creator_identities.py --review-bundle docs/evidence/creator-registry-review-2026-09-19/review_bundle.json --baseline docs/evidence/creator-registry-review-2026-09-19/trusted_baseline_1370.json --trusted-registry C:/Users/Icezaza/Documents/GitHub/ThaiVirtualCreatorRegistry/data/registry.json --legacy-decisions docs/evidence/creator-registry-review-2026-09-19/legacy_visual_identity_review.json --researched docs/evidence/creator-registry-review-2026-09-19/identity_research_linked.json --output data/registry/identity_resolutions.json --platform youtube --platform tiktok --platform website --platform instagram --platform facebook --platform ganknow --validate-only
```

Expected: 117 accepted, 117 resolved, 0 conflicts, 0 missing evidence. Add a test that every YouTube account has a valid Channel ID and its evidence owner agrees with the resolution.

- [ ] **Step 5: Commit the reviewed batch**

```bash
git add docs/evidence/creator-registry-review-2026-09-19/identity_research_linked.json data/registry/identity_resolutions.json tests/test_creator_identity_resolution.py
git commit -m "data(registry): resolve linked-platform creator identities"
```

### Task 7: Resolve X Accounts

**Files:**
- Create: `docs/evidence/creator-registry-review-2026-09-19/identity_research_x.json`
- Modify: `data/registry/identity_resolutions.json`
- Test: `tests/test_creator_identity_resolution.py`

**Interfaces:**
- Consumes: exactly 126 accepted X accounts and cached public X/profile evidence.
- Produces: 126 evidence-backed resolution rows merged by discovery ID.

- [ ] **Step 1: Generate and validate the X queue**

Assert exactly 126 unique accepted X discovery IDs. Pre-resolve exact verified account URLs from the trusted registry and official cross-links captured in profile website fields.

- [ ] **Step 2: Inspect official identity paths**

For unresolved rows, follow the profile website, Carrd, Linktree, YouTube, Twitch, or agency-member page controlled by the persona. Record `existing_persona` only when a source connects both accounts. Otherwise record `new_persona` with explicit self-identification evidence.

- [ ] **Step 3: Reject unsafe joins**

Add regression fixtures for two accounts with the same display name and two accounts in the same agency. Confirm neither merges without an official cross-link.

- [ ] **Step 4: Validate and commit**

Run the resolver with `--platform x --validate-only`.

Expected: 126 accepted, 126 resolved, 0 conflicts, 0 missing evidence.

```bash
git add docs/evidence/creator-registry-review-2026-09-19/identity_research_x.json data/registry/identity_resolutions.json tests/test_creator_identity_resolution.py
git commit -m "data(registry): resolve X creator identities"
```

### Task 8: Resolve Twitch Accounts and Seal the Ledger

**Files:**
- Create: `docs/evidence/creator-registry-review-2026-09-19/identity_research_twitch.json`
- Modify: `data/registry/identity_resolutions.json`
- Test: `tests/test_creator_identity_resolution.py`

**Interfaces:**
- Consumes: exactly 150 accepted Twitch accounts, captured About panels/video evidence, official social links, and trusted links.
- Produces: final 392-row `identity_resolutions.json`.

- [ ] **Step 1: Generate and validate the Twitch queue**

Assert exactly 150 unique accepted Twitch discovery IDs. Load official social links from the saved public Twitch snapshots before performing new searches.

- [ ] **Step 2: Resolve all Twitch identities**

Use About-panel links, official creator sites, YouTube channels, X accounts, and agency roster pages. The video thumbnail establishes VTuber eligibility but does not by itself establish a cross-platform identity merge.

- [ ] **Step 3: Seal the complete ledger**

Run the full resolver validation. It must assert:

```text
accepted=392
unique_discovery_ids=392
resolved=392
missing_evidence=0
conflicts=0
```

Also assert platform totals: Twitch 150, X 126, TikTok 58, YouTube 26, website 17, Instagram 7, Facebook 6, Ganknow 3.

- [ ] **Step 4: Run the full identity test file and commit**

Run: `python -m pytest tests/test_creator_identity_resolution.py tests/test_youtube_identity_client.py -q`

```bash
git add docs/evidence/creator-registry-review-2026-09-19/identity_research_twitch.json data/registry/identity_resolutions.json tests/test_creator_identity_resolution.py
git commit -m "data(registry): complete accepted-account identity ledger"
```

### Task 9: Deterministic Canonical Registry Builder

**Files:**
- Create: `scripts/build_creator_registry.py`
- Create: `tests/test_creator_registry_build.py`
- Create: `data/registry/creators.json`

**Interfaces:**
- Consumes: `build_registry(baseline: list[dict], review_bundle: dict, resolutions: dict) -> dict`.
- Produces: schema-v2 canonical payload validated by `validate_registry` and written by `write_registry_atomic(payload, path)`.

- [ ] **Step 1: Write failing build invariants**

```python
def test_build_preserves_baseline_and_accepted_accounts():
    payload = build_registry(BASELINE, REVIEW_BUNDLE, RESOLUTIONS)
    youtube_ids = {a['platform_id'] for a in payload['accounts'] if a['platform'] == 'youtube'}
    discovery_ids = {a.get('discovery_id') for a in payload['accounts']}
    assert BASELINE_CHANNEL_IDS <= youtube_ids
    assert ACCEPTED_DISCOVERY_IDS <= discovery_ids
    assert not EXCLUDED_DISCOVERY_IDS & discovery_ids
    assert not UNAVAILABLE_DISCOVERY_IDS & discovery_ids

def test_build_is_byte_deterministic(tmp_path):
    first = write_registry_atomic(build_registry(BASELINE, REVIEW_BUNDLE, RESOLUTIONS), tmp_path / 'one.json')
    second = write_registry_atomic(build_registry(BASELINE, REVIEW_BUNDLE, RESOLUTIONS), tmp_path / 'two.json')
    assert first.read_bytes() == second.read_bytes()

def test_baseline_rows_with_same_person_id_share_one_creator():
    payload = build_registry(BASELINE_WITH_TWO_CHANNELS_FOR_ONE_PERSON, REVIEW_BUNDLE, RESOLUTIONS)
    assert sum(row['persona_id'] == 'vtuber_alpha' for row in payload['creators']) == 1
    assert sum(row['persona_id'] == 'vtuber_alpha' for row in payload['accounts']) == 2
```

Add tests for 292 trusted-baseline duplicates adding zero accounts, old excluded `new_persona` decisions not re-entering, null metrics remaining null, and a simulated write failure preserving the original target.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_creator_registry_build.py -q`

Expected: import failure.

- [ ] **Step 3: Implement baseline conversion and resolution application**

Retain each valid baseline `person_id` as `persona_id`; when multiple baseline channels share one `person_id`, emit one creator with multiple YouTube accounts. Convert each baseline row to one YouTube account and one evidence record. Apply the 392 final resolution rows, deduplicating accounts by platform ID or normalized URL. When an accepted account resolves to an existing persona, append only the missing account; when it resolves to a new persona, create exactly one creator for that `persona_id`. Never merge two distinct baseline `person_id` values from name similarity; a later merge requires the same qualifying identity evidence as every other account merge.

Stable order:

```python
payload['creators'].sort(key=lambda row: row['persona_id'])
payload['accounts'].sort(key=lambda row: row['account_id'])
payload['evidence'].sort(key=lambda row: row['evidence_id'])
```

Operational timestamps are excluded from the canonical bytes; observed evidence timestamps remain source values.

- [ ] **Step 4: Build the real canonical file**

Run:

```text
python scripts/build_creator_registry.py --baseline docs/evidence/creator-registry-review-2026-09-19/trusted_baseline_1370.json --review-bundle docs/evidence/creator-registry-review-2026-09-19/review_bundle.json --resolutions data/registry/identity_resolutions.json --output data/registry/creators.json
```

The command must print actual creator/account/evidence totals and the required inclusion/exclusion assertions. Do not hardcode the final persona count.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_creator_registry_contract.py tests/test_creator_catalog.py tests/test_creator_registry_build.py -q`

```bash
git add scripts/build_creator_registry.py tests/test_creator_registry_build.py data/registry/creators.json
git commit -m "feat(registry): build canonical creator catalog"
```

### Task 10: Migrate Collection and Control-plane Readers

**Files:**
- Modify: `core/registry.py`
- Modify: `collector/thai_vtuber_registry_builder.py`
- Modify: `collector/balanced_video_collector.py`
- Modify: `collector/video_catalog_builder.py`
- Modify: `scripts/run_batch_network_350.py`
- Modify: `scripts/run_hybrid_crawler_30.py`
- Create: `tests/test_registry_consumer_migration.py`

**Interfaces:**
- Consumes: `CreatorCatalog.youtube_rows()` and `CreatorCatalog.youtube_accounts()`.
- Produces: the same legacy-shaped dictionaries expected by collection code without reading legacy CSV/JSON files.

- [ ] **Step 1: Write failing no-direct-read and equivalence tests**

```python
LEGACY_NAMES = {
    'thai_vtuber_registry.json', 'thai_vtuber_registry.csv',
    'registry_vtubers.csv', 'master_creators.json'
}

def test_collection_modules_do_not_reference_legacy_registry_names():
    for path in COLLECTION_MODULES:
        source = path.read_text(encoding='utf-8')
        assert not any(name in source for name in LEGACY_NAMES), path

def test_catalog_legacy_rows_preserve_baseline_shape():
    rows = CreatorCatalog.from_path(CANONICAL).youtube_rows()
    original = json.loads(BASELINE.read_text(encoding='utf-8'))
    assert {r['channel_id'] for r in original} <= {r['channel_id'] for r in rows}
    for field in ('channel_id', 'name', 'handle', 'agency', 'activity_status', 'vtuber_status', 'enabled'):
        assert field in rows[0]
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_registry_consumer_migration.py -q`

Expected: direct-read assertion failures.

- [ ] **Step 3: Replace local registry loading**

Instantiate the catalog with `CreatorCatalog.from_path(CREATOR_REGISTRY_PATH)` and replace CSV/JSON reads with `youtube_rows()`. Preserve active/hiatus filtering at the caller. `RegistryManager.load_vtubers()` uses catalog rows when no sheet is configured. `save_vtubers()` must not rewrite `creators.json`; keep external-sheet behavior isolated and make local-only mutation raise a clear error.

Change `ThaiVTuberRegistryBuilder` to emit discovery/intake evidence rather than overwrite the canonical registry. Its output cannot enter `creators.json` without eligibility and identity resolution.

- [ ] **Step 4: Run collection-focused tests**

Run:

```text
python -m pytest tests/test_registry_consumer_migration.py tests/test_offline_entrypoints.py tests/test_continuous_collection.py tests/test_real_adapters.py -q
```

- [ ] **Step 5: Commit**

```bash
git add core/registry.py collector/thai_vtuber_registry_builder.py collector/balanced_video_collector.py collector/video_catalog_builder.py scripts/run_batch_network_350.py scripts/run_hybrid_crawler_30.py tests/test_registry_consumer_migration.py
git commit -m "refactor(registry): migrate collection consumers"
```

### Task 11: Migrate Analysis, Research, and Web Builders

**Files:**
- Modify: `scripts/audit_creator_identity_mapping.py`
- Modify: `scripts/audit_research_v2_consistency.py`
- Modify: `scripts/audit_sheets_privacy.py`
- Modify: `scripts/build_collab_registries.py`
- Modify: `scripts/build_creator_ecosystem_data.py`
- Modify: `scripts/build_creator_lifecycle_evidence.py`
- Modify: `scripts/build_discovery_candidates_new.py`
- Modify: `scripts/build_discovery_universe.py`
- Modify: `scripts/build_historical_lifecycle.py`
- Modify: `scripts/build_research_v2_data.py`
- Modify: `scripts/build_web_data.py`
- Modify: `scripts/compact_campaign_review.py`
- Modify: `scripts/create_target_manifest.py`
- Modify: `scripts/update_web_with_real_data.py`
- Modify: `tests/test_frontend_public_boundary.py`
- Modify: `tests/test_refactor_equivalence.py`
- Create: `tests/test_sheets_privacy_audit.py`

**Interfaces:**
- Consumes: `CreatorCatalog` lookup and export methods.
- Produces: unchanged frozen-cohort membership and equivalent baseline metadata while allowing new canonical creators in non-frozen ecosystem outputs.

- [ ] **Step 1: Extend the direct-read test to all consumers**

Add every listed script to `CONSUMER_MODULES` and assert none contains a legacy registry filename. Update the public-web boundary test to derive allowed Channel IDs from `CreatorCatalog.youtube_accounts()`.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_registry_consumer_migration.py tests/test_frontend_public_boundary.py tests/test_refactor_equivalence.py -q`

Expected: direct-read failures before migration.

- [ ] **Step 3: Replace JSON and CSV parsing with catalog calls**

Use `youtube_rows()` where callers need legacy metadata dictionaries, `youtube_accounts()` where they need normalized records, and `account_by_platform_id('youtube', channel_id)` for point lookups. Preserve joins against `target_manifest.csv`; do not add new channels to that file. `audit_sheets_privacy.py` compares the sheet export to `CreatorCatalog.youtube_rows()` and never restores the retired CSV.

For web builders, public nodes may use every available YouTube Channel ID in the canonical catalog, but any existing frozen or sampled view keeps its documented selection rule. Every newly generated registry-derived public JSON writes `metadata.creator_registry_sha256` from `CreatorCatalog.source_fingerprint()`, and its contract test rejects a stale or missing fingerprint. Do not regenerate protected releases in this task.

- [ ] **Step 4: Run directly affected suites**

Run:

```text
python -m pytest tests/test_registry_consumer_migration.py tests/test_frontend_public_boundary.py tests/test_refactor_equivalence.py tests/test_research_v2_data_contract.py tests/test_research_source_integrity.py tests/test_historical_catalog.py tests/test_lifecycle_timeline.py tests/test_sheets_privacy_audit.py -q
```

- [ ] **Step 5: Commit**

```bash
git add scripts/audit_creator_identity_mapping.py scripts/audit_research_v2_consistency.py scripts/audit_sheets_privacy.py scripts/build_collab_registries.py scripts/build_creator_ecosystem_data.py scripts/build_creator_lifecycle_evidence.py scripts/build_discovery_candidates_new.py scripts/build_discovery_universe.py scripts/build_historical_lifecycle.py scripts/build_research_v2_data.py scripts/build_web_data.py scripts/compact_campaign_review.py scripts/create_target_manifest.py scripts/update_web_with_real_data.py tests/test_frontend_public_boundary.py tests/test_refactor_equivalence.py tests/test_registry_consumer_migration.py tests/test_sheets_privacy_audit.py
git commit -m "refactor(registry): migrate analysis and web consumers"
```

### Task 12: Remove Legacy Registries and Update Documentation

**Files:**
- Delete: `data/thai_vtuber_registry.json`
- Delete: `data/thai_vtuber_registry.csv`
- Delete: `data/registry_vtubers.csv`
- Delete: `data/master_creators.json`
- Delete: `scripts/reconstruct_master_creators.py`
- Delete: `scripts/update_master_with_review_and_dedup.py`
- Delete: `scripts/validate_master_creators.py`
- Delete: `data/entity_resolution/visual_identity_review.json`
- Delete: root `index.html`
- Delete: `tools/visual_identity_review/index.html`
- Delete: `tools/visual_identity_review/server.py`
- Delete: `scripts/test_review_server.py`
- Modify: `README.md`
- Modify: `docs/PROJECT.md`
- Modify: `data/phase1_registry_report.md`
- Modify: `docs/research_v2/CURRENT_DATA_CAPABILITIES.md`
- Modify: `docs/research_v2/LONG_RUNNING_RESEARCH_REPORT.md`
- Modify: `docs/research_v2/OVERNIGHT_REPORT.md`
- Preserve unchanged as historical audit evidence: `docs/refactor/REFACTOR_AUDIT.md`, `docs/refactor/REFACTOR_PLAN.md`, `docs/refactor_protected_hashes.json`, and existing files under `docs/evidence/`.

**Interfaces:**
- Consumes: completed consumer migration and canonical catalog.
- Produces: repository with no runtime dependency on obsolete registries and one documented source of truth.

- [ ] **Step 1: Write the deletion gate**

```python
def test_legacy_registry_files_and_runtime_references_are_gone():
    for path in LEGACY_PATHS:
        assert not path.exists(), path
    matches = legacy_runtime_references(ROOT)
    assert matches == []
```

Allow historical references only inside sealed design/audit documents that explicitly label the path as legacy. Runtime code, active README instructions, and tests may not reference old paths.

- [ ] **Step 2: Verify the gate fails before deletion**

Run: `python -m pytest tests/test_registry_consumer_migration.py::test_legacy_registry_files_and_runtime_references_are_gone -q`

Expected: FAIL because legacy files still exist.

- [ ] **Step 3: Re-scan and remove only validated obsolete files**

Run `rg -n 'thai_vtuber_registry|registry_vtubers|master_creators|visual_identity_review'` and classify every remaining match. Remove every file listed in this task only after runtime matches equal zero. The earlier review UI, its server, and its executable test are obsolete because the final decisions are sealed in `legacy_visual_identity_review.json` and the 392-row ledger. Do not delete target manifests, checkpoints, system metadata, discovery seeds, evidence, or frozen releases. The untracked `tools/eligibility_review/` working-copy artifact is not copied into the isolated worktree and is outside this branch.

- [ ] **Step 4: Update active documentation**

Document `data/registry/creators.json`, `CreatorCatalog`, identity policy, derived views, rebuild command, and the distinction between the canonical registry and frozen 193-channel cohort.

- [ ] **Step 5: Verify and commit**

Run: `python -m pytest tests/test_registry_consumer_migration.py tests/test_creator_registry_contract.py tests/test_creator_catalog.py -q`

```bash
git add -A data core scripts collector tests README.md docs web tools
git commit -m "refactor(registry): retire duplicate creator registries"
```

### Task 13: End-to-end Rebuild, Privacy Check, and Regression Audit

**Files:**
- Create: `docs/evidence/creator-registry-review-2026-09-19/post_refactor_validation.json`
- No production modification is planned; when validation exposes a defect, return to its owning task, fix it there, rerun that task's focused tests, then restart Task 13.

**Interfaces:**
- Consumes: the complete refactor branch.
- Produces: fresh evidence that the canonical registry rebuilds deterministically and protected files did not change.

- [ ] **Step 1: Rebuild into two independent temporary paths**

Run the canonical builder twice with identical inputs:

```powershell
python scripts/build_creator_registry.py --baseline docs/evidence/creator-registry-review-2026-09-19/trusted_baseline_1370.json --review-bundle docs/evidence/creator-registry-review-2026-09-19/review_bundle.json --resolutions data/registry/identity_resolutions.json --output C:/Users/Icezaza/AppData/Local/Temp/thaivtubersna-registry-tests/rebuild-one.json
python scripts/build_creator_registry.py --baseline docs/evidence/creator-registry-review-2026-09-19/trusted_baseline_1370.json --review-bundle docs/evidence/creator-registry-review-2026-09-19/review_bundle.json --resolutions data/registry/identity_resolutions.json --output C:/Users/Icezaza/AppData/Local/Temp/thaivtubersna-registry-tests/rebuild-two.json
python -c "from pathlib import Path; from core.creator_catalog import CreatorCatalog; a=Path(r'C:/Users/Icezaza/AppData/Local/Temp/thaivtubersna-registry-tests/rebuild-one.json'); b=Path(r'C:/Users/Icezaza/AppData/Local/Temp/thaivtubersna-registry-tests/rebuild-two.json'); assert a.read_bytes()==b.read_bytes(); CreatorCatalog.from_path(a); CreatorCatalog.from_path(b)"
```

- [ ] **Step 2: Verify exact inclusion and exclusion contracts**

Produce machine-checked counts for baseline Channel IDs, accepted discovery IDs, trusted-baseline duplicates, excluded IDs, unavailable IDs, creators, accounts, evidence, and YouTube accounts. Required fixed values are 1,370 baseline Channel IDs, 392 accepted discovery IDs, 292 trusted-baseline duplicates, 106 excluded IDs, and 94 unavailable IDs; creator and total-account counts are observed outputs.

- [ ] **Step 3: Verify protected hashes and privacy**

Compare every protected-file hash to `pre_refactor_baseline.json`. Run `python scripts/privacy_audit.py`, `python scripts/audit_data_security.py --git-only --output C:/Users/Icezaza/AppData/Local/Temp/thaivtubersna-registry-tests/data-security.json`, and the frontend public-boundary tests. Confirm no API key or raw credential appears in committed files.

- [ ] **Step 4: Run focused and full test suites**

Run the focused registry/consumer suite first:

```text
python -m pytest tests/test_creator_registry_baseline.py tests/test_creator_review_evidence.py tests/test_creator_registry_contract.py tests/test_creator_catalog.py tests/test_youtube_identity_client.py tests/test_creator_identity_resolution.py tests/test_creator_registry_build.py tests/test_registry_consumer_migration.py tests/test_frontend_public_boundary.py tests/test_refactor_equivalence.py -q --basetemp C:/Users/Icezaza/AppData/Local/Temp/thaivtubersna-registry-tests/final-focused
```

Then run the full suite:

```text
python -m pytest -q --basetemp C:/Users/Icezaza/AppData/Local/Temp/thaivtubersna-registry-tests/final-full
```

All focused tests must pass. Compare any full-suite failures against Task 1's saved baseline and report every difference by test name.

- [ ] **Step 5: Write validation evidence**

`post_refactor_validation.json` must include the canonical SHA-256, rebuild equality, actual counts, protected hash comparison, focused/full test summaries, privacy audit result, and commit SHA. Do not include credentials, raw API payloads, or private viewer data.

- [ ] **Step 6: Final commit and branch review**

```bash
git add docs/evidence/creator-registry-review-2026-09-19/post_refactor_validation.json
git commit -m "test(registry): verify canonical consolidation"
```

Set `$registryBase = git merge-base HEAD origin/main`, run `git diff "$registryBase...HEAD" --check`, inspect the entire branch diff, and confirm no unrelated files changed before requesting final review.
