"""
Thai VTuber Audience Network (SNA)
Batch Collection & Direct Google Sheets Sync (In-Memory / Zero Local Clutter)

Policy: All new data is streamed into Google Sheets directly. ZERO data files stored locally.
- In-memory video discovery (10 uploads per channel via UU playlist)
- In-memory comment collection & commenter profiling
- In-memory DuckDB overlap matrix computation
- Direct upload to Google Sheets:
  - 'NETWORK_RESULT': Overlap graph edges (Channel A, Channel B, Shared Viewers)
  - 'ALL_COMMENTERS': All discovered commenters (authorDisplayName, authorChannelUrl, comment_count, channels_active)
  - 'SYSTEM': Run metadata, timestamps, quota consumption
"""
import os
import sys
import csv
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Set
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import requests
import pyarrow as pa
import duckdb
import gspread

from config.settings import YOUTUBE_API_KEY, GOOGLE_SHEETS_CONFIG, DATA_DIR
from core.hasher import PrivacyHasher, compute_key_fingerprint, load_persistent_secret_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BatchNetwork")

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


def fetch_channel_recent_videos(channel_id: str, session: requests.Session, max_videos: int = 10) -> List[Dict[str, Any]]:
    """Fetches latest uploads for a channel using uploads playlist (UU... - 1 API unit)."""
    if not channel_id or not channel_id.startswith("UC"):
        return []

    uploads_playlist_id = "UU" + channel_id[2:]
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet",
        "playlistId": uploads_playlist_id,
        "maxResults": max_videos,
        "key": YOUTUBE_API_KEY
    }
    try:
        resp = session.get(url, params=params, timeout=12)
        if resp.status_code != 200:
            return []
        data = resp.json()
        videos = []
        for item in data.get("items", []):
            snip = item.get("snippet", {})
            vid = snip.get("resourceId", {}).get("videoId")
            title = snip.get("title", "")
            pub = snip.get("publishedAt", "")
            if vid:
                videos.append({
                    "video_id": vid,
                    "title": title,
                    "published_at": pub,
                    "channel_id": channel_id
                })
        return videos
    except Exception:
        return []

def fetch_video_comments_and_profiles(video_id: str, channel_id: str, channel_name: str, hasher: PrivacyHasher, session: requests.Session, max_comments: int = 100):
    """Fetches comments: returns privacy-hashed presence records + raw public profiles."""
    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": min(max_comments, 100),
        "key": YOUTUBE_API_KEY
    }
    try:
        resp = session.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return [], []
        data = resp.json()
        events = []
        profiles = []

        for item in data.get("items", []):
            top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            author_cid = top.get("authorChannelId", {}).get("value")
            author_name = top.get("authorDisplayName", "").strip()
            author_url = top.get("authorChannelUrl", "").strip()
            pub = top.get("publishedAt") or datetime.now(timezone.utc).isoformat()

            if not author_cid or not str(author_cid).startswith("UC"):
                continue

            if not author_url:
                author_url = f"https://www.youtube.com/channel/{author_cid}"

            v_hash = hasher.hash_viewer_id(author_cid)
            events.append({
                "viewer_hash": v_hash,
                "vtuber_channel_id": channel_id,
                "video_id": video_id,
                "source_type": "comment",
                "first_seen": pub,
                "last_seen": pub,
                "appearances": 1
            })

            profiles.append({
                "user_key": author_cid,
                "authorDisplayName": author_name,
                "authorChannelUrl": author_url,
                "vtuber_name": channel_name,
                "timestamp": pub
            })

        return events, profiles
    except Exception:
        return [], []

def main():
    raise RuntimeError("Legacy crawler retired: use the authorized private Sheet ingestion interface; T20 is on hold.")
    logger.info("==========================================================")
    logger.info(" Thai VTuber SNA: Batch Collection & Direct Sheet Sync   ")
    logger.info(" Storage Policy: ZERO Local Disk Storage (100% In-Memory) ")
    logger.info("==========================================================")

    if not YOUTUBE_API_KEY:
        logger.error("YOUTUBE_API_KEY is not configured!")
        return

    cred_path = GOOGLE_SHEETS_CONFIG.get("credentials_path")
    sheet_id = GOOGLE_SHEETS_CONFIG.get("spreadsheet_id")
    if not (cred_path and Path(cred_path).exists() and sheet_id):
        logger.error("Google Sheets credentials or spreadsheet_id not found!")
        return

    # Verify Google Sheets connection
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

    # Target Channels: Active + (Subs >= 5,000 OR Agency != Independent)
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

    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=25, pool_maxsize=25)
    session.mount("https://", adapter)

    # 1. Step: Fetch Latest 10 Videos per Channel
    logger.info("Phase 1: Discovering recent uploads for each channel...")
    all_videos_to_process = []
    
    def fetch_vids(ch):
        cid = ch["channel_id"]
        cname = ch.get("name", cid)
        vids = fetch_channel_recent_videos(cid, session, max_videos=10)
        for v in vids:
            v["channel_name"] = cname
        return vids

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_vids, ch): ch for ch in target_channels}
        done = 0
        for fut in as_completed(futures):
            done += 1
            vids = fut.result()
            all_videos_to_process.extend(vids)
            if done % 50 == 0 or done == len(target_channels):
                logger.info(f" -> Discovery: {done}/{len(target_channels)} channels resolved ({len(all_videos_to_process)} videos found).")

    logger.info(f"Phase 1 Complete: Discovered {len(all_videos_to_process)} videos across {len(target_channels)} channels.")

    # 2. Step: In-Memory Ingestion of Comments & Profiles
    logger.info(f"Phase 2: Ingesting comments in-memory across {len(all_videos_to_process)} videos...")
    in_memory_events = []
    unique_commenter_profiles: Dict[str, Dict[str, Any]] = {}
    completed_videos = 0

    def process_video_task(vinfo):
        vid = vinfo["video_id"]
        cid = vinfo["channel_id"]
        cname = vinfo.get("channel_name", cid)
        return fetch_video_comments_and_profiles(vid, cid, cname, hasher, session, max_comments=100)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_video_task, v): v for v in all_videos_to_process}
        for fut in as_completed(futures):
            completed_videos += 1
            evs, profs = fut.result()
            if evs:
                in_memory_events.extend(evs)
            for p in profs:
                ukey = p["user_key"]
                if ukey not in unique_commenter_profiles:
                    unique_commenter_profiles[ukey] = {
                        "authorDisplayName": p["authorDisplayName"],
                        "authorChannelUrl": p["authorChannelUrl"],
                        "vtubers": {p["vtuber_name"]},
                        "comment_count": 1,
                        "last_seen": p["timestamp"]
                    }
                else:
                    unique_commenter_profiles[ukey]["comment_count"] += 1
                    unique_commenter_profiles[ukey]["vtubers"].add(p["vtuber_name"])
                    if p["timestamp"] > unique_commenter_profiles[ukey]["last_seen"]:
                        unique_commenter_profiles[ukey]["last_seen"] = p["timestamp"]

            if completed_videos % 400 == 0 or completed_videos == len(all_videos_to_process):
                logger.info(f" -> Ingestion: {completed_videos}/{len(all_videos_to_process)} videos processed. Recorded {len(in_memory_events)} presence rows, {len(unique_commenter_profiles)} unique commenters.")

    logger.info(f"Phase 2 Complete: Collected {len(in_memory_events)} presence records and {len(unique_commenter_profiles)} unique commenters.")

    # 3. Step: DuckDB In-Memory Overlap Computation
    logger.info("==========================================================")
    logger.info(" Phase 3: DuckDB In-Memory Overlap Matrix Computation     ")
    logger.info("==========================================================")

    con = duckdb.connect(":memory:")

    # Convert in-memory events to PyArrow Table
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
                COUNT(DISTINCT CASE WHEN source_type = 'live_chat' THEN video_id END) AS live_streams_seen,
                COUNT(DISTINCT CASE WHEN source_type = 'comment' THEN video_id END) AS comment_videos_seen,
                SUM(COALESCE(appearances, 1)) AS total_appearances,
                BOOL_OR(source_type = 'live_chat') AS in_live_chat,
                BOOL_OR(source_type = 'comment') AS in_comment,
                MIN(first_seen) AS first_seen,
                MAX(last_seen) AS last_seen
            FROM raw_events
            WHERE viewer_hash != ''
            GROUP BY vtuber_channel_id, viewer_hash
        ),
        channel_totals AS (
            SELECT 
                vtuber_channel_id, 
                COUNT(DISTINCT viewer_hash) AS total_viewers,
                COUNT(DISTINCT CASE WHEN in_live_chat THEN viewer_hash END) AS live_chat_viewers,
                COUNT(DISTINCT CASE WHEN in_comment THEN viewer_hash END) AS comment_viewers
            FROM viewer_channel_stats
            GROUP BY vtuber_channel_id
        ),
        shared_pairs AS (
            SELECT 
                a.vtuber_channel_id AS vtuber_a,
                b.vtuber_channel_id AS vtuber_b,
                COUNT(DISTINCT a.viewer_hash) AS shared_any,
                COUNT(DISTINCT CASE WHEN a.in_live_chat AND b.in_live_chat THEN a.viewer_hash END) AS shared_live_chat,
                COUNT(DISTINCT CASE WHEN a.in_comment AND b.in_comment THEN a.viewer_hash END) AS shared_comments,
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
    logger.info(f"DuckDB computed {len(overlap_rows)} audience overlap connections across channels!")

    # 4. Step: Sync Everything Directly to Google Sheets
    logger.info("==========================================================")
    logger.info(" Phase 4: Syncing ALL Data to Google Sheets               ")
    logger.info(" (No files written to local disk)                         ")
    logger.info("==========================================================")
    calc_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 4A. Sync NETWORK_RESULT
    logger.info("Syncing NETWORK_RESULT sheet...")
    ws_network = get_or_create_worksheet(sh, "NETWORK_RESULT", rows=max(100, len(overlap_rows) + 20), cols=7)
    network_sheet_data = [["Channel A", "Agency A", "Channel B", "Agency B", "Shared Viewers", "Strong Shared", "Calculated At"]]
    for r in overlap_rows:
        ca, cb, shared_any, strong_shared, sa, sb = r
        na = cid_to_name.get(ca, ca)
        nb = cid_to_name.get(cb, cb)
        aga = cid_to_agency.get(ca, "Independent")
        agb = cid_to_agency.get(cb, "Independent")
        network_sheet_data.append([na, aga, nb, agb, shared_any, strong_shared, calc_time])

    safe_update_sheet(ws_network, network_sheet_data, batch_size=2000)
    logger.info(f" -> Synced {len(network_sheet_data)-1} overlap connections to 'NETWORK_RESULT'!")

    # 4B. Sync ALL_COMMENTERS (The requested commenter list!)
    logger.info("Syncing ALL_COMMENTERS sheet...")
    sorted_commenters = sorted(unique_commenter_profiles.values(), key=lambda x: x["comment_count"], reverse=True)
    ws_commenters = get_or_create_worksheet(sh, "ALL_COMMENTERS", rows=max(100, len(sorted_commenters) + 20), cols=5)
    
    commenter_sheet_data = [["authorDisplayName", "authorChannelUrl", "comment_count", "channels_active", "last_seen"]]
    for u in sorted_commenters:
        vt_list = ", ".join(sorted(list(u["vtubers"]))[:3])
        if len(u["vtubers"]) > 3:
            vt_list += f" (+{len(u['vtubers'])-3} others)"
        commenter_sheet_data.append([
            u["authorDisplayName"],
            u["authorChannelUrl"],
            u["comment_count"],
            vt_list,
            u["last_seen"]
        ])

    safe_update_sheet(ws_commenters, commenter_sheet_data, batch_size=2000)
    logger.info(f" -> Synced {len(commenter_sheet_data)-1} commenters to 'ALL_COMMENTERS'!")

    # 4C. Sync SYSTEM status
    logger.info("Syncing SYSTEM status sheet...")
    ws_system = get_or_create_worksheet(sh, "SYSTEM", rows=20, cols=3)
    sys_rows = [
        ["Metric", "Value"],
        ["Project", "Thai VTuber Audience Network (SNA) - Batch Run"],
        ["Target Channels Monitored", f"{len(target_channels)} channels (Top Active & Agencies)"],
        ["Videos Analyzed", f"{len(all_videos_to_process)} videos"],
        ["Overlap Connections Discovered", f"{len(overlap_rows)} connections"],
        ["Total Unique Commenters", f"{len(unique_commenter_profiles):,} people"],
        ["Last Execution Time", calc_time],
        ["Storage Policy", "Cloud Only (Google Sheets) - Zero Local Disk Clutter"],
        ["HMAC Key Fingerprint", key_fingerprint]
    ]
    safe_update_sheet(ws_system, sys_rows, batch_size=100)
    logger.info(" -> Updated 'SYSTEM' status.")

    logger.info("==========================================================")
    logger.info(" Finished! All data uploaded directly to Google Sheets!   ")
    logger.info(f" URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
    logger.info("==========================================================")

    con.close()

if __name__ == "__main__":
    main()
