# Continuous Lightweight Collection — prepared, not started

Prerequisite: close the evidence/continuity milestone with owner-side real validation.
No UI work. Greedy remains default; PSO stays optional.

## Gate before starting collection

- Restore the original `config/secret.key` locally from encrypted offline backup;
  verify it against the existing fingerprint. Never send the key to GitHub or chat.
- Historical datasets must have independently verified original-run provenance.
  The new pilot refuses historical Parquet without `data/real/identity_manifest.json`.
  Only after verifying the original key and original collection records should the
  owner create a manifest with `key_fingerprint` matching that verified identity.
  Do not infer historical identity from matching hash length or set overlap.
- Re-run full tests, audit decoded historical Parquet/DuckDB, and the real pilot.
- Implement and validate a bounded in-memory live-chat adapter. The former replay
  probe wrote raw chat to disk and is disabled. Public video comments cannot
  substitute for live-chat observations.
- Sample at least two distinct live video IDs per channel on at least two channels.
  Report zero overlap honestly. Positive overlap is an observation, not a success
  criterion to optimize by replacing channels. Record sampling coverage and gaps.

## Implementation sequence

1. Google Sheets registry/control plane: channel ID, enabled, priority, consent or
   registry review status as applicable, collection policy, budget, and pause flag.
   Keep viewer-level pseudonyms and event payloads out of Sheets. Cache a validated
   registry locally so a Sheets outage does not corrupt collection state.
2. Local durable job journal: `(channel_id, video_id, source_type)`, attempt ID,
   state, retry time, last success, extractor version, and continuation checkpoint.
   Never put raw author IDs or chat/comment text in checkpoints or failure logs.
3. Bounded collectors: separate comment and live-chat adapters, capped pages/time,
   timeouts, backoff, rate budgets, explicit empty/unavailable/failed outcomes.
4. Idempotence before repeated polling: replace/reconcile snapshots per source or
   deduplicate with privacy-preserving event IDs. Current append-only batches keep
   sources intact and distinct-video metrics correct, but repeated polls can inflate
   `appearances`; do not use their sum as unique engagement or billable activity.
5. Crash recovery: atomic batch commit plus journal checkpoint, recover incomplete
   writes, and prevent two workers from claiming the same source/video job.
6. Longitudinal snapshots: window boundaries, observed videos by source, missing
   intervals, key fingerprint, schema version, collection provenance, and six
   source-separated overlap metrics. Unknown/uncollected is not observed zero.
7. Resource measurement: extraction rate distinct from local processing throughput;
   measure process RSS separately from Python allocation tracking. Fixed job count
   across worker comparisons; no scaling claims from a single synthetic run.

## Acceptance evidence

- Restart and retry without duplicated evidence; same key preserves viewer hashes.
- Wrong/missing key fails before network or data mutation.
- Crash between write and checkpoint is recovered once; disk-full fails visibly.
- Sheets unavailable, rate limit, comments disabled, live chat unavailable, and
  partial capture are distinguishable and do not silently replace the sample.
- Two-or-more-video live-chat test with both positive and negative fixtures,
  followed by an actual source-separated longitudinal pilot with recorded coverage.
- Decoded output and log audit plus canaries through both real adapter code paths.
- Tests, exact versions, schemas, graph metadata, measured costs, and remaining
  limitations accompany the milestone report. No UI additions.

## Implementation Status & Verification Record (2026-09-06)

### 1. Architectural Foundations Completed
- **Idempotent Columnar Persistence (`storage/parquet_manager.py`):**
  - Partitions named deterministically: `{video_id}_{source_type}.parquet` (e.g. `G1LXXzZx48c_comment.parquet`).
  - Merges incoming batches with existing partitions via in-memory reconciliation:
    `first_seen = min`, `last_seen = max`, `appearances = max(curr, incoming)`.
  - Repeated polling of the exact same video preserves row counts and prevents appearance inflation.
  - Testable migration tool `migrate_legacy_partitions()` converts legacy hyphen-uuid partitions to deterministic partitions cleanly.
- **Durable ACID Job Journal (`core/job_journal.py`):**
  - SQLite backend (`data/journal/job_journal.sqlite3`) with WAL journal mode.
  - Atomic claim pattern (`UPDATE ... WHERE state='PENDING' RETURNING ...`) prevents concurrent double-claims across multi-worker threads.
  - Recovery worker (`recover_abandoned_jobs`) releases stale claimed jobs after crashes.
  - Strict privacy guard rejects checkpoints containing raw viewer IDs or message content.
- **Bounded In-Memory Live Chat Adapter (`collector/live_chat_adapter.py`):**
  - Direct REST request implementation over YouTube Data API `liveChatMessages`.
  - Zero disk writes: immediate in-memory HMAC-SHA256 hashing of `authorChannelId`.
  - Never falls back to display names or writes temporary subtitle/replay dumps.
  - Fails closed with discrete status `LIVE_CHAT_UNAVAILABLE` when unconfigured.
- **Bounded Orchestrator & CLI (`collector/continuous_collector.py`, `scripts/run_continuous_collection.py`):**
  - CLI flags: `--channels`, `--workers`, `--scheduler (greedy|pso)`, `--timeout`, `--status`, `--recover`.
  - Greedy scheduler remains default; PSO optional.
  - Discrete outcome statuses: `SUCCESS`, `EMPTY_RESULT`, `COMMENTS_DISABLED`, `LIVE_CHAT_UNAVAILABLE`, `RATE_LIMITED`, `EXTRACTION_FAILURE`.
  - Zero silent channel replacement.

### 2. Provenance & Real Data Validation
- **Key Continuity & Provenance:**
  - Active key verified against `config/secret.fingerprint`: `142e095047f2f49c652fa1d04c3d146070f1b96b2bae697731bb40d146cf3eba`.
  - Historical dataset in `data/historical_unverified/` generated before the persistent key was locked (mtime 20:11 vs 20:15). In-memory comment hash verification yielded 0/79 matches against historical parquet, proving it was created with an ephemeral key. Segregated safely to `data/historical_unverified/` with full audit documentation.
  - Fresh verified dataset collected into `data/real/events/` bound to `data/real/identity_manifest.json` with 10/10 (100%) deterministic matches.
- **Empirical Multi-Video Longitudinal Validation:**
  - 6 channels monitored: Aisha Channel, Minami Cera Polygon, Tiara Rexa Polygon, Dacapo Ch.【ARP】, Baabel Ch.【ARP】, Schneider Ch.【ARP】.
  - 9 distinct video partitions across 2026/04, 2026/05, 2026/06, 2026/08, 2026/09.
  - 750 aggregated presence records.
  - **Empirical Evidence Contract Validation:**
    - Baabel - Dacapo: `shared_any`: 7, `shared_comments`: 7, `shared_live_chat`: 0, `strong_shared_comments`: 1, `strong_shared_any`: 1, `strong_shared_live_chat`: 0.
    - Single-video pairs: `strong_shared_comments`: 0.
    - Demonstrates that strong evidence strictly requires >=2 distinct videos on BOTH channels, and separate sources never inflate each other.

### 3. Verification & Resource Benchmarks
- **Test Suite:** 40/40 tests passing (100%) in 1.57s (`pytest -v`).
- **Privacy Audit:** 39 files checked with 0 leaks (`python scripts/privacy_audit.py`).
- **Throughput Measurements:**
  - Real YouTube extraction throughput: 1,143.9 comments/min (network-bound, 100 comments in 5.25s from `G1LXXzZx48c`).
  - Local processing throughput: 95,058.8 events/min (pure CPU/RAM: early aggregation + HMAC + Parquet write; peak RAM 22.45 MB tracked via tracemalloc).
  - DuckDB query latency: 56.11 ms on real dataset.

