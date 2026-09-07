# Phase T5 Bounded Real Pilot Report

**Generated at:** 2026-09-07 19:48:21 UTC  
**Scope:** Bounded 20-Channel Pilot Cohort  
**Storage Engine:** Local Parquet + DuckDB (`data/temporal/observations/comment/`)  

---

## 1. Executive Summary

| Metric | Value | Notes / Methodology |
| :--- | :---: | :--- |
| **Manifest Videos Registered** | **4,630** | Total stratified videos queued |
| **Videos Successfully Extracted** | **318** | Parquet observations written |
| **Total Comment Observations** | **6,759** | Deduplicated presence records |
| **Partial Captures (hit 100 cap)** | **25** | Videos where $>100$ comments exist |
| **Comments Disabled** | **2** | YouTube comments disabled by creator |
| **No Comments Found** | **30** | Video with 0 comments posted |
| **Video Unavailable / 404** | **0** | Private, deleted, or unlisted |
| **Pending Jobs** | **4,280** | Ready for subsequent batch execution |
| **Failed Jobs** | **0** | Network or unexpected API errors |

> [!NOTE]
> Observations represent observed commenters with dated interaction evidence. Raw viewer channel IDs were hashed immediately via HMAC-SHA256 within the extraction loop, and zero commenter display names, URLs, or comment texts are stored.

---

## 2. Longitudinal Interaction Evidence Coverage by Year

| Year | Sampled Videos | Completed | Active Channels | Comment Observations | Partial Captures | Disabled/Empty |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2020 | 164 | 7 | 2 | 283 | 0 | 1 |
| 2021 | 383 | 39 | 8 | 1,032 | 6 | 0 |
| 2022 | 576 | 66 | 12 | 1,050 | 2 | 6 |
| 2023 | 788 | 88 | 17 | 1,990 | 7 | 14 |
| 2024 | 930 | 103 | 19 | 2,230 | 10 | 11 |
| 2025 | 962 | 15 | 3 | 174 | 0 | 0 |
| 2026 | 827 | 0 | 0 | 0 | 0 | 0 |

---

## 3. Coverage by Demographic Segments

### By Subscriber Tier

| Tier | Manifest Videos | Completed | Comment Observations |
| :--- | :---: | :---: | :---: |
| A | 1,867 | 123 | 2,089 |
| B | 1,399 | 43 | 300 |
| C | 89 | 19 | 106 |
| D | 1 | 0 | 0 |
| S | 1,274 | 133 | 4,264 |

### By Agency Group

| Agency | Manifest Videos | Completed | Comment Observations |
| :--- | :---: | :---: | :---: |
| AStars Production | 27 | 9 | 20 |
| Algorhythm Project | 812 | 35 | 1,117 |
| Euphora Project | 48 | 20 | 169 |
| Independent | 2,845 | 101 | 2,705 |
| Lumina Live | 204 | 51 | 820 |
| Pixela Project | 522 | 39 | 557 |
| Polygon Official | 24 | 12 | 103 |
| RPG | 1 | 0 | 0 |
| Ti19t | 37 | 20 | 241 |
| Virtual Zeven (VZ) | 110 | 31 | 1,027 |

---

## 4. Privacy & Methodological Disclosures

1. **Sampled Observation Scope:** Observations are capped at 100 top-level comments per sampled video. This constitutes a representative sample rather than exhaustive comment archives.
2. **Strict Temporal Integrity:** Comment timestamps are mapped directly from YouTube `publishedAt`. Videos with unavailable comment timestamps have `interaction_at = NULL` and are excluded from temporal windows.
3. **Zero PII Leakage:** Local privacy audit verified 0 raw `UC...` viewer IDs, 0 display names, 0 URLs, and 0 comment bodies across all generated outputs.
