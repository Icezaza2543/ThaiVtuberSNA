# Final analytical and transactional hotfix verification

## Current analytical artifacts

T15 reads T10's 2026 comment-only configuration (threshold 1, resolution 1, seed 42): NMI **0.8733**, ARI **0.8878**. No numeric constants are used in the report binding.

| Year | Interaction evidence channels | Catalog published channels | Intersection | Catalog active recall | Target manifest coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020 | 29 | 36 | 29 | 0.805556 | 0.150259 |
| 2021 | 72 | 73 | 71 | 0.972603 | 0.373057 |
| 2022 | 101 | 101 | 99 | 0.980198 | 0.523316 |
| 2023 | 141 | 137 | 133 | 0.970803 | 0.730570 |
| 2024 | 166 | 160 | 156 | 0.975000 | 0.860104 |
| 2025 | 173 | 165 | 163 | 0.987879 | 0.896373 |
| 2026 | 176 | 147 | 143 | 0.972789 | 0.860104 |

T19 binds and regression-checks all **7 elapsed horizons** against the actual `pooled_cohort_size`, `pooled_reobserved_viewers`, `same_channel_persistence_rate` and `cross_channel_persistence_rate` columns. Missing required files/columns raise errors. Unsupported narrative findings and numeric fallbacks were removed.

## Transaction and downstream evidence

T16 crash points A (before artifact writes), B (after batch), C (after snapshot), D (before state promotion), and E (after transaction decision, before cleanup) all pass. Each recovered batch, snapshot, pipeline state and release-state file equals the clean execution byte for byte.

A durable undo journal precedes file mutations. A commit marker decides recovery; an interrupted uncommitted generation restores its before image. Advisory locks serialize ingestion. These checks simulate process interruption, not hardware power loss.

The update graph runs T7 communities and audience transitions, T11 lineage, T12 cohorts, T13 centrality, T14 ecosystem, T9 event effects, T10 sensitivity, T15 quality, T17 dashboard, T18 release, T19 report, final release checksums, and validation. The reproducer first rebuilds canonical snapshots. Catalog/lifecycle annotations and window definitions are explicit frozen inputs; derived analyses are not copied.

Synthetic **2027** update ran without skipped downstream stages and published **v1.1.0**. All-time shared audience changed **15 → 16 → 15**.

Rollback restored **40 public output checksums**, yearly/cumulative/all-time snapshots, all downstream products, T16 state and the observatory version/state. The batch disappeared. The operational run ledger deliberately retains the rollback audit trail. A separate injected failure after T12 also restores the complete before image.

Two clean synthetic input rebuilds: **REPRODUCIBLE_FROM_INPUTS**, **40 artifacts**, **0 differences**. Exact comparison rules and fingerprints are in [hotfix_synthetic_reproducibility.json](evidence/hotfix_synthetic_reproducibility.json).

The build clock is a declared deterministic reference, not a wall-clock collection timestamp. Comparison permits generated_at/calculated_at metadata and row/newline normalization; analytical values are not discarded.

The checked-in real release is **SELF_CONSISTENT**. The synthetic reproduction proof is not presented as proof that the real release was rebuilt from the live workbook.

## Validation

| Check | Result |
| --- | --- |
| `python -m pytest tests/ -q` | PASS: 286 tests; 106.266 seconds; final JUnit evidence saved |
| `python scripts/audit_data_security.py` | PASS: Git, local project files and all 11 existing workbook tabs; zero findings |
| `python scripts/privacy_audit.py` | PASS: 139 local files; canary passed; zero private local data findings |
| `python scripts/audit_sheets_privacy.py --verify` | PASS: all 11 existing workbook tabs; zero findings |
| `python scripts/validate_dataset_release.py` | PASS: 40 artifacts, 11 sections; SELF_CONSISTENT |
| `git diff --check` | PASS |

The final full suite passed **286 tests** after all code changes. The suite includes historical-window preservation, a shared writer lock and nested T16/T20 recovery. Small synthetic graphs emit undefined-assortativity warnings; these are not failed checks.

## Preserved security and historical contracts

- LEVEL A credentials remain local/ignored, never Git or Sheets.
- LEVEL B viewer records remain only in the existing authorized ThaiVtuber_SNA workbook. No private tabs were removed or written by this hotfix.
- Real T15 regeneration reads the private archive into RAM; exported artifacts are LEVEL C aggregates.
- Local generation journals are permitted only in external synthetic sandboxes. The real T20 local-storage guard remains active pending a transactional Sheet ingestion backend.
- HMAC key and fingerprint were not changed. Historical snapshots and coordinates were not regenerated.

Coordinates: `sha256_47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`.

Protected pre-2026 snapshot digest: `sha256_2588ce1ce8e48df69a449ebe3bb8de7266b1cf6bf18b08495ae4d4acc5c43805`.

No live collection or broad production-readiness claim is made by these sandbox results.
