# Antigravity: continuous collection corrective work

Status: **not ready for continuous collection**.

Target: `feat/continuous-lightweight-collection`.
Code inspected locally: `a825cf0287741611090cd24c9731d9d56317abf8`
(local branch and cached origin ref agree; remote freshness was not checked).

The reviewer reports 39 passing tests and 1 failure on a fresh clone, plus
reproductions of the defects below. This handoff is based on that report and
static inspection; it does not claim a new test run or completed fixes.

Implement in the following order. Keep real datasets and production keys intact.
Do not resume collection or describe the milestone as ready until the acceptance
evidence below is available. No UI work; greedy remains the default scheduler.

## 1. Prevent incorrect or lost data

### Source separation — storage/parquet_manager.py

`write_events()` accepts mixed sources, chooses a filename from the first row,
and reconciles by viewer hash alone. Group input by channel/video/source before
writing, or reject mixed partitions before any mutation with a documented API
contract. Use the full presence identity when reconciling. Apply identical rules
to legacy migration, including mixed-source legacy files.

Regression: write comment and live-chat evidence for the same viewer/video,
repeat both mixed and separate batches in reversed order, and verify both sources
survive in decoded Parquet and DuckDB with unchanged repeated-poll counts.

### Stable partition identity — storage/parquet_manager.py

The current path still uses the first event's month. Define a canonical location
independent of batch order, event timestamp and polling date. Update readers and
migration together. Reconcile existing monthly duplicates explicitly; delete old
files only after verified successful migration. Migration must be restartable.

Regression: collect the same video/source across two months, including an earlier
timestamp arriving later; assert one logical partition and no duplicate presence
or repeated-poll inflation. Repeat after restart and after migration.

Additional defect found in static inspection: a reconciliation read error falls
through to overwriting the existing partition. Fail closed instead. Use unique
temporary files and serialize concurrent read/merge/replace for each partition.
Regression: corrupt/read-failing existing partition remains untouched; concurrent
writers cannot lose either batch; interrupted migration preserves recoverability.

### Dataset identity — collector/continuous_collector.py

Share a dataset identity validation path with `scripts/run_real_pilot.py`.
Validate the actual hasher's fingerprint against the dataset manifest before
network access, storage creation/writes or journal mutation. Existing data with
missing, malformed or mismatched identity must fail closed. Never infer historical
identity from hash length or overlap. New empty datasets may initialize identity
atomically under a defined policy; concurrent initialization must not mix keys.

Regression: matching identity succeeds; wrong/missing/malformed identity on an
existing dataset fails before network or writes. Inject a different hasher and
verify it cannot bypass identity checks. Use temporary synthetic keys/manifests.

## 2. Make repeated collection work

### Reschedule successful jobs — core/job_journal.py

`register_job()` only updates PENDING/RETRY rows; COMPLETED jobs never become
eligible again. Define a polling interval and durable next-collection time.
Re-enqueue due successful jobs across restarts, keep last success/checkpoint, and
separate retry attempts within a poll from successful polling generations.
Re-registration must not defeat backoff or duplicate an active claim.

Regression with an injected clock: complete poll A, register again, advance to
the due time, collect poll B containing a new viewer, and verify the new evidence
is present without inflating old evidence. Assert no early poll or active double
claim, and repeat across restart.

### Explicit extraction outcomes — collector/youtube_collector.py

Both extraction backends catch exceptions and return empty lists. Propagate a
sanitized typed failure or explicit outcome to the orchestrator. Distinguish a
successful empty response, disabled comments, unavailable live chat, rate limit,
partial capture and retryable extraction failure. Make fallback behavior explicit
so one backend's failure cannot silently become an empty successful job.
Do not persist or return raw exception payloads containing author IDs or text.

Regression: inject failures at the actual API and yt-dlp boundaries, rather than
only mocking the aggregate method. Failures enter retry/backoff or the specified
terminal state; a successful empty response alone yields EMPTY_RESULT. Include
canaries in exceptions and inspect outputs/logs for leaks.

## 3. Make recovery trustworthy

### Fence claim ownership — core/job_journal.py and orchestrator

Issue a unique claim token/generation per claim. Require it for commit, fail,
checkpoint and heartbeat updates using conditional SQL. Recovery invalidates the
old token, including when the same worker name is reused. Check mutation results.
Fence publication as well: checking ownership once before a file write leaves a
race. Serialize ownership validation and publication with recovery, or publish
attempt-scoped data through an ownership-checked commit protocol.

Regression: worker A claims, recovery runs, worker B claims, and A attempts commit,
failure, checkpoint update and data publication. Every stale operation must fail
without changing B's state or data. Include a barrier-controlled concurrent race,
and crash after data staging/publication but before journal completion.

### Enforce an actual deadline — collector/continuous_collector.py

The ThreadPoolExecutor context and as_completed currently wait for every job.
Stopping submissions or calling Future.cancel() does not stop a running thread.
Use deadline-aware adapters plus an isolation/termination strategy for blocking
extraction. Bound outstanding work, retry sleeps and request timeouts. Ensure an
expired attempt cannot publish data or complete later; report timeout explicitly.

Regression: a blocking extractor with a 0.25 s duration and a 0.01 s deadline
returns within a declared platform-aware tolerance, reports timeout, and cannot
write/commit afterward. Also test a longer blocking extractor, pending jobs,
multiple workers and clean shutdown. Report measured wall time, not only job count.

### Audit SQLite — scripts/privacy_audit.py

Support SQLite journal databases in both audit_file and full audit discovery.
Open read-only, inspect decoded columns and values in every relevant table using
bounded batches, and parse structured checkpoint JSON recursively. Include
WAL-visible committed records. Report corrupt/unreadable files as errors and
report sidecar coverage/limitations explicitly; do not count skipped files as PASS.

Regression: safe journal passes; forbidden columns, nested checkpoint fields and
raw canaries fail; corrupt DB reports ERROR; full audit discovers the journal.
Keep a WAL connection open for the WAL visibility test. Auditing must not modify
the database or echo private values.

## 4. Reproducible tests and readiness decision

The supplied hasher is currently ignored by persistent-key validation and by the
internally constructed YouTubeCollector. Inject dependencies consistently while
retaining production fail-closed defaults. Tests must use temporary datasets,
journals, keys and fingerprints and must not require the owner's secret.key,
.env, network access or existing data. Keep production missing-key tests.

Deliver:

- Regression tests covering every acceptance case above, with failure evidence
  against the original commit and passing evidence against the fix.
- Full test command, commit SHA, environment/dependency versions, actual counts,
  exit status and complete output from a clean checkout with no production key.
- Decoded audit results including SQLite and both adapter canary paths.
- A two-cycle synthetic integration run, restart/recovery evidence and measured
  deadline behavior; keep synthetic and real evidence clearly separated.
- Updated milestone documentation that replaces unsupported readiness claims,
  explains migration/count semantics, and lists unverified real-world conditions.

`strong_shared_comments = 1` remains an observation about the sampled comment
network. It does not establish scheduler recurrence, data safety, deadline
enforcement, live-chat coverage or recovery correctness. Reassess readiness only
after the fixes and evidence are reviewed; do not present that metric as proof
that continuous collection is ready.
