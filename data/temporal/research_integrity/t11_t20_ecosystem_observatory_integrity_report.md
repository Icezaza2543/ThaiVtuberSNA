# Programmatic Research Integrity Report: Phases T11–T20

- **Generated At**: `2026-09-08T15:56:00+00:00`
- **Audit Scope**: Upstream Hotfixes T11–T16, Repaired Layers T17–T19, & Phase T20 Continuous Observatory
- **Integrity Status**: `SEALED & PRODUCTION READY`
- **Overall Test Suite**: `250 passed in full test suite (100% PASS)`
- **Data Privacy Audit**: `PASS (0 failures across 4,554 files, zero unhashed viewer IDs or PII)`
- **Google Sheets Live Audit**: `PASS (100% Privacy Compliant, zero PII)`
- **Visualizer Protected Baseline**: `sha256_47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc` (`web/app.js` MATCHED)
- **Pre-2026 Historical Snapshot Digest**: `sha256_2588ce1ce8e48df69a449ebe3bb8de7266b1cf6bf18b08495ae4d4acc5c43805` (BYTE-IDENTICAL)
- **HMAC Key Fingerprint**: `sha256_142e095047f2f49c652fa1d04c3d146070f1b96b2bae697731bb40d146cf3eba` (CONTINUOUS)

---

## 1. Executive Summary & Hotfix Gate Resolution

The previous run inadvertently bypassed the mandatory hotfix gates for Phases T11, T13, T14, T15, and T16, proceeding prematurely to provisional commits for T17–T19 (`92b8bbb`, `5a6825c`, `3a8f3ba`). In strict compliance with research governance and audit constraints, these provisional commits were preserved in git history without destructive rewriting, all mathematical flaws in upstream foundations were corrected and verified with regression tests, and all downstream artifacts (T17–T19) were rebuilt and verified before authorizing Phase T20.

Phase T20 (Continuous Thai VTuber Ecosystem Observatory) has now been fully engineered, validated with 8 comprehensive integration tests, and deployed with automated quality gates and fail-safe rollback mechanisms.

---

## 2. Complete Milestone & Commit Ledger (T11–T20)

| Phase | Commit | Architecture / Implementation Summary | Validation Result |
| :--- | :--- | :--- | :--- |
| **T11** | `f352f74` | **True Global Maximum-Weight Bipartite Matching**: Replaced sorted greedy heuristic with global maximum-weight bipartite matching ($W = 0.4 \cdot J + 0.3 \cdot F + 0.3 \cdot B$). Added regression proof demonstrating greedy is suboptimal ($A\text{-}X=0.90, A\text{-}Y=0.80, B\text{-}X=0.85, B\text{-}Y=0.10 \to A\text{-}Y + B\text{-}X$). | **VERIFIED** |
| **T12** | `5ea48be` | **Cross-Agency Cohort Logic**: Explicitly separated cross-channel vs cross-agency persistence. Multi-agency base sets tracked, full Cartesian cohort grid with zero-reobserved cells preserved. | **VERIFIED** |
| **T13** | `e1d4e2e` | **Tie-Aware Centrality & Bridge Stability**: Graph distance defined as $d = 1.0 / W$. Average fractional ranking (`rank(method='average', pct=True)`). Strict requirement: `th5_retention_ratio >= 0.50` for `STABLE_BRIDGE`, otherwise demoted to `STABLE_BRIDGE_CANONICAL_ONLY`. | **VERIFIED** |
| **T14** | `d8713c4` | **Selection-Time Agency Metrics & Window Caveats**: Renamed agency metrics to `agency_at_selection_assortativity` and `agency_at_selection_independent_mixing`. Designated 2025->2026 structural transition as `PARTIAL_WINDOW_DESCRIPTIVE_ONLY`. | **VERIFIED** |
| **T15** | `235085a` | **Evidence Reliability & Modality Sensitivity**: Replaced raw count rates with `high_comment_volume_rate` and `cohort_population_coverage_rate` over active catalog channels. Integrated collection truncation rates ($2.9\%\text{--}3.7\%$). Computed deterministic 10% dropout sensitivity across 5 seeds. | **VERIFIED** |
| **T16** | `8f5243e` | **Incremental Temporal Update Engine**: Built additive overlay engine preserving HMAC key continuity (`sha256_142e095047f2f49c652fa1d04c3d146070f1b96b2bae697731bb40d146cf3eba`). Implemented exact deduplication on `(viewer_hash, vtuber_channel_id, video_id, source_type)`. 10 mandatory integration tests covering isolation, crash recovery, and multi-slice updates. | **VERIFIED** |
| **T17** | `e46bd57` | **Research Dashboard Rebuild**: Updated `web/research/index.html` and `dashboard_data.json`. Promoted privacy label to `NO_VIEWER_LEVEL_DATA`. Added explicit data classification banner and 2026 YTD horizon caveats. | **VERIFIED** |
| **T18** | `384e3e4` | **Dataset Release Package & Reproducibility**: Built deterministic release manifest `dataset_manifest.json` with independent `deterministic_content_hash` (`sha256_1036574679f392422b8120cb03591daa96a5dbfad75ef145b3e8149863910f76`), schema dictionary, provenance map, and one-click reproducer script. | **VERIFIED** |
| **T19** | `98d4d3c` | **Technical Report & Appendix Field Alignment**: Fixed exact column bindings (`same_channel_reobserved_viewers`, `cross_agency_reobserved_viewers`, `jaccard_similarity`). Dynamically bound all macro metrics from parquet. Added non-causal disclaimer and selection-time metadata notice. 7 regression tests passing. | **VERIFIED** |
| **Integrity**| `aa8c684` | **T11–T19 Final Integrity Report**: Documented synthetic fixture proof, verification ledgers, and privacy audits. | **VERIFIED** |
| **T20** | `c6a5237` | **Continuous Observatory Controller**: Implemented production CLI `scripts/observatory_controller.py`, run ledger, observatory state tracking, semver release pointer (`v1.0.0`), automated quality gates, and fail-safe rollback. 8 tests passing. | **VERIFIED** |

*Note: Provisional commits `92b8bbb` (T17), `5a6825c` (T18), and `3a8f3ba` (T19) are retained in commit history as provisional milestones prior to upstream corrections.*

---

## 3. Empirical Synthetic Fixture Proof (Phase T16 Engine)

To demonstrate that the Phase T16 Incremental Temporal Pipeline functions end-to-end with mathematical correctness, snapshot mutation, and strict historical isolation, a synthetic batch was executed against a sandboxed snapshot state.

### Fixture Parameters
- **Target Channels**: Channel A (`UCpGtwNmbOtgmcKIY81MIX_w`, Algorhythm Project) and Channel B (`UCGBkYTR4tMKS38TQHGWWLjg`, Pixela Project).
- **Synthetic Batch ID**: `batch_fixture_proof`
- **Incoming Evidence**: 2 interaction events from synthetic author `fixture_synthetic_viewer_x99` interacting with both Channel A (`2026-05-15T10:00:00Z`) and Channel B (`2026-05-15T10:05:00Z`).

### Empirical Verification Results

```
========================================================================================
PHASE T16 SYNTHETIC INCREMENTAL FIXTURE PROOF
========================================================================================
Target Edge: UCpGtwNmbOtgmcKIY81MIX_w <---> UCGBkYTR4tMKS38TQHGWWLjg
Window 1: yearly_2026     (window_start: 2026-01-01, window_end: 2026-12-31)
  - BEFORE shared_any:    15
  - AFTER shared_any:     16  (Delta: +1, verified)

Window 2: cumulative_2026 (window_start: 2020-01-01, window_end: 2026-12-31)
  - BEFORE shared_any:    43
  - AFTER shared_any:     44  (Delta: +1, verified)

Window 3: all_time        (window_start: 2020-01-01, window_end: 2026-12-31)
  - BEFORE shared_any:    43
  - AFTER shared_any:     44  (Delta: +1, verified)

Affected Snapshot Windows: [yearly_2026, cumulative_2026, all_time]
Batch Ingestion Status:    COMMITTED
Records Inserted:          2
Duplicates Suppressed:     0

Historical Baseline Isolation (Pre-2026 Windows: 2020–2025):
  - BEFORE Checksum:      sha256_2588ce1ce8e48df69a449ebe3bb8de7266b1cf6bf18b08495ae4d4acc5c43805
  - AFTER Checksum:       sha256_2588ce1ce8e48df69a449ebe3bb8de7266b1cf6bf18b08495ae4d4acc5c43805
  - Byte-Identity Match:  TRUE (Zero historical mutation)
========================================================================================
```

---

## 4. Phase T17 Research Dashboard Verification

- **Location**: `web/research/index.html` & `web/research/dashboard_data.json`
- **Data Classification**: `NO_VIEWER_LEVEL_DATA` (Aggregated macro statistics only)
- **Horizon Transparency**: Prominent warning banner articulating that 2026 represents a partial observation window (YTD) and that modularity / density trends must be interpreted cautiously.
- **Evidence Quality Integration**: Low, Moderate, and High tier distributions rendered across historical years.

---

## 5. Phase T18 Reproducibility Package Verification

- **Manifest**: `data/temporal/release/dataset_manifest.json`
- **Total Tracked Artifacts**: `39` across 11 functional domains
- **Deterministic Content Hash**: `sha256_1036574679f392422b8120cb03591daa96a5dbfad75ef145b3e8149863910f76`
- **Data Dictionary**: `data/temporal/release/data_dictionary.json` (6 schemas strictly matched)
- **Provenance Map**: `data/temporal/release/provenance_map.json`
- **Environment Dependencies**: `data/temporal/release/environment_dependencies.json`
- **Release Notes**: `data/temporal/release/dataset_release_notes.md`
- **Reproducer Orchestrator**: `scripts/reproduce_temporal_dataset.py` (passes `--dry-run` and full validation)

---

## 6. Phase T19 Technical Report Consistency

- **Location**: `data/temporal/report/technical_report.md` & `appendix_tables.md`
- **Dynamic Metric Binding**: Directly populated from parquet sources without hardcoded estimates.
- **Field Alignment**: Corrected bindings for `same_channel_reobserved_viewers`, `cross_agency_reobserved_viewers`, and `jaccard_similarity`.
- **Methodological Disclaimer**: Clear statement of non-causal observational framing, selection-time agency metadata semantics, and pending status of formal literature review.

---

## 7. Phase T20 Continuous Observatory Architecture

The observatory CLI controller (`scripts/observatory_controller.py`) establishes an automated, production-grade operational workflow:

1. **Commands Implemented**:
   - `status`: Displays real-time observatory health, dataset release version (`v1.0.0`), data freshness, historical baseline integrity, and coordinates block hash.
   - `validate`: Runs all 5 automated quality gates (coordinates, historical baseline, key continuity, release manifest, privacy audit).
   - `dry-run`: Simulates batch ingestion and checks duplicate suppression and affected slices without touching disk state.
   - `update`: Ingests incremental evidence, updates network snapshots, triggers downstream rebuilds, enforces quality gates, promotes semver version, and logs to ledger.
   - `publish`: Explicitly publishes current state under target semver pointer.
   - `rollback`: Reverts the last update from recovery metadata, deletes batch file, and resets dataset version.
2. **Persistent Run Ledger**: `data/temporal/observatory/run_ledger.json` logs every execution with complete recovery metadata, affected years, and quality gate outcomes.
3. **Observatory State Tracker**: `data/temporal/observatory/observatory_state.json` tracks active dataset version, last success run ID, last data interaction time, and baseline checksums.
4. **Stale Data Monitoring**: Automatically alerts if elapsed time since latest data interaction exceeds threshold (default: 30 days).
5. **Quality Gate Fail-Safe**: Any gate failure immediately rolls back the batch, restores snapshots from backup, logs the failure, and prevents version promotion.
6. **Automated Test Suite**: All 8 tests in `tests/test_observatory_controller.py` pass cleanly.

---

## 8. Cryptographic & Security Verification Gate Summary

1. **Full Pytest Suite**:
   ```bash
   python -m pytest tests/ -q
   # Result: 250 passed in 237.51s (100% PASS)
   ```
2. **Data Privacy Audit**:
   ```bash
   python scripts/privacy_audit.py
   # Result: 4,554 files checked, 0 failures, canary passed. Zero unhashed viewer IDs or PII.
   ```
3. **Google Sheets Live Privacy Audit**:
   ```bash
   python scripts/audit_sheets_privacy.py --verify
   # Result: PASS - 100% Privacy Compliant across all worksheets.
   ```
4. **Git Diff Hygiene**:
   ```bash
   git diff --check
   # Result: Clean, zero whitespace issues or conflict markers.
   ```
5. **Visualizer Protected Baseline**:
   - SHA-256 Digest: `sha256_47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc` (MATCHED)
6. **Pre-2026 Historical Snapshot Isolation**:
   - SHA-256 Digest: `sha256_2588ce1ce8e48df69a449ebe3bb8de7266b1cf6bf18b08495ae4d4acc5c43805` (MATCHED)

---

## 9. Conclusion & Production Readiness

All hotfix gates (T11–T16), repaired downstream layers (T17–T19), and Phase T20 Continuous Observatory have been executed with mathematical rigor, cryptographic integrity, and privacy compliance. The repository is sealed, reproducible, and production-ready on `main`.
