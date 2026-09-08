# Phase T8: Historical Lifecycle & Timeline Report (Research Integrity Edition)

## Executive Summary
This report documents the historical lifecycle timeline for the **193** Thai VTuber target cohort channels.

### Methodological Corrections & Evidence Contracts
1. **Separation of Verified Anchors from Observational Boundaries:**
   - `oldest_video_published_at` is classified strictly as `earliest_observed_content`, an `INFERRED_PROXY` date with `LOW` confidence. It is never treated as a verified debut date.
   - `newest_video_published_at` is classified as an observational activity boundary, NOT a verified graduation or hiatus date.
   - Verified milestones require explicit evidence (official agency disbandment announcements, verified stream titles, or audited registry entries).
2. **Strict Non-Projection of Agency:**
   - `agency_at_selection` represents static agency affiliation at the time of cohort selection (2026-09-07). It is **NEVER** projected backward as verified historical membership.
   - Historical tenure intervals default to `effective_agency = "Unknown"` unless supported by verified evidence.
3. **No Invented Transitions:**
   - Zero invented agency join, exit, or transfer events. All counts reflect explicit artifacts.

---

## 1. Lifecycle Event Counts by Verification Status

| Verification Status | Event Type | Count | Evidence Basis | Confidence |
| :--- | :--- | :---: | :--- | :---: |
| **`INFERRED_PROXY`** | `agency_closure` | 2 | `inferred_agency_closure` | `LOW` |
| **`INFERRED_PROXY`** | `earliest_observed_content` | 182 | `observational_catalog_boundary` | `LOW` |
| **`INFERRED_PROXY`** | `graduation_proxy` | 8 | `observational_activity_boundary` | `LOW` |
| **`INFERRED_PROXY`** | `hiatus_proxy` | 32 | `observational_inactivity_threshold` | `LOW` |
| **`VERIFIED`** | `graduation` | 1 | `verified_video_stream` | `HIGH` |
| **`VERIFIED`** | `re_debut` | 1 | `verified_video_stream` | `HIGH` |

**Total Lifecycle Events:** 226
- **Verified Events:** 2
- **Inferred Proxy Events:** 224

---

## 2. Verified Lifecycle Events

| Channel / Entity | Event Type | Event Date | Agency | Evidence Source | Verification Status |
| :--- | :--- | :---: | :--- | :--- | :---: |
| **UC3ZglUA0HEUCuGbe5b8zXKw** | `re_debut` | 2022-01-17 | Independent | video_catalog.csv: 【Re-Debut : การกลับมาของลูปัสแอลลล】 | `VERIFIED` |
| **UC32lsx7u7vqy63SguuuzmVg** | `graduation` | 2025-12-20 | Independent | video_catalog.csv: 【🔴[Graduation] Last Expedition —เพราะเราเดินทางด้วยกัน | `VERIFIED` |

---

## 3. Channel Lifecycle Intervals Overview

- **Total Channels Modeled:** 193
- **Total Intervals Built:** 237
- **Interval Breakdown by Status & Verification:**

| Lifecycle Status | Verification Status | Interval Count | Effective Agency Assignment |
| :--- | :--- | :---: | :--- |
| `active` | `INFERRED_PROXY` | 186 | Unknown (Agency not projected backward) |
| `active` | `UNKNOWN` | 1 | Unknown (Agency not projected backward) |
| `graduated` | `INFERRED_PROXY` | 8 | Unknown (Agency not projected backward) |
| `graduated` | `UNKNOWN` | 4 | Unknown (Agency not projected backward) |
| `hiatus` | `INFERRED_PROXY` | 32 | Unknown (Agency not projected backward) |
| `hiatus` | `UNKNOWN` | 1 | Unknown (Agency not projected backward) |
| `unknown` | `UNKNOWN` | 5 | Unknown (Agency not projected backward) |

---

## 4. Key Epistemic Principles
1. **Observational Bounds are not Biographical Milestones:** YouTube collection cutoff (such as the 1,000 video cap or playlist exhaustion) records data availability, not creator biography.
2. **Temporal SNA Grounding:** By separating verified dates from observational proxies, subsequent network analysis (T9 event impact, T10 robustness) can evaluate shock effects against genuine empirical anchors without confounding observational artifacts.

---
*Report generated automatically by `scripts/build_historical_lifecycle.py`.*
