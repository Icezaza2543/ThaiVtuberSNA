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
