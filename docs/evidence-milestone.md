# Evidence Separation, Persistent Keys, Longitudinal Strength

Status: **implementation validated with fixtures; real longitudinal gate BLOCKED**.
Baseline: `699313850423f3ec2266f18b0e35f1550bdfb69e`. Reviewed 2026-09-06.
No UI changes. No real secret created, uploaded, replaced, or reconstructed.

## Findings corrected

- Removed misleading `streams_seen` output alias; comments only contribute to
  `videos_seen` and `comment_videos_seen`.
- Existing six overlap metrics were present. Preserved them and fixed aggregation
  to key by viewer, channel, video, **and source**. Export includes source Jaccards.
- Strong metrics always use at least two distinct videos on **both** channels.
  Reject threshold overrides that would silently change the named metric.
- Raw, aggregated, mixed, and empty Parquet datasets have a consistent DuckDB view.
  Invalid source/video fields and unreadable Parquet fail instead of leaving a
  stale view behind. Storage requires explicit source and writes atomic batches
  instead of overwriting another source's evidence for the same video.
- Removed environment key bypass. Missing key/fingerprint and changed fingerprint
  fail before collector network work. Explicit initialization cannot replace an
  existing key or fingerprint. New key files use owner-only creation permissions
  on POSIX; operators must set equivalent ACLs on Windows.
- Pilot now checks a dataset identity manifest, unions cached per-channel viewers,
  deduplicates channel metadata and refuses success with insufficient channels.
- Disabled the legacy replay probe: it wrote raw chat to temporary disk and then
  deleted it. That behavior violated the requirement even if later audit passed.
- Replaced overbroad audit claims with decoded Parquet/DuckDB/JSON/CSV inspection,
  errors that fail validation, bounded log checks, and a synthetic canary through
  the actual collector extraction/aggregation/storage code path.
- Benchmark keys are exactly `youtube_extraction_rate` and
  `local_processing_throughput`. Local measurement now actually aggregates;
  synthetic generation is included. Removed hardcoded scheduler speed claims.
- Tests no longer depend on unrecorded real network state or the owner's key;
  the two external adapter tests explicitly mock network boundaries.

## Executed verification

| Check | Result |
|---|---|
| `python -m pytest -v` | **30 passed**, no skips; see `evidence/pytest.txt` |
| `python scripts/privacy_audit.py` | **18 files**, no detected violations; canary passed |
| `python scripts/run_real_pilot.py` | **Exit 1**, missing `config/secret.key`, before collection |
| `python scripts/benchmark_suite.py` | Local benchmark completed; YouTube rate explicitly blocked |
| Actual stored schemas | Read synthetic Parquet schema and `DESCRIBE raw_events` from DuckDB |
| Existing real graph | 6 nodes, 9 edges, all six overlap attributes present |
| `git check-ignore config/secret.key` | Ignored |
| `git log --all -- config/secret.key` | No history for that path in fetched repository refs |
| Python compile and `git diff --check` | Passed |

Captured local benchmark: 73,272.6 input events/minute, 1,000 input events to
545 aggregated rows, 23.65 MiB Python allocations, 21.38 ms DuckDB query.
This query used a one-channel synthetic dataset (zero pairs), **not real OLAP
performance**. Greedy 0.105 ms vs PSO 3.234 ms in one synthetic run; not a general
speed or scaling guarantee. See `evidence/benchmark.json` and dependency versions
in `evidence/schemas-and-graph.json`.

## Actual schema inspection

Parquet aggregated columns: `viewer_hash`, `vtuber_channel_id`, `video_id`,
`first_seen`, `last_seen`, `appearances`, `source_type`. All are strings except
`appearances: int64`. DuckDB normalizes these to VARCHAR and BIGINT.
The raw schema retains `timestamp` and is normalized to first/last seen in the view.
No raw message field exists in these inspected schemas. These are **synthetic
outputs generated here**, because historical real Parquet/DuckDB is not in Git.

The existing real `data/real/analytics/network_graph.json` reports Dacapo–Baabel
`shared_any=18`, `shared_comments=18`, `shared_live_chat=0`; every edge's strong
metrics is zero. This is inspection of an existing export, not a fresh reproduction
of its source data or proof of historical key provenance. The file is unchanged.

## Unresolved limits and failed assumptions

- A fresh clone cannot run the real pilot without the original private key.
  Do not treat the expected missing-key failure as a successful pilot.
- No supported memory-only live-chat collector exists. Positive live-chat overlap
  and longitudinal live-chat overlap remain unproven on actual data here.
- The current pilot's one video/channel cannot prove longitudinal strength. Tests
  demonstrate the computation, not the existence of strong overlap in the wild.
- Historical Parquet without an identity manifest now requires manual migration
  after verifying original run/key provenance. A fingerprint is not a signature.
- Append batches protect source evidence but repeated collections can inflate
  appearance totals. Distinct-video metrics remain stable. Idempotent polling is
  a prerequisite in the next milestone.
- YouTube API extraction currently reads one page of up to 100 top-level comments;
  yt-dlp is bounded separately. Neither proves complete audience coverage.
- The audit is bounded by named fields, decoded pseudonym format, canaries and
  selected output directories. It cannot prove anonymity or absence of arbitrary
  unlabelled sensitive text, and does not inspect OS swap, backups, or deleted data.
- HMAC viewer pseudonyms remain linkable. This project does not observe lurkers,
  watch duration, or all viewers. A zero count may reflect incomplete collection.

The next milestone is prepared in `continuous-lightweight-collection.md`; it is
**not marked started or passed**. Restore/validate the original key privately,
validate historical data provenance, and complete the real evidence gate first.

## Exact changed files
- `.env.example`
- `.gitignore`
- `README.md`
- `analytics/exporter.py`
- `collector/mock_collector.py`
- `collector/youtube_collector.py`
- `core/hasher.py`
- `docs/continuous-lightweight-collection.md`
- `docs/evidence-milestone.md`
- `docs/evidence/benchmark.json`
- `docs/evidence/privacy-audit.json`
- `docs/evidence/pytest.txt`
- `docs/evidence/real-pilot.txt`
- `docs/evidence/schemas-and-graph.json`
- `requirements.txt`
- `scripts/benchmark_suite.py`
- `scripts/privacy_audit.py`
- `scripts/run_real_pilot.py`
- `scripts/test_live_chat_empirically.py`
- `storage/duckdb_engine.py`
- `storage/parquet_manager.py`
- `tests/test_milestone_regressions.py`
- `tests/test_real_adapters.py`
