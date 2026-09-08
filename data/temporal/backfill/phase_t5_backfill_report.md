# Phase T5 Historical Backfill Report

- **Generated at:** 2026-09-08 05:11:39 UTC
- **Scope:** Full Stratified Historical Cohort
- **Dataset Stage:** `historical_stratified_backfill_complete`
- **Sampling Strategy:** deterministic SHA-256 hash ranking; first-ranked candidate per temporal bin
- **Storage Engine:** Local Parquet + DuckDB (`data/temporal/observations/comment/`)

---

## 1. Executive Summary

| Metric | Value | Notes / Methodology |
| :--- | :---: | :--- |
| **Dataset Maturity Stage** | **`historical_stratified_backfill_complete`** | Explicit partial vs complete gate |
| **Sampling Manifest Total** | **4,630** | Total stratified videos queued |
| **Terminal Jobs** | **4,630** | Completed, empty, disabled, unavailable, or failed |
| **Pending Jobs** | **0** | Remaining jobs to process |
| **Completion Ratio** | **100.0%** | Terminal jobs / manifest videos |
| **Completed with Observations** | **3,675** | Parquet observations successfully written |
| **Total Comment Observations** | **66,167** | Deduplicated presence records |
| **Partial Captures (hit 100 cap)** | **226** | Videos where $>100$ comments exist |
| **Comments Disabled** | **44** | YouTube comments disabled by creator |
| **No Comments Found** | **911** | Video with 0 comments posted |
| **Video Unavailable / 404** | **0** | Private, deleted, or unlisted |
| **Failed Jobs** | **0** | Network or unexpected API errors |

> [!NOTE]
> Observations represent observed commenters with dated interaction evidence. Raw viewer channel IDs were hashed immediately via HMAC-SHA256 within the extraction loop, and zero commenter display names, URLs, or comment texts are stored.

---

## 2. Longitudinal Interaction Evidence Coverage by Year

| Year | Manifest Videos | Terminal Jobs | Completed with Observations | No Comments | Disabled | Unavailable | Failed | Pending | Channels with Captured Comments | Comment Observations | Partial Captures |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2020 | 164 | 164 | 133 | 24 | 7 | 0 | 0 | 0 | 31 | 4,038 | 20 |
| 2021 | 383 | 383 | 327 | 55 | 1 | 0 | 0 | 0 | 72 | 8,733 | 40 |
| 2022 | 576 | 576 | 441 | 129 | 6 | 0 | 0 | 0 | 98 | 8,513 | 22 |
| 2023 | 788 | 788 | 622 | 157 | 9 | 0 | 0 | 0 | 134 | 11,420 | 37 |
| 2024 | 930 | 930 | 762 | 157 | 11 | 0 | 0 | 0 | 155 | 11,694 | 34 |
| 2025 | 962 | 962 | 778 | 179 | 5 | 0 | 0 | 0 | 162 | 12,394 | 46 |
| 2026 | 827 | 827 | 612 | 210 | 5 | 0 | 0 | 0 | 141 | 9,375 | 27 |

---

## 3. Coverage by Demographic Segments

### By Subscriber Tier

| Tier | Manifest Videos | Completed | Comment Observations |
| :--- | :---: | :---: | :---: |
| A | 1,867 | 1,534 | 22,854 |
| B | 1,399 | 969 | 10,299 |
| C | 89 | 49 | 249 |
| D | 1 | 0 | 0 |
| S | 1,274 | 1,123 | 32,765 |

### By Agency Group

| Agency | Manifest Videos | Completed | Comment Observations |
| :--- | :---: | :---: | :---: |
| AStars Production | 27 | 21 | 154 |
| Algorhythm Project | 812 | 603 | 7,644 |
| Euphora Project | 48 | 43 | 716 |
| Independent | 2,845 | 2,203 | 47,363 |
| Lumina Live | 204 | 193 | 1,732 |
| Pixela Project | 522 | 467 | 5,564 |
| Polygon Official | 24 | 23 | 183 |
| RPG | 1 | 0 | 0 |
| Ti19t | 37 | 23 | 244 |
| Virtual Zeven (VZ) | 110 | 99 | 2,567 |

---

## 4. Privacy & Methodological Disclosures

1. **Sampled Observation Scope:** Observations are capped at 100 top-level comments per sampled video. This constitutes a representative sample rather than exhaustive comment archives.
2. **Strict Temporal Integrity:** Comment timestamps are mapped directly from YouTube `publishedAt`. Videos with unavailable comment timestamps have `interaction_at = NULL` and are excluded from temporal windows.
3. **Zero PII Leakage:** Local privacy audit verified 0 raw `UC...` viewer IDs, 0 display names, 0 URLs, and 0 comment bodies across all generated outputs.
