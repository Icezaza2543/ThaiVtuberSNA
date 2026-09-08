# Phase T13: Dynamic Bridges & Centrality Evolution Report

## Executive Summary
This report tracks the longitudinal evolution of creator structural network roles across the Thai VTuber interaction ecosystem from 2020 through 2026. Across **790 channel-year evaluations**, channel centrality is measured via normalized percentile bands to avoid overinterpreting threshold-sensitive ordinal ranks.

### Scientific Framing & Guardrails
1. **Structural Position, Not Causal Influence:** Betweenness centrality and bridge metrics quantify topological position on shortest paths between creator communities. They must never be interpreted as personal 'influence' or causal authority.
2. **Percentile Bands over Raw Ranks:** In alignment with Phase T10 findings demonstrating rank volatility under edge pruning, channels are classified into standardized percentile bands (`TOP_1_PERCENT`, `TOP_5_PERCENT`, `TOP_10_PERCENT`, `TOP_QUARTILE`).
3. **Threshold Sensitivity Testing:** Bridge stability is tested against edge weight thresholds (>= 1, >= 3, >= 5 shared viewers) to quantify peripheral attrition vs structural robustness.

---

## 1. Classification of Creator Structural Roles

- **STABLE_BRIDGE Creators:** 6
- **EMERGING_BRIDGE Creators:** 10
- **DECLINING_BRIDGE Creators:** 23
- **VOLATILE Structural Positions:** 29

### 1.1 Stable Bridge Creators (Sustained Cross-Community Integration)
| Channel Name | Agency | Years Observed | Yrs in Top Decile | Mean Btw Pct | Max Btw Pct | Cross-Comm Share | Cross-Agency Share | Th=5 Retention |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Uniinu ch. Euphora** | Euphora Project | 3 | 3 | 95.0% | 97.0% | 63.1% | 98.8% | 33.3% |
| **Gibpuri Ch** | Independent | 7 | 5 | 90.5% | 100.0% | 69.9% | 38.9% | 75.0% |
| **HØRI 07 ⌜VZ⌟** | Virtual Zeven (VZ) | 6 | 4 | 90.4% | 98.7% | 54.9% | 97.0% | 0.0% |
| **Beariss Beam** | Independent | 7 | 4 | 88.2% | 98.5% | 62.4% | 35.5% | 0.0% |
| **Aito LH** | Independent | 5 | 3 | 87.2% | 99.4% | 43.9% | 30.9% | 0.0% |
| **Lunatrix Ch.** | Independent | 6 | 3 | 65.6% | 93.1% | 57.1% | 44.0% | 33.3% |

### 1.2 Emerging Bridge Creators (Recent Ascents 2024–2026)
| Channel Name | Agency | First Top Decile | Mean Btw Pct | Max Btw Pct | Cross-Comm Share | Cross-Agency Share |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **KAMAI** | Independent | 2024 | 84.7% | 93.6% | 56.3% | 46.2% |
| **ดอยล์** | Independent | 2025 | 83.1% | 97.6% | 50.0% | 51.2% |
| **Nongwan TV** | Independent | 2025 | 83.0% | 99.4% | 47.1% | 37.2% |
| **Solar Ch.【ARP】** | Algorhythm Project | 2026 | 78.6% | 90.6% | 56.2% | 69.1% |
| **Ivy Ch.【ARP】** | Algorhythm Project | 2024 | 78.1% | 97.5% | 52.2% | 65.1% |
| **Aisha Channel** | Independent | 2026 | 75.1% | 100.0% | 60.0% | 48.5% |
| **Magnum Ch.【ARP】** | Algorhythm Project | 2026 | 73.1% | 98.8% | 50.0% | 54.2% |
| **Schneider Ch.【ARP】** | Algorhythm Project | 2026 | 67.4% | 95.6% | 32.6% | 47.7% |
| **Zenith Ch.【ARP】** | Algorhythm Project | 2026 | 51.2% | 96.2% | 39.8% | 51.1% |
| **Nergal Near Ch.** | Independent | 2026 | 46.0% | 91.2% | 26.5% | 19.0% |

### 1.3 Declining Bridge Creators
| Channel Name | Agency | Years in Top Decile | Mean Btw Pct | Max Btw Pct | Rule Reason |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **โป๊ะโกะ / PoKo ปลวกทูปเบ๋อ** | Independent | 1 | 84.1% | 99.4% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **Ardalita Lilibelle Ch. Lumina-First-Myth** | Lumina Live | 2 | 81.2% | 92.8% | Was in top decile in 2 year(s) but dropped below 75th percentile in 2026 |
| **Pyork The Pork** | Independent | 2 | 77.7% | 96.8% | Was in top decile in 2 year(s) but dropped below 75th percentile in 2026 |
| **MamiMumei** | Independent | 1 | 75.3% | 98.8% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **LIVIANA Ch.** | Independent | 2 | 73.7% | 97.5% | Was in top decile in 2 year(s) but dropped below 75th percentile in 2026 |
| **TeenWISU** | Independent | 1 | 72.1% | 95.7% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **MOLLY** | Independent | 2 | 68.8% | 94.6% | Was in top decile in 2 year(s) but dropped below 75th percentile in 2026 |
| **MONARICA** | Independent | 1 | 68.5% | 94.3% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **Ayna Ch.【ARP】** | Algorhythm Project | 3 | 67.7% | 95.3% | Was in top decile in 3 year(s) but dropped below 75th percentile in 2026 |
| **Eileennoir Ch.** | Independent | 1 | 66.3% | 92.4% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **Meraki Keimii Ch. Pixela Legends** | Pixela Project | 2 | 63.4% | 97.7% | Was in top decile in 2 year(s) but dropped below 75th percentile in 2026 |
| **Supeacha ⌜VZ⌟** | Virtual Zeven (VZ) | 1 | 63.1% | 100.0% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **Terios Ch.** | Independent | 2 | 62.6% | 100.0% | Was in top decile in 2 year(s) but dropped below 75th percentile in 2026 |
| **Princess Zelina Ch. Pixela Project** | Pixela Project | 1 | 61.5% | 94.6% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **Liz's | WISLIVE** | Independent | 1 | 57.4% | 93.5% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **ChaoPlaThong** | Independent | 1 | 52.2% | 95.4% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **Effy Ch.【ARP】** | Algorhythm Project | 1 | 51.4% | 96.2% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **JayVounter** | Independent | 1 | 51.2% | 95.5% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **JueBigHead** | Independent | 1 | 49.6% | 93.0% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **Hinabe HongFei Ch. Pixela Project** | Pixela Project | 2 | 49.3% | 98.9% | Was in top decile in 2 year(s) but dropped below 75th percentile in 2026 |
| **Zekai Ch.【ARP】** | Algorhythm Project | 1 | 47.2% | 96.4% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **Hey Solly** | Independent | 1 | 46.0% | 100.0% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |
| **【graduated】Ice Shirakoi Ch. / AStars Amakara** | AStars Production | 1 | 39.4% | 92.2% | Was in top decile in 1 year(s) but dropped below 75th percentile in 2026 |

---

## 2. Centrality Change-Point Candidates (Rapid Reconfigurations)

Detected **228 major structural change-points** (|delta| >= 25 percentile points between adjacent years):
- **Rapid Ascents:** 110
- **Rapid Declines:** 118

| Channel Name | Year Transition | Change Type | From Pct | To Pct | Delta | From Band | To Band |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| ChaAYM | 2020 -> 2021 | `RAPID_DECLINE` | 66.7% | 13.9% | -52.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| JayVounter | 2020 -> 2021 | `RAPID_ASCENT` | 9.5% | 70.8% | +61.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Aoi Crescent Ch. | 2020 -> 2021 | `RAPID_ASCENT` | 42.9% | 96.9% | +54.1% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| CoolRin CH | 2020 -> 2021 | `RAPID_ASCENT` | 4.8% | 64.6% | +59.9% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| L4zyGone | 2020 -> 2021 | `RAPID_DECLINE` | 61.9% | 24.6% | -37.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Supeacha ⌜VZ⌟ | 2021 -> 2022 | `RAPID_ASCENT` | 29.2% | 82.6% | +53.4% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Aoi Crescent Ch. | 2021 -> 2022 | `RAPID_DECLINE` | 96.9% | 3.3% | -93.7% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| Terios Ch. | 2021 -> 2022 | `RAPID_DECLINE` | 100.0% | 44.6% | -55.4% | `TOP_1_PERCENT` | `BELOW_QUARTILE` |
| Hey Solly | 2021 -> 2022 | `RAPID_ASCENT` | 38.5% | 64.1% | +25.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| RAF4EL | 2021 -> 2022 | `RAPID_DECLINE` | 46.2% | 13.0% | -33.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Hinabe HongFei Ch. Pixela Project | 2021 -> 2022 | `RAPID_ASCENT` | 63.1% | 98.9% | +35.8% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Laguna JuJu Ch. Pixela Project | 2021 -> 2022 | `RAPID_DECLINE` | 67.7% | 38.0% | -29.6% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Pyork The Pork | 2021 -> 2022 | `RAPID_ASCENT` | 33.9% | 89.1% | +55.3% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Aisha Channel | 2021 -> 2022 | `RAPID_DECLINE` | 80.0% | 46.7% | -33.3% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| dtto. | 2021 -> 2022 | `RAPID_ASCENT` | 6.2% | 97.8% | +91.7% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| CoolRin CH | 2021 -> 2022 | `RAPID_DECLINE` | 64.6% | 20.6% | -44.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| ITsMeYao | 2021 -> 2022 | `RAPID_ASCENT` | 44.6% | 73.9% | +29.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Zekai Ch.【ARP】 | 2021 -> 2022 | `RAPID_DECLINE` | 36.9% | 1.1% | -35.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| NutsuruSama | 2021 -> 2022 | `RAPID_ASCENT` | 1.5% | 40.2% | +38.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Khaojao | 2021 -> 2022 | `RAPID_DECLINE` | 78.5% | 17.4% | -61.1% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Poppy the Puppy | 2021 -> 2022 | `RAPID_DECLINE` | 53.8% | 10.9% | -43.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| SAYU Ch. 小百合さゆ | 2021 -> 2022 | `RAPID_ASCENT` | 40.0% | 71.7% | +31.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Toru Kumaトルくま | 2021 -> 2022 | `RAPID_ASCENT` | 21.5% | 76.1% | +54.5% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| LIVIANA Ch. | 2021 -> 2022 | `RAPID_DECLINE` | 90.8% | 35.9% | -54.9% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| TheQuillmon ⌜VZ⌟ | 2021 -> 2022 | `RAPID_DECLINE` | 84.6% | 23.9% | -60.7% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Ponpun. | 2021 -> 2022 | `RAPID_DECLINE` | 60.0% | 18.5% | -41.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Selene Ch.【ARP】 | 2021 -> 2022 | `RAPID_ASCENT` | 50.8% | 83.7% | +32.9% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Tatsuki Ch. | 2021 -> 2022 | `RAPID_DECLINE` | 72.3% | 27.2% | -45.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Kyomu Ch. | 2021 -> 2022 | `RAPID_ASCENT` | 18.5% | 54.4% | +35.9% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Bloodyflora | 2021 -> 2022 | `RAPID_ASCENT` | 20.0% | 52.2% | +32.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| CooGa | 2021 -> 2022 | `RAPID_DECLINE` | 41.5% | 15.2% | -26.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| ChaAYM | 2022 -> 2023 | `RAPID_DECLINE` | 37.0% | 8.5% | -28.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| ITsMeYao | 2022 -> 2023 | `RAPID_DECLINE` | 73.9% | 43.4% | -30.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| NutsuruSama | 2022 -> 2023 | `RAPID_DECLINE` | 40.2% | 12.4% | -27.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Bloodyflora | 2022 -> 2023 | `RAPID_DECLINE` | 52.2% | 17.1% | -35.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Aoi Crescent Ch. | 2022 -> 2023 | `RAPID_ASCENT` | 3.3% | 32.6% | +29.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Zekai Ch.【ARP】 | 2022 -> 2023 | `RAPID_ASCENT` | 1.1% | 39.5% | +38.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| นานาโฮชิ นานะ / 七星ナナ | 2022 -> 2023 | `RAPID_ASCENT` | 34.8% | 92.2% | +57.5% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Selene Ch.【ARP】 | 2022 -> 2023 | `RAPID_DECLINE` | 83.7% | 10.1% | -73.6% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| LIVIANA Ch. | 2022 -> 2023 | `RAPID_ASCENT` | 35.9% | 68.2% | +32.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Jolly Estaa Ch. Pixela-Isekai | 2022 -> 2023 | `RAPID_ASCENT` | 59.8% | 87.6% | +27.8% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Aranis Elvene Ch. Pixela-Isekai | 2022 -> 2023 | `RAPID_DECLINE` | 66.3% | 34.9% | -31.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| S1R Ch.【ARP】 | 2022 -> 2023 | `RAPID_DECLINE` | 84.8% | 23.3% | -61.5% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| MONARICA | 2022 -> 2023 | `RAPID_DECLINE` | 77.2% | 22.5% | -54.7% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Poppy the Puppy | 2022 -> 2023 | `RAPID_ASCENT` | 10.9% | 46.5% | +35.6% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Toru Kumaトルくま | 2022 -> 2023 | `RAPID_DECLINE` | 76.1% | 6.2% | -69.9% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Kitsuneko Mewten Ch. Pixela-Isekai | 2022 -> 2023 | `RAPID_DECLINE` | 88.0% | 41.9% | -46.2% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Puipui Memory | 2022 -> 2023 | `RAPID_ASCENT` | 7.6% | 40.3% | +32.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Nerumi-s | 2022 -> 2023 | `RAPID_ASCENT` | 50.0% | 86.8% | +36.8% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Aosora Popo Ch. | 2022 -> 2023 | `RAPID_ASCENT` | 39.1% | 82.2% | +43.0% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| 久檻夜くぅ / Qualia Qu Ch. | 2022 -> 2023 | `RAPID_DECLINE` | 94.6% | 62.8% | -31.8% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| Darin V | 2022 -> 2023 | `RAPID_DECLINE` | 72.8% | 3.9% | -69.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| dtto. | 2022 -> 2023 | `RAPID_DECLINE` | 97.8% | 50.4% | -47.4% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| Pengu Ch.【Ti19t】 | 2022 -> 2023 | `RAPID_DECLINE` | 79.3% | 24.0% | -55.3% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Melita X Ch. Pixela Project | 2022 -> 2023 | `RAPID_DECLINE` | 87.0% | 30.2% | -56.7% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| MOLLY | 2022 -> 2023 | `RAPID_ASCENT` | 28.3% | 94.6% | +66.3% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Akemi Arlin Ch. Pixela Legends | 2022 -> 2023 | `RAPID_ASCENT` | 14.1% | 77.5% | +63.4% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Uniwii Ch.【ARP】 | 2022 -> 2023 | `RAPID_DECLINE` | 81.5% | 31.8% | -49.7% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Azato Stacia Ch. | 2022 -> 2023 | `RAPID_ASCENT` | 41.3% | 81.4% | +40.1% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| MiYuu43 ch. みゆ | 2022 -> 2023 | `RAPID_DECLINE` | 75.0% | 29.5% | -45.5% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Aito LH | 2022 -> 2023 | `RAPID_ASCENT` | 58.7% | 96.9% | +38.2% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Baku Ch.【ARP】 | 2022 -> 2023 | `RAPID_ASCENT` | 33.7% | 69.8% | +36.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Eileennoir Ch. | 2022 -> 2023 | `RAPID_ASCENT` | 29.3% | 67.4% | +38.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Liz's | WISLIVE | 2022 -> 2023 | `RAPID_DECLINE` | 93.5% | 25.6% | -67.9% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| Kamiyu Reirin Ch. Lumina-First-Myth | 2022 -> 2023 | `RAPID_ASCENT` | 25.0% | 72.1% | +47.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| White Sky Ch. | 2022 -> 2023 | `RAPID_ASCENT` | 21.7% | 65.9% | +44.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| SAYU Ch. 小百合さゆ | 2023 -> 2024 | `RAPID_DECLINE` | 61.2% | 31.2% | -30.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Jolly Estaa Ch. Pixela-Isekai | 2023 -> 2024 | `RAPID_DECLINE` | 87.6% | 40.8% | -46.8% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Poppy the Puppy | 2023 -> 2024 | `RAPID_DECLINE` | 46.5% | 0.6% | -45.9% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| MONARICA | 2023 -> 2024 | `RAPID_ASCENT` | 22.5% | 94.3% | +71.8% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| PeachiView | 2023 -> 2024 | `RAPID_DECLINE` | 47.3% | 11.5% | -35.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Nerumi-s | 2023 -> 2024 | `RAPID_DECLINE` | 86.8% | 33.1% | -53.7% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| SEO A XAY | 2023 -> 2024 | `RAPID_ASCENT` | 11.6% | 50.3% | +38.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Hinabe HongFei Ch. Pixela Project | 2023 -> 2024 | `RAPID_DECLINE` | 98.5% | 10.8% | -87.6% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| CoolRin CH | 2023 -> 2024 | `RAPID_ASCENT` | 17.8% | 45.2% | +27.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| ITsMeYao | 2023 -> 2024 | `RAPID_ASCENT` | 43.4% | 73.9% | +30.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Kyomu Ch. | 2023 -> 2024 | `RAPID_DECLINE` | 57.4% | 28.7% | -28.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Lunatrix Ch. | 2023 -> 2024 | `RAPID_ASCENT` | 31.0% | 93.0% | +62.0% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| xLazyYui | 2023 -> 2024 | `RAPID_DECLINE` | 49.6% | 12.7% | -36.9% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| White Sky Ch. | 2023 -> 2024 | `RAPID_DECLINE` | 65.9% | 24.2% | -41.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Ayna Ch.【ARP】 | 2023 -> 2024 | `RAPID_DECLINE` | 95.3% | 8.9% | -86.4% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| Liz's | WISLIVE | 2023 -> 2024 | `RAPID_ASCENT` | 25.6% | 88.5% | +63.0% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Superpretty TAKOPERO Ch. Pixela Legends | 2023 -> 2024 | `RAPID_ASCENT` | 24.8% | 70.1% | +45.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Jiru ch. Euphora | 2023 -> 2024 | `RAPID_ASCENT` | 20.9% | 68.8% | +47.9% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Akemi Arlin Ch. Pixela Legends | 2023 -> 2024 | `RAPID_DECLINE` | 77.5% | 39.5% | -38.0% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Hanabi Lafy Ch. Pixela-Isekai | 2023 -> 2024 | `RAPID_DECLINE` | 59.7% | 31.9% | -27.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| LIVIANA Ch. | 2023 -> 2024 | `RAPID_ASCENT` | 68.2% | 97.5% | +29.2% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Supeacha ⌜VZ⌟ | 2023 -> 2024 | `RAPID_DECLINE` | 71.3% | 45.9% | -25.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Zekai Ch.【ARP】 | 2023 -> 2024 | `RAPID_ASCENT` | 39.5% | 65.0% | +25.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Hey Solly | 2023 -> 2024 | `RAPID_ASCENT` | 56.6% | 100.0% | +43.4% | `BELOW_QUARTILE` | `TOP_1_PERCENT` |
| TeenWISU | 2023 -> 2024 | `RAPID_DECLINE` | 79.8% | 21.0% | -58.8% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Asteroth Ch.【ARP】 | 2023 -> 2024 | `RAPID_DECLINE` | 84.5% | 46.5% | -38.0% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Aoi Crescent Ch. | 2023 -> 2024 | `RAPID_ASCENT` | 32.6% | 80.2% | +47.7% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| JueBigHead | 2023 -> 2024 | `RAPID_DECLINE` | 93.0% | 22.9% | -70.1% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| Ngerntong-เงินทอง | 2023 -> 2024 | `RAPID_ASCENT` | 9.3% | 76.4% | +67.1% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Roselia de Magentia Ch. Pixela S | 2023 -> 2024 | `RAPID_ASCENT` | 1.6% | 69.4% | +67.9% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| HyougaAlpha Ch.【ARP】 | 2023 -> 2024 | `RAPID_DECLINE` | 34.1% | 5.1% | -29.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Nergal Near Ch. | 2023 -> 2024 | `RAPID_ASCENT` | 0.8% | 77.1% | +76.3% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Amnuai CH | 2023 -> 2024 | `RAPID_ASCENT` | 2.3% | 44.6% | +42.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Magnum Ch.【ARP】 | 2023 -> 2024 | `RAPID_ASCENT` | 37.2% | 86.0% | +48.8% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Baabel Ch.【ARP】 | 2023 -> 2024 | `RAPID_DECLINE` | 75.2% | 43.3% | -31.9% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Euthalia Zéphyr Ch. Pixela Destiny | 2023 -> 2024 | `RAPID_ASCENT` | 36.4% | 87.3% | +50.8% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Ark Ch.【ARP】 | 2023 -> 2024 | `RAPID_ASCENT` | 21.7% | 86.6% | +64.9% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| it’s hi Ch.【ARP】 | 2023 -> 2024 | `RAPID_DECLINE` | 80.6% | 35.7% | -45.0% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Ivy Ch.【ARP】 | 2023 -> 2024 | `RAPID_ASCENT` | 52.7% | 94.9% | +42.2% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| ghostmaiky | 2023 -> 2024 | `RAPID_DECLINE` | 89.9% | 55.4% | -34.5% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| SwordAce | 2023 -> 2024 | `RAPID_ASCENT` | 42.6% | 82.8% | +40.2% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Poru Ch.【ARP】 | 2023 -> 2024 | `RAPID_DECLINE` | 78.3% | 49.0% | -29.2% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Grimus Grimm Ch. Pixela Destiny | 2023 -> 2024 | `RAPID_ASCENT` | 38.0% | 78.3% | +40.4% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Fiatake | 2023 -> 2024 | `RAPID_DECLINE` | 72.9% | 7.6% | -65.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Luxia Ch. | 2023 -> 2024 | `RAPID_DECLINE` | 63.6% | 36.3% | -27.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| 久檻夜くぅ / Qualia Qu Ch. | 2023 -> 2024 | `RAPID_DECLINE` | 62.8% | 24.8% | -38.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Terios Ch. | 2023 -> 2024 | `RAPID_ASCENT` | 45.7% | 79.0% | +33.2% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| JayVounter | 2023 -> 2024 | `RAPID_ASCENT` | 35.7% | 95.5% | +59.9% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Aoi Crescent Ch. | 2024 -> 2025 | `RAPID_DECLINE` | 80.2% | 16.9% | -63.4% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Supeacha ⌜VZ⌟ | 2024 -> 2025 | `RAPID_ASCENT` | 45.9% | 100.0% | +54.1% | `BELOW_QUARTILE` | `TOP_1_PERCENT` |
| ChaoPlaThong | 2024 -> 2025 | `RAPID_ASCENT` | 14.0% | 43.4% | +29.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| CoolRin CH | 2024 -> 2025 | `RAPID_DECLINE` | 45.2% | 3.0% | -42.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Terios Ch. | 2024 -> 2025 | `RAPID_DECLINE` | 79.0% | 31.9% | -47.0% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Zenith Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 26.8% | 62.1% | +35.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| CooGa | 2024 -> 2025 | `RAPID_DECLINE` | 37.6% | 6.0% | -31.6% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| SEO A XAY | 2024 -> 2025 | `RAPID_DECLINE` | 50.3% | 24.7% | -25.6% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Hey Solly | 2024 -> 2025 | `RAPID_DECLINE` | 100.0% | 2.4% | -97.6% | `TOP_1_PERCENT` | `BELOW_QUARTILE` |
| Sora A.C.G. | 2024 -> 2025 | `RAPID_DECLINE` | 49.7% | 9.6% | -40.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| JayVounter | 2024 -> 2025 | `RAPID_DECLINE` | 95.5% | 44.6% | -51.0% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| Darin V | 2024 -> 2025 | `RAPID_ASCENT` | 20.4% | 47.6% | +27.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| ChaAYM | 2024 -> 2025 | `RAPID_ASCENT` | 30.6% | 66.9% | +36.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| S1R Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 3.2% | 74.7% | +71.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Mabelle.a | 2024 -> 2025 | `RAPID_DECLINE` | 68.2% | 36.1% | -32.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| TakumaRei「บ่นไปเรื่อย」 | 2024 -> 2025 | `RAPID_ASCENT` | 34.4% | 98.2% | +63.8% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| TeenWISU | 2024 -> 2025 | `RAPID_ASCENT` | 21.0% | 76.5% | +55.5% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Grimus Grimm Ch. Pixela Destiny | 2024 -> 2025 | `RAPID_DECLINE` | 78.3% | 31.3% | -47.0% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| SwordAce | 2024 -> 2025 | `RAPID_DECLINE` | 82.8% | 41.6% | -41.2% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Karu Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 75.8% | 49.4% | -26.4% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Baabel Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 43.3% | 84.9% | +41.6% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Azato Stacia Ch. | 2024 -> 2025 | `RAPID_DECLINE` | 90.5% | 57.8% | -32.6% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| MiYuu43 ch. みゆ | 2024 -> 2025 | `RAPID_ASCENT` | 47.8% | 85.5% | +37.8% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Baku Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 73.2% | 13.9% | -59.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Poru Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 49.0% | 77.7% | +28.7% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Hanami Lay CH. | 2024 -> 2025 | `RAPID_DECLINE` | 84.1% | 33.7% | -50.3% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| moujob | 2024 -> 2025 | `RAPID_DECLINE` | 67.5% | 17.5% | -50.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| 【graduated】Ice Shirakoi Ch. / AStars Amakara | 2024 -> 2025 | `RAPID_ASCENT` | 19.1% | 92.2% | +73.1% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Doyser | 2024 -> 2025 | `RAPID_ASCENT` | 1.9% | 38.0% | +36.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Pak LIGHT | 2024 -> 2025 | `RAPID_DECLINE` | 56.0% | 30.7% | -25.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Ivy Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 94.9% | 67.5% | -27.4% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| ดอยล์ | 2024 -> 2025 | `RAPID_ASCENT` | 61.8% | 97.6% | +35.8% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| NEBUEL | VTUBER | 2024 -> 2025 | `RAPID_DECLINE` | 47.1% | 16.3% | -30.9% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Ngerntong-เงินทอง | 2024 -> 2025 | `RAPID_DECLINE` | 76.4% | 13.2% | -63.2% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| JayloNy | 2024 -> 2025 | `RAPID_ASCENT` | 10.2% | 39.2% | +29.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Nergal Near Ch. | 2024 -> 2025 | `RAPID_DECLINE` | 77.1% | 15.1% | -62.0% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Padzang Channel | 2024 -> 2025 | `RAPID_DECLINE` | 27.4% | 1.2% | -26.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Draki Kona Ch. Lumina-First-Myth | 2024 -> 2025 | `RAPID_ASCENT` | 41.4% | 72.9% | +31.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Midnight Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 15.9% | 66.3% | +50.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| TheQuillmon ⌜VZ⌟ | 2024 -> 2025 | `RAPID_ASCENT` | 54.1% | 87.4% | +33.2% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Selene Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 5.7% | 87.9% | +82.2% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Solar Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 89.8% | 54.8% | -35.0% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Mycara Melony Ch. Pixela-Mystic | 2024 -> 2025 | `RAPID_DECLINE` | 82.2% | 37.4% | -44.8% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Meraki Keimii Ch. Pixela Legends | 2024 -> 2025 | `RAPID_DECLINE` | 83.4% | 23.5% | -60.0% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Poppy the Puppy | 2024 -> 2025 | `RAPID_ASCENT` | 0.6% | 54.2% | +53.6% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Kitsuneko Mewten Ch. Pixela-Isekai | 2024 -> 2025 | `RAPID_DECLINE` | 56.7% | 29.5% | -27.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Zekai Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 65.0% | 96.4% | +31.4% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Princess Zelina Ch. Pixela Project | 2024 -> 2025 | `RAPID_ASCENT` | 66.2% | 94.6% | +28.3% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Liz's | WISLIVE | 2024 -> 2025 | `RAPID_DECLINE` | 88.5% | 45.2% | -43.4% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Effy Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 96.2% | 18.1% | -78.1% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| Schneider Ch.【ARP】 | 2024 -> 2025 | `RAPID_DECLINE` | 79.6% | 35.5% | -44.1% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Ayna Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 8.9% | 95.2% | +86.3% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Listen Ch.【ARP】 | 2024 -> 2025 | `RAPID_ASCENT` | 35.0% | 65.1% | +30.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Friskfitz | 2024 -> 2025 | `RAPID_ASCENT` | 26.1% | 80.1% | +54.0% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Victor Hoshino【GRADUATED】 | 2024 -> 2025 | `RAPID_ASCENT` | 9.6% | 60.8% | +51.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Nogi Sensei | 2024 -> 2025 | `RAPID_DECLINE` | 42.0% | 15.7% | -26.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| MOLLY | 2024 -> 2025 | `RAPID_DECLINE` | 91.7% | 58.4% | -33.3% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| Jolly Estaa Ch. Pixela-Isekai | 2025 -> 2026 | `RAPID_ASCENT` | 21.1% | 80.0% | +58.9% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| นานาโฮชิ นานะ / 七星ナナ | 2025 -> 2026 | `RAPID_ASCENT` | 68.7% | 98.1% | +29.4% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Midnight Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 66.3% | 29.4% | -36.9% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Khaojao | 2025 -> 2026 | `RAPID_ASCENT` | 0.6% | 28.7% | +28.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Mycara Melony Ch. Pixela-Mystic | 2025 -> 2026 | `RAPID_ASCENT` | 37.4% | 88.8% | +51.4% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Supeacha ⌜VZ⌟ | 2025 -> 2026 | `RAPID_DECLINE` | 100.0% | 74.4% | -25.6% | `TOP_1_PERCENT` | `BELOW_QUARTILE` |
| Aosora Popo Ch. | 2025 -> 2026 | `RAPID_DECLINE` | 51.2% | 24.4% | -26.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| dtto. | 2025 -> 2026 | `RAPID_ASCENT` | 56.6% | 85.6% | +29.0% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| SEO A XAY | 2025 -> 2026 | `RAPID_ASCENT` | 24.7% | 75.0% | +50.3% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Aisha Channel | 2025 -> 2026 | `RAPID_ASCENT` | 65.7% | 100.0% | +34.3% | `BELOW_QUARTILE` | `TOP_1_PERCENT` |
| SiamNeko Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 47.0% | 10.0% | -37.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Darin V | 2025 -> 2026 | `RAPID_DECLINE` | 47.6% | 5.6% | -42.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Toru Kumaトルくま | 2025 -> 2026 | `RAPID_ASCENT` | 4.2% | 40.0% | +35.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Solar Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 54.8% | 90.6% | +35.8% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Zenith Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 62.1% | 96.2% | +34.2% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Bloodyflora | 2025 -> 2026 | `RAPID_ASCENT` | 7.8% | 40.6% | +32.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| MONARICA | 2025 -> 2026 | `RAPID_DECLINE` | 89.8% | 61.3% | -28.5% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Selene Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 87.9% | 58.8% | -29.2% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Kyomu Ch. | 2025 -> 2026 | `RAPID_ASCENT` | 22.9% | 75.6% | +52.7% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Princess Zelina Ch. Pixela Project | 2025 -> 2026 | `RAPID_DECLINE` | 94.6% | 23.8% | -70.8% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| Zekai Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 96.4% | 44.4% | -52.0% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| S1R Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 74.7% | 47.5% | -27.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Umino Ciala Ch. Pixela Legends | 2025 -> 2026 | `RAPID_DECLINE` | 81.9% | 38.1% | -43.8% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Hanami Lay CH. | 2025 -> 2026 | `RAPID_ASCENT` | 33.7% | 67.5% | +33.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Cerafine Mikael Ch. Lumina-First-Myth | 2025 -> 2026 | `RAPID_ASCENT` | 34.3% | 65.0% | +30.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| SwordAce | 2025 -> 2026 | `RAPID_ASCENT` | 41.6% | 83.8% | +42.2% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Magnum Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 70.5% | 98.8% | +28.3% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Euthalia Zéphyr Ch. Pixela Destiny | 2025 -> 2026 | `RAPID_DECLINE` | 81.3% | 8.8% | -72.6% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Karu Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 49.4% | 81.9% | +32.5% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Unnämed | 2025 -> 2026 | `RAPID_DECLINE` | 41.0% | 5.0% | -36.0% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Biscuit Blythe Ch. Pixela Destiny | 2025 -> 2026 | `RAPID_DECLINE` | 39.8% | 7.5% | -32.3% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Schneider Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 35.5% | 95.6% | +60.1% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| TEENIE | WISLIVE | 2025 -> 2026 | `RAPID_ASCENT` | 51.8% | 76.9% | +25.1% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| MiYuu43 ch. みゆ | 2025 -> 2026 | `RAPID_DECLINE` | 85.5% | 55.0% | -30.5% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Eileennoir Ch. | 2025 -> 2026 | `RAPID_DECLINE` | 88.5% | 53.8% | -34.8% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Listen Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 65.1% | 26.2% | -38.8% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Nezumi Elze Ch. Pixela Legends | 2025 -> 2026 | `RAPID_ASCENT` | 25.3% | 60.0% | +34.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Mosant Ch. | 2025 -> 2026 | `RAPID_ASCENT` | 60.2% | 89.4% | +29.1% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Baku Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 13.9% | 57.5% | +43.6% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Ayna Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 95.2% | 48.8% | -46.4% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| Lucene Ch. | 2025 -> 2026 | `RAPID_ASCENT` | 57.2% | 86.2% | +29.0% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| Ark Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 79.5% | 17.5% | -62.0% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Friskfitz | 2025 -> 2026 | `RAPID_DECLINE` | 80.1% | 37.5% | -42.6% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Ivy Ch.【ARP】 | 2025 -> 2026 | `RAPID_ASCENT` | 67.5% | 97.5% | +30.0% | `BELOW_QUARTILE` | `TOP_5_PERCENT` |
| Nergal Near Ch. | 2025 -> 2026 | `RAPID_ASCENT` | 15.1% | 91.2% | +76.2% | `BELOW_QUARTILE` | `TOP_10_PERCENT` |
| Quentin Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 56.0% | 12.5% | -43.5% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Xonebu X'thulhu Ch. Lumina-World-End | 2025 -> 2026 | `RAPID_ASCENT` | 53.0% | 81.2% | +28.2% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| JueBigHead | 2025 -> 2026 | `RAPID_ASCENT` | 20.5% | 61.9% | +41.4% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Sisira Hydrangea Ch. Pixela S | 2025 -> 2026 | `RAPID_DECLINE` | 69.9% | 38.8% | -31.1% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Hoku Ch. | 2025 -> 2026 | `RAPID_DECLINE` | 53.6% | 19.4% | -34.2% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Mabelle.a | 2025 -> 2026 | `RAPID_ASCENT` | 36.1% | 78.8% | +42.6% | `BELOW_QUARTILE` | `TOP_QUARTILE` |
| 【graduated】Ice Shirakoi Ch. / AStars Amakara | 2025 -> 2026 | `RAPID_DECLINE` | 92.2% | 6.9% | -85.3% | `TOP_10_PERCENT` | `BELOW_QUARTILE` |
| โป๊ะโกะ / PoKo ปลวกทูปเบ๋อ | 2025 -> 2026 | `RAPID_DECLINE` | 99.4% | 68.8% | -30.6% | `TOP_1_PERCENT` | `BELOW_QUARTILE` |
| MamiMumei | 2025 -> 2026 | `RAPID_DECLINE` | 98.8% | 51.9% | -46.9% | `TOP_5_PERCENT` | `BELOW_QUARTILE` |
| DEV Ch.【ARP】 | 2025 -> 2026 | `RAPID_DECLINE` | 72.3% | 20.6% | -51.7% | `BELOW_QUARTILE` | `BELOW_QUARTILE` |
| Stamp LMTY ⌜VZ⌟ | 2025 -> 2026 | `RAPID_DECLINE` | 75.3% | 46.9% | -28.4% | `TOP_QUARTILE` | `BELOW_QUARTILE` |
| Plathong Ch. | 2025 -> 2026 | `RAPID_DECLINE` | 83.1% | 55.6% | -27.5% | `TOP_QUARTILE` | `BELOW_QUARTILE` |

---

## 3. Threshold Sensitivity Comparison

In accordance with Phase T10 validation, pruning low-weight edges removes peripheral shared-viewer bridges while concentrating centrality among high-density agency channels. Stable bridges with >= 50% retention under threshold >= 5 demonstrate genuine multi-viewer co-interaction bridges, whereas channels with 0% retention represent single-viewer tie bridges susceptible to sampling variation.

---
*Report generated automatically by `scripts/analyze_centrality_evolution.py`.*
