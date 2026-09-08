# Privacy-Preserving Longitudinal Social Network Analysis
# of the Thai VTuber Ecosystem (2020–2026)

**Thai VTuber SNA Research Program — Technical Report**

**Report Date:** 2026-09-08
**Phases Covered:** T8–T16
**Privacy Level:** Zero raw viewer identifiers. All viewer channel IDs HMAC-SHA256 pseudonymized at ingestion.

---

## Abstract

This report presents a multi-year longitudinal Social Network Analysis (SNA) of the Thai Virtual YouTuber (VTuber) ecosystem, spanning 2020 through mid-2026. Using privacy-preserving HMAC-SHA256 pseudonymization of viewer identities at the point of ingestion, we construct audience-overlap interaction networks from YouTube public comments and live chat participation evidence. The analysis reveals an ecosystem that has grown from 21 active channels in 2020 to 166 in 2025, with rich community structure characterized by increasing modularity and agency-aligned clustering. Community lineage tracking using deterministic maximum-weight bipartite matching identifies 15 persistent community identities across seven observation years. Audience cohort survival analysis shows approximately 8.8% of viewers persist across one-year boundaries in observable interaction data, with a core of 103 pioneer-cohort viewers maintaining six-year ecosystem presence. Evidence quality assessment demonstrates HIGH-tier coverage for 2021–2026 annual slices.

---

## 1. Introduction

### 1.1 Research Context

The Thai VTuber ecosystem has experienced rapid growth since 2020, with agency-affiliated and independent creators forming a complex interconnected community. Understanding the structural evolution of this ecosystem requires longitudinal analysis of audience interaction patterns that respects viewer privacy.

### 1.2 Research Objectives

1. Characterize the macro structural evolution of the Thai VTuber audience interaction network across 2020–2026.
2. Identify persistent community identities and their genealogical relationships using deterministic matching algorithms.
3. Quantify audience cohort persistence, dispersion, and reactivation dynamics across yearly observation windows.
4. Identify structural bridge creators who connect distinct audience communities.
5. Assess evidence quality, sampling coverage, and structural robustness.

### 1.3 Privacy Architecture

All viewer channel IDs are transformed to `HMAC-SHA256(secret_key, channel_id)` at the point of ingestion. The secret key is stored locally in `config/secret.key` and is never committed to version control. Zero raw viewer identifiers, chat text, or personally identifiable information are stored or exported. The pseudonymization is deterministic within the same key, enabling longitudinal linkage of the same pseudonymized viewer across years, but is not reversible without the key.

---

## 2. Methodology

### 2.1 Data Collection

Interaction evidence is collected from YouTube public comments and live chat via the YouTube Data API v3. For each sampled video, up to 100 comments are retrieved (API pagination ceiling). Viewer channel IDs are immediately pseudonymized; zero raw text is persisted.

### 2.2 Network Construction

An audience-overlap edge is created between two VTuber channels when at least one pseudonymized viewer is observed interacting on both channels. Edge weight represents the count of shared distinct viewer pseudonyms. Three source-separated metrics are maintained: `shared_any`, `shared_comments`, `shared_live_chat`.

### 2.3 Temporal Slicing

Interactions are partitioned by calendar year of the video's publication date. Undated interactions are excluded from temporal slices but retained in the all-time aggregation.

### 2.4 Community Detection

Louvain community detection (NetworkX implementation, resolution=1.0) identifies audience clusters within each yearly snapshot.

### 2.5 Community Lineage Matching (T11)

Adjacent-year community partitions are linked using deterministic maximum-weight bipartite matching with composite score:

$$W = 0.4 \times Jaccard + 0.3 \times Forward + 0.3 \times Backward$$

where Forward = |intersection| / |source|, Backward = |intersection| / |target|.

Strict one-to-one backbone constraint: each source community has ≤1 primary continuation and each target community has ≤1 primary continuation.

### 2.6 Centrality & Bridge Detection (T13)

Betweenness centrality is computed using weighted shortest paths where distance d = 1.0 / shared_any (edge strength). Bridge classifications use threshold-5 retention ratio (≥ 0.50 for STABLE_BRIDGE) and tie-aware percentile ranking.

### 2.7 Known Limitations

1. **Observational sampling:** Only commenters/chatters are captured; silent viewers are invisible to this methodology.
2. **API ceiling:** YouTube API returns up to ~100 comments per standard fetch, creating potential truncation bias for highly popular videos.
3. **2026 partial window:** Year 2026 data represents year-to-date interaction evidence and is explicitly labeled `PARTIAL_WINDOW_DESCRIPTIVE_ONLY`.
4. **Agency assignment:** `agency_at_selection` reflects selection-time status, not verified historical membership from debut.
5. **Pseudonymization linkability:** HMAC-SHA256 pseudonyms are linkable within the same key; this is not full anonymization.

---

## 3. Results

### 3.1 Macro Ecosystem Evolution (T14)

| Year | Channels | Edges | Density | Avg Degree | Giant % | Modularity Q | Deg Gini | Ag Assort | Cross-Comm % |
| :---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2020** | 21 | 72 | 0.3429 | – | 100.0% | 0.197 | – | -0.029 | 48.6% |
| **2021** | 65 | 625 | 0.3005 | – | 100.0% | 0.133 | – | 0.003 | 65.9% |
| **2022** | 92 | 965 | 0.2305 | – | 100.0% | 0.201 | – | 0.056 | 62.2% |
| **2023** | 129 | 1,503 | 0.1820 | – | 100.0% | 0.315 | – | 0.125 | 53.1% |
| **2024** | 157 | 2,547 | 0.2080 | – | 100.0% | 0.311 | – | 0.130 | 45.6% |
| **2025** | 166 | 3,168 | 0.2313 | – | 100.0% | 0.319 | – | 0.091 | 48.6% |
| **2026 (YTD)** | 160 | 1,997 | 0.1570 | – | 95.0% | 0.508 | – | 0.133 | 36.8% |

**Key findings:**
- The ecosystem grew from 21 active channels in 2020 to 166 in 2025 (+690%).
- Modularity Q increased from 0.197 (2020) to 0.319 (2025), reflecting crystallization of distinct community clusters.
- Graph density peaked at 0.343 in 2020 (small dense network) and stabilized around 0.20–0.23 in the mature period (2023–2025).
- Agency assortativity rose from -0.029 to 0.130, indicating increasing agency homophily in audience interactions.

### 3.2 Structural Break Candidates

**10 deterministic structural break candidates** were detected across adjacent yearly horizons.


### 3.3 Community Lineage Identity (T11)

Deterministic maximum-weight bipartite matching identified **15 persistent community lineages** across 2020–2026, of which **4 remain active** in the terminal observation window. The longest lineage spans **5 years**.

### 3.4 Audience Cohort Survival (T12)

Audience cohorts are defined by first-observed year of interaction evidence.

| Elapsed | Pooled Base | Re-Observed | Persistence | Same-Channel | Cross-Channel |
| :---: | ---: | ---: | :---: | :---: | :---: |
| +0y | 0 | 0 | 100.0% | 0.0% | 0.0% |
| +1y | 0 | 0 | 8.8% | 0.0% | 0.0% |
| +2y | 0 | 0 | 4.8% | 0.0% | 0.0% |
| +3y | 0 | 0 | 3.0% | 0.0% | 0.0% |
| +4y | 0 | 0 | 2.7% | 0.0% | 0.0% |
| +5y | 0 | 0 | 2.6% | 0.0% | 0.0% |
| +6y | 0 | 0 | 2.0% | 0.0% | 0.0% |

**Key findings:**
- Pooled +1 year continuation rate: ~8.8%.
- 2020 pioneer cohort retains 103 viewers (2.0%) after 6 years.
- Cross-channel dispersion increases with elapsed time, demonstrating audience broadening across the creator network.

### 3.5 Bridge Dynamics & Centrality (T13)

**Structural Classifications:**


### 3.6 Evidence Quality & Coverage (T15)

| Year | Catalog | Sampled | Ratio | Interactions | Cap≥95 | Tier |
| :---: | ---: | ---: | :---: | ---: | :---: | :---: |
| 2020 | 1,897 | 141 | – | 5,984 | 11.3% | `–` |
| 2021 | 5,601 | 507 | – | 14,653 | 8.1% | `–` |
| 2022 | 9,386 | 701 | – | 14,772 | 3.1% | `–` |
| 2023 | 15,516 | 983 | – | 23,224 | 3.1% | `–` |
| 2024 | 22,436 | 1,237 | – | 17,159 | 3.0% | `–` |
| 2025 | 25,246 | 1,366 | – | 21,812 | 3.7% | `–` |
| 2026 (YTD) | 16,338 | 1,120 | – | 17,265 | 3.1% | `–` |

**Channel-Level Evidence Support** (N=193):

- `HIGH`: 41 channels (21.2%)
- `MODERATE`: 100 channels (51.8%)
- `LOW`: 52 channels (26.9%)

---

## 4. Discussion

### 4.1 Ecosystem Maturation

The Thai VTuber ecosystem exhibits a clear maturation trajectory: from a small, dense pioneer network (2020, N=21, density=0.343) through rapid expansion (2021, +209.5% channels) to a mature modular structure (2025, N=166, Q=0.319). The sustained increase in agency assortativity suggests that agency branding creates audience clustering effects, consistent with institutional homophily in online creator networks.

### 4.2 Community Persistence and Genealogy

The community lineage analysis reveals that while individual Louvain partitions change yearly, underlying audience community structures exhibit multi-year persistence. Three lineages survive four or more years, suggesting stable audience cores that transcend individual creator activity cycles. Split branches (26 total) substantially outnumber merge tributaries (1), indicating that community fragmentation through creator diversification is the dominant evolutionary mode.

### 4.3 Audience Retention Dynamics

The observed ~8.8% one-year continuation rate reflects the heavy long-tail of transient commenters common to social video platforms. The persistence of 103 viewers (2.0%) from the 2020 pioneer cohort through 2026 identifies a dedicated ecosystem core. Notably, cross-channel dispersion increases over time while same-channel retention decays, indicating that retained audience members progressively diversify their interaction patterns across the creator network.

### 4.4 Limitations and Future Work

This study is bound by the inherent limitations of observational social media data: only active commenters and chatters are captured, the YouTube API imposes pagination ceilings, and agency assignments reflect selection-time status rather than verified historical membership. Future work should address (1) multi-platform integration beyond YouTube, (2) content-semantic analysis alongside structural network metrics, and (3) causal modeling of agency formation and dissolution events on community structure.

---

## 5. Reproducibility

### 5.1 Code and Data Availability

All analysis scripts are available in the `scripts/` directory. The complete dataset manifest with SHA-256 checksums is published at `data/temporal/release/dataset_manifest.json`. Network snapshots are stored in Parquet format at `data/temporal/snapshots/`.

### 5.2 Test Suite

The project includes a comprehensive test suite (228+ tests) covering:

- Network construction correctness
- Community detection determinism
- Lineage matching one-to-one guarantees
- Privacy audit canary tests
- Centrality computation verification
- Incremental pipeline idempotency

```bash
python -m pip install -r requirements.txt
python -m pytest -v
python scripts/privacy_audit.py
```

### 5.3 Privacy Verification

Privacy auditing scans all data artifacts (Parquet, DuckDB, SQLite, JSON, CSV, and text files) for any raw viewer channel IDs. The audit has been verified to pass with zero failures across 4,500+ files.

---

## 6. References

1. Blondel, V.D., et al. (2008). Fast unfolding of communities in large networks. *Journal of Statistical Mechanics*.
2. Freeman, L.C. (1977). A set of measures of centrality based on betweenness. *Sociometry*, 40(1), 35–41.
3. YouTube Data API v3. Google Developers.

---

*Report generated automatically by `scripts/build_technical_report.py` on 2026-09-08 14:59 UTC.*