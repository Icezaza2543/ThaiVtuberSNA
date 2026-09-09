# Pass 2 Empirical Gap Review & Pass 3 Execution Plan

**Document Type:** Research Gap Audit & Prioritized Phase 3 Roadmap  
**Research Session:** `SESSION-MARATHON-01`  
**Completed Pass:** Pass 2 (Systematic Audit Across 7 Workstreams)  
**Status:** PASS_2_COMPLETE $\to$ PASS_3_IN_PROGRESS  
**Generated At:** 2026-09-09T04:03:00+07:00  

---

## 1. Summary of Pass 2 Empirical Achievements

Across Pass 2, all 7 mandated workstreams were executed with strict mechanical derivation and fail-closed epistemic boundaries:

| Workstream | Pass 2 Implementation | Key Output Metric | Epistemic Status |
| :--- | :--- | :--- | :--- |
| **2A: Creator Lifecycle** | Audited all 151 Fandom Thai VTuber pages via MediaWiki API and official primary announcements. | 232 status events (13 PRIMARY_EVENT_SPECIFIC, 40 SECONDARY_DOCUMENTED, 179 INFERRED_PROXY). 35 channels with NONE remaining gap. | Strictly Calibrated (Primary vs Secondary Documented vs Proxy) |
| **2B: Collab Catalog Scope** | Evaluated all 581 title-covered records from historical catalog. Enforced strict no-fuzzy handle matching policy. | 54 candidate videos; 45 queued in `collab_description_queue.parquet`; 11 pairwise events in verified observed collaboration subset. Precision: INSUFFICIENT_EVIDENCE. Catalog recall: INSUFFICIENT_EVIDENCE. | Verified Observed Collaboration Subset |
| **2C: Agency History** | Re-audited all 12 agencies in cohort; attached explicit `verification_tier` to 19 milestone events. Labeled corporate entities as OFFICIAL_BRAND_ENTITY (or INDEPENDENT_COLLECTIVE) with CORPORATE_REGISTRATION_UNVERIFIED (or NOT_APPLICABLE). | 19 agency events (10 PRIMARY_EVENT_SPECIFIC, 8 SECONDARY_DOCUMENTED, 1 INFERRED_PROXY). Generic profile URLs designated PRIMARY_ENTITY_GENERAL (not event evidence). | PRIMARY_EVENT_SPECIFIC (10), SECONDARY (8), PROXY (1) |
| **2D: Market & Ledger** | Mechanically audited 250 unique URLs in `SOURCE_LEDGER.csv` (76 Primary Specific, 15 Primary Entity General, 152 Secondary Documented, 7 Rejected). Maintained fail-closed market size. | 250 unique audited URLs (243 accepted, 7 rejected). Total market valuation: `UNANSWERABLE_WITH_CURRENT_DATA`. | Fail-Closed Compliant |
| **2E: Real Discovery** | Built `discovery_candidates_new.parquet` distinguishing baseline registry from newly discovered candidates. | 1,382 total discovery records (1,370 baseline known, 6 new candidates, 2 new verified, 4 rejected foreign/multinational). | `KNOWN_REGISTRY` vs `NEW_CANDIDATE` |
| **2F: Audience Deep Behavior** | Derived full quantiles (P25, P50, P75, P90, P95), discrete breadth buckets, and exposure for observed commenter/chat participant accounts. | 7 longitudinal yearly records (2020–2026 YTD). Returning account share expanded to 20.91% in 2026 YTD. Top 10% event concentration: 18.75%–20.63%. | Level C Public Aggregate (Zero PII, Interaction != Watching) |
| **2G: Self-Falsification** | Evaluated H1–H8 in `OUTLOOK_HYPOTHESES.md` with consecutive intervals (2022$\to$2023, 2023$\to$2024, 2024$\to$2025, 2026 YTD quarantined) and counter-evidence. | Addressed high churn (~91% turnover of interacting accounts), single-channel breadth (90%), and domestic demographic ceiling (labeled HYPOTHESIS requiring EXTERNAL_EVIDENCE_REQUIRED). | Non-Dogmatic Synthesis |

---

## 2. Ranked Gap List for Pass 3

In compliance with the Anti-Early-Exit mandate, research does not terminate with Pass 2. The remaining empirical gaps are ranked by:
1. **Research Importance** (Impact on core ecosystem conclusions)
2. **Current Evidence Weakness** (Extent of reliance on proxies or secondary sources)
3. **Expected Value of Further Research** (Availability of public corroboration)

```mermaid
graph TD
    A[Pass 2 Empirical Foundation] --> G1[Gap 1: Inactive/Hiatus Creator Primary Verification]
    A --> G2[Gap 2: High-Value Collab Event Triangulation]
    A --> G3[Gap 3: Corporate Registration & Institutional Backing]
    
    G1 --> P3A[Pass 3A: Target 10 Hiatus Channels via Official Creator/Agency Announcements]
    G2 --> P3B[Pass 3B: Description & Participant Resolution for Top 20 Candidates]
    G3 --> P3C[Pass 3C: Legal Entity & Corporate Filing Triangulation]
```

### Rank 1: Inactive & Hiatus Creator Primary-Source Verification (Creator Lifecycle)
- **Importance:** High. Determining whether long-tail cohort creators formally graduated, went on indefinite hiatus, or redebuted affects survival curves and cohort attrition metrics.
- **Evidence Weakness:** 28 creators in the frozen cohort have unconfirmed departure dates and rely on `TIER_5_INFERRED_PROXY` (last observed interaction).
- **Target Channels for Pass 3 Triangulation:**
  - Daisy Daisy VTuber members (e.g. Miu, Yuri, Haru)
  - Polygon Project departed members (e.g. Lucine, Hype, Luxia)
  - Lumina Live departed members (e.g. Ardalita, Mutelu line)
  - Independent pioneer channels with sudden cessation in 2023–2024.
- **Pass 3 Alternate Strategy:** Official Twitter announcement $\to$ YouTube community post / final stream $\to$ archived agency roster notice.

### Rank 2: High-Value Collab Event Triangulation (Collab Dynamics)
- **Importance:** High. Resolving candidate videos into verified co-streaming events powers the non-causal mobility and audience crossover analysis.
- **Evidence Weakness:** 45 candidate videos in `collab_description_queue.parquet` match tournament/collab keywords ("Among Us", "Minecraft", "Gartic", "เล่นกับ") but lack exact handle confirmation in the title alone.
- **Pass 3 Alternate Strategy:** Title keyword candidate $\to$ Video description extraction / stream participant roster $\to$ Official cross-channel schedule image verification $\to$ promote to `EXACT_HANDLE_VERIFIED` or `OFFICIAL_EVENT_METADATA`.

### Rank 3: Institutional Corporate & Legal Entity Triangulation (Agency & Market Infrastructure)
- **Importance:** High. Verifies the thesis of Institutional Maturation (H2) and Consolidation (H3) by examining parent company registrations, international investment (Brave Group APAC), and corporate formalization.
- **Evidence Weakness:** Agency parent companies (Realic Co., Ltd., Pixela Co., Ltd., Virtual Zeven Co., Ltd., Guardian Angel A.I., Brave Group) are documented on Fandom wikis, but specific corporate details (incorporation dates, Japanese parent company press releases, DBD corporate status) have not been directly triangulated.
- **Pass 3 Alternate Strategy:** Fandom mention $\to$ Corporate press releases / PR Times (Brave Group) $\to$ Department of Business Development (DBD) corporate registration entity verification $\to$ promote to Tier 1 Corporate Institutional Record.

---

## 3. Pass 3 Immediate Action Mandate

Pass 3 begins immediately without waiting for user intervention. Work begins on:
1. **Pass 3A:** Resolving priority hiatus and departure announcements for top cohort channels.
2. **Pass 3B:** Enriching descriptions and participant rosters for high-value collab tournament candidates.
3. **Pass 3C:** Documenting official corporate entity profiles for Realic, Pixela, Brave Group APAC, and Virtual Zeven.
