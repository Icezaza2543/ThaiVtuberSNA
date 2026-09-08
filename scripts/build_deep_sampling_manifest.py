"""
scripts/build_deep_sampling_manifest.py

Phase T6: Build Deepening Sampling Manifest & Initialize T6 Checkpoint
Queries the Phase T5 backfill checkpoint for videos marked COMPLETED and partial_capture = 1 (226 videos).
Generates deterministic manifests:
- data/temporal/deep_backfill/deep_sampling_manifest.parquet
- data/temporal/deep_backfill/deep_sampling_manifest.csv
Initializes dedicated SQLite checkpoint:
- data/temporal/deep_backfill/deep_backfill_checkpoint.sqlite3
"""
import sys
import sqlite3
import logging
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DATA_DIR
from collector.deep_comment_backfill import DeepCommentBackfiller, DEFAULT_DEEP_CHECKPOINT_DB

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BuildDeepSamplingManifest")

T5_CHECKPOINT_DB = DATA_DIR / "temporal" / "backfill" / "backfill_checkpoint.sqlite3"
DEEP_MANIFEST_DIR = DATA_DIR / "temporal" / "deep_backfill"
DEEP_MANIFEST_PARQUET = DEEP_MANIFEST_DIR / "deep_sampling_manifest.parquet"
DEEP_MANIFEST_CSV = DEEP_MANIFEST_DIR / "deep_sampling_manifest.csv"

DEEP_MANIFEST_SCHEMA = pa.schema([
    ("sample_id", pa.string()),
    ("channel_id", pa.string()),
    ("video_id", pa.string()),
    ("year", pa.int64()),
    ("video_published_at", pa.string()),
    ("time_bin", pa.string()),
    ("sampling_reason", pa.string()),
    ("t5_capture_count", pa.int64()),
    ("t5_output_file", pa.string()),
])


def build_deep_sampling_manifest() -> int:
    if not T5_CHECKPOINT_DB.exists():
        raise FileNotFoundError(f"T5 checkpoint not found at {T5_CHECKPOINT_DB}")

    DEEP_MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(T5_CHECKPOINT_DB)) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("""
            SELECT
                sample_id,
                channel_id,
                video_id,
                year,
                video_published_at,
                time_bin,
                sampling_reason,
                capture_count AS t5_capture_count,
                output_file AS t5_output_file
            FROM backfill_jobs
            WHERE status = 'COMPLETED' AND partial_capture = 1
            ORDER BY year ASC, channel_id ASC, video_id ASC
        """)
        rows = [dict(r) for r in cur.fetchall()]

    total_records = len(rows)
    logger.info(f"Retrieved {total_records} partial_capture videos from T5 checkpoint.")
    if total_records != 226:
        logger.warning(f"Expected exactly 226 partial_capture records, found {total_records}")

    # Build Parquet and CSV
    tbl = pa.Table.from_pylist(rows, schema=DEEP_MANIFEST_SCHEMA)
    pq.write_table(tbl, DEEP_MANIFEST_PARQUET, compression="snappy")
    logger.info(f"Wrote deep sampling manifest Parquet: {DEEP_MANIFEST_PARQUET}")

    df = pd.DataFrame(rows)
    df.to_csv(DEEP_MANIFEST_CSV, index=False, encoding="utf-8")
    logger.info(f"Wrote deep sampling manifest CSV: {DEEP_MANIFEST_CSV}")

    # Initialize T6 Checkpoint Database
    backfiller = DeepCommentBackfiller(db_path=DEFAULT_DEEP_CHECKPOINT_DB)
    with sqlite3.connect(str(DEFAULT_DEEP_CHECKPOINT_DB)) as con:
        cur = con.cursor()
        for r in rows:
            cur.execute("""
                INSERT INTO deep_backfill_jobs (
                    sample_id, channel_id, video_id, year, video_published_at,
                    time_bin, sampling_reason, status, attempts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', 0)
                ON CONFLICT(sample_id) DO NOTHING
            """, (
                r["sample_id"],
                r["channel_id"],
                r["video_id"],
                r["year"],
                r["video_published_at"],
                r["time_bin"],
                r["sampling_reason"]
            ))
        con.commit()

        cur.execute("SELECT status, COUNT(*) FROM deep_backfill_jobs GROUP BY status")
        counts = cur.fetchall()
        logger.info(f"T6 Checkpoint initialized: {counts}")

    return total_records


if __name__ == "__main__":
    build_deep_sampling_manifest()
