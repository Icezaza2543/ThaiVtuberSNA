# Phase closure and codebase consolidation

The research phase is closed in scope. Ecosystem integration, new research, feature expansion and T20 remain paused. Evidence gaps are limitations, not follow-up tasks. This is a behavior-preserving consolidation, not independent verification of every research claim or production path.

## Baseline

- Commit: `83e97625bac0f5e0a0996f36267f040ea4efd6a1`; tracked worktree clean. Ignored local scratch diagnostics and an inaccessible local pytest cache were present and preserved.
- Remote recovery tag: `pre-refactor-20260909-83e9762-145346` (new tag; no replacement).
- Offline suite: **362 passed, 120 warnings in 127.75s (0:02:07)**.
- 400 tracked files; 120 production code files; 32,286 production code lines. Counting rule: tracked `.py`, `.js`, `.mjs` under core/, analytics/, storage/, collector/, scripts/, web/, config/; physical lines including comments/blanks. Tests/docs excluded from production count.
- Protected set: all 182 baseline tracked files under data/, web/, docs/evidence/, config/. SHA-256 of sorted JSON `{relative_path: file_SHA256}`: `8851626a45634c5b114cc3ac92b55efa9c755a554f808b532f96559d7659388b`. Compare every file before/after, not just aggregate counts.
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

Integration validation and final counts are recorded here after the remaining entry-point/documentation batch.

## Retained limitations

Identity quarantine and historical affiliation questions remain unresolved; full-registry audience denominators and authoritative organizational closure evidence remain unavailable. Existing analysis_context rebinding is retained to avoid an orchestration rewrite. Assertions and research rules retain their current semantics. Production collection/publishing remain on hold. Prior broader src/ architecture plans are historical proposals, not authorization to expand this phase.
