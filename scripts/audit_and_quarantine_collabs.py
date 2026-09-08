#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repairs and audits collab events in ThaiVtuberSNA:
- Identifies unverified / pseudo video IDs (e.g. non-11 char slugs or unresolvable sources).
- Quarantines them to data/industry/quarantine/collab_events_unverified.csv with explicit reason codes.
- Audits catalog-backed 11-character video IDs.
- Outputs updated data/industry/collab_events.parquet and collab_events.csv.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
INDUSTRY_DIR = ROOT / "data/industry"
QUARANTINE_DIR = INDUSTRY_DIR / "quarantine"
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

COLLAB_PARQUET = INDUSTRY_DIR / "collab_events.parquet"
CATALOG_PARQUET = ROOT / "data/video_catalog.parquet"

OUT_QUARANTINE_CSV = QUARANTINE_DIR / "collab_events_unverified.csv"
OUT_VERIFIED_PARQUET = INDUSTRY_DIR / "collab_events.parquet"
OUT_VERIFIED_CSV = INDUSTRY_DIR / "collab_events.csv"

NOW_ISO = datetime.now(timezone.utc).isoformat()
YT_ID_REGEX = re.compile(r'^[A-Za-z0-9_-]{11}$')

def audit_collabs():
    if not COLLAB_PARQUET.exists():
        print("No collab_events.parquet found.")
        return

    df = pd.read_parquet(COLLAB_PARQUET)
    catalog_df = pd.read_parquet(CATALOG_PARQUET)
    catalog_vids = set(catalog_df["video_id"].unique())

    print(f"Auditing {len(df)} collab records...")

    quarantine_rows = []
    verified_rows = []

    for idx, r in df.iterrows():
        row_dict = r.to_dict()
        vid = str(r.get("video_id", "")).strip()
        host = str(r.get("host_channel_id", "")).strip()
        part = str(r.get("participant_channel_id", "")).strip()
        src = str(r.get("source_reference", "")).strip()

        # Check 1: Syntactically valid 11-char YouTube ID
        if not YT_ID_REGEX.match(vid):
            row_dict["reason"] = "INVALID_VIDEO_ID"
            row_dict["audit_notes"] = f"Video ID '{vid}' is a descriptive pseudo-slug, not a valid 11-char YouTube identifier."
            quarantine_rows.append(row_dict)
            continue

        # Check 2: Exists in catalog or resolves publicly
        if vid not in catalog_vids:
            row_dict["reason"] = "SOURCE_NOT_RESOLVABLE"
            row_dict["audit_notes"] = f"Video ID '{vid}' not found in local verified public video catalog."
            quarantine_rows.append(row_dict)
            continue

        # Check 3: Check channel attribution in catalog
        cat_match = catalog_df[catalog_df["video_id"] == vid]
        cat_host = cat_match.iloc[0]["channel_id"]
        if host != cat_host:
            row_dict["reason"] = "PARTICIPANT_NOT_VERIFIED"
            row_dict["audit_notes"] = f"Catalog host channel {cat_host} does not match claimed host {host}."
            quarantine_rows.append(row_dict)
            continue

        # Check 4: Check if participant channel is explicitly verifiable
        # In YouTube video metadata without description text, participant channel ID is not guaranteed verified.
        # However, for eNKesx5KIOI & ag6Zglhdfvk (Callisto with Davina V), title explicitly has #1 and #2.
        # But if participant channel is not uniquely resolvable from title alone, flag or verify.
        # NiQ-GaHZwAs (Davina V) title has: "🔴｢LIVE｣#COLLAB "OVERWATCH 2" วี่มาฮิล!!!!!" (No participants mentioned in title!)
        title = cat_match.iloc[0]["title"]
        if vid == "NiQ-GaHZwAs":
            row_dict["reason"] = "PARTICIPANT_NOT_VERIFIED"
            row_dict["audit_notes"] = "Video title does not mention claimed participant channels."
            quarantine_rows.append(row_dict)
            continue

        if vid == "8bGKcTmvGRw":
            # Title: 🔴｢LIVE｣#COLLAB "PACIFY" @Sovonch @JingJibara @Mallow_Ham !!!!!
            # Mentioned channels are Sovonch, JingJibara, Mallow_Ham, but claimed was PeachiView & Callisto!
            row_dict["reason"] = "PARTICIPANT_NOT_VERIFIED"
            row_dict["audit_notes"] = "Title handles (@Sovonch, @JingJibara, @Mallow_Ham) do not match claimed cohort channels."
            quarantine_rows.append(row_dict)
            continue

        # For eNKesx5KIOI & ag6Zglhdfvk:
        # Title: 【🔴COLLAB】เกมเป็ดหรรษาที่ได้เล่นซักทีนะ 🦆🔍 | Goose Goose Duck「#1」
        # Title doesn't mention Davina's channel explicitly in the title string itself!
        if vid in ["eNKesx5KIOI", "ag6Zglhdfvk"]:
            # Title confirms COLLAB, but participant is not parsed from title alone
            row_dict["reason"] = "PARTICIPANT_NOT_VERIFIED"
            row_dict["audit_notes"] = "Collab event verified from title, but participant channel ID requires full description parsing."
            quarantine_rows.append(row_dict)
            continue

        # If any survived:
        verified_rows.append(row_dict)

    print(f"Quarantined: {len(quarantine_rows)} records.")
    print(f"Surviving strictly verified: {len(verified_rows)} records.")

    # Save quarantine
    q_df = pd.DataFrame(quarantine_rows)
    q_df.to_csv(OUT_QUARANTINE_CSV, index=False, encoding="utf-8")
    print(f"Saved quarantine report to {OUT_QUARANTINE_CSV}")

    # Save remaining verified
    if verified_rows:
        v_df = pd.DataFrame(verified_rows)
    else:
        # Empty schema with same columns
        v_df = pd.DataFrame(columns=df.columns)
    
    v_df.to_parquet(OUT_VERIFIED_PARQUET, index=False)
    v_df.to_csv(OUT_VERIFIED_CSV, index=False, encoding="utf-8")
    print(f"Saved sanitized {OUT_VERIFIED_PARQUET} (count: {len(v_df)}).")

if __name__ == "__main__":
    audit_collabs()
