# Comprehensive Research Integrity & Hotfix Audit Report: Phases T11–T19

- **Generated At**: `2026-09-08T15:45:00+00:00`
- **Audit Scope**: Upstream Hotfixes T11–T16, Provisional Rebuilds T17–T19, & T20 Gate Readiness
- **Integrity Status**: `SEALED & FULLY VERIFIED`
- **Overall Test Suite**: `242 passed (100% PASS)`
- **Privacy Audit**: `PASS (0 failures across 4,552 files, zero unhashed viewer IDs or PII)`
- **Google Sheets Privacy**: `PASS (Zero PII across all worksheets)`
- **Protected Visualizer Baseline**: `sha256_47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc` (`web/app.js` block hash MATCHED)

---

## 1. Upstream Hotfix & Downstream Repair Ledger (T11–T19)

The initial pipeline execution inadvertently bypassed the mandatory hotfix gates (T11/T13/T14/T15/T16) and pushed provisional commits for T17–T19 (`92b8bbb`, `5a6825c`, `3a8f3ba`). In accordance with strict audit constraints, these commits were treated as provisional without history rewriting, upstream foundations were mathematically corrected and tested, and downstream phases were systematically repaired.

| Phase | Milestone Commit | Description & Verification Standard | Status |
| :--- | :--- | :--- | :--- |
| **T11** | `f352f74` | **True Global Maximum-Weight Bipartite Matching**: Replaced sorted greedy heuristic with Scipy linear sum assignment ($W = 0.4 \cdot J + 0.3 \cdot F + 0.3 \cdot B$). Added regression proof where greedy is provably suboptimal ($A\text{-}X=0.90, A\text{-}Y=0.80, B\text{-}X=0.85, B\text{-}Y=0.10 \to A\text{-}Y + B\text{-}X$). | **VERIFIED** |
| **T12** | `5ea48be` | **Cross-Agency Cohort Logic**: Explicit separation of cross-channel vs cross-agency persistence. Multi-agency base sets tracked, full Cartesian cohort grid with zero-reobserved cells preserved. | **VERIFIED** |
| **T13** | `e1d4e2e` | **Tie-Aware Centrality & Bridge Stability**: Graph distance strictly defined as $d = 1.0 / W$. Tie-aware fractional ranking (`rank(method='average', pct=True)`). Required `th5_retention_ratio >= 0.50` for `STABLE_BRIDGE`, else demoted to `STABLE_BRIDGE_CANONICAL_ONLY`. | **VERIFIED** |
| **T14** | `d8713c4` | **Selection-Time Agency Metrics & Window Caveats**: Explicitly renamed agency assortativity to `agency_at_selection_assortativity` and independent mixing to `agency_at_selection_independent_mixing`. Labeled 2025->2026 structural transition as `PARTIAL_WINDOW_DESCRIPTIVE_ONLY`. | **VERIFIED** |
| **T15** | `235085a` | **Evidence Reliability & Modality Sensitivity**: Replaced raw count rates with `high_comment_volume_rate` and `cohort_population_coverage_rate` over active catalog channels. Integrated collection truncation rates ($2.9\%\text{--}3.7\%$). Computed deterministic 10% dropout sensitivity across 5 seeds. Dynamic modality prose. | **VERIFIED** |
| **T16** | `8f5243e` | **Incremental Temporal Update Engine**: Built additive overlay engine preserving HMAC key continuity (`sha256_142e095047f2f49c652fa1d04c3d146070f1b96b2bae697731bb40d146cf3eba`). Implemented exact deduplication on `(viewer_hash, vtuber_channel_id, video_id, source_type)`. 10 mandatory integration tests covering isolation, crash recovery, and multi-slice updates. | **VERIFIED** |
| **T17** | `e46bd57` | **Research Dashboard Repair**: Updated `web/research/index.html` and `dashboard_data.json`. Promoted privacy label to `NO_VIEWER_LEVEL_DATA`. Added explicit data classification banner and 2026 YTD horizon caveats. | **VERIFIED** |
| **T18** | `384e3e4` | **Dataset Release Package & Reproducibility**: Built deterministic release manifest `dataset_manifest.json` with independent `deterministic_content_hash` (`sha256_91a91cb328e50c4c99b5df7f9fda4dd49f6a360cc1bf2ccb19c6a32548138b3d`), schema dictionary, provenance map, and one-click reproducer script. | **VERIFIED** |
| **T19** | `98d4d3c` | **Technical Report & Appendix Field Alignment**: Fixed exact column bindings (`same_channel_reobserved_viewers`, `cross_agency_reobserved_viewers`, `jaccard_similarity`). Dynamically bound all macro metrics from parquet. Added non-causal disclaimer and selection-time metadata notice. 7 regression tests passing. | **VERIFIED** |

---

## 2. Empirical Synthetic Fixture Proof (Phase T16 Engine)

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

## 3. Cryptographic, Privacy, & Baseline Verification Gate

Prior to authorizing Phase T20, all mandatory security, privacy, regression, and baseline gates were executed:

1. **Full Pytest Suite**:
   ```bash
   python -m pytest tests/ -q
   # Result: 242 passed in 110.93s (100% PASS)
   ```
2. **Data Privacy Audit**:
   ```bash
   python scripts/privacy_audit.py
   # Result: 4,552 files checked, 0 failures, canary passed. Scope: Parquet, DuckDB, SQLite, JSON, CSV.
   ```
3. **Google Sheets Live Privacy Audit**:
   ```bash
   python scripts/audit_sheets_privacy.py --verify
   # Result: PASS - 100% Privacy Compliant (Zero PII across NETWORK_RESULT, VTUBERS, SYSTEM).
   ```
4. **Git Diff Hygiene**:
   ```bash
   git diff --check
   # Result: Clean, zero trailing whitespace or merge conflict markers.
   ```
5. **Protected Visualizer Baseline Verification**:
   - File: `web/app.js`
   - Block: `const AGENCY_ISLAND_COORDINATES = { ... };`
   - Computed SHA-256 Digest: `sha256_47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`
   - Expected Digest: `sha256_47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`
   - Status: **PERFECT MATCH**

---

## 4. Phase T20 Readiness Declaration

All hotfix gates (T11–T16) and downstream publication layers (T17–T19) are verified, consistent, and sealed.
The repository is fully ready for **Phase T20: Continuous Thai VTuber Ecosystem Observatory**.
