# Research v2 Data Gap Audit & Epistemic Boundaries

> **Document Status**: AUTHORITATIVE POST-OVERNIGHT GAP INVENTORY  
> **Epistemic Principle**: Scientific integrity demands complete transparency regarding what data is known, what is derivable, what requires collection, and what is fundamentally unanswerable from public observational evidence.

---

## 1. Summary of Gaps Solved Tonight (`SOLVED_THIS_RUN`)

The overnight research session successfully engineered and verified 10 major public analytical assets:

1. **Normalized Creator Status Events (`data/industry/creator_status_events.parquet`)**:
   - 236 total lifecycle events (13 verified milestone anchors, 223 proxy observation boundaries).
   - Covers debuts, re-debuts, hiatus boundaries, verified graduations, and agency disbandments across 2020–2026 YTD.
2. **Creator Public Snapshot (`data/industry/creator_public_snapshot.parquet`)**:
   - Standardized profile for all 100 core target cohort channels, distinguishing agencies (Algorhythm Project, Pixela, Polygon, AStars) from independents.
3. **Verified Collaboration Event Registry (`data/industry/collab_events.parquet`)**:
   - 48 verified pairwise collaboration events across 2020–2026 YTD, with traceable video IDs, titles, and verification methods.
4. **Observational Collaboration Effects Model (`data/industry/collab_event_effects.parquet`)**:
   - Quantitative pre/post window analysis measuring shared accounts delta, overlap coefficient delta, and betweenness centrality shifts.
5. **Annual Behavioral Audience Segments (`data/industry/audience_behavior_yearly.parquet`)**:
   - 7 years of k-anonymized aggregate audience dimensions (single vs multi-channel, new vs returning, comment vs live-chat vs mixed modality).
6. **Market & Monetization Evidence Registry (`data/market/market_evidence.parquet` & `source_registry.csv`)**:
   - 16 verified public market signals across 5 evidence classes, with strict `can_be_summed=False` flags and double-count risk disclosures.
7. **Macro Addressable Market Context (`docs/research_v2/MARKET_CONTEXT.md`)**:
   - Platform reach benchmarks (44.2M YouTube reach, 33.8M gamers) clearly separated from observed VTuber community counts.
8. **Market Sizing Model Specification (`docs/research_v2/MARKET_MODEL_SPEC.md`)**:
   - Three-tier economic framework: Observed Floor (~12.5M THB), Structural Sizing (Insufficient Evidence), and Sensitivity Scenarios (Conservative / Base / Upside).
9. **Empirical Ecosystem Outlook Model (`data/industry/outlook_indicators.parquet` & `docs/research_v2/OUTLOOK_MODEL.md`)**:
   - 11-dimension empirical scorecard resolving the "Is the industry dying?" debate into a verdict of **Structural Consolidation (`CONSOLIDATING` / `NICHE_STABLE`)**.
10. **Research v2 Public Aggregate Data Contract (`web/research/data/research_v2.json`)**:
    - Unified JSON contract feeding all 193 slots in `web/research/index_v2.html`, validated by automated tests (`tests/test_research_v2_data_contract.py`).

---

## 2. Derivable After Architectural Refactor (`DERIVABLE_AFTER_REFACTOR`)

These items require no new external evidence, but await cleaner backend abstractions:

| Gap / Capability | Dependency | Refactor Phase | Target Location |
|---|---|---|---|
| **Unified Catalog Store** | Consolidates target manifest, registry CSV, and Google Sheets `VTUBERS` tab | Phase R2 / R3 | `src/storage/catalog_store.py` |
| **Direct Frontend DOM Hydration** | Dynamic population of `index_v2.html` from `research_v2.json` | Phase R7 | `web/research/research_v2.js` |
| **Pre-Computed Sankey Coordinates** | Eliminates client-side array sorting for mobility flows | Phase R6 | `scripts/build_research_v2_data.py` |
| **Continuous Milestone Scanner** | Automatically flags new video titles containing graduation or debut keywords | Phase R8 | `src/events/lifecycle_monitor.py` |

---

## 3. Requires Additional Data Collection (`NEEDS_MORE_COLLECTION`)

These gaps can be filled empirically with additional automated scraping or collection jobs:

1. **Historical Live Chat Archives (2020–2022)**:
   - Early observation windows are comment-heavy because YouTube live chat replays for archived streams are frequently disabled or expired. Targeted chat replay extraction for preserved VODs would balance early modality ratios.
2. **Independent Creator Debut Documentation**:
   - Outside major agencies, indie VTubers frequently debut without formal announcement videos (e.g. streaming immediately on Twitch or unlisted YouTube streams). Secondary cataloging of social media announcement links (X / Twitter) would upgrade proxy dates to verified debuts.
3. **Mid-Tier Target Cohort Expansion**:
   - Expanding the longitudinal backfill from the top 100 channels to the broader 350-channel active pool will improve long-tail community representation.

---

## 4. Requires Manual Human Verification (`NEEDS_MANUAL_VERIFICATION`)

These questions cannot be resolved automatically without manual human curation:

1. **Cross-Namespace Identity Reconciliation**:
   - The 28,762 candidate rows in the legacy `@handle` namespace require verified one-way Handle $\to$ Channel UC ID mapping before they can be merged into the 79,718 canonical HMAC namespace.
2. **Silent Hiatus vs. Formal Graduation**:
   - 39 channels in the target cohort have ceased uploading for $> 180$ days without a formal graduation video. Only manual verification of community posts or creator personal statements can distinguish temporary hiatus from permanent retirement.
3. **Corporate Sponsorship Attribution**:
   - Identifying commercial sponsors in livestream titles (e.g. game publisher logos, promotional discount codes) requires qualitative editorial review to distinguish paid commercial partnerships from organic gameplay.

---

## 5. External Data Commercially Unavailable (`EXTERNAL_DATA_UNAVAILABLE`)

These commercial figures cannot be discovered in public data and must remain unobserved unless disclosed by agency partners:

1. **Active YouTube Channel Membership Counts**:
   - YouTube Studio does not expose active paying subscriber counts publicly. Estimating membership revenue without authenticated creator export is speculative.
2. **Merchandise Sales & Unit Volume**:
   - Physical goods sales (acrylic stands, apparel, birthday sets) and digital voice pack downloads on private stores (Booth, Shopee, agency portals) are confidential proprietary figures.
3. **Brand Sponsorship Transaction Values**:
   - Commercial brand partnerships are strictly governed by Non-Disclosure Agreements (NDAs).
4. **Direct Tip Gateway Totals**:
   - Direct creator donations via local PromptPay gateways (e.g. Tipme) bypass YouTube Super Chat APIs entirely.

---

## 6. Methodologically Unanswerable Questions (`METHODOLOGICALLY_UNANSWERABLE`)

These research questions are **epistemically unanswerable** from observational public web data and must **NEVER** be claimed:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. TRUE UNIQUE HUMAN BEINGS                                                 │
│    A single person may control multiple YouTube accounts, switch devices,  │
│    or use shared household smart TVs. SNA observes pseudonymous accounts.  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. SILENT VIEWERS (LURKERS)                                                 │
│    Over 90% of live audiences watch silently without commenting or chatting.│
│    Public scrapers cannot detect passive viewership.                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. AUDIENCE DEMOGRAPHICS (AGE, GENDER, INCOME)                              │
│    YouTube APIs do not reveal viewer demographic profiles. Inferring user   │
│    gender, age, or income from username or avatar is unscientific.          │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. CAUSAL COLLABORATION ATTRIBUTION                                         │
│    Public observational streaming does not allow randomized controlled      │
│    trials. Collab impacts must remain labeled BEFORE_AFTER_DESCRIPTIVE.     │
└─────────────────────────────────────────────────────────────────────────────┘
```
