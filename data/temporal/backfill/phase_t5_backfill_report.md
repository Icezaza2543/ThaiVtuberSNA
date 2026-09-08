# Phase T5 Historical Backfill Report

- **Generated at:** 2026-09-08 05:00:04 UTC
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
| **Terminal Jobs** | **1,350** | Completed, empty, disabled, unavailable, or failed |
| **Pending Jobs** | **3,280** | Remaining jobs to process |
| **Completion Ratio** | **29.2%** | Terminal jobs / manifest videos |
| **Completed with Observations** | **1,103** | Parquet observations successfully written |
| **Total Comment Observations** | **25,597** | Deduplicated presence records |
| **Partial Captures (hit 100 cap)** | **99** | Videos where $>100$ comments exist |
| **Comments Disabled** | **15** | YouTube comments disabled by creator |
| **No Comments Found** | **232** | Video with 0 comments posted |
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
| 2022 | 576 | 572 | 437 | 129 | 6 | 0 | 0 | 4 | 98 | 8,432 | 22 |
| 2023 | 788 | 102 | 88 | 13 | 1 | 0 | 0 | 686 | 17 | 1,990 | 7 |
| 2024 | 930 | 114 | 103 | 11 | 0 | 0 | 0 | 816 | 19 | 2,230 | 10 |
| 2025 | 962 | 15 | 15 | 0 | 0 | 0 | 0 | 947 | 3 | 174 | 0 |
| 2026 | 827 | 0 | 0 | 0 | 0 | 0 | 0 | 827 | 0 | 0 | 0 |

---

## 3. Coverage by Demographic Segments

### By Subscriber Tier

| Tier | Manifest Videos | Completed | Comment Observations |
| :--- | :---: | :---: | :---: |
| A | 1,867 | 463 | 8,600 |
| B | 1,399 | 229 | 3,116 |
| C | 89 | 29 | 155 |
| D | 1 | 0 | 0 |
| S | 1,274 | 382 | 13,726 |

### By Agency Group

| Agency | Manifest Videos | Completed | Comment Observations |
| :--- | :---: | :---: | :---: |
| AStars Production | 27 | 9 | 20 |
| Algorhythm Project | 812 | 114 | 2,056 |
| Euphora Project | 48 | 20 | 169 |
| Independent | 2,845 | 703 | 17,940 |
| Lumina Live | 204 | 51 | 820 |
| Pixela Project | 522 | 125 | 2,762 |
| Polygon Official | 24 | 12 | 103 |
| RPG | 1 | 0 | 0 |
| Ti19t | 37 | 20 | 241 |
| Virtual Zeven (VZ) | 110 | 49 | 1,486 |

---

## 4. Privacy & Methodological Disclosures

1. **Sampled Observation Scope:** Observations are capped at 100 top-level comments per sampled video. This constitutes a representative sample rather than exhaustive comment archives.
2. **Strict Temporal Integrity:** Comment timestamps are mapped directly from YouTube `publishedAt`. Videos with unavailable comment timestamps have `interaction_at = NULL` and are excluded from temporal windows.
3. **Zero PII Leakage:** Local privacy audit verified 0 raw `UC...` viewer IDs, 0 display names, 0 URLs, and 0 comment bodies across all generated outputs.
