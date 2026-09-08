# Research dashboard: Thai analytics

Implemented Thai navigation, overview year selection, three primary metrics, plain-language interpretations, metric definitions, searchable creator roles, and accessible data tables for every chart. Public creator and agency names retain their source spelling.

The display uses the current dashboard schema for community counts, degree, lineage transitions, persistence, centrality changes, sampling coverage, and sensitivity scenarios. The dropout standard deviation is excluded from the mean-scenario comparison. Missing values remain distinct from zero. The partial-year evidence boundary (8 September 2026) is separate from the generation date.

Validation: 24 tab/viewport combinations (1440, 1280, 1024, 390 pixels), all seven year selections, keyboard tabs, empty search, chart/table parity, and no page overflow or browser exceptions passed. Release reproducibility: 7 tests passed. Screenshots inspected for desktop overview, mobile overview, and lineage. Tests: `tests/research_thai.mjs`.

Protected coordinates unchanged: `sha256_47a63e3160c1b1282fe0ceb997f08ef6ae5beec584771c237bb11d50fab83adc`. No backend, analytical data, or security changes. Release manifest refresh affects only the three Research frontend artifacts and derived metadata.
