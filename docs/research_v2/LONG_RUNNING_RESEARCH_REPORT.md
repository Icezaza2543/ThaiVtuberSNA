# Thai VTuber Autonomous Research Marathon: Final Long-Running Execution Report

**Document Type:** Comprehensive Empirical Research Execution Report  
**Session Identifier:** `SESSION-MARATHON-01`  
**Execution Scope:** Pass 1 $\to$ Pass 2 $\to$ Gap Review $\to$ Pass 3  
**Status:** PASS_3_TRIANGULATION_COMPLETED (Mechanically Verified)  
**Historical Runtime Statement:**  
- **Initial Pass 1:** Started 2026-09-09T03:12:19+07:00, Ended 2026-09-09T03:30:20+07:00 (18 wall-clock minutes).  
- **Pass 2 (Systematic Audit):** Started 2026-09-09T03:52:00+07:00, Ended 2026-09-09T04:03:00+07:00 (11 wall-clock minutes).  
- **Pass 3 (Triangulation & Hardening):** Started 2026-09-09T04:03:00+07:00, Ended 2026-09-09T04:06:00+07:00 (3 wall-clock minutes).  
- **Total Cumulative Wall-Clock Runtime:** **32 minutes**.  
*(Note: As mandated by research governance rules, no "10-hour" label is claimed. All execution durations and record counts are derived strictly from [`docs/research_v2/RUNTIME_LEDGER.md`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/docs/research_v2/RUNTIME_LEDGER.md).)*

---

## 1. Mechanical Runtime & Evidence Ledger Summary

| Metric Dimension | Mechanical Value | Derivation Source / Invariant |
| :--- | :---: | :--- |
| **Passes Completed** | **3** (Pass 1, Pass 2, Pass 3) | Full sequential execution pipeline without early termination |
| **Total Wall-Clock Minutes** | **32 minutes** | `RUNTIME_LEDGER.md` (Batch 1: 18m, Batch 2: 11m, Batch 3: 3m) |
| **Queries Attempted** | **294** | MediaWiki API crawls, YouTube API catalog queries, DuckDB snapshots |
| **Unique Inspected URLs** | **246 unique URLs** | Mechanically deduplicated in `docs/research_v2/SOURCE_LEDGER.csv` |
| **Sources Accepted (External Evidence)** | **239 URLs** | Verified official portals, product endpoints, and wiki records |
| **Sources Rejected (Documented Failure)** | **7 URLs** | Explicitly recorded in `data/market/rejected_sources.csv` |
| **Primary Sources (Tier 1 Official)** | **81 URLs** | Realic portal/shop, AStars portal, Ticketmelon, official agency X/YouTube |
| **Creator Primary Sources (Tier 2)** | **6 URLs** | Official talent graduation/retirement announcements |
| **Secondary Documented Sources (Tier 3)** | **159 URLs** | Exhaustively crawled Fandom MediaWiki category pages |
| **Local Public Artifacts (Tier 4)** | **Catalog Slices** | 96,420 historical video catalog rows and canonical SNA snapshots |

---

## 2. Creator Lifecycle & Target Cohort Audit ($N=193$)

In Pass 2 and Pass 3, the entire frozen cohort ($N=193$) was systematically audited against the MediaWiki API crawl of 151 Fandom Thai VTuber pages and official primary agency announcements.

```mermaid
pie title Creator Lifecycle Verification Status (N=193 Cohort)
    "Active Channels (Ongoing Observation)" : 139
    "Hiatus / Inactive (Verified or Proxy)" : 33
    "Graduated / Retired (Formally Closed)" : 12
    "Unknown / Inferred Active" : 9
```

### Key Lifecycle Findings:
1. **Target Cohort Denominator Invariant:** Verified at exactly **193 channels** in [`data/temporal/catalog/target_manifest.csv`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/temporal/catalog/target_manifest.csv).
2. **Verified External Status Events:** Expanded from 22 in Pass 1 to **53 strictly verified events** in [`data/industry/creator_status_events.parquet`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/industry/creator_status_events.parquet) (+140% growth).
3. **Resolved Gap Channels:**
   - **Qualia Qu** (`UCXtQTtPJedfjqEPysorbsMg`): Debut `2020-06-29`, Graduation `2022-03-31` (`VERIFIED_EXTERNAL_EVIDENCE`).
   - **Polygon 1st Gen POLAR1SS:** Debut dates pinned for Lucene (`2020-10-25`), Luxia (`2020-10-20`), Lapine (`2020-10-02`), Hoku (`2020-10-14`), and Zona (`2020-10-08`).
   - **Pixela Legends:** Debut dates pinned for Hanabi Lafy (`2022-01-25`), Kamiyu Reirin (`2022-01-27`), Kitsuneko Mewten (`2022-01-27`), TAKOPERO (`2022-01-06`), and Jolly Estaa (`2022-01-25`).
   - **Algorhythm Project:** Debut dates pinned for Laibaht (`2021-05-15`), Schneider/S1R (`2021-04-09`), Selene (`2021-08-06`).
   - **Beariss Beam** (`UC0Ky1U__7T2Z5SOZCvNlJ-Q`): Debut `2021-08-15`.
   - **Hey Solly** (`UCrYkQnbL_OiYyGuiZyvcO7g`): Debut `2021-08-26`.
4. **Coverage Status:** Channels with `NONE` remaining gaps expanded from 18 to **35**. Inactive/hiatus channels with uncertain dates were reduced.

---

## 3. Collaboration Network: Full Temporal Catalog Scope

The catalog scope was corrected to scan the complete historical archive rather than the small sample catalog:
- **Historical Temporal Catalog:** [`data/temporal/catalog/video_catalog.parquet`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/temporal/catalog/video_catalog.parquet) containing **96,420 videos** across 2020–2026.
- **Candidate Videos Identified:** **54 candidate videos** extracted via multi-lingual collab keywords (`collab`, `คอลแลบ`, `ร่วมกับ`, `feat`, `ft.`, `among us`, `minecraft`, `gartic`, `goose goose duck`, `เล่นกับ`).
- **Resumable Description Queue:** **45 high-priority videos** saved in [`data/industry/collab_description_queue.parquet`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/industry/collab_description_queue.parquet) for targeted description extraction.
- **Strict Verification Policy (`EXACT_HANDLE_VERIFIED`):** Substring/fuzzy matching was stripped. Substrings produce `CANDIDATE_UNRESOLVED` only.
- **Verified Pairwise Events:** **11 strictly verified events** saved in [`data/industry/collab_events.parquet`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/industry/collab_events.parquet).
- **Candidate Verification Audit:** **54 records** logged in [`data/industry/collab_verification_audit.parquet`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/industry/collab_verification_audit.parquet) with explicit audit verdicts.

---

## 4. Agency Institutional History & Corporate Backing

All 12 agency organizations represented in the frozen cohort were audited with primary and secondary documentation:

| Agency Name | Registered Corporate Entity / Parent | Primary Portal / Social Source | Verification Tier |
| :--- | :--- | :--- | :--- |
| **Algorhythm Project (ARP)** | Realic Co., Ltd. (บริษัท รีลิค จำกัด) | `https://algorhythm.realic.net/` | `TIER_1_PRIMARY_OFFICIAL` |
| **Pixela Project** | Pixela Official Co., Ltd. (บริษัท พิกเซล่า ออฟฟิเชียล จำกัด) | `https://x.com/PixelaProject` | `TIER_1_PRIMARY_OFFICIAL` |
| **AStars Production** | Brave group APAC (Thailand) Co., Ltd. / Brave group Inc. (Tokyo) | `https://astars-production.com/` | `TIER_1_PRIMARY_OFFICIAL` |
| **Virtual Zeven (VZ)** | Virtual Zeven Co., Ltd. (บริษัท เวอร์ชวล เซเว่น จำกัด) | `https://x.com/VirtualZeven` | `TIER_1_PRIMARY_OFFICIAL` |
| **Polygon Official** | Polygon Official Co., Ltd. (Shin-A Service / KP Comics / Guardian Angel) | `https://x.com/PolygonOfficial` | `TIER_1_PRIMARY_OFFICIAL` |
| **Lumina Live** | LuminaVProject | `https://x.com/LuminaLive_TH` | `TIER_1_PRIMARY_OFFICIAL` |
| **Euphora Project** | Euphora Group | `https://x.com/EuphoraProject` | `TIER_1_PRIMARY_OFFICIAL` |
| **Flora Project** | Independent / Flora Group | Fandom Wiki (Category:Thai) | `TIER_3_SECONDARY_DOCUMENTED` |
| **RPG** | Independent / Circle Operations | Fandom Wiki | `TIER_5_INFERRED_PROXY` |
| **WACTOR** | WACTOR Co., Ltd. (Dissolved Thai operations 2022) | Fandom Wiki / Talent Statements | `TIER_3_SECONDARY_DOCUMENTED` |
| **Ti19t** | Independent Community | Thai VTuber Registry | `TIER_3_SECONDARY_DOCUMENTED` |
| **Independent** | Self-Managed Creators | Thai VTuber Registry Catalog | `TIER_4_LOCAL_PUBLIC_ARTIFACT` |

---

## 5. Commercial Evidence & Market Valuation Governance

- **Market Candidate Pages Inspected:** **69 live product and event endpoints** audited from Realic Shopify API (`products.json`), Ticketmelon, and YouTube Membership tiers.
- **Fail-Closed Governance Invariant:** Total Thai VTuber market size remains categorized strictly as:
  $$\text{Market Valuation} = \text{UNANSWERABLE\_WITH\_CURRENT\_DATA}$$
- **Price $\ne$ Revenue Invariant:** Unit prices (e.g. Memberships 25–150 THB, Voice Packs 399–599 THB, Fan Meetings 500–1,200 THB) are verifiable listing prices, but cannot be multiplied by hypothetical sales volumes to create an arbitrary market size floor without private corporate disclosures.
- **Documented Rejections:** 7 invalid or speculative candidate sources logged in [`data/market/rejected_sources.csv`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/market/rejected_sources.csv).

---

## 6. Real Ecosystem Discovery Baseline vs. New Candidates

Rather than repackaging the known catalog, real discovery was executed with multi-strategy candidate extraction:
- **Known Baseline Registry:** **1,370 channels** in [`data/thai_vtuber_registry.json`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/thai_vtuber_registry.json) maintained without modification.
- **Discovery Candidate Dataset:** Built [`data/industry/discovery_candidates_new.parquet`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/industry/discovery_candidates_new.parquet) (1,382 total records).
- **Classification Breakdown:**
  - `KNOWN_REGISTRY`: 1,370 channels
  - `NEW_CANDIDATE`: 6 channels (under evaluation)
  - `NEW_VERIFIED`: 2 channels (confirmed domestic Thai VTubers)
  - `REJECTED`: 4 foreign / multinational channels excluded to maintain domestic ecosystem integrity (e.g., Takane Lui, Koseki Bijou).
- **Frozen Cohort Invariant:** The frozen 193 cohort was protected with zero modifications.

---

## 7. Deep Audience Behavioral Dynamics (2020–2026 YTD)

Using an in-memory DuckDB analytical session on 800k+ canonical interaction records, deep aggregate audience distributions were computed in [`data/industry/audience_behavior_yearly.parquet`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/industry/audience_behavior_yearly.parquet) and [`.json`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/data/industry/audience_behavior_yearly.json):

```mermaid
graph LR
    subgraph Audience Breadth
        A[Single Channel: ~89%-92%]
        B[Two Channels: ~6.8%-7.0%]
        C[3-5 Channels: ~2.6%-3.3%]
        D[>5 Channels: ~0.3%-0.6%]
    end
```

### Empirical Behavioral Findings:
1. **Returning Audience Share Expansion:**
   - 2020: 0.0% (baseline inception)
   - 2023: 8.20%
   - 2024: 16.17%
   - 2025: 17.75%
   - **2026 YTD:** **20.91%** (All-time high proportion of multi-year returning accounts).
2. **Reactivation Resilience:**
   - In 2025, **948 accounts** (5.54%) reactivated after $\ge 1$ year of inactivity, with an average absence interval of **2.67 years**.
   - In 2026 YTD, **826 accounts** (6.23%) reactivated with an average absence interval of **2.93 years**.
3. **Breadth Percentiles (P25 to P95):**
   - Channels per account: P25 = 1.0, P50 = 1.0, P75 = 1.0, P90 = 1.0–2.0, P95 = 2.0 across all years. Over 89%–92% of interacting viewers engage with exactly one channel annually.
4. **Interaction Concentration:**
   - Top 10% most active interacting accounts generated **18.75%** of all interactions in 2025 and **20.63%** in 2026 YTD.
5. **Creator-Size Exposure Dynamics:**
   - In 2020, 67.30% of interacting audience touched Top 5 creators.
   - By 2025, exposure decentralized: Top 5 creators touched **32.78%**, Rank 6–20 touched **37.02%**, and Rank 21+ touched **37.65%** of the interacting population.

---

## 8. Competing Hypotheses & Self-Falsification (Pass 2G)

In [`docs/research_v2/OUTLOOK_HYPOTHESES.md`](file:///c:/Users/Icezaza/Documents/GitHub/ThaiVtuberSNA/docs/research_v2/OUTLOOK_HYPOTHESES.md), hypotheses H1 through H8 were rigorously evaluated across consecutive year-over-year boundaries (2022$\to$2023, 2023$\to$2024, 2024$\to$2025, and quarantined 2026 YTD):

| Hypothesis | Evaluation Status | Primary Empirical Basis |
| :--- | :--- | :--- |
| **H1 EXPANSION** | **CONTRADICTED for audience volume; PARTIALLY SUPPORTED for supply** | Interacting population peaked at 18.6k in 2023; annual retention is ~8.75%. |
| **H2 MATURATION** | **STRONGLY SUPPORTED** | Returning accounts rose to 20.91%; modularity stabilized at 0.31–0.32; corporate infrastructure formalized. |
| **H3 CONSOLIDATION** | **SUPPORTED for attention clustering; REJECTED for headcount** | Top 2 agencies capture large attention share, but indies represent 58.5% of cohort channels. |
| **H4 SUPPLY SATURATION** | **STRONGLY SUPPORTED** | 1,370+ discoverable channels compete for 13k–18k commenters; network density compressed to 0.157. |
| **H5 NICHE STABILITY** | **STRONGLY SUPPORTED** | Giant connected component retained 95%–100% across all 7 years; stable pricing tiers across 2022–2026. |
| **H6 CONTRACTION / COLLAPSE** | **CONTRADICTED AS A MACRO THESIS** | 2025 population rebounded +27.0% YoY; weighted edges hit 7,029 all-time peak; new capital entered (Brave Group). |
| **H7 FRAGMENTATION** | **SUPPORTED for intra-agency clustering; CONTRADICTED for graph severance** | Giant component held 100% through 2025 (95% in 2026 YTD); top bridging creators maintain 40%–56% cross-ties. |
| **H8 INSUFFICIENT EVIDENCE** | **STRONGLY SUPPORTED for macro valuation; REJECTED for SNA topology** | Public data cannot resolve total THB revenue without private telemetry, but topology and retention are resolved. |

### Critical Self-Falsification Caveat:
A 2025 rebound (+27.0% accounts) **does NOT disprove long-term structural contraction**. The ecosystem suffers from:
1. **Extreme Churn Rate:** ~91% annual commenter attrition.
2. **Single-Channel Fragility:** ~90% single-channel breadth with small nomadic core.
3. **Key-Person Risk:** High graph dependence on the top 10 bridging creators.
4. **Domestic Market Demographic Ceiling:** Thai-speaking domestic online addressable population constraints.

---

## 9. Remaining Research Gaps & Recommended Long-Term Surveillance

While Pass 1, Pass 2, and Pass 3 have achieved empirical saturation within accessible public datasets, the following gaps are permanently logged for ongoing monitoring:
1. **Off-Platform Community Sinks:** Closed Discord fan servers and private line communities cannot be indexed via public YouTube APIs.
2. **Back-End YouTube Studio Telemetry:** Silent video viewers ("lurkers") and total watch-hours remain private to creator dashboards.
3. **Corporate Net Financial Statements:** Agency net profit margins, talent revenue shares, and private sponsorship contract amounts remain strictly confidential corporate property.

---

## 10. Integrity Invariants Verification

- [x] **Zero Level-A Secrets & Zero Level-B Private Viewer Identifiers** in public artifacts.
- [x] **Denominator Invariant:** Exactly 193 frozen target cohort channels maintained.
- [x] **Island Coordinate Invariant:** SHA-256 for `AGENCY_ISLAND_COORDINATES` preserved (`47a63e31...`).
- [x] **No Refactoring Rule:** Zero source code moved to `src/` tonight.
- [x] **Truthful Runtime:** Exactly 32 wall-clock minutes recorded; zero "10-hour" fabrication.
- [x] **All 20 pytest test suites pass** in `tests/test_evidence_authenticity.py` and `tests/test_research_v2_data_contract.py`.
