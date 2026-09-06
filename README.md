# ThaiVtuberSNA

Experimental Thai VTuber audience-overlap analysis using HMAC-SHA256 pseudonyms,
Parquet, DuckDB, and NetworkX. Google Sheets is a lightweight registry/control
plane. Greedy is the default scheduler; PSO is optional. UI work is out of scope
for the evidence/continuity milestone.

## Evidence contract

- `videos_seen`: distinct video IDs with observed evidence of either source.
- `live_streams_seen`: distinct video IDs with `live_chat` evidence only.
- `shared_any`, `shared_live_chat`, `shared_comments`: distinct shared viewer
  pseudonyms, with the specified source required on both channels.
- `strong_shared_any`, `strong_shared_live_chat`, `strong_shared_comments`:
  the same pseudonym appears on at least **two distinct video IDs per channel**,
  using the indicated source on both channels. Repeated messages on one video
  never satisfy this definition. Comments under a livestream are still comments.
- The two source-specific sets can overlap; their counts must not be summed to
  obtain `shared_any`. Cross-source-only viewers can belong only to `shared_any`.
- These metrics describe observed commenters/chat participants, not all viewers,
  watch duration, or proof that a person attended an entire stream.

## Setup and verification

```bash
python -m pip install -r requirements.txt
python -m pytest -v
python scripts/privacy_audit.py
python scripts/benchmark_suite.py
```

Tests use synthetic identities and mocked network boundaries. They do not replace
real data validation. Benchmark JSON separates `youtube_extraction_rate` from
`local_processing_throughput`; missing real keys produce a blocked extraction
measurement, not an invented rate.

## Persistent key operations

Real collectors require `config/secret.key` and the matching
`config/secret.fingerprint` before network I/O. Environment salt overrides are
ignored. The fingerprint checks accidental key continuity only; it is not proof
of data integrity or authenticity.

**For this existing project, restore the ORIGINAL key from an encrypted offline
backup.** Keep that backup and test restoration in a private environment. Losing
it prevents linking newly collected viewer identities to historical snapshots.
Do not upload the key, credentials, or raw message payloads. `.gitignore` prevents
ordinary new tracking, not previously tracked secrets or arbitrary ZIP exports.

```bash
python -m core.hasher --verify-key
python scripts/run_real_pilot.py
```

`python -m core.hasher --init-key` is only for a genuinely new identity with no
existing key or fingerprint. It never runs automatically and cannot overwrite
existing identity records, including with the deprecated `--force` flag.

The pilot binds a new dataset to its key fingerprint in `identity_manifest.json`.
Historical data without this manifest requires verified provenance before manual
migration; see the next-milestone document. A fresh Git clone intentionally has no
real key or historical Parquet/DuckDB. It cannot independently reproduce the
historical graph solely from its JSON export.

## Current limits

The real collector implements public **comments**, not live-chat replay. The old
replay probe persisted raw chat to temporary files and is disabled. No raw
chat/comment text is deliberately persisted by the supported collector.
Pseudonymous viewer data remains linkable; HMAC is not an anonymity guarantee.

Storage appends atomic batches so one source cannot overwrite another. Repeated
polls can inflate `appearances` until collection idempotence is implemented;
distinct-video overlap is unaffected by duplicate rows. The pilot still samples
one configured video per channel and cannot establish longitudinal live evidence.

- [Milestone findings and test evidence](docs/evidence-milestone.md)
- [Continuous Lightweight Collection plan](docs/continuous-lightweight-collection.md)

## License

Internal Research / All Rights Reserved.
