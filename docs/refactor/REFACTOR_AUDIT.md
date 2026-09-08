# Comprehensive Repository Architecture & Codebase Refactor Audit

> **Document Status**: SEALED ARCHITECTURAL AUDIT  
> **Repository**: `C:\Users\Icezaza\Documents\GitHub\ThaiVtuberSNA`  
> **Focus**: Pipeline Complexity, Technical Debt, Coupling Points, and Security Boundaries

---

## 1. Executive Summary

Over successive development milestones (T1 through T20, plus tonight's Research v2 data engineering), the repository expanded to 55+ root scripts, 29 parquet tables, 319 unit tests, and multiple web applications. While the analytical outputs are rigorously verified, the codebase suffers from **monolithic script growth**, **redundant sources of truth**, and **deep coupling between data generation and frontend delivery**.

This audit details the structural friction points to prepare for the upcoming major refactor.

---

## 2. Core Friction Points & Technical Debt

### 2.1 The Monolithic Web Application (`web/app.js`)
- **Current State**: `web/app.js` is over 3,500 lines of Vanilla JavaScript combining:
  - Three.js 3D WebGL rendering, camera animation, and particle systems.
  - Hardcoded `AGENCY_ISLAND_COORDINATES` dictionary (protected invariant hash `47a63e31...`).
  - Graph traversal, Louvain community color palettes, time slider playback logic.
  - Channel search, detail drawer, sidebar rendering, and metrics formatting.
- **Problem**: Any change to rendering risks breaking data parsing. Coordinates are hardcoded rather than loaded from an external asset.
- **Refactor Directive**: Decompose into modular ES modules:
  - `web/observatory/src/scene.js` (WebGL/Three.js rendering)
  - `web/observatory/src/controls.js` (Camera and time slider)
  - `web/observatory/src/ui.js` (Drawer and search)
  - `web/observatory/src/data.js` (Data fetching and coordinate binding)

### 2.2 Dual Research Frontends (`Research v1` vs `Research v2`)
- **Current State**:
  - `web/research/index.html` (Research v1): Monolithic dashboard consuming `web/research/dashboard_data.json` (2MB). Heavy client-side math.
  - `web/research/index_v2.html` (Research v2): Question-driven executive interface with 193 `data-field` slots designed for `web/research/data/research_v2.json`.
- **Problem**: Redundant data models. Research v1 generates legacy fields; Research v2 requires clean, pre-calculated executive summaries.
- **Refactor Directive**: Sunset v1 into an archival view and make v2 the canonical research portal.

### 2.3 Multiple Sources of Truth for Creator Registry
- **Current State**: Channel metadata lives in:
  1. `data/temporal/catalog/target_manifest.csv` (100 core channels).
  2. `data/thai_vtuber_registry.csv` (1,370 channels).
  3. `data/registry_vtubers.csv` (1,500 channels).
  4. Google Sheets `VTUBERS` worksheet (1,500 channels).
  5. Static dictionaries in `scripts/build_historical_lifecycle.py`.
- **Problem**: Minor discrepancies in handle spelling, channel name updates, or agency changes require manual edits in multiple files.
- **Refactor Directive**: Build a single `src/storage/catalog_store.py` that reads from canonical storage and serves cached views.

### 2.4 Tight Coupling in `scripts/analysis_dag.py` and `scripts/observatory_controller.py`
- **Current State**:
  - `analysis_dag.py` dynamically re-imports modules and monkey-patches global variables (e.g. `datetime.now`, `BASE_DIR`, `build_unified_raw_view`).
  - `observatory_controller.py` executes tasks sequentially with strict string pattern matching on log outputs.
- **Problem**: Refactoring any script filename breaks the string tuples in the DAG.
- **Refactor Directive**: Replace monkey-patching with explicit dependency injection and typed pipeline steps.

### 2.5 Data Storage Architecture & Private/Public Boundaries
- **Current State**:
  - Private data plane resides in Google Sheets `ThaiVtuber_SNA` and DuckDB views.
  - Multiple storage adapters exist: `storage/private_sheet_store.py`, `storage/private_sheet_analytics.py`, `core/storage_boundary.py`.
- **Problem**: Confusing overlap between `storage/` and root `scripts/`.
- **Refactor Directive**: Consolidate all storage logic under `src/storage/` with clean interface boundaries: `PrivateDataStore`, `PublicDataStore`, `CacheStore`.

### 2.6 Fragmented Analytical Modules
- Over 15 separate scripts in `scripts/` perform post-snapshot analysis:
  - `analyze_temporal_communities.py`
  - `analyze_audience_transitions.py`
  - `analyze_centrality_evolution.py`
  - `analyze_ecosystem_evolution.py`
  - `analyze_audience_cohorts.py`
  - `analyze_event_impact.py`
  - `analyze_evidence_quality.py`
  - `validate_temporal_robustness.py`
  - `build_creator_ecosystem_data.py` (tonight)
  - `analyze_collab_events.py` (tonight)
  - `derive_audience_behavior_aggregates.py` (tonight)
  - `build_market_evidence_registry.py` (tonight)
  - `build_outlook_model.py` (tonight)
  - `build_research_v2_data.py` (tonight)
- **Problem**: Flat root directory with 55+ scripts makes onboarding difficult and blurs boundaries between collection, analysis, and publishing.
- **Refactor Directive**: Organize into domain packages under `src/`.

---

## 3. Security & Governance Review

| Governance Check | Status | Verification Detail |
|---|---|---|
| **Level-A Secrets in Git** | **CLEAN** | Zero API keys, HMAC secrets, or service account JSONs found across repo. |
| **Level-B Private Viewer Rows** | **CLEAN** | No viewer_hash or individual account records committed in public git. |
| **HMAC Non-Invertibility** | **VERIFIED** | One-way keyed SHA-256 pseudonymization contract preserved. |
| **Protected Coordinates** | **VERIFIED** | `AGENCY_ISLAND_COORDINATES` SHA-256 matches `47a63e31...` exactly. |
| **Google Sheet ID Leakage** | **VERIFIED** | Spreadsheet ID absent from public web scripts (`app.js`, `research_v2.js`). |

---

## 4. Summary of Refactor Objectives
1. **Zero Analytical Regression**: All 29 parquet datasets and Research v2 fields must produce identical results before and after refactoring.
2. **Directory Modernization**: Move from flat `scripts/` to structured `src/` packages.
3. **Decompose Web Monolith**: Split `web/app.js` into testable ES modules while preserving the coordinate hash.
4. **Single Catalog Authority**: Unify channel metadata into a single authoritative store.
5. **Declarative Pipeline**: Replace monkey-patched DAG with typed pipeline runners.
