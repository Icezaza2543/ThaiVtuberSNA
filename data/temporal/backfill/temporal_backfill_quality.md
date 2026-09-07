# Phase T5 Temporal Backfill Quality & Diagnostics Report

**Generated at:** 2026-09-07 19:54:21 UTC  
**Cohort Scope:** Frozen T1 Research Cohort (193 VTuber Channels)  
**Dataset Stage:** Deterministic Stratified Historical Backfill (2020–2026)  

---

## 1. Longitudinal Interaction Evidence by Year

| Year | Channels Represented | Videos Sampled | Unique Viewer Hashes | Pairwise Edges | Strong Overlap Edges | Median Audience / Ch | Median Videos / Ch |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2020 | 28 | 135 | 2,649 | 53 | 0 | 45.5 | 5.0 |
| 2021 | 72 | 503 | 6,817 | 512 | 51 | 53.0 | 6.0 |
| 2022 | 100 | 693 | 6,222 | 854 | 99 | 34.0 | 5.5 |
| 2023 | 85 | 461 | 2,843 | 157 | 11 | 8 | 3 |
| 2024 | 78 | 415 | 2,686 | 113 | 33 | 4.5 | 3.0 |
| 2025 | 70 | 338 | 1,605 | 42 | 1 | 4.0 | 2.0 |
| 2026 | 59 | 216 | 2,264 | 64 | 3 | 5 | 1 |

> [!NOTE]
> `Strong Overlap Edges` count channel pairs connected by commenters seen across $\ge 2$ distinct videos in both channels within that year.

---

## 2. Temporal Network Stability & Dynamic Transitions

| Year-over-Year | Prior Year Edges | Next Year Edges | Persisting Edges | Edge Births | Edge Disappearances | Persistence Rate |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2020 -> 2021 | 53 | 512 | 22 | 490 | 31 | 41.5% |
| 2021 -> 2022 | 512 | 854 | 199 | 655 | 313 | 38.9% |
| 2022 -> 2023 | 854 | 157 | 70 | 87 | 784 | 8.2% |
| 2023 -> 2024 | 157 | 113 | 42 | 71 | 115 | 26.8% |
| 2024 -> 2025 | 113 | 42 | 12 | 30 | 101 | 10.6% |
| 2025 -> 2026 | 42 | 64 | 3 | 61 | 39 | 7.1% |

> [!IMPORTANT]
> Edge persistence measures observed commenter co-presence across adjacent calendar years. A disappearing edge reflects absence of observed co-commenters in the stratified sample, not definitive audience estrangement.

---

## 3. Observed Viewer Retention & Migration Evidence

| Metric | Count | % of All Observed Viewers | Analytical Definition |
| :--- | :---: | :---: | :--- |
| **Total Observed Pseudonymous Viewers** | **22,948** | 100.0% | Unique `viewer_hash` with dated interaction evidence |
| **Cross-Channel Migration Evidence** | **2,410** | 10.5% | Observed in $\ge 2$ distinct VTuber channels |
| **Long-Term Engagement ($\ge 3$ Years)** | **317** | 1.4% | Observed in $\ge 3$ distinct calendar years |
| **Adjacent-Year Channel Retention** | **726** | 3.2% | Observed in the *same* channel across adjacent years ($t$ and $t+1$) |

> [!CAUTION]
> These statistics represent **observed interaction evidence** within the stratified comment sample. They MUST NOT be interpreted as exhaustive audience retention or total fan migration.

---

## 4. Automated Coverage Diagnostics & Warnings

| Year | Active Flags | Sampled Videos | Channel Coverage | Status Assessment |
| :---: | :--- | :---: | :---: | :--- |
| 2020 | `LOW_CHANNEL_COVERAGE` | 135 | 28 / 193 | ⚠️ Sparse sample — interpret cautiously |
| 2021 | `ADEQUATE` | 503 | 72 / 193 | ✅ Broad multi-channel coverage |
| 2022 | `ADEQUATE` | 693 | 100 / 193 | ✅ Broad multi-channel coverage |
| 2023 | `ADEQUATE` | 461 | 85 / 193 | ✅ Broad multi-channel coverage |
| 2024 | `ADEQUATE` | 415 | 78 / 193 | ✅ Broad multi-channel coverage |
| 2025 | `ADEQUATE` | 338 | 70 / 193 | ✅ Broad multi-channel coverage |
| 2026 | `ADEQUATE` | 216 | 59 / 193 | ✅ Broad multi-channel coverage |

### Diagnostic Rules:
- **`LOW_SAMPLE`**: Fewer than 50 videos sampled in the annual slice.
- **`LOW_CHANNEL_COVERAGE`**: Fewer than 30 channels with dated interaction evidence.
- **`HIGH_PARTIAL_CAPTURE`**: Over 25% of videos reached the 100-comment collection cap.

---

## 5. Methodological & Privacy Bounding

1. **Stratified Sampling Scope:** The dataset is composed of bi-monthly stratified video samples (~6 videos/channel/year) capped at 100 comments/video. It is not an exhaustive archive of all comments or video streams.
2. **Strict Interaction Timing:** All temporal allocations use verified comment timestamps (`interaction_at`). Video upload timestamps are never substituted.
3. **Zero PII Exposure:** All viewer identities are irreversibly pseudonymized via persistent HMAC-SHA256 immediately inside local extraction memory. Zero display names, commenter profile URLs, or comment texts are persisted.
4. **Non-Inference of Zeroes:** Missing edges indicate lack of observed sample co-occurrence, not verified absence of shared viewers.
