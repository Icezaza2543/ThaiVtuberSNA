# Phase T6 Deep Comment History & Bias Correction Report

- **Generated at:** 2026-09-08 05:50:44 UTC
- **Dataset Stage:** `deep_historical_backfill_partial`
- **Deepening Target Cohort:** 226 Partial-Capture Historical Videos
- **Terminal Jobs:** 161 / 226 (71.2%)
- **Pending Jobs:** 65
- **Total Pages Fetched:** 634
- **Total Raw Comments Captured:** 54,174
- **Total Unique Viewer-Video Observations:** 51,097

---

## 1. Execution Status Breakdown

| Terminal State | Job Count | % of Deep Targets | Definition |
| :--- | :---: | :---: | :--- |
| **COMPLETED (Full Pagination)** | **161** | 71.2% | Complete pagination reached via nextPageToken |
| **NO_COMMENTS** | **0** | 0.0% | Verified zero comments |
| **COMMENTS_DISABLED** | **0** | 0.0% | Comments disabled by publisher |
| **VIDEO_UNAVAILABLE** | **0** | 0.0% | Video private, deleted, or removed |
| **FAILED** | **0** | 0.0% | Unrecoverable execution error |
| **PENDING / RUNNING** | **65** | 28.8% | Awaiting execution or batch allocation |

---

## 2. Per-Year Deepening Completion

| Calendar Year | Target Videos | Completed | No Comments | Disabled | Unavailable / Failed | Pending | Completion Rate |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2020** | 20 | 20 | 0 | 0 | 0 | 0 | **100.0%** |
| **2021** | 40 | 40 | 0 | 0 | 0 | 0 | **100.0%** |
| **2022** | 22 | 22 | 0 | 0 | 0 | 0 | **100.0%** |
| **2023** | 37 | 37 | 0 | 0 | 0 | 0 | **100.0%** |
| **2024** | 34 | 34 | 0 | 0 | 0 | 0 | **100.0%** |
| **2025** | 46 | 5 | 0 | 0 | 0 | 41 | **10.9%** |
| **2026** | 27 | 3 | 0 | 0 | 0 | 24 | **11.1%** |

---

## 3. Methodological & Privacy Guarantees

1. **Full Temporal Scope:** All comments are retrieved chronologically using `commentThreads.list` with `order=time` and `pageToken` pagination.
2. **Strict Privacy Boundary:** Raw author IDs are immediately hashed using persistent HMAC-SHA256 within the item processing loop. Zero raw commenter names, handles, URLs, or comment texts are ever written to disk or preserved in memory.
3. **Zero Fallback Substitution:** `interaction_at` represents verified comment `publishedAt`. Missing timestamps are never populated with video upload dates.
4. **Precedence Hierarchy:** In snapshot construction, T6 deep observations strictly supersede T5 shallow observations for the same video (`T6 deep > T5 shallow > T2/legacy`), eliminating double counting.
