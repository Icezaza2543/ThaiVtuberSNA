"""
collector/deep_comment_backfill.py

Phase T6: Resumable Multipage Deep Comment Collector
Deepens partial-capture historical videos from Phase T5:
- Paginates YouTube Data API commentThreads.list using nextPageToken until exhausted.
- Enforces strict privacy extraction boundary: raw authorChannelId is immediately
  HMAC-hashed via PrivacyHasher inside the item iteration loop.
- No raw commenter names, handles, URLs, or comment texts are ever persisted or kept in memory.
- Deduplicates per (viewer_hash, channel_id, video_id, source_type).
- Preserves earliest interaction timestamp, latest interaction timestamp, and appearance count.
- Dedicated T6 SQLite checkpoint tracking with staging table for crash-safe mid-video resumption.
- Respects global API quota budget and cleanly checkpoints upon exhaustion.
- Atomic Parquet persistence via _atomic_replace_with_retry.

Persisted Output:
data/temporal/deep_observations/comment/{channel_id}/{video_id}.parquet
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

logger = logging.getLogger("DeepCommentBackfill")

DEFAULT_DEEP_CHECKPOINT_DB = DATA_DIR / "temporal" / "deep_backfill" / "deep_backfill_checkpoint.sqlite3"
DEFAULT_DEEP_OBSERVATIONS_DIR = DATA_DIR / "temporal" / "deep_observations"

DEEP_OBSERVATION_SCHEMA = pa.schema([
    ("viewer_hash", pa.string()),
    ("vtuber_channel_id", pa.string()),
    ("video_id", pa.string()),
    ("source_type", pa.string()),              # 'comment'
    ("video_published_at", pa.string()),        # ISO string
    ("interaction_at", pa.string()),            # earliest ISO string or None
    ("latest_interaction_at", pa.string()),     # latest ISO string or None
    ("appearances", pa.int64()),                # count of comments by this viewer on this video
    ("timestamp_quality", pa.string()),         # 'exact' or 'missing'
    ("collected_at", pa.string()),              # crawler UTC ISO
    ("sampling_manifest_version", pa.string()),  # '1.0'
    ("sample_id", pa.string()),
    ("capture_status", pa.string()),            # 'DEEP_COMPLETE'
    ("backend", pa.string()),                   # 'youtube_api_v3'
    ("pages_fetched", pa.int64()),
    ("deep_backfill_version", pa.string()),     # '1.0'
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


class DeepCommentBackfiller:
    def __init__(
        self,
        db_path: Path = DEFAULT_DEEP_CHECKPOINT_DB,
        observations_dir: Path = DEFAULT_DEEP_OBSERVATIONS_DIR,
        quota_budget: int = 2500,
        api_key: Optional[str] = None,
        hasher: Optional[PrivacyHasher] = None,
        session: Optional[requests.Session] = None
    ):
        self.db_path = Path(db_path)
        self.observations_dir = Path(observations_dir)
        self.quota_budget = int(quota_budget)
        self.api_key = api_key or YOUTUBE_API_KEY
        self.hasher = hasher or PrivacyHasher()
        self.session = session or requests.Session()

        self.api_requests_used = 0
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.observations_dir.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self) -> None:
        """Initializes the dedicated T6 checkpoint schema and staging tables."""
        with sqlite3.connect(str(self.db_path)) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS deep_backfill_jobs (
                    sample_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    video_id TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    video_published_at TEXT,
                    time_bin TEXT,
                    sampling_reason TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    capture_status TEXT,
                    next_page_token TEXT,
                    pages_fetched INTEGER DEFAULT 0,
                    total_items_fetched INTEGER DEFAULT 0,
                    capture_count INTEGER DEFAULT 0,
                    oldest_interaction TEXT,
                    newest_interaction TEXT,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    output_file TEXT
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS deep_staging_viewers (
                    sample_id TEXT NOT NULL,
                    viewer_hash TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    video_id TEXT NOT NULL,
                    video_published_at TEXT,
                    earliest_interaction TEXT,
                    latest_interaction TEXT,
                    appearances INTEGER DEFAULT 1,
                    timestamp_quality TEXT,
                    PRIMARY KEY (sample_id, viewer_hash)
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_deep_status ON deep_backfill_jobs(status)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_deep_vid ON deep_backfill_jobs(video_id)")
            con.commit()

    def fetch_page_api(
        self,
        video_id: str,
        page_token: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str], Optional[str]]:
        """
        Executes a single commentThreads.list request.
        Returns: (raw_items, next_page_token, terminal_status, error_msg)
        terminal_status is set if the video is disabled, unavailable, or 404.
        """
        if self.api_requests_used >= self.quota_budget:
            raise BudgetExhaustedException(
                f"API quota budget reached: {self.api_requests_used}/{self.quota_budget}"
            )

        url = "https://www.googleapis.com/youtube/v3/commentThreads"
        params: Dict[str, Any] = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": 100,
            "order": "time",
            "textFormat": "plainText",
            "key": self.api_key
        }
        if page_token:
            params["pageToken"] = page_token

        self.api_requests_used += 1

        try:
            resp = self.session.get(url, params=params, timeout=12)
        except Exception as e:
            return [], None, None, f"Network error: {str(e)}"

        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            next_token = data.get("nextPageToken")
            return items, next_token, None, None

        elif resp.status_code == 403:
            err_body = resp.text
            if "commentsDisabled" in err_body:
                return [], None, "COMMENTS_DISABLED", "commentsDisabled"
            elif "quotaExceeded" in err_body or "dailyLimitExceeded" in err_body:
                raise BudgetExhaustedException("Google API Quota Exceeded (HTTP 403 quotaExceeded).")
            elif "videoNotFound" in err_body:
                return [], None, "VIDEO_UNAVAILABLE", "videoNotFound"
            else:
                return [], None, None, f"HTTP 403: {err_body[:200]}"

        elif resp.status_code == 404:
            return [], None, "VIDEO_UNAVAILABLE", "HTTP 404 Not Found"

        return [], None, None, f"HTTP {resp.status_code}: {resp.text[:200]}"

    def process_deep_job(self, job: Dict[str, Any]) -> str:
        """
        Processes a deep backfill job with full pagination across all commentThreads pages.
        Persists intermediate progress to deep_staging_viewers for crash safety.
        Returns final status: 'COMPLETED', 'NO_COMMENTS', 'COMMENTS_DISABLED', 'VIDEO_UNAVAILABLE', 'FAILED', 'PENDING'
        """
        sample_id = job["sample_id"]
        channel_id = job["channel_id"]
        video_id = job["video_id"]
        pub_at = job.get("video_published_at")
        next_token = job.get("next_page_token")
        pages_fetched = job.get("pages_fetched") or 0
        total_items_fetched = job.get("total_items_fetched") or 0

        now_utc = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(str(self.db_path)) as con:
            con.execute(
                "UPDATE deep_backfill_jobs SET status = 'RUNNING', started_at = COALESCE(started_at, ?), attempts = attempts + 1 WHERE sample_id = ?",
                (now_utc, sample_id)
            )
            con.commit()

        # In-memory accumulator initialized from staging table
        viewer_map: Dict[str, Dict[str, Any]] = {}
        with sqlite3.connect(str(self.db_path)) as con:
            staged = con.execute(
                "SELECT viewer_hash, channel_id, video_id, video_published_at, earliest_interaction, latest_interaction, appearances, timestamp_quality FROM deep_staging_viewers WHERE sample_id = ?",
                (sample_id,)
            ).fetchall()
            for r in staged:
                viewer_map[r[0]] = {
                    "viewer_hash": r[0],
                    "channel_id": r[1],
                    "video_id": r[2],
                    "video_published_at": r[3],
                    "earliest_interaction": r[4],
                    "latest_interaction": r[5],
                    "appearances": r[6],
                    "timestamp_quality": r[7]
                }

        while True:
            try:
                items, new_next_token, term_status, err = self.fetch_page_api(video_id, next_token)
            except BudgetExhaustedException as be:
                logger.warning(f"Quota budget reached during video {video_id}: {be}")
                # Save checkpoint state and exit cleanly
                with sqlite3.connect(str(self.db_path)) as con:
                    con.execute(
                        "UPDATE deep_backfill_jobs SET status = 'PENDING', next_page_token = ?, pages_fetched = ?, total_items_fetched = ?, last_error = ? WHERE sample_id = ?",
                        (next_token, pages_fetched, total_items_fetched, str(be), sample_id)
                    )
                    con.commit()
                raise be

            if term_status:
                with sqlite3.connect(str(self.db_path)) as con:
                    con.execute(
                        "UPDATE deep_backfill_jobs SET status = ?, last_error = ?, completed_at = ? WHERE sample_id = ?",
                        (term_status, err, datetime.now(timezone.utc).isoformat(), sample_id)
                    )
                    con.execute("DELETE FROM deep_staging_viewers WHERE sample_id = ?", (sample_id,))
                    con.commit()
                return term_status

            if err:
                with sqlite3.connect(str(self.db_path)) as con:
                    con.execute(
                        "UPDATE deep_backfill_jobs SET status = 'RETRYABLE', last_error = ?, next_page_token = ?, pages_fetched = ?, total_items_fetched = ? WHERE sample_id = ?",
                        (err, next_token, pages_fetched, total_items_fetched, sample_id)
                    )
                    con.commit()
                return "RETRYABLE"

            pages_fetched += 1
            total_items_fetched += len(items)

            # Process items with immediate HMAC pseudonymization
            for it in items:
                snip = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                cid = snip.get("authorChannelId", {}).get("value")
                pub_raw = snip.get("publishedAt")

                if cid and str(cid).startswith("UC"):
                    # IMMEDIATE HMAC pseudonymization - raw ID dropped immediately
                    v_hash = self.hasher.hash_viewer_id(str(cid))
                    inter_iso = parse_iso_dt(pub_raw)
                    ts_quality = "exact" if inter_iso is not None else "missing"

                    if v_hash not in viewer_map:
                        viewer_map[v_hash] = {
                            "viewer_hash": v_hash,
                            "channel_id": channel_id,
                            "video_id": video_id,
                            "video_published_at": pub_at,
                            "earliest_interaction": inter_iso,
                            "latest_interaction": inter_iso,
                            "appearances": 1,
                            "timestamp_quality": ts_quality
                        }
                    else:
                        rec = viewer_map[v_hash]
                        rec["appearances"] += 1
                        if inter_iso:
                            if rec["earliest_interaction"] is None or inter_iso < rec["earliest_interaction"]:
                                rec["earliest_interaction"] = inter_iso
                            if rec["latest_interaction"] is None or inter_iso > rec["latest_interaction"]:
                                rec["latest_interaction"] = inter_iso
                            rec["timestamp_quality"] = "exact"

            # Checkpoint intermediate page to SQLite staging
            with sqlite3.connect(str(self.db_path)) as con:
                staged_rows = [
                    (
                        sample_id,
                        r["viewer_hash"],
                        channel_id,
                        video_id,
                        pub_at,
                        r["earliest_interaction"],
                        r["latest_interaction"],
                        r["appearances"],
                        r["timestamp_quality"]
                    )
                    for r in viewer_map.values()
                ]
                con.executemany("""
                    INSERT INTO deep_staging_viewers (
                        sample_id, viewer_hash, channel_id, video_id, video_published_at,
                        earliest_interaction, latest_interaction, appearances, timestamp_quality
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sample_id, viewer_hash) DO UPDATE SET
                        earliest_interaction = excluded.earliest_interaction,
                        latest_interaction = excluded.latest_interaction,
                        appearances = excluded.appearances,
                        timestamp_quality = excluded.timestamp_quality
                """, staged_rows)
                con.execute(
                    "UPDATE deep_backfill_jobs SET next_page_token = ?, pages_fetched = ?, total_items_fetched = ? WHERE sample_id = ?",
                    (new_next_token, pages_fetched, total_items_fetched, sample_id)
                )
                con.commit()

            next_token = new_next_token
            if not next_token:
                # Pagination completely exhausted!
                break

        # Finished all pages for this video
        completed_at = datetime.now(timezone.utc).isoformat()

        if not viewer_map and total_items_fetched == 0:
            with sqlite3.connect(str(self.db_path)) as con:
                con.execute(
                    "UPDATE deep_backfill_jobs SET status = 'NO_COMMENTS', capture_status = 'NO_COMMENTS', completed_at = ?, pages_fetched = ?, total_items_fetched = 0 WHERE sample_id = ?",
                    (completed_at, pages_fetched, sample_id)
                )
                con.execute("DELETE FROM deep_staging_viewers WHERE sample_id = ?", (sample_id,))
                con.commit()
            return "NO_COMMENTS"

        # Build final Parquet observations
        out_rows = []
        oldest_ts: Optional[str] = None
        newest_ts: Optional[str] = None

        for rec in viewer_map.values():
            e_ts = rec["earliest_interaction"]
            l_ts = rec["latest_interaction"]
            if e_ts:
                if oldest_ts is None or e_ts < oldest_ts:
                    oldest_ts = e_ts
            if l_ts:
                if newest_ts is None or l_ts > newest_ts:
                    newest_ts = l_ts

            out_rows.append({
                "viewer_hash": rec["viewer_hash"],
                "vtuber_channel_id": channel_id,
                "video_id": video_id,
                "source_type": "comment",
                "video_published_at": pub_at,
                "interaction_at": e_ts,
                "latest_interaction_at": l_ts,
                "appearances": rec["appearances"],
                "timestamp_quality": rec["timestamp_quality"],
                "collected_at": completed_at,
                "sampling_manifest_version": "1.0",
                "sample_id": sample_id,
                "capture_status": "DEEP_COMPLETE",
                "backend": "youtube_api_v3",
                "pages_fetched": pages_fetched,
                "deep_backfill_version": "1.0",
            })

        out_file = self.observations_dir / "comment" / channel_id / f"{video_id}.parquet"
        out_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            tbl = pa.Table.from_pylist(out_rows, schema=DEEP_OBSERVATION_SCHEMA)
            tmp_p = out_file.parent / f"{out_file.name}.tmp.{int(time.time()*1000)}"
            pq.write_table(tbl, tmp_p, compression="snappy")
            _atomic_replace_with_retry(tmp_p, out_file)
        except Exception as e:
            logger.error(f"Failed writing deep parquet for {video_id}: {e}")
            with sqlite3.connect(str(self.db_path)) as con:
                con.execute(
                    "UPDATE deep_backfill_jobs SET status = 'FAILED', last_error = ? WHERE sample_id = ?",
                    (f"Parquet write error: {str(e)}", sample_id)
                )
                con.commit()
            return "FAILED"

        # Mark COMPLETED and clean up staging
        with sqlite3.connect(str(self.db_path)) as con:
            con.execute("""
                UPDATE deep_backfill_jobs SET
                    status = 'COMPLETED',
                    capture_status = 'DEEP_COMPLETE',
                    next_page_token = NULL,
                    pages_fetched = ?,
                    total_items_fetched = ?,
                    capture_count = ?,
                    oldest_interaction = ?,
                    newest_interaction = ?,
                    completed_at = ?,
                    output_file = ?,
                    last_error = NULL
                WHERE sample_id = ?
            """, (
                pages_fetched,
                total_items_fetched,
                len(out_rows),
                oldest_ts,
                newest_ts,
                completed_at,
                str(out_file),
                sample_id
            ))
            con.execute("DELETE FROM deep_staging_viewers WHERE sample_id = ?", (sample_id,))
            con.commit()

        logger.info(
            f"Deepened video {video_id} ({channel_id}): {pages_fetched} pages, "
            f"{total_items_fetched} comments, {len(out_rows)} unique viewers. Oldest: {oldest_ts}"
        )
        return "COMPLETED"

    def run_batch(self, limit: Optional[int] = None) -> Dict[str, int]:
        """Runs a bounded batch of pending or retryable deep backfill jobs."""
        with sqlite3.connect(str(self.db_path)) as con:
            con.row_factory = sqlite3.Row
            query = """
                SELECT * FROM deep_backfill_jobs
                WHERE status IN ('PENDING', 'RETRYABLE')
                ORDER BY year ASC, channel_id ASC, sample_id ASC
            """
            if limit:
                query += f" LIMIT {int(limit)}"
            jobs = [dict(r) for r in con.execute(query).fetchall()]

        logger.info(f"Loaded {len(jobs)} pending/retryable deep jobs for execution (budget={self.quota_budget}).")
        counts: Dict[str, int] = {
            "COMPLETED": 0,
            "NO_COMMENTS": 0,
            "COMMENTS_DISABLED": 0,
            "VIDEO_UNAVAILABLE": 0,
            "FAILED": 0,
            "RETRYABLE": 0,
            "PENDING": 0
        }

        for j in jobs:
            try:
                st = self.process_deep_job(j)
                counts[st] = counts.get(st, 0) + 1
            except BudgetExhaustedException as be:
                logger.warning(f"Batch halted due to quota exhaustion: {be}")
                break
            except Exception as e:
                logger.error(f"Unexpected error on job {j['sample_id']}: {e}", exc_info=True)
                counts["FAILED"] = counts.get("FAILED", 0) + 1
                with sqlite3.connect(str(self.db_path)) as con:
                    con.execute(
                        "UPDATE deep_backfill_jobs SET status = 'FAILED', last_error = ? WHERE sample_id = ?",
                        (str(e), j["sample_id"])
                    )
                    con.commit()

        return counts
