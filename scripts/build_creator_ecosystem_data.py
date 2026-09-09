#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds normalized public creator snapshot for Research v2:
- data/industry/creator_public_snapshot.parquet

CANONICAL WRITER GOVERNANCE:
- scripts/build_creator_lifecycle_evidence.py is the SOLE CANONICAL WRITER
  for creator_status_events.parquet, creator_status_events.csv, and creator_evidence_coverage.parquet.
- This module MUST NOT write creator_status_events.*.
- It derives creator_public_snapshot strictly from canonical lifecycle evidence.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

TARGET_MANIFEST_CSV = ROOT / "data/temporal/catalog/target_manifest.csv"
CHANNEL_COVERAGE_PARQUET = ROOT / "data/temporal/catalog/channel_coverage.parquet"
REGISTRY_JSON = ROOT / "data/thai_vtuber_registry.json"
CANONICAL_EVENTS_PARQUET = ROOT / "data/industry/creator_status_events.parquet"
CANONICAL_COVERAGE_PARQUET = ROOT / "data/industry/creator_evidence_coverage.parquet"

INDUSTRY_DIR = ROOT / "data/industry"
INDUSTRY_DIR.mkdir(parents=True, exist_ok=True)

OUT_SNAPSHOT_PARQUET = INDUSTRY_DIR / "creator_public_snapshot.parquet"


def build_creator_public_snapshot() -> pd.DataFrame:
    """Builds creator_public_snapshot.parquet derived from canonical lifecycle evidence."""
    print("Loading canonical lifecycle evidence and target manifest...")
    targets_df = pd.read_csv(TARGET_MANIFEST_CSV)
    coverage_df = pd.read_parquet(CHANNEL_COVERAGE_PARQUET)
    with open(REGISTRY_JSON, "r", encoding="utf-8") as f:
        registry_data = json.load(f)
    registry_map = {r["channel_id"]: r for r in registry_data}
    
    # Load canonical lifecycle evidence
    canonical_cov_df = pd.read_parquet(CANONICAL_COVERAGE_PARQUET)
    canonical_cov_map = {r["creator_channel_id"]: r for _, r in canonical_cov_df.iterrows()}
    canonical_events_df = pd.read_parquet(CANONICAL_EVENTS_PARQUET)
    
    # Identify channels with verified primary or secondary status events
    verified_cids = set()
    grad_cids = set()
    unavail_cids = set()
    
    for _, ev in canonical_events_df.iterrows():
        cid = ev["creator_channel_id"]
        etype = str(ev.get("event_type", "")).upper()
        tier = str(ev.get("evidence_tier", "")).upper()
        if tier in ["PRIMARY_EVENT_SPECIFIC", "SECONDARY_DOCUMENTED"]:
            verified_cids.add(cid)
            if "GRAD" in etype:
                grad_cids.add(cid)
            if "UNAVAILABLE" in etype or "TERMINATION" in etype:
                unavail_cids.add(cid)

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
    snapshot_df.to_parquet(OUT_SNAPSHOT_PARQUET, index=False)
    print(f"Saved {OUT_SNAPSHOT_PARQUET} ({len(snapshot_df)} rows) derived from canonical lifecycle evidence.")
    return snapshot_df


def build_creator_datasets():
    """Deprecated alias: delegates to build_creator_public_snapshot."""
    return build_creator_public_snapshot()


if __name__ == "__main__":
    build_creator_public_snapshot()
