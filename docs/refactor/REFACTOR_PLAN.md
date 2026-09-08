# Step-by-Step Refactor Execution Roadmap (Phases R0–R10)

> **Execution Window**: Post-Overnight Phase  
> **Guiding Principle**: Each phase is independently executable, verifiable, and rollback-safe. Analytical results must remain identical.

---

## Phase R0: Freeze & Baseline Validation

- **Objective**: Establish the pre-refactor cryptographic and analytical baseline.
- **Files Affected**: None (Read-only check).
- **Risk**: Very Low.
- **Migration Strategy**:
  1. Record current git commit SHA.
  2. Compute SHA-256 digests of all 29 parquet tables and `web/app.js` coordinates block.
  3. Execute full pytest suite (`python -m pytest -q`) and record 319-test green state.
- **Tests**: `pytest tests/ -v`, coordinate hash assertion.
- **Rollback Plan**: N/A (No changes made).
- **Acceptance Criteria**: Baseline checksum manifest written to `docs/evidence/pre_refactor_manifest.json`.

---

## Phase R1: Data Contracts & Type Schemas

- **Objective**: Formalize typed schemas for all pipeline inputs, intermediate tables, and exports.
- **Files Affected**: `src/canonical/event_schemas.py`, `docs/research_v2/field_contract.json`.
- **Risk**: Low.
- **Migration Strategy**: Create Pydantic or dataclass contracts for canonical events, snapshots, creator events, and research output objects without touching runtime callers.
- **Tests**: Schema instantiation unit tests.
- **Rollback Plan**: `git rm src/canonical/event_schemas.py`.
- **Acceptance Criteria**: All 29 parquet table schemas typed and validated.

---

## Phase R2: Storage Boundaries & Catalog Consolidation

- **Objective**: Unify fragmented creator registries into `src/storage/catalog_store.py`.
- **Files Affected**:
  - `src/storage/catalog_store.py` (New)
  - `data/temporal/catalog/target_manifest.csv`
  - `data/thai_vtuber_registry.csv`
- **Risk**: Medium.
- **Migration Strategy**:
  1. Implement `CatalogStore` providing unified lookups for channel name, handle, agency, and tier.
  2. Re-route `build_creator_ecosystem_data.py` and `build_collab_events.py` to use `CatalogStore`.
  3. Retain existing CSV files as read-only fallbacks.
- **Tests**: Unit tests comparing `CatalogStore` query results against original CSV lookups.
- **Rollback Plan**: Revert caller scripts to read CSVs directly.
- **Acceptance Criteria**: Single source of truth for channel metadata; zero regressions in target channel attributes.

---

## Phase R3: Canonical Event Model Migration

- **Objective**: Extract DuckDB in-memory event builder from `build_duckdb_temporal_snapshots.py` into `src/canonical/duckdb_builder.py`.
- **Files Affected**:
  - `src/canonical/duckdb_builder.py` (New)
  - `scripts/build_duckdb_temporal_snapshots.py`
  - `scripts/derive_audience_behavior_aggregates.py`
- **Risk**: Medium.
- **Migration Strategy**:
  1. Move `build_unified_raw_view` and `build_canonical_events_view` into `src/canonical/duckdb_builder.py`.
  2. Maintain thin shim functions in `scripts/build_duckdb_temporal_snapshots.py` for backward compatibility.
- **Tests**: Rebuild canonical view in-memory and compare row counts and schema against baseline.
- **Rollback Plan**: Revert shim to original functions.
- **Acceptance Criteria**: Canonical events view produces identical year/source_type distribution.

---

## Phase R4: Temporal Snapshots & Network Package

- **Objective**: Package graph metric and community detection algorithms under `src/temporal/`, `src/network/`, and `src/community/`.
- **Files Affected**:
  - `src/temporal/snapshot_engine.py`
  - `src/network/graph_metrics.py`
  - `src/network/centrality_engine.py`
  - `src/community/louvain_detector.py`
  - `src/community/lineage_v2.py`
- **Risk**: High.
- **Migration Strategy**:
  1. Relocate analysis modules into domain packages.
  2. Replace dynamic monkey-patching with class-based configuration (`PipelineContext(root=..., epoch=...)`).
  3. Re-run T7, T11, T13, T14 on test fixtures.
- **Tests**: Byte-for-byte Parquet comparisons on newly computed tables against Phase R0 baseline.
- **Rollback Plan**: Re-point imports back to `scripts/`.
- **Acceptance Criteria**: Generated `network_snapshots.parquet`, `community_snapshots.parquet`, and `yearly_centrality.parquet` match baseline exactly.

---

## Phase R5: Audience, Event & Market Modules

- **Objective**: Relocate audience cohort, transition, collab, and market engines under `src/audience/`, `src/events/`, and `src/market/`.
- **Files Affected**:
  - `src/audience/cohort_tracker.py`
  - `src/audience/transition_matrix.py`
  - `src/audience/behavioral_segments.py`
  - `src/events/lifecycle_registry.py`
  - `src/events/collab_analyzer.py`
  - `src/market/evidence_registry.py`
- **Risk**: Medium.
- **Migration Strategy**: Copy scripts into `src/` hierarchy; ensure all exports write to standard `data/` directories.
- **Tests**: Validate `audience_behavior_yearly.parquet`, `collab_event_effects.parquet`, and `market_evidence.parquet`.
- **Rollback Plan**: Restore scripts in `scripts/`.
- **Acceptance Criteria**: 100% test pass on `test_data_dictionary_semantics.py` and `test_research_v2_data_contract.py`.

---

## Phase R6: Research v2 Unified Generator

- **Objective**: Establish `src/research/research_v2_builder.py` as the canonical production generator.
- **Files Affected**:
  - `src/research/research_v2_builder.py`
  - `src/research/outlook_evaluator.py`
  - `web/research/data/research_v2.json`
- **Risk**: Medium.
- **Migration Strategy**:
  1. Wire all upstream modules (R1–R5) into `research_v2_builder.py`.
  2. Include pre-calculated Sankey coordinate nodes to eliminate client-side math.
- **Tests**: `pytest tests/test_research_v2_data_contract.py -v`.
- **Rollback Plan**: Re-run `scripts/build_research_v2_data.py`.
- **Acceptance Criteria**: `research_v2.json` re-generated cleanly; all 10 contract tests pass.

---

## Phase R7: Frontend Decomposition (`web/app.js`)

- **Objective**: Split 3,500-line `web/app.js` into modular ES modules while strictly preserving `AGENCY_ISLAND_COORDINATES`.
- **Files Affected**:
  - `web/observatory/src/coordinates.js` (Isolates protected coordinates block)
  - `web/observatory/src/scene.js` (Three.js WebGL rendering)
  - `web/observatory/src/controls.js` (Time slider and camera animation)
  - `web/observatory/src/ui.js` (Detail drawer and search)
  - `web/app.js` (Becomes thin bundler/loader or re-exports modules)
- **Risk**: High (Visual / Three.js regressions).
- **Migration Strategy**:
  1. Extract `AGENCY_ISLAND_COORDINATES` byte-for-byte into `coordinates.js`.
  2. Verify SHA-256 matches `47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`.
  3. Progressively extract UI and camera controllers into separate files.
- **Tests**: Automated coordinate hash test; visual smoke testing of 3D canvas and time slider.
- **Rollback Plan**: Restore original monolithic `web/app.js`.
- **Acceptance Criteria**: Coordinate hash identical; 3D camera transitions and time slider function smoothly.

---

## Phase R8: Observatory Scheduler & DAG Modernization

- **Objective**: Upgrade `analysis_dag.py` and `observatory_controller.py` to use typed dependency injection.
- **Files Affected**:
  - `src/observatory/pipeline_dag.py`
  - `src/observatory/controller.py`
- **Risk**: High.
- **Migration Strategy**:
  1. Replace string-based task tuples with typed Step objects (`PipelineStep(name="T7", func=..., inputs=[...])`).
  2. Implement structured JSON logging for run ledgers.
- **Tests**: Execute full DAG in dry-run mode and verification mode.
- **Rollback Plan**: Revert controller to legacy script.
- **Acceptance Criteria**: Clean autonomous pipeline run from Layer 0 to Layer 7.

---

## Phase R9: Automated Test Suite & Release Verification

- **Objective**: Consolidate test suites under `tests/` and verify complete dataset release.
- **Files Affected**:
  - `tests/test_storage_boundaries.py`
  - `tests/test_analytical_integrity.py`
  - `data/temporal/release/dataset_manifest.json`
- **Risk**: Low.
- **Migration Strategy**: Run full pytest suite across all modules, generate updated SHA-256 release manifests, and run privacy leak audits.
- **Tests**: `pytest tests/ -v`, `scripts/audit_private_data_plane.py`.
- **Rollback Plan**: Address any failed assertions before committing.
- **Acceptance Criteria**: 100% test green; zero Level-A or Level-B leaks.

---

## Phase R10: Legacy Code Sunset & Clean Removal

- **Objective**: Safely delete superseded files once all post-refactor tests pass.
- **Files Affected**:
  - `data/temporal/analysis/community_lineage.parquet` (v1) $\to$ Delete
  - `data/video_catalog.csv` (partial slice) $\to$ Delete
  - Obsolete scratch scripts $\to$ Purge
- **Risk**: Low.
- **Migration Strategy**: Run `git rm` on explicitly deprecated files.
- **Tests**: Full project test run after removal.
- **Rollback Plan**: `git checkout HEAD~1 -- <file>`.
- **Acceptance Criteria**: Clean repository tree; zero dead files; zero broken imports.
