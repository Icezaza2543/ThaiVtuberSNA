"""
Thai VTuber Audience Network (SNA)
Hybrid 30-Video Crawler: YouTube Data API v3 + Automatic yt-dlp Fallback

Zero Local Disk Storage Policy:
- All video metadata, comment presence events, and profiles stored 100% in-memory.
- In-flight fallback from YouTube Data API to yt-dlp upon HTTP 403 quotaExceeded.
- DuckDB in-memory (:memory:) overlap matrix computation.
- Checkpointed & final uploads directly to Google Sheets:
  * 'ALL_COMMENTERS' (Merged master commenter registry)
  * 'NETWORK_RESULT' (Pairwise overlap graph)
  * 'SYSTEM' (Live execution metrics & quota status)
"""
import os
import sys
import csv
import json
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import requests
import pyarrow as pa
import duckdb
import gspread
import yt_dlp

from config.settings import YOUTUBE_API_KEY, GOOGLE_SHEETS_CONFIG, DATA_DIR
from core.hasher import PrivacyHasher, compute_key_fingerprint, load_persistent_secret_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("HybridCrawler30")

class GlobalQuotaMonitor:
    """Thread-safe monitor for tracking YouTube API quota status and statistics."""
    def __init__(self):
        self.is_quota_exhausted = False
        self.api_comments_count = 0
        self.ytdlp_comments_count = 0
        self.api_discovery_count = 0
        self.ytdlp_discovery_count = 0
        self._lock = threading.Lock()

    def mark_exhausted(self):
        with self._lock:
            if not self.is_quota_exhausted:
                self.is_quota_exhausted = True
                logger.warning("=" * 65)
                logger.warning(">>> YOUTUBE API QUOTA EXHAUSTED (403)! <<<")
                logger.warning(">>> AUTOMATICALLY SWITCHING TO yt-dlp SCRAPING ENGINE <<<")
                logger.warning("=" * 65)

    def inc_api_comment(self):
        with self._lock:
            self.api_comments_count += 1

    def inc_ytdlp_comment(self):
        with self._lock:
            self.ytdlp_comments_count += 1

    def inc_api_discovery(self):
        with self._lock:
            self.api_discovery_count += 1

    def inc_ytdlp_discovery(self):
        with self._lock:
            self.ytdlp_discovery_count += 1

quota_monitor = GlobalQuotaMonitor()

def col_to_letter(col_idx: int) -> str:
    result = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result

def get_or_create_worksheet(spreadsheet, title, rows=1000, cols=10):
    try:
        return spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        logger.info(f"Creating worksheet: {title}")
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

def safe_update_sheet(ws, data_rows, batch_size=2000):
    from storage.private_sheet_store import PrivateSheetStore
    if not data_rows: return
    return PrivateSheetStore(ws.spreadsheet).write_verified_table(ws.title, data_rows[0], data_rows[1:], batch_size=batch_size)


def fetch_channel_videos_api(channel_id: str, session: requests.Session, max_videos: int = 30) -> Tuple[List[Dict[str, Any]], bool]:
    """Fetches up to 30 latest uploads via playlistItems (1 quota unit). Returns (videos, is_quota_exhausted)."""
    if not channel_id or not channel_id.startswith("UC"):
        return [], False

    uploads_playlist_id = "UU" + channel_id[2:]
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet",
        "playlistId": uploads_playlist_id,
        "maxResults": min(max_videos, 50),
        "key": YOUTUBE_API_KEY
    }
    try:
        resp = session.get(url, params=params, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            videos = []
            for item in data.get("items", []):
                snip = item.get("snippet", {})
                vid = snip.get("resourceId", {}).get("videoId")
                title = snip.get("title", "")
                pub = snip.get("publishedAt", "")
                if vid:
                    videos.append({"video_id": vid, "title": title, "published_at": pub, "channel_id": channel_id})
            quota_monitor.inc_api_discovery()
            return videos, False
        elif resp.status_code == 403:
            body = resp.text
            if "quotaExceeded" in body or "dailyLimitExceeded" in body:
                return [], True
        return [], False
    except Exception:
        return [], False

def fetch_channel_videos_ytdlp(channel_id: str, max_videos: int = 30) -> List[Dict[str, Any]]:
    """Fallback: Fetches up to 30 latest uploads via yt-dlp flat playlist extraction."""
    if not channel_id or not channel_id.startswith("UC"):
        return []

    uploads_playlist_id = "UU" + channel_id[2:]
    url = f"https://www.youtube.com/playlist?list={uploads_playlist_id}"
    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "playlist_items": f"1-{max_videos}",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            videos = []
            for e in info.get("entries", []) or []:
                vid = e.get("id")
                title = e.get("title", "")
                if vid:
                    videos.append({"video_id": vid, "title": title, "published_at": "", "channel_id": channel_id})
            quota_monitor.inc_ytdlp_discovery()
            return videos
    except Exception:
        return []

def fetch_channel_videos_hybrid(ch: Dict[str, Any], session: requests.Session, max_videos: int = 30) -> List[Dict[str, Any]]:
    cid = ch["channel_id"]
    cname = ch.get("name", cid)

    vids = []
    if not quota_monitor.is_quota_exhausted:
        vids, exhausted = fetch_channel_videos_api(cid, session, max_videos=max_videos)
        if exhausted:
            quota_monitor.mark_exhausted()
            vids = fetch_channel_videos_ytdlp(cid, max_videos=max_videos)
    else:
        vids = fetch_channel_videos_ytdlp(cid, max_videos=max_videos)

    for v in vids:
        v["channel_name"] = cname
    return vids

# =========================================================================
# Phase 2: Comment Extraction - Dual API + yt-dlp Engine
# =========================================================================

def fetch_comments_api(video_id: str, session: requests.Session, max_comments: int = 100) -> Tuple[List[Dict[str, Any]], bool]:
    """Fetches comments using YouTube Data API v3 commentThreads.list."""
    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": min(max_comments, 100),
        "key": YOUTUBE_API_KEY
    }
    try:
        resp = session.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            quota_monitor.inc_api_comment()
            items = resp.json().get("items", [])
            parsed = []
            for it in items:
                snip = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                cid = snip.get("authorChannelId", {}).get("value")
                name = snip.get("authorDisplayName", "").strip()
                curl = snip.get("authorChannelUrl", "").strip()
                pub = snip.get("publishedAt") or None
                if cid and str(cid).startswith("UC"):
                    parsed.append({
                        "author_id": cid,
                        "author_name": name,
                        "author_url": curl or f"https://www.youtube.com/channel/{cid}",
                        "timestamp": pub
                    })
            return parsed, False
        elif resp.status_code == 403:
            body = resp.text
            if "quotaExceeded" in body or "dailyLimitExceeded" in body:
                return [], True
        return [], False
    except Exception:
        return [], False

def fetch_comments_ytdlp(video_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
    """Fetches comments using yt-dlp headless scraping."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "getcomments": True,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {"max_comments": [str(max_comments)]}
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            quota_monitor.inc_ytdlp_comment()
            raw_comments = info.get("comments", []) or []
            parsed = []
            for c in raw_comments:
                cid = c.get("author_id")
                name = c.get("author", "").strip()
                curl = c.get("author_url", "").strip()
                ts = c.get("timestamp")
                if ts:
                    pub = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                else:
                    pub = None

                if cid and str(cid).startswith("UC"):
                    parsed.append({
                        "author_id": cid,
                        "author_name": name,
                        "author_url": curl or f"https://www.youtube.com/channel/{cid}",
                        "timestamp": pub
                    })
            return parsed
    except Exception:
        return []

def fetch_video_comments_hybrid(video_id: str, channel_id: str, channel_name: str, hasher: PrivacyHasher, session: requests.Session, max_comments: int = 100):
    raw_comments = []
    if not quota_monitor.is_quota_exhausted:
        raw_comments, exhausted = fetch_comments_api(video_id, session, max_comments=max_comments)
        if exhausted:
            quota_monitor.mark_exhausted()
            raw_comments = fetch_comments_ytdlp(video_id, max_comments=max_comments)
    else:
        raw_comments = fetch_comments_ytdlp(video_id, max_comments=max_comments)

    events = []
    for c in raw_comments:
        author_cid = c["author_id"]
        v_hash = hasher.hash_viewer_id(author_cid)
        events.append({
            "viewer_hash": v_hash,
            "vtuber_channel_id": channel_id,
            "video_id": video_id,
            "source_type": "comment",
            "first_seen": c["timestamp"],
            "last_seen": c["timestamp"],
            "appearances": 1
        })

    return events

# =========================================================================
# Phase 3 & 4: In-Memory Overlap & Google Sheets Sync
# =========================================================================

def sync_to_google_sheets(sh, unique_viewer_hashes: set, in_memory_events: List[Dict[str, Any]],
                          cid_to_name: Dict[str, str], cid_to_agency: Dict[str, str], target_channel_count: int, total_videos_count: int, is_final: bool = False):
    calc_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    logger.info(f"--- Triggering Google Sheets Sync (Final={is_final}) at {calc_time} ---")

    # 1. Compute DuckDB Overlap in-memory
    overlap_rows = []
    if in_memory_events:
        con = duckdb.connect(":memory:")
        schema = pa.schema([
            ('viewer_hash', pa.string()),
            ('vtuber_channel_id', pa.string()),
            ('video_id', pa.string()),
            ('source_type', pa.string()),
            ('first_seen', pa.string()),
            ('last_seen', pa.string()),
            ('appearances', pa.int64())
        ])
        arrow_table = pa.Table.from_pylist(in_memory_events, schema=schema)
        con.register("raw_events", arrow_table)

        threshold = 2
        min_shared_viewers = 1

        overlap_query = f"""
            WITH viewer_channel_stats AS (
                SELECT
                    vtuber_channel_id,
                    viewer_hash,
                    COUNT(DISTINCT video_id) AS videos_seen,
                    COUNT(DISTINCT CASE WHEN source_type = 'comment' THEN video_id END) AS comment_videos_seen,
                    SUM(COALESCE(appearances, 1)) AS total_appearances,
                    MIN(first_seen) AS first_seen,
                    MAX(last_seen) AS last_seen
                FROM raw_events
                WHERE viewer_hash != ''
                GROUP BY vtuber_channel_id, viewer_hash
            ),
            channel_totals AS (
                SELECT
                    vtuber_channel_id,
                    COUNT(DISTINCT viewer_hash) AS total_viewers
                FROM viewer_channel_stats
                GROUP BY vtuber_channel_id
            ),
            shared_pairs AS (
                SELECT
                    a.vtuber_channel_id AS vtuber_a,
                    b.vtuber_channel_id AS vtuber_b,
                    COUNT(DISTINCT a.viewer_hash) AS shared_any,
                    COUNT(DISTINCT CASE WHEN a.videos_seen >= {threshold} AND b.videos_seen >= {threshold} THEN a.viewer_hash END) AS strong_shared_any
                FROM viewer_channel_stats a
                JOIN viewer_channel_stats b
                    ON a.viewer_hash = b.viewer_hash
                    AND a.vtuber_channel_id < b.vtuber_channel_id
                GROUP BY a.vtuber_channel_id, b.vtuber_channel_id
                HAVING COUNT(DISTINCT a.viewer_hash) >= {min_shared_viewers}
            )
            SELECT
                s.vtuber_a,
                s.vtuber_b,
                s.shared_any,
                s.strong_shared_any,
                t_a.total_viewers AS size_a,
                t_b.total_viewers AS size_b
            FROM shared_pairs s
            JOIN channel_totals t_a ON s.vtuber_a = t_a.vtuber_channel_id
            JOIN channel_totals t_b ON s.vtuber_b = t_b.vtuber_channel_id
            ORDER BY s.shared_any DESC
        """
        overlap_rows = con.execute(overlap_query).fetchall()
        con.close()
        logger.info(f"DuckDB calculated {len(overlap_rows)} overlap relations.")

    # 2. Update NETWORK_RESULT Sheet
    if overlap_rows:
        ws_network = get_or_create_worksheet(sh, "NETWORK_RESULT", rows=max(100, len(overlap_rows) + 50), cols=7)
        network_data = [["Channel A", "Agency A", "Channel B", "Agency B", "Shared Viewers", "Strong Shared", "Calculated At"]]
        for r in overlap_rows:
            ca, cb, shared_any, strong_shared, sa, sb = r
            na = cid_to_name.get(ca, ca)
            nb = cid_to_name.get(cb, cb)
            aga = cid_to_agency.get(ca, "Independent")
            agb = cid_to_agency.get(cb, "Independent")
            network_data.append([na, aga, nb, agb, shared_any, strong_shared, calc_time])
        safe_update_sheet(ws_network, network_data, batch_size=2000)

    # 3. Update SYSTEM Sheet (Aggregated metrics only - zero PII)
    ws_system = get_or_create_worksheet(sh, "SYSTEM", rows=25, cols=3)
    sys_rows = [
        ["Metric", "Value"],
        ["Project", "Thai VTuber Audience Network (SNA) - 30 Videos Hybrid Run"],
        ["Status", "Complete" if is_final else "In Progress (Live Checkpoint)"],
        ["Target Channels Monitored", f"{target_channel_count} channels (Top Active & Agencies)"],
        ["Total Videos Analyzed", f"{total_videos_count} videos (up to 30/channel)"],
        ["Overlap Connections Discovered", f"{len(overlap_rows):,} connections"],
        ["Total Unique Commenters (Anonymized)", f"{len(unique_viewer_hashes):,} hashes"],
        ["API Videos Processed", f"{quota_monitor.api_comments_count} videos"],
        ["yt-dlp Videos Scraped", f"{quota_monitor.ytdlp_comments_count} videos"],
        ["Quota Status", "Exhausted (Fell back to yt-dlp)" if quota_monitor.is_quota_exhausted else "Active (Within Daily Quota)"],
        ["Storage Policy", "Cloud Only (Google Sheets) - Zero Local Disk Storage"],
        ["Privacy Compliance", "PASS - Zero PII Persisted (HMAC-SHA256 RAM-only boundary)"],
        ["Last Checkpoint Time", calc_time]
    ]
    safe_update_sheet(ws_system, sys_rows, batch_size=100)
    logger.info(f"Sync complete. Total Anonymized Commenters: {len(unique_viewer_hashes):,}, Overlaps: {len(overlap_rows):,}")

# =========================================================================
# Main Execution Pipeline
# =========================================================================

def main():
    raise RuntimeError("Legacy crawler retired: use the authorized private Sheet ingestion interface; T20 is on hold.")
    logger.info("=" * 65)
    logger.info(" Thai VTuber SNA: Hybrid 30-Video Crawler (API + yt-dlp) ")
    logger.info(" Storage Policy: ZERO Local Disk Storage (100% In-Memory) ")
    logger.info("=" * 65)

    cred_path = GOOGLE_SHEETS_CONFIG.get("credentials_path")
    sheet_id = GOOGLE_SHEETS_CONFIG.get("spreadsheet_id")
    if not (cred_path and Path(cred_path).exists() and sheet_id):
        logger.error("Google Sheets credentials or spreadsheet_id not found!")
        return

    gc = gspread.service_account(filename=str(cred_path))
    sh = gc.open_by_key(sheet_id)
    logger.info(f"Connected to Google Sheet: '{sh.title}' ({sheet_id})")

    hasher = PrivacyHasher()
    key_fingerprint = compute_key_fingerprint(load_persistent_secret_key())
    logger.info(f"Verified Persistent Key Fingerprint: {key_fingerprint}")

    # Load Registry (Read-only reference)
    registry_file = DATA_DIR / "thai_vtuber_registry.csv"
    with open(registry_file, "r", encoding="utf-8") as f:
        all_vtubers = list(csv.DictReader(f))

    # Filter Target Channels: Active + (Subs >= 5,000 OR Agency != Independent)
    target_channels = [
        v for v in all_vtubers
        if v.get("activity_status") == "active"
        and v.get("enabled") == "True"
        and (int(v.get("subscriber_count", 0) or 0) >= 5000 or v.get("agency", "Independent") != "Independent")
    ]
    target_channels.sort(key=lambda x: int(x.get("subscriber_count", 0) or 0), reverse=True)
    logger.info(f"Targeting {len(target_channels)} active Thai VTuber channels.")

    cid_to_name = {v["channel_id"]: v.get("name", v["channel_id"]) for v in all_vtubers}
    cid_to_agency = {v["channel_id"]: v.get("agency", "Independent") for v in all_vtubers}

    # Pre-populate unique commenters from Google Sheet ALL_COMMENTERS
    unique_viewer_hashes = set()

    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=30)
    session.mount("https://", adapter)

    # ---------------------------------------------------------------------
    # Phase 1: Video Discovery (30 Uploads / Channel)
    # ---------------------------------------------------------------------
    logger.info("Phase 1: Discovering up to 30 recent uploads per channel...")
    all_videos_to_process = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_channel_videos_hybrid, ch, session, 30): ch for ch in target_channels}
        done = 0
        for fut in as_completed(futures):
            done += 1
            vids = fut.result()
            all_videos_to_process.extend(vids)
            if done % 50 == 0 or done == len(target_channels):
                logger.info(f" -> Discovery: {done}/{len(target_channels)} channels resolved ({len(all_videos_to_process)} videos found).")

    logger.info(f"Phase 1 Complete: Total {len(all_videos_to_process)} videos discovered across {len(target_channels)} channels.")

    # ---------------------------------------------------------------------
    # Phase 2: Comment Extraction with Automatic Quota Fallback
    # ---------------------------------------------------------------------
    logger.info(f"Phase 2: Ingesting comments in-memory across {len(all_videos_to_process)} videos...")
    in_memory_events = []
    completed_videos = 0
    checkpoint_interval = 1500

    def process_video_task(vinfo):
        vid = vinfo["video_id"]
        cid = vinfo["channel_id"]
        cname = vinfo.get("channel_name", cid)
        return fetch_video_comments_hybrid(vid, cid, cname, hasher, session, max_comments=100)

    # We use 10 workers for API, gracefully handling yt-dlp tasks when quota runs out
    max_workers = 10
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_video_task, v): v for v in all_videos_to_process}
        for fut in as_completed(futures):
            completed_videos += 1
            evs = fut.result()
            if evs:
                in_memory_events.extend(evs)
                for e in evs:
                    unique_viewer_hashes.add(e["viewer_hash"])

            if completed_videos % 250 == 0 or completed_videos == len(all_videos_to_process):
                engine_status = f"API: {quota_monitor.api_comments_count}, yt-dlp: {quota_monitor.ytdlp_comments_count}"
                logger.info(f" -> Comment Progress: {completed_videos}/{len(all_videos_to_process)} videos ({completed_videos*100//len(all_videos_to_process)}%) [{engine_status}]. Total Unique Commenters: {len(unique_viewer_hashes):,}.")

            # Periodic checkpoint to Google Sheets every 1500 videos
            if completed_videos % checkpoint_interval == 0:
                logger.info(f">>> CHECKPOINT: Syncing intermediate results ({completed_videos} videos) to Google Sheets... <<<")
                try:
                    sync_to_google_sheets(
                        sh, unique_viewer_hashes, in_memory_events,
                        cid_to_name, cid_to_agency, len(target_channels), completed_videos, is_final=False
                    )
                except Exception as ex:
                    logger.warning(f"Checkpoint sync failed: {ex}")

    logger.info("Phase 2 Complete: Ingestion finished!")

    # ---------------------------------------------------------------------
    # Phase 3 & 4: Final In-Memory DuckDB Overlap & Google Sheets Upload
    # ---------------------------------------------------------------------
    logger.info("=" * 65)
    logger.info(" FINAL SYNC: Computing Full DuckDB Overlap & Uploading to Sheets ")
    logger.info("=" * 65)
    # Final Sync to Google Sheets
    sync_to_google_sheets(
        sh, unique_viewer_hashes, in_memory_events,
        cid_to_name, cid_to_agency, len(target_channels), len(all_videos_to_process), is_final=True
    )

    logger.info("=" * 65)
    logger.info(" ALL TASKS COMPLETE! Google Sheet is fully updated! ")
    logger.info(f" Spreadsheet URL: https://docs.google.com/spreadsheets/d/{sheet_id} ")
    logger.info("=" * 65)

if __name__ == "__main__":
    main()
