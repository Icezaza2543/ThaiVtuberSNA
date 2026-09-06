"""
Thai VTuber Audience Network (SNA)
Re-classify Thai VTuber Agencies from Channel Names and Descriptions

Scans all channels in thai_vtuber_registry.csv to detect authentic Thai agency affiliations
that were previously defaulted to 'Independent' due to strict initial heuristics.
"""
import csv
import json
import logging
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ReclassifyAgencies")

AGENCY_PATTERNS: List[Tuple[str, str]] = [
    # Major agencies
    (r'(?i)\b(algorhythm(?:\s*project)?|arp)\b', 'Algorhythm Project'),
    (r'(?i)\bpolygon(?:\s*(?:official|project))?\b', 'Polygon Official'),
    (r'(?i)\bpixela(?:\s*(?:project|isekai|retro))?\b', 'Pixela Project'),
    (r'(?i)\blumina(?:\s*live)?\b', 'Lumina Live'),
    (r'(?i)\beuphora(?:\s*project)?\b', 'Euphora Project'),
    (r'(?i)\bastars(?:\s*(?:production|chrono\s*prince|amakara))?\b', 'AStars Production'),
    (r'(?i)(?:⌜\s*vz\s*⌟|\bvirtual\s*zeven\b)', 'Virtual Zeven (VZ)'),
    (r'(?i)(?:flora\s*(?:vtuber\s*)?project|\bflora\s*project\b)', 'Flora Project'),
    (r'(?i)\bgenesis(?:\s*(?:vt|project))?\b', 'Genesis Project'),
    (r'(?i)(?:\|\s*oal\b|\[oal\])', 'OAL'),
    (r'(?i)(?:\|\s*v\.w\.y\b|\[vwy\]|\|\s*vwy\b)', 'V.W.Y'),
    (r'(?i)(?:《\s*atx\s*》|\[atx\])', 'ATX'),
    (r'(?i)(?:〖\s*dpx\s*〗|『\s*dpx\s*』|【\s*dpx\s*】|\[dpx\])', 'DPX'),
    (r'(?i)(?:《\s*exia\s*》|\[exia\])', 'EXia'),
    (r'(?i)(?:「\s*alf\s*」|\[alf\])', 'ALF'),
    (r'(?i)(?:\[autumnia\]|〖\s*autumnia\s*〗|\bautumnia\b)', 'Autumnia'),
    (r'(?i)(?:『\s*paralist\s*』|「\s*paralist\s*」|\bparalist\b)', 'Paralist'),
    (r'(?i)(?:【\s*hz\s*】|\[hz\])', 'HZ'),
    (r'(?i)(?:\|\s*rpg\b|\[rpg\])', 'RPG'),
    (r'(?i)(?:\[pandora\]|\bpandora\b)', 'Pandora'),
    (r'(?i)(?:【\s*ti19t\s*】|\[ti19t\])', 'Ti19t'),
    (r'(?i)\bvtopia\b', 'Vtopia'),
    (r'(?i)\bwactor\b', 'WACTOR'),
    (r'(?i)(?:_eylz\b|\beylz\b)', 'EYLZ'),
    (r'(?i)loveland\s*project', 'Loveland Project'),
    (r'(?i)\[stp\]', 'STP'),
    (r'(?i)\bmyriad\s*colors\b', 'Myriad Colors'),
    (r'(?i)\bvirtual\s*union\b', 'Virtual Union'),
    (r'(?i)\bhorganice\b', 'Horganice'),
    (r'(?i)\ba-live\b', 'A-Live'),
    (r'(?i)\bmori\s*project\b', 'Mori Project'),
]


def run_reclassification():
    reg_csv = DATA_DIR / "thai_vtuber_registry.csv"
    if not reg_csv.exists():
        logger.error("Registry CSV not found!")
        return

    with open(reg_csv, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    reclassified_count = 0
    agency_counts_before = {}
    agency_counts_after = {}

    for row in reader:
        old_ag = row.get("agency", "Independent")
        agency_counts_before[old_ag] = agency_counts_before.get(old_ag, 0) + 1
        name = row.get("name", "")

        # Also normalize existing VZ to Virtual Zeven (VZ)
        if old_ag == "VZ":
            row["agency"] = "Virtual Zeven (VZ)"
            reclassified_count += 1
            continue

        if old_ag == "Independent":
            for pat, new_ag in AGENCY_PATTERNS:
                if re.search(pat, name):
                    row["agency"] = new_ag
                    reclassified_count += 1
                    logger.info(f"Reclassified: {row['channel_id']} | '{name}' -> {new_ag}")
                    break

        new_ag = row["agency"]
        agency_counts_after[new_ag] = agency_counts_after.get(new_ag, 0) + 1

    logger.info(f"Total reclassified channels: {reclassified_count}")

    # Write updated CSV
    fieldnames = list(reader[0].keys())
    with open(reg_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reader)

    # Write updated JSON
    reg_json = DATA_DIR / "thai_vtuber_registry.json"
    with open(reg_json, "w", encoding="utf-8") as f:
        json.dump(reader, f, indent=2, ensure_ascii=False)

    # Sync to registry_vtubers.csv
    compat_csv = DATA_DIR / "registry_vtubers.csv"
    if compat_csv.exists():
        with open(compat_csv, "r", encoding="utf-8") as f:
            compat_rows = list(csv.DictReader(f))
        
        agency_map = {r["channel_id"]: r["agency"] for r in reader}
        for c_row in compat_rows:
            cid = c_row["channel_id"]
            if cid in agency_map:
                c_row["agency"] = agency_map[cid]

        with open(compat_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(compat_rows[0].keys()))
            writer.writeheader()
            writer.writerows(compat_rows)

    logger.info("Successfully updated registry files and control plane!")
    print("\n=== Top 15 Agency Distribution After Reclassification ===")
    for ag, cnt in sorted(agency_counts_after.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {ag:25s}: {cnt:4d} channels")


if __name__ == "__main__":
    run_reclassification()
