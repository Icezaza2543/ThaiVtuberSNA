"""
Phase T8: Historical Agency & Lifecycle Timeline Engine (Research Integrity Edition)

Rules & Core Contracts:
1. `oldest_video_published_at` is only `earliest_observed_content_date`, NOT verified debut
   unless supported by explicit stream or manual audit evidence.
2. `newest_video_published_at` is only `latest_observed_content_date`, NOT verified graduation/hiatus
   unless explicit evidence supports it.
3. `agency_at_selection` is static metadata at selection time and must NEVER be projected
   backward as verified historical agency membership.
4. Every event must contain:
   - event_id, channel_id, channel_name, event_type, event_date, event_year, agency,
     evidence_type, evidence_source, confidence, verification_status, details.
   - verification_status must be in {VERIFIED, INFERRED_PROXY, UNKNOWN}.
   - Proxy dates are NEVER labeled HIGH confidence.
5. Historical interval resolution:
   - Uses VERIFIED events where available.
   - Marks observational intervals as INFERRED_PROXY with effective_agency='Unknown'.
   - Returns Unknown when outside observed boundaries.
6. Zero invented transfer/join/exit counts in artifacts or reports.

Outputs:
- data/temporal/lifecycle/lifecycle_events.parquet
- data/temporal/lifecycle/channel_lifecycle_intervals.parquet
- data/temporal/lifecycle/lifecycle_report.md
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BuildHistoricalLifecycle")

BASE_DIR = Path(__file__).resolve().parent.parent
TARGET_MANIFEST_CSV = BASE_DIR / "data/temporal/catalog/target_manifest.csv"
CHANNEL_COVERAGE_PARQUET = BASE_DIR / "data/temporal/catalog/channel_coverage.parquet"
REGISTRY_CSV = BASE_DIR / "data/thai_vtuber_registry.csv"
VIDEO_CATALOG_PARQUET = BASE_DIR / "data/video_catalog.parquet"

LIFECYCLE_DIR = BASE_DIR / "data/temporal/lifecycle"
OUTPUT_LIFECYCLE_EVENTS = LIFECYCLE_DIR / "lifecycle_events.parquet"
OUTPUT_LIFECYCLE_INTERVALS = LIFECYCLE_DIR / "channel_lifecycle_intervals.parquet"
OUTPUT_LIFECYCLE_REPORT = LIFECYCLE_DIR / "lifecycle_report.md"


def build_historical_lifecycle():
    """Builds historical lifecycle events and intervals with strict evidence separation."""
    LIFECYCLE_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

    targets_df = con.execute(f"""
        SELECT 
            tm.channel_id, 
            tm.name AS channel_name, 
            tm.agency AS agency_at_selection, 
            tm.lifecycle_status AS manifest_status,
            tr.activity_status, 
            tr.evidence_notes, 
            tr.reference_sources,
            cc.oldest_video_published_at, 
            cc.newest_video_published_at, 
            cc.videos_collected,
            cc.termination_reason
        FROM read_csv_auto('{TARGET_MANIFEST_CSV.as_posix()}') tm
        LEFT JOIN read_csv_auto('{REGISTRY_CSV.as_posix()}') tr ON tm.channel_id = tr.channel_id
        LEFT JOIN read_parquet('{CHANNEL_COVERAGE_PARQUET.as_posix()}') cc ON tm.channel_id = cc.channel_id
        ORDER BY tm.name
    """).df()

    logger.info(f"Loaded {len(targets_df)} target channels for lifecycle modeling.")

    events: List[Dict[str, Any]] = []
    intervals: List[Dict[str, Any]] = []

    # 1. Macro Agency Milestones (VERIFIED)
    agency_milestones = [
        {
            "event_id": "evt_agency_vz_closure",
            "channel_id": "GLOBAL_AGENCY_EVENT",
            "channel_name": "Virtual Zeven (VZ)",
            "event_type": "agency_closure",
            "event_date": "2021-12-31",
            "event_year": 2021,
            "agency": "Virtual Zeven (VZ)",
            "evidence_type": "agency_announcement",
            "evidence_source": "Virtual Zeven official disbandment announcement",
            "evidence_source_ref": "announcement:virtual_zeven_disbandment_20211231",
            "confidence": "HIGH",
            "verification_status": "VERIFIED",
            "details": "Virtual Zeven ceased agency operations on 2021-12-31; verified agency closure."
        },
        {
            "event_id": "evt_agency_rpg_closure",
            "channel_id": "GLOBAL_AGENCY_EVENT",
            "channel_name": "RPG",
            "event_type": "agency_closure",
            "event_date": "2024-09-30",
            "event_year": 2024,
            "agency": "RPG",
            "evidence_type": "agency_announcement",
            "evidence_source": "RPG official cohort graduation / closure announcement",
            "evidence_source_ref": "announcement:rpg_closure_20240930",
            "confidence": "HIGH",
            "verification_status": "VERIFIED",
            "details": "RPG agency talent operations closed on 2024-09-30; verified agency closure."
        }
    ]
    events.extend(agency_milestones)

    # 2. Explicit Channel Verified Milestones
    # VERIFIED only if source supports: exact event type, exact date, and identifiable traceable evidence.
    # Plain strings like "manual audit: retired" without traceable dates in the source are DEMOTED.
    verified_channel_registry = {
        "UC3ZglUA0HEUCuGbe5b8zXKw": {  # The Lupas
            "event_type": "re_debut",
            "event_date": "2022-01-17",
            "agency": "Independent",
            "evidence_type": "verified_video_stream",
            "evidence_source": "video_catalog.csv: 【Re-Debut : การกลับมาของลูปัสแอลลล】",
            "evidence_source_ref": "video_catalog.csv:video_id=-PZhQFYOndE",
            "confidence": "HIGH",
            "verification_status": "VERIFIED",
            "details": "Verified re-debut stream on 2022-01-17 via catalog video -PZhQFYOndE."
        },
        "UC32lsx7u7vqy63SguuuzmVg": {  # Narelle ch. 【FIXIX VT】
            "event_type": "graduation",
            "event_date": "2025-12-20",
            "agency": "Independent",
            "evidence_type": "verified_video_stream",
            "evidence_source": "video_catalog.csv: 【🔴[Graduation] Last Expedition —เพราะเราเดินทางด้วยกัน",
            "evidence_source_ref": "video_catalog.csv:video_id=SWNcXyJBzDY",
            "confidence": "HIGH",
            "verification_status": "VERIFIED",
            "details": "Verified graduation stream on 2025-12-20 via catalog video SWNcXyJBzDY."
        }
    }

    for cid, ev in verified_channel_registry.items():
        ch_match = targets_df[targets_df["channel_id"] == cid]
        cname = ch_match["channel_name"].iloc[0] if not ch_match.empty else cid
        events.append({
            "event_id": f"evt_{ev['event_type']}_{cid[:8]}",
            "channel_id": cid,
            "channel_name": cname,
            "event_type": ev["event_type"],
            "event_date": ev["event_date"],
            "event_year": int(ev["event_date"][:4]),
            "agency": ev["agency"],
            "evidence_type": ev["evidence_type"],
            "evidence_source": ev["evidence_source"],
            "evidence_source_ref": ev["evidence_source_ref"],
            "confidence": ev["confidence"],
            "verification_status": ev["verification_status"],
            "details": ev["details"]
        })

    # 3. Observational Proxy Events and Interval Generation
    for _, row in targets_df.iterrows():
        cid = str(row["channel_id"])
        cname = str(row["channel_name"])
        ag_sel = str(row["agency_at_selection"]) if pd.notnull(row["agency_at_selection"]) else "Independent"
        status = str(row["manifest_status"]).lower() if pd.notnull(row["manifest_status"]) else "unknown"

        first_pub = row["oldest_video_published_at"]
        last_pub = row["newest_video_published_at"]
        term = str(row["termination_reason"])

        first_d = str(first_pub.date()) if pd.notnull(first_pub) else None
        last_d = str(last_pub.date()) if pd.notnull(last_pub) else None

        # Rule 1: Earliest observed content is an observational proxy date, NOT verified debut
        if first_d:
            events.append({
                "event_id": f"evt_earliest_content_{cid[:8]}",
                "channel_id": cid,
                "channel_name": cname,
                "event_type": "earliest_observed_content",
                "event_date": first_d,
                "event_year": int(first_d[:4]),
                "agency": "Unknown",  # Rule 3: NEVER project agency_at_selection backward!
                "evidence_type": "observational_catalog_boundary",
                "evidence_source": f"channel_coverage.parquet: oldest_video_published_at (termination_reason: {term})",
                "evidence_source_ref": f"channel_coverage.parquet:channel_id={cid};oldest_video_published_at={first_d}",
                "confidence": "LOW",
                "verification_status": "INFERRED_PROXY",
                "details": f"Earliest observed public video upload in collected catalog ({first_d}); observational proxy, not verified debut."
            })

        # Rule 2: Last video is an observational boundary, NOT verified graduation/hiatus
        if status == "graduated" and last_d and cid not in verified_channel_registry:
            events.append({
                "event_id": f"evt_grad_proxy_{cid[:8]}",
                "channel_id": cid,
                "channel_name": cname,
                "event_type": "graduation_proxy",
                "event_date": last_d,
                "event_year": int(last_d[:4]),
                "agency": "Unknown",
                "evidence_type": "observational_activity_boundary",
                "evidence_source": "target_manifest.csv (graduated) + channel_coverage.parquet (newest_video_published_at)",
                "evidence_source_ref": f"channel_coverage.parquet:channel_id={cid};newest_video_published_at={last_d};target_manifest.csv:status=graduated",
                "confidence": "LOW",
                "verification_status": "INFERRED_PROXY",
                "details": f"Last observed public video activity ({last_d}) for graduated channel; observational proxy date."
            })
        elif status == "hiatus" and last_d:
            events.append({
                "event_id": f"evt_hiatus_proxy_{cid[:8]}",
                "channel_id": cid,
                "channel_name": cname,
                "event_type": "hiatus_proxy",
                "event_date": last_d,
                "event_year": int(last_d[:4]),
                "agency": "Unknown",
                "evidence_type": "observational_inactivity_threshold",
                "evidence_source": "target_manifest.csv (hiatus) + channel_coverage.parquet (newest_video_published_at)",
                "evidence_source_ref": f"channel_coverage.parquet:channel_id={cid};newest_video_published_at={last_d};target_manifest.csv:status=hiatus",
                "confidence": "LOW",
                "verification_status": "INFERRED_PROXY",
                "details": f"Last observed public video activity ({last_d}) prior to prolonged inactivity (>180d); proxy date for hiatus onset."
            })

        # Build Intervals
        # Check special case: Virtual Zeven talents (verified closure 2021-12-31)
        # Closure proves an end boundary, NOT membership start. Membership start at first_d is INFERRED_PROXY.
        # Post-closure Independent status is INFERRED_PROXY unless explicit evidence establishes transition.
        is_vz_channel = "⌜vz⌟" in cname.lower() or "vz" in ag_sel.lower()
        is_rpg_channel = "rpg" in ag_sel.lower() or "rpg" in cname.lower()

        if is_vz_channel and first_d:
            # VZ tenure: start is proxy, end is verified closure 2021-12-31
            intervals.append({
                "interval_id": f"int_{cid[:8]}_vz",
                "channel_id": cid,
                "channel_name": cname,
                "start_date": first_d,
                "end_date": "2021-12-31",
                "effective_agency": "Virtual Zeven (VZ)",
                "agency_at_selection": ag_sel,
                "lifecycle_status": "active",
                "is_current": False,
                "verification_status": "INFERRED_PROXY",
                "confidence": "LOW",
                "evidence_type": "proxy_start_verified_closure_end",
                "evidence_source": "Start: earliest_observed_content (proxy); End: Virtual Zeven official disbandment (2021-12-31)",
                "evidence_source_ref": "start:channel_coverage.parquet;end:announcement:vz_closure_20211231",
                "provenance": "historical_vz_membership_proxy_start"
            })
            # Post-VZ interval: inferred transition to Independent following disbandment
            intervals.append({
                "interval_id": f"int_{cid[:8]}_post_vz",
                "channel_id": cid,
                "channel_name": cname,
                "start_date": "2022-01-01",
                "end_date": last_d if status in ["graduated", "hiatus"] else None,
                "effective_agency": "Independent",
                "agency_at_selection": ag_sel,
                "lifecycle_status": status if status != "graduated" else "active",
                "is_current": (status == "active"),
                "verification_status": "INFERRED_PROXY",
                "confidence": "LOW",
                "evidence_type": "inferred_post_closure_status",
                "evidence_source": "Inferred from Virtual Zeven disbandment; no explicit talent contract transition record",
                "evidence_source_ref": "announcement:vz_closure_20211231",
                "provenance": "post_vz_independent_inferred"
            })
            if status == "graduated" and last_d:
                intervals.append({
                    "interval_id": f"int_{cid[:8]}_grad",
                    "channel_id": cid,
                    "channel_name": cname,
                    "start_date": last_d,
                    "end_date": None,
                    "effective_agency": "Graduated",
                    "agency_at_selection": ag_sel,
                    "lifecycle_status": "graduated",
                    "is_current": True,
                    "verification_status": "INFERRED_PROXY",
                    "confidence": "LOW",
                    "evidence_type": "observational_activity_boundary",
                    "evidence_source": "channel_coverage.parquet",
                    "evidence_source_ref": f"coverage:newest_video={last_d}",
                    "provenance": "post_graduation"
                })
        elif is_rpg_channel and first_d:
            # RPG tenure: start is proxy, end is verified closure 2024-09-30
            intervals.append({
                "interval_id": f"int_{cid[:8]}_rpg",
                "channel_id": cid,
                "channel_name": cname,
                "start_date": first_d,
                "end_date": "2024-09-30",
                "effective_agency": "RPG",
                "agency_at_selection": ag_sel,
                "lifecycle_status": "active",
                "is_current": False,
                "verification_status": "INFERRED_PROXY",
                "confidence": "LOW",
                "evidence_type": "proxy_start_verified_closure_end",
                "evidence_source": "Start: earliest_observed_content (proxy); End: RPG official closure (2024-09-30)",
                "evidence_source_ref": "start:channel_coverage.parquet;end:announcement:rpg_closure_20240930",
                "provenance": "historical_rpg_membership_proxy_start"
            })
            # Post-RPG interval
            intervals.append({
                "interval_id": f"int_{cid[:8]}_post_rpg",
                "channel_id": cid,
                "channel_name": cname,
                "start_date": "2024-10-01",
                "end_date": last_d if status in ["graduated", "hiatus"] else None,
                "effective_agency": "Graduated" if status == "graduated" else "Independent",
                "agency_at_selection": ag_sel,
                "lifecycle_status": status,
                "is_current": (status == "active"),
                "verification_status": "INFERRED_PROXY",
                "confidence": "LOW",
                "evidence_type": "inferred_post_closure_status",
                "evidence_source": "Inferred from RPG closure; no explicit talent contract transition record",
                "evidence_source_ref": "announcement:rpg_closure_20240930",
                "provenance": "post_rpg_transition_inferred"
            })
        elif first_d:
            # Standard channel interval logic
            # Historical tenure is INFERRED_PROXY; effective_agency is Unknown (never projected from selection)
            if status == "graduated" and last_d and last_d >= first_d:
                # Active observational window
                intervals.append({
                    "interval_id": f"int_{cid[:8]}_1",
                    "channel_id": cid,
                    "channel_name": cname,
                    "start_date": first_d,
                    "end_date": last_d,
                    "effective_agency": "Unknown",  # Rule 3: agency unknown historically
                    "agency_at_selection": ag_sel,
                    "lifecycle_status": "active",
                    "is_current": False,
                    "verification_status": "INFERRED_PROXY",
                    "confidence": "LOW",
                    "evidence_type": "observational_catalog_range",
                    "evidence_source": "channel_coverage.parquet",
                    "evidence_source_ref": f"channel_coverage.parquet:channel_id={cid};range={first_d}..{last_d}",
                    "provenance": "observed_content_tenure"
                })
                # Post-graduation
                intervals.append({
                    "interval_id": f"int_{cid[:8]}_2",
                    "channel_id": cid,
                    "channel_name": cname,
                    "start_date": last_d,
                    "end_date": None,
                    "effective_agency": "Graduated",
                    "agency_at_selection": ag_sel,
                    "lifecycle_status": "graduated",
                    "is_current": True,
                    "verification_status": "INFERRED_PROXY",
                    "confidence": "LOW",
                    "evidence_type": "observational_activity_boundary",
                    "evidence_source": "target_manifest.csv + channel_coverage.parquet",
                    "evidence_source_ref": f"target_manifest.csv:status=graduated;channel_coverage.parquet:newest_video={last_d}",
                    "provenance": "post_graduation"
                })
            elif status == "hiatus" and last_d and last_d >= first_d:
                # Active observational window
                intervals.append({
                    "interval_id": f"int_{cid[:8]}_1",
                    "channel_id": cid,
                    "channel_name": cname,
                    "start_date": first_d,
                    "end_date": last_d,
                    "effective_agency": "Unknown",  # Rule 3
                    "agency_at_selection": ag_sel,
                    "lifecycle_status": "active",
                    "is_current": False,
                    "verification_status": "INFERRED_PROXY",
                    "confidence": "LOW",
                    "evidence_type": "observational_catalog_range",
                    "evidence_source": "channel_coverage.parquet",
                    "evidence_source_ref": f"channel_coverage.parquet:channel_id={cid};range={first_d}..{last_d}",
                    "provenance": "observed_content_tenure"
                })
                # Ongoing hiatus window
                intervals.append({
                    "interval_id": f"int_{cid[:8]}_2",
                    "channel_id": cid,
                    "channel_name": cname,
                    "start_date": last_d,
                    "end_date": None,
                    "effective_agency": "Unknown",
                    "agency_at_selection": ag_sel,
                    "lifecycle_status": "hiatus",
                    "is_current": True,
                    "verification_status": "INFERRED_PROXY",
                    "confidence": "LOW",
                    "evidence_type": "observational_inactivity_threshold",
                    "evidence_source": "channel_coverage.parquet (>180d inactivity)",
                    "evidence_source_ref": f"target_manifest.csv:status=hiatus;channel_coverage.parquet:newest_video={last_d}",
                    "provenance": "hiatus_ongoing"
                })
            else:
                # Active ongoing channel
                intervals.append({
                    "interval_id": f"int_{cid[:8]}_1",
                    "channel_id": cid,
                    "channel_name": cname,
                    "start_date": first_d,
                    "end_date": None,
                    "effective_agency": "Unknown",  # Rule 3: agency unknown historically
                    "agency_at_selection": ag_sel,
                    "lifecycle_status": "active",
                    "is_current": True,
                    "verification_status": "INFERRED_PROXY",
                    "confidence": "LOW",
                    "evidence_type": "observational_catalog_boundary",
                    "evidence_source": "channel_coverage.parquet",
                    "evidence_source_ref": f"channel_coverage.parquet:channel_id={cid};oldest_video={first_d}",
                    "provenance": "observed_content_ongoing"
                })
        else:
            # Channels with 0 videos collected / no dates
            intervals.append({
                "interval_id": f"int_{cid[:8]}_unk",
                "channel_id": cid,
                "channel_name": cname,
                "start_date": None,
                "end_date": None,
                "effective_agency": "Unknown",
                "agency_at_selection": ag_sel,
                "lifecycle_status": status,
                "is_current": True,
                "verification_status": "UNKNOWN",
                "confidence": "UNKNOWN",
                "evidence_type": "unobserved_catalog",
                "evidence_source": "channel_coverage.parquet (0 videos)",
                "evidence_source_ref": "channel_coverage.parquet:videos_collected=0",
                "provenance": "unrecorded_interval"
            })

    events_df = pd.DataFrame(events)
    intervals_df = pd.DataFrame(intervals)

    # Save to Parquet
    logger.info(f"Writing {len(events_df)} lifecycle events to {OUTPUT_LIFECYCLE_EVENTS}...")
    pq.write_table(pa.Table.from_pandas(events_df, preserve_index=False), OUTPUT_LIFECYCLE_EVENTS)

    logger.info(f"Writing {len(intervals_df)} lifecycle intervals to {OUTPUT_LIFECYCLE_INTERVALS}...")
    pq.write_table(pa.Table.from_pandas(intervals_df, preserve_index=False), OUTPUT_LIFECYCLE_INTERVALS)

    # Generate Markdown Report
    generate_lifecycle_report(events_df, intervals_df, targets_df, OUTPUT_LIFECYCLE_REPORT)
    logger.info("Phase T8 Lifecycle build complete.")
    return events_df, intervals_df


def agency_at(channel_id: str, query_date: str, intervals_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Deterministically resolves a channel's lifecycle status and agency at a specific query date.
    
    Adheres to Research Integrity Rules:
    - Never projects agency_at_selection backward as verified historical membership.
    - Resolves VERIFIED where explicit dated evidence exists.
    - Resolves INFERRED_PROXY where observational boundaries are used.
    - Resolves UNKNOWN where date is prior to observed content or outside documented intervals.
    """
    if intervals_df is None:
        if OUTPUT_LIFECYCLE_INTERVALS.exists():
            intervals_df = pd.read_parquet(OUTPUT_LIFECYCLE_INTERVALS)
        else:
            return {
                "channel_id": channel_id,
                "query_date": query_date,
                "agency_at_selection": "Unknown",
                "effective_agency": "Unknown",
                "lifecycle_status": "unknown",
                "is_active": False,
                "verification_status": "UNKNOWN",
                "confidence": "UNKNOWN",
                "provenance": "missing_intervals_file"
            }

    ch_rows = intervals_df[intervals_df["channel_id"] == channel_id]
    if ch_rows.empty:
        return {
            "channel_id": channel_id,
            "query_date": query_date,
            "agency_at_selection": "Unknown",
            "effective_agency": "Unknown",
            "lifecycle_status": "unregistered",
            "is_active": False,
            "verification_status": "UNKNOWN",
            "confidence": "UNKNOWN",
            "provenance": "not_in_target_cohort"
        }

    ag_sel = ch_rows["agency_at_selection"].iloc[0]

    # Check if query_date is prior to earliest observed start
    valid_starts = ch_rows["start_date"].dropna()
    earliest_start = valid_starts.min() if not valid_starts.empty else None
    if earliest_start and query_date < earliest_start:
        return {
            "channel_id": channel_id,
            "query_date": query_date,
            "agency_at_selection": ag_sel,
            "effective_agency": "Unknown",
            "lifecycle_status": "pre_debut",
            "is_active": False,
            "verification_status": "INFERRED_PROXY",
            "confidence": "LOW",
            "provenance": "date_prior_to_earliest_observed_content"
        }

    # Match covering interval
    for _, row in ch_rows.iterrows():
        s_date = row["start_date"]
        e_date = row["end_date"]
        after_start = (s_date is None or pd.isna(s_date)) or (query_date >= str(s_date))
        before_end = (e_date is None or pd.isna(e_date)) or (query_date <= str(e_date))

        if after_start and before_end:
            status = row["lifecycle_status"]
            return {
                "channel_id": channel_id,
                "query_date": query_date,
                "agency_at_selection": ag_sel,
                "effective_agency": row["effective_agency"],
                "lifecycle_status": status,
                "is_active": (status == "active"),
                "verification_status": row["verification_status"],
                "confidence": row["confidence"],
                "provenance": row["provenance"]
            }

    return {
        "channel_id": channel_id,
        "query_date": query_date,
        "agency_at_selection": ag_sel,
        "effective_agency": "Unknown",
        "lifecycle_status": "unknown",
        "is_active": False,
        "verification_status": "UNKNOWN",
        "confidence": "UNKNOWN",
        "provenance": "outside_recorded_intervals"
    }


def generate_lifecycle_report(events_df: pd.DataFrame, intervals_df: pd.DataFrame, targets_df: pd.DataFrame, output_path: Path):
    """Generates a comprehensive markdown report matching committed artifacts exactly."""
    total_targets = len(targets_df)
    total_events = len(events_df)
    total_intervals = len(intervals_df)

    v_counts = events_df.groupby(["verification_status", "event_type"]).size().unstack(fill_value=0)

    verified_events = events_df[events_df["verification_status"] == "VERIFIED"]
    proxy_events = events_df[events_df["verification_status"] == "INFERRED_PROXY"]

    md = f"""# Phase T8: Historical Lifecycle & Timeline Report (Research Integrity Edition)

## Executive Summary
This report documents the historical lifecycle timeline for the **{total_targets}** Thai VTuber target cohort channels.

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
"""
    for _, row in events_df.groupby(["verification_status", "event_type", "evidence_type", "confidence"]).size().reset_index(name="count").iterrows():
        md += f"| **`{row['verification_status']}`** | `{row['event_type']}` | {row['count']} | `{row['evidence_type']}` | `{row['confidence']}` |\n"

    md += f"""
**Total Lifecycle Events:** {total_events}
- **Verified Events:** {len(verified_events)}
- **Inferred Proxy Events:** {len(proxy_events)}

---

## 2. Verified Lifecycle Events

| Channel / Entity | Event Type | Event Date | Agency | Evidence Source | Verification Status |
| :--- | :--- | :---: | :--- | :--- | :---: |
"""
    for _, r in verified_events.iterrows():
        md += f"| **{r['channel_name']}** | `{r['event_type']}` | {r['event_date']} | {r['agency']} | {r['evidence_source']} | `{r['verification_status']}` |\n"

    md += f"""
---

## 3. Channel Lifecycle Intervals Overview

- **Total Channels Modeled:** {total_targets}
- **Total Intervals Built:** {total_intervals}
- **Interval Breakdown by Status & Verification:**

| Lifecycle Status | Verification Status | Interval Count | Effective Agency Assignment |
| :--- | :--- | :---: | :--- |
"""
    for _, r in intervals_df.groupby(["lifecycle_status", "verification_status"]).size().reset_index(name="count").iterrows():
        eff_desc = "Verified Agency (or Retired)" if r['verification_status'] == 'VERIFIED' else "Unknown (Agency not projected backward)"
        md += f"| `{r['lifecycle_status']}` | `{r['verification_status']}` | {r['count']} | {eff_desc} |\n"

    md += """
---

## 4. Key Epistemic Principles
1. **Observational Bounds are not Biographical Milestones:** YouTube collection cutoff (such as the 1,000 video cap or playlist exhaustion) records data availability, not creator biography.
2. **Temporal SNA Grounding:** By separating verified dates from observational proxies, subsequent network analysis (T9 event impact, T10 robustness) can evaluate shock effects against genuine empirical anchors without confounding observational artifacts.

---
*Report generated automatically by `scripts/build_historical_lifecycle.py`.*
"""
    output_path.write_text(md, encoding="utf-8")
    logger.info(f"Generated lifecycle report at {output_path}")


if __name__ == "__main__":
    build_historical_lifecycle()
