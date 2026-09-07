"""
Creates and Freezes the Target Manifest for Phase T1 Historical Catalog
Cohort includes Tier S, Tier A, top Tier B, and Graduated VTubers (193 channels).
Outputs immutable manifest to data/temporal/catalog/target_manifest.csv.
"""
import sys
import csv
import logging
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CreateTargetManifest")

OUTPUT_DIR = DATA_DIR / "temporal" / "catalog"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = OUTPUT_DIR / "target_manifest.csv"

def get_tier(subscriber_count: int) -> str:
    if subscriber_count >= 100000: return "S"
    if subscriber_count >= 50000: return "A"
    if subscriber_count >= 10000: return "B"
    if subscriber_count >= 1000: return "C"
    return "D"

def main():
    logger.info("Building frozen target manifest for Phase T1 Historical Catalog...")
    registry_file = DATA_DIR / "thai_vtuber_registry.csv"
    if not registry_file.exists():
        logger.error(f"Registry not found: {registry_file}")
        sys.exit(1)

    with open(registry_file, "r", encoding="utf-8") as f:
        vtubers = list(csv.DictReader(f))

    selected_rows = []
    now_str = datetime.now(timezone.utc).isoformat()

    for v in vtubers:
        cid = v["channel_id"].strip()
        name = v.get("name", "").strip()
        subs_raw = v.get("subscriber_count", "0")
        try:
            subs = int(float(subs_raw or 0))
        except Exception:
            subs = 0

        tier = get_tier(subs)
        lifecycle = v.get("activity_status", "active").strip()
        agency = v.get("agency", "Independent").strip()
        
        is_grad = (
            lifecycle == "graduated" or 
            "graduat" in name.lower() or 
            "graduat" in v.get("evidence_notes", "").lower()
        )

        reason = None
        if subs >= 100000:
            reason = "Tier S (>=100k subscribers)"
        elif subs >= 50000:
            reason = "Tier A (>=50k subscribers)"
        elif is_grad:
            reason = "Graduated VTuber (Lifecycle & Migration Tracking)"
        elif subs >= 30000:
            reason = "Tier B High-Sub (>=30k subscribers)"
        elif agency in ("Algorhythm Project", "Pixela Project", "Virtual Zeven (VZ)", "Lumina Live") and subs >= 25000:
            reason = f"Core Agency ({agency}) >=25k"

        if reason:
            selected_rows.append({
                "channel_id": cid,
                "name": name,
                "tier_at_selection": tier,
                "subscriber_count_at_selection": subs,
                "lifecycle_status": "graduated" if is_grad else lifecycle,
                "agency": agency,
                "selection_reason": reason,
                "selected_at": now_str
            })

    # Sort deterministically by subscribers descending
    selected_rows.sort(key=lambda r: r["subscriber_count_at_selection"], reverse=True)

    fieldnames = [
        "channel_id",
        "name",
        "tier_at_selection",
        "subscriber_count_at_selection",
        "lifecycle_status",
        "agency",
        "selection_reason",
        "selected_at"
    ]

    with open(MANIFEST_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected_rows)

    logger.info(f"Target manifest created with {len(selected_rows)} channels: {MANIFEST_PATH}")
    for tier_code in ["S", "A", "B", "C", "D"]:
        count = sum(1 for r in selected_rows if r["tier_at_selection"] == tier_code)
        if count > 0:
            logger.info(f"  - Tier {tier_code}: {count} channels")
    grad_count = sum(1 for r in selected_rows if r["lifecycle_status"] == "graduated")
    logger.info(f"  - Graduated VTubers: {grad_count} channels")

if __name__ == "__main__":
    main()
