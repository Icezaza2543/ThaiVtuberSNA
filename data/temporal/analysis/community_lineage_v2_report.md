# Phase T11: Multi-Year Community Lineage v2 Report

## Executive Summary
This report establishes persistent multi-year community identities across Thai VTuber network snapshots from 2020 through 2026. Across this seven-year longitudinal horizon, Louvain community partitions were mapped into **11 distinct persistent community lineages**, resolving arbitrary yearly community re-indexing into traceable genealogical structures.

### Key Methodological Contracts
1. **Deterministic Identity Resolution:** Community identities are assigned via backbone continuation (Jaccard similarity and bidirectional node overlap) rather than raw clustering indices.
2. **Separation of Relation Edges & Lifecycle States:** Adjacent transitions (`continuation`, `split_branch`, `merge_tributary`) are modeled separately from boundary states (`birth`, `disappearance`), preventing contradictory multi-state labels.
3. **Non-Equivalence with Agencies:** Communities reflect emergent audience co-interaction structures. While dominant agency homophily is tracked, communities are never treated as formal corporate agency proxies.

---

## 1. Persistent Community Lifecycles

| Lineage ID | Birth Year | Last Observed | Lifespan (Yrs) | Status | Dominant Agency | Agency Share | Total Creators | Churn Rate | Split Ancestors | Merge Ancestors |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :--- | :--- |
| `LINEAGE_01` | 2020 | 2020 | 1 | `DISAPPEARED` | Independent | 100.0% | 8 | 0.0% | None | None |
| `LINEAGE_02` | 2020 | 2024 | 5 | `DISAPPEARED` | Independent | 97.7% | 44 | 75.5% | LINEAGE_04; LINEAGE_05; LINEAGE_06 | None |
| `LINEAGE_03` | 2020 | 2020 | 1 | `DISAPPEARED` | Independent | 83.3% | 6 | 0.0% | None | None |
| `LINEAGE_04` | 2021 | 2021 | 1 | `DISAPPEARED` | Independent | 80.0% | 20 | 0.0% | None | None |
| `LINEAGE_05` | 2021 | 2022 | 2 | `DISAPPEARED` | Independent | 90.0% | 30 | 70.0% | LINEAGE_02; LINEAGE_04 | None |
| `LINEAGE_06` | 2021 | 2026 | 6 | `ACTIVE` | Independent | 40.5% | 84 | 53.9% | LINEAGE_05 | None |
| `LINEAGE_07` | 2021 | 2026 | 6 | `ACTIVE` | Independent | 77.4% | 106 | 65.7% | LINEAGE_02; LINEAGE_04; LINEAGE_05; LINEAGE_06; LINEAGE_10 | None |
| `LINEAGE_08` | 2023 | 2026 | 4 | `ACTIVE` | Independent | 46.9% | 64 | 51.6% | LINEAGE_02; LINEAGE_07; LINEAGE_10 | None |
| `LINEAGE_09` | 2023 | 2023 | 1 | `DISAPPEARED` | Independent | 66.7% | 3 | 0.0% | None | None |
| `LINEAGE_10` | 2025 | 2025 | 1 | `DISAPPEARED` | Independent | 72.7% | 22 | 0.0% | LINEAGE_02; LINEAGE_07 | None |
| `LINEAGE_11` | 2026 | 2026 | 1 | `ACTIVE` | Unknown | 100.0% | 8 | 0.0% | None | None |

### Substantive Observations on Community Lifecycles
- **Persistent Backbones:** 4 lineages exhibited extended multi-year persistence (>= 4 years lifespan).
- **Active Clusters in 2026:** 4 lineages remain active in the terminal 2026 observation window.
- **Emergent Specialization:** Lineages with dominant agencies (e.g. Algorhythm Project, Polygon Official) maintain high internal cohesion while gradually absorbing peripheral independent creators.

---

## 2. Genealogical Relation Edges (Adjacent Years)

- **Primary Continuations:** 12 transitions
- **Split Branches:** 23 transitions
- **Merge Tributaries:** 2 transitions

| Transition Years | From Comm | To Comm | From Lineage | To Lineage | Relation Type | Shared Channels | Jaccard | Fwd Overlap | Bwd Overlap |
| :---: | :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| 2020 -> 2021 | `comm_2020_02` | `comm_2021_05` | `LINEAGE_02` | `LINEAGE_02` | `continuation` | 4 | 0.333 | 57.1% | 44.4% |
| 2021 -> 2022 | `comm_2021_02` | `comm_2022_02` | `LINEAGE_05` | `LINEAGE_05` | `continuation` | 9 | 0.300 | 64.3% | 36.0% |
| 2021 -> 2022 | `comm_2021_01` | `comm_2022_01` | `LINEAGE_04` | `LINEAGE_07` | `split_branch` | 7 | 0.167 | 35.0% | 24.1% |
| 2021 -> 2022 | `comm_2021_01` | `comm_2022_02` | `LINEAGE_04` | `LINEAGE_05` | `split_branch` | 7 | 0.184 | 35.0% | 28.0% |
| 2021 -> 2022 | `comm_2021_01` | `comm_2022_04` | `LINEAGE_04` | `LINEAGE_02` | `split_branch` | 4 | 0.125 | 20.0% | 25.0% |
| 2021 -> 2022 | `comm_2021_02` | `comm_2022_01` | `LINEAGE_05` | `LINEAGE_07` | `split_branch` | 3 | 0.075 | 21.4% | 10.3% |
| 2021 -> 2022 | `comm_2021_03` | `comm_2022_03` | `LINEAGE_06` | `LINEAGE_06` | `split_branch` | 6 | 0.214 | 50.0% | 27.3% |
| 2021 -> 2022 | `comm_2021_03` | `comm_2022_04` | `LINEAGE_06` | `LINEAGE_02` | `split_branch` | 4 | 0.167 | 33.3% | 25.0% |
| 2021 -> 2022 | `comm_2021_05` | `comm_2022_02` | `LINEAGE_02` | `LINEAGE_05` | `split_branch` | 3 | 0.097 | 33.3% | 12.0% |
| 2021 -> 2022 | `comm_2021_05` | `comm_2022_04` | `LINEAGE_02` | `LINEAGE_02` | `split_branch` | 4 | 0.191 | 44.4% | 25.0% |
| 2021 -> 2022 | `comm_2021_04` | `comm_2022_01` | `LINEAGE_07` | `LINEAGE_07` | `merge_tributary` | 7 | 0.219 | 70.0% | 24.1% |
| 2022 -> 2023 | `comm_2022_01` | `comm_2023_04` | `LINEAGE_07` | `LINEAGE_07` | `continuation` | 11 | 0.256 | 37.9% | 44.0% |
| 2022 -> 2023 | `comm_2022_03` | `comm_2023_01` | `LINEAGE_06` | `LINEAGE_06` | `continuation` | 19 | 0.463 | 86.4% | 50.0% |
| 2022 -> 2023 | `comm_2022_01` | `comm_2023_02` | `LINEAGE_07` | `LINEAGE_08` | `split_branch` | 8 | 0.151 | 27.6% | 25.0% |
| 2022 -> 2023 | `comm_2022_02` | `comm_2023_01` | `LINEAGE_05` | `LINEAGE_06` | `split_branch` | 5 | 0.086 | 20.0% | 13.2% |
| 2022 -> 2023 | `comm_2022_02` | `comm_2023_03` | `LINEAGE_05` | `LINEAGE_02` | `split_branch` | 7 | 0.143 | 28.0% | 22.6% |
| 2022 -> 2023 | `comm_2022_02` | `comm_2023_04` | `LINEAGE_05` | `LINEAGE_07` | `split_branch` | 5 | 0.111 | 20.0% | 20.0% |
| 2022 -> 2023 | `comm_2022_04` | `comm_2023_03` | `LINEAGE_02` | `LINEAGE_02` | `split_branch` | 8 | 0.205 | 50.0% | 25.8% |
| 2022 -> 2023 | `comm_2022_04` | `comm_2023_04` | `LINEAGE_02` | `LINEAGE_07` | `split_branch` | 4 | 0.108 | 25.0% | 16.0% |
| 2023 -> 2024 | `comm_2023_01` | `comm_2024_03` | `LINEAGE_06` | `LINEAGE_06` | `continuation` | 24 | 0.453 | 63.2% | 61.5% |
| 2023 -> 2024 | `comm_2023_02` | `comm_2024_02` | `LINEAGE_08` | `LINEAGE_08` | `continuation` | 22 | 0.440 | 68.8% | 55.0% |
| 2023 -> 2024 | `comm_2023_01` | `comm_2024_01` | `LINEAGE_06` | `LINEAGE_07` | `split_branch` | 8 | 0.081 | 21.1% | 11.6% |
| 2023 -> 2024 | `comm_2023_03` | `comm_2024_01` | `LINEAGE_02` | `LINEAGE_07` | `split_branch` | 19 | 0.235 | 61.3% | 27.5% |
| 2023 -> 2024 | `comm_2023_03` | `comm_2024_04` | `LINEAGE_02` | `LINEAGE_02` | `split_branch` | 8 | 0.250 | 25.8% | 88.9% |
| 2023 -> 2024 | `comm_2023_04` | `comm_2024_01` | `LINEAGE_07` | `LINEAGE_07` | `merge_tributary` | 20 | 0.270 | 80.0% | 29.0% |
| 2024 -> 2025 | `comm_2024_01` | `comm_2025_02` | `LINEAGE_07` | `LINEAGE_07` | `continuation` | 34 | 0.391 | 49.3% | 65.4% |
| 2024 -> 2025 | `comm_2024_02` | `comm_2025_03` | `LINEAGE_08` | `LINEAGE_08` | `continuation` | 28 | 0.560 | 70.0% | 73.7% |
| 2024 -> 2025 | `comm_2024_03` | `comm_2025_01` | `LINEAGE_06` | `LINEAGE_06` | `continuation` | 35 | 0.603 | 89.7% | 64.8% |
| 2024 -> 2025 | `comm_2024_01` | `comm_2025_04` | `LINEAGE_07` | `LINEAGE_10` | `split_branch` | 14 | 0.182 | 20.3% | 63.6% |
| 2024 -> 2025 | `comm_2024_04` | `comm_2025_02` | `LINEAGE_02` | `LINEAGE_07` | `split_branch` | 2 | 0.034 | 22.2% | 3.9% |
| 2024 -> 2025 | `comm_2024_04` | `comm_2025_03` | `LINEAGE_02` | `LINEAGE_08` | `split_branch` | 3 | 0.068 | 33.3% | 7.9% |
| 2024 -> 2025 | `comm_2024_04` | `comm_2025_04` | `LINEAGE_02` | `LINEAGE_10` | `split_branch` | 3 | 0.107 | 33.3% | 13.6% |
| 2025 -> 2026 | `comm_2025_01` | `comm_2026_02` | `LINEAGE_06` | `LINEAGE_06` | `continuation` | 40 | 0.571 | 74.1% | 71.4% |
| 2025 -> 2026 | `comm_2025_02` | `comm_2026_01` | `LINEAGE_07` | `LINEAGE_07` | `continuation` | 40 | 0.580 | 76.9% | 70.2% |
| 2025 -> 2026 | `comm_2025_03` | `comm_2026_03` | `LINEAGE_08` | `LINEAGE_08` | `continuation` | 24 | 0.453 | 63.2% | 61.5% |
| 2025 -> 2026 | `comm_2025_04` | `comm_2026_01` | `LINEAGE_10` | `LINEAGE_07` | `split_branch` | 9 | 0.129 | 40.9% | 15.8% |
| 2025 -> 2026 | `comm_2025_04` | `comm_2026_03` | `LINEAGE_10` | `LINEAGE_08` | `split_branch` | 6 | 0.109 | 27.3% | 15.4% |

---
*Report generated automatically by `scripts/build_community_lineage_v2.py`.*
