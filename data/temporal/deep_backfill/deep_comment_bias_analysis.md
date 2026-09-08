# Phase T6: Deep Comment History & Bias Correction Analysis

- **Generated at:** 2026-09-08 06:32:40 UTC
- **Target Population:** All 226 Partial-Capture Historical Videos from Phase T5
- **Scope:** Exhaustive Pagination of Top-Level Comment Threads (`nextPageToken` loop)
- **Dataset Maturity:** Deep Historical Sampling Bias Correction Complete

---

## 1. Executive Summary & Core Empirical Findings

In Phase T5, the 100-comment ceiling caused recent-comment truncation bias on high-engagement videos. By exhaustively paginating all remaining comments across all 226 target videos, Phase T6 recovered substantial historical audience evidence that was previously truncated:

- **Unique Viewer Observations:** Increased from **21,708** to **64,504** (+**42,796** unique viewer-video observations, a **+197.1%** increase).
- **Older Comments Recovered:** In **164** out of 226 videos (**72.6%**), comments older than the shallow T5 boundary were uncovered.
- **Earliest Interaction Shift:** On average, the earliest observed comment date was pushed back by **46.7 days** per video.

---

## 2. Temporal Metrics Comparison by Calendar Year

| Calendar Year | Target Videos | T5 Shallow Viewers | T6 Deep Viewers | Viewer Gain (%) | Videos with Older Evidence Recovered | Mean Earliest Shift (Days) | Mean Temporal Span Expansion |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2020** | 20 | 1,913 | 6,868 | **+259.0%** | 14 / 20 (70.0%) | +228.4 d | +227.6 d |
| **2021** | 40 | 3,872 | 8,860 | **+128.8%** | 30 / 40 (75.0%) | +21.9 d | +17.4 d |
| **2022** | 22 | 2,048 | 9,088 | **+343.8%** | 17 / 22 (77.3%) | +108.1 d | +107.9 d |
| **2023** | 37 | 3,521 | 15,386 | **+337.0%** | 32 / 37 (86.5%) | +47.3 d | +46.6 d |
| **2024** | 34 | 3,313 | 7,188 | **+117.0%** | 20 / 34 (58.8%) | +20.9 d | +15.4 d |
| **2025** | 46 | 4,416 | 11,085 | **+151.0%** | 33 / 46 (71.7%) | +5.7 d | +3.9 d |
| **2026** | 27 | 2,625 | 6,029 | **+129.7%** | 18 / 27 (66.7%) | +0.3 d | +0.3 d |

> [!NOTE]
> `Mean Earliest Shift` measures how many days earlier the oldest comment interaction timestamp moved as a result of deep pagination.
> `Temporal Span Expansion` measures the increase in duration between the earliest and latest recorded comment for each video.

---

## 3. Top 10 High-Impact Deepened Videos

The videos that benefited most significantly from full comment pagination:

| Year | VTuber Channel ID | Video ID | T5 Viewers | T6 Viewers | Gain (x) | Earliest Comment Shift | Total Comments Paginated |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 2022 | `UCompe4fS2oUss8C...` | `oEOHgyuLgrA` | 96 | **3,824** | **39.8x** | +0.0 days | 3,824 |
| 2023 | `UCrIs26bEKOvA_lR...` | `qRCDtZZfmHo` | 91 | **3,115** | **34.2x** | +364.0 days | 3,115 |
| 2020 | `UC0Ky1U__7T2Z5SO...` | `l2AmVo5rbdE` | 96 | **1,870** | **19.5x** | +2139.3 days | 1,870 |
| 2023 | `UCompe4fS2oUss8C...` | `Gct3vVD5FB0` | 94 | **1,670** | **17.8x** | +839.2 days | 1,670 |
| 2025 | `UCC4Wb_x57Ks43GR...` | `UiOUOWDd3TM` | 96 | **1,572** | **16.4x** | +0.0 days | 1,572 |
| 2022 | `UCompe4fS2oUss8C...` | `2a6wLpArdzg` | 92 | **1,228** | **13.3x** | +15.2 days | 1,228 |
| 2023 | `UCrIs26bEKOvA_lR...` | `FdcY-pQW45A` | 94 | **1,222** | **13.0x** | +152.6 days | 1,222 |
| 2026 | `UCpGtwNmbOtgmcKI...` | `ngEBOlB3fDU` | 96 | **1,120** | **11.7x** | +0.1 days | 1,120 |
| 2023 | `UCNTEr2_96vJnXNa...` | `XXwGjoaL3-M` | 91 | **1,015** | **11.2x** | +281.0 days | 1,015 |
| 2023 | `UCmg0gZHGn-zuq1J...` | `_izxVoShzVA` | 95 | **940** | **9.9x** | +1.1 days | 940 |

---

## 4. Methodological & Scientific Bounds

1. **Measured Empirical Scope:** These measurements document the precise difference between a 100-comment ceiling and full `commentThreads` exhaustion across the 226 target videos.
2. **Truncation Boundary Removal:** The 100-comment truncation boundary was removed for the 226 exhaustively paginated T6 target videos. YouTube's native moderation and user deletions still mean unmoderated or deleted historical comments cannot be recovered.
3. **Explicit Source Provenance Precedence:** In snapshot construction, explicit source provenance precedence (`T6 deep > T5 stratified > T2 pilot > legacy`) excludes lower-priority comment rows for the same video, verified by regression tests.
4. **Zero PII Exposure:** All analysis was performed on irreversibly pseudonymized `viewer_hash` tokens. All audited surfaces conform to configured privacy checks.
