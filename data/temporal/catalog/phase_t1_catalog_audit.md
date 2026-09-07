# Historical Catalog Audit Report (Phase T1)

**Audit Execution Timestamp:** 2026-09-07 18:25:29 UTC  
**Target Cohort:** Tier S, Tier A, Top Tier B, and Graduated VTubers  
**Output Directory:** `C:\Users\Icezaza\Documents\GitHub\ThaiVtuberSNA\data\temporal\catalog`  

---

## 1. Executive Summary & Verification Matrix

| Metric | Result | Target / Standard | Status |
| :--- | :--- | :--- | :--- |
| **Target Channels in Cohort** | **193** channels | 180–200 channels | PASS |
| **Channels Cataloged** | **193** / 193 | 100% of target cohort | PASS |
| **Total Videos Cataloged** | **96,420** videos | Scaled historical inventory | PASS |
| **Channels Hitting 1k Cap** | **28** channels | 1,000 video boundary enforced | PASS |
| **Channels Complete to 2020** | **20** channels | 2020-01-01 boundary reached | PASS |
| **Channels Playlist Exhausted** | **136** channels | Exhausted down to first upload | PASS |
| **Oldest Video Across Network** | `2020-01-01` | Historical depth | PASS |
| **Newest Video Across Network** | `2026-09-07` | 2026 YTD | PASS |
| **Total API Calls (1 unit/call)** | **2,015** requests | $\le 4,000$ quota units | PASS |
| **Total Quota Used** | **2,015** units | Daily limit: 10,000 units | PASS |

---

## 2. Mathematical Year Coverage (% Provably Complete)

$$\text{Year Coverage }(Y) = \frac{\sum_{c \in \text{Cohort}} \mathbb{I}(\text{Channel } c \text{ is provably complete throughout year } Y)}{|\text{Cohort}|}$$

| Year | Provably Complete Channels | Target Cohort | Year Coverage % | Status |
| :---: | :---: | :---: | :---: | :--- |
| **2020** | 165 | 193 | **85.5%** | Developing |
| **2021** | 166 | 193 | **86.0%** | Developing |
| **2022** | 168 | 193 | **87.0%** | Developing |
| **2023** | 176 | 193 | **91.2%** | Complete |
| **2024** | 183 | 193 | **94.8%** | Complete |
| **2025** | 191 | 193 | **99.0%** | Complete |
| **2026 YTD (through 2026-09-08)** | 193 | 193 | **100.0%** | Complete |

---

## 3. Channel Termination Breakdown

- **CAP_REACHED (1,000 videos):** 28 channels
- **CUTOFF_REACHED (Reached 2020-01-01):** 20 channels
- **PLAYLIST_EXHAUSTED (All uploads cataloged):** 136 channels
- **NO_VIDEOS (Zero uploads):** 9 channels
- **FAILED / PARTIAL_ERROR:** 0 channels

---

## 4. Architectural & Privacy Compliance

- [x] **Zero videos.list Calls:** Catalog uses strictly `playlistItems.list(part='snippet,contentDetails')` (1 unit per request).
- [x] **contentDetails.videoPublishedAt:** Extracted actual video publish dates; NULLs preserved without `now()` fallback.
- [x] **Atomic Page Checkpoints:** Data pages written to parquet prior to token advancement; resume idempotency verified.
- [x] **Target Manifest Frozen:** Active, Hiatus, and Graduated VTubers locked before crawling.