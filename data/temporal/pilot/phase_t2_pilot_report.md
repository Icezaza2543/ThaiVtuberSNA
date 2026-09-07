# Phase T2: Sampled Historical Comment Observations Pilot Report

**Audit Execution Timestamp:** 2026-09-07 19:19:30 UTC

> [!NOTE]
> **Sampling Contract Disclosure:** This report analyzes **sampled historical comment observations** from a representative pilot cohort. It does NOT represent complete or exhaustive historical audience coverage.
> - **Sampling Method:** YouTube Data API `commentThreads.list` (top-level comment sample, up to 100 comments per sampled video)
> - **Pagination:** Single-page sampling (max 100 top-level comments per video)

## 1. Pilot Sample Overview

| Metric | Value |
| :--- | :--- |
| **Videos Sampled** | 51 videos |
| **Comments Collected** | 1,474 comments |
| **Missing Timestamps** | 0 observations |
| **Oldest Interaction Observed** | `2021-06-16 11:48:34 UTC` |
| **Newest Interaction Observed** | `2026-09-07 04:52:22 UTC` |
| **Sampling Method** | Top-level comment sample, up to 100 comments per video |
| **Max Comments Per Video** | 100 |

---

## 2. Interaction Year vs Video Publication Year Matrix (Sampled Pilot)

| Video Year | Total Comments | Same-Year Interaction | Post-Year Interaction | Old-Video Interaction % |
| :---: | :---: | :---: | :---: | :---: |
| **2021** | 186 | 160 | 26 | **14.0%** |
| **2022** | 134 | 132 | 2 | **1.5%** |
| **2023** | 490 | 424 | 66 | **13.5%** |
| **2024** | 164 | 163 | 1 | **0.6%** |
| **2025** | 373 | 322 | 51 | **13.7%** |
| **2026** | 127 | 127 | 0 | **0.0%** |

---

## 3. Empirical Findings from Pilot Sample

- **Empirical Finding:** Historical videos in the sample continue to accumulate comments in later years (up to 14.0% post-year comments observed).
- **Architectural Implication:** Validates that `interaction_at` must never fallback to `video_published_at` or `now()`.
- **Evidence Separation:** Observed commenters are distinct from live chat participants and distinct from total passive viewers.