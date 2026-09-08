# Thai VTuber SNA — Reproducible Research Dataset Release Notes

**Version:** 1.0.0
**Generated:** 2026-09-08T14:57:00.983249+00:00
**Phases:** T8–T16
**Temporal Range:** 2020–2026 (2026 = YTD partial window)
**Privacy:** AGGREGATED_MACRO_ONLY
**Total Files:** 38
**Total Size:** 1043.8 KB

---

## Privacy Guarantee

Zero raw viewer identifiers, channel IDs are public YouTube metadata.

---

## Methodology

**Data Collection:** YouTube public comment and live chat interaction evidence collected via YouTube Data API v3 with HMAC-SHA256 pseudonymization at ingestion. Viewer channel IDs are irreversibly transformed; zero raw IDs are stored.

**Network Construction:** Co-commenter/co-chatter edges built from shared pseudonymized viewer presence across channel video pairs. Edge weight = count of shared distinct viewer pseudonyms.

**Temporal Slicing:** Interactions partitioned by calendar year of video publication date. Undated interactions excluded from temporal slices.

**Community Detection:** Louvain community detection (NetworkX) at resolution=1.0.

**Lineage Matching:** Deterministic maximum-weight bipartite matching per adjacent-year pair using W = 0.4*Jaccard + 0.3*Forward + 0.3*Backward. Strict one-to-one backbone constraint.

### Known Limitations

- Observational sampling: only commenters/chatters captured, not silent viewers.
- YouTube API pagination ceiling: ~100 comments per standard fetch.
- 2026 represents partial Year-To-Date window.
- Agency/group assignments reflect selection-time status, not historical membership.
- HMAC pseudonymization is linkable within the same key; not full anonymity.

---

## Dataset Contents

### T8: Lifecycle Events & Intervals
**Files:** 3 | **Size:** 64.4 KB

| File | Format | Size | Checksum |
| :--- | :---: | ---: | :--- |
| `channel_lifecycle_intervals.parquet` | parquet | 29.6 KB | `sha256_02a9c74d626c6...` |
| `lifecycle_events.parquet` | parquet | 30.8 KB | `sha256_e3be8f0d5b74f...` |
| `lifecycle_report.md` | md | 4.0 KB | `sha256_9ce6476954e44...` |

**`channel_lifecycle_intervals.parquet`** schema (237 rows × 15 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `interval_id` | `str` | 0 |
| `channel_id` | `str` | 0 |
| `channel_name` | `str` | 0 |
| `start_date` | `str` | 11 |
| `end_date` | `str` | 191 |
| `effective_agency` | `str` | 0 |
| `agency_at_selection` | `str` | 0 |
| `lifecycle_status` | `str` | 0 |
| `is_current` | `bool` | 0 |
| `verification_status` | `str` | 0 |
| `confidence` | `str` | 0 |
| `evidence_type` | `str` | 0 |
| `evidence_source` | `str` | 0 |
| `evidence_source_ref` | `str` | 0 |
| `provenance` | `str` | 0 |

**`lifecycle_events.parquet`** schema (226 rows × 13 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `event_id` | `str` | 0 |
| `channel_id` | `str` | 0 |
| `channel_name` | `str` | 0 |
| `event_type` | `str` | 0 |
| `event_date` | `str` | 0 |
| `event_year` | `int64` | 0 |
| `agency` | `str` | 0 |
| `evidence_type` | `str` | 0 |
| `evidence_source` | `str` | 0 |
| `evidence_source_ref` | `str` | 0 |
| `confidence` | `str` | 0 |
| `verification_status` | `str` | 0 |
| `details` | `str` | 0 |

---

### T9: Lifecycle Event Impact Analysis
**Files:** 2 | **Size:** 52.5 KB

| File | Format | Size | Checksum |
| :--- | :---: | ---: | :--- |
| `event_impact_metrics.parquet` | parquet | 45.0 KB | `sha256_6c5873664d872...` |
| `event_impact_report.md` | md | 7.5 KB | `sha256_9b26a18eb3f56...` |

**`event_impact_metrics.parquet`** schema (448 rows × 30 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `event_id` | `str` | 0 |
| `channel_id` | `str` | 0 |
| `channel_name` | `str` | 0 |
| `event_type` | `str` | 0 |
| `event_date` | `str` | 0 |
| `verification_status` | `str` | 0 |
| `confidence` | `str` | 0 |
| `analysis_tier` | `str` | 0 |
| `window_days` | `int32` | 0 |
| `pre_start` | `str` | 0 |
| `pre_end` | `str` | 0 |
| `post_start` | `str` | 0 |
| `post_end` | `str` | 0 |
| `pre_focal_viewers` | `int64` | 0 |
| `post_focal_viewers` | `int64` | 0 |
| `delta_focal_viewers` | `int64` | 0 |
| `pct_change_focal_viewers` | `float64` | 385 |
| `continuing_focal_viewers` | `int64` | 0 |
| `focal_retention_rate` | `float64` | 0 |
| `pre_viewers_seen_other_post` | `int64` | 0 |
| `same_agency_other_viewers` | `int64` | 0 |
| `cross_agency_other_viewers` | `int64` | 0 |
| `distinct_other_channels_engaged` | `int64` | 0 |
| `pre_focal_degree` | `int64` | 0 |
| `post_focal_degree` | `int64` | 0 |
| `evidence_status` | `str` | 0 |
| `evidence_note` | `str` | 0 |
| `top_post_associated_channels` | `str` | 0 |
| `agency_at_event` | `str` | 0 |
| `agency_at_selection` | `str` | 0 |

---

### T10: Sensitivity & Robustness Analysis
**Files:** 3 | **Size:** 57.1 KB

| File | Format | Size | Checksum |
| :--- | :---: | ---: | :--- |
| `robustness_report.md` | md | 7.3 KB | `sha256_634e3615673dd...` |
| `robustness_summary.parquet` | parquet | 9.0 KB | `sha256_c56f61819634e...` |
| `sensitivity_results.parquet` | parquet | 40.9 KB | `sha256_0ea5c9f7bad60...` |

**`robustness_summary.parquet`** schema (6 rows × 8 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `finding_id` | `str` | 0 |
| `research_domain` | `str` | 0 |
| `finding_statement` | `str` | 0 |
| `measured_metric_name` | `str` | 0 |
| `measured_metric_value` | `float64` | 0 |
| `classification` | `str` | 0 |
| `deterministic_rule_basis` | `str` | 0 |
| `methodological_implication` | `str` | 0 |

**`sensitivity_results.parquet`** schema (860 rows × 28 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `slice_type` | `str` | 0 |
| `slice_label` | `str` | 0 |
| `slice_start` | `str` | 0 |
| `slice_end` | `str` | 0 |
| `evidence_mode` | `str` | 0 |
| `dataset_depth` | `str` | 0 |
| `edge_threshold` | `int64` | 0 |
| `louvain_resolution` | `float64` | 0 |
| `random_seed` | `int64` | 0 |
| `active_nodes` | `int64` | 0 |
| `active_edges` | `int64` | 0 |
| `community_count` | `int64` | 0 |
| `modularity_q` | `float64` | 0 |
| `nmi_to_baseline` | `float64` | 0 |
| `ari_to_baseline` | `float64` | 0 |
| `jaccard_top_bridges` | `float64` | 0 |
| `top_5_bridges` | `str` | 0 |
| `agency_purity` | `float64` | 0 |
| `t6_nodes` | `int64` | 0 |
| `t5_nodes` | `float64` | 840 |
| `common_nodes` | `float64` | 840 |
| `t6_edges` | `int64` | 0 |
| `t5_edges` | `float64` | 840 |
| `t6_modularity` | `float64` | 0 |
| `t5_modularity` | `float64` | 840 |
| `real_nmi` | `float64` | 0 |
| `real_ari` | `float64` | 0 |
| `status` | `str` | 0 |

---

### T11: Community Lineage & Network Metrics
**Files:** 10 | **Size:** 195.6 KB

| File | Format | Size | Checksum |
| :--- | :---: | ---: | :--- |
| `agency_transition_matrix.parquet` | parquet | 5.9 KB | `sha256_831f2511b3948...` |
| `channel_transition_summary.parquet` | parquet | 101.3 KB | `sha256_bbd04bafb81a8...` |
| `community_lifecycles.parquet` | parquet | 8.7 KB | `sha256_61b9a267feaf6...` |
| `community_lineage.parquet` | parquet | 6.0 KB | `sha256_9c37cbbe8c2f7...` |
| `community_lineage_v2.parquet` | parquet | 9.1 KB | `sha256_970f6e733b7db...` |
| `community_lineage_v2_report.md` | md | 9.7 KB | `sha256_276ab18ea0f62...` |
| `community_snapshots.parquet` | parquet | 12.7 KB | `sha256_e13e6436f1a70...` |
| `temporal_community_report.md` | md | 19.4 KB | `sha256_a52ffdee640ad...` |
| `temporal_migration_report.md` | md | 15.2 KB | `sha256_e0b13ad8c7d0a...` |
| `yearly_network_metrics.parquet` | parquet | 7.6 KB | `sha256_bdeaffc0822b3...` |

**`agency_transition_matrix.parquet`** schema (266 rows × 6 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `from_year` | `int32` | 0 |
| `to_year` | `int32` | 0 |
| `from_agency_at_selection` | `str` | 0 |
| `to_agency_at_selection` | `str` | 0 |
| `transition_type` | `str` | 0 |
| `observed_transition_viewers` | `int64` | 0 |

**`channel_transition_summary.parquet`** schema (15455 rows × 10 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `from_year` | `int32` | 0 |
| `to_year` | `int32` | 0 |
| `from_channel_id` | `str` | 0 |
| `from_channel_name` | `str` | 0 |
| `from_agency_at_selection` | `str` | 0 |
| `to_channel_id` | `str` | 0 |
| `to_channel_name` | `str` | 0 |
| `to_agency_at_selection` | `str` | 0 |
| `transition_type` | `str` | 0 |
| `observed_transition_viewers` | `int64` | 0 |

**`community_lifecycles.parquet`** schema (15 rows × 12 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `lineage_id` | `str` | 0 |
| `birth_year` | `int32` | 0 |
| `last_observed_year` | `int32` | 0 |
| `lifespan_years` | `int32` | 0 |
| `lifecycle_status` | `str` | 0 |
| `dominant_agency` | `str` | 0 |
| `dominant_agency_share` | `float64` | 0 |
| `total_unique_creators` | `int64` | 0 |
| `mean_membership_churn` | `float64` | 0 |
| `split_contributors` | `str` | 0 |
| `merge_contributors` | `str` | 0 |
| `member_snapshot_communities` | `str` | 0 |

**`community_lineage.parquet`** schema (53 rows × 11 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `from_year` | `int32` | 0 |
| `to_year` | `int32` | 0 |
| `from_community_id` | `str` | 0 |
| `to_community_id` | `str` | 0 |
| `event_category` | `str` | 0 |
| `event_type` | `str` | 0 |
| `shared_channel_count` | `int64` | 0 |
| `jaccard_similarity` | `float64` | 0 |
| `forward_overlap_ratio` | `float64` | 0 |
| `backward_overlap_ratio` | `float64` | 0 |
| `details` | `str` | 0 |

**`community_lineage_v2.parquet`** schema (41 rows × 12 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `from_year` | `int32` | 0 |
| `to_year` | `int32` | 0 |
| `from_community_id` | `str` | 0 |
| `to_community_id` | `str` | 0 |
| `from_lineage_id` | `str` | 0 |
| `to_lineage_id` | `str` | 0 |
| `relation_type` | `str` | 0 |
| `shared_channels` | `int64` | 0 |
| `jaccard_similarity` | `float64` | 0 |
| `forward_overlap` | `float64` | 0 |
| `backward_overlap` | `float64` | 0 |
| `is_primary_backbone` | `bool` | 0 |

**`community_snapshots.parquet`** schema (790 rows × 8 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `year` | `int32` | 0 |
| `community_id` | `str` | 0 |
| `channel_id` | `str` | 0 |
| `channel_name` | `str` | 0 |
| `agency_at_selection` | `str` | 0 |
| `community_size` | `int64` | 0 |
| `community_rank` | `int64` | 0 |
| `yearly_modularity` | `float64` | 0 |

**`yearly_network_metrics.parquet`** schema (7 rows × 20 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `year` | `float64` | 0 |
| `active_channels` | `int64` | 0 |
| `active_edges` | `int64` | 0 |
| `community_count` | `int64` | 0 |
| `modularity` | `float64` | 0 |
| `distinct_observed_viewers` | `int64` | 0 |
| `total_observed_interactions` | `int64` | 0 |
| `adjacent_transition_window` | `str` | 0 |
| `active_viewers_t` | `int64` | 0 |
| `active_viewers_t1` | `int64` | 0 |
| `continuing_viewers_any` | `int64` | 0 |
| `same_channel_retained_viewers` | `int64` | 0 |
| `cross_channel_continuing_viewers` | `int64` | 0 |
| `same_agency_cross_viewers` | `int64` | 0 |
| `cross_agency_viewers` | `int64` | 0 |
| `continuation_rate` | `float64` | 0 |
| `same_channel_retention_rate` | `float64` | 0 |
| `conditional_same_channel_rate` | `float64` | 0 |
| `reliability_flag` | `str` | 0 |
| `calculated_at` | `str` | 0 |

---

### T12: Audience Cohort Survival
**Files:** 4 | **Size:** 31.7 KB

| File | Format | Size | Checksum |
| :--- | :---: | ---: | :--- |
| `cohort_reactivation.parquet` | parquet | 5.6 KB | `sha256_4a3949f5017b4...` |
| `cohort_retention_matrix.parquet` | parquet | 10.4 KB | `sha256_edc7da18dfad0...` |
| `cohort_survival.parquet` | parquet | 7.1 KB | `sha256_54cbb235498f7...` |
| `cohort_survival_report.md` | md | 8.6 KB | `sha256_5036c08ef461a...` |

**`cohort_reactivation.parquet`** schema (35 rows × 7 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `cohort_year` | `int64` | 0 |
| `reactivation_year` | `int64` | 0 |
| `gap_years` | `int64` | 0 |
| `reactivated_viewers` | `int64` | 0 |
| `cohort_size` | `int64` | 0 |
| `reactivation_rate_of_cohort` | `float64` | 0 |
| `reactivation_note` | `str` | 0 |

**`cohort_retention_matrix.parquet`** schema (28 rows × 13 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `cohort_year` | `int64` | 0 |
| `observation_year` | `int64` | 0 |
| `elapsed_years` | `int64` | 0 |
| `cohort_size` | `int64` | 0 |
| `reobserved_viewers` | `int64` | 0 |
| `continuation_rate` | `float64` | 0 |
| `same_channel_reobserved_viewers` | `int64` | 0 |
| `same_channel_retention_rate` | `float64` | 0 |
| `cross_channel_reobserved_viewers` | `int64` | 0 |
| `cross_channel_rate` | `float64` | 0 |
| `cross_agency_reobserved_viewers` | `int64` | 0 |
| `cross_agency_rate` | `float64` | 0 |
| `median_channel_breadth` | `float64` | 0 |

**`cohort_survival.parquet`** schema (7 rows × 9 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `elapsed_years` | `int64` | 0 |
| `cohorts_evaluated_count` | `int64` | 0 |
| `pooled_cohort_size` | `int64` | 0 |
| `pooled_reobserved_viewers` | `int64` | 0 |
| `persistence_rate` | `float64` | 0 |
| `same_channel_persistence_rate` | `float64` | 0 |
| `cross_channel_persistence_rate` | `float64` | 0 |
| `cross_agency_persistence_rate` | `float64` | 0 |
| `mean_of_cohort_median_channel_breadth` | `float64` | 0 |

---

### T13: Bridge Dynamics & Centrality
**Files:** 4 | **Size:** 132.6 KB

| File | Format | Size | Checksum |
| :--- | :---: | ---: | :--- |
| `bridge_dynamics.parquet` | parquet | 29.6 KB | `sha256_80b16c98366d0...` |
| `bridge_dynamics_report.md` | md | 30.7 KB | `sha256_1ed36fd0efdbd...` |
| `centrality_change_points.parquet` | parquet | 15.2 KB | `sha256_a47cee69b0998...` |
| `yearly_centrality.parquet` | parquet | 57.0 KB | `sha256_97ed2e5a06675...` |

**`bridge_dynamics.parquet`** schema (189 rows × 17 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `channel_id` | `str` | 0 |
| `channel_name` | `str` | 0 |
| `agency_at_selection` | `str` | 0 |
| `first_observed_year` | `int64` | 0 |
| `last_observed_year` | `int64` | 0 |
| `years_observed_count` | `int64` | 0 |
| `years_in_top_decile_count` | `int64` | 0 |
| `first_year_entering_top_decile` | `int64` | 0 |
| `mean_betweenness_percentile` | `float64` | 0 |
| `max_betweenness_percentile` | `float64` | 0 |
| `min_betweenness_percentile` | `float64` | 0 |
| `percentile_volatility_std` | `float64` | 0 |
| `mean_cross_community_share` | `float64` | 0 |
| `mean_cross_agency_share` | `float64` | 0 |
| `threshold_th5_retention_ratio` | `float64` | 0 |
| `bridge_classification` | `str` | 0 |
| `classification_rule_basis` | `str` | 0 |

**`centrality_change_points.parquet`** schema (214 rows × 10 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `channel_id` | `str` | 0 |
| `channel_name` | `str` | 0 |
| `from_year` | `int64` | 0 |
| `to_year` | `int64` | 0 |
| `from_percentile` | `float64` | 0 |
| `to_percentile` | `float64` | 0 |
| `percentile_delta` | `float64` | 0 |
| `change_type` | `str` | 0 |
| `from_band` | `str` | 0 |
| `to_band` | `str` | 0 |

**`yearly_centrality.parquet`** schema (790 rows × 18 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `year` | `int64` | 0 |
| `channel_id` | `str` | 0 |
| `channel_name` | `str` | 0 |
| `agency_at_selection` | `str` | 0 |
| `community_id` | `str` | 0 |
| `degree` | `int64` | 0 |
| `weighted_degree` | `float64` | 0 |
| `betweenness_centrality` | `float64` | 0 |
| `pagerank` | `float64` | 0 |
| `eigenvector_centrality` | `float64` | 0 |
| `cross_community_edge_share` | `float64` | 0 |
| `cross_agency_edge_share` | `float64` | 0 |
| `betweenness_percentile` | `float64` | 0 |
| `degree_percentile` | `float64` | 0 |
| `pagerank_percentile` | `float64` | 0 |
| `bridge_percentile_band` | `str` | 0 |
| `is_in_top_decile` | `bool` | 0 |
| `is_in_top_quartile` | `bool` | 0 |

---

### T14: Ecosystem Structural Evolution
**Files:** 3 | **Size:** 23.2 KB

| File | Format | Size | Checksum |
| :--- | :---: | ---: | :--- |
| `ecosystem_evolution_report.md` | md | 4.7 KB | `sha256_f17cc80d5de4b...` |
| `structural_breaks.parquet` | parquet | 6.4 KB | `sha256_13b1f230128b4...` |
| `yearly_ecosystem_metrics.parquet` | parquet | 12.2 KB | `sha256_0532bad84e1c1...` |

**`structural_breaks.parquet`** schema (10 rows × 8 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `transition` | `str` | 0 |
| `metric_dimension` | `str` | 0 |
| `from_value` | `float64` | 0 |
| `to_value` | `float64` | 0 |
| `absolute_delta` | `float64` | 0 |
| `relative_change_pct` | `float64` | 0 |
| `break_category` | `str` | 0 |
| `descriptive_note` | `str` | 0 |

**`yearly_ecosystem_metrics.parquet`** schema (7 rows × 18 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `year` | `int64` | 0 |
| `year_label` | `str` | 0 |
| `is_ytd` | `bool` | 0 |
| `active_channels` | `int64` | 0 |
| `edges` | `int64` | 0 |
| `density` | `float64` | 0 |
| `weighted_edge_strength` | `float64` | 0 |
| `average_degree` | `float64` | 0 |
| `connected_components` | `int64` | 0 |
| `giant_component_nodes` | `int64` | 0 |
| `giant_component_share` | `float64` | 0 |
| `community_count` | `int64` | 0 |
| `modularity` | `float64` | 0 |
| `degree_concentration_gini` | `float64` | 0 |
| `strength_concentration_gini` | `float64` | 0 |
| `agency_assortativity` | `float64` | 0 |
| `agency_independent_mixing` | `float64` | 0 |
| `cross_community_edge_share` | `float64` | 0 |

---

### T15: Evidence Quality & Bias
**Files:** 4 | **Size:** 57.5 KB

| File | Format | Size | Checksum |
| :--- | :---: | ---: | :--- |
| `bias_sensitivity.parquet` | parquet | 6.5 KB | `sha256_ba10dc627cd07...` |
| `channel_evidence_quality.parquet` | parquet | 28.0 KB | `sha256_81bf24438483a...` |
| `evidence_quality_report.md` | md | 6.9 KB | `sha256_9ee9ce39741c8...` |
| `yearly_evidence_quality.parquet` | parquet | 16.1 KB | `sha256_ff369d1b83243...` |

**`bias_sensitivity.parquet`** schema (35 rows × 8 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `year` | `int32` | 0 |
| `perturbation_scenario` | `str` | 0 |
| `active_channels` | `int64` | 0 |
| `edges` | `int64` | 0 |
| `density` | `float64` | 0 |
| `average_degree` | `float64` | 0 |
| `giant_component_share` | `float64` | 0 |
| `modularity` | `float64` | 0 |

**`channel_evidence_quality.parquet`** schema (193 rows × 17 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `channel_id` | `str` | 0 |
| `channel_name` | `str` | 0 |
| `agency` | `str` | 0 |
| `catalog_videos_count` | `int64` | 0 |
| `sampled_videos_count` | `int64` | 0 |
| `sampling_coverage_rate` | `float64` | 0 |
| `total_interactions` | `int64` | 0 |
| `distinct_viewers_count` | `int64` | 0 |
| `t6_deepened_interactions` | `int64` | 0 |
| `t6_deepened_share` | `float64` | 0 |
| `cap_100_hit_videos` | `int64` | 0 |
| `cap_100_exposure_rate` | `float64` | 0 |
| `has_live_chat` | `bool` | 0 |
| `years_active_count` | `int64` | 0 |
| `lifecycle_verification_status` | `str` | 0 |
| `evidence_support_tier` | `str` | 0 |
| `evidence_tier_rationale` | `str` | 0 |

**`yearly_evidence_quality.parquet`** schema (7 rows × 23 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `year` | `int32` | 0 |
| `year_label` | `str` | 0 |
| `is_ytd` | `bool` | 0 |
| `catalog_videos` | `int64` | 0 |
| `sampled_videos` | `int64` | 0 |
| `video_sampling_ratio` | `float64` | 0 |
| `total_interactions` | `int64` | 0 |
| `comment_interactions` | `int64` | 0 |
| `live_chat_interactions` | `int64` | 0 |
| `live_chat_share` | `float64` | 0 |
| `t6_deepened_interactions` | `int64` | 0 |
| `t6_deepened_share` | `float64` | 0 |
| `mean_comments_per_video` | `float64` | 0 |
| `median_comments_per_video` | `float64` | 0 |
| `cap_100_hit_videos` | `int64` | 0 |
| `cap_100_exposure_rate` | `float64` | 0 |
| `catalog_channels_active` | `int64` | 0 |
| `channels_with_evidence` | `int64` | 0 |
| `channel_coverage_rate` | `float64` | 0 |
| `catalog_channel_coverage_rate` | `float64` | 0 |
| `source_provenance_entropy` | `float64` | 0 |
| `evidence_support_tier` | `str` | 0 |
| `evidence_tier_rationale` | `str` | 0 |

---

### Integrity Reports
**Files:** 2 | **Size:** 12.0 KB

| File | Format | Size | Checksum |
| :--- | :---: | ---: | :--- |
| `t11_t16_integrity_report.md` | md | 8.2 KB | `sha256_718d14631501c...` |
| `t8_t10_integrity_report.md` | md | 3.8 KB | `sha256_6e5580228bec0...` |
---

### Network Snapshots
**Files:** 1 | **Size:** 416.2 KB

| File | Format | Size | Checksum |
| :--- | :---: | ---: | :--- |
| `network_snapshots.parquet` | parquet | 416.2 KB | `sha256_4ba8560db946f...` |

**`network_snapshots.parquet`** schema (48290 rows × 19 cols):

| Column | Type | Nulls |
| :--- | :--- | ---: |
| `window_type` | `str` | 0 |
| `window_start` | `str` | 0 |
| `window_end` | `str` | 0 |
| `vtuber_a` | `str` | 0 |
| `vtuber_b` | `str` | 0 |
| `shared_any` | `int64` | 0 |
| `shared_comments` | `int64` | 0 |
| `shared_live_chat` | `int64` | 0 |
| `strong_shared_any` | `int64` | 0 |
| `strong_shared_comments` | `int64` | 0 |
| `strong_shared_live_chat` | `int64` | 0 |
| `jaccard_comments` | `float64` | 0 |
| `jaccard_live_chat` | `float64` | 0 |
| `overlap_coefficient` | `float64` | 0 |
| `size_a` | `int64` | 0 |
| `size_b` | `int64` | 0 |
| `coverage_a` | `float64` | 0 |
| `coverage_b` | `float64` | 0 |
| `calculated_at` | `str` | 0 |

---

### Pipeline State
**Files:** 2 | **Size:** 0.9 KB

| File | Format | Size | Checksum |
| :--- | :---: | ---: | :--- |
| `pipeline_state.json` | json | 0.3 KB | `sha256_6ff3199892e0c...` |
| `release_manifest.json` | json | 0.6 KB | `sha256_97d86a6f5dd2c...` |
---

*Release manifest generated automatically by `scripts/build_dataset_release.py`.*