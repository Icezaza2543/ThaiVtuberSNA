# Thai VTuber SNA — Reproducible Research Dataset Release Notes

**Release Version:** 1.0.0
**Deterministic Content Hash:** `sha256_1036574679f392422b8120cb03591daa96a5dbfad75ef145b3e8149863910f76`
**Privacy Classification:** `NO_VIEWER_LEVEL_DATA`
**Documented Artifacts:** 39 files (1.04 MB)
**Generated Timestamp:** 2026-09-08T15:45:39.151676+00:00

---

## 1. Privacy & Data Classification

- **Public Creator Metadata:** Exposed (public VTuber channel IDs, names, agency affiliations).
- **Aggregate Network Metrics:** Exposed (pairwise edge counts, modularity, centrality, community sizes).
- **Viewer-Level Records:** **STRICTLY ZERO**. Zero raw user IDs, zero viewer pseudonyms, zero individual comments.

---

## 2. Rigorous Methodology & Slicing Rules

- **Temporal Interaction Slicing:** Strictly partitioned by interaction_time (from interaction_at, first_seen, or timestamp). Video publication date is NEVER used as fallback for temporal interaction slicing. Undated interaction records are strictly excluded from temporal slices.
- **Comment Volume & Pagination:** API commentThreads endpoint yields up to 100 comments per standard page. Exhaustive pagination was implemented in Phase T6, resolving all historical cap exposures (0 unresolved). Single-page pilot records are tracked explicitly under collection truncation metadata.
- **Network Construction:** Bipartite projection into co-commenter/co-chatter undirected graphs. Edge weight represents count of shared pseudonymized viewers active on both channels.
- **Lineage Genealogy:** Deterministic maximum-weight bipartite matching per adjacent-year pair using score W = 0.4*Jaccard + 0.3*Forward + 0.3*Backward with strict one-to-one backbone.

### Key Limitations

- Observational sampling: captures active commenters and chatters; silent viewers are unobserved.
- 2026 data reflects partial Year-To-Date window (PARTIAL_WINDOW_DESCRIPTIVE_ONLY).
- Agency affiliations represent selection-time status (agency_at_selection) and do not imply historical membership.
- Observed network structures reflect audience co-attendance, not direct creator coordination or causality.

---

## 3. Dataset Artifacts & Checksums

### T8: Lifecycle Events & Intervals
**Files:** 3 | **Size:** 64.4 KB

| File Path | Format | Size | SHA-256 Checksum |
| :--- | :---: | ---: | :--- |
| `data/temporal/lifecycle/channel_lifecycle_intervals.parquet` | parquet | 29.6 KB | `sha256_02a9c74d626c60a36...` |
| `data/temporal/lifecycle/lifecycle_events.parquet` | parquet | 30.8 KB | `sha256_e3be8f0d5b74fd599...` |
| `data/temporal/lifecycle/lifecycle_report.md` | md | 4.0 KB | `sha256_9ce6476954e445cc4...` |

---

### T9: Lifecycle Event Impact Analysis
**Files:** 2 | **Size:** 52.5 KB

| File Path | Format | Size | SHA-256 Checksum |
| :--- | :---: | ---: | :--- |
| `data/temporal/event_analysis/event_impact_metrics.parquet` | parquet | 45.0 KB | `sha256_6c5873664d8720219...` |
| `data/temporal/event_analysis/event_impact_report.md` | md | 7.5 KB | `sha256_9b26a18eb3f567f60...` |

---

### T10: Sensitivity & Robustness Analysis
**Files:** 3 | **Size:** 57.1 KB

| File Path | Format | Size | SHA-256 Checksum |
| :--- | :---: | ---: | :--- |
| `data/temporal/robustness/robustness_report.md` | md | 7.3 KB | `sha256_634e3615673dd5824...` |
| `data/temporal/robustness/robustness_summary.parquet` | parquet | 9.0 KB | `sha256_c56f61819634e2bee...` |
| `data/temporal/robustness/sensitivity_results.parquet` | parquet | 40.9 KB | `sha256_0ea5c9f7bad60bc79...` |

---

### T11: Community Lineage & Network Metrics
**Files:** 10 | **Size:** 195.6 KB

| File Path | Format | Size | SHA-256 Checksum |
| :--- | :---: | ---: | :--- |
| `data/temporal/analysis/agency_transition_matrix.parquet` | parquet | 5.9 KB | `sha256_831f2511b39488925...` |
| `data/temporal/analysis/channel_transition_summary.parquet` | parquet | 101.3 KB | `sha256_bbd04bafb81a8919d...` |
| `data/temporal/analysis/community_lifecycles.parquet` | parquet | 8.7 KB | `sha256_61b9a267feaf66df0...` |
| `data/temporal/analysis/community_lineage.parquet` | parquet | 6.0 KB | `sha256_9c37cbbe8c2f73522...` |
| `data/temporal/analysis/community_lineage_v2.parquet` | parquet | 9.1 KB | `sha256_402ee6c0d3770a252...` |
| `data/temporal/analysis/community_lineage_v2_report.md` | md | 9.7 KB | `sha256_5a59668eaeb7efaa3...` |
| `data/temporal/analysis/community_snapshots.parquet` | parquet | 12.7 KB | `sha256_e13e6436f1a707151...` |
| `data/temporal/analysis/temporal_community_report.md` | md | 19.4 KB | `sha256_a52ffdee640ad4634...` |
| `data/temporal/analysis/temporal_migration_report.md` | md | 15.2 KB | `sha256_e0b13ad8c7d0a8d7c...` |
| `data/temporal/analysis/yearly_network_metrics.parquet` | parquet | 7.6 KB | `sha256_bdeaffc0822b32033...` |

---

### T12: Audience Cohort Survival
**Files:** 4 | **Size:** 31.7 KB

| File Path | Format | Size | SHA-256 Checksum |
| :--- | :---: | ---: | :--- |
| `data/temporal/cohorts/cohort_reactivation.parquet` | parquet | 5.6 KB | `sha256_4a3949f5017b469c7...` |
| `data/temporal/cohorts/cohort_retention_matrix.parquet` | parquet | 10.4 KB | `sha256_edc7da18dfad0e196...` |
| `data/temporal/cohorts/cohort_survival.parquet` | parquet | 7.1 KB | `sha256_54cbb235498f78295...` |
| `data/temporal/cohorts/cohort_survival_report.md` | md | 8.6 KB | `sha256_5036c08ef461adf22...` |

---

### T13: Bridge Dynamics & Centrality
**Files:** 4 | **Size:** 132.6 KB

| File Path | Format | Size | SHA-256 Checksum |
| :--- | :---: | ---: | :--- |
| `data/temporal/centrality/bridge_dynamics.parquet` | parquet | 29.6 KB | `sha256_f710c1c0cc65ec94d...` |
| `data/temporal/centrality/bridge_dynamics_report.md` | md | 30.7 KB | `sha256_a8807146e599538a4...` |
| `data/temporal/centrality/centrality_change_points.parquet` | parquet | 15.2 KB | `sha256_a47cee69b09984a1b...` |
| `data/temporal/centrality/yearly_centrality.parquet` | parquet | 57.0 KB | `sha256_97ed2e5a06675021d...` |

---

### T14: Ecosystem Structural Evolution
**Files:** 3 | **Size:** 26.6 KB

| File Path | Format | Size | SHA-256 Checksum |
| :--- | :---: | ---: | :--- |
| `data/temporal/ecosystem/ecosystem_evolution_report.md` | md | 5.6 KB | `sha256_7e66c99329b79ece8...` |
| `data/temporal/ecosystem/structural_breaks.parquet` | parquet | 7.2 KB | `sha256_2a878bac07ed4ed10...` |
| `data/temporal/ecosystem/yearly_ecosystem_metrics.parquet` | parquet | 13.8 KB | `sha256_9ede583857887ac54...` |

---

### T15: Evidence Quality & Bias
**Files:** 4 | **Size:** 71.4 KB

| File Path | Format | Size | SHA-256 Checksum |
| :--- | :---: | ---: | :--- |
| `data/temporal/quality/bias_sensitivity.parquet` | parquet | 7.1 KB | `sha256_deb43738a77aa22a2...` |
| `data/temporal/quality/channel_evidence_quality.parquet` | parquet | 32.4 KB | `sha256_c8e5f957c99cd3edf...` |
| `data/temporal/quality/evidence_quality_report.md` | md | 9.4 KB | `sha256_a55945a868bc7235d...` |
| `data/temporal/quality/yearly_evidence_quality.parquet` | parquet | 22.5 KB | `sha256_889b9555865faa873...` |

---

### Integrity Reports
**Files:** 3 | **Size:** 19.5 KB

| File Path | Format | Size | SHA-256 Checksum |
| :--- | :---: | ---: | :--- |
| `data/temporal/research_integrity/t11_t16_integrity_report.md` | md | 8.2 KB | `sha256_718d14631501c7d72...` |
| `data/temporal/research_integrity/t11_t19_final_integrity_report.md` | md | 7.5 KB | `sha256_efb2ddf2a2c88dfd9...` |
| `data/temporal/research_integrity/t8_t10_integrity_report.md` | md | 3.8 KB | `sha256_6e5580228bec0413f...` |

---

### Network Snapshots
**Files:** 1 | **Size:** 416.2 KB

| File Path | Format | Size | SHA-256 Checksum |
| :--- | :---: | ---: | :--- |
| `data/temporal/snapshots/network_snapshots.parquet` | parquet | 416.2 KB | `sha256_4ba8560db946ff493...` |

---

### Pipeline State
**Files:** 2 | **Size:** 0.9 KB

| File Path | Format | Size | SHA-256 Checksum |
| :--- | :---: | ---: | :--- |
| `data/temporal/state/pipeline_state.json` | json | 0.3 KB | `sha256_6ff3199892e0c6bd4...` |
| `data/temporal/state/release_manifest.json` | json | 0.6 KB | `sha256_97d86a6f5dd2c44bf...` |

---

*Artifact manifest generated automatically via `scripts/build_dataset_release.py`.*