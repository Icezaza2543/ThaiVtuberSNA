"""
Run Phase T1: Historical Video Catalog Collection (2020 ➔ Present)
Processes all 193 channels in target_manifest.csv.
Applies:
- max 1,000 videos / channel
- 2020-01-01T00:00:00Z cutoff date
- playlistItems.list with part=snippet,contentDetails (1 unit per request)
- Atomic page-level checkpointing
- Auto-generates final audit report upon completion.
"""
import sys
import csv
import time
import logging
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DATA_DIR
from collector.historical_catalog_builder import HistoricalCatalogBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RunPhaseT1Catalog")

CATALOG_DIR = DATA_DIR / "temporal" / "catalog"
MANIFEST_PATH = CATALOG_DIR / "target_manifest.csv"

def main():
    logger.info("==========================================================")
    logger.info(" PHASE T1: Historical Video Catalog Collection (2020-2026)")
    logger.info("==========================================================")

    if not MANIFEST_PATH.exists():
        logger.error(f"Target manifest not found: {MANIFEST_PATH}. Run create_target_manifest.py first.")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8-sig") as f:
        target_channels = list(csv.DictReader(f))

    logger.info(f"Loaded {len(target_channels)} target channels from manifest.")
    builder = HistoricalCatalogBuilder(output_dir=CATALOG_DIR, max_videos_per_channel=1000)

    total_channels = len(target_channels)
    total_videos_cataloged = 0
    total_api_calls = 0
    start_time = time.time()

    for idx, ch in enumerate(target_channels, start=1):
        cid = ch["channel_id"]
        cname = ch.get("name", cid)
        tier = ch.get("tier_at_selection", "?")
        reason = ch.get("selection_reason", "")

        logger.info(f"[{idx}/{total_channels}] Channel: {cname} ({cid}) [Tier {tier}]...")
        try:
            res = builder.crawl_channel(cid, target_reason=reason)
            total_videos_cataloged += res.get("videos_collected", 0)
            total_api_calls += res.get("api_calls", 0)
        except Exception as e:
            logger.error(f"Unhandled error crawling channel {cid}: {e}", exc_info=True)

        if idx % 10 == 0 or idx == total_channels:
            elapsed = time.time() - start_time
            rate = idx / max(1, elapsed)
            logger.info(
                f" -> Progress: {idx}/{total_channels} channels completed ({idx*100//total_channels}%) | "
                f"Total API Calls: {total_api_calls} (Quota: {total_api_calls} units) | "
                f"Elapsed: {elapsed:.1f}s ({rate:.2f} ch/s)"
            )

    logger.info("==========================================================")
    logger.info(" Phase T1 Crawl Complete! Generating Audit Report...      ")
    logger.info("==========================================================")

    from scripts.generate_catalog_audit_report import main as generate_report
    generate_report()

if __name__ == "__main__":
    main()
