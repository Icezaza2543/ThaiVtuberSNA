"""
Historical Video Catalog Builder (Temporal Foundation 2020 ➔ Present)
Specialized collector for Phase T1:
- Uses YouTube Data API v3 playlistItems.list with part=snippet,contentDetails (max 50/page).
- Strictly 1 quota unit per request; 0 calls to videos.list.
- Paginates up to max_videos_per_channel (default 1,000) or cutoff date (default 2020-01-01T00:00:00Z).
- Atomic page-level checkpointing: flushes data page to parquet before updating next_page_token.
- Output isolated in data/temporal/catalog/.
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set

import requests
import pyarrow as pa
import pyarrow.parquet as pq

from config.settings import DATA_DIR, YOUTUBE_API_KEY

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HistoricalCatalogBuilder")

DEFAULT_CUTOFF_DATE = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
SCHEMA_VERSION = "2.0"

# PyArrow Schemas
VIDEO_CATALOG_SCHEMA = pa.schema([
    ("channel_id", pa.string()),
    ("video_id", pa.string()),
    ("video_published_at", pa.timestamp("us", tz="UTC")),
    ("playlist_added_at", pa.timestamp("us", tz="UTC")),
    ("timestamp_quality", pa.string()),  # 'exact' | 'missing'
    ("fetched_at", pa.timestamp("us", tz="UTC")),
    ("page_index", pa.int32()),
    ("source", pa.string()),             # 'youtube_api_v3'
    ("schema_version", pa.string())
])

CHANNEL_COVERAGE_SCHEMA = pa.schema([
    ("channel_id", pa.string()),
    ("target_reason", pa.string()),
    ("videos_collected", pa.int32()),
    ("oldest_video_published_at", pa.timestamp("us", tz="UTC")),
    ("newest_video_published_at", pa.timestamp("us", tz="UTC")),
    ("termination_reason", pa.string()),  # CUTOFF_REACHED | PLAYLIST_EXHAUSTED | CAP_REACHED | PARTIAL_ERROR | NO_VIDEOS
    ("next_page_token", pa.string()),
    ("api_calls", pa.int32()),
    ("hit_cap", pa.bool_()),
    ("coverage_complete_from", pa.timestamp("us", tz="UTC")),
    ("status", pa.string()),              # completed | in_progress | failed
    ("last_error", pa.string())
])


class HistoricalCatalogBuilder:
    def __init__(
        self,
        output_dir: Optional[Path] = None,
        max_videos_per_channel: int = 1000,
        cutoff_date: datetime = DEFAULT_CUTOFF_DATE,
        api_key: Optional[str] = None,
        session: Optional[requests.Session] = None
    ):
        self.output_dir = output_dir or (DATA_DIR / "temporal" / "catalog")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_videos_per_channel = max_videos_per_channel
        self.cutoff_date = cutoff_date
        self.api_key = api_key or YOUTUBE_API_KEY
        self.session = session or requests.Session()

        self.video_catalog_path = self.output_dir / "video_catalog.parquet"
        self.channel_coverage_path = self.output_dir / "channel_coverage.parquet"
        self.checkpoint_path = self.output_dir / "checkpoint.json"

        # In-memory tracking & checkpoint initialization
        self.checkpoint = self._load_checkpoint()
        self.seen_video_ids: Set[str] = self._load_existing_video_ids()

    def _load_checkpoint(self) -> Dict[str, Any]:
        if self.checkpoint_path.exists():
            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint file, re-initializing: {e}")
        return {"completed_channels": [], "in_progress_channels": {}}

    def _save_checkpoint_atomic(self):
        tmp_file = self.checkpoint_path.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(self.checkpoint, f, indent=2)
        tmp_file.replace(self.checkpoint_path)

    def _load_existing_video_ids(self) -> Set[str]:
        seen = set()
        if self.video_catalog_path.exists():
            try:
                tbl = pq.read_table(self.video_catalog_path, columns=["video_id"])
                for vid in tbl["video_id"].to_pylist():
                    if vid:
                        seen.add(vid)
            except Exception as e:
                logger.warning(f"Failed reading existing catalog: {e}")
        return seen

    @staticmethod
    def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            # Handle ISO formats like 2024-05-11T01:02:42Z
            clean_str = dt_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    def _append_video_records_atomic(self, records: List[Dict[str, Any]]):
        """Atomically appends records to video_catalog.parquet."""
        if not records:
            return

        new_table = pa.Table.from_pylist(records, schema=VIDEO_CATALOG_SCHEMA)
        if self.video_catalog_path.exists():
            existing_table = pq.read_table(self.video_catalog_path)
            combined_table = pa.concat_tables([existing_table, new_table])
        else:
            combined_table = new_table

        tmp_file = self.video_catalog_path.with_suffix(".tmp")
        pq.write_table(combined_table, tmp_file, compression="snappy")
        tmp_file.replace(self.video_catalog_path)

        for r in records:
            self.seen_video_ids.add(r["video_id"])

    def _upsert_channel_coverage_atomic(self, coverage_record: Dict[str, Any]):
        """Upserts a channel coverage record in channel_coverage.parquet."""
        cid = coverage_record["channel_id"]
        records = [coverage_record]

        if self.channel_coverage_path.exists():
            try:
                existing_table = pq.read_table(self.channel_coverage_path)
                existing_records = [
                    r for r in existing_table.to_pylist() if r["channel_id"] != cid
                ]
                records = existing_records + records
            except Exception as e:
                logger.warning(f"Error reading existing channel coverage: {e}")

        new_table = pa.Table.from_pylist(records, schema=CHANNEL_COVERAGE_SCHEMA)
        tmp_file = self.channel_coverage_path.with_suffix(".tmp")
        pq.write_table(new_table, tmp_file, compression="snappy")
        tmp_file.replace(self.channel_coverage_path)

    def fetch_page_api(self, playlist_id: str, page_token: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Optional[str], int]:
        """
        Fetches 1 page from playlistItems endpoint (max 50 results).
        Strictly requests part=snippet,contentDetails and fields to minimize payload.
        Returns: (items, next_page_token, http_status)
        """
        url = "https://www.googleapis.com/youtube/v3/playlistItems"
        params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
            "key": self.api_key
        }
        if page_token:
            params["pageToken"] = page_token

        resp = self.session.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            next_token = data.get("nextPageToken")
            return items, next_token, 200
        else:
            return [], None, resp.status_code

    def crawl_channel(self, channel_id: str, target_reason: str = "cohort_manifest") -> Dict[str, Any]:
        """
        Crawls up to max_videos_per_channel videos for a single channel.
        Stops when:
        1. videoPublishedAt < cutoff_date (CUTOFF_REACHED)
        2. videos_collected >= max_videos_per_channel (CAP_REACHED)
        3. nextPageToken is empty (PLAYLIST_EXHAUSTED)
        """
        if channel_id in self.checkpoint.get("completed_channels", []):
            logger.info(f"[{channel_id}] Already marked completed in checkpoint. Skipping.")
            return {"channel_id": channel_id, "status": "completed", "skipped": True}

        uploads_playlist_id = "UU" + channel_id[2:] if channel_id.startswith("UC") else ""
        if not uploads_playlist_id:
            logger.warning(f"[{channel_id}] Invalid channel ID format. Cannot construct uploads playlist.")
            cov = {
                "channel_id": channel_id,
                "target_reason": target_reason,
                "videos_collected": 0,
                "oldest_video_published_at": None,
                "newest_video_published_at": None,
                "termination_reason": "NO_VIDEOS",
                "next_page_token": None,
                "api_calls": 0,
                "hit_cap": False,
                "coverage_complete_from": None,
                "status": "failed",
                "last_error": "Invalid channel ID prefix"
            }
            self._upsert_channel_coverage_atomic(cov)
            return cov

        # Resume state
        state = self.checkpoint.get("in_progress_channels", {}).get(channel_id, {})
        next_page_token = state.get("next_page_token")
        page_index = state.get("page_index", 0)
        videos_collected = state.get("videos_collected", 0)
        api_calls = state.get("api_calls", 0)
        oldest_pub_dt: Optional[datetime] = self.parse_iso_datetime(state.get("oldest_video_date"))
        newest_pub_dt: Optional[datetime] = self.parse_iso_datetime(state.get("newest_video_date"))

        termination_reason = "PLAYLIST_EXHAUSTED"
        last_error = None
        status = "in_progress"

        logger.info(f"[{channel_id}] Starting historical crawl (Resuming at page {page_index}, {videos_collected} vids so far)...")

        while True:
            # Check cap before fetching
            if videos_collected >= self.max_videos_per_channel:
                termination_reason = "CAP_REACHED"
                status = "completed"
                break

            items, next_token, status_code = self.fetch_page_api(uploads_playlist_id, next_page_token)
            api_calls += 1

            if status_code == 404:
                logger.info(f"[{channel_id}] Uploads playlist not found (0 uploads).")
                termination_reason = "NO_VIDEOS"
                status = "completed"
                break
            elif status_code == 403:
                logger.error(f"[{channel_id}] YouTube API Quota Exceeded (403). Pausing channel crawl.")
                status = "failed"
                last_error = "YouTube API Quota Exceeded (403)"
                termination_reason = "PARTIAL_ERROR"
                break
            elif status_code != 200:
                logger.warning(f"[{channel_id}] HTTP error {status_code}. Pausing channel crawl.")
                status = "failed"
                last_error = f"HTTP {status_code}"
                termination_reason = "PARTIAL_ERROR"
                break

            if not items:
                termination_reason = "PLAYLIST_EXHAUSTED"
                status = "completed"
                break

            page_records = []
            hit_cutoff_in_page = False
            now_utc = datetime.now(timezone.utc)

            for item in items:
                content = item.get("contentDetails", {})
                snippet = item.get("snippet", {})
                vid = content.get("videoId") or snippet.get("resourceId", {}).get("videoId")

                if not vid:
                    continue
                if vid in self.seen_video_ids:
                    continue

                raw_pub = content.get("videoPublishedAt")
                pub_dt = self.parse_iso_datetime(raw_pub)
                timestamp_quality = "exact" if pub_dt else "missing"

                raw_added = snippet.get("publishedAt")
                added_dt = self.parse_iso_datetime(raw_added)

                # Track oldest & newest
                if pub_dt:
                    if oldest_pub_dt is None or pub_dt < oldest_pub_dt:
                        oldest_pub_dt = pub_dt
                    if newest_pub_dt is None or pub_dt > newest_pub_dt:
                        newest_pub_dt = pub_dt

                    # Cutoff boundary check
                    if pub_dt < self.cutoff_date:
                        hit_cutoff_in_page = True
                        # Do not collect videos older than cutoff
                        continue

                rec = {
                    "channel_id": channel_id,
                    "video_id": vid,
                    "video_published_at": pub_dt,
                    "playlist_added_at": added_dt,
                    "timestamp_quality": timestamp_quality,
                    "fetched_at": now_utc,
                    "page_index": page_index,
                    "source": "youtube_api_v3",
                    "schema_version": SCHEMA_VERSION
                }
                page_records.append(rec)
                videos_collected += 1

                if videos_collected >= self.max_videos_per_channel:
                    break

            # 1. Atomically persist page data
            if page_records:
                self._append_video_records_atomic(page_records)

            page_index += 1
            next_page_token = next_token

            # 2. Atomically update checkpoint to advance page
            if hit_cutoff_in_page:
                termination_reason = "CUTOFF_REACHED"
                status = "completed"
                break

            if videos_collected >= self.max_videos_per_channel:
                termination_reason = "CAP_REACHED"
                status = "completed"
                break

            if not next_page_token:
                termination_reason = "PLAYLIST_EXHAUSTED"
                status = "completed"
                break

            # Update in-progress checkpoint
            self.checkpoint.setdefault("in_progress_channels", {})[channel_id] = {
                "next_page_token": next_page_token,
                "page_index": page_index,
                "videos_collected": videos_collected,
                "oldest_video_date": oldest_pub_dt.isoformat() if oldest_pub_dt else None,
                "newest_video_date": newest_pub_dt.isoformat() if newest_pub_dt else None,
                "api_calls": api_calls
            }
            self._save_checkpoint_atomic()

        # Finalize channel status
        if status == "completed":
            if channel_id not in self.checkpoint.get("completed_channels", []):
                self.checkpoint.setdefault("completed_channels", []).append(channel_id)
            self.checkpoint.get("in_progress_channels", {}).pop(channel_id, None)
            self._save_checkpoint_atomic()

        # Calculate coverage_complete_from
        coverage_from = None
        if termination_reason == "CUTOFF_REACHED":
            coverage_from = self.cutoff_date
        elif termination_reason == "PLAYLIST_EXHAUSTED":
            coverage_from = oldest_pub_dt or self.cutoff_date

        cov_record = {
            "channel_id": channel_id,
            "target_reason": target_reason,
            "videos_collected": videos_collected,
            "oldest_video_published_at": oldest_pub_dt,
            "newest_video_published_at": newest_pub_dt,
            "termination_reason": termination_reason,
            "next_page_token": next_page_token,
            "api_calls": api_calls,
            "hit_cap": (videos_collected >= self.max_videos_per_channel),
            "coverage_complete_from": coverage_from,
            "status": status,
            "last_error": last_error
        }
        self._upsert_channel_coverage_atomic(cov_record)
        logger.info(f"[{channel_id}] Finished: {videos_collected} videos collected ({termination_reason}, {api_calls} API calls).")
        return cov_record
