# Privacy-Preserving Longitudinal Social Network Analysis
# of the Thai VTuber Ecosystem (2020–2026)

## Methods and storage architecture

Temporal slices use interaction_time; video publication date is NEVER a fallback. Undated events are excluded. Edges measure audience co-attendance and do not establish social causality.
Agency labels are selection-time metadata (agency_at_selection), not historical affiliations.
LEVEL A credentials remain local and never enter Git or Google Sheets. LEVEL B viewer records are private and stored only in the authorized ThaiVtuber_SNA workbook. LEVEL C public artifacts contain creator metadata and aggregate research metrics; NO_VIEWER_LEVEL_DATA applies to public exports.
Louvain partitions use resolution 1 and seed 42. Lineage matching uses 0.4 Jaccard + 0.3 forward overlap + 0.3 backward overlap with one-to-one primary matches.
Observations describe sampled active commenters/chatters, not passive viewers or the complete population. The 2026 YTD window is PARTIAL_WINDOW_DESCRIPTIVE_ONLY.

## Ecosystem measurements

| year | active_channels | edges | density | modularity | community_count | agency_at_selection_assortativity |
| --- | --- | --- | --- | --- | --- | --- |
| 2020 | 21 | 72 | 0.3429 | 0.1968 | 3 | -0.0286 |
| 2021 | 65 | 625 | 0.3005 | 0.1333 | 5 | 0.0029 |
| 2022 | 92 | 965 | 0.2305 | 0.2007 | 4 | 0.0561 |
| 2023 | 129 | 1503 | 0.182 | 0.3146 | 5 | 0.1252 |
| 2024 | 157 | 2547 | 0.208 | 0.3106 | 4 | 0.1295 |
| 2025 | 166 | 3168 | 0.2313 | 0.3189 | 4 | 0.0911 |
| 2026 | 160 | 1997 | 0.157 | 0.5085 | 4 | 0.1332 |

Observed persistent lineages: 15. Terminal-window ACTIVE lineages: 4.

## Cohort survival (cohort_survival.parquet)

| Elapsed Horizon | Pooled Cohort Base | Re-Observed Audience | Continuation Rate | Same-Channel Retained | Cross-Channel Broadened |
| --- | ---: | ---: | ---: | ---: | ---: |
| +0 Years | 79718 | 79718 | 1.0 | 1.0 | 0.0 |
| +1 Years | 69232 | 6058 | 0.0875 | 0.0396 | 0.0574 |
| +2 Years | 55151 | 2644 | 0.0479 | 0.0165 | 0.0356 |
| +3 Years | 43826 | 1329 | 0.0303 | 0.0083 | 0.0243 |
| +4 Years | 26722 | 723 | 0.0271 | 0.0042 | 0.0241 |
| +5 Years | 15982 | 423 | 0.0265 | 0.0029 | 0.0244 |
| +6 Years | 5232 | 103 | 0.0197 | 0.001 | 0.0191 |

Rates above are proportions with the exact stored Parquet precision. Same-channel and cross-channel categories may overlap; neither implies continuous attendance.

## Evidence quality

| year | interaction_evidence_channel_count | catalog_published_channel_count | intersection_count | catalog_active_recall | target_manifest_coverage | total_interactions | evidence_support_tier |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 29 | 36 | 29 | 0.8055555555555556 | 0.15025906735751296 | 5984 | MODERATE |
| 2021 | 72 | 73 | 71 | 0.9726027397260274 | 0.37305699481865284 | 14653 | HIGH |
| 2022 | 101 | 101 | 99 | 0.9801980198019802 | 0.5233160621761658 | 14772 | HIGH |
| 2023 | 141 | 137 | 133 | 0.9708029197080292 | 0.7305699481865285 | 23224 | HIGH |
| 2024 | 166 | 160 | 156 | 0.975 | 0.8601036269430051 | 17159 | HIGH |
| 2025 | 173 | 165 | 163 | 0.9878787878787879 | 0.8963730569948186 | 21812 | HIGH |
| 2026 | 176 | 147 | 143 | 0.9727891156462585 | 0.8601036269430051 | 17265 | HIGH |

## Bridge classifications

- DECLINING_BRIDGE: 6 channels
- EMERGING_BRIDGE: 10 channels
- INSUFFICIENT_EVIDENCE: 86 channels
- MODERATE_PERIPHERAL: 29 channels
- STABLE_BRIDGE: 2 channels
- STABLE_BRIDGE_CANONICAL_ONLY: 2 channels
- VOLATILE: 54 channels

## Literature Review

PENDING formal bibliography curation; no citations have been invented.
