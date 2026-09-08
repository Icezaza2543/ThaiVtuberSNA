# Phase T8 — Historical Agency & Lifecycle Timeline Report

## Executive Summary
Phase T8 establishes a dated historical lifecycle and agency timeline layer for the 193 channels in the research cohort.
This replaces the analytical limitation of static `agency_at_selection` with verified, time-bounded intervals.

> [!IMPORTANT]
> **Epistemic Stance & Strict Non-Inference:**
> - Historical agency membership is **NEVER** inferred from current metadata alone.
> - Intervals prior to a channel's recorded debut date are strictly classified as `pre_debut` with agency `Unknown`.
> - Channels with unverified video history retain an explicit `unknown` status.
> - Frozen `agency_at_selection` metadata is preserved separately alongside `effective_agency` in every interval.

---

## Lifecycle Event Summary

| Event Type | Count | Earliest Date | Latest Date | Primary Provenance Source |
|:---|:---:|:---:|:---:|:---|
| `agency_closure` | 2 | 2021-12-31 | 2024-09-30 | `historical_community_announcement` |
| `agency_exit` | 3 | 2024-09-03 | 2025-04-30 | `graduation_agency_separation` |
| `agency_join` | 75 | 2018-02-07 | 2025-07-10 | `target_manifest_cohort_record` |
| `debut` | 182 | 2007-02-09 | 2025-07-10 | `video_catalog_earliest_upload` |
| `graduation` | 8 | 2022-10-16 | 2025-12-28 | `manifest_status_and_final_stream` |
| `hiatus` | 32 | 2020-08-13 | 2026-02-20 | `registry_hiatus_and_last_stream` |

---

## Channel Interval Coverage

- **Total Target Channels:** 193
- **Total Lifecycle Intervals:** 233
- **Channels with Verified Debut:** 182
- **Channels with Active Status:** 183
- **Channels in Hiatus:** 33
- **Graduated Channels:** 12
- **Unknown/Undated Intervals:** 11

---

## Sample Deterministic Agency Resolutions (`agency_at`)

| Channel Name | Query Date | Effective Agency | Status | Is Active | Resolution Provenance |
|:---|:---:|:---:|:---:|:---:|:---|
| Doyser | 2018-01-01 | **Unknown** | `pre_debut` | `False` | `date_prior_to_debut` |
| Doyser | 2024-06-01 | **Unknown** | `pre_debut` | `False` | `date_prior_to_debut` |
| Dacapo Ch.【ARP】 | 2020-01-01 | **Unknown** | `pre_debut` | `False` | `date_prior_to_debut` |
| Dacapo Ch.【ARP】 | 2023-06-01 | **Algorhythm Project** | `active` | `True` | `catalog_debut_ongoing` |
| Hinabe HongFei Ch. Pixela Project | 2025-06-01 | **Pixela Project** | `hiatus` | `False` | `hiatus_ongoing` |
| 【graduated】Ice Shirakoi Ch. / AStars Amakara | 2025-06-01 | **Graduated** | `graduated` | `False` | `post_graduation` |
