# Phase closure and codebase consolidation

The research phase is closed in scope. Ecosystem integration, new research, feature expansion and T20 remain paused. Evidence gaps are limitations, not follow-up tasks. This is a behavior-preserving consolidation, not independent verification of every research claim or production path.

## Baseline

- Commit: `83e97625bac0f5e0a0996f36267f040ea4efd6a1`; tracked worktree clean. Ignored local scratch diagnostics and an inaccessible local pytest cache were present and preserved.
- Remote recovery tag: `pre-refactor-20260909-83e9762-145346` (new tag; no replacement).
- Offline suite: **362 passed, 120 warnings in 127.75s (0:02:07)**.
- 400 tracked files; 120 production code files; 32,286 production code lines. Counting rule: tracked `.py`, `.js`, `.mjs` under core/, analytics/, storage/, collector/, scripts/, web/, config/; physical lines including comments/blanks. Tests/docs excluded from production count.
- Protected set: all 182 baseline tracked files under data/, web/, docs/evidence/, config/. SHA-256 of sorted JSON `{relative_path: file_SHA256}`: `8851626a45634c5b114cc3ac92b55efa9c755a554f808b532f96559d7659388b`. Compare every file before/after, not just aggregate counts. [Per-file baseline hashes](refactor_protected_hashes.json) are retained as machine-readable evidence.
- Coordinate block SHA-256: `47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`.

## Decisions and structure

Luna performed read-only code/caller mapping. Astra owns implementation and deletion decisions. Imports, dynamic DAG module names, subprocess entry points, documented CLI commands, tests, frontend consumers and output writers were inspected. No CI workflow directory exists in this checkout.

| Disposition | Path / responsibility | Reference evidence and rationale |
|---|---|---|
| KEEP | scripts/analysis_dag.py | Existing run_dag/analysis_context imported by reproduce_temporal_dataset.py, observatory_controller.py and integration fixtures. No competing rebuild pipeline; DAG and rebuild behavior retained. |
| MOVE | scripts/research_integrity_contract.py → analytics/research_integrity.py | Domain scope/series rules have no CLI. Updated all four callers: v2 builder, report refresher, source audit and regression tests. Old module removed; one canonical implementation, no unsupported shim. |
| MOVE | identity validation → core/creator_identity.py | Pure rules accept manifest and registry. Documented audit_creator_identity_mapping.py CLI and audit_identity import remain as an I/O wrapper, used by lifecycle builder and consistency tests. No alias/affiliation/evidence rule changed. |
| MOVE / DELETE | snapshot transformation → analytics/creator_snapshot.py | Script retains existing loader/writer and supported entry points. Removed only three sets and their population loop that were never read; later activity/tier transformation is unchanged. |
| KEEP | scripts/build_creator_lifecycle_evidence.py | Curated identity/event dictionary and provenance references unchanged; sole lifecycle writer retained. |
| UNCERTAIN | scratch/ | Ignored, untracked operator diagnostics, not part of Git consolidation. No deletion. |
| UNCERTAIN | old collab/market writers and quarantine writer | Overlapping outputs do not establish semantic equivalence. Old files contain unique curated evidence; quarantine artifact is required by tests. Retained without executing or rewriting frozen artifacts. |
| KEEP | migration/recovery tools and dependencies | Operational callers/unique behavior not proven obsolete. No deletion or dependency removal based solely on absent text matches. |

No frozen evidence, identifiers, keys, cohort membership, thresholds, formulas, workbook architecture, UI or production hold safeguards changed.

## Validation and equivalence

Batch 1: **20 passed in 1.37s** (snapshot characterization, existing source integrity and v2 data contracts); both existing identity/consistency audits PASS. All 182 protected files remain byte-identical.

A three-creator synthetic fixture was executed by the baseline snapshot writer before refactoring. The committed expected records are compared field-for-field after extraction; the persisted temporary Parquet is also compared with the returned DataFrame. No timestamp exclusion is used. No production rebuild or private-input validation is claimed.

Batch 2 targeted tests: **13 passed in 2.91s**. Integrated offline suite: **366 passed, 120 warnings in 119.95s (0:01:59)**, versus 362 baseline tests. All original scenarios/assertions and pytest discovery are retained; four tests add characterization and offline dispatch checks. The 120 existing warnings are NetworkX assortativity warnings.

Research consistency (including identity), synthetic privacy canary and module/CLI smoke checks PASS. At consolidation, Git security **failed at both baseline and milestone 27c2aaf**, with the same single finding: `docs/evidence/viewer_index_after_summary.json`, classified `PRIVATE_DATA` / `Individual viewer identity records`. The protected artifact was not edited, deleted or exempted; the consolidated command correctly returned nonzero at that time. The subsequent bounded correction below identifies and resolves this false positive without changing the artifact. No live/local private-data audit was run.

Existing DAG functions are AST-identical to baseline. All 182 protected files remain byte-identical, including public frontend assets and frozen data. Existing reproduction tests retain their existing normalization of `generated_at` and `calculated_at`; this refactor adds no exclusions. The new snapshot fixture comparison excludes no fields.

Final structure/counts: **408 tracked files, 122 production code files, 32,342 production code lines** (same counting rule), versus 400 / 120 / 32,286. This is not a claim of net repository shrinkage: reusable module boundaries, the audit dispatcher and regression evidence add files; the supported snapshot script shrinks **138 → 60 lines** and the old dead classification loop is removed. No dependency was proven unused, so requirements are unchanged.

Milestone 1: `27c2aaf` — extracted identity/snapshot/integrity domain logic, tested and pushed. Milestone 2 consolidates offline checks and current navigation; its commit is identified in the final handoff.

Browser validation: existing `frontend_observatory.mjs` and `research_v2.mjs` PASS at 1440×900, 1280×800, 1024×768 and 390×844, with zero page errors. Main/inspector/Research v1 pass their existing behavior checks; v2 retains 193 fields, 7 charts and 9 sections, with zero fetch/XHR requests and working no-JavaScript navigation. Four JavaScript syntax checks PASS (`app.js`, `observatory-ui.js`, `research_dashboard.js`, `research_v2.js`). Browser images/logs remain temporary, not added to Git. `git diff --check`, navigation links, nine module imports, reproduction `--help` and both DAG list CLI forms PASS.

## Canonical commands and navigation

- `python -m scripts.analysis_dag --list`: lists the existing DAG, no execution. Direct-script form is equivalent.
- `python -m scripts.analysis_dag --audit`: existing research consistency + Git security + synthetic privacy canary; preserves failures. Never calls run_dag, audit_local, collection or a workbook.
- `python scripts/audit_creator_identity_mapping.py` and `python scripts/audit_research_v2_consistency.py`: existing supported CLI wrappers.
- `python scripts/reproduce_temporal_dataset.py --help`: existing guarded reproduction interface; help only was smoke-tested. Actual production rebuild remains out of scope.
- `python -m pytest`: full offline suite, unchanged test discovery.
- [Documentation index](README.md): current contracts/results separated from historical milestone proposals. Previous src/ migration plans are retained with superseded-execution notices.

Luna's post-change reference review found no stale imports or lost supported callers. Old standalone collab/market writers, historical provenance identifiers, quarantine writer and operator utilities were retained rather than deleting unique behavior based on reference searches alone.

## Retained limitations

Identity quarantine and historical affiliation questions remain unresolved; full-registry audience denominators and authoritative organizational closure evidence remain unavailable. Existing analysis_context rebinding is retained to avoid an orchestration rewrite. Assertions and research rules retain their current semantics. Production collection/publishing remain on hold. Prior broader src/ architecture plans are historical proposals, not authorization to expand this phase.


## Bounded field-count audit correction

The previous Git finding was a classifier false positive: `viewer_index_after_summary.json` contains per-field completeness counters, not individual identities. The old nonempty-private-field rule treated the counter dictionary under `viewer_hash` as a viewer value.

`core/data_security.py` now recognizes only a nonempty mapping of known completeness-summary fields to exactly `TOTAL_ROWS`, `NON_EMPTY`, `MISSING`, `INVALID`, each an exact non-negative integer (booleans, floats, strings and nested payloads are rejected). Unknown fields/sample containers cannot enter the exception by containing counters. No filename/directory exemption is used. Credential detection remains first; recursive inspection is retained. Actual identity records, mixed summary/identity payloads and malformed counters remain private.

The protected summary remains byte-identical: SHA-256 `5ed9a60af0c5f7b331accbd47050a118b27e34bff97fd5bcb3fa14d5d70928ad`. This changes only classification of the validated aggregate shape, not research outputs, workbook data or unrelated audit rules. The earlier modular consolidation and conservative pruning claims/counts above remain historical facts; this correction is not additional refactoring.

Validation of the bounded correction:

- Targeted security/public-boundary tests: **69 passed in 9.05s**.
- Existing offline dispatcher: **research_consistency PASS; synthetic_privacy_canary PASS; git_security PASS; git_findings 0**.
- Full `python -m pytest`: **397 passed, 120 warnings in 124.96s (0:02:04)**. The 120 existing NetworkX warnings remain; test discovery and earlier assertions are unchanged.
- Protected summary byte comparison and `git diff --check`: **PASS**.
- No remaining findings from these audits. No workbook access, local private-dataset scan, collection or research-output regeneration was performed.
