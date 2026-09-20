# ThaiVtuberSNA Data Contract & Architecture

## Role & Mission
`ThaiVtuberSNA` is the backend data collection worker and pipeline engine powering [ThaiVtuberMaster](https://github.com/Icezaza2543/ThaiVtuberMaster).
It runs 24/7 with zero human intervention required for ongoing collection and SNA overlap recomputations.

```
ThaiVtuberSNA
      │
      ▼
[1] DISCOVER / COLLECT   (Twitch Helix API, vtuberthai.com, etc.)
      │
      ▼
[2] REVIEW EVIDENCE      (First-party proof, idempotent queue processing)
      │
      ▼
[3] CALCULATE SNA        (DuckDB overlap on interactions, Jaccard, Simpson)
      │
      ▼
[4] EXPORT TO MASTER     (5 clean CSV exports consumed by ThaiVtuberMaster)
      │
      ▼
ThaiVtuberMaster
```

## Storage & Database
- **Runtime Database**: `runtime/thaivtubersna.duckdb` (gitignored, working state).
- **Cold-Start Snapshot**: `data/bootstrap.json` (tracked in git). Fresh clones automatically initialize DuckDB from this snapshot on first run.
- **Tables**:
  - Original 13 registry tables: `evidence`, `personas`, `accounts`, `account_links`, `lifecycle_events`, `activity_observations`, `affiliations`, `continuity_links`, `discovery_runs`, `candidates`, `discovery_hits`, `legacy_claims`, `review_queue`.
  - `interactions`: Deduped audience presence (`creator_id`, `video_id`, `viewer_hash`, `source_type`, `observed_at`).
  - `network_edges`: Pairwise overlap metrics (`creator_a`, `creator_b`, `shared_any`, `strong_shared_any`, `jaccard`, `simpson`, `calculation_source`).
  - `worker_state`: Key-value checkpoints and schedules (`last_*_at`, `next_*_at`, `last_success`, `last_error`, `consecutive_failures`).

## Baseline Parity Guarantee
All migrations preserve exact baseline metrics:
- Personas: 895 (Verified personas: 873)
- Accounts: 4,721
- Candidates: 1,205
- Evidence: 9,411
- Account Links: 2,692
- Lifecycle Events: 34
- Affiliations: 14
- Discovery Runs: 2,035
- Discovery Hits: 6,362
- Review Queue: 1,402
- Legacy Claims: 1,370
- Network Edges: 913 (`calculation_source = 'legacy_seed'`)

## 24/7 Worker Operation
```bash
# Run one full cycle then exit
python -m thaivtubersna run

# Run 24/7 loop with interval scheduling and exponential backoff
python -m thaivtubersna worker

# Verify database health and parity
python -m thaivtubersna validate

# Export CSVs for ThaiVtuberMaster
python -m thaivtubersna export --output dist/export/
```

## Export Files for ThaiVtuberMaster
1. `VTUBERS.csv`: Verified YouTube accounts linked to verified personas.
2. `NETWORK_RESULT.csv`: Pairwise audience overlap network edges.
3. `TIKTOK_VERIFIED.csv`: Verified TikTok creators.
4. `TWITCH_VERIFIED.csv`: Verified Twitch creators.
5. `ANALYTICS_METRICS.csv`: Creator-level analytics metrics.


## Audience Interaction Contract
- YouTube audience collection requires `YOUTUBE_API_KEY`.
- The worker rotates through trusted YouTube channels and collects recent top-level comments plus active live-chat participants.
- Raw viewer account IDs are never persisted. They are HMAC-SHA256 hashed with `VIEWER_HMAC_KEY` or a generated local `runtime/viewer_hmac.key`.
- `interactions` is idempotent on `(creator_id, video_id, viewer_hash, source_type)`.
- `strong_shared_any`: same viewer appears in at least 2 distinct videos for both creators.
- `strong_shared_live_chat`: same viewer appears in live chat of at least 2 distinct videos for both creators.
- `strong_shared_comments`: same viewer comments on at least 2 distinct videos for both creators.
- Freshly recomputed edges use `calculation_source = live_interactions`; migrated 913 historical edges remain `legacy_seed` until superseded.

Optional worker tuning:
```text
YOUTUBE_CHANNELS_PER_CYCLE=25
YOUTUBE_RECENT_VIDEOS=5
VIEWER_HMAC_KEY=<persistent secret; optional if local runtime key is acceptable>
```
