"""Public creator snapshot transformation; activity and lifecycle tiers remain separate."""
from typing import Any, Dict, List
import pandas as pd


def build_snapshot_frame(targets_df, coverage_df, registry_data, canonical_cov_df, canonical_events_df):
    """Return the existing snapshot schema without reading or writing artifacts."""
    registry_map = {r["channel_id"]: r for r in registry_data}
    canonical_cov_map = {r["creator_channel_id"]: r for _, r in canonical_cov_df.iterrows()}
    # Merge channel coverage dates
    merged = targets_df.merge(
        coverage_df[["channel_id", "oldest_video_published_at", "newest_video_published_at"]],
        on="channel_id",
        how="left"
    )

    snapshot_records: List[Dict[str, Any]] = []

    for _, row in merged.iterrows():
        cid = row["channel_id"]
        cname = row["name"]
        agency = row.get("agency", "Independent")
        tier = row.get("tier_at_selection", "Tier 2")
        manifest_status = row.get("lifecycle_status", "active")
        oldest = str(row.get("oldest_video_published_at", ""))[:10] if pd.notna(row.get("oldest_video_published_at")) else "Unknown"
        newest = str(row.get("newest_video_published_at", ""))[:10] if pd.notna(row.get("newest_video_published_at")) else "Unknown"

        reg_info = registry_map.get(cid, {})
        handle = reg_info.get("handle", "")
        sub_count = int(reg_info.get("subscriber_count", 0)) if pd.notna(reg_info.get("subscriber_count")) else 0
        vid_count = int(reg_info.get("video_count", 0)) if pd.notna(reg_info.get("video_count")) else 0
        view_count = int(reg_info.get("view_count", 0)) if pd.notna(reg_info.get("view_count")) else 0

        # Classify agency type
        if agency in ("Independent", "Unknown", None, ""):
            agency_type = "INDEPENDENT"
        elif agency in ("Polygon Official", "Algorhythm Project", "Pixela Project", "AStars Production", "Virtual Zeven (VZ)", "RPG", "Flora Project", "Euphora Project"):
            agency_type = "AGENCY"
        else:
            agency_type = "COMMUNITY_OR_GROUP"

        # Determine activity and verification status from canonical evidence
        cov_entry = canonical_cov_map.get(cid, {})
        canonical_status = cov_entry.get("lifecycle_status", manifest_status)

        # Activity is a frozen selection observation, never evidence of legal lifecycle status.
        act_state = "ACTIVE_OBSERVED" if canonical_status == "active" else str(canonical_status).upper() + "_OBSERVED"
        tiers = set(canonical_events_df.loc[canonical_events_df.creator_channel_id == cid, "evidence_tier"])
        verif_stat = next((t for t in ("PRIMARY_EVENT_SPECIFIC", "SECONDARY_DOCUMENTED", "INFERRED_PROXY") if t in tiers), "UNKNOWN")

        snapshot_records.append({
            "channel_id": cid,
            "creator_name": cname,
            "handle": handle,
            "agency": agency,
            "agency_type": agency_type,
            "selection_tier": tier,
            "is_target_cohort": True,
            "first_observed_date": oldest,
            "latest_observed_date": newest,
            "activity_status": act_state,
            "verification_status": verif_stat,
            "activity_status_source": "MANIFEST_AT_SELECTION",
            "lifecycle_evidence_tier": verif_stat,
            "subscriber_count": sub_count,
            "video_count": vid_count,
            "view_count": view_count,
            "snapshot_date": "2026-09-08"
        })

    snapshot_df = pd.DataFrame(snapshot_records).sort_values(by=["agency_type", "agency", "creator_name"])
    return snapshot_df
