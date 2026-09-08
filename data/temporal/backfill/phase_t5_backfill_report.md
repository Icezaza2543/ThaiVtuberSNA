# Phase T5 Historical Backfill Report

- **Generated at:** 2026-09-08 05:10:26 UTC
- **Scope:** Full Stratified Historical Cohort
- **Dataset Stage:** `historical_stratified_backfill_partial`
- **Sampling Strategy:** deterministic SHA-256 hash ranking; first-ranked candidate per temporal bin
- **Storage Engine:** Local Parquet + DuckDB (`data/temporal/observations/comment/`)

---

## 1. Executive Summary

| Metric | Value | Notes / Methodology |
| :--- | :---: | :--- |
| **Dataset Maturity Stage** | **`historical_stratified_backfill_partial`** | Explicit partial vs complete gate |
| **Sampling Manifest Total** | **4,630** | Total stratified videos queued |
| **Terminal Jobs** | **4,350** | Completed, empty, disabled, unavailable, or failed |
| **Pending Jobs** | **280** | Remaining jobs to process |
| **Completion Ratio** | **94.0%** | Terminal jobs / manifest videos |
| **Completed with Observations** | **3,480** | Parquet observations successfully written |
| **Total Comment Observations** | **63,250** | Deduplicated presence records |
| **Partial Captures (hit 100 cap)** | **215** | Videos where $>100$ comments exist |
| **Comments Disabled** | **41** | YouTube comments disabled by creator |
| **No Comments Found** | **829** | Video with 0 comments posted |
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
| 2026 | 827 | 547 | 417 | 128 | 2 | 0 | 0 | 280 | 93 | 6,458 | 16 |

---

## 3. Coverage by Demographic Segments

### By Subscriber Tier

| Tier | Manifest Videos | Completed | Comment Observations |
| :--- | :---: | :---: | :---: |
| A | 1,867 | 1,461 | 21,836 |
| B | 1,399 | 912 | 9,982 |
| C | 89 | 49 | 249 |
| D | 1 | 0 | 0 |
| S | 1,274 | 1,058 | 31,183 |

### By Agency Group

| Agency | Manifest Videos | Completed | Comment Observations |
| :--- | :---: | :---: | :---: |
| AStars Production | 27 | 21 | 154 |
| Algorhythm Project | 812 | 579 | 7,460 |
| Euphora Project | 48 | 43 | 716 |
| Independent | 2,845 | 2,083 | 44,798 |
| Lumina Live | 204 | 170 | 1,638 |
| Pixela Project | 522 | 439 | 5,490 |
| Polygon Official | 24 | 23 | 183 |
| RPG | 1 | 0 | 0 |
| Ti19t | 37 | 23 | 244 |
| Virtual Zeven (VZ) | 110 | 99 | 2,567 |

---

## 4. Privacy & Methodological Disclosures

1. **Sampled Observation Scope:** Observations are capped at 100 top-level comments per sampled video. This constitutes a representative sample rather than exhaustive comment archives.
2. **Strict Temporal Integrity:** Comment timestamps are mapped directly from YouTube `publishedAt`. Videos with unavailable comment timestamps have `interaction_at = NULL` and are excluded from temporal windows.
3. **Zero PII Leakage:** Local privacy audit verified 0 raw `UC...` viewer IDs, 0 display names, 0 URLs, and 0 comment bodies across all generated outputs.
