"""
Thai VTuber Audience Network (SNA)
Continuous Lightweight Collector Orchestrator

Coordinates bounded, idempotent, and privacy-preserving collection across:
1. Public VOD / Video Comments (Snapshot reconciliation)
2. Live Chat Telemetry (Bounded in-memory streaming via LiveChatAdapter)
3. Durable ACID State & Claim Tracking (JobJournal)
4. Idempotent Columnar Persistence (ParquetStorageManager)

Guarantees:
- Greedy scheduler is default; PSO is optional.
- Bounded runtime, worker counts, retry budgets, and timeouts.
- Explicit outcome categorisation without silent channel replacement.
- Zero raw viewer IDs or message bodies persisted anywhere.
"""
import concurrent.futures
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.hasher import PrivacyHasher, load_persistent_secret_key, compute_key_fingerprint
from core.job_journal import JobJournal
from core.scheduler import BaselinePriorityQueueScheduler, PSOScheduler
from storage.parquet_manager import ParquetStorageManager
from collector.youtube_collector import YouTubeCollector
from collector.live_chat_adapter import LiveChatAdapter
from config.settings import DATA_DIR, EVENTS_DIR

logger = logging.getLogger(__name__)


class ContinuousCollector:
    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        journal_path: Optional[Path] = None,
        max_workers: int = 3,
        scheduler_type: str = "greedy",
        hasher: Optional[PrivacyHasher] = None
    ):
        # Validate persistent key continuity before any collector operations
        self.key_fingerprint = compute_key_fingerprint(load_persistent_secret_key())
        self.hasher = hasher or PrivacyHasher()
        
        self.storage_dir = Path(storage_dir or (DATA_DIR / "real" / "events"))
        self.storage_mgr = ParquetStorageManager(base_dir=self.storage_dir)
        self.journal = JobJournal(db_path=journal_path)
        
        self.max_workers = max(1, max_workers)
        self.scheduler_type = scheduler_type.lower()
        
        self.comment_collector = YouTubeCollector()
        self.live_chat_adapter = LiveChatAdapter(hasher=self.hasher)

        # Recover any stale claimed jobs from a previous interrupted session
        self.journal.recover_abandoned_jobs(timeout_seconds=60)

    def plan_and_register_jobs(
        self,
        candidate_pool: List[Dict[str, Any]],
        sources: List[str] = None
    ) -> List[str]:
        """
        Registers candidate videos/channels into the durable JobJournal.
        Uses priority queue / PSO scheduler to assign priority scores.
        """
        sources = sources or ["comment"]
        registered_job_ids = []

        # Build stream candidate list for scheduler
        sched_items = []
        for cand in candidate_pool:
            cid = cand["channel_id"]
            vid = cand.get("video_id") or self.comment_collector.fetch_latest_video_for_channel(cid)
            if not vid:
                continue
            cand_copy = dict(cand)
            cand_copy["video_id"] = vid
            sched_items.append({
                "vtuber_channel_id": cid,
                "video_id": vid,
                "is_live": False,
                "vtuber": cand_copy
            })

        # Schedule jobs based on selected strategy
        if self.scheduler_type == "pso" and sched_items:
            scheduler = PSOScheduler(num_workers=self.max_workers, swarm_size=10, max_iter=15)
        else:
            scheduler = BaselinePriorityQueueScheduler(num_workers=self.max_workers)

        scheduled_jobs = scheduler.schedule(sched_items)
        priority_map = {j.video_id: getattr(j, "priority_score", 1.0) for j in scheduled_jobs}

        for item in sched_items:
            cid = item["vtuber_channel_id"]
            vid = item["video_id"]
            score = priority_map.get(vid, 1.0)
            for src in sources:
                job_id = self.journal.register_job(
                    vtuber_channel_id=cid,
                    video_id=vid,
                    source_type=src,
                    priority=score,
                    max_attempts=3
                )
                registered_job_ids.append(job_id)

        logger.info(f"Registered {len(registered_job_ids)} collection jobs in durable journal.")
        return registered_job_ids

    def process_single_job(self, job: Dict[str, Any], max_events: int = 150) -> Dict[str, Any]:
        """
        Executes a claimed job, reconciles storage idempotently, and commits status.
        Never replaces channels or suppresses failure reasons.
        """
        job_id = job["job_id"]
        cid = job["vtuber_channel_id"]
        vid = job["video_id"]
        source_type = job["source_type"]

        logger.info(f"Worker processing job {job_id} ({source_type})...")
        t0 = time.perf_counter()

        try:
            if source_type == "comment":
                # Collect snapshot comments
                events = self.comment_collector.collect_aggregated_events(
                    {"vtuber_channel_id": cid, "video_id": vid, "source_type": "comment"},
                    max_comments=max_events
                )
                if not events:
                    self.journal.commit_job(job_id, records_committed=0)
                    return {"job_id": job_id, "status": "EMPTY_RESULT", "records": 0, "duration": time.perf_counter() - t0}

                # Idempotent write / reconciliation
                written_path = self.storage_mgr.write_events(events)
                self.journal.commit_job(job_id, records_committed=len(events))
                return {
                    "job_id": job_id,
                    "status": "SUCCESS",
                    "records": len(events),
                    "path": str(written_path),
                    "duration": time.perf_counter() - t0
                }

            elif source_type == "live_chat":
                # Collect memory-only live chat
                outcome = self.live_chat_adapter.collect_live_chat_events(
                    {"vtuber_channel_id": cid, "video_id": vid},
                    max_messages=max_events,
                    continuation_token=job.get("checkpoint")
                )
                status = outcome["status"]
                events = outcome["events"]

                if status == "SUCCESS" and events:
                    written_path = self.storage_mgr.write_events(events)
                    # Use continuation token as checkpoint if available (no raw IDs)
                    token = outcome.get("continuation_token")
                    safe_checkpoint = f'{{"continuation": "{token}"}}' if token else None
                    self.journal.commit_job(job_id, records_committed=len(events), checkpoint=safe_checkpoint)
                    return {
                        "job_id": job_id,
                        "status": "SUCCESS",
                        "records": len(events),
                        "path": str(written_path),
                        "duration": time.perf_counter() - t0
                    }
                elif status == "LIVE_CHAT_UNAVAILABLE":
                    self.journal.fail_job(job_id, error_reason="LIVE_CHAT_UNAVAILABLE", retryable=False)
                    return {"job_id": job_id, "status": "LIVE_CHAT_UNAVAILABLE", "records": 0, "duration": time.perf_counter() - t0}
                elif status == "RATE_LIMITED":
                    self.journal.fail_job(job_id, error_reason="RATE_LIMITED", retryable=True, backoff_seconds=60)
                    return {"job_id": job_id, "status": "RATE_LIMITED", "records": 0, "duration": time.perf_counter() - t0}
                else:
                    self.journal.fail_job(job_id, error_reason=outcome.get("reason", "EXTRACTION_FAILURE"), retryable=True)
                    return {"job_id": job_id, "status": "EXTRACTION_FAILURE", "records": 0, "duration": time.perf_counter() - t0}

            else:
                self.journal.fail_job(job_id, error_reason=f"INVALID_SOURCE_{source_type}", retryable=False)
                return {"job_id": job_id, "status": "EXTRACTION_FAILURE", "records": 0, "duration": time.perf_counter() - t0}

        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}")
            err_str = str(e).lower()
            if "comments are turned off" in err_str or "disabled" in err_str:
                status = "COMMENTS_DISABLED"
                retryable = False
            else:
                status = "EXTRACTION_FAILURE"
                retryable = True

            self.journal.fail_job(job_id, error_reason=status, retryable=retryable)
            return {"job_id": job_id, "status": status, "records": 0, "duration": time.perf_counter() - t0, "error": str(e)}

    def run_bounded_cycle(
        self,
        max_jobs_to_process: int = 10,
        max_events_per_job: int = 120,
        max_cycle_seconds: float = 60.0
    ) -> Dict[str, Any]:
        """
        Executes a bounded batch of jobs across worker threads.
        """
        start_time = time.perf_counter()
        results = []
        processed_count = 0

        logger.info(f"Starting bounded collection cycle (max_jobs={max_jobs_to_process}, workers={self.max_workers})...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_job = {}

            while processed_count < max_jobs_to_process:
                # Check cycle timeout
                if (time.perf_counter() - start_time) >= max_cycle_seconds:
                    logger.warning("Bounded collection cycle reached maximum time limit. Halting gracefully.")
                    break

                # Claim job atomically
                worker_tag = f"worker_{processed_count % self.max_workers}"
                job = self.journal.claim_next_job(worker_id=worker_tag)
                if not job:
                    # No pending jobs available
                    break

                fut = executor.submit(self.process_single_job, job, max_events_per_job)
                future_to_job[fut] = job["job_id"]
                processed_count += 1

            for fut in concurrent.futures.as_completed(future_to_job):
                jid = future_to_job[fut]
                try:
                    res = fut.result()
                    results.append(res)
                except Exception as exc:
                    results.append({"job_id": jid, "status": "EXTRACTION_FAILURE", "error": str(exc)})

        elapsed = time.perf_counter() - start_time
        total_records = sum(r.get("records", 0) for r in results)
        statuses = {}
        for r in results:
            st = r.get("status", "UNKNOWN")
            statuses[st] = statuses.get(st, 0) + 1

        summary = {
            "elapsed_seconds": round(elapsed, 3),
            "jobs_processed": len(results),
            "total_records_persisted": total_records,
            "status_breakdown": statuses,
            "journal_summary": self.journal.get_summary()
        }
        logger.info(f"Bounded cycle complete: {summary}")
        return summary
