"""
Builds data/industry/discovery_universe.parquet & .csv

Quantifies the broader Thai VTuber universe beyond the frozen 193-channel research cohort:
- Identifies 1,370 total discoverable channels
- Separates frozen analytical cohort (193) from broader ecosystem (1,177)
- Preserves longitudinal comparability of the frozen cohort
- Provides evidence strength ratings and provenance sources
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BuildDiscoveryUniverse")

BASE_DIR = Path(".")
DATA_DIR = BASE_DIR / "data"
INDUSTRY_DIR = DATA_DIR / "industry"
INDUSTRY_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_PATH = DATA_DIR / "thai_vtuber_registry.json"
MANIFEST_PATH = DATA_DIR / "temporal" / "catalog" / "target_manifest.csv"


def build_discovery_universe():
    manifest = pd.read_csv(MANIFEST_PATH)
    frozen_ids = set(manifest["channel_id"])
    logger.info(f"Loaded {len(frozen_ids)} frozen target channels from manifest.")

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        reg_data = json.load(f)
    logger.info(f"Loaded {len(reg_data)} channels from Thai VTuber Registry.")

    universe_rows = []
    for r in reg_data:
        cid = r["channel_id"]
        name = r.get("name") or "Unknown"
        handle = r.get("handle") or ""
        agency = r.get("agency") or "Independent"
        source = r.get("reference_sources") or "Thai VTuber Ranking"
        checked = r.get("checked_date") or ""
        status = r.get("activity_status") or "unknown"
        is_frozen = cid in frozen_ids

        vt_st = r.get("vtuber_status", "UNKNOWN")
        try:
            thai_conf = float(r.get("thai_confidence", 0.5) or 0.5)
        except Exception:
            thai_conf = 0.5

        if vt_st == "CONFIRMED" and thai_conf >= 0.8:
            evidence_strength = "HIGH_CONFIDENCE"
        elif vt_st == "CONFIRMED" or thai_conf >= 0.5:
            evidence_strength = "MEDIUM_CONFIDENCE"
        else:
            evidence_strength = "LOW_CONFIDENCE"

        universe_rows.append({
            "channel_id": cid,
            "name": name,
            "handle": handle,
            "agency": agency,
            "discovery_source": source,
            "first_discovered_at": checked,
            "candidate_status": status,
            "already_in_frozen_cohort": is_frozen,
            "evidence_strength": evidence_strength
        })

    df = pd.DataFrame(universe_rows)

    out_parquet = INDUSTRY_DIR / "discovery_universe.parquet"
    out_csv = INDUSTRY_DIR / "discovery_universe.csv"
    df.to_parquet(out_parquet, index=False)
    df.to_csv(out_csv, index=False)

    logger.info(f"Saved {len(df)} channels to {out_parquet} and {out_csv}")
    logger.info(f"Frozen cohort members: {df['already_in_frozen_cohort'].sum()}")
    logger.info(f"External discoverable channels: {(~df['already_in_frozen_cohort']).sum()}")
    logger.info(f"Evidence strength breakdown: {df['evidence_strength'].value_counts().to_dict()}")


if __name__ == "__main__":
    build_discovery_universe()
