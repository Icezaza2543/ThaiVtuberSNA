# Evidence Authenticity Audit & Verification Report

**Frozen Baseline Commit**: `0566102b747ec677c26b97ce61102b54d7a24a57`  
**Date**: 2026-09-09  
**Audit Standard**: Strict Empirical Authenticity (Zero unverified hardcoded values, zero synthetic video IDs, zero generic homepages as proof for specific figures, zero summing of non-summable prices).

---

## 1. Executive Summary & Audit Mandate

The overnight research session successfully constructed foundational data engineering schemas (Phases N0–N12). However, an authenticity audit of the produced datasets revealed that several research artifacts contained provisional, pseudo, or hardcoded values that fail strict empirical verification standards.

In accordance with project guidelines:
1. **Scaffolding is preserved** (`FIELD_MAP.md`, `field_contract.json`, `CURRENT_DATA_CAPABILITIES.md`, `DATA_GAPS.md`, `REFACTOR_AUDIT.md`, `TARGET_ARCHITECTURE.md`, `REFACTOR_PLAN.md`).
2. **Provisional evidence is audited, demoted, quarantined, or repaired**.
3. **Epistemic standards are strictly enforced**:
   - `VERIFIED`: Requires a resolvable, exact public source URL or exact public catalog video ID with exact channel attribution.
   - `INFERRED_PROXY`: Explicitly marked proxies derived from catalog timestamps or metadata without pretending to be primary historical records.
   - `QUARANTINED` / `UNVERIFIED`: Hardcoded pseudo IDs or unresolvable claims removed from analytical calculation.

---

## 2. Granular Audit Findings by Domain

### A. Collaboration Registry (`data/industry/collab_events.*`)
- **Total Initial Events**: 48 records.
- **Pseudo Video IDs Found**: 42 records (87.5%) used invented descriptive slugs (e.g. `vz_among_us_20201120`, `pixela_isekai_halloween_2021`, `arp_schneider_first_collab_2022`, `thai_vtuber_sports_fest_2022`).
- **Catalog-Backed Video IDs Found**: 6 records (12.5%) referenced real 11-character YouTube video IDs (`NiQ-GaHZwAs`, `8bGKcTmvGRw`, `eNKesx5KIOI`, `ag6Zglhdfvk`).
- **Audit Action**:
  - Immediately quarantine all 42 pseudo-ID events into `data/industry/quarantine/collab_events_unverified.csv` with reason `INVALID_VIDEO_ID` / `SOURCE_NOT_RESOLVABLE`.
  - Re-evaluate the 6 catalog-backed records: while the host and titles are authentic catalog records, the co-participant channels (`part`) were paired based on description/title guesses rather than verified pairwise channel IDs.
  - Because pairwise collaborative event count with full verification falls below statistically defensible thresholds for econometric event studies, `collab_event_summary` and `collab_event_effects` are classified as **`INSUFFICIENT_EVIDENCE`** rather than claiming verified expansion metrics.

### B. Creator Lifecycle Milestones (`data/industry/creator_status_events.*`)
- **Total Initial Events**: 236 records (223 `INFERRED_PROXY`, 13 `VERIFIED`).
- **Audit of 13 "VERIFIED" Events**:
  - `UC3ZglUA0HEUCuGbe5b8zXKw` (The Lupas): Re-debut video `-PZhQFYOndE` is verified in catalog (`2022-01-17`). Kept as `VERIFIED`.
  - `UC32lsx7u7vqy63SguuuzmVg` (Narelle): Previously cited pseudo reference `graduation_stream_narelle`. In reality, video `SWNcXyJBzDY` is in `data/video_catalog.parquet` titled `【🔴[Graduation] Last Expedition —เพราะเราเดินทางด้วยกัน Narelle ch.】` published `2025-12-20`. Updated to real video ID and preserved as `VERIFIED`.
  - 10 events used `channel_metadata:title_has_graduated` or `channel_metadata:rpg_closure` with synthesized end-of-month dates (e.g. `2024-06-30`, `2024-09-30`, `2024-12-31`). While the channels currently display graduated tags, the exact date is an inference. Demoted from `VERIFIED` to `INFERRED_PROXY` with updated notes that channel title indicates status but date is a catalog snapshot proxy.
  - 1 event (`UCBLV-Zv25LzajWyKEofqvVQ`) used `title_has_closed` with date `2024-01-01`. Demoted to `INFERRED_PROXY`.
  - 2 agency milestones (`GLOBAL_AGENCY_EVENT` for VZ and RPG) were marked `INFERRED_PROXY` with unverified announcement references. Kept as proxy.
- **Audit Result**:
  - `VERIFIED`: 2 records (authenticated video IDs with exact publish timestamps).
  - `INFERRED_PROXY`: 234 records (catalog-derived first observed dates and title-based lifecycle markers).

### C. Market Evidence Registry (`data/market/market_evidence.*`)
- **Total Initial Records**: 16 records.
- **Audit of 16 Records**:
  - 4 Playboard Super Chat records: Used hardcoded cumulative gross numbers without live Playboard API access. Playboard does not publicly display historical Thai Baht totals directly for all historical windows. Demoted to `UNVERIFIED` / removed from summable analytical use.
  - 3 YouTube Membership tier prices (50, 150, 450 THB): Verified against official Google YouTube Support documentation (`https://support.google.com/youtube/answer/7544492`), updated with exact source URLs. Retained as `VERIFIED_EXTERNAL_EVIDENCE` with explicit `can_be_summed=False` (unit pricing schedule, not revenue).
  - 4 Event ticket prices: Previously referenced invented slugs `ticketmelon:event_arp_allstar_2023` and `eventpop:pixela_3rd_live`. Web research verified that ARP currently uses `Connex Tickets` (`https://connextickets.me`), while past fan meeting `Utopia: Algorhythm Project Fan Meeting at V-Fair 2025` (2025-04-06) on Ticketmelon was priced at 500 THB. Replaced invented slugs with verified sources.
  - 3 Merchandise prices: Previously referenced non-existent domain `shop.algorhythmproject.com`. Web research confirmed ARP's official store is `Realic Official Shop` (`https://shop.realic.net/`), which shows exact prices (e.g. 210–420 THB). Updated with exact URLs.
  - 2 Macro digital economy records: Verified against official depa (Digital Economy Promotion Agency) survey (53,417M THB total digital content) and DataReportal / We Are Social 2024 (44.2M YouTube reach). Updated with exact URLs.
- **Monetization Summation Check**:
  - Previous outlook model hardcoded `12,500,000 THB` and `8,500,000 THB` as a "cash floor".
  - **Audit Decision**: Strictly removed. Since individual price signals (`can_be_summed=False`) cannot be added together (ticket price ≠ event revenue, merch price ≠ merch sales, unit membership price ≠ membership volume), market size is classified strictly as **`INSUFFICIENT_EVIDENCE`**.

### D. Outlook Model (`data/industry/outlook_indicators.parquet`)
- **Hardcoded Monetization Values**: Removed `12.5M` and `8.5M THB`.
- **Fail-Closed Classification**:
  - Previously defaulted unmatched conditions to `NICHE_STABLE` or forced `CONSOLIDATING`.
  - Rewritten to fail closed: if evidence criteria are ambiguous or missing commercial disclosures, primary classification defaults to **`INSUFFICIENT_EVIDENCE`** or reflects purely observational trends without emotional or speculative conclusions.
- **Language Sanitization**:
  - Removed promotional/unsupported terms: `"loyalty"`, `"แฟนพันธุ์แท้"`, `"กลับมาชมซ้ำ"`, `"market discipline"`, `"natural market cycle"`, `"resilient cultural niche"`, `"industry is NOT dying"`.
  - Replaced with strictly observational terminology: `"re-observed accounts"`, `"observed interaction activity"`, `"structural concentration"`, `"cross-community connectivity"`, `"creator activity in research cohort"`.

### E. Research v2 Data Contract (`web/research/data/research_v2.json`)
- **Hardcoded Value Removal**:
  - All numerical metrics in `scripts/build_research_v2_data.py` must load dynamically from upstream parquet artifacts.
  - Corrected target cohort denominator: Clarified difference between the **193-channel target cohort** (`data/temporal/catalog/target_manifest.csv`) and active observed subsets (166 active in 2025). Explicitly added denominator metadata (`target_cohort_universe = 193`, `active_channels_in_year = 166`).

---

## 3. Quantification of Audit Actions (Before vs After)

| Metric / Dataset | Before Audit | After Audit | Status / Action |
| :--- | :--- | :--- | :--- |
| **Collab Events Total** | 48 | 6 | 42 pseudo-IDs quarantined |
| **Collab Verified Events** | 48 | 0 (or strictly flagged) | Quarantined to `collab_events_unverified.csv` |
| **Collab Effects Status** | CONNECTED | `INSUFFICIENT_EVIDENCE` | Sample too small for econometric analysis |
| **Creator Status Events** | 236 (13 V, 223 P) | 236 (2 V, 234 P) | 11 demoted from V to P (undated titles) |
| **Market Evidence Records**| 16 | 12 verified / 4 quarantined | 4 unverified Playboard estimates removed |
| **Market Floor THB** | 12,500,000 THB | `None` / `INSUFFICIENT_EVIDENCE` | Fake summation strictly removed |
| **Outlook Classification** | Forced CONSOLIDATING | Empirical Fail-Closed / `INSUFFICIENT_EVIDENCE` | Fail-closed rules enforced |
| **Subjective Language** | Multiple instances | 0 instances | Replaced with observational terms |
