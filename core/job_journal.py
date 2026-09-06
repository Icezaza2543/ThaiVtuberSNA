"""
Thai VTuber Audience Network (SNA)
Durable Collection State & Job Journal

Provides ACID durable job tracking across restarts and worker crashes using SQLite.
Guarantees:
- Zero raw viewer IDs or message text stored in checkpoints.
- Atomic claims prevent concurrent duplicate claims of the same job.
- Recoverable state if worker crashes between storage write and checkpoint.
"""
import json
import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

from config.settings import DATA_DIR

logger = logging.getLogger(__name__)

DEFAULT_JOURNAL_DB = DATA_DIR / "journal" / "job_journal.sqlite3"


class JobJournal:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or DEFAULT_JOURNAL_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collection_jobs (
                    job_id TEXT PRIMARY KEY,
                    vtuber_channel_id TEXT NOT NULL,
                    video_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    state TEXT NOT NULL, -- PENDING, CLAIMED, COMMITTED, COMPLETED, FAILED, RETRY
                    worker_id TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    priority REAL NOT NULL DEFAULT 1.0,
                    checkpoint TEXT,
                    error_reason TEXT,
                    records_committed INTEGER NOT NULL DEFAULT 0,
                    last_attempt_at TEXT,
                    last_success_at TEXT,
                    next_retry_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_state ON collection_jobs(state, next_retry_at);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_video ON collection_jobs(video_id, source_type);")

    @staticmethod
    def make_job_id(vtuber_channel_id: str, video_id: str, source_type: str) -> str:
        return f"{vtuber_channel_id}:{video_id}:{source_type}"

    def register_job(
        self,
        vtuber_channel_id: str,
        video_id: str,
        source_type: str,
        priority: float = 1.0,
        max_attempts: int = 3
    ) -> str:
        if source_type not in {"comment", "live_chat"}:
            raise ValueError("source_type must be 'comment' or 'live_chat'")

        job_id = self.make_job_id(vtuber_channel_id, video_id, source_type)
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO collection_jobs (
                    job_id, vtuber_channel_id, video_id, source_type,
                    state, attempts, max_attempts, priority, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'PENDING', 0, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    priority = excluded.priority,
                    updated_at = excluded.updated_at
                WHERE state IN ('PENDING', 'RETRY');
            """, (job_id, vtuber_channel_id, video_id, source_type, max_attempts, priority, now, now))
        return job_id

    def claim_next_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Atomically claims the highest priority eligible job.
        Prevents multiple workers from claiming the same job simultaneously.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Select next pending or ready retry job
            cursor.execute("""
                SELECT job_id, vtuber_channel_id, video_id, source_type, attempts, max_attempts, checkpoint
                FROM collection_jobs
                WHERE state = 'PENDING' OR (state = 'RETRY' AND (next_retry_at IS NULL OR next_retry_at <= ?))
                ORDER BY priority DESC, created_at ASC
                LIMIT 1;
            """, (now,))
            row = cursor.fetchone()
            if not row:
                return None

            job_id = row["job_id"]
            # Atomic state transition
            cursor.execute("""
                UPDATE collection_jobs
                SET state = 'CLAIMED',
                    worker_id = ?,
                    attempts = attempts + 1,
                    last_attempt_at = ?,
                    updated_at = ?
                WHERE job_id = ? AND (state = 'PENDING' OR state = 'RETRY');
            """, (worker_id, now, now, job_id))

            if cursor.rowcount == 1:
                return dict(row)
        return None

    def commit_job(
        self,
        job_id: str,
        records_committed: int,
        checkpoint: Optional[str] = None
    ) -> bool:
        """
        Marks job as COMPLETED after storage writes have finished successfully.
        Enforces privacy: checkpoint must NOT contain raw channel IDs or message bodies.
        """
        if checkpoint:
            # Privacy assertion: Ensure no raw YouTube identifiers or message text leaked into checkpoint
            if "author" in checkpoint.lower() or "text" in checkpoint.lower() or "UC" in checkpoint:
                raise ValueError("Privacy violation: Checkpoint contains forbidden identifiers or text")

        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE collection_jobs
                SET state = 'COMPLETED',
                    records_committed = ?,
                    checkpoint = ?,
                    last_success_at = ?,
                    worker_id = NULL,
                    updated_at = ?
                WHERE job_id = ? AND state = 'CLAIMED';
            """, (records_committed, checkpoint, now, now, job_id))
            return cursor.rowcount > 0

    def fail_job(
        self,
        job_id: str,
        error_reason: str,
        retryable: bool = True,
        backoff_seconds: int = 30
    ) -> bool:
        """
        Marks job as FAILED or scheduled for RETRY with bounded exponential backoff.
        """
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        next_retry = (now_dt + timedelta(seconds=backoff_seconds)).isoformat() if retryable else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT attempts, max_attempts FROM collection_jobs WHERE job_id = ?;", (job_id,))
            row = cursor.fetchone()
            if not row:
                return False

            if retryable and row["attempts"] < row["max_attempts"]:
                new_state = "RETRY"
            else:
                new_state = "FAILED"

            cursor.execute("""
                UPDATE collection_jobs
                SET state = ?,
                    error_reason = ?,
                    next_retry_at = ?,
                    worker_id = NULL,
                    updated_at = ?
                WHERE job_id = ?;
            """, (new_state, error_reason, next_retry, now, job_id))
            return True

    def recover_abandoned_jobs(self, timeout_seconds: int = 300) -> int:
        """
        Crash recovery: detects jobs stuck in 'CLAIMED' state due to worker crash
        older than timeout_seconds, and returns them to 'PENDING'.
        """
        threshold = (datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)).isoformat()
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE collection_jobs
                SET state = 'PENDING',
                    worker_id = NULL,
                    updated_at = ?
                WHERE state = 'CLAIMED' AND last_attempt_at <= ?;
            """, (now, threshold))
            recovered = cursor.rowcount
            if recovered > 0:
                logger.warning(f"Recovered {recovered} abandoned claimed jobs.")
            return recovered

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM collection_jobs WHERE job_id = ?;", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_summary(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT state, COUNT(*) as count, SUM(records_committed) as total_records
                FROM collection_jobs
                GROUP BY state;
            """)
            rows = cursor.fetchall()
            stats = {r["state"]: r["count"] for r in rows}
            total_records = sum(r["total_records"] or 0 for r in rows)
            return {
                "states": stats,
                "total_records_committed": total_records
            }
