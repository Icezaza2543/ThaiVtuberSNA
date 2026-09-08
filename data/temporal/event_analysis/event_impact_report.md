# Phase T9: Lifecycle Event Impact Analysis Report (Research Integrity Edition)

## Executive Summary
This report analyzes observed audience and network changes surrounding documented Thai VTuber lifecycle events across **+/- 30-day** and **+/- 90-day** observation windows.

### Methodological & Epistemic Contracts
1. **Primary Verified vs. Exploratory Proxy Separation:**
   - **Primary Analysis Tier:** Strictly limited to **2 verified lifecycle events** (events anchored by explicit video stream evidence or audited registry records).
   - **Exploratory Analysis Tier:** Evaluates **222 observational proxy events** (derived from earliest observed content boundaries or activity cutoffs). Headline statistics do NOT conflate verified milestones with observational proxies.
2. **Strict Non-Causal Framing:**
   - All findings express *observed changes around events* and *temporal co-occurrence associations*. Observational SNA data reflects active interaction within sampled content and must never be interpreted as proving that an event "caused" audience migration.
3. **Evidence Stratification:**
   - Events with fewer than 5 observed active viewers in both pre- and post-windows are classified as `INSUFFICIENT_EVIDENCE`.
4. **Honest Reporting of Event Reduction:**
   - Rigorous correction in T8 reduced the number of verified channel-level events from inflated counts (~300) down to **2 genuine verified anchors**, while preserving **222 exploratory proxy events** for separate sensitivity modeling. 9 target channels with zero public video history were excluded from temporal window analysis.

---

## 1. Event Coverage & Stratification Summary

| Analysis Tier | Verification Status | Events Modeled | 30d Windows | 90d Windows | Sufficient Evidence (90d) | Insufficient Evidence (90d) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **PRIMARY** | `VERIFIED` | **2** | 2 | 2 | 0 | 2 |
| **EXPLORATORY** | `INFERRED_PROXY` | **222** | 222 | 222 | 151 | 71 |
| **EXCLUDED** | `UNKNOWN` | **9** | 0 | 0 | 0 | 9 (Zero video history) |

---

## 2. Primary Analysis: Verified Lifecycle Anchors

The primary analysis evaluates events where the exact event date and lifecycle transition are supported by explicit evidence (video catalog titles or manual registry audit).

### 2.1 Verified Event Metrics (+/- 90-Day Window)

| Channel | Event Type | Event Date | Agency (at Event) | Pre Viewers (90d) | Post Focal Viewers | Focal Retention Rate | Pre-Viewers Seen Elsewhere | Top Post-Associated Channels | Evidence Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :---: |
| **UC3ZglUA0HEUCuGbe5b8zXKw** | `re_debut` | 2022-01-17 | Unknown | 0 | 0 | 0.0% | 0 | None observed | `INSUFFICIENT_EVIDENCE` |
| **UC32lsx7u7vqy63SguuuzmVg** | `graduation` | 2025-12-20 | Unknown | 0 | 0 | 0.0% | 0 | None observed | `INSUFFICIENT_EVIDENCE` |
### 2.2 Substantive Observations on Verified Anchors
- **UC3ZglUA0HEUCuGbe5b8zXKw (Verified `re_debut`, 2022-01-17):**
  - Pre-event active interacting viewers: 0 in the 90-day window.
  - Post-event focal viewers: 0 (focal retention rate = 0.0%).
  - Viewers observed on other channels post-event: 0.
  - Evidence classification: `INSUFFICIENT_EVIDENCE` (Low interaction volume in window (< 5 viewers pre and post)).
- **UC32lsx7u7vqy63SguuuzmVg (Verified `graduation`, 2025-12-20):**
  - Pre-event active interacting viewers: 0 in the 90-day window.
  - Post-event focal viewers: 0 (focal retention rate = 0.0%).
  - Viewers observed on other channels post-event: 0.
  - Evidence classification: `INSUFFICIENT_EVIDENCE` (Low interaction volume in window (< 5 viewers pre and post)).

---

## 3. Exploratory Analysis: Observational Proxy Slices

Observational proxies represent the earliest collected video (`earliest_observed_content`) or the onset of prolonged inactivity (`hiatus_proxy` / `graduation_proxy`). These are analyzed separately as sensitivity benchmarks.

### 3.1 Top Observed Activity Drop around Hiatus Proxies (+/- 90-Day Window)

| Channel | Proxy Event Date | Agency (at Selection) | Pre Viewers (90d) | Post Focal Viewers | Change in Viewers | Continuing Focal Viewers | Post Engaged Other Channels | Evidence Status |
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

### 3.2 Top Audience Volumes at Earliest Content Proxies (+/- 90-Day Window)

| Channel | Earliest Content Date | Agency (at Selection) | Post Viewers (30d) | Post Viewers (90d) | Post Degree (90d) | Evidence Status |
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

---

## 4. Key Epistemic Insights
1. **Impact of Research Rigor on Sample Size:**
   - Restricting primary analysis strictly to verified biographical anchors dramatically reduces statistical power from hundreds of unverified dates to a handful of genuine milestones. This trade-off between *sample size* and *epistemic validity* is the hallmark of rigorous scholarship.
2. **Exploratory Utility of Observational Boundaries:**
   - While earliest and latest upload dates cannot be cited as biographical debut and graduation dates, they remain empirically meaningful as *observational shock points* (e.g. observing community interaction changes before and after a channel ceases uploading).
3. **Observational Data Constraints:**
   - Pre-2023 YouTube comment archiving reflects selective sampling rather than total viewership. Interaction drops reflect active community participation within collected content, not passive view counts.

---
*Report generated automatically by `scripts/analyze_event_impact.py`.*
