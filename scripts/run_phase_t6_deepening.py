"""
scripts/run_phase_t6_deepening.py

Phase T6 Orchestrator:
- Checks status of deep backfill checkpoint
- Runs pilot (~20 partial videos across years/agencies)
- Runs bounded batches with strict API quota budgets
- Generates markdown progress and completion reports
"""
import sys
import argparse
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DATA_DIR
from collector.deep_comment_backfill import (
    DeepCommentBackfiller,
    DEFAULT_DEEP_CHECKPOINT_DB,
    DEFAULT_DEEP_OBSERVATIONS_DIR,
    BudgetExhaustedException
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PhaseT6Orchestrator")

REPORT_PATH = DATA_DIR / "temporal" / "deep_backfill" / "phase_t6_deepening_report.md"


def get_checkpoint_status(db_path: Path = DEFAULT_DEEP_CHECKPOINT_DB) -> Dict[str, Any]:
    """Retrieves authoritative counts and summary stats from T6 SQLite checkpoint."""
    if not db_path.exists():
        return {"error": "Checkpoint database does not exist"}

    with sqlite3.connect(str(db_path)) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        status_rows = cur.execute("""
            SELECT status, COUNT(*) as cnt
            FROM deep_backfill_jobs
            GROUP BY status
        """).fetchall()
        status_counts = {r["status"]: r["cnt"] for r in status_rows}

        year_rows = cur.execute("""
            SELECT
                year,
                COUNT(*) as manifest_total,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'NO_COMMENTS' THEN 1 ELSE 0 END) as no_comments,
                SUM(CASE WHEN status = 'COMMENTS_DISABLED' THEN 1 ELSE 0 END) as disabled,
                SUM(CASE WHEN status = 'VIDEO_UNAVAILABLE' THEN 1 ELSE 0 END) as unavail,
                SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status IN ('PENDING', 'RETRYABLE', 'RUNNING') THEN 1 ELSE 0 END) as pending
            FROM deep_backfill_jobs
            GROUP BY year
            ORDER BY year
        """).fetchall()
        by_year = [dict(r) for r in year_rows]

        totals = cur.execute("""
            SELECT
                COUNT(*) as total_jobs,
                SUM(pages_fetched) as total_pages,
                SUM(total_items_fetched) as total_comments,
                SUM(capture_count) as total_unique_viewers
            FROM deep_backfill_jobs
        """).fetchone()

    total_jobs = totals["total_jobs"] or 0
    terminal_jobs = (
        status_counts.get("COMPLETED", 0) +
        status_counts.get("NO_COMMENTS", 0) +
        status_counts.get("COMMENTS_DISABLED", 0) +
        status_counts.get("VIDEO_UNAVAILABLE", 0) +
        status_counts.get("FAILED", 0)
    )
    pending_jobs = (
        status_counts.get("PENDING", 0) +
        status_counts.get("RETRYABLE", 0) +
        status_counts.get("RUNNING", 0)
    )

    return {
        "total_jobs": total_jobs,
        "terminal_jobs": terminal_jobs,
        "pending_jobs": pending_jobs,
        "completion_ratio": round(terminal_jobs / total_jobs, 4) if total_jobs else 0.0,
        "status_counts": status_counts,
        "total_pages": totals["total_pages"] or 0,
        "total_comments": totals["total_comments"] or 0,
        "total_unique_viewers": totals["total_unique_viewers"] or 0,
        "by_year": by_year
    }


def print_status(db_path: Path = DEFAULT_DEEP_CHECKPOINT_DB) -> None:
    st = get_checkpoint_status(db_path)
    print("\n============================================================")
    print("PHASE T6 DEEPENING CHECKPOINT STATUS")
    print("============================================================")
    print(f"Total Targets:     {st['total_jobs']}")
    print(f"Terminal Jobs:     {st['terminal_jobs']} ({st['completion_ratio']*100:.1f}%)")
    print(f"Pending Jobs:      {st['pending_jobs']}")
    print(f"Total Pages:       {st['total_pages']:,}")
    print(f"Total Comments:    {st['total_comments']:,}")
    print(f"Total Viewers:     {st['total_unique_viewers']:,}")
    print("------------------------------------------------------------")
    print("Status Breakdown:")
    for status, count in sorted(st["status_counts"].items()):
        print(f"  {status:<20}: {count}")
    print("------------------------------------------------------------")
    print("Per-Year Breakdown:")
    for y in st["by_year"]:
        print(f"  {y['year']}: Total={y['manifest_total']}, Completed={y['completed']}, Pending={y['pending']}")
    print("============================================================\n")


def generate_report(output_path: Path = REPORT_PATH, db_path: Path = DEFAULT_DEEP_CHECKPOINT_DB) -> None:
    st = get_checkpoint_status(db_path)
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    stage = (
        "deep_historical_backfill_complete"
        if st["pending_jobs"] == 0 and st["total_jobs"] > 0
        else "deep_historical_backfill_partial"
    )

    lines = [
        "# Phase T6 Deep Comment History & Bias Correction Report",
        "",
        f"- **Generated at:** {now_utc}",
        f"- **Dataset Stage:** `{stage}`",
        f"- **Deepening Target Cohort:** 226 Partial-Capture Historical Videos",
        f"- **Terminal Jobs:** {st['terminal_jobs']} / {st['total_jobs']} ({st['completion_ratio']*100:.1f}%)",
        f"- **Pending Jobs:** {st['pending_jobs']}",
        f"- **Total Pages Fetched:** {st['total_pages']:,}",
        f"- **Total Raw Comments Captured:** {st['total_comments']:,}",
        f"- **Total Unique Viewer-Video Observations:** {st['total_unique_viewers']:,}",
        "",
        "---",
        "",
        "## 1. Execution Status Breakdown",
        "",
        "| Terminal State | Job Count | % of Deep Targets | Definition |",
        "| :--- | :---: | :---: | :--- |",
        f"| **COMPLETED (Full Pagination)** | **{st['status_counts'].get('COMPLETED', 0):,}** | {round(st['status_counts'].get('COMPLETED', 0)/st['total_jobs']*100, 1) if st['total_jobs'] else 0}% | Complete pagination reached via nextPageToken |",
        f"| **NO_COMMENTS** | **{st['status_counts'].get('NO_COMMENTS', 0):,}** | {round(st['status_counts'].get('NO_COMMENTS', 0)/st['total_jobs']*100, 1) if st['total_jobs'] else 0}% | Verified zero comments |",
        f"| **COMMENTS_DISABLED** | **{st['status_counts'].get('COMMENTS_DISABLED', 0):,}** | {round(st['status_counts'].get('COMMENTS_DISABLED', 0)/st['total_jobs']*100, 1) if st['total_jobs'] else 0}% | Comments disabled by publisher |",
        f"| **VIDEO_UNAVAILABLE** | **{st['status_counts'].get('VIDEO_UNAVAILABLE', 0):,}** | {round(st['status_counts'].get('VIDEO_UNAVAILABLE', 0)/st['total_jobs']*100, 1) if st['total_jobs'] else 0}% | Video private, deleted, or removed |",
        f"| **FAILED** | **{st['status_counts'].get('FAILED', 0):,}** | {round(st['status_counts'].get('FAILED', 0)/st['total_jobs']*100, 1) if st['total_jobs'] else 0}% | Unrecoverable execution error |",
        f"| **PENDING / RUNNING** | **{st['pending_jobs']:,}** | {round(st['pending_jobs']/st['total_jobs']*100, 1) if st['total_jobs'] else 0}% | Awaiting execution or batch allocation |",
        "",
        "---",
        "",
        "## 2. Per-Year Deepening Completion",
        "",
        "| Calendar Year | Target Videos | Completed | No Comments | Disabled | Unavailable / Failed | Pending | Completion Rate |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    for y in st["by_year"]:
        term = y["completed"] + y["no_comments"] + y["disabled"] + y["unavail"] + y["failed"]
        tot = y["manifest_total"]
        pct = round(term / tot * 100, 1) if tot > 0 else 0.0
        lines.append(
            f"| **{y['year']}** | {tot} | {y['completed']} | {y['no_comments']} | {y['disabled']} | {y['unavail'] + y['failed']} | {y['pending']} | **{pct}%** |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. Methodological & Privacy Guarantees",
        "",
        "1. **Full Temporal Scope:** All comments are retrieved chronologically using `commentThreads.list` with `order=time` and `pageToken` pagination.",
        "2. **Strict Privacy Boundary:** Raw author IDs are immediately hashed using persistent HMAC-SHA256 within the item processing loop. Zero raw commenter names, handles, URLs, or comment texts are ever written to disk or preserved in memory.",
        "3. **Zero Fallback Substitution:** `interaction_at` represents verified comment `publishedAt`. Missing timestamps are never populated with video upload dates.",
        "4. **Explicit Precedence Hierarchy:** In snapshot construction, explicit source provenance precedence (`T6 deep > T5 stratified > T2 pilot > legacy`) excludes lower-priority comment rows for the same video, verified by regression tests."
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info(f"Generated deepening report: {output_path}")


def run_pilot(db_path: Path = DEFAULT_DEEP_CHECKPOINT_DB, budget: int = 400) -> None:
    """
    Selects ~20 diverse target videos across all years (2020-2026) and different channels,
    and runs them through DeepCommentBackfiller.
    """
    logger.info("Selecting diverse pilot targets across 2020-2026...")
    with sqlite3.connect(str(db_path)) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        # Pick 3 targets per year from 2020 to 2026 (7 * 3 = 21 targets)
        cur.execute("""
            WITH Ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER(PARTITION BY year ORDER BY channel_id ASC, video_id ASC) as rn
                FROM deep_backfill_jobs
                WHERE status IN ('PENDING', 'RETRYABLE')
            )
            SELECT * FROM Ranked
            WHERE rn <= 3
            ORDER BY year ASC, channel_id ASC
        """)
        pilot_jobs = [dict(r) for r in cur.fetchall()]

    logger.info(f"Selected {len(pilot_jobs)} pilot target videos across years 2020-2026.")
    backfiller = DeepCommentBackfiller(db_path=db_path, quota_budget=budget)

    counts: Dict[str, int] = {}
    for j in pilot_jobs:
        try:
            st = backfiller.process_deep_job(j)
            counts[st] = counts.get(st, 0) + 1
        except BudgetExhaustedException as be:
            logger.warning(f"Pilot halted due to quota limit: {be}")
            break

    logger.info(f"Pilot execution finished with counts: {counts}, API requests used: {backfiller.api_requests_used}")
    print_status(db_path)
    generate_report(REPORT_PATH, db_path)


def main():
    parser = argparse.ArgumentParser(description="Phase T6 Deep Comment History Orchestrator")
    parser.add_argument("--status", action="store_true", help="Print current status of T6 checkpoint")
    parser.add_argument("--pilot", action="store_true", help="Run bounded pilot on ~21 target videos")
    parser.add_argument("--limit", type=int, default=None, help="Max jobs to process in this run")
    parser.add_argument("--api-quota-budget", type=int, default=2500, help="Max API requests before clean halt")
    parser.add_argument("--generate-report", action="store_true", help="Generate markdown status report")
    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.generate_report:
        generate_report()
        return

    if args.pilot:
        run_pilot(budget=args.api_quota_budget)
        return

    backfiller = DeepCommentBackfiller(quota_budget=args.api_quota_budget)
    counts = backfiller.run_batch(limit=args.limit)
    logger.info(f"Batch execution completed: {counts}, API requests used: {backfiller.api_requests_used}")

    print_status()
    generate_report()


if __name__ == "__main__":
    main()
