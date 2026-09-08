# Research Integrity Verification Report: T8–T10

This report is programmatically generated from committed analytical artifacts to verify evidence traceability and analytical consistency across Phases T8, T9, and T10.

## 1. T8 Lifecycle Evidence Tier Breakdown

### Historical Events Breakdown
- **VERIFIED Events**: 2
- **INFERRED_PROXY Events**: 224
- **UNKNOWN Events**: 0
- **Total Lifecycle Events**: 226

### Channel Historical Intervals Breakdown
- **VERIFIED Intervals**: 0
- **INFERRED_PROXY Intervals**: 226
- **UNKNOWN Intervals**: 11
- **Total Historical Intervals**: 237

## 2. T9 Event Impact Cohort Separation

- **PRIMARY_VERIFIED Anchors**: 2
- **EXPLORATORY_PROXY Events**: 222
- **UNKNOWN Events**: 9
- **Total Evaluated Event Cohorts**: 224

### Primary Verified Impact Details (+/- 90-Day Window)
| Event ID | Channel Name | Event Type | Event Date | Pre Viewers | Post Viewers | Focal Retention Rate | Evidence Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `evt_re_debut_UC3ZglUA` | UC3ZglUA0HEUCuGbe5b8zXKw | re_debut | 2022-01-17 | 0 | 0 | 0.0% | `INSUFFICIENT_EVIDENCE` |
| `evt_graduation_UC32lsx7` | UC32lsx7u7vqy63SguuuzmVg | graduation | 2025-12-20 | 0 | 0 | 0.0% | `INSUFFICIENT_EVIDENCE` |

## 3. T10 Cross-Depth Partition Metrics (T5 Stratified Baseline vs T6 Deepened)

| Year | T6 Nodes | T5 Nodes | Common Nodes | T6 Edges | T5 Edges | T6 Modularity ($Q$) | T5 Modularity ($Q$) | Real NMI | Real ARI |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2021 | 65 | 64 | 64 | 625 | 512 | 0.1354 | 0.1879 | 0.6135 | 0.4611 |
| 2022 | 92 | 88 | 88 | 965 | 857 | 0.1957 | 0.2067 | 0.5184 | 0.3583 |
| 2023 | 129 | 126 | 126 | 1503 | 1252 | 0.3144 | 0.3082 | 0.7437 | 0.7663 |
| 2024 | 157 | 155 | 155 | 2547 | 2387 | 0.3119 | 0.2782 | 0.9046 | 0.9432 |

## 4. T10 Modality Invariance Metrics (Year 2026)

| Modality | Active Nodes | Active Edges | Modularity ($Q$) | NMI to Unified Baseline | ARI to Unified Baseline |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `comment_only` | 160 | 1986 | 0.3248 | 0.8733 | 0.8878 |
| `unified` | 160 | 1997 | 0.5085 | 1.0000 | 1.0000 |

## 5. T10 Rule-Derived Robustness Classifications

| Finding ID | Domain | Metric | Measured Value | Classification | Rule Basis |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `FINDING_1_AGENCY_ISLAND_CLUSTERING` | Community Structure & Agency Homophily | mean_agency_purity | 0.7012 | `ROBUST` | Stable across the tested parameter range (mean_agency_purity=0.701 >= 0.70). |
| `FINDING_2_MAJOR_COMMUNITY_PERSISTENCE` | Macro-Community Partition Stability | mean_res_nmi | 0.6989 | `MODERATELY_SENSITIVE` | Shows moderate variation across the tested parameter range (0.50 <= mean_res_nmi=0.699 < 0.70). |
| `FINDING_3_BRIDGE_CREATOR_RANKINGS` | Network Centrality & Cross-Agency Bridges | mean_bridge_top5_jaccard | 0.2500 | `MODERATELY_SENSITIVE` | Shows moderate variation across the tested parameter range (0.20 <= bridge_jaccard=0.250 < 0.50). |
| `FINDING_4_PERIPHERAL_INDEPENDENT_INTEGRATION` | Small Creator Integration & Thresholding | node_retention_ratio_th5 | 0.4395 | `HIGHLY_SENSITIVE` | Substantially sensitive to parameter perturbation (node_retention_ratio=0.439 < 0.45). |
| `FINDING_5_DATASET_DEPTH_CONCORDANCE` | Data Provenance (T5 Stratified vs T6 Deepened) | mean_t5_t6_nmi_res1 | 0.6950 | `ROBUST` | Stable across the tested parameter range (real_depth_nmi=0.695 >= 0.50). |
| `FINDING_6_LIVE_CHAT_STANDALONE_SUFFICIENCY` | Evidence Modality (Live Chat vs Comment) | historical_live_edges | 0.0000 | `INSUFFICIENT_EVIDENCE` | Evidence insufficient to evaluate (zero or near-zero historical live-chat edges recorded). |

---
*Report generated automatically by `scripts/generate_integrity_report.py`.*
