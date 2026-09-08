# Phase T5 Temporal Backfill Quality & Diagnostics Report

- **Generated at:** 2026-09-08 06:32:34 UTC
- **Cohort Scope:** Frozen T1 Research Cohort (193 VTuber Channels)
- **Sampling Manifest:** 4,630 videos (deterministic SHA-256 hash ranking; first-ranked candidate per temporal bin)
- **Dataset Stage:** `historical_stratified_backfill_complete` (100% Terminal Execution)

---

## 1. Data Provenance & Evidence Sources

This longitudinal network unifies newly captured Phase T5 stratified historical comments with pre-existing pilot and legacy evidence. All numbers below are explicitly broken down by provenance to avoid confounding new backfill data with older artifacts.

| Evidence Layer | Parquet Sources | Dated Interactions | Unique Viewer Hashes | Channels Represented | Videos Represented | Primary Scope |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **T6 Deepened Comments** | 226 | 64,504 | 53,612 | 71 / 193 | 226 | Exhaustively paginated comments for high-engagement historical videos |
| **T5 Stratified Backfill** | 3,675 | 66,167 | 45,844 | 180 / 193 | 3,675 | Bi-monthly stratified historical comment backfill (2020–2026) |
| **Legacy / T2 Pilot** | 567 | 6,276 | 3,990 | 19 / 193 | 617 | T2 comment pilot (60 videos) + legacy live-chat / comment archives |
| **Unified Temporal Network** | 4,468 | 114,869 | 79,718 | 190 / 193 | 4,260 | Combined evidence powering the final temporal snapshots & time slider |

---

## 2. Sampling Manifest Completeness by Year (T5-E Gate)

Every single sampling job in the 4,630-video manifest was executed to an authoritative terminal state. No jobs remain pending or retryable.

| Year | Manifest Videos | Terminal Completed | Completed with Comments | No Comments | Disabled | Unavailable / Failed | Pending | Completeness Rate |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2020 | 164 | 164 | 133 | 24 | 7 | 0 | 0 | **100.0%** |
| 2021 | 383 | 383 | 327 | 55 | 1 | 0 | 0 | **100.0%** |
| 2022 | 576 | 576 | 441 | 129 | 6 | 0 | 0 | **100.0%** |
| 2023 | 788 | 788 | 622 | 157 | 9 | 0 | 0 | **100.0%** |
| 2024 | 930 | 930 | 762 | 157 | 11 | 0 | 0 | **100.0%** |
| 2025 | 962 | 962 | 778 | 179 | 5 | 0 | 0 | **100.0%** |
| 2026 | 827 | 827 | 612 | 210 | 5 | 0 | 0 | **100.0%** |

> [!NOTE]
> Terminal completion includes `COMPLETED` (comments successfully extracted), `NO_COMMENTS` (verified empty comment section), and `COMMENTS_DISABLED` (verified publisher disabled). All represent valid, terminal scientific observations.

---

## 3. Longitudinal Interaction Evidence by Year

The table below details annual evidence for the **Unified Temporal Network**, with T5-only video and channel contributions shown for comparison.

| Year | Unified Channels | T5 Channels | Unified Videos | T5 Videos | Unique Viewers (Unified) | Pairwise Edges | Strong Overlap Edges | Median Audience / Ch | Median Videos / Ch | Sampling Completeness |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2020 | 29 / 193 | 28 / 193 | 141 | 121 | 5,232 | 72 | 6 | 39 | 5 | 100.0% |
| 2021 | 72 / 193 | 72 / 193 | 507 | 378 | 11,259 | 625 | 98 | 57.0 | 6.0 | 100.0% |
| 2022 | 101 / 193 | 100 / 193 | 701 | 589 | 12,005 | 965 | 121 | 36 | 5 | 100.0% |
| 2023 | 141 / 193 | 140 / 193 | 983 | 844 | 18,646 | 1,503 | 127 | 43 | 6 | 100.0% |
| 2024 | 166 / 193 | 166 / 193 | 1237 | 1136 | 13,478 | 2,547 | 690 | 35.0 | 6.0 | 100.0% |
| 2025 | 173 / 193 | 173 / 193 | 1366 | 1228 | 17,119 | 3,168 | 613 | 36 | 6 | 100.0% |
| 2026 | 176 / 193 | 165 / 193 | 1120 | 1010 | 13,259 | 1,997 | 275 | 23.0 | 6.0 | 100.0% |

> [!NOTE]
> `Strong Overlap Edges` count channel pairs connected by commenters seen across $\ge 2$ distinct videos in both channels within that year.

---

## 4. Temporal Network Stability & Dynamic Transitions

Dynamic transitions between adjacent calendar years measure the continuity of audience co-presence in the unified network.

| Year-over-Year | Prior Year Edges | Next Year Edges | Persisting Edges | Edge Births | Edge Disappearances | Persistence Rate |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2020 -> 2021 | 72 | 625 | 34 | 591 | 38 | 47.2% |
| 2021 -> 2022 | 625 | 965 | 268 | 697 | 357 | 42.9% |
| 2022 -> 2023 | 965 | 1,503 | 383 | 1,120 | 582 | 39.7% |
| 2023 -> 2024 | 1,503 | 2,547 | 703 | 1,844 | 800 | 46.8% |
| 2024 -> 2025 | 2,547 | 3,168 | 1,339 | 1,829 | 1,208 | 52.6% |
| 2025 -> 2026 | 3,168 | 1,997 | 1,120 | 877 | 2,048 | 35.4% |

> [!IMPORTANT]
> Edge persistence measures observed commenter co-presence across adjacent calendar years.
> A disappearing edge reflects absence of observed co-commenters in the stratified sample, not definitive audience estrangement.

---

## 5. Observed Viewer Retention & Migration Evidence

Longitudinal engagement and migration metrics separated by data provenance layer:

| Analytical Metric | T5-Only Stratified Backfill | Legacy / T2 Pilot | Unified Temporal Network | Analytical Definition |
| :--- | :---: | :---: | :---: | :--- |
| **Total Observed Pseudonymous Viewers** | **45,844** (100%) | **3,990** (100%) | **79,718** (100%) | Unique `viewer_hash` with dated interaction evidence |
| **Cross-Channel Migration Evidence** | **5,664** (12.4%) | **407** (10.2%) | **9,694** (12.2%) | Observed commenting on $\ge 2$ distinct VTuber channels |
| **Long-Term Engagement ($\ge 3$ Years)** | **1,298** (2.8%) | **44** (1.1%) | **2,047** (2.6%) | Observed commenting across $\ge 3$ distinct calendar years |
| **Adjacent-Year Channel Retention** | **1,927** (4.2%) | **139** (3.5%) | **3,145** (3.9%) | Observed in the *same* channel across adjacent years ($t$ and $t+1$) |

> [!CAUTION]
> These statistics represent **observed interaction evidence** within the stratified comment sample.
> They MUST NOT be interpreted as exhaustive audience retention or total fan migration.

---

## 6. Automated Coverage Diagnostics & Warnings

| Year | Active Flags | Sampled Videos | Channel Coverage | Status Assessment |
| :---: | :--- | :---: | :---: | :--- |
| 2020 | `LOW_CHANNEL_COVERAGE` | 141 | 29 / 193 | ⚠️ Sparse sample — interpret cautiously |
| 2021 | `ADEQUATE` | 507 | 72 / 193 | ✅ Broad multi-channel coverage |
| 2022 | `ADEQUATE` | 701 | 101 / 193 | ✅ Broad multi-channel coverage |
| 2023 | `ADEQUATE` | 983 | 141 / 193 | ✅ Broad multi-channel coverage |
| 2024 | `ADEQUATE` | 1237 | 166 / 193 | ✅ Broad multi-channel coverage |
| 2025 | `ADEQUATE` | 1366 | 173 / 193 | ✅ Broad multi-channel coverage |
| 2026 | `ADEQUATE` | 1120 | 176 / 193 | ✅ Broad multi-channel coverage |

### Diagnostic Rules:
- **`LOW_SAMPLE`**: Fewer than 50 videos sampled in the annual slice.
- **`LOW_CHANNEL_COVERAGE`**: Fewer than 30 channels with dated interaction evidence.
- **`HIGH_PARTIAL_CAPTURE`**: Over 25% of videos reached the 100-comment collection cap.

---

## 7. Methodological & Privacy Bounding

1. **Stratified Sampling Scope:** The dataset is composed of bi-monthly stratified video samples (~6 videos/channel/year) capped at 100 comments/video. It is not an exhaustive archive of all comments or video streams.
2. **Strict Interaction Timing:** All temporal allocations use verified comment timestamps (`interaction_at`). Video upload timestamps are never substituted.
3. **Zero PII Exposure:** All viewer identities are irreversibly pseudonymized via persistent HMAC-SHA256 immediately inside local extraction memory. Zero display names, commenter profile URLs, or comment texts are persisted.
4. **Non-Inference of Zeroes:** Missing edges indicate lack of observed sample co-occurrence, not verified absence of shared viewers.
5. **Audited Privacy Boundary:** All audited current persisted surfaces passed the configured privacy checks.
