# Phase T13: Dynamic Bridges & Centrality Evolution Report

## Executive Summary
This report tracks the longitudinal evolution of creator structural network roles across the Thai VTuber interaction ecosystem from 2020 through 2026. Across **790 channel-year evaluations**, channel centrality is measured via normalized percentile bands to avoid overinterpreting threshold-sensitive ordinal ranks.

### Scientific Framing & Guardrails
1. **Edge Distance vs Strength Semantics:** Betweenness centrality models shortest paths where edge weight represents traversal distance (`distance = 1.0 / strength`, where `strength = shared_any`). Higher co-audience strength creates shorter graph distance. Degree, PageRank, and eigenvector centrality utilize edge strength directly.
2. **Deterministic Tie-Aware Percentiles:** Percentiles are computed using average rank (`Series.rank(method='average', pct=True)`), ensuring identical centrality values receive strictly equal percentiles invariant to node insertion order.
3. **Structural Position, Not Causal Influence:** Betweenness centrality and bridge metrics quantify topological position on shortest paths between creator communities. They must never be interpreted as personal 'influence' or causal authority.
4. **Percentile Bands over Raw Ranks:** In alignment with Phase T10 findings demonstrating rank volatility under edge pruning, channels are classified into standardized percentile bands (`TOP_1_PERCENT`, `TOP_5_PERCENT`, `TOP_10_PERCENT`, `TOP_QUARTILE`).
5. **Threshold Sensitivity & Robustness:** Bridge stability is tested against edge weight thresholds (>= 1, >= 3, >= 5 shared viewers) to distinguish multi-viewer structural bridges from single-viewer peripheral ties.

---

## 1. Classification of Creator Structural Roles

- **STABLE_BRIDGE Creators (Threshold Robust):** 2
- **STABLE_BRIDGE_CANONICAL_ONLY (Threshold >= 1 Only):** 2
- **EMERGING_BRIDGE Creators (Ascending 2024–2026):** 10
- **DECLINING_BRIDGE Creators:** 6
- **VOLATILE Structural Positions:** 54

### 1.1 Stable Bridge Creators (Sustained Cross-Community Integration)
| Channel Name | Agency | Years Observed | Yrs in Top Decile | Mean Btw Pct | Max Btw Pct | Cross-Comm Share | Cross-Agency Share | Th=5 Retention |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pixela Official** | Pixela Project | 6 | 5 | 94.2% | 100.0% | 57.2% | 81.0% | 80.0% |
| **Beariss Beam** | Independent | 7 | 5 | 90.1% | 98.5% | 62.4% | 35.5% | 60.0% |
| **Aisha Channel (Th>=1 only)** | Independent | 6 | 4 | 87.6% | 97.5% | 60.0% | 48.5% | 25.0% |
| **Reilim Channel (Th>=1 only)** | Independent | 7 | 3 | 80.9% | 94.4% | 54.9% | 43.4% | 0.0% |

### 1.2 Emerging Bridge Creators (Recent Ascents 2024–2026)
| Channel Name | Agency | First Top Decile | Mean Btw Pct | Max Btw Pct | Cross-Comm Share | Cross-Agency Share |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Uniinu ch. Euphora** | Euphora Project | 2025 | 89.3% | 98.1% | 63.1% | 98.8% |
| **Nongwan TV** | Independent | 2024 | 88.7% | 100.0% | 47.1% | 37.2% |
| **HØRI 07 ⌜VZ⌟** | Virtual Zeven (VZ) | 2024 | 76.4% | 94.3% | 54.9% | 97.0% |
| **Magnum Ch.【ARP】** | Algorhythm Project | 2026 | 67.6% | 96.9% | 50.0% | 54.2% |
| **MOLLY** | Independent | 2024 | 67.4% | 100.0% | 55.5% | 41.9% |
| **Lunatrix Ch.** | Independent | 2025 | 66.8% | 95.6% | 57.1% | 44.0% |
| **นานาโฮชิ นานะ / 七星ナナ** | Independent | 2026 | 65.9% | 99.4% | 56.8% | 50.3% |
| **Nergal Near Ch.** | Independent | 2026 | 60.3% | 91.9% | 26.5% | 19.0% |
| **Ivy Ch.【ARP】** | Algorhythm Project | 2026 | 56.0% | 96.2% | 52.2% | 65.1% |
| **Mosant Ch.** | Independent | 2026 | 50.0% | 91.2% | 46.4% | 48.2% |

### 1.3 Declining Bridge Creators
| Channel Name | Agency | Years in Top Decile | Mean Btw Pct | Max Btw Pct | Rule Reason |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Dacapo Ch.【ARP】** | Algorhythm Project | 3 | 90.3% | 99.4% | Previously reached top decile in 3 years (>= 2), but declined below top quartile (< 0.75) or inactive in 2026 |
| **Gibpuri Ch** | Independent | 4 | 88.6% | 98.9% | Previously reached top decile in 4 years (>= 2), but declined below top quartile (< 0.75) or inactive in 2026 |
| **Ardalita Lilibelle Ch. Lumina-First-Myth** | Lumina Live | 3 | 86.4% | 92.2% | Previously reached top decile in 3 years (>= 2), but declined below top quartile (< 0.75) or inactive in 2026 |
| **Pyork The Pork** | Independent | 3 | 81.6% | 100.0% | Previously reached top decile in 3 years (>= 2), but declined below top quartile (< 0.75) or inactive in 2026 |
| **Evalia Ch.【ARP】** | Algorhythm Project | 3 | 80.9% | 98.7% | Previously reached top decile in 3 years (>= 2), but declined below top quartile (< 0.75) or inactive in 2026 |
| **久檻夜くぅ / Qualia Qu Ch.** | Independent | 2 | 66.4% | 95.2% | Previously reached top decile in 2 years (>= 2), but declined below top quartile (< 0.75) or inactive in 2026 |

---

## 2. Centrality Change-Point Candidates (Rapid Reconfigurations)

Detected **214 major structural change-points** (|delta| >= 25 percentile points between adjacent years):
- **Rapid Ascents:** 106
- **Rapid Declines:** 108

| Channel Name | Year Transition | Change Type | From Pct | To Pct | Delta | From Band | To Band |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| Darin V | 2020 -> 2021 | `RAPID_DECLINE` | 100.0% | 58.5% | -41.5% | `TOP_1_PERCENT` | `BELOW_QUARTILE` |
| Terios Ch. | 2020 -> 2021 | `RAPID_ASCENT` | 33.3% | 63.8% | +30.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Sora A.C.G. | 2020 -> 2021 | `RAPID_DECLINE` | 66.7% | 29.2% | -37.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Aoi Crescent Ch. | 2020 -> 2021 | `RAPID_ASCENT` | 33.3% | 77.7% | +44.4% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Aoi Crescent Ch. | 2021 -> 2022 | `RAPID_DECLINE` | 77.7% | 34.2% | -43.5% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| JayVounter | 2021 -> 2022 | `RAPID_ASCENT` | 29.2% | 71.7% | +42.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Supeacha ⌜VZ⌟ | 2021 -> 2022 | `RAPID_ASCENT` | 29.2% | 71.7% | +42.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Nerumi-s | 2021 -> 2022 | `RAPID_DECLINE` | 86.2% | 34.2% | -51.9% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Laguna JuJu Ch. Pixela Project | 2021 -> 2022 | `RAPID_DECLINE` | 75.4% | 34.2% | -41.1% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| dtto. | 2021 -> 2022 | `RAPID_ASCENT` | 29.2% | 92.4% | +63.2% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Zekai Ch.【ARP】 | 2021 -> 2022 | `RAPID_DECLINE` | 67.7% | 34.2% | -33.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Lunatrix Ch. | 2021 -> 2022 | `RAPID_DECLINE` | 60.0% | 34.2% | -25.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Laibaht Ch. / หลายบาท | 2021 -> 2022 | `RAPID_DECLINE` | 83.1% | 34.2% | -48.8% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Princess Zelina Ch. Pixela Project | 2021 -> 2022 | `RAPID_DECLINE` | 80.0% | 34.2% | -45.8% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| HØRI 07 ⌜VZ⌟ | 2021 -> 2022 | `RAPID_DECLINE` | 72.3% | 34.2% | -38.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Pengu Ch.【Ti19t】 | 2021 -> 2022 | `RAPID_DECLINE` | 73.9% | 34.2% | -39.6% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Asteroth Ch.【ARP】 | 2021 -> 2022 | `RAPID_DECLINE` | 87.7% | 34.2% | -53.4% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Hey Solly | 2021 -> 2022 | `RAPID_DECLINE` | 70.8% | 34.2% | -36.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Evalia Ch.【ARP】 | 2021 -> 2022 | `RAPID_ASCENT` | 63.8% | 94.6% | +30.7% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Kyomu Ch. | 2021 -> 2022 | `RAPID_ASCENT` | 29.2% | 71.7% | +42.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Tatsuki Ch. | 2021 -> 2022 | `RAPID_ASCENT` | 29.2% | 78.3% | +49.0% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Bloodyflora | 2021 -> 2022 | `RAPID_ASCENT` | 29.2% | 73.9% | +44.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| MONARICA | 2021 -> 2022 | `RAPID_ASCENT` | 29.2% | 87.0% | +57.7% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| CooGa | 2021 -> 2022 | `RAPID_DECLINE` | 63.8% | 34.2% | -29.6% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Toru Kumaトルくま | 2021 -> 2022 | `RAPID_ASCENT` | 29.2% | 83.7% | +54.5% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Supeacha ⌜VZ⌟ | 2022 -> 2023 | `RAPID_DECLINE` | 71.7% | 29.1% | -42.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Terios Ch. | 2022 -> 2023 | `RAPID_DECLINE` | 77.2% | 29.1% | -48.1% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| HØRI 07 ⌜VZ⌟ | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 80.6% | +46.4% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Laibaht Ch. / หลายบาท | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 66.7% | +32.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Asteroth Ch.【ARP】 | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 64.3% | +30.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Princess Zelina Ch. Pixela Project | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 59.3% | +25.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Melita X Ch. Pixela Project | 2022 -> 2023 | `RAPID_DECLINE` | 85.9% | 29.1% | -56.8% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Umino Ciala Ch. Pixela Legends | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 59.3% | +25.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Jolly Estaa Ch. Pixela-Isekai | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 82.2% | +47.9% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| S1R Ch.【ARP】 | 2022 -> 2023 | `RAPID_DECLINE` | 68.5% | 29.1% | -39.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Mosant Ch. | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 64.3% | +30.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| MONARICA | 2022 -> 2023 | `RAPID_DECLINE` | 87.0% | 29.1% | -57.9% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| SAYU Ch. 小百合さゆ | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 69.0% | +34.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Toru Kumaトルくま | 2022 -> 2023 | `RAPID_DECLINE` | 83.7% | 29.1% | -54.6% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Mycara Melony Ch. Pixela-Mystic | 2022 -> 2023 | `RAPID_DECLINE` | 93.5% | 61.2% | -32.2% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| นานาโฮชิ นานะ / 七星ナナ | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 74.4% | +40.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Bloodyflora | 2022 -> 2023 | `RAPID_DECLINE` | 73.9% | 29.1% | -44.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| JayVounter | 2022 -> 2023 | `RAPID_DECLINE` | 71.7% | 29.1% | -42.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| dtto. | 2022 -> 2023 | `RAPID_DECLINE` | 92.4% | 29.1% | -63.3% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| Liz's | WISLIVE | 2022 -> 2023 | `RAPID_DECLINE` | 90.2% | 29.1% | -61.2% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| Eileennoir Ch. | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 99.2% | +65.0% | `BELOW_QUARTILE` | `TOP_1_PERCENT` |
| Baku Ch.【ARP】 | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 64.3% | +30.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Aito LH | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 84.5% | +50.3% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Nerumi-s | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 79.1% | +44.8% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Luxia Ch. | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 77.5% | +43.3% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Azato Stacia Ch. | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 90.7% | +56.5% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Kamiyu Reirin Ch. Lumina-First-Myth | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 83.0% | +48.7% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| MOLLY | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 72.9% | +38.6% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Akemi Arlin Ch. Pixela Legends | 2022 -> 2023 | `RAPID_ASCENT` | 34.2% | 76.0% | +41.7% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Listen Ch.【ARP】 | 2022 -> 2023 | `RAPID_DECLINE` | 69.6% | 29.1% | -40.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Lunatrix Ch. | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 87.3% | +58.2% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Terios Ch. | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 86.0% | +56.9% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Nerumi-s | 2023 -> 2024 | `RAPID_DECLINE` | 79.1% | 29.0% | -50.1% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Hey Solly | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 93.6% | +64.6% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Asteroth Ch.【ARP】 | 2023 -> 2024 | `RAPID_DECLINE` | 64.3% | 29.0% | -35.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Zekai Ch.【ARP】 | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 59.6% | +30.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Aoi Crescent Ch. | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 83.8% | +54.7% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Princess Zelina Ch. Pixela Project | 2023 -> 2024 | `RAPID_DECLINE` | 59.3% | 29.0% | -30.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| TeenWISU | 2023 -> 2024 | `RAPID_DECLINE` | 86.8% | 29.0% | -57.8% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Superpretty TAKOPERO Ch. Pixela Legends | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 66.2% | +37.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Umino Ciala Ch. Pixela Legends | 2023 -> 2024 | `RAPID_DECLINE` | 59.3% | 29.0% | -30.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Mosant Ch. | 2023 -> 2024 | `RAPID_DECLINE` | 64.3% | 29.0% | -35.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Baku Ch.【ARP】 | 2023 -> 2024 | `RAPID_DECLINE` | 64.3% | 29.0% | -35.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Kyomu Ch. | 2023 -> 2024 | `RAPID_DECLINE` | 72.1% | 29.0% | -43.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| LIVIANA Ch. | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 91.7% | +62.6% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Ayna Ch.【ARP】 | 2023 -> 2024 | `RAPID_DECLINE` | 89.9% | 29.0% | -60.9% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Liz's | WISLIVE | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 61.8% | +32.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| SAYU Ch. 小百合さゆ | 2023 -> 2024 | `RAPID_DECLINE` | 69.0% | 29.0% | -40.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Solar Ch.【ARP】 | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 98.1% | +69.0% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| MONARICA | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 69.4% | +40.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Draki Kona Ch. Lumina-First-Myth | 2023 -> 2024 | `RAPID_DECLINE` | 58.1% | 29.0% | -29.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Grimus Grimm Ch. Pixela Destiny | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 61.8% | +32.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| SwordAce | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 92.4% | +63.3% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Nergal Near Ch. | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 89.2% | +60.1% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Ivy Ch.【ARP】 | 2023 -> 2024 | `RAPID_DECLINE` | 67.8% | 29.0% | -38.9% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Unnämed | 2023 -> 2024 | `RAPID_DECLINE` | 73.6% | 29.0% | -44.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| moujob | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 88.5% | +59.5% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Aruna Shuun Ch. Pixela Destiny | 2023 -> 2024 | `RAPID_DECLINE` | 85.3% | 29.0% | -56.3% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Euthalia Zéphyr Ch. Pixela Destiny | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 75.8% | +46.7% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Poru Ch.【ARP】 | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 61.8% | +32.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Karu Ch.【ARP】 | 2023 -> 2024 | `RAPID_DECLINE` | 83.7% | 29.0% | -54.7% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| MOLLY | 2023 -> 2024 | `RAPID_ASCENT` | 72.9% | 100.0% | +27.1% | `BELOW_QUARTILE` | `TOP_1_PERCENT` |
| Azato Stacia Ch. | 2023 -> 2024 | `RAPID_DECLINE` | 90.7% | 29.0% | -61.7% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| Luxia Ch. | 2023 -> 2024 | `RAPID_DECLINE` | 77.5% | 29.0% | -48.5% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Akemi Arlin Ch. Pixela Legends | 2023 -> 2024 | `RAPID_DECLINE` | 76.0% | 29.0% | -47.0% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Jiru ch. Euphora | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 64.3% | +35.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Lapine Ch. | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 73.2% | +44.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| JayVounter | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 83.8% | +54.7% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| dtto. | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 66.9% | +37.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Hinabe HongFei Ch. Pixela Project | 2023 -> 2024 | `RAPID_DECLINE` | 89.1% | 29.0% | -60.2% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| 久檻夜くぅ / Qualia Qu Ch. | 2023 -> 2024 | `RAPID_DECLINE` | 64.3% | 29.0% | -35.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Roselia de Magentia Ch. Pixela S | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 58.3% | +29.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| JueBigHead | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 83.8% | +54.7% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Ark Ch.【ARP】 | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 74.2% | +45.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Fiatake | 2023 -> 2024 | `RAPID_DECLINE` | 79.1% | 29.0% | -50.1% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Magnum Ch.【ARP】 | 2023 -> 2024 | `RAPID_ASCENT` | 29.1% | 79.0% | +49.9% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| it’s hi Ch.【ARP】 | 2023 -> 2024 | `RAPID_DECLINE` | 79.1% | 29.0% | -50.1% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Meraki Keimii Ch. Pixela Legends | 2024 -> 2025 | `RAPID_DECLINE` | 81.5% | 31.0% | -50.5% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Poru Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 61.8% | 89.8% | +28.0% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Ayna Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 97.6% | +68.6% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Poppy the Puppy | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 70.5% | +41.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Kitsuneko Mewten Ch. Pixela-Isekai | 2024 -> 2025 | `RAPID_DECLINE` | 58.3% | 31.0% | -27.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Selene Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 75.9% | +46.9% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Umino Ciala Ch. Pixela Legends | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 68.7% | +39.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Aranis Elvene Ch. Pixela-Isekai | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 75.3% | +46.3% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Jiru ch. Euphora | 2024 -> 2025 | `RAPID_DECLINE` | 64.3% | 31.0% | -33.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Eileennoir Ch. | 2024 -> 2025 | `RAPID_DECLINE` | 87.9% | 31.0% | -56.9% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Aoi Crescent Ch. | 2024 -> 2025 | `RAPID_DECLINE` | 83.8% | 31.0% | -52.7% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Supeacha ⌜VZ⌟ | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 95.2% | +66.2% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Terios Ch. | 2024 -> 2025 | `RAPID_DECLINE` | 86.0% | 31.0% | -55.0% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Princess Zelina Ch. Pixela Project | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 99.4% | +70.4% | `BELOW_QUARTILE` | `TOP_1_PERCENT` |
| ChaoPlaThong | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 78.9% | +49.9% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Beariss Beam | 2024 -> 2025 | `RAPID_DECLINE` | 96.8% | 71.1% | -25.7% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| Superpretty TAKOPERO Ch. Pixela Legends | 2024 -> 2025 | `RAPID_DECLINE` | 66.2% | 31.0% | -35.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Liz's | WISLIVE | 2024 -> 2025 | `RAPID_DECLINE` | 61.8% | 31.0% | -30.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Solar Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 98.1% | 31.0% | -67.1% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| TeenWISU | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 86.1% | +57.2% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| SiamNeko Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 76.4% | 31.0% | -45.4% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Laibaht Ch. / หลายบาท | 2024 -> 2025 | `RAPID_DECLINE` | 68.8% | 31.0% | -37.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Hey Solly | 2024 -> 2025 | `RAPID_DECLINE` | 93.6% | 31.0% | -62.6% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| Zekai Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 59.6% | 93.4% | +33.8% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| ITsMeYao | 2024 -> 2025 | `RAPID_DECLINE` | 67.5% | 31.0% | -36.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Evalia Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 98.7% | 71.7% | -27.0% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| JueBigHead | 2024 -> 2025 | `RAPID_DECLINE` | 83.8% | 31.0% | -52.7% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Friskfitz | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 89.2% | +60.2% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Choya Ch. | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 87.9% | +59.0% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Faminé Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 59.6% | 31.0% | -28.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Nergal Near Ch. | 2024 -> 2025 | `RAPID_DECLINE` | 89.2% | 31.0% | -58.1% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Grimus Grimm Ch. Pixela Destiny | 2024 -> 2025 | `RAPID_DECLINE` | 61.8% | 31.0% | -30.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Hanami Lay CH. | 2024 -> 2025 | `RAPID_DECLINE` | 80.9% | 31.0% | -49.9% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Effy Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 79.6% | 31.0% | -48.6% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| deksammy | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 67.2% | +38.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| TEENIE | WISLIVE | 2024 -> 2025 | `RAPID_DECLINE` | 72.0% | 31.0% | -40.9% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| SwordAce | 2024 -> 2025 | `RAPID_DECLINE` | 92.4% | 31.0% | -61.3% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| Cerafine Mikael Ch. Lumina-First-Myth | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 69.9% | +40.9% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Beta AMI Ch. Lumina-World-End | 2024 -> 2025 | `RAPID_DECLINE` | 70.1% | 31.0% | -39.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| T-Reina Ashyra Ch. Lumina-World-End | 2024 -> 2025 | `RAPID_DECLINE` | 94.9% | 31.0% | -63.9% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| NEBUEL | VTUBER | 2024 -> 2025 | `RAPID_DECLINE` | 83.8% | 31.0% | -52.7% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Ginnique Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 83.8% | 31.0% | -52.7% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Quentin Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 83.1% | +54.1% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Fumi Hausu | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 64.5% | +35.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Mild-R Ch. Lumina-World-End | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 63.5% | +34.6% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| TakumaRei「บ่นไปเรื่อย」 | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 96.4% | +67.4% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Sisira Hydrangea Ch. Pixela S | 2024 -> 2025 | `RAPID_DECLINE` | 71.3% | 31.0% | -40.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| 【graduated】Ice Shirakoi Ch. / AStars Amakara | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 79.5% | +50.5% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| moujob | 2024 -> 2025 | `RAPID_DECLINE` | 88.5% | 31.0% | -57.5% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Schneider Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 74.2% | 31.0% | -43.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Luxia Ch. | 2024 -> 2025 | `RAPID_ASCENT` | 29.0% | 62.4% | +33.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| MOLLY | 2024 -> 2025 | `RAPID_DECLINE` | 100.0% | 31.0% | -69.0% | `TOP_1_PERCENT` | `BELOW_QUARTILE` |
| Atlanteia Sireen Ch. Lumina-First-Myth | 2024 -> 2025 | `RAPID_DECLINE` | 68.2% | 31.0% | -37.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Zekai Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 93.4% | 61.3% | -32.1% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| SEO A XAY | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 76.2% | +45.2% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| JayVounter | 2025 -> 2026 | `RAPID_DECLINE` | 81.0% | 26.9% | -54.1% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| TeenWISU | 2025 -> 2026 | `RAPID_DECLINE` | 86.1% | 26.9% | -59.3% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Reilim Channel | 2025 -> 2026 | `RAPID_ASCENT` | 67.2% | 94.4% | +27.2% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Jiru ch. Euphora | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 71.9% | +40.9% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Eileennoir Ch. | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 59.1% | +28.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Lapine Ch. | 2025 -> 2026 | `RAPID_DECLINE` | 62.4% | 26.9% | -35.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| MiYuu43 ch. みゆ | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 68.1% | +37.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Baku Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 56.2% | +25.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Ayna Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 97.6% | 57.8% | -39.8% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| Umino Ciala Ch. Pixela Legends | 2025 -> 2026 | `RAPID_DECLINE` | 68.7% | 26.9% | -41.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Mosant Ch. | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 91.2% | +60.2% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Hanabi Lafy Ch. Pixela-Isekai | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 66.2% | +35.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| LIVIANA Ch. | 2025 -> 2026 | `RAPID_DECLINE` | 72.9% | 26.9% | -46.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Zenith Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 88.1% | +57.1% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| RaFa DXD | 2025 -> 2026 | `RAPID_DECLINE` | 65.4% | 26.9% | -38.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Poppy the Puppy | 2025 -> 2026 | `RAPID_DECLINE` | 70.5% | 26.9% | -43.6% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Solar Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 62.2% | +31.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Toru Kumaトルくま | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 73.8% | +42.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Draki Kona Ch. Lumina-First-Myth | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 71.2% | +40.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Kyomu Ch. | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 80.6% | +49.6% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| MONARICA | 2025 -> 2026 | `RAPID_DECLINE` | 84.3% | 57.8% | -26.5% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Supeacha ⌜VZ⌟ | 2025 -> 2026 | `RAPID_DECLINE` | 95.2% | 53.8% | -41.4% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| ChaoPlaThong | 2025 -> 2026 | `RAPID_DECLINE` | 78.9% | 26.9% | -52.0% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Princess Zelina Ch. Pixela Project | 2025 -> 2026 | `RAPID_DECLINE` | 99.4% | 26.9% | -72.5% | `TOP_1_PERCENT` | `BELOW_QUARTILE` |
| Pyork The Pork | 2025 -> 2026 | `RAPID_DECLINE` | 83.1% | 26.9% | -56.3% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| yoinmori | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 86.9% | +55.9% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Karu Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 83.1% | +52.1% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Euthalia Zéphyr Ch. Pixela Destiny | 2025 -> 2026 | `RAPID_DECLINE` | 78.3% | 26.9% | -51.4% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Atlanteia Sireen Ch. Lumina-First-Myth | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 63.7% | +32.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Schneider Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 90.6% | +59.6% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| TEENIE | WISLIVE | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 80.6% | +49.6% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Luxia Ch. | 2025 -> 2026 | `RAPID_DECLINE` | 62.4% | 26.9% | -35.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| MOLLY | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 98.8% | +67.7% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Azato Stacia Ch. | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 60.3% | +29.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Nezumi Elze Ch. Pixela Legends | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 74.4% | +43.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| JueBigHead | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 56.2% | +25.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Friskfitz | 2025 -> 2026 | `RAPID_DECLINE` | 89.2% | 26.9% | -62.3% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Nergal Near Ch. | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 91.9% | +60.9% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Choya Ch. | 2025 -> 2026 | `RAPID_DECLINE` | 87.9% | 26.9% | -61.1% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Ivy Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 96.2% | +65.2% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| SwordAce | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 82.5% | +51.5% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Faminé Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 76.9% | +45.9% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| ghostmaiky | 2025 -> 2026 | `RAPID_DECLINE` | 91.0% | 65.3% | -25.7% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| Ark Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 77.1% | 26.9% | -50.2% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Magnum Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 65.4% | 96.9% | +31.5% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| NEBUEL | VTUBER | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 80.6% | +49.6% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| T-Reina Ashyra Ch. Lumina-World-End | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 72.5% | +41.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Beta AMI Ch. Lumina-World-End | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 70.0% | +39.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Quentin Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 83.1% | 26.9% | -56.3% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Fumi Hausu | 2025 -> 2026 | `RAPID_DECLINE` | 64.5% | 26.9% | -37.6% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| SICXERZ : CORE Ch. | 2025 -> 2026 | `RAPID_ASCENT` | 31.0% | 59.1% | +28.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| 【graduated】Ice Shirakoi Ch. / AStars Amakara | 2025 -> 2026 | `RAPID_DECLINE` | 79.5% | 26.9% | -52.6% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| MamiMumei | 2025 -> 2026 | `RAPID_DECLINE` | 76.5% | 26.9% | -49.6% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Nirvana Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 97.0% | 26.9% | -70.1% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| DEV Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 80.1% | 26.9% | -53.2% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| พรี่โอม Omoro & คุณนายกระต่าย BunBun | 2025 -> 2026 | `RAPID_DECLINE` | 81.0% | 26.9% | -54.1% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Plathong Ch. | 2025 -> 2026 | `RAPID_DECLINE` | 83.1% | 26.9% | -56.3% | `TOP_QUARTILE` | `BELOW_QUARTILE` |

---

## 3. Threshold Sensitivity Comparison

In accordance with Phase T10 validation, pruning low-weight edges removes peripheral shared-viewer bridges while concentrating centrality among high-density agency channels. Stable bridges with >= 50% retention under threshold >= 5 demonstrate genuine multi-viewer co-interaction bridges, whereas channels with 0% retention represent single-viewer tie bridges susceptible to sampling variation.

---
*Report generated automatically by `scripts/analyze_centrality_evolution.py`.*
