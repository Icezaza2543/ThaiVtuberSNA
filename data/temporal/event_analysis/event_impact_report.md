# Phase T9: Lifecycle Event Impact Analysis Report

## Executive Summary
This report analyzes observed audience and network changes surrounding **300** documented Thai VTuber lifecycle events across **+/- 30-day** and **+/- 90-day** observation windows.

### Methodological & Epistemic Guardrails
- **Non-Causal Contract:** All metrics reflect *observed changes around events* and *temporal co-occurrence associations*. Under no circumstances does this report claim that an event "caused" audience migration or behavioral shifts. Observational YouTube interaction data (comments and live chats) captures active participation within sampled content, which may reflect shifting sampling density, creator activity schedules, or general community interest.
- **Evidence Stratification:** Events with fewer than 5 observed active viewers in both pre- and post-windows are explicitly classified as `INSUFFICIENT_EVIDENCE` to prevent statistical distortion from sparse observations.
- **Privacy Standard:** Zero individual viewer hashes (`viewer_hash`) or personal identifiers are stored or exported. All figures represent aggregate counts.

---

## 1. Evidence Stratification Overview

| Observation Window | Sufficient Evidence (>= 5 viewers) | Insufficient Evidence (< 5 viewers) | Total Event Windows | Sufficient Ratio |
| :--- | :---: | :---: | :---: | :---: |
| +/- 30 Days | 164 | 136 | 300 | 54.7% |
| +/- 90 Days | 212 | 88 | 300 | 70.7% |

---

## 2. Event Type Breakdown (+/- 90-Day Window)

| Event Type | Total Events | Sufficient Evidence | Insufficient Evidence | Mean Pre-Viewers | Mean Post-Viewers |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `agency_exit` | 3 | 2 | 1 | 26.3 | 9.3 |
| `agency_join` | 75 | 59 | 16 | 0.0 | 51.5 |
| `debut` | 182 | 123 | 59 | 1.7 | 84.1 |
| `graduation` | 8 | 5 | 3 | 13.6 | 5.5 |
| `hiatus` | 32 | 23 | 9 | 29.0 | 44.8 |

---

## 3. Detailed Case Studies: Observed Associations

### 3.1 Graduation Events (Observed Pre/Post Dynamics)
For talent graduations, we analyze the retention of pre-graduation audience on the focal channel post-graduation (typically zero or minimal archival comments) and the observed presence of those same viewers on other community channels during the post-event window.

| Channel | Event Date | Agency (at Event) | Pre Viewers (90d) | Post Focal Viewers | Focal Retention Rate | Pre-Viewers Seen Elsewhere | Top Post-Associated Channels | Evidence Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :---: |
| **【graduated】Ice Shirakoi Ch. / AStars Amakara** | 2025-04-30 | AStars Production | 51 | 23 | 7.8% | 9 | Uniwii Ch.【ARP】 (2); Lunatrix Ch. (1); TeenWISU (1) | `SUFFICIENT_EVIDENCE` |
| **【graduated】Amaris Sayo Ch. / AStars Amakara** | 2025-02-14 | AStars Production | 28 | 5 | 0.0% | 7 | 【graduated】Ice Shirakoi Ch. / AStars Amakara (4); Ayna Ch.【ARP】 (3); Supeacha ⌜VZ⌟ (2) | `SUFFICIENT_EVIDENCE` |
| **Shimonz** | 2022-10-16 | Independent | 14 | 3 | 0.0% | 0 | None observed | `SUFFICIENT_EVIDENCE` |
| **Morika Rei【ARRI】[Graduated]** | 2025-12-28 | Independent | 8 | 1 | 0.0% | 1 | dtto. (1) | `SUFFICIENT_EVIDENCE` |
| **Victor Hoshino【GRADUATED】** | 2025-09-20 | Independent | 6 | 7 | 16.7% | 0 | None observed | `SUFFICIENT_EVIDENCE` |
| **Rawley Izzy G. Ch. | Graduated** | 2024-03-15 | Independent | 2 | 4 | 0.0% | 0 | None observed | `INSUFFICIENT_EVIDENCE` |
| **Mysterica X. Ch. | RPG** | 2024-09-03 | RPG | 0 | 0 | 0.0% | 0 | None observed | `INSUFFICIENT_EVIDENCE` |
| **Lord Cha Zele Ch. ◤Graduation◢** | 2025-05-08 | Independent | 0 | 1 | 0.0% | 0 | None observed | `INSUFFICIENT_EVIDENCE` |

*Analytical Observation on Graduations:*
- Channels graduating after active community tenure (e.g. *Ice Shirakoi*, *Amaris Sayo*, *Shimonz*) display noticeable temporal associations: pre-event viewers are subsequently observed interacting with affiliated agency peers (e.g. other AStars or ARP talents) or prominent independent creators.
- Graduated channels with low pre-event catalog coverage or archival interactions (< 5 viewers) are appropriately flagged as `INSUFFICIENT_EVIDENCE`.

### 3.2 Hiatus Events (Pre-Hiatus vs Post-Hiatus Dynamics)
For hiatus periods, we observe whether audiences remain engaged with the channel or whether engagement drops markedly during the hiatus window.

| Channel | Event Date | Agency (at Event) | Pre Viewers (90d) | Post Focal Viewers | Change in Viewers | Continuing Focal Viewers | Post Engaged Other Channels | Evidence Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **PeachiView** | 2022-01-14 | Independent | 271 | 132 | -139 | 29 | 10 | `SUFFICIENT_EVIDENCE` |
| **Quentin Ch.【ARP】** | 2025-04-02 | Algorhythm Project | 149 | 13 | -136 | 0 | 15 | `SUFFICIENT_EVIDENCE` |
| **Euthalia Zéphyr Ch. Pixela Destiny** | 2025-04-11 | Pixela Project | 86 | 4 | -82 | 1 | 23 | `SUFFICIENT_EVIDENCE` |
| **Meraki Keimii Ch. Pixela Legends** | 2023-08-01 | Pixela Project | 74 | 496 | +422 | 30 | 24 | `SUFFICIENT_EVIDENCE` |
| **Beariss Beam** | 2025-10-13 | Independent | 61 | 73 | +12 | 1 | 3 | `SUFFICIENT_EVIDENCE` |
| **Princess Zelina Ch. Pixela Project** | 2025-05-10 | Pixela Project | 44 | 312 | +268 | 17 | 30 | `SUFFICIENT_EVIDENCE` |
| **Hey Solly** | 2024-08-27 | Independent | 37 | 29 | -8 | 1 | 1 | `SUFFICIENT_EVIDENCE` |
| **TEENIE | WISLIVE** | 2024-11-03 | Independent | 34 | 12 | -22 | 0 | 7 | `SUFFICIENT_EVIDENCE` |
| **Ayna Ch.【ARP】** | 2025-04-05 | Algorhythm Project | 33 | 167 | +134 | 4 | 18 | `SUFFICIENT_EVIDENCE` |
| **CoolRin CH** | 2024-02-13 | Independent | 23 | 14 | -9 | 2 | 8 | `SUFFICIENT_EVIDENCE` |
| **Aruna Shuun Ch. Pixela Destiny** | 2025-06-08 | Pixela Project | 23 | 1 | -22 | 0 | 3 | `SUFFICIENT_EVIDENCE` |
| **MamMam Ch. 真夢マム** | 2022-06-18 | Independent | 20 | 2 | -18 | 0 | 0 | `SUFFICIENT_EVIDENCE` |
| **Jiru ch. Euphora** | 2026-02-01 | Euphora Project | 14 | 25 | +11 | 3 | 23 | `SUFFICIENT_EVIDENCE` |
| **Castesia | Phoenix Vtuber of Noxus** | 2024-03-28 | Independent | 13 | 1 | -12 | 0 | 1 | `SUFFICIENT_EVIDENCE` |
| **Hinabe HongFei Ch. Pixela Project** | 2023-12-10 | Pixela Project | 11 | 72 | +61 | 1 | 6 | `SUFFICIENT_EVIDENCE` |

*Analytical Observation on Hiatuses:*
- When established channels enter documented hiatuses (e.g. *PeachiView*, *Castesia*), focal active participation decreases substantially in the subsequent 90 days.
- Audience members active prior to hiatus are observed continuing participation on peer channels within the broader VTuber ecosystem.

### 3.3 Debut Events (Audience Influx & Pre-Existing Network)
For channel debuts, pre-debut focal interaction is inherently zero (or limited to pre-stream chat). The post-debut window demonstrates initial audience volume and early network co-occurrence.

| Channel | Event Date | Agency (at Event) | Post Viewers (30d) | Post Viewers (90d) | Post Degree (90d) | Evidence Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Unnämed** | 2023-02-05 | Independent | 2469 | 3463 | 4 | `SUFFICIENT_EVIDENCE` |
| **久檻夜くぅ / Qualia Qu Ch.** | 2020-06-29 | Independent | 1155 | 1237 | 6 | `SUFFICIENT_EVIDENCE` |
| **Pyork The Pork** | 2021-09-04 | Independent | 221 | 830 | 30 | `SUFFICIENT_EVIDENCE` |
| **Aisha Channel** | 2021-10-31 | Independent | 608 | 757 | 33 | `SUFFICIENT_EVIDENCE` |
| **TeenWISU** | 2021-08-24 | Independent | 7 | 467 | 20 | `SUFFICIENT_EVIDENCE` |
| **Nongwan TV** | 2023-09-25 | Independent | 282 | 460 | 15 | `SUFFICIENT_EVIDENCE` |
| **โป๊ะโกะ / PoKo ปลวกทูปเบ๋อ** | 2025-07-10 | Independent | 203 | 452 | 36 | `SUFFICIENT_EVIDENCE` |
| **Roxzy ロキジー** | 2025-06-19 | Independent | 92 | 431 | 22 | `SUFFICIENT_EVIDENCE` |
| **KAMAI** | 2024-11-23 | Independent | 282 | 400 | 37 | `SUFFICIENT_EVIDENCE` |
| **Mycara Melony Ch. Pixela-Mystic** | 2022-11-24 | Pixela Project | 238 | 312 | 28 | `SUFFICIENT_EVIDENCE` |
| **SiamNeko Ch.【ARP】** | 2021-06-23 | Algorhythm Project | 147 | 306 | 24 | `SUFFICIENT_EVIDENCE` |
| **Laibaht Ch. / หลายบาท** | 2021-05-10 | Independent | 144 | 273 | 18 | `SUFFICIENT_EVIDENCE` |

---

## 4. Key Network Takeaways
1. **Network Continuity Across Lifecycle Shocks:**
   - Even when a talent graduates or halts activity, their audience is frequently observed maintaining active participation across other Thai VTuber channels.
   - For agency graduations, observed transitions are divided between agency peer channels and major independent creators.
2. **Impact of Observation Window Length:**
   - The +/- 90-day window increases the proportion of events with sufficient evidence from **54.7%** (30-day) to **70.7%** (90-day), demonstrating that audience return and cross-channel engagement unfold over multi-month horizons.
3. **Data Limitations:**
   - Events occurring near the boundaries of available temporal sampling (e.g., late 2025/2026 or early 2020) have truncated post- or pre-observation windows.
   - Catalog coverage differences across channels naturally modulate the absolute viewer numbers.

---
*Report generated automatically by `scripts/analyze_event_impact.py`.*
