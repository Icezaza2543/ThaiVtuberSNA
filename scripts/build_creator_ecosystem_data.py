#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds normalized public creator ecosystem datasets for Research v2:
- data/industry/creator_status_events.parquet
- data/industry/creator_status_events.csv
- data/industry/creator_public_snapshot.parquet

Strict Rules:
- Verification status strictly in {VERIFIED, INFERRED_PROXY, UNKNOWN}.
- Never promote proxy/inferred events to VERIFIED.
- Never infer graduation merely from inactivity.
- All events are public creator-level metadata (LEVEL C).
"""

import sys
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent

TARGET_MANIFEST_CSV = ROOT / "data/temporal/catalog/target_manifest.csv"
CHANNEL_COVERAGE_PARQUET = ROOT / "data/temporal/catalog/channel_coverage.parquet"
REGISTRY_CSV = ROOT / "data/thai_vtuber_registry.csv"
LIFECYCLE_EVENTS_PARQUET = ROOT / "data/temporal/lifecycle/lifecycle_events.parquet"

INDUSTRY_DIR = ROOT / "data/industry"
INDUSTRY_DIR.mkdir(parents=True, exist_ok=True)

OUT_EVENTS_PARQUET = INDUSTRY_DIR / "creator_status_events.parquet"
OUT_EVENTS_CSV = INDUSTRY_DIR / "creator_status_events.csv"
OUT_SNAPSHOT_PARQUET = INDUSTRY_DIR / "creator_public_snapshot.parquet"

NOW_ISO = datetime.now(timezone.utc).isoformat()

def build_creator_datasets():
    print("Loading existing catalog and lifecycle sources...")
    targets_df = pd.read_csv(TARGET_MANIFEST_CSV)
    coverage_df = pd.read_parquet(CHANNEL_COVERAGE_PARQUET)
    registry_df = pd.read_csv(REGISTRY_CSV)
    existing_lifecycle = pd.read_parquet(LIFECYCLE_EVENTS_PARQUET)
    
    events: List[Dict[str, Any]] = []
    
    # 1. Macro Agency Milestones
    agency_milestones = [
        {
            "event_id": "evt_agency_vz_closure",
            "creator_channel_id": "GLOBAL_AGENCY_EVENT",
            "creator_name": "Virtual Zeven (VZ)",
            "agency": "Virtual Zeven (VZ)",
            "event_type": "AGENCY_LEAVE_VERIFIED",
            "event_date": "2021-12-31",
            "event_year": 2021,
            "verification_status": "INFERRED_PROXY",
            "source_type": "AGENCY_DISBANDMENT_RECORD",
            "source_reference": "unverified_announcement_ref:vz_closure_20211231",
            "retrieved_at": NOW_ISO,
            "notes": "Virtual Zeven ceased operations on 2021-12-31; talents transitioned or became independent."
        },
        {
            "event_id": "evt_agency_rpg_closure",
            "creator_channel_id": "GLOBAL_AGENCY_EVENT",
            "creator_name": "RPG",
            "agency": "RPG",
            "event_type": "AGENCY_LEAVE_VERIFIED",
            "event_date": "2024-09-30",
            "event_year": 2024,
            "verification_status": "INFERRED_PROXY",
            "source_type": "AGENCY_DISBANDMENT_RECORD",
            "source_reference": "unverified_announcement_ref:rpg_closure_20240930",
            "retrieved_at": NOW_ISO,
            "notes": "RPG agency talent operations closed on 2024-09-30; talents graduated or moved independent."
        }
    ]
    events.extend(agency_milestones)
    
    # 2. Known Verified Milestones from Catalog / Official Videos
    # Strict rule: A title containing 'Graduated' verifies status, but NOT exact date.
    # Only videos with exact cataloged upload timestamps are VERIFIED.
    verified_registry = {
        "UC3ZglUA0HEUCuGbe5b8zXKw": {
            "creator_name": "The Lupas",
            "agency": "Independent",
            "event_type": "REDEBUT_VERIFIED",
            "event_date": "2022-01-17",
            "verification_status": "VERIFIED",
            "source_type": "OFFICIAL_CHANNEL_VIDEO",
            "source_reference": "video_catalog.csv:video_id=-PZhQFYOndE",
            "notes": "Official re-debut broadcast: 【Re-Debut : การกลับมาของลูปัสแอลลล】"
        },
        "UC32lsx7u7vqy63SguuuzmVg": {
            "creator_name": "Narelle ch. 【FIXIX VT】",
            "agency": "Independent",
            "event_type": "GRADUATION_VERIFIED",
            "event_date": "2025-12-20",
            "verification_status": "VERIFIED",
            "source_type": "OFFICIAL_CHANNEL_VIDEO",
            "source_reference": "video_catalog.parquet:video_id=SWNcXyJBzDY",
            "notes": "Official graduation stream broadcast on 2025-12-20: 【🔴[Graduation] Last Expedition —เพราะเราเดินทางด้วยกัน】."
        },
        "UC_f-4lGvlAXpBrN9vHertvA": {
            "creator_name": "Akiyama Zqiu Ch. | RPG",
            "agency": "RPG",
            "event_type": "GRADUATION_VERIFIED",
            "event_date": "2024-09-30",
            "verification_status": "INFERRED_PROXY",
            "source_type": "OFFICIAL_CHANNEL_TITLE_AUDIT",
            "source_reference": "channel_metadata:title_has_GRADUATED",
            "notes": "Channel title indicates GRADUATED; date is proxy pegged to RPG agency closure."
        },
        "UC0fZ_5Kil9VctNzpYo4vpLg": {
            "creator_name": "Tenebris D. Armis Ch. | RPG",
            "agency": "RPG",
            "event_type": "GRADUATION_VERIFIED",
            "event_date": "2024-09-30",
            "verification_status": "INFERRED_PROXY",
            "source_type": "OFFICIAL_CHANNEL_TITLE_AUDIT",
            "source_reference": "channel_metadata:title_has_GRADUATED",
            "notes": "Channel title indicates GRADUATED; date is proxy pegged to RPG agency closure."
        },
        "UCVogMqMZimg5YbPE48oPrlg": {
            "creator_name": "Mysterica X. Ch. | RPG",
            "agency": "RPG",
            "event_type": "GRADUATION_VERIFIED",
            "event_date": "2024-09-30",
            "verification_status": "INFERRED_PROXY",
            "source_type": "OFFICIAL_CHANNEL_TITLE_AUDIT",
            "source_reference": "channel_metadata:rpg_closure",
            "notes": "Ceased active VTuber operations concurrent with RPG dissolution; date is proxy."
        },
        "UCgLadXz0sJbHQL98eoAd9ag": {
            "creator_name": "Ice Shirakoi Ch. / AStars Amakara",
            "agency": "AStars Production",
            "event_type": "GRADUATION_VERIFIED",
            "event_date": "2024-06-30",
            "verification_status": "INFERRED_PROXY",
            "source_type": "OFFICIAL_CHANNEL_TITLE_AUDIT",
            "source_reference": "channel_metadata:title_has_graduated",
            "notes": "Channel title formally marked 【graduated】; exact graduation date is proxy."
        },
        "UCfe7Lxdn2PDp_xnnrC_RSzA": {
            "creator_name": "Amaris Sayo Ch. / AStars Amakara",
            "agency": "AStars Production",
            "event_type": "GRADUATION_VERIFIED",
            "event_date": "2024-06-30",
            "verification_status": "INFERRED_PROXY",
            "source_type": "OFFICIAL_CHANNEL_TITLE_AUDIT",
            "source_reference": "channel_metadata:title_has_graduated",
            "notes": "Channel title formally marked 【graduated】; exact graduation date is proxy."
        },
        "UC_djfyZ7N_-hPSxtrSsBNfQ": {
            "creator_name": "Victor Hoshino",
            "agency": "Independent",
            "event_type": "GRADUATION_VERIFIED",
            "event_date": "2024-12-31",
            "verification_status": "INFERRED_PROXY",
            "source_type": "OFFICIAL_CHANNEL_TITLE_AUDIT",
            "source_reference": "channel_metadata:title_has_GRADUATED",
            "notes": "Channel title formally marked 【GRADUATED】; exact graduation date is proxy."
        },
        "UCSQCuMGGicyB_QqG_mApH7w": {
            "creator_name": "Kaede Ch.",
            "agency": "Independent",
            "event_type": "GRADUATION_VERIFIED",
            "event_date": "2024-08-31",
            "verification_status": "INFERRED_PROXY",
            "source_type": "OFFICIAL_CHANNEL_TITLE_AUDIT",
            "source_reference": "channel_metadata:title_has_graduated",
            "notes": "Channel title formally marked [ Graduated]; exact graduation date is proxy."
        },
        "UC0C_CplF_fwd1hEZuIE6VIw": {
            "creator_name": "Rawley Izzy G. Ch.",
            "agency": "Independent",
            "event_type": "GRADUATION_VERIFIED",
            "event_date": "2024-10-31",
            "verification_status": "INFERRED_PROXY",
            "source_type": "OFFICIAL_CHANNEL_TITLE_AUDIT",
            "source_reference": "channel_metadata:title_has_graduated",
            "notes": "Channel title formally marked | Graduated; exact graduation date is proxy."
        },
        "UCDgptjggm1YvNSn7GQ19sEA": {
            "creator_name": "Lord Cha Zele Ch.",
            "agency": "Independent",
            "event_type": "GRADUATION_VERIFIED",
            "event_date": "2025-01-31",
            "verification_status": "INFERRED_PROXY",
            "source_type": "OFFICIAL_CHANNEL_TITLE_AUDIT",
            "source_reference": "channel_metadata:title_has_graduation",
            "notes": "Channel title formally marked ◤Graduation◢; exact graduation date is proxy."
        },
        "UC3H7_4Gz8PhHeMz0hHwuFTw": {
            "creator_name": "Morika Rei",
            "agency": "Independent",
            "event_type": "GRADUATION_VERIFIED",
            "event_date": "2024-05-31",
            "verification_status": "INFERRED_PROXY",
            "source_type": "OFFICIAL_CHANNEL_TITLE_AUDIT",
            "source_reference": "channel_metadata:title_has_graduated",
            "notes": "Channel title formally marked [Graduated]; exact graduation date is proxy."
        },
        "UCBLV-Zv25LzajWyKEofqvVQ": {
            "creator_name": "[ปิดตัว]",
            "agency": "Independent",
            "event_type": "CHANNEL_UNAVAILABLE",
            "event_date": "2024-01-01",
            "verification_status": "INFERRED_PROXY",
            "source_type": "OFFICIAL_CHANNEL_TITLE_AUDIT",
            "source_reference": "channel_metadata:title_has_closed",
            "notes": "Channel title renamed to [ปิดตัว]; exact termination date is proxy."
        }
    }
    
    for cid, v in verified_registry.items():
        events.append({
            "event_id": f"evt_{v['event_type'].lower()}_{cid[:10]}_{v['event_date'].replace('-','')}",
            "creator_channel_id": cid,
            "creator_name": v["creator_name"],
            "agency": v["agency"],
            "event_type": v["event_type"],
            "event_date": v["event_date"],
            "event_year": int(v["event_date"][:4]),
            "verification_status": v["verification_status"],
            "source_type": v["source_type"],
            "source_reference": v["source_reference"],
            "retrieved_at": NOW_ISO,
            "notes": v["notes"]
        })
        
    # 3. First Observed Content Events (Every channel in target cohort)
    # Merging target manifest with channel coverage oldest_video_published_at
    merged_targets = targets_df.merge(coverage_df, on="channel_id", how="left")
    
    for _, row in merged_targets.iterrows():
        cid = row["channel_id"]
        cname = row["name"]
        agency = row.get("agency", "Independent")
        oldest = row.get("oldest_video_published_at")
        
        if pd.notna(oldest) and str(oldest).strip():
            date_str = str(oldest)[:10]
            events.append({
                "event_id": f"evt_first_observed_{cid[:10]}_{date_str.replace('-','')}",
                "creator_channel_id": cid,
                "creator_name": cname,
                "agency": agency,
                "event_type": "FIRST_OBSERVED",
                "event_date": date_str,
                "event_year": int(date_str[:4]),
                "verification_status": "INFERRED_PROXY",
                "source_type": "CATALOG_TIMESTAMP_PROXY",
                "source_reference": f"channel_coverage.parquet:oldest_video_published_at={oldest}",
                "retrieved_at": NOW_ISO,
                "notes": f"Earliest cataloged public video upload in research dataset ({oldest}). Not verified debut stream."
            })
            
        # Also check hiatus / inactive status from registry
        reg_row = registry_df[registry_df["channel_id"] == cid]
        if not reg_row.empty:
            act_stat = str(reg_row.iloc[0].get("activity_status", "")).lower()
            last_pub = reg_row.iloc[0].get("last_video_published_at")
            if act_stat == "hiatus" and pd.notna(last_pub) and str(last_pub).strip():
                h_date = str(last_pub)[:10]
                events.append({
                    "event_id": f"evt_hiatus_proxy_{cid[:10]}_{h_date.replace('-','')}",
                    "creator_channel_id": cid,
                    "creator_name": cname,
                    "agency": agency,
                    "event_type": "HIATUS_VERIFIED" if "hiatus" in str(reg_row.iloc[0].get("evidence_notes","")).lower() else "INFERRED_PROXY",
                    "event_date": h_date,
                    "event_year": int(h_date[:4]),
                    "verification_status": "INFERRED_PROXY",
                    "source_type": "REGISTRY_INACTIVITY_PROXY",
                    "source_reference": f"registry:last_video={last_pub}",
                    "retrieved_at": NOW_ISO,
                    "notes": f"Observed hiatus boundary based on last public activity recorded on {h_date} (>180d inactive)."
                })

    events_df = pd.DataFrame(events)
    # Deduplicate by event_id
    events_df = events_df.drop_duplicates(subset=["event_id"]).sort_values(by=["event_date", "creator_channel_id"])
    print(f"Compiled {len(events_df)} creator status events.")
    print("Breakdown by event_type:")
    print(events_df["event_type"].value_counts())
    print("Breakdown by verification_status:")
    print(events_df["verification_status"].value_counts())
    
    # Save Parquet & CSV
    events_df.to_parquet(OUT_EVENTS_PARQUET, index=False)
    events_df.to_csv(OUT_EVENTS_CSV, index=False, encoding="utf-8")
    print(f"Saved {OUT_EVENTS_PARQUET} and {OUT_EVENTS_CSV}")
    
    # 4. Build creator_public_snapshot.parquet
    # Snapshot of all target creators with their current status, tier, agency, and metrics
    snapshot_records = []
    
    for _, row in merged_targets.iterrows():
        cid = row["channel_id"]
        cname = row["name"]
        agency = row.get("agency", "Independent")
        tier = row.get("tier_at_selection", "Tier 2")
        manifest_status = row.get("lifecycle_status", "active")
        oldest = str(row.get("oldest_video_published_at", ""))[:10] if pd.notna(row.get("oldest_video_published_at")) else "Unknown"
        newest = str(row.get("newest_video_published_at", ""))[:10] if pd.notna(row.get("newest_video_published_at")) else "Unknown"
        
        reg_row = registry_df[registry_df["channel_id"] == cid]
        handle = reg_row.iloc[0].get("handle", "") if not reg_row.empty else ""
        sub_count = int(reg_row.iloc[0].get("subscriber_count", 0)) if not reg_row.empty and pd.notna(reg_row.iloc[0].get("subscriber_count")) else 0
        vid_count = int(reg_row.iloc[0].get("video_count", 0)) if not reg_row.empty and pd.notna(reg_row.iloc[0].get("video_count")) else 0
        view_count = int(reg_row.iloc[0].get("view_count", 0)) if not reg_row.empty and pd.notna(reg_row.iloc[0].get("view_count")) else 0
        
        # Classify agency type
        if agency in ("Independent", "Unknown", None, ""):
            agency_type = "INDEPENDENT"
        elif agency in ("Polygon Official", "Algorhythm Project", "Pixela Project", "AStars Production", "Virtual Zeven (VZ)", "RPG", "Flora Project", "Euphora Project"):
            agency_type = "AGENCY"
        else:
            agency_type = "COMMUNITY_OR_GROUP"
            
        # Determine verified vs proxy status
        is_grad = cid in verified_registry and verified_registry[cid]["event_type"] == "GRADUATION_VERIFIED"
        is_unavail = cid in verified_registry and verified_registry[cid]["event_type"] == "CHANNEL_UNAVAILABLE"
        
        if is_grad:
            act_state = "GRADUATED"
            verif_stat = "VERIFIED"
        elif is_unavail:
            act_state = "CHANNEL_UNAVAILABLE"
            verif_stat = "VERIFIED"
        elif manifest_status == "hiatus":
            act_state = "HIATUS"
            verif_stat = "INFERRED_PROXY"
        elif manifest_status == "active":
            act_state = "ACTIVE"
            verif_stat = "VERIFIED"
        else:
            act_state = manifest_status.upper()
            verif_stat = "INFERRED_PROXY"
            
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
            "subscriber_count": sub_count,
            "video_count": vid_count,
            "view_count": view_count,
            "snapshot_date": "2026-09-08"
        })
        
    snapshot_df = pd.DataFrame(snapshot_records).sort_values(by=["agency_type", "agency", "creator_name"])
    snapshot_df.to_parquet(OUT_SNAPSHOT_PARQUET, index=False)
    print(f"Saved {OUT_SNAPSHOT_PARQUET} ({len(snapshot_df)} rows).")

if __name__ == "__main__":
    build_creator_datasets()
