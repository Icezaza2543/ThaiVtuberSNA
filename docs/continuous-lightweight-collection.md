# Continuous collection: correctness repair

The implementation at `a825cf0287741611090cd24c9731d9d56317abf8` was not ready
for continuous collection. Its reported 40/40 result is superseded: the original
suite reproduced **39 passed / 1 failed** in a checkout without a production key.
Historical real-pilot and throughput files are prior observations, not validation
of the repaired implementation.

The repair is validated offline with synthetic data. Production collection was
not started, historical data was not migrated, and production credentials were
not read or changed. No claim of exhaustive live coverage or production readiness
follows from these tests.

## What changed

- Canonical files are `events/canonical/{channel_id}/{video_id}_{source}.parquet`.
  Dates, batch order and polling month do not change the path. Mixed inputs split
  by channel/video/source; reconciliation includes viewer identity. Single-group
  writes return a Path; multi-group writes return a list of Paths.
- Raw observations aggregate within a batch. Between batches, presence is unioned,
  first/last timestamps widen, and appearances takes the maximum observed batch
  count. **Appearances is not a lifetime unique message count.** Different live
  pages can undercount total messages; event-level cumulative counting is not
  implemented. Distinct-video/source overlap remains the evidence contract.
- Existing unreadable Parquet fails closed. A cross-process dataset lock
  serializes read/merge/replace; temporary filenames are unique and files are
  flushed before atomic replacement. Multi-source batches are atomic per file,
  not an all-files transaction.
- The actual injected/default hasher binds to the dataset manifest before network
  or journal/storage initialization. Existing data without a valid matching
  manifest fails closed. The same validator is used by the pilot. Identity is
  checked again before publishing. A journal is bound to one dataset/fingerprint.
- Successful and successful-empty jobs get a durable next collection time.
  Re-registration preserves active claims and retry backoff. Due completed jobs
  begin a new poll generation and reset that poll's attempt budget. Retry delays
  double per attempt, capped at one hour; exhausted retries stop visibly.
- Both comment backends raise sanitized, explicit failures. API failure/empty
  responses no longer silently fall back to yt-dlp. Newest comments are requested.
  A detected cap/incomplete page reports PARTIAL_CAPTURE, preserves observed
  evidence and schedules another poll. It does not claim a complete archive.
- Each claim has a unique token and lease. Commit/fail/checkpoint require that
  token. Publication holds the journal write transaction so recovery cannot
  transfer ownership between validation and publication. Old/expired claims
  cannot publish. Recovery respects retry budgets.
- Extraction runs in spawn-based processes with no storage/journal references.
  The coordinator stops them on deadline; no extraction result publishes later.
  At most the worker limit is in flight. `process_single_job` is a synchronous
  test/helper API; use `run_bounded_cycle` for deadline enforcement.
- SQLite auditing decodes all user tables, structured JSON values and committed
  WAL-visible rows through a read-only snapshot. Corrupt DBs are errors.
  Sidecars are reported separately and orphan sidecars fail the full audit.
- Live-chat page tokens are decoded from checkpoint JSON. Entire API pages are
  consumed before advancing tokens, including empty pages. YouTube requires at
  least 200 messages per request, so a requested cap below 200 uses one bounded
  page of up to 200 messages. No replay download is used.

## Crash and deadline semantics

Parquet replacement and SQLite commit are not a distributed transaction. A crash
after a replacement but before journal commit can leave data ahead of the
checkpoint. Recovery replays the old checkpoint and idempotently reconciles the
same evidence. A failed journal update must never be represented as success.

The deadline bounds extraction and starts process termination. Small OS teardown
overhead is expected. Already-started synchronous local publication, fsync and
journal lock acquisition can add latency; this is not a hard real-time guarantee
under a stalled disk/OS. Tests cover a 0.01-second budget versus a 0.25-second
blocking extraction, and termination after a 10-second extractor actually starts.
No background extraction is allowed to write data.

Advisory locks coordinate this application's writers on a local filesystem;
external manual edits, network filesystem semantics and power-loss durability
of directory entries are outside the guarantee.

## Offline migration

Stop collection and analytical readers before migration. Verify the original
dataset/key provenance first. Do not create a manifest to re-label unverified
historical data.

```bash
python scripts/run_continuous_collection.py --dataset data/real/events --migrate
```

Migration reads and validates old files before publication, groups sources and
reconciles monthly duplicates. It removes legacy files only after canonical writes
succeed. If interrupted, rerun it before analytics: readers refuse mixed legacy
and canonical layouts so transient duplicate files do not inflate results.

Old journals under `data/journal/` are left intact. The default journal now lives
beside the dataset at `data/real/job_journal.sqlite3`; use `--journal` explicitly
for another journal. A new journal re-registers jobs and safely re-polls snapshots.
It does not claim to recover unavailable historical live-chat messages.

## Running

Restore the original production key and verify dataset identity first. Commands
below use the configured explicit video pool; automatic discovery of new videos,
Sheets-driven pause/budgets and channel replacement are not implemented here.

```bash
python scripts/run_continuous_collection.py --status
python scripts/run_continuous_collection.py --recover
python scripts/run_continuous_collection.py --channels 2 --workers 2 --timeout 60
python scripts/run_continuous_collection.py --continuous --poll-interval 300 --sources comment live_chat
```

The continuous loop repeatedly checks due work until Ctrl+C. Missing credentials,
disabled comments and unavailable live chat are reported explicitly; terminal
jobs require an explicit policy/operator decision rather than hidden retries or
substituted channels. Active live chat requires YouTube API credentials; replay
and exhaustive missed-interval backfill remain unsupported.

## Reproducible verification

Recorded on Windows 11 / Python 3.13.2: **79 passed in 7.66 seconds**.
All 14 selected behavioral regression cases fail on the original reviewed commit
and pass in the repaired suite. The synthetic two-poll run retains two distinct
presence rows after restart; a 0.01-second extraction budget returned TIMEOUT in
0.014673 seconds. The checkout audit checked seven available files with no
failures; the separate synthetic run explicitly audits Parquet, DuckDB and SQLite.
These counts and timings describe the saved run, not a performance guarantee.

```bash
python -m pytest -v
python scripts/verify_continuous_collection.py --output docs/evidence/continuous-correctness.json
python scripts/privacy_audit.py
```

The suite uses synthetic identities, temporary paths and mocked network boundaries.
No production key, .env or existing data is required. Evidence files:

- `docs/evidence/continuous-tests.txt`: complete repaired-suite output.
- `docs/evidence/continuous-baseline-regressions.txt`: selected unchanged public-API
  regressions run against the original reviewed commit.
- `docs/evidence/continuous-correctness.json`: two process-based polls across
  restart, deadline measurement, decoded synthetic audit and runtime versions.
- `docs/evidence/continuous-privacy-audit.json`: full audit of the isolated checkout.

Privacy auditing checks explicit schemas/fields and supplied canaries; it cannot
prove arbitrary unlabelled personal text is absent, inspect deleted SQLite pages,
uncommitted WAL frames, OS swap/backups, or authenticate historical hash origins.
Live-chat and comment canary regression tests cover persisted Parquet and journal
outputs, including extraction failures.

`strong_shared_comments = 1` remains a prior sample observation. It does not
validate recurrence, deadlines, recovery or live-chat coverage. A real longitudinal
pilot with documented coverage is still required before operational sign-off.
