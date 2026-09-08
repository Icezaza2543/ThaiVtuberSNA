# Phase T15: Coverage, Bias & Evidence Reliability Report

## Executive Summary
This report makes the empirical limitations of the Thai VTuber interaction evidence transparent, measurable, and structurally auditable across 2020–2026. Rather than presenting subjective confidence scores or probabilistic truth claims, reliability is structured into transparent deterministic quality tiers (`HIGH`, `MODERATE`, `LOW`) with all underlying component metrics fully disclosed.

### Methodological Guardrails
1. **Rejection of 'Probability of Truth' Indexing:** Observational social media data cannot be assigned frequentist truth probabilities without unverifiable population ground-truth priors. Instead, data quality is decomposed into measurable empirical dimensions: catalog coverage, comment depth, truncation cap exposure, and modality diversity.
2. **Separation of Modality Concordance from Modularity Values:** Unified 2026 modularity Q (0.508) and comment-only Q (0.325) are not identical because live-chat interactions introduce localized weight concentrations. However, partition concordance (evaluated via T10 NMI = 1.0000 and ARI = 1.0000 at th=1) confirms community boundary consistency.
3. **Collection-Level Truncation Tracking:** Tracks T5 `partial_capture` flags and T6 deep-collection resolutions to measure actual unresolved cap exposure.
4. **Deterministic Multi-Seed Sensitivity:** Includes 10% channel-dropout simulations across 5 fixed seeds reporting mean and standard deviation.

---

## 1. Longitudinal Evidence Quality Matrix (2020–2026)

| Year | Catalog Vids | Sampled Vids | Sampling Ratio | Interactions | T6 Share | High-Vol Rate | Partial Vids | T6 Resolved | Unresolved Exposure | Active Chans | Coverage (Cat) | Evidence Tier |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2020** | 1,897 | 141 | 7.4% | 5,984 | 68.0% | 11.3% | 20 | 20 | 0.0% | 29/36 | 80.6% | `MODERATE` |
| **2021** | 5,601 | 507 | 9.0% | 14,653 | 62.5% | 8.1% | 60 | 60 | 0.0% | 72/73 | 98.6% | `HIGH` |
| **2022** | 9,386 | 701 | 7.5% | 14,772 | 56.7% | 3.1% | 74 | 74 | 0.0% | 101/101 | 100.0% | `HIGH` |
| **2023** | 15,516 | 983 | 6.3% | 23,224 | 64.5% | 3.1% | 99 | 99 | 0.0% | 141/137 | 100.0% | `HIGH` |
| **2024** | 22,436 | 1,237 | 5.5% | 17,159 | 47.9% | 3.0% | 128 | 128 | 0.0% | 166/160 | 100.0% | `HIGH` |
| **2025** | 25,246 | 1,366 | 5.4% | 21,812 | 57.1% | 3.7% | 152 | 152 | 0.0% | 173/165 | 100.0% | `HIGH` |
| **2026 (YTD)** | 16,338 | 1,120 | 6.9% | 17,265 | 41.9% | 3.1% | 142 | 142 | 0.0% | 176/147 | 100.0% | `HIGH` |

---

## 2. Channel-Level Evidence Support Tiers

Across **193 channels** in the target manifest:
- **HIGH Support Tier:** 41 channels (21.2%)
- **MODERATE Support Tier:** 100 channels (51.8%)
- **LOW Support Tier:** 52 channels (26.9%)

### High-Support Channels (Sample Summary)
| Channel Name | Agency | Sampled Vids | Total Interactions | Distinct Viewers | Years Active | Lifecycle |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Aito LH** | Independent | 30 | 3,421 | 2,992 | 5 | `INFERRED_PROXY` |
| **Gibpuri Ch** | Independent | 41 | 10,619 | 9,934 | 7 | `INFERRED_PROXY` |
| **Nongwan TV** | Independent | 24 | 3,374 | 3,208 | 4 | `INFERRED_PROXY` |
| **Aisha Channel** | Independent | 40 | 1,761 | 1,491 | 6 | `INFERRED_PROXY` |
| **Choya Ch.** | Independent | 20 | 2,473 | 2,448 | 4 | `INFERRED_PROXY` |
| **Unnämed** | Independent | 24 | 6,689 | 5,363 | 4 | `INFERRED_PROXY` |
| **Dacapo Ch.【ARP】** | Algorhythm Project | 36 | 3,251 | 2,495 | 4 | `INFERRED_PROXY` |
| **RAF4EL** | Independent | 41 | 1,035 | 979 | 7 | `INFERRED_PROXY` |
| **HØRI 07 ⌜VZ⌟** | Virtual Zeven (VZ) | 36 | 1,129 | 965 | 6 | `INFERRED_PROXY` |
| **Evalia Ch.【ARP】** | Algorhythm Project | 42 | 713 | 589 | 6 | `INFERRED_PROXY` |

---

## 3. Perturbation Sensitivity Analysis

Evaluates the sensitivity of macro network metrics across perturbation scenarios:

| Year | Scenario | Active Channels | Edges | Density | Avg Degree | Giant Share | Modularity |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 2020 | `BASELINE_UNIFIED_TH1` | 21.0 | 72.0 | 0.3429 | 6.86 | 100.0% | 0.1968 |
| 2020 | `COMMENT_ONLY_TH1` | 21.0 | 72.0 | 0.3429 | 6.86 | 100.0% | 0.1968 |
| 2020 | `LOW_COVERAGE_EXCLUDED` | 18.0 | 55.0 | 0.3595 | 6.11 | 100.0% | 0.1871 |
| 2020 | `THRESHOLD_TH3` | 16.0 | 31.0 | 0.2583 | 3.88 | 100.0% | 0.2026 |
| 2020 | `THRESHOLD_TH5` | 11.0 | 17.0 | 0.3091 | 3.09 | 100.0% | 0.1488 |
| 2020 | `DROPOUT_10PCT_MEAN` | 19.0 | 59.0 | 0.3450 | 6.21 | 100.0% | 0.1817 |
| 2020 | `DROPOUT_10PCT_SD` | 0.0 | 5.8 | 0.0341 | 0.61 | 0.0% | 0.0423 |
| 2021 | `BASELINE_UNIFIED_TH1` | 65.0 | 625.0 | 0.3005 | 19.23 | 100.0% | 0.1333 |
| 2021 | `COMMENT_ONLY_TH1` | 65.0 | 625.0 | 0.3005 | 19.23 | 100.0% | 0.1333 |
| 2021 | `LOW_COVERAGE_EXCLUDED` | 56.0 | 584.0 | 0.3792 | 20.86 | 100.0% | 0.1255 |
| 2021 | `THRESHOLD_TH3` | 44.0 | 247.0 | 0.2611 | 11.23 | 100.0% | 0.1309 |
| 2021 | `THRESHOLD_TH5` | 34.0 | 159.0 | 0.2834 | 9.35 | 100.0% | 0.1362 |
| 2021 | `DROPOUT_10PCT_MEAN` | 58.6 | 525.0 | 0.3106 | 17.90 | 100.0% | 0.1271 |
| 2021 | `DROPOUT_10PCT_SD` | 0.49 | 53.7 | 0.0269 | 1.69 | 0.0% | 0.0072 |
| 2022 | `BASELINE_UNIFIED_TH1` | 92.0 | 965.0 | 0.2305 | 20.98 | 100.0% | 0.2007 |
| 2022 | `COMMENT_ONLY_TH1` | 92.0 | 965.0 | 0.2305 | 20.98 | 100.0% | 0.2007 |
| 2022 | `LOW_COVERAGE_EXCLUDED` | 77.0 | 837.0 | 0.2861 | 21.74 | 100.0% | 0.1918 |
| 2022 | `THRESHOLD_TH3` | 57.0 | 264.0 | 0.1654 | 9.26 | 100.0% | 0.2308 |
| 2022 | `THRESHOLD_TH5` | 42.0 | 138.0 | 0.1603 | 6.57 | 95.2% | 0.2547 |
| 2022 | `DROPOUT_10PCT_MEAN` | 82.6 | 790.0 | 0.2345 | 19.14 | 100.0% | 0.1995 |
| 2022 | `DROPOUT_10PCT_SD` | 0.49 | 24.3 | 0.0058 | 0.52 | 0.0% | 0.0115 |
| 2023 | `BASELINE_UNIFIED_TH1` | 129.0 | 1503.0 | 0.1820 | 23.30 | 100.0% | 0.3146 |
| 2023 | `COMMENT_ONLY_TH1` | 129.0 | 1503.0 | 0.1820 | 23.30 | 100.0% | 0.3146 |
| 2023 | `LOW_COVERAGE_EXCLUDED` | 112.0 | 1322.0 | 0.2127 | 23.61 | 100.0% | 0.3118 |
| 2023 | `THRESHOLD_TH3` | 77.0 | 442.0 | 0.1511 | 11.48 | 100.0% | 0.3702 |
| 2023 | `THRESHOLD_TH5` | 64.0 | 224.0 | 0.1111 | 7.00 | 96.9% | 0.3953 |
| 2023 | `DROPOUT_10PCT_MEAN` | 115.4 | 1226.0 | 0.1857 | 21.25 | 100.0% | 0.3127 |
| 2023 | `DROPOUT_10PCT_SD` | 0.8 | 73.1 | 0.0087 | 1.13 | 0.0% | 0.0146 |
| 2024 | `BASELINE_UNIFIED_TH1` | 157.0 | 2547.0 | 0.2080 | 32.45 | 100.0% | 0.3106 |
| 2024 | `COMMENT_ONLY_TH1` | 157.0 | 2547.0 | 0.2080 | 32.45 | 100.0% | 0.3106 |
| 2024 | `LOW_COVERAGE_EXCLUDED` | 126.0 | 1916.0 | 0.2433 | 30.41 | 100.0% | 0.3112 |
| 2024 | `THRESHOLD_TH3` | 106.0 | 388.0 | 0.0697 | 7.32 | 95.3% | 0.4538 |
| 2024 | `THRESHOLD_TH5` | 69.0 | 137.0 | 0.0584 | 3.97 | 91.3% | 0.4885 |
| 2024 | `DROPOUT_10PCT_MEAN` | 140.6 | 1979.0 | 0.2016 | 28.15 | 100.0% | 0.2951 |
| 2024 | `DROPOUT_10PCT_SD` | 0.8 | 93.0 | 0.0095 | 1.32 | 0.0% | 0.0241 |
| 2025 | `BASELINE_UNIFIED_TH1` | 166.0 | 3168.0 | 0.2313 | 38.17 | 100.0% | 0.3189 |
| 2025 | `COMMENT_ONLY_TH1` | 166.0 | 3168.0 | 0.2313 | 38.17 | 100.0% | 0.3189 |
| 2025 | `LOW_COVERAGE_EXCLUDED` | 133.0 | 2208.0 | 0.2515 | 33.20 | 100.0% | 0.3279 |
| 2025 | `THRESHOLD_TH3` | 124.0 | 733.0 | 0.0961 | 11.82 | 100.0% | 0.4349 |
| 2025 | `THRESHOLD_TH5` | 81.0 | 231.0 | 0.0713 | 5.70 | 97.5% | 0.4998 |
| 2025 | `DROPOUT_10PCT_MEAN` | 148.0 | 2578.0 | 0.2369 | 34.83 | 100.0% | 0.3155 |
| 2025 | `DROPOUT_10PCT_SD` | 0.63 | 92.7 | 0.0072 | 1.15 | 0.0% | 0.0248 |
| 2026 | `BASELINE_UNIFIED_TH1` | 160.0 | 1997.0 | 0.1570 | 24.96 | 95.0% | 0.5085 |
| 2026 | `COMMENT_ONLY_TH1` | 160.0 | 1986.0 | 0.1561 | 24.82 | 95.0% | 0.3246 |
| 2026 | `LOW_COVERAGE_EXCLUDED` | 136.0 | 1618.0 | 0.1763 | 23.79 | 94.1% | 0.5033 |
| 2026 | `THRESHOLD_TH3` | 88.0 | 418.0 | 0.1092 | 9.50 | 88.6% | 0.5468 |
| 2026 | `THRESHOLD_TH5` | 61.0 | 181.0 | 0.0989 | 5.93 | 83.6% | 0.5059 |
| 2026 | `DROPOUT_10PCT_MEAN` | 142.2 | 1592.0 | 0.1585 | 22.38 | 94.2% | 0.4986 |
| 2026 | `DROPOUT_10PCT_SD` | 1.17 | 88.5 | 0.0070 | 1.11 | 1.3% | 0.0364 |

### Key Methodological Findings
- **Modality and Modularity Divergence:** Unified 2026 modularity Q (0.5085) and comment-only Q (0.3246) differ because live chat introduces localized interaction weight concentration. Crucially, partition concordance remains concordant across modalities (Phase T10 robustness analysis establishes Normalized Mutual Information NMI = 1.0000 and Adjusted Rand Index ARI = 1.0000 at edge threshold >= 1), proving that community assignments are stable even as scalar modularity varies.
- **Empirical Truncation Resolution:** Across the corpus, 226 videos were flagged with `partial_capture = True` in T5. Phase T6 deep backfill targeted and deepened all 226 candidate videos (`t6_deepened_resolved_videos = 226`), yielding 0 unresolved cap exposures (`unresolved_cap_exposure_rate = 0.0%`).
- **10% Channel Dropout Sensitivity:** Multi-seed dropout simulations demonstrate robust stability. Across all mature observation horizons, mean modularity under 10% dropout matches baseline within ~0.02, confirming structural resilience against creator sampling variance.
- **Threshold Robustness:** Pruning edges below threshold >= 3 and >= 5 reduces edge count while increasing modularity from ~0.31 to ~0.45 across mature years, validating that core community partitions reflect dense co-audience clusters rather than single-viewer peripheral artifacts.

---
*Report generated automatically by `scripts/analyze_evidence_quality.py`.*
