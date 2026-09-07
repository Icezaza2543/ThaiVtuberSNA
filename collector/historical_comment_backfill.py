"""
collector/historical_comment_backfill.py

Phase T5-C: Privacy-Safe Resumable Historical Comment Backfill Engine
Extracts historical comment observations according to the stratified sampling manifest:
- Enforces strict extraction boundary: raw author ID is immediately HMAC-hashed.
- Deduplicates commenters per video (one presence record per viewer per video).
- Strict timestamps: comment interaction_at = actual publishedAt or None (never now() or video date).
- Configurable API quota budget: cleanly checkpoints upon reaching budget limit.
- Resumable SQLite checkpoint tracking: safe across interruptions and restarts.
- Atomic file writes via _atomic_replace_with_retry: fail-closed integrity.

Persisted Output:
data/temporal/observations/comment/{channel_id}/{video_id}.parquet
"""
import sys
import json
import time
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set

import requests
import pyarrow as pa
import pyarrow.parquet as pq

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DATA_DIR, YOUTUBE_API_KEY
from core.hasher import PrivacyHasher
from collector.historical_catalog_builder import _atomic_replace_with_retry

logger = logging.getLogger("HistoricalCommentBackfill")

DEFAULT_CHECKPOINT_DB = DATA_DIR / "temporal" / "backfill" / "backfill_checkpoint.sqlite3"
DEFAULT_OBSERVATIONS_DIR = DATA_DIR / "temporal" / "observations"

OBSERVATION_SCHEMA = pa.schema([
    ("viewer_hash", pa.string()),
    ("vtuber_channel_id", pa.string()),
    ("video_id", pa.string()),
    ("source_type", pa.string()),              # 'comment'
    ("video_published_at", pa.string()),        # ISO string
    ("interaction_at", pa.string()),            # ISO string or None
    ("timestamp_quality", pa.string()),         # 'exact' or 'missing'
    ("collected_at", pa.string()),              # crawler UTC ISO
    ("sampling_manifest_version", pa.string()),  # '1.0'
    ("sample_id", pa.string()),
    ("capture_status", pa.string()),
    ("backend", pa.string()),                   # 'youtube_api_v3' | 'yt_dlp'
    ("partial_capture", pa.bool_()),
])


def parse_iso_dt(dt_str: Optional[str]) -> Optional[str]:
    """Parses an ISO string and returns a standardized UTC ISO string or None."""
    if not dt_str:
        return None
    try:
        clean = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return None


class BudgetExhaustedException(Exception):
    """Raised when configured API quota budget is reached."""
    pass


class HistoricalCommentBackfiller:
    def __init__(
        self,
        db_path: Path = DEFAULT_CHECKPOINT_DB,
        observations_dir: Path = DEFAULT_OBSERVATIONS_DIR,
        quota_budget: int = 7000,
        max_comments_per_video: int = 100,
        api_key: Optional[str] = None,
        hasher: Optional[PrivacyHasher] = None,
        session: Optional[requests.Session] = None,
        use_ytdlp_fallback: bool = False
    ):
        self.db_path = Path(db_path)
        self.observations_dir = Path(observations_dir)
        self.quota_budget = int(quota_budget)
        self.max_comments_per_video = int(max_comments_per_video)
        self.api_key = api_key or YOUTUBE_API_KEY
        self.hasher = hasher or PrivacyHasher()
        self.session = session or requests.Session()
        self.use_ytdlp_fallback = use_ytdlp_fallback

        self.api_requests_used = 0
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.observations_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initializes checkpoint SQLite table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backfill_jobs (
                    sample_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    video_id TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    video_published_at TEXT,
                    time_bin TEXT,
                    sampling_reason TEXT,
                    selection_method TEXT,
                    status TEXT NOT NULL, -- PENDING, COMPLETED, NO_COMMENTS, COMMENTS_DISABLED, VIDEO_UNAVAILABLE, FAILED
                    capture_status TEXT,  -- COMPLETE_WITHIN_LIMIT, PARTIAL_CAPTURE, NO_COMMENTS, etc.
                    attempts INTEGER DEFAULT 0,
                    backend TEXT,
                    last_error TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    capture_count INTEGER DEFAULT 0,
                    partial_capture INTEGER DEFAULT 0,
                    output_file TEXT
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bf_status ON backfill_jobs(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bf_channel ON backfill_jobs(channel_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bf_year ON backfill_jobs(year);")
            conn.commit()

    def sync_manifest(self, manifest_records: List[Dict[str, Any]]) -> int:
        """Inserts any new records from sampling manifest into SQLite with PENDING status."""
        new_count = 0
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            for r in manifest_records:
                cur.execute("""
                    INSERT OR IGNORE INTO backfill_jobs (
                        sample_id, channel_id, video_id, year, video_published_at,
                        time_bin, sampling_reason, selection_method, status, attempts
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 0);
                """, (
                    r["sample_id"],
                    r["channel_id"],
                    r["video_id"],
                    r["year"],
                    r.get("video_published_at"),
                    r.get("time_bin"),
                    r.get("sampling_reason"),
                    r.get("selection_method")
                ))
                if cur.rowcount > 0:
                    new_count += 1
            conn.commit()
        logger.info(f"Synchronized manifest into checkpoint DB: {new_count} new jobs added.")
        return new_count

    def get_pending_jobs(self, limit: Optional[int] = None, channel_ids: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
        """Retrieves pending or retryable jobs."""
        query = "SELECT sample_id, channel_id, video_id, year, video_published_at, attempts FROM backfill_jobs WHERE status IN ('PENDING', 'RETRYABLE')"
        params = []
        if channel_ids:
            placeholders = ",".join("?" for _ in channel_ids)
            query += f" AND channel_id IN ({placeholders})"
            params.extend(list(channel_ids))
        query += " ORDER BY year ASC, channel_id ASC, sample_id ASC"
        if limit:
            query += f" LIMIT {int(limit)}"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def extract_comments_api(
        self,
        video_id: str,
        channel_id: str,
        sample_id: str,
        video_published_at: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], str, bool, Optional[str]]:
        """
        Fetches up to max_comments_per_video using YouTube Data API v3.
        Enforces extraction boundary: raw author ID is hashed immediately inside loop.
        Returns: (deduplicated_observations, capture_status, partial_capture, error_msg)
        """
        if self.api_requests_used >= self.quota_budget:
            raise BudgetExhaustedException(f"API quota budget reached: {self.api_requests_used}/{self.quota_budget}")

        url = "https://www.googleapis.com/youtube/v3/commentThreads"
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(self.max_comments_per_video, 100),
            "textFormat": "plainText",
            "key": self.api_key
        }

        self.api_requests_used += 1
        now_utc = datetime.now(timezone.utc).isoformat()

        try:
            resp = self.session.get(url, params=params, timeout=12)
        except Exception as e:
            return [], "API_ERROR", False, f"Network error: {str(e)}"

        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            has_next = bool(data.get("nextPageToken"))
            total_items = len(items)

            if total_items == 0:
                return [], "NO_COMMENTS", False, None

            # Deduplicate by viewer_hash within this video
            # Keep earliest interaction timestamp for each distinct viewer
            viewer_map: Dict[str, Dict[str, Any]] = {}
            for it in items:
                snip = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                cid = snip.get("authorChannelId", {}).get("value")
                pub_raw = snip.get("publishedAt")

                if cid and str(cid).startswith("UC"):
                    # IMMEDIATE HMAC pseudonymization
                    v_hash = self.hasher.hash_viewer_id(str(cid))
                    inter_iso = parse_iso_dt(pub_raw)
                    ts_quality = "exact" if inter_iso is not None else "missing"

                    if v_hash not in viewer_map:
                        viewer_map[v_hash] = {
                            "viewer_hash": v_hash,
                            "vtuber_channel_id": channel_id,
                            "video_id": video_id,
                            "source_type": "comment",
                            "video_published_at": video_published_at,
                            "interaction_at": inter_iso,
                            "timestamp_quality": ts_quality,
                            "collected_at": now_utc,
                            "sampling_manifest_version": "1.0",
                            "sample_id": sample_id,
                            "backend": "youtube_api_v3",
                        }
                    else:
                        # If existing record had missing timestamp and this one has exact, update
                        if viewer_map[v_hash]["timestamp_quality"] == "missing" and ts_quality == "exact":
                            viewer_map[v_hash]["interaction_at"] = inter_iso
                            viewer_map[v_hash]["timestamp_quality"] = "exact"

            partial_capture = has_next or (total_items >= self.max_comments_per_video)
            capture_status = "PARTIAL_CAPTURE" if partial_capture else "COMPLETE_WITHIN_LIMIT"

            # Assign capture_status and partial_capture flag to all rows
            res = []
            for row in viewer_map.values():
                row["capture_status"] = capture_status
                row["partial_capture"] = partial_capture
                res.append(row)

            return res, capture_status, partial_capture, None

        elif resp.status_code == 403:
            err_body = resp.text
            if "commentsDisabled" in err_body:
                return [], "COMMENTS_DISABLED", False, "commentsDisabled"
            elif "quotaExceeded" in err_body or "dailyLimitExceeded" in err_body:
                raise BudgetExhaustedException("Google API Quota Exceeded (HTTP 403 quotaExceeded).")
            elif "videoNotFound" in err_body:
                return [], "VIDEO_UNAVAILABLE", False, "videoNotFound"
            else:
                return [], "API_ERROR", False, f"HTTP 403: {err_body[:200]}"

        elif resp.status_code == 404:
            return [], "VIDEO_UNAVAILABLE", False, "HTTP 404 Not Found"

        return [], "API_ERROR", False, f"HTTP {resp.status_code}: {resp.text[:200]}"

    def process_job(self, job: Dict[str, Any]) -> str:
        """Processes a single sampling job and writes Parquet if comments are present."""
        sample_id = job["sample_id"]
        channel_id = job["channel_id"]
        video_id = job["video_id"]
        video_published_at = job.get("video_published_at")

        started_at = datetime.now(timezone.utc).isoformat()

        # Update job to IN_PROGRESS
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE backfill_jobs SET status = 'IN_PROGRESS', started_at = ?, attempts = attempts + 1 WHERE sample_id = ?",
                (started_at, sample_id)
            )
            conn.commit()

        observations, capture_status, partial_capture, err_msg = self.extract_comments_api(
            video_id=video_id,
            channel_id=channel_id,
            sample_id=sample_id,
            video_published_at=video_published_at
        )

        completed_at = datetime.now(timezone.utc).isoformat()
        out_file_str = None

        if observations:
            # Write atomic Parquet file
            target_dir = self.observations_dir / "comment" / channel_id
            target_dir.mkdir(parents=True, exist_ok=True)
            target_parquet = target_dir / f"{video_id}.parquet"
            tmp_parquet = target_dir / f"{video_id}.parquet.tmp"

            tbl = pa.Table.from_pylist(observations, schema=OBSERVATION_SCHEMA)
            pq.write_table(tbl, tmp_parquet, compression="snappy")
            _atomic_replace_with_retry(tmp_parquet, target_parquet, attempts=5, delay=0.05)
            out_file_str = str(target_parquet)

        # Determine final status
        if capture_status in ("COMPLETE_WITHIN_LIMIT", "PARTIAL_CAPTURE"):
            final_status = "COMPLETED"
        elif capture_status in ("NO_COMMENTS", "COMMENTS_DISABLED", "VIDEO_UNAVAILABLE"):
            final_status = capture_status
        else:
            final_status = "FAILED"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE backfill_jobs SET
                    status = ?,
                    capture_status = ?,
                    backend = 'youtube_api_v3',
                    last_error = ?,
                    completed_at = ?,
                    capture_count = ?,
                    partial_capture = ?,
                    output_file = ?
                WHERE sample_id = ?
            """, (
                final_status,
                capture_status,
                err_msg,
                completed_at,
                len(observations),
                1 if partial_capture else 0,
                out_file_str,
                sample_id
            ))
            conn.commit()

        return final_status

    def run_backfill(
        self,
        limit: Optional[int] = None,
        channel_ids: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """Runs the backfill process on pending jobs up to limit or budget exhaustion."""
        pending = self.get_pending_jobs(limit=limit, channel_ids=channel_ids)
        logger.info(f"Found {len(pending)} pending jobs to process (budget: {self.quota_budget - self.api_requests_used} requests remaining).")

        attempted = 0
        completed = 0
        partial = 0
        comments_disabled = 0
        no_comments = 0
        unavailable = 0
        failed = 0
        total_observations = 0
        budget_exhausted = False

        for job in pending:
            if self.api_requests_used >= self.quota_budget:
                logger.warning(f"API quota budget reached ({self.api_requests_used}/{self.quota_budget}). Cleanly suspending run.")
                budget_exhausted = True
                break

            try:
                attempted += 1
                status = self.process_job(job)
                if status == "COMPLETED":
                    completed += 1
                elif status == "COMMENTS_DISABLED":
                    comments_disabled += 1
                elif status == "NO_COMMENTS":
                    no_comments += 1
                elif status == "VIDEO_UNAVAILABLE":
                    unavailable += 1
                else:
                    failed += 1

                if attempted % 25 == 0:
                    logger.info(f"Processed {attempted}/{len(pending)} videos (API calls: {self.api_requests_used}/{self.quota_budget}).")

            except BudgetExhaustedException as be:
                logger.warning(f"Budget limit exception encountered: {be}")
                budget_exhausted = True
                break
            except Exception as ex:
                logger.error(f"Error processing job {job['sample_id']}: {ex}")
                failed += 1

        # Summary statistics from DB
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*), SUM(capture_count) FROM backfill_jobs WHERE status = 'COMPLETED'")
            row = cur.fetchone()
            total_db_completed = row[0] or 0
            total_db_observations = row[1] or 0

            cur.execute("SELECT COUNT(*) FROM backfill_jobs WHERE status IN ('PENDING', 'RETRYABLE')")
            total_db_pending = cur.fetchone()[0] or 0

        summary = {
            "videos_attempted": attempted,
            "videos_completed": completed,
            "comments_disabled": comments_disabled,
            "no_comments": no_comments,
            "videos_unavailable": unavailable,
            "videos_failed": failed,
            "budget_exhausted": budget_exhausted,
            "api_requests_used": self.api_requests_used,
            "budget_remaining": max(0, self.quota_budget - self.api_requests_used),
            "db_total_completed": total_db_completed,
            "db_total_observations": total_db_observations,
            "db_total_pending": total_db_pending,
        }
        logger.info(f"Backfill batch complete: {summary}")
        return summary
