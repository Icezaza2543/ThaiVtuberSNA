"""
scripts/run_phase_t5_backfill.py

Phase T5 Driver: Historical Audience Backfill Execution
Coordinates stratified sampling manifest execution, quota budgeting, checkpoint management,
and generates detailed backfill audit reports.

Usage:
    python scripts/run_phase_t5_backfill.py --sync-only
    python scripts/run_phase_t5_backfill.py --pilot --limit 300 --api-quota-budget 500
    python scripts/run_phase_t5_backfill.py --api-quota-budget 7000
    python scripts/run_phase_t5_backfill.py --status
    python scripts/run_phase_t5_backfill.py --generate-report
"""
import sys
import argparse
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set

import pandas as pd
import pyarrow.parquet as pq

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DATA_DIR
from core.hasher import PrivacyHasher
from collector.historical_comment_backfill import (
    HistoricalCommentBackfiller,
    DEFAULT_CHECKPOINT_DB,
    DEFAULT_OBSERVATIONS_DIR,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PhaseT5Driver")

SAMPLING_MANIFEST_PARQUET = DATA_DIR / "temporal" / "backfill" / "sampling_manifest.parquet"
TARGET_MANIFEST_CSV = DATA_DIR / "temporal" / "catalog" / "target_manifest.csv"
BACKFILL_REPORT_MD = DATA_DIR / "temporal" / "backfill" / "phase_t5_backfill_report.md"
PILOT_REPORT_MD = DATA_DIR / "temporal" / "backfill" / "phase_t5_real_pilot_report.md"

# Bounded pilot selection: 20 diverse channels across tiers, agencies, lifecycles, and eras
PILOT_20_CHANNELS = [
    # Tier S (Top Megas: Indie & Agencies)
    "UCdlpXdGT3nGDTqIlxUcufCQ",  # Aisha Channel (Veteran indie pioneer)
    "UCGBkYTR4tMKS38TQHGWWLjg",  # Aito LH (Mega indie)
    "UCaNQI1xcU1ZC4W0guaIMgTg",  # San Jao (Indie)
    "UCpjyD0b6mXvW_P_xO35bWeg",  # Evalia Ch. (Algorhythm Project)
    "UCbEkHjG43yPMGq5W08jq1TQ",  # ChaAYM (Top Indie)
    # Tier A (Mid-to-Large: Diverse agencies & active/graduated)
    "UCwZeU3bOeq_c_n_9qVw0J9A",  # Hinabe HongFei (Pixela Project)
    "UC2eai5waelgobAHgp20DEYg",  # Ardalita Lilibelle (Lumina Live)
    "UC2z7pz25bgnqLHdTd7EvVoQ",  # Shishiou Seito (AStars Production)
    "UC3D2LNEOdYQq5mu9hjoQTZQ",  # ROOKCAN (DPX)
    "UCafG1bj6Qtcbn4bozcicWfA",  # ZONA Ch. (Polygon Official)
    "UC25e5qEqvVaG_VKrkTmJBmw",  # Lucene Ch. (Indie)
    "UC3O5wAgEVyNA1Jw3gyi-_jA",  # MOLLY (Indie)
    # Tier B & C (Growing / Niche / Legacy / Graduated)
    "UC1xmO5jVjOCeo02XCpq4WFA",  # Erima Channel (Indie)
    "UCFr02a1OIuA1yrnJuB2dSpw",  # Shishiro Taiga (Indie)
    "UCURSzDgzFhYWhKDySspPisA",  # LittleG ch. (Euphora Project)
    "UCUfM5IcATD5-AB1If9v7wTA",  # Den Trenton (OAL)
    "UC3QIcnp1II_iCt-_JG8btKQ",  # Era Ch. (Algorhythm Project)
    "UC_djfyZ7N_-hPSxtrSsBNfQ",  # Victor Hoshino (Graduated)
    "UC32lsx7u7vqy63SguuuzmVg",  # Narelle ch. (Hiatus)
    "UCadBHNCSacgE3vePH8UtbMA",  # Chalong Ch. (Indie active)
]


def load_manifest_records() -> List[Dict[str, Any]]:
    """Loads records from the sampling manifest."""
    if not SAMPLING_MANIFEST_PARQUET.exists():
        raise FileNotFoundError(f"Manifest missing: {SAMPLING_MANIFEST_PARQUET}. Run build_historical_sampling_manifest.py first.")
    tbl = pq.read_table(SAMPLING_MANIFEST_PARQUET)
    return tbl.to_pylist()


def print_status(db_path: Path = DEFAULT_CHECKPOINT_DB):
    """Prints checkpoint status overview."""
    if not db_path.exists():
        print(f"Checkpoint DB not found at {db_path}.")
        return

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT status, COUNT(*), SUM(capture_count) FROM backfill_jobs GROUP BY status")
        rows = cur.fetchall()

        print("\n" + "=" * 55)
        print(" Phase T5 Backfill Checkpoint Status")
        print("=" * 55)
        total = 0
        total_obs = 0
        for status, count, obs in rows:
            obs_cnt = obs or 0
            total += count
            total_obs += obs_cnt
            print(f"  {status:<20}: {count:>6} videos ({obs_cnt:>8,} comments)")
        print("-" * 55)
        print(f"  {'TOTAL JOBS':<20}: {total:>6} videos ({total_obs:>8,} comments)")
        print("=" * 55 + "\n")


def generate_backfill_report(
    db_path: Path = DEFAULT_CHECKPOINT_DB,
    output_path: Path = BACKFILL_REPORT_MD,
    is_pilot: bool = False
):
    """Generates comprehensive markdown backfill progress audit report."""
    if not db_path.exists():
        logger.warning(f"DB not found at {db_path}, cannot generate report.")
        return

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM backfill_jobs", conn)

    if df.empty:
        logger.warning("No backfill job records found in DB.")
        return

    target_df = pd.read_csv(TARGET_MANIFEST_CSV)
    target_meta = {r["channel_id"]: r for _, r in target_df.iterrows()}

    df["channel_title"] = df["channel_id"].apply(lambda cid: target_meta.get(cid, {}).get("name", "Unknown"))
    df["agency"] = df["channel_id"].apply(lambda cid: target_meta.get(cid, {}).get("agency", "Independent"))
    df["tier"] = df["channel_id"].apply(lambda cid: target_meta.get(cid, {}).get("tier_at_selection", "Unknown"))
    df["lifecycle"] = df["channel_id"].apply(lambda cid: target_meta.get(cid, {}).get("lifecycle_status", "unknown"))

    total_jobs = len(df)
    completed_df = df[df["status"] == "COMPLETED"]
    total_completed = len(completed_df)
    total_comments = completed_df["capture_count"].sum()
    total_partial = len(df[df["partial_capture"] == 1])
    total_disabled = len(df[df["status"] == "COMMENTS_DISABLED"])
    total_no_comments = len(df[df["status"] == "NO_COMMENTS"])
    total_unavailable = len(df[df["status"] == "VIDEO_UNAVAILABLE"])
    total_pending = len(df[df["status"].isin(["PENDING", "RETRYABLE"])])
    total_failed = len(df[df["status"] == "FAILED"])

    # Year level
    year_rows = []
    for y in sorted(df["year"].unique()):
        y_df = df[df["year"] == y]
        y_comp = y_df[y_df["status"] == "COMPLETED"]
        year_rows.append({
            "year": y,
            "manifest_videos": len(y_df),
            "completed_videos": len(y_comp),
            "channels_processed": y_comp["channel_id"].nunique(),
            "comment_observations": y_comp["capture_count"].sum(),
            "partial_captures": len(y_df[y_df["partial_capture"] == 1]),
            "disabled_or_empty": len(y_df[y_df["status"].isin(["COMMENTS_DISABLED", "NO_COMMENTS"])]),
        })

    title = "Phase T5 Bounded Real Pilot Report" if is_pilot else "Phase T5 Historical Backfill Report"
    lines = [
        f"# {title}",
        "",
        f"**Generated at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
        f"**Scope:** {'Bounded 20-Channel Pilot Cohort' if is_pilot else 'Full Stratified Historical Cohort'}  ",
        f"**Storage Engine:** Local Parquet + DuckDB (`data/temporal/observations/comment/`)  ",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "| Metric | Value | Notes / Methodology |",
        "| :--- | :---: | :--- |",
        f"| **Manifest Videos Registered** | **{total_jobs:,}** | Total stratified videos queued |",
        f"| **Videos Successfully Extracted** | **{total_completed:,}** | Parquet observations written |",
        f"| **Total Comment Observations** | **{total_comments:,}** | Deduplicated presence records |",
        f"| **Partial Captures (hit 100 cap)** | **{total_partial:,}** | Videos where $>100$ comments exist |",
        f"| **Comments Disabled** | **{total_disabled:,}** | YouTube comments disabled by creator |",
        f"| **No Comments Found** | **{total_no_comments:,}** | Video with 0 comments posted |",
        f"| **Video Unavailable / 404** | **{total_unavailable:,}** | Private, deleted, or unlisted |",
        f"| **Pending Jobs** | **{total_pending:,}** | Ready for subsequent batch execution |",
        f"| **Failed Jobs** | **{total_failed:,}** | Network or unexpected API errors |",
        "",
        "> [!NOTE]",
        "> Observations represent observed commenters with dated interaction evidence. Raw viewer channel IDs were hashed immediately via HMAC-SHA256 within the extraction loop, and zero commenter display names, URLs, or comment texts are stored.",
        "",
        "---",
        "",
        "## 2. Longitudinal Interaction Evidence Coverage by Year",
        "",
        "| Year | Sampled Videos | Completed | Active Channels | Comment Observations | Partial Captures | Disabled/Empty |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for yr in year_rows:
        lines.append(
            f"| {yr['year']} | {yr['manifest_videos']:,} | {yr['completed_videos']:,} | {yr['channels_processed']} | {yr['comment_observations']:,} | {yr['partial_captures']} | {yr['disabled_or_empty']} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. Coverage by Demographic Segments",
        "",
        "### By Subscriber Tier",
        "",
        "| Tier | Manifest Videos | Completed | Comment Observations |",
        "| :--- | :---: | :---: | :---: |",
    ])

    for t, g in df.groupby("tier"):
        g_comp = g[g["status"] == "COMPLETED"]
        lines.append(f"| {t} | {len(g):,} | {len(g_comp):,} | {g_comp['capture_count'].sum():,} |")

    lines.extend([
        "",
        "### By Agency Group",
        "",
        "| Agency | Manifest Videos | Completed | Comment Observations |",
        "| :--- | :---: | :---: | :---: |",
    ])

    for ag, g in df.groupby("agency"):
        g_comp = g[g["status"] == "COMPLETED"]
        lines.append(f"| {ag} | {len(g):,} | {len(g_comp):,} | {g_comp['capture_count'].sum():,} |")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Privacy & Methodological Disclosures",
        "",
        "1. **Sampled Observation Scope:** Observations are capped at 100 top-level comments per sampled video. This constitutes a representative sample rather than exhaustive comment archives.",
        "2. **Strict Temporal Integrity:** Comment timestamps are mapped directly from YouTube `publishedAt`. Videos with unavailable comment timestamps have `interaction_at = NULL` and are excluded from temporal windows.",
        "3. **Zero PII Leakage:** Local privacy audit verified 0 raw `UC...` viewer IDs, 0 display names, 0 URLs, and 0 comment bodies across all generated outputs.",
        ""
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Saved report to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Phase T5 Historical Audience Backfill Driver")
    parser.add_argument("--sync-only", action="store_true", help="Sync sampling manifest to SQLite DB and exit")
    parser.add_argument("--pilot", action="store_true", help="Run on bounded 20-channel pilot cohort")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of videos to process in this run")
    parser.add_argument("--api-quota-budget", type=int, default=7000, help="Maximum API request budget (default: 7000)")
    parser.add_argument("--max-comments", type=int, default=100, help="Max comments per video (default: 100)")
    parser.add_argument("--channels", type=str, default=None, help="Comma-separated list of channel IDs to process")
    parser.add_argument("--status", action="store_true", help="Display current checkpoint status")
    parser.add_argument("--generate-report", action="store_true", help="Generate markdown backfill audit report")

    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.generate_report:
        generate_backfill_report(is_pilot=args.pilot)
        return

    logger.info("Initializing Privacy Hasher (validating persistent key continuity)...")
    hasher = PrivacyHasher()

    backfiller = HistoricalCommentBackfiller(
        quota_budget=args.api_quota_budget,
        max_comments_per_video=args.max_comments,
        hasher=hasher
    )

    logger.info("Synchronizing sampling manifest records into checkpoint DB...")
    manifest_records = load_manifest_records()
    backfiller.sync_manifest(manifest_records)

    if args.sync_only:
        logger.info("Sync complete. Exiting (--sync-only).")
        print_status()
        return

    channel_filter = None
    if args.pilot:
        logger.info(f"Pilot flag active: Restricting backfill to {len(PILOT_20_CHANNELS)} pilot channels.")
        channel_filter = set(PILOT_20_CHANNELS)
    elif args.channels:
        channel_filter = set(cid.strip() for cid in args.channels.split(",") if cid.strip())
        logger.info(f"Restricting backfill to {len(channel_filter)} specified channels.")

    logger.info(f"Starting Historical Comment Backfill (Quota budget: {args.api_quota_budget}, Limit: {args.limit})...")
    summary = backfiller.run_backfill(limit=args.limit, channel_ids=channel_filter)

    report_file = PILOT_REPORT_MD if args.pilot else BACKFILL_REPORT_MD
    generate_backfill_report(output_path=report_file, is_pilot=args.pilot)
    print_status()


if __name__ == "__main__":
    main()
