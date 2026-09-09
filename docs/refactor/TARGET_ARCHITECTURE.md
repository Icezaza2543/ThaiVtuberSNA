# Target Architecture Proposal & Module Migration Map

> **Historical proposal — execution superseded by phase closure.** Preserve for architectural context; the current bounded implementation is documented in [refactor_summary.md](../refactor_summary.md). The proposed src/ rewrite and R0–R10 roadmap are not active tasks.

> **Status**: HISTORICAL BLUEPRINT (not the current execution contract)
> **Rule**: Do NOT mechanically move files tonight. This document defines the target structural end-state.

---

## 1. Target Directory Architecture

```
ThaiVtuberSNA/
├── src/                                  # Core Python Packages
│   ├── collection/                       # YouTube API & Crawler Clients
│   │   ├── catalog_crawler.py
│   │   ├── backfill_sampler.py
│   │   └── hybrid_collector.py
│   ├── identity/                         # Cryptographic Pseudonymization
│   │   ├── hmac_provider.py
│   │   └── namespace_validator.py
│   ├── storage/                          # Data Access Layer & Boundaries
│   │   ├── catalog_store.py              # Unified single source of truth for creators
│   │   ├── private_sheet_store.py        # Read-only adapter for Google Sheets
│   │   └── parquet_store.py              # Local parquet persistence adapter
│   ├── canonical/                        # Unified In-Memory Event Views
│   │   ├── duckdb_builder.py
│   │   └── event_schemas.py
│   ├── temporal/                         # Temporal Window & Snapshot Logic
│   │   ├── snapshot_engine.py
│   │   └── window_manager.py
│   ├── network/                          # Graph Metrics & Topology
│   │   ├── graph_metrics.py
│   │   └── centrality_engine.py
│   ├── community/                        # Community Detection & Lineage
│   │   ├── louvain_detector.py
│   │   └── lineage_v2.py
│   ├── audience/                         # Privacy-Preserving Audience Metrics
│   │   ├── cohort_tracker.py
│   │   ├── transition_matrix.py
│   │   └── behavioral_segments.py
│   ├── events/                           # Creator Lifecycle & Collab Registries
│   │   ├── lifecycle_registry.py
│   │   └── collab_analyzer.py
│   ├── market/                           # Market Evidence & Modeling
│   │   ├── evidence_registry.py
│   │   └── market_model.py
│   ├── research/                         # Public Research v2 Generators
│   │   ├── research_v2_builder.py
│   │   └── outlook_evaluator.py
│   └── observatory/                      # Production Scheduler & Ledger
│       ├── controller.py
│       └── run_ledger.py
│
├── web/                                  # Public Web Applications
│   ├── observatory/                      # 3D WebGL Observatory
│   │   ├── index.html
│   │   ├── css/
│   │   └── src/                          # Decomposed ES Modules
│   │       ├── main.js
│   │       ├── scene.js
│   │       ├── coordinates.js            # Sealed AGENCY_ISLAND_COORDINATES
│   │       ├── ui.js
│   │       └── controls.js
│   └── research/                         # Research v2 Decision Portal
│       ├── index_v2.html                 # Canonical Research Portal
│       ├── index.html                    # Legacy v1 (Archive View)
│       ├── research_v2.css
│       ├── research_v2.js
│       └── data/
│           ├── research_v2.json          # Authoritative Public Contract
│           └── dashboard_data.json       # Legacy v1 Data
│
├── data/                                 # Tabular Data Store
│   ├── public/                           # Fully public, safe to commit
│   │   ├── catalog/                      # Target manifest & video listings
│   │   ├── industry/                     # Creator events, collabs, audience segments
│   │   ├── market/                       # Market evidence & sources
│   │   └── temporal/                     # Snapshots, communities, metrics
│   ├── private/                          # Strictly gitignored local working snapshots
│   │   └── README.md                     # Private data plane access policy
│   ├── derived/                          # Ephemeral caches and sqlite ledgers
│   └── releases/                         # Sealed release manifests and checksums
│
├── docs/                                 # Documentation & Research Reports
│   ├── research_v2/                      # Research v2 contracts, maps, reports
│   ├── refactor/                         # Refactor audit, target, and plans
│   └── evidence/                         # Checksums, isolation audits, migration logs
│
└── tests/                                # Comprehensive Automated Test Suite
    ├── test_data_dictionary_semantics.py
    ├── test_research_v2_data_contract.py
    ├── test_storage_boundaries.py
    └── test_analytical_integrity.py
```

---

## 2. Module Migration & Action Taxonomy

Every current script and data asset is assigned an explicit migration disposition:
- **`KEEP`**: Essential production module, keep logic intact, adjust imports if moved.
- **`MOVE`**: Relocate from flat `scripts/` to structured `src/` package.
- **`MERGE`**: Consolidate overlapping scripts into a single unified module.
- **`DEPRECATE`**: Retain temporarily for backwards compatibility; scheduled for sunset.
- **`DELETE_AFTER_VALIDATION`**: Redundant, superseded, or obsolete file to be removed once refactor tests pass.

### Comprehensive Module Mapping Table

| Current File Path | Target Architecture Path | Action | Rationale |
|---|---|---|---|
| `scripts/analysis_dag.py` | `src/observatory/pipeline_dag.py` | **MOVE** | Clean up dynamic monkey-patching with typed pipeline runner. |
| `scripts/observatory_controller.py` | `src/observatory/controller.py` | **MOVE** | Core DAG controller and scheduler. |
| `scripts/build_duckdb_temporal_snapshots.py` | `src/temporal/snapshot_engine.py` | **MOVE** | DuckDB raw/canonical views and network edge snapshot builder. |
| `scripts/build_community_lineage_v2.py` | `src/community/lineage_v2.py` | **MOVE** | Authoritative Hungarian match lineage algorithm. |
| `data/temporal/analysis/community_lineage.parquet` | — | **DELETE_AFTER_VALIDATION** | Superseded v1 lineage table. |
| `scripts/analyze_temporal_communities.py` | `src/community/louvain_detector.py` | **MOVE** | Louvain community detection and modularity. |
| `scripts/analyze_audience_cohorts.py` | `src/audience/cohort_tracker.py` | **MOVE** | Cohort retention, survival, and reactivation. |
| `scripts/analyze_audience_transitions.py` | `src/audience/transition_matrix.py` | **MOVE** | Channel and agency transition matrices. |
| `scripts/derive_audience_behavior_aggregates.py` | `src/audience/behavioral_segments.py` | **MOVE** | Privacy-preserving annual audience aggregates. |
| `scripts/analyze_centrality_evolution.py` | `src/network/centrality_engine.py` | **MOVE** | PageRank, betweenness, and bridge dynamics. |
| `scripts/analyze_ecosystem_evolution.py` | `src/network/graph_metrics.py` | **MOVE** | Density, concentration Gini, and structural breaks. |
| `scripts/build_creator_ecosystem_data.py` | `src/events/lifecycle_registry.py` | **MOVE** | Creator status events and public snapshots. |
| `scripts/build_collab_events.py` | `src/events/collab_registry.py` | **MOVE** | Verified collaboration event builder. |
| `scripts/analyze_collab_events.py` | `src/events/collab_analyzer.py` | **MOVE** | Observational before/after collab study. |
| `scripts/build_market_evidence_registry.py` | `src/market/evidence_registry.py` | **MOVE** | Market evidence and source registry builder. |
| `scripts/build_outlook_model.py` | `src/research/outlook_evaluator.py` | **MOVE** | 11-dimension empirical scorecard builder. |
| `scripts/build_research_v2_data.py` | `src/research/research_v2_builder.py` | **MOVE** | Authoritative Research v2 contract generator. |
| `scripts/build_historical_lifecycle.py` | `src/events/lifecycle_registry.py` | **MERGE** | Merge with `build_creator_ecosystem_data.py`. |
| `storage/private_sheet_store.py` | `src/storage/private_sheet_store.py` | **MOVE** | Google Sheets authenticated adapter. |
| `storage/private_sheet_analytics.py` | `src/storage/private_sheet_analytics.py` | **MOVE** | Google Sheets analytics extractor. |
| `core/storage_boundary.py` | `src/storage/storage_boundary.py` | **MOVE** | Privacy plane boundary enforcement. |
| `data/temporal/catalog/target_manifest.csv` | `data/public/catalog/target_manifest.csv` | **MOVE** | 193 frozen target channels. |
| `data/video_catalog.csv` | — | **DELETE_AFTER_VALIDATION** | Partial 581-video slice superseded by full 96k catalog. |
| `web/app.js` | `web/observatory/src/*.js` | **MERGE / SPLIT** | Decompose 3,500-line monolith while sealing coordinate hash. |
| `web/research/index_v2.html` | `web/research/index_v2.html` | **KEEP** | Promoted to primary canonical research portal. |
| `web/research/index.html` | `web/research/legacy_v1.html` | **DEPRECATE** | Preserved as historical v1 reference view. |
| `scripts/build_research_dashboard_data.py` | `src/research/legacy_v1_builder.py` | **DEPRECATE** | Legacy Research v1 generator. |
| `tests/test_data_dictionary_semantics.py` | `tests/test_data_dictionary_semantics.py` | **KEEP** | 14 sealed semantic regression tests. |
| `tests/test_research_v2_data_contract.py` | `tests/test_research_v2_data_contract.py` | **KEEP** | 10 sealed Research v2 contract tests. |
| `tests/test_evidence_authenticity.py` | `tests/test_evidence_authenticity.py` | **KEEP** | Sealed authenticity & anti-fabrication tests. |
| `scratch/` | — | **KEEP (GITIGNORED)** | Temporary local workspace. Never committed. |

---

## 3. Overnight Research Discoveries & Inventory Governance

### DATASETS_TO_KEEP (Audited & Verified Source of Truth)
- `data/temporal/catalog/target_manifest.csv`: 193 frozen target creators. Must never be altered or expanded to ensure longitudinal comparability.
- `data/temporal/catalog/video_catalog.parquet`: 96,420 cataloged videos spanning 2020–2026 across 184 channels.
- `data/industry/creator_status_events.parquet`: 231 audited events (33 verified external/local, 198 observational proxies).
- `data/industry/creator_evidence_coverage.parquet`: 193 rows assessing verified vs proxy evidence gaps per creator.
- `data/industry/collab_candidates.parquet`: 54 keyword-detected candidate collab videos.
- `data/industry/collab_events.parquet`: 12 pairwise verified collab events from resolved @handles.
- `data/industry/collab_verification_audit.parquet`: 54 verification audit logs.
- `data/industry/agency_history.parquet`: 12 agencies cataloged with parent companies and founding dates.
- `data/industry/agency_events.parquet`: 19 verified agency launch, unit, and restructuring milestones.
- `data/market/market_evidence.parquet`: 27 accepted public unit prices with zero-revenue summation guards.
- `data/market/rejected_sources.csv`: 7 logged rejected sources with explicit failure reasons.
- `data/industry/discovery_universe.parquet`: 1,370 total discoverable Thai VTuber channels (193 frozen + 1,177 broader ecosystem).
- `data/industry/audience_behavior_yearly.parquet`: Independently audited annual behavioral segments across 2020–2026 YTD.
- `data/temporal/analysis/yearly_network_metrics.parquet`: 7 annual network snapshots.
- `data/temporal/cohorts/cohort_retention_matrix.parquet`: 7-year pooled retention matrix.

### DATASETS_TO_REBUILD
- `data/industry/collab_event_effects.parquet`: Rebuild using only the 12 strictly verified collab events.
- `data/industry/collab_event_summary.parquet`: Rebuild from verified collab events.
- `web/research/data/research_v2.json`: Rebuild after tomorrow's refactor to bind newly verified creator coverage and agency milestones.

### LEGACY_ARTIFACTS (Marked for Sunset / Archival)
- `data/industry/quarantine/collab_events_unverified.csv`: 42 quarantined pseudo collab IDs.
- `data/historical_unverified/`: Deprecated unverified legacy files.
- `web/research/dashboard_data.json`: Legacy v1 data blob.

### NEW_SOURCE_OF_TRUTH ARCHITECTURE
- **Creator Identity & Manifest**: `data/temporal/catalog/target_manifest.csv` (Frozen 193) + `data/industry/discovery_universe.parquet` (Discovered 1,370).
- **Creator Events**: `data/industry/creator_status_events.parquet`.
- **Collaborations**: `data/industry/collab_events.parquet` (Verified) + `data/industry/collab_candidates.parquet` (Candidates).
- **Agencies**: `data/industry/agency_history.parquet` + `data/industry/agency_events.parquet`.
- **Market & Commercial**: `data/market/market_evidence.parquet`.
- **Audience Behavioral Segments**: `data/industry/audience_behavior_yearly.parquet`.

### MIGRATION_RISKS & MITIGATIONS
1. **Coordinate Hash Invariance**: Moving `AGENCY_ISLAND_COORDINATES` to `coordinates.js` must preserve SHA-256 `47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`. Automated test in `tests/test_frontend_public_boundary.py` must run continuously.
2. **Fail-Closed Revenue Invariant**: Any script consuming `market_evidence.parquet` must check `can_be_summed == False` and refuse to compute a naive sum of unit prices.
3. **Cohort Isolation Invariant**: Discovery universe channels (1,177) must NEVER be mixed into the frozen analytical cohort (193).

---

## 4. Implementation Guardrails

1. **Hash Invariance**:
   - `AGENCY_ISLAND_COORDINATES` in `web/observatory/src/coordinates.js` must produce exact SHA-256: `47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`.
2. **Zero In-Place Rewrites**:
   - Migration must follow the *copy $\to$ validate $\to$ switch $\to$ delete* protocol.
3. **Continuous Test Enforcement**:
   - At every step of the refactor, `pytest` must pass 100% green before staging commits.
