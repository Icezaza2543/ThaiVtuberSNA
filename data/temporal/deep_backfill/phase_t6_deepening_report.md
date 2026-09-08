# Phase T6 Deep Comment History & Bias Correction Report

- **Generated at:** 2026-09-08 05:49:03 UTC
- **Dataset Stage:** `deep_historical_backfill_partial`
- **Deepening Target Cohort:** 226 Partial-Capture Historical Videos
- **Terminal Jobs:** 91 / 226 (40.3%)
- **Pending Jobs:** 135
- **Total Pages Fetched:** 339
- **Total Raw Comments Captured:** 28,784
- **Total Unique Viewer-Video Observations:** 27,304

---

## 1. Execution Status Breakdown

| Terminal State | Job Count | % of Deep Targets | Definition |
| :--- | :---: | :---: | :--- |
| **COMPLETED (Full Pagination)** | **91** | 40.3% | Complete pagination reached via nextPageToken |
| **NO_COMMENTS** | **0** | 0.0% | Verified zero comments |
| **COMMENTS_DISABLED** | **0** | 0.0% | Comments disabled by publisher |
| **VIDEO_UNAVAILABLE** | **0** | 0.0% | Video private, deleted, or removed |
| **FAILED** | **0** | 0.0% | Unrecoverable execution error |
| **PENDING / RUNNING** | **135** | 59.7% | Awaiting execution or batch allocation |

---

## 2. Per-Year Deepening Completion

| Calendar Year | Target Videos | Completed | No Comments | Disabled | Unavailable / Failed | Pending | Completion Rate |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2020** | 20 | 20 | 0 | 0 | 0 | 0 | **100.0%** |
| **2021** | 40 | 40 | 0 | 0 | 0 | 0 | **100.0%** |
| **2022** | 22 | 19 | 0 | 0 | 0 | 3 | **86.4%** |
| **2023** | 37 | 3 | 0 | 0 | 0 | 34 | **8.1%** |
| **2024** | 34 | 3 | 0 | 0 | 0 | 31 | **8.8%** |
| **2025** | 46 | 3 | 0 | 0 | 0 | 43 | **6.5%** |
| **2026** | 27 | 3 | 0 | 0 | 0 | 24 | **11.1%** |

---

## 3. Methodological & Privacy Guarantees

1. **Full Temporal Scope:** All comments are retrieved chronologically using `commentThreads.list` with `order=time` and `pageToken` pagination.
2. **Strict Privacy Boundary:** Raw author IDs are immediately hashed using persistent HMAC-SHA256 within the item processing loop. Zero raw commenter names, handles, URLs, or comment texts are ever written to disk or preserved in memory.
3. **Zero Fallback Substitution:** `interaction_at` represents verified comment `publishedAt`. Missing timestamps are never populated with video upload dates.
4. **Precedence Hierarchy:** In snapshot construction, T6 deep observations strictly supersede T5 shallow observations for the same video (`T6 deep > T5 shallow > T2/legacy`), eliminating double counting.
