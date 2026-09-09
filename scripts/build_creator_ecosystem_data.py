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

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))
from analytics.creator_snapshot import build_snapshot_frame

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
    
    # Load canonical lifecycle evidence
    canonical_cov_df = pd.read_parquet(CANONICAL_COVERAGE_PARQUET)
    canonical_events_df = pd.read_parquet(CANONICAL_EVENTS_PARQUET)
    
    snapshot_df = build_snapshot_frame(targets_df, coverage_df, registry_data, canonical_cov_df, canonical_events_df)
    snapshot_df.to_parquet(OUT_SNAPSHOT_PARQUET, index=False)
    print(f"Saved {OUT_SNAPSHOT_PARQUET} ({len(snapshot_df)} rows) derived from canonical lifecycle evidence.")
    return snapshot_df


def build_creator_datasets():
    """Deprecated alias: delegates to build_creator_public_snapshot."""
    return build_creator_public_snapshot()


if __name__ == "__main__":
    build_creator_public_snapshot()
