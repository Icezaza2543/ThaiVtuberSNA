# Phase T5-A Historical Sampling Audit Report

**Generated at:** 2026-09-07 19:44:15 UTC  
**Manifest Version:** v1.0  
**Sampling Engine:** Deterministic Stratified Bimonthly Hash  

---

## 1. Executive Summary

| Metric | Value | Proportion / Context |
| :--- | :--- | :--- |
| **Target Cohort Population** | **193** channels | Frozen T1 research cohort |
| **Channels Represented in Sample** | **184** channels | **95.3%** cohort coverage |
| **Known Zero-Upload Channels** | **9** channels | Confirmed zero uploads (`NO_VIDEOS`) |
| **Total Historical Catalog Videos** | **96,420** videos | T1 Parquet video catalog |
| **Eligible Videos (2020–2026)** | **96,420** videos | 100.0% of catalog is in 2020–2026 |
| **Stratified Sampled Videos** | **4,630** videos | **4.80%** overall selection rate |
| **Target Rate** | **6 videos / channel / year** | Bi-monthly representative dispersion |

> [!NOTE]
> The sampling rate of ~4.8% intentionally achieves comprehensive longitudinal coverage across all 7 years without brute-forcing 96,420 videos. Missing evidence in earlier years is mathematically tracked and never conflated with zero audience.

---

## 2. Year-by-Year Stratification Breakdown

| Year | Catalog Videos | Sampled Videos | Channels Active | Cohort Coverage | Median Videos/Channel |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 2020 | 1,897 | 164 | 36 | 18.7% | 6 |
| 2021 | 5,601 | 383 | 73 | 37.8% | 6 |
| 2022 | 9,386 | 576 | 101 | 52.3% | 6 |
| 2023 | 15,516 | 788 | 137 | 71.0% | 6 |
| 2024 | 22,436 | 930 | 160 | 82.9% | 6 |
| 2025 | 25,246 | 962 | 165 | 85.5% | 6 |
| 2026 | 16,338 | 827 | 147 | 76.2% | 6 |

---

## 3. Channel-Year Strata Completeness (1,351 Total Strata)

A channel-year stratum represents one `(channel_id, year)` combination for the 193 frozen cohort channels across 7 calendar years (193 × 7 = 1,351 strata):

| Stratum Status | Count | Percentage | Definition & Classification |
| :--- | :---: | :---: | :--- |
| **Full Target Sample** | **745** | **55.1%** | Exactly 6 representative videos sampled across temporal bins |
| **Partial Sample** | **74** | **5.5%** | All available videos sampled (1 to 5 uploads in stratum) |
| **Zero Videos: Known Zero** | **63** | **4.7%** | Channel confirmed to have 0 uploads (`NO_VIDEOS`) |
| **Zero Videos: No Eligible Video** | **388** | **28.7%** | Channel debut was after this year (`PLAYLIST_EXHAUSTED` / `CUTOFF_REACHED`) |
| **Zero Videos: Catalog Incomplete** | **81** | **6.0%** | Catalog reached 1,000 video cap before reaching this early year |
| **Total Strata** | **1351** | **100.0%** | Comprehensive cohort longitudinal space |

---

## 4. Stratification by Demographic Groups

### Agency Coverage

| Agency / Group | Total Channels | Sampled Channels | Sampled Videos |
| :--- | :---: | :---: | :---: |
| Independent | 113 | 109 | 2,845 |
| Algorhythm Project | 33 | 33 | 812 |
| Pixela Project | 21 | 21 | 522 |
| Lumina Live | 9 | 9 | 204 |
| Virtual Zeven (VZ) | 5 | 5 | 110 |
| RPG | 3 | 1 | 1 |
| AStars Production | 2 | 2 | 27 |
| Euphora Project | 2 | 2 | 48 |
| Flora Project | 2 | 0 | 0 |
| Polygon Official | 1 | 1 | 24 |
| Ti19t | 1 | 1 | 37 |
| WACTOR | 1 | 0 | 0 |

### Subscriber Tier Coverage

| Tier | Total Channels | Sampled Channels | Sampled Videos |
| :--- | :---: | :---: | :---: |
| A | 73 | 72 | 1,867 |
| B | 61 | 57 | 1,399 |
| C | 8 | 5 | 89 |
| D | 1 | 1 | 1 |
| S | 50 | 49 | 1,274 |

### Lifecycle Status Coverage

| Lifecycle Status | Total Channels | Sampled Channels | Sampled Videos |
| :--- | :---: | :---: | :---: |
| active | 139 | 139 | 3,816 |
| hiatus | 33 | 33 | 601 |
| graduated | 12 | 8 | 117 |
| unknown | 9 | 4 | 96 |

---

## 5. Methodological Assurances & Integrity

1. **Deterministic Reproducibility:** Repeated execution of the manifest builder produces the exact same `(channel_id, video_id)` set verified by SHA-256 hash assertions.
2. **Zero T1 Mutation:** The frozen T1 catalog (`video_catalog.parquet`, `channel_coverage.parquet`, `target_manifest.csv`) was strictly read-only and preserved bit-for-bit.
3. **Absence != Zero Audience:** Strata with 0 observations are categorized explicitly into `KNOWN_ZERO`, `NO_ELIGIBLE_VIDEO`, or `CATALOG_INCOMPLETE`.
4. **Longitudinal Span:** Samples span from the earliest 2020 Thai VTuber community foundations through to 2026 YTD.
