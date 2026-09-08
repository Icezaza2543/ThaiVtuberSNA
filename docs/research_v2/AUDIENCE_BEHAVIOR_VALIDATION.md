# Audience Behavior Yearly Derivation: Mathematical & Epistemic Audit Report

**Date of Audit:** September 9, 2026  
**Audited Artifacts:**
- `data/industry/audience_behavior_yearly.parquet`
- `data/industry/audience_behavior_yearly.json`
- `scripts/derive_audience_behavior_aggregates.py`

---

## 1. Executive Summary

An independent mathematical and governance audit was conducted on the yearly behavioral audience aggregation engine (`scripts/derive_audience_behavior_aggregates.py`). The pipeline derives aggregate public metrics from internal privacy-preserving hashed interaction events across 2020–2026 YTD.

The audit verified:
1. **Mathematical Consistency**: `population_observed_accounts = newly_observed_accounts + re_observed_accounts` holds exactly for all years ($\Delta = 0$).
2. **Channel Breadth Partition**: `population_observed_accounts = single_channel_observed + multi_channel_observed` holds exactly ($\Delta = 0$).
3. **Modality Partition**: `comment_only + live_chat_only + mixed_modality = population_observed_accounts` holds with zero unaccounted accounts ($\Delta = 0$).
4. **Epistemic Integrity**: No viewer-level data or demographics (age, gender, location, income) are inferred or exported. Outputs are strictly **k-anonymized public behavioral interaction aggregates (Level C)**.

---

## 2. Metric-by-Metric Verification Matrix

| Metric Name | Mathematical Definition | Denominator | Boundary Condition Validation | Status |
| :--- | :--- | :--- | :--- | :--- |
| `population_observed_accounts` | $\lvert \{ v \in \text{Viewers} : \text{year}(v) = y \} \rvert$ | N/A (Base) | Counts distinct `viewer_hash` active within civil calendar year $y$. | **VERIFIED** |
| `newly_observed_accounts` | $\lvert \{ v : \text{year}(v) = y \land \min(\text{years}(v)) = y \} \rvert$ | `population_observed_accounts` | Identifies accounts whose earliest observed interaction in the canonical catalog occurs in year $y$. | **VERIFIED** |
| `re_observed_accounts` | `population_observed_accounts - newly_observed_accounts` | `population_observed_accounts` | $0$ in 2020 baseline; strictly monotonically positive thereafter (509 in 2021 to 3,038 in 2025). | **VERIFIED** |
| `reactivated_accounts` | $\lvert \{ v : \text{year}(v)=y \land \min \le y-2 \land y-1 \notin \text{years}(v) \} \rvert$ | `population_observed_accounts` | Enforces gap of $\ge 1$ calendar year. Exactly $0$ in 2020 and 2021 by mathematical definition. | **VERIFIED** |
| `single_channel_observed` | $\lvert \{ v : \text{year}(v)=y \land \lvert \text{channels}(v, y) \rvert = 1 \} \rvert$ | `population_observed_accounts` | Accounts interacting with exactly 1 target creator in year $y$. | **VERIFIED** |
| `multi_channel_observed` | $\lvert \{ v : \text{year}(v)=y \land \lvert \text{channels}(v, y) \rvert \ge 2 \} \rvert$ | `population_observed_accounts` | Accounts interacting with $\ge 2$ target creators in year $y$. Complement of single-channel. | **VERIFIED** |
| `same_community_multi` | $\lvert \{ v : \lvert\text{channels}\rvert \ge 2 \land \lvert\text{communities}(v, y)\rvert = 1 \} \rvert$ | `population_observed_accounts` | Multi-channel accounts whose interactions fall entirely within a single Louvain community cluster. | **VERIFIED** |
| `cross_community_observed`| $\lvert \{ v : \lvert\text{communities}(v, y)\rvert \ge 2 \} \rvert$ | `population_observed_accounts` | Cross-community bridge accounts. | **VERIFIED** |
| `cross_agency_observed` | $\lvert \{ v : \lvert\text{agencies}(v, y)\rvert \ge 2 \} \rvert$ | `population_observed_accounts` | Accounts crossing agency boundaries (e.g. ARP and Pixela, or Indie and Corporate). | **VERIFIED** |
| `comment_only_observed` | $\lvert \{ v : \text{has\_comment}=1 \land \text{has\_chat}=0 \} \rvert$ | `population_observed_accounts` | Asynchronous feedback audience. | **VERIFIED** |
| `live_chat_only_observed` | $\lvert \{ v : \text{has\_comment}=0 \land \text{has\_chat}=1 \} \rvert$ | `population_observed_accounts` | Synchronous livestream chat audience. | **VERIFIED** |
| `mixed_modality_observed` | $\lvert \{ v : \text{has\_comment}=1 \land \text{has\_chat}=1 \} \rvert$ | `population_observed_accounts` | Core omnichannel engaged audience. | **VERIFIED** |

---

## 3. Longitudinal Boundary Checks & Year-by-Year Breakdown

| Year | Total Population | Newly Observed | Re-Observed | Reactivated | Single-Channel | Multi-Channel | Cross-Agency | Mixed Modality |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2020** | 5,232 | 5,232 (100.0%) | 0 (0.0%) | 0 (0.0%) | 5,081 (97.1%) | 151 (2.9%) | 7 (0.1%) | 49 (0.9%) |
| **2021** | 11,259 | 10,750 (95.5%) | 509 (4.5%) | 0 (0.0%) | 10,176 (90.4%) | 1,083 (9.6%) | 627 (5.6%) | 382 (3.4%) |
| **2022** | 12,005 | 10,740 (89.5%) | 1,265 (10.5%) | 111 (0.9%) | 11,198 (93.3%) | 807 (6.7%) | 393 (3.3%) | 301 (2.5%) |
| **2023** | 18,646 | 17,104 (91.7%) | 1,542 (8.3%) | 369 (2.0%) | 17,251 (92.5%) | 1,395 (7.5%) | 733 (3.9%) | 612 (3.3%) |
| **2024** | 13,478 | 11,325 (84.0%) | 2,153 (16.0%) | 476 (3.5%) | 12,279 (91.1%) | 1,199 (8.9%) | 546 (4.1%) | 520 (3.9%) |
| **2025** | 17,119 | 14,081 (82.3%) | 3,038 (17.7%) | 948 (5.5%) | 15,421 (90.1%) | 1,698 (9.9%) | 692 (4.0%) | 788 (4.6%) |
| **2026 YTD** | 13,259 | 10,486 (79.1%) | 2,773 (20.9%) | 826 (6.2%) | 11,840 (89.3%) | 1,419 (10.7%) | 356 (2.7%) | 494 (3.7%) |

---

## 4. Key Epistemic Insights

1. **Re-observation Rate Accumulation**:
   - In 2020, 100% of accounts were new to the observational window.
   - By 2025–2026 YTD, **17.7% to 20.9%** of annual active accounts are longitudinally returning viewers previously observed in earlier years.
   - Reactivated accounts (returning after at least 1 full year of absence) grew from 0.9% in 2022 to **5.5% in 2025** and **6.2% in 2026 YTD**, disproving the hypothesis of complete audience turnover.

2. **Stability of the Multi-Channel Tail**:
   - Throughout 2021–2026, the percentage of viewers interacting across $\ge 2$ target channels within a single year has remained bounded within **6.7% to 10.7%**.
   - The overwhelming majority (~90%) of observed interacting accounts interact with only one channel per calendar year in our sampled catalog.

3. **2026 YTD Labeling**:
   - The 2026 window represents partial-year data through September 2026 (`2026 (YTD / Partial)`). It must not be directly compared against full 12-month calendar totals without normalizing for observation duration.
