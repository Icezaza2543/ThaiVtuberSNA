# Temporal Community Evolution Report (2020–2026)

## Executive Summary
This report analyzes the structural evolution of the Thai VTuber interaction network across calendar years 2020 to 2026.
Communities are detected using deterministic weighted Louvain modularity optimization (resolution=1.0, seed=42) on canonical network snapshots.

> [!NOTE]
> **Methodological Stance & Terminology:**
> - Communities are detected purely through observed interaction overlap (`shared_any` viewers). They do **NOT** equate to agencies.
> - Agency labels reflect `agency_at_selection` (frozen target cohort metadata) and are not assumed to be historically dynamic agency timelines.
> - Year 2020 carries a `LOW_CHANNEL_COVERAGE` and `LOW_EDGE_COUNT` flag and should be interpreted as an early pioneer cluster.
> - 2026 is an in-progress calendar year and is explicitly labeled **2026 YTD**.

---

## Yearly Community Overview

| Year | Active Channels | Active Edges | Communities | Modularity (Q) | Dominant Agency at Selection | Reliability Flag |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 2020 | 21 | 72 | 3 | 0.1968 | Independent | `LOW_CHANNEL_COVERAGE / LOW_EDGE_COUNT` |
| 2021 | 65 | 625 | 5 | 0.1333 | Independent | `NORMAL` |
| 2022 | 92 | 965 | 4 | 0.2007 | Independent | `NORMAL` |
| 2023 | 129 | 1503 | 5 | 0.3146 | Independent | `NORMAL` |
| 2024 | 157 | 2547 | 4 | 0.3106 | Independent | `NORMAL` |
| 2025 | 166 | 3168 | 4 | 0.3189 | Independent | `NORMAL` |
| 2026 YTD | 160 | 1997 | 4 | 0.5085 | Independent | `NORMAL` |

---

## Detailed Yearly Snapshots

### Year 2020
- **Active Channels:** 21
- **Observed Edges:** 72
- **Communities Detected:** 3
- **Weighted Modularity (Q):** 0.1968
- **Reliability Flag:** `LOW_CHANNEL_COVERAGE / LOW_EDGE_COUNT`

| Community ID | Channels | Top Agencies at Selection | Key Anchor Channels |
|:---|:---:|:---|:---|
| `comm_2020_01` | 8 | Independent (8) | 久檻夜くぅ / Qualia Qu Ch., Darin V, Reilim Channel, Aosora Popo Ch. |
| `comm_2020_02` | 7 | Independent (7) | Gibpuri Ch, Nerumi-s, Terios Ch., Sora A.C.G. |
| `comm_2020_03` | 6 | Independent (5), Virtual Zeven (VZ) (1) | Beariss Beam, ChaoPlaThong, Supeacha ⌜VZ⌟, JayVounter |

### Year 2021
- **Active Channels:** 65
- **Observed Edges:** 625
- **Communities Detected:** 5
- **Weighted Modularity (Q):** 0.1333
- **Reliability Flag:** `NORMAL`

| Community ID | Channels | Top Agencies at Selection | Key Anchor Channels |
|:---|:---:|:---|:---|
| `comm_2021_01` | 20 | Independent (16), Algorhythm Project (2), Ti19t (1) | SiamNeko Ch.【ARP】, Reilim Channel, Pyork The Pork, Pengu Ch.【Ti19t】 |
| `comm_2021_02` | 14 | Independent (13), Virtual Zeven (VZ) (1) | Beariss Beam, TeenWISU, Nerumi-s, JayVounter |
| `comm_2021_03` | 12 | Independent (7), Pixela Project (5) | Hinabe HongFei Ch. Pixela Project, Laguna JuJu Ch. Pixela Project, Princess Zelina Ch. Pixela Project, Aisha Channel |
| `comm_2021_04` | 10 | Algorhythm Project (6), Independent (4) | Asteroth Ch.【ARP】, Evalia Ch.【ARP】, Zekai Ch.【ARP】, Zenith Ch.【ARP】 |
| `comm_2021_05` | 9 | Independent (8), Virtual Zeven (VZ) (1) | Gibpuri Ch, Terios Ch., CooGa, Sora A.C.G. |

### Year 2022
- **Active Channels:** 92
- **Observed Edges:** 965
- **Communities Detected:** 4
- **Weighted Modularity (Q):** 0.2007
- **Reliability Flag:** `NORMAL`

| Community ID | Channels | Top Agencies at Selection | Key Anchor Channels |
|:---|:---:|:---|:---|
| `comm_2022_01` | 29 | Independent (16), Algorhythm Project (12), Euphora Project (1) | Evalia Ch.【ARP】, Reilim Channel, Ayna Ch.【ARP】, MONARICA |
| `comm_2022_02` | 25 | Independent (22), Virtual Zeven (VZ) (3) | dtto., 久檻夜くぅ / Qualia Qu Ch., Beariss Beam, Pyork The Pork |
| `comm_2022_03` | 22 | Pixela Project (15), Independent (4), Lumina Live (2) | Pixela Official, Mycara Melony Ch. Pixela-Mystic, Meraki Keimii Ch. Pixela Legends, Kitsuneko Mewten Ch. Pixela-Isekai |
| `comm_2022_04` | 16 | Independent (16) | Gibpuri Ch, Aisha Channel, Hey Solly, Laibaht Ch. / หลายบาท |

### Year 2023
- **Active Channels:** 129
- **Observed Edges:** 1503
- **Communities Detected:** 5
- **Weighted Modularity (Q):** 0.3146
- **Reliability Flag:** `NORMAL`

| Community ID | Channels | Top Agencies at Selection | Key Anchor Channels |
|:---|:---:|:---|:---|
| `comm_2023_01` | 38 | Pixela Project (16), Independent (13), Lumina Live (5) | Meraki Keimii Ch. Pixela Legends, Pixela Official, Ardalita Lilibelle Ch. Lumina-First-Myth, Hinabe HongFei Ch. Pixela Project |
| `comm_2023_02` | 32 | Algorhythm Project (20), Independent (7), Pixela Project (4) | Schneider Ch.【ARP】, Dacapo Ch.【ARP】, Eileennoir Ch., Unnämed |
| `comm_2023_03` | 31 | Independent (31) | TEENIE | WISLIVE, TeenWISU, Gibpuri Ch, Beariss Beam |
| `comm_2023_04` | 25 | Independent (21), Ti19t (1), Virtual Zeven (VZ) (1) | Pyork The Pork, นานาโฮชิ นานะ / 七星ナナ, moujob, Reilim Channel |
| `comm_2023_05` | 3 | Independent (2), Algorhythm Project (1) | Selene Ch.【ARP】, Victor Hoshino【GRADUATED】, Aosora Popo Ch. |

### Year 2024
- **Active Channels:** 157
- **Observed Edges:** 2547
- **Communities Detected:** 4
- **Weighted Modularity (Q):** 0.3106
- **Reliability Flag:** `NORMAL`

| Community ID | Channels | Top Agencies at Selection | Key Anchor Channels |
|:---|:---:|:---|:---|
| `comm_2024_01` | 69 | Independent (57), Algorhythm Project (5), Virtual Zeven (VZ) (3) | MOLLY, KAMAI, Evalia Ch.【ARP】, Nongwan TV |
| `comm_2024_02` | 40 | Algorhythm Project (24), Independent (15), Pixela Project (1) | Dacapo Ch.【ARP】, Baabel Ch.【ARP】, Solar Ch.【ARP】, Ginnique Ch.【ARP】 |
| `comm_2024_03` | 39 | Pixela Project (18), Independent (10), Lumina Live (9) | Pixela Official, Ardalita Lilibelle Ch. Lumina-First-Myth, T-Reina Ashyra Ch. Lumina-World-End, Mycara Melony Ch. Pixela-Mystic |
| `comm_2024_04` | 9 | Independent (9) | SwordAce, ghostmaiky, Gibpuri Ch, deksammy |

### Year 2025
- **Active Channels:** 166
- **Observed Edges:** 3168
- **Communities Detected:** 4
- **Weighted Modularity (Q):** 0.3189
- **Reliability Flag:** `NORMAL`

| Community ID | Channels | Top Agencies at Selection | Key Anchor Channels |
|:---|:---:|:---|:---|
| `comm_2025_01` | 54 | Pixela Project (17), Independent (17), Lumina Live (9) | Princess Zelina Ch. Pixela Project, Ardalita Lilibelle Ch. Lumina-First-Myth, Pixela Official, Aranis Elvene Ch. Pixela-Isekai |
| `comm_2025_02` | 52 | Independent (48), Virtual Zeven (VZ) (2), Pixela Project (1) | โป๊ะโกะ / PoKo ปลวกทูปเบ๋อ, KAMAI, Roxzy ロキジー, นานาโฮชิ นานะ / 七星ナナ |
| `comm_2025_03` | 38 | Algorhythm Project (20), Independent (16), Virtual Zeven (VZ) (1) | Baabel Ch.【ARP】, Dacapo Ch.【ARP】, Zekai Ch.【ARP】, Quentin Ch.【ARP】 |
| `comm_2025_04` | 22 | Independent (16), Algorhythm Project (4), AStars Production (2) | 【graduated】Ice Shirakoi Ch. / AStars Amakara, 【graduated】Amaris Sayo Ch. / AStars Amakara, Pyork The Pork, Midnight Ch.【ARP】 |

### Year 2026 YTD
- **Active Channels:** 160
- **Observed Edges:** 1997
- **Communities Detected:** 4
- **Weighted Modularity (Q):** 0.5085
- **Reliability Flag:** `NORMAL`

| Community ID | Channels | Top Agencies at Selection | Key Anchor Channels |
|:---|:---:|:---|:---|
| `comm_2026_01` | 57 | Independent (49), Virtual Zeven (VZ) (4), Algorhythm Project (1) | Nongwan TV, นานาโฮชิ นานะ / 七星ナナ, MOLLY, Lunatrix Ch. |
| `comm_2026_02` | 56 | Pixela Project (18), Independent (17), Algorhythm Project (10) | Pixela Official, Mild-R Ch. Lumina-World-End, UCEvyDOkcGkzCTo62d9BrhkA, Aranis Elvene Ch. Pixela-Isekai |
| `comm_2026_03` | 39 | Independent (19), Algorhythm Project (18), Pixela Project (2) | Magnum Ch.【ARP】, Ivy Ch.【ARP】, Baabel Ch.【ARP】, Dacapo Ch.【ARP】 |
| `comm_2026_04` | 8 | Independent (8) | UC_ARP005_DACAPO, UC_ARP003_MAYLYN, UC_ARP002_BAABEL, UC_POLY001_HOKU |

---

## Community Lineage Transitions (Adjacent Years)

| Year Transition | Category | Event Type | Source Community | Target Community | Shared Nodes | Jaccard | Forward % | Backward % | Details |
|:---:|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---|
| 2020 -> 2021 | `relation` | **PERSISTENT** | `comm_2020_02` | `comm_2021_05` | 4 | 0.33 | 57.1% | 44.4% | Persistent backbone: comm_2020_02 -> comm_2021_05 (J=0.33, shared=4) |
| 2020 -> 2021 | `lifecycle` | **BIRTH** | `NEW` | `comm_2021_03` | 0 | 0.00 | 0.0% | 0.0% | New community birth in 2021 (12 nodes), zero significant predecessor relations (max overlap=0.0%) |
| 2020 -> 2021 | `lifecycle` | **BIRTH** | `NEW` | `comm_2021_04` | 0 | 0.00 | 0.0% | 0.0% | New community birth in 2021 (10 nodes), zero significant predecessor relations (max overlap=0.0%) |
| 2021 -> 2022 | `relation` | **SPLIT_BRANCH** | `comm_2021_01` | `comm_2022_01` | 7 | 0.17 | 35.0% | 24.1% | Split branch: comm_2021_01 -> comm_2022_01 (7 nodes, 35.0% of source) |
| 2021 -> 2022 | `relation` | **SPLIT_BRANCH** | `comm_2021_01` | `comm_2022_02` | 7 | 0.18 | 35.0% | 28.0% | Split branch: comm_2021_01 -> comm_2022_02 (7 nodes, 35.0% of source) |
| 2021 -> 2022 | `relation` | **SPLIT_BRANCH** | `comm_2021_01` | `comm_2022_04` | 4 | 0.12 | 20.0% | 25.0% | Split branch: comm_2021_01 -> comm_2022_04 (4 nodes, 20.0% of source) |
| 2021 -> 2022 | `relation` | **SPLIT_BRANCH** | `comm_2021_02` | `comm_2022_01` | 3 | 0.07 | 21.4% | 10.3% | Split branch: comm_2021_02 -> comm_2022_01 (3 nodes, 21.4% of source) |
| 2021 -> 2022 | `relation` | **SPLIT_BRANCH** | `comm_2021_02` | `comm_2022_02` | 9 | 0.30 | 64.3% | 36.0% | Split branch: comm_2021_02 -> comm_2022_02 (9 nodes, 64.3% of source) |
| 2021 -> 2022 | `relation` | **SPLIT_BRANCH** | `comm_2021_03` | `comm_2022_03` | 6 | 0.21 | 50.0% | 27.3% | Split branch: comm_2021_03 -> comm_2022_03 (6 nodes, 50.0% of source) |
| 2021 -> 2022 | `relation` | **SPLIT_BRANCH** | `comm_2021_03` | `comm_2022_04` | 4 | 0.17 | 33.3% | 25.0% | Split branch: comm_2021_03 -> comm_2022_04 (4 nodes, 33.3% of source) |
| 2021 -> 2022 | `relation` | **SPLIT_BRANCH** | `comm_2021_05` | `comm_2022_02` | 3 | 0.10 | 33.3% | 12.0% | Split branch: comm_2021_05 -> comm_2022_02 (3 nodes, 33.3% of source) |
| 2021 -> 2022 | `relation` | **SPLIT_BRANCH** | `comm_2021_05` | `comm_2022_04` | 4 | 0.19 | 44.4% | 25.0% | Split branch: comm_2021_05 -> comm_2022_04 (4 nodes, 44.4% of source) |
| 2021 -> 2022 | `relation` | **MERGE_TRIBUTARY** | `comm_2021_01` | `comm_2022_01` | 7 | 0.17 | 35.0% | 24.1% | Merge tributary: comm_2021_01 -> comm_2022_01 (7 nodes, 24.1% of target) |
| 2021 -> 2022 | `relation` | **MERGE_TRIBUTARY** | `comm_2021_04` | `comm_2022_01` | 7 | 0.22 | 70.0% | 24.1% | Merge tributary: comm_2021_04 -> comm_2022_01 (7 nodes, 24.1% of target) |
| 2021 -> 2022 | `relation` | **MERGE_TRIBUTARY** | `comm_2021_01` | `comm_2022_02` | 7 | 0.18 | 35.0% | 28.0% | Merge tributary: comm_2021_01 -> comm_2022_02 (7 nodes, 28.0% of target) |
| 2021 -> 2022 | `relation` | **MERGE_TRIBUTARY** | `comm_2021_02` | `comm_2022_02` | 9 | 0.30 | 64.3% | 36.0% | Merge tributary: comm_2021_02 -> comm_2022_02 (9 nodes, 36.0% of target) |
| 2021 -> 2022 | `relation` | **MERGE_TRIBUTARY** | `comm_2021_01` | `comm_2022_04` | 4 | 0.12 | 20.0% | 25.0% | Merge tributary: comm_2021_01 -> comm_2022_04 (4 nodes, 25.0% of target) |
| 2021 -> 2022 | `relation` | **MERGE_TRIBUTARY** | `comm_2021_03` | `comm_2022_04` | 4 | 0.17 | 33.3% | 25.0% | Merge tributary: comm_2021_03 -> comm_2022_04 (4 nodes, 25.0% of target) |
| 2021 -> 2022 | `relation` | **MERGE_TRIBUTARY** | `comm_2021_05` | `comm_2022_04` | 4 | 0.19 | 44.4% | 25.0% | Merge tributary: comm_2021_05 -> comm_2022_04 (4 nodes, 25.0% of target) |
| 2022 -> 2023 | `relation` | **PERSISTENT** | `comm_2022_03` | `comm_2023_01` | 19 | 0.46 | 86.4% | 50.0% | Persistent backbone: comm_2022_03 -> comm_2023_01 (J=0.46, shared=19) |
| 2022 -> 2023 | `relation` | **SPLIT_BRANCH** | `comm_2022_01` | `comm_2023_02` | 8 | 0.15 | 27.6% | 25.0% | Split branch: comm_2022_01 -> comm_2023_02 (8 nodes, 27.6% of source) |
| 2022 -> 2023 | `relation` | **SPLIT_BRANCH** | `comm_2022_01` | `comm_2023_04` | 11 | 0.26 | 37.9% | 44.0% | Split branch: comm_2022_01 -> comm_2023_04 (11 nodes, 37.9% of source) |
| 2022 -> 2023 | `relation` | **SPLIT_BRANCH** | `comm_2022_02` | `comm_2023_01` | 5 | 0.09 | 20.0% | 13.2% | Split branch: comm_2022_02 -> comm_2023_01 (5 nodes, 20.0% of source) |
| 2022 -> 2023 | `relation` | **SPLIT_BRANCH** | `comm_2022_02` | `comm_2023_03` | 7 | 0.14 | 28.0% | 22.6% | Split branch: comm_2022_02 -> comm_2023_03 (7 nodes, 28.0% of source) |
| 2022 -> 2023 | `relation` | **SPLIT_BRANCH** | `comm_2022_02` | `comm_2023_04` | 5 | 0.11 | 20.0% | 20.0% | Split branch: comm_2022_02 -> comm_2023_04 (5 nodes, 20.0% of source) |
| 2022 -> 2023 | `relation` | **SPLIT_BRANCH** | `comm_2022_04` | `comm_2023_03` | 8 | 0.21 | 50.0% | 25.8% | Split branch: comm_2022_04 -> comm_2023_03 (8 nodes, 50.0% of source) |
| 2022 -> 2023 | `relation` | **SPLIT_BRANCH** | `comm_2022_04` | `comm_2023_04` | 4 | 0.11 | 25.0% | 16.0% | Split branch: comm_2022_04 -> comm_2023_04 (4 nodes, 25.0% of source) |
| 2022 -> 2023 | `relation` | **MERGE_TRIBUTARY** | `comm_2022_02` | `comm_2023_03` | 7 | 0.14 | 28.0% | 22.6% | Merge tributary: comm_2022_02 -> comm_2023_03 (7 nodes, 22.6% of target) |
| 2022 -> 2023 | `relation` | **MERGE_TRIBUTARY** | `comm_2022_04` | `comm_2023_03` | 8 | 0.21 | 50.0% | 25.8% | Merge tributary: comm_2022_04 -> comm_2023_03 (8 nodes, 25.8% of target) |
| 2022 -> 2023 | `relation` | **MERGE_TRIBUTARY** | `comm_2022_01` | `comm_2023_04` | 11 | 0.26 | 37.9% | 44.0% | Merge tributary: comm_2022_01 -> comm_2023_04 (11 nodes, 44.0% of target) |
| 2022 -> 2023 | `relation` | **MERGE_TRIBUTARY** | `comm_2022_02` | `comm_2023_04` | 5 | 0.11 | 20.0% | 20.0% | Merge tributary: comm_2022_02 -> comm_2023_04 (5 nodes, 20.0% of target) |
| 2023 -> 2024 | `relation` | **PERSISTENT** | `comm_2023_01` | `comm_2024_03` | 24 | 0.45 | 63.2% | 61.5% | Persistent backbone: comm_2023_01 -> comm_2024_03 (J=0.45, shared=24) |
| 2023 -> 2024 | `relation` | **PERSISTENT** | `comm_2023_02` | `comm_2024_02` | 22 | 0.44 | 68.8% | 55.0% | Persistent backbone: comm_2023_02 -> comm_2024_02 (J=0.44, shared=22) |
| 2023 -> 2024 | `relation` | **SPLIT_BRANCH** | `comm_2023_01` | `comm_2024_01` | 8 | 0.08 | 21.1% | 11.6% | Split branch: comm_2023_01 -> comm_2024_01 (8 nodes, 21.1% of source) |
| 2023 -> 2024 | `relation` | **SPLIT_BRANCH** | `comm_2023_01` | `comm_2024_03` | 24 | 0.45 | 63.2% | 61.5% | Split branch: comm_2023_01 -> comm_2024_03 (24 nodes, 63.2% of source) |
| 2023 -> 2024 | `relation` | **SPLIT_BRANCH** | `comm_2023_03` | `comm_2024_01` | 19 | 0.23 | 61.3% | 27.5% | Split branch: comm_2023_03 -> comm_2024_01 (19 nodes, 61.3% of source) |
| 2023 -> 2024 | `relation` | **SPLIT_BRANCH** | `comm_2023_03` | `comm_2024_04` | 8 | 0.25 | 25.8% | 88.9% | Split branch: comm_2023_03 -> comm_2024_04 (8 nodes, 25.8% of source) |
| 2023 -> 2024 | `relation` | **MERGE_TRIBUTARY** | `comm_2023_03` | `comm_2024_01` | 19 | 0.23 | 61.3% | 27.5% | Merge tributary: comm_2023_03 -> comm_2024_01 (19 nodes, 27.5% of target) |
| 2023 -> 2024 | `relation` | **MERGE_TRIBUTARY** | `comm_2023_04` | `comm_2024_01` | 20 | 0.27 | 80.0% | 29.0% | Merge tributary: comm_2023_04 -> comm_2024_01 (20 nodes, 29.0% of target) |
| 2024 -> 2025 | `relation` | **PERSISTENT** | `comm_2024_01` | `comm_2025_02` | 34 | 0.39 | 49.3% | 65.4% | Persistent backbone: comm_2024_01 -> comm_2025_02 (J=0.39, shared=34) |
| 2024 -> 2025 | `relation` | **PERSISTENT** | `comm_2024_02` | `comm_2025_03` | 28 | 0.56 | 70.0% | 73.7% | Persistent backbone: comm_2024_02 -> comm_2025_03 (J=0.56, shared=28) |
| 2024 -> 2025 | `relation` | **PERSISTENT** | `comm_2024_03` | `comm_2025_01` | 35 | 0.60 | 89.7% | 64.8% | Persistent backbone: comm_2024_03 -> comm_2025_01 (J=0.60, shared=35) |
| 2024 -> 2025 | `relation` | **SPLIT_BRANCH** | `comm_2024_01` | `comm_2025_02` | 34 | 0.39 | 49.3% | 65.4% | Split branch: comm_2024_01 -> comm_2025_02 (34 nodes, 49.3% of source) |
| 2024 -> 2025 | `relation` | **SPLIT_BRANCH** | `comm_2024_01` | `comm_2025_04` | 14 | 0.18 | 20.3% | 63.6% | Split branch: comm_2024_01 -> comm_2025_04 (14 nodes, 20.3% of source) |
| 2024 -> 2025 | `relation` | **SPLIT_BRANCH** | `comm_2024_04` | `comm_2025_02` | 2 | 0.03 | 22.2% | 3.8% | Split branch: comm_2024_04 -> comm_2025_02 (2 nodes, 22.2% of source) |
| 2024 -> 2025 | `relation` | **SPLIT_BRANCH** | `comm_2024_04` | `comm_2025_03` | 3 | 0.07 | 33.3% | 7.9% | Split branch: comm_2024_04 -> comm_2025_03 (3 nodes, 33.3% of source) |
| 2024 -> 2025 | `relation` | **SPLIT_BRANCH** | `comm_2024_04` | `comm_2025_04` | 3 | 0.11 | 33.3% | 13.6% | Split branch: comm_2024_04 -> comm_2025_04 (3 nodes, 33.3% of source) |
| 2025 -> 2026 | `relation` | **PERSISTENT** | `comm_2025_01` | `comm_2026_02` | 40 | 0.57 | 74.1% | 71.4% | Persistent backbone: comm_2025_01 -> comm_2026_02 (J=0.57, shared=40) |
| 2025 -> 2026 | `relation` | **PERSISTENT** | `comm_2025_02` | `comm_2026_01` | 40 | 0.58 | 76.9% | 70.2% | Persistent backbone: comm_2025_02 -> comm_2026_01 (J=0.58, shared=40) |
| 2025 -> 2026 | `relation` | **PERSISTENT** | `comm_2025_03` | `comm_2026_03` | 24 | 0.45 | 63.2% | 61.5% | Persistent backbone: comm_2025_03 -> comm_2026_03 (J=0.45, shared=24) |
| 2025 -> 2026 | `relation` | **SPLIT_BRANCH** | `comm_2025_04` | `comm_2026_01` | 9 | 0.13 | 40.9% | 15.8% | Split branch: comm_2025_04 -> comm_2026_01 (9 nodes, 40.9% of source) |
| 2025 -> 2026 | `relation` | **SPLIT_BRANCH** | `comm_2025_04` | `comm_2026_03` | 6 | 0.11 | 27.3% | 15.4% | Split branch: comm_2025_04 -> comm_2026_03 (6 nodes, 27.3% of source) |
| 2025 -> 2026 | `lifecycle` | **BIRTH** | `NEW` | `comm_2026_04` | 0 | 0.00 | 0.0% | 0.0% | New community birth in 2026 (8 nodes), zero significant predecessor relations (max overlap=0.0%) |

---

## Research Insights & Modularity Interpretation

> [!NOTE]
> **Bounded Modularity Interpretation:**
> Modularity varies across years under the same Louvain configuration. Higher values indicate stronger separation in the observed yearly network, but cross-year comparisons may be affected by network size, density, coverage, and 2026 YTD sampling.

1. **Early Network Formation (2020–2021):**
   - 2020 represents the initial cohort of early VTubers (21 active nodes, 72 edges, Q=0.1968, flag: `LOW_CHANNEL_COVERAGE / LOW_EDGE_COUNT`).
   - By 2021, the network expanded to 65 active channels (625 edges, Q=0.1333). This influx created new community births (`comm_2021_01`, `comm_2021_02`, `comm_2021_03`), reflecting independent and pioneering group formations.

2. **Cohort Differentiation & Agency Clustering (2022–2025):**
   - Between 2022 (92 channels, Q=0.2007) and 2025 (166 channels, Q=0.3189), modularity reflected higher partition structure as agency rosters (Algorhythm Project, Pixela Project, Lumina Live) formed distinct core audiences while maintaining collaborative bridges.
   - Lineage events during this period exhibited split branches and merge tributaries as cohorts expanded, crossed over, and regrouped.

3. **Mature Network & 2026 YTD Sampling:**
   - In 2026 YTD, modularity measured 0.5085 across 160 active channels (1,997 edges). Persistent backbones remained stable across core agency clusters.
   - Higher modularity in 2026 YTD reflects denser intra-community interactions in the available sample; cross-year comparisons should consider that 2026 is an in-progress sampling window.
