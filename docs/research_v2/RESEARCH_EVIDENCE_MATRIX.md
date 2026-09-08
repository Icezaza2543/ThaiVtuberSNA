# Research Evidence Coverage Matrix (Research v2)

**Status:** LIVING_RESEARCH_ARTIFACT  
**Last Updated:** September 9, 2026  
**Standards:** Fail-Closed Epistemic Policy (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `WEAK`, `UNSUPPORTED`, `UNANSWERABLE_WITH_CURRENT_DATA`)

---

## 1. Evidence Matrix

| Research Question | Required Evidence | Available Evidence | Coverage | External Validation | Methodological Validity | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Q1: Creator Lifecycle Timing**<br>*When do Thai creators debut, pause, and graduate?* | Debut dates, hiatus dates, graduation/retirement dates, official notices for all 193 cohort creators. | Audited dates for 21 key creators via Fandom & official announcements; catalog timestamp proxies for 172 channels. | 100% of 193 channels reviewed;<br>33 verified events,<br>198 proxy boundaries. | Cross-checked against Fandom wiki, X/Twitter announcements, YouTube streams. | Sound separation between verified dates and observational proxies. | **PARTIALLY_SUPPORTED** |
| **Q2: Collaboration Network**<br>*How frequently and between whom do cross-channel collabs occur?* | Historical video titles, descriptions, guest rosters, and participant verification. | 54 collab candidate videos scanned from catalog; 12 pairwise verified collab events from resolved @handles. | Catalog scan completed for root catalog; candidates indexed across 2021–2026. | Validated participant handles against Thai VTuber Registry. | High precision, low false-positive rate; excludes audience overlap inference. | **PARTIALLY_SUPPORTED** |
| **Q3: Agency History & Institutionalization**<br>*What is the timeline of agency launches, units, and closures?* | Founding dates, generation debuts, organizational restructuring, closures. | 12 agencies cataloged; 19 key historical milestones documented across ARP, Pixela, VZ, AStars, Polygon, RPG. | All 12 agencies in target cohort covered. | Fandom corporate pages, Brave Group press releases, agency social notices. | High qualitative and institutional rigor. Separate from `agency_at_selection`. | **SUPPORTED** |
| **Q4: Macro Market Valuation**<br>*What is the exact financial valuation of the Thai VTuber market?* | Total gross revenue from Super Chats, memberships, sponsorships, and merchandise across all channels. | 27 accepted public unit prices (memberships: 25–150 THB; voice packs: 399–599 THB; fan-meets: 500–700 THB; goods: 159–890 THB). Total revenue undisclosed. | 27 accepted records; 7 rejected sources. | Realic Official Store Shopify API, Ticketmelon, YouTube pricing schedule. | Unit prices cannot be summed without private sales volume. Fail-closed enforced. | **UNANSWERABLE_WITH_CURRENT_DATA** |
| **Q5: Audience Longevity & Cohort Dynamics**<br>*Do viewers churn completely or return across multiple years?* | Multi-year longitudinal interaction tracking of pseudonymous accounts. | 7-year cohort retention matrix (2020–2026); pooled survival rates; reactivation tracking. | 79,718 pooled cohort viewer instances across 2020–2026 YTD. | Re-calculated independently via DuckDB in-memory pipeline. | Privacy-preserving hashed IDs; k-anonymized aggregate outputs; zero viewer PII. | **SUPPORTED** |
| **Q6: Ecosystem Universe Scope**<br>*How representative is the 193 frozen target cohort?* | Comprehensive registry of discoverable Thai VTuber channels. | 1,370 discoverable channels indexed in `discovery_universe.parquet` (193 frozen + 1,177 external). | Full registry coverage with evidence strength classification. | Thai VTuber Ranking directory, manual audits, Fandom wiki. | Frozen cohort represents top ~14% active tier; preserves longitudinal comparability. | **SUPPORTED** |
| **Q7: Ecosystem Structural Health**<br>*Is the Thai VTuber ecosystem collapsing?* | Longitudinal network topology, modularity, giant component share, degree assortativity. | Annual SNA metrics across 7 time slices; 8 competing hypotheses evaluated with disconfirming tests. | Full temporal coverage (2020–2026 YTD). | Cross-checked against external corporate transitions and talent events. | Rigorous graph theory; robust Louvain community detection; fail-closed on revenue. | **SUPPORTED** |

---

## 2. Evidence Gap Prioritization for Future Passes

1. **Collab Description Ingestion**: Ingest full descriptions for the 96,420-video temporal catalog to extract secondary participant rosters currently missing from short titles.
2. **Long-Tail Hiatus Disambiguation**: Cross-check remaining 25 hiatus channels with active Twitter/Facebook handles to distinguish voluntary hiatus from permanent silent abandonment.
3. **Macro Commercial Disclosures**: Monitor depa annual surveys and corporate filings for the first audited release of segregated VTuber sector revenue figures.
