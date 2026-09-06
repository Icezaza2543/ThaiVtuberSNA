"""
Thai VTuber Audience Network (SNA)
Continuous Lightweight Collection Runner

Usage:
  python scripts/run_continuous_collection.py [--channels 6] [--workers 3] [--scheduler greedy]
  python scripts/run_continuous_collection.py --status
  python scripts/run_continuous_collection.py --recover
"""
import argparse
import json
import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from collector.continuous_collector import ContinuousCollector
from core.job_journal import JobJournal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ContinuousCollectionRunner")

# Real Candidate Pool for Bounded Collection
DEFAULT_CANDIDATE_POOL = [
    {"channel_id": "UCqhhWjpw23dWhJ5rRwCCrMA", "name": "Aisha Channel", "agency": "Independent", "video_id": "G1LXXzZx48c"},
    {"channel_id": "UCuZ1ajvlGFUMCHZAPdetKHw", "name": "Dacapo Ch.【ARP】", "agency": "Algorhythm Project", "video_id": "5o4H5e3QLk0"},
    {"channel_id": "UCAr4U_HGMYXn1EZjdWiGSLQ", "name": "Baabel Ch.【ARP】", "agency": "Algorhythm Project", "video_id": "FASPZW15oSo"},
    {"channel_id": "UCNTEr2_96vJnXNazr5MwNLA", "name": "Schneider Ch.【ARP】", "agency": "Algorhythm Project", "video_id": "D3TxwjyV2I8"},
    {"channel_id": "UCEvyDOkcGkzCTo62d9BrhkA", "name": "Minami Cera Polygon", "agency": "Polygon Official", "video_id": "EAmImNNAQSQ"},
    {"channel_id": "UCfcNIwkAhHcDTP1rQg2n5nw", "name": "Tiara Rexa Polygon", "agency": "Polygon Official", "video_id": "0Txm89An9Io"}
]


def main():
    parser = argparse.ArgumentParser(description="Continuous Lightweight Collection Runner")
    parser.add_argument("--channels", type=int, default=6, help="Max channels to process")
    parser.add_argument("--events-per-job", type=int, default=120, help="Max events extracted per job")
    parser.add_argument("--workers", type=int, default=3, help="Max concurrent worker threads")
    parser.add_argument("--scheduler", choices=["greedy", "pso"], default="greedy", help="Scheduler algorithm")
    parser.add_argument("--timeout", type=float, default=60.0, help="Max cycle duration in seconds")
    parser.add_argument("--status", action="store_true", help="Print journal status and exit")
    parser.add_argument("--recover", action="store_true", help="Recover abandoned claimed jobs and exit")

    args = parser.parse_args()

    if args.status:
        journal = JobJournal()
        summary = journal.get_summary()
        print("\n=== Durable Job Journal Status ===")
        print(json.dumps(summary, indent=2))
        return

    if args.recover:
        journal = JobJournal()
        recovered = journal.recover_abandoned_jobs(timeout_seconds=0)
        print(f"Recovered {recovered} abandoned jobs.")
        return

    collector = ContinuousCollector(
        max_workers=args.workers,
        scheduler_type=args.scheduler
    )

    candidates = DEFAULT_CANDIDATE_POOL[:args.channels]
    logger.info(f"Planning collection for {len(candidates)} channels...")
    collector.plan_and_register_jobs(candidates, sources=["comment"])

    logger.info("Executing bounded continuous collection cycle...")
    summary = collector.run_bounded_cycle(
        max_jobs_to_process=args.channels,
        max_events_per_job=args.events_per_job,
        max_cycle_seconds=args.timeout
    )

    print("\n==================================================")
    print("      BOUNDED COLLECTION RUN REPORT               ")
    print("==================================================")
    print(f" Elapsed Time:     {summary['elapsed_seconds']} s")
    print(f" Jobs Processed:   {summary['jobs_processed']}")
    print(f" Records Saved:    {summary['total_records_persisted']}")
    print(f" Status Breakdown: {json.dumps(summary['status_breakdown'], indent=2)}")
    print(f" Journal Summary:  {json.dumps(summary['journal_summary']['states'], indent=2)}")
    print("==================================================")


if __name__ == "__main__":
    main()
