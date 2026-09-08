# Phase T14: Thai VTuber Ecosystem Structural Evolution Report (2020–2026)

## Executive Summary
This report provides an empirical macro-structural characterization of the Thai VTuber interaction network across its 2020–2026 evolution. All graph properties are derived from canonical multi-channel co-commenter and co-chatter edges. Year 2026 represents Year-To-Date (YTD) interaction evidence.

### Scientific Guardrails
1. **Strictly Non-Causal Descriptive Scope:** Identified topological shifts and structural break candidates reflect empirical co-interaction properties across sampled YouTube interaction data. No causal claims regarding creator popularity, algorithmic steering, or agency policies are inferred.
2. **Selection-Time Agency Metadata (`agency_at_selection`):** Agency classifications reflect status at cohort selection time, NOT dynamic historical corporate membership. Trends in assortativity or cross-sector mixing must not be interpreted as retroactive organizational shifts.
3. **Exclusion of 2025->2026 YTD from Full-Calendar Structural-Break Counts:** 2026 interactions represent an incomplete observation window. The 2025->2026 transition is classified strictly as `PARTIAL_WINDOW_DESCRIPTIVE_ONLY` and excluded from annualized structural-break totals.
4. **Zero Individual Viewer Hash Export:** Only aggregated macro network properties are published.

---

## 1. Longitudinal Macro Topological Metrics (2020–2026)

| Year | Active Channels | Edges | Density | Avg Degree | Edge Strength (W) | Giant Share | Comms | Modularity (Q) | Deg Gini | Agency at Sel Assort | Agency at Sel Mix | Cross-Comm Share |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2020** | 21 | 72 | 0.3429 | 6.9 | 228 | 100.0% | 3 | 0.197 | 0.345 | -0.029 | 5.6% | 48.6% |
| **2021** | 65 | 625 | 0.3005 | 19.2 | 2,767 | 100.0% | 5 | 0.133 | 0.399 | 0.003 | 46.6% | 65.9% |
| **2022** | 92 | 965 | 0.2305 | 21.0 | 2,697 | 100.0% | 4 | 0.201 | 0.444 | 0.056 | 46.5% | 62.2% |
| **2023** | 129 | 1,503 | 0.1820 | 23.3 | 4,364 | 100.0% | 5 | 0.315 | 0.457 | 0.125 | 44.0% | 53.1% |
| **2024** | 157 | 2,547 | 0.2080 | 32.5 | 4,666 | 100.0% | 4 | 0.311 | 0.442 | 0.130 | 42.0% | 45.6% |
| **2025** | 166 | 3,168 | 0.2313 | 38.2 | 7,029 | 100.0% | 4 | 0.319 | 0.426 | 0.091 | 43.2% | 48.6% |
| **2026 (YTD)** | 160 | 1,997 | 0.1570 | 25.0 | 5,750 | 95.0% | 4 | 0.508 | 0.489 | 0.133 | 39.8% | 36.8% |

---

## 2. Structural Break Candidates (Empirical Shift Detection)

Detected **8 full-calendar macro structural break candidates** across adjacent completed calendar years (and **2 partial-window descriptive observations** for 2025->2026 YTD, classified as `PARTIAL_WINDOW_DESCRIPTIVE_ONLY`):

| Transition | Scope | Metric Dimension | Category | From | To | Absolute Delta | Relative Shift | Descriptive Context |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `2020->2021` | `FULL_CALENDAR` | `active_channels` | `RAPID_ECOSYSTEM_EXPANSION` | 21 | 65 | +44 | +209.5% | Active creator count shifted by +209.5% YoY (21 to 65). |
| `2020->2021` | `FULL_CALENDAR` | `modularity` | `MODULAR_DIFFUSION` | 0.1968 | 0.1333 | -0.0635 | -32.3% | Community modularity Q shifted by -0.0635 (0.197 to 0.133). |
| `2020->2021` | `FULL_CALENDAR` | `density` | `DENSITY_DILUTION` | 0.3429 | 0.3005 | -0.0424 | -12.4% | Graph density shifted by -0.0424 (0.3429 to 0.3005). |
| `2020->2021` | `FULL_CALENDAR` | `agency_at_selection_independent_mixing` | `CROSS_SECTOR_INTEGRATION` | 0.0556 | 0.4656 | +0.41 | +737.4% | Agency-at-selection/independent bridging edge share shifted by +41.0% (5.6% to 46.6%). |
| `2021->2022` | `FULL_CALENDAR` | `modularity` | `MODULAR_CONSOLIDATION` | 0.1333 | 0.2007 | +0.0674 | +50.6% | Community modularity Q shifted by +0.0674 (0.133 to 0.201). |
| `2021->2022` | `FULL_CALENDAR` | `density` | `DENSITY_DILUTION` | 0.3005 | 0.2305 | -0.07 | -23.3% | Graph density shifted by -0.0700 (0.3005 to 0.2305). |
| `2022->2023` | `FULL_CALENDAR` | `modularity` | `MODULAR_CONSOLIDATION` | 0.2007 | 0.3146 | +0.1139 | +56.8% | Community modularity Q shifted by +0.1139 (0.201 to 0.315). |
| `2022->2023` | `FULL_CALENDAR` | `density` | `DENSITY_DILUTION` | 0.2305 | 0.182 | -0.0485 | -21.0% | Graph density shifted by -0.0485 (0.2305 to 0.1820). |
| `2025->2026 (YTD)` | `PARTIAL_WINDOW_DESCRIPTIVE_ONLY` | `modularity` | `PARTIAL_WINDOW_DESCRIPTIVE_ONLY` | 0.3189 | 0.5085 | +0.1896 | +59.5% | [PARTIAL_WINDOW_DESCRIPTIVE_ONLY] Community modularity Q shifted by +0.1896 (0.319 to 0.508). |
| `2025->2026 (YTD)` | `PARTIAL_WINDOW_DESCRIPTIVE_ONLY` | `density` | `PARTIAL_WINDOW_DESCRIPTIVE_ONLY` | 0.2313 | 0.157 | -0.0743 | -32.1% | [PARTIAL_WINDOW_DESCRIPTIVE_ONLY] Graph density shifted by -0.0743 (0.2313 to 0.1570). |

### Methodological Interpretation of Structural Shifts
- **Pioneer Explosion (2020 -> 2021):** Active channels tripled (+209.5%) accompanied by a surge in agency-at-selection/independent mixing from 5.6% to 46.6%, indicating the formation of an interconnected shared audience space across independent and emergent agency creators.
- **Modular Maturation (2022 -> 2023):** Modularity Q experienced a sustained shift upward (+0.114), reflecting the crystallization of distinct audience co-interaction clusters.
- **Partial-Window Observation (2025 -> 2026 YTD):** The partial 2026 observation window displays elevated modularity (Q = 0.508) and lower edge density (0.157), marked as `PARTIAL_WINDOW_DESCRIPTIVE_ONLY` due to incomplete calendar year exposure.

---
*Report generated automatically by `scripts/analyze_ecosystem_evolution.py`.*
