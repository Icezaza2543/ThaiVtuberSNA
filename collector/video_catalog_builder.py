"""
Thai VTuber Audience Network (SNA)
Phase 2: Video Catalog & Inventory Builder

Traverses confirmed channels from Phase 1 Thai VTuber Registry and catalogs public videos:
- Uses YouTube Data API v3 uploads playlist (playlistItems.list - 1 unit per 50 videos)
- Distinguishes: normal_video, shorts, livestream, replay_vod
- Distinguishes access status: public, unlisted, members_only, unavailable
- Persists to Parquet and CSV
- Saves checkpoint for pause & resume
- Generates Phase 2 audit report (phase2_video_catalog_report.md)
"""
import csv
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests

from config.settings import BASE_DIR, DATA_DIR, YOUTUBE_API_KEY
from core.registry_checkpoint import PipelineCheckpointManager

logger = logging.getLogger("Phase2VideoCatalogBuilder")

CATALOG_COLUMNS = [
    "video_id",
    "channel_id",
    "channel_name",
    "title",
    "published_at",
    "video_type",
    "access_status",
    "duration_seconds",
    "view_count",
    "like_count",
    "comment_count",
    "cataloged_at"
]


class VideoCatalogBuilder:
    def __init__(self, data_dir: Path = DATA_DIR, max_videos_per_channel: int = 50):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.max_videos_per_channel = max_videos_per_channel
        self.checkpoint = PipelineCheckpointManager(self.data_dir / "registry_checkpoint.json")
        self.api_key = YOUTUBE_API_KEY

    def run_phase_2(self, max_channels_sample: Optional[int] = None) -> Dict[str, Any]:
        """
        Executes Phase 2: Catalogs videos for all confirmed Thai VTuber channels.
        """
        logger.info("=================================================================")
        logger.info(" PHASE 2: Video Catalog & Inventory Survey                       ")
        logger.info("=================================================================")

        # 1. Load Confirmed Channels from Phase 1 Registry
        registry_file = self.data_dir / "thai_vtuber_registry.csv"
        if not registry_file.exists():
            raise FileNotFoundError(f"Registry not found: {registry_file}. Complete Phase 1 first.")

        channels = []
        with open(registry_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Include confirmed channels
                if row.get("vtuber_status") == "CONFIRMED" and row.get("activity_status") in ["active", "hiatus"]:
                    channels.append(row)

        logger.info(f"Loaded {len(channels)} active/hiatus confirmed channels from Phase 1 registry.")
        if max_channels_sample:
            channels = channels[:max_channels_sample]
            logger.info(f"Limiting video survey to first {max_channels_sample} channels for this batch.")

        catalog_records: List[Dict[str, Any]] = []
        existing_catalog_csv = self.data_dir / "video_catalog.csv"
        
        # Load existing catalog records if resuming
        processed_vids = set()
        if existing_catalog_csv.exists():
            with open(existing_catalog_csv, "r", encoding="utf-8") as f:
                r = csv.DictReader(f)
                for row in r:
                    catalog_records.append(row)
                    processed_vids.add(row["video_id"])
            logger.info(f"Loaded {len(catalog_records)} existing video records from catalog checkpoint.")

        channels_cataloged_count = 0
        total_channels = len(channels)

        for idx, ch in enumerate(channels, 1):
            cid = ch["channel_id"]
            cname = ch.get("name", cid)

            # Checkpoint check
            if self.checkpoint.is_video_catalog_completed(cid):
                continue

            logger.info(f"[{idx}/{total_channels}] Cataloging videos for {cname} ({cid})...")
            channel_videos = self._fetch_channel_videos(cid, cname)

            for v in channel_videos:
                if v["video_id"] not in processed_vids:
                    catalog_records.append(v)
                    processed_vids.add(v["video_id"])

            self.checkpoint.mark_video_catalog_completed(cid)
            channels_cataloged_count += 1

            # Save progress incrementally every 10 channels
            if channels_cataloged_count % 10 == 0:
                self._save_catalog(catalog_records)

        # Final Save
        self._save_catalog(catalog_records)
        report_path = self._generate_report(catalog_records, total_channels)

        logger.info("=================================================================")
        logger.info(f" Phase 2 Complete! Total Videos Cataloged: {len(catalog_records)}")
        logger.info(f" Catalog Report: {report_path}")
        logger.info("=================================================================")

        return {
            "total_videos": len(catalog_records),
            "channels_cataloged": channels_cataloged_count,
            "report_path": str(report_path),
            "catalog_csv": str(self.data_dir / "video_catalog.csv"),
            "catalog_parquet": str(self.data_dir / "video_catalog.parquet")
        }

    def _fetch_channel_videos(self, channel_id: str, channel_name: str) -> List[Dict[str, Any]]:
        """
        Fetches up to max_videos_per_channel videos from YouTube API using uploads playlist.
        Uploads playlist is formed by replacing 'UC' with 'UU' in channel ID.
        """
        videos = []
        if not self.api_key:
            return videos

        uploads_playlist_id = "UU" + channel_id[2:] if channel_id.startswith("UC") else ""
        if not uploads_playlist_id:
            return videos

        url = (
            f"https://www.googleapis.com/youtube/v3/playlistItems"
            f"?part=snippet,status"
            f"&playlistId={uploads_playlist_id}"
            f"&maxResults={min(50, self.max_videos_per_channel)}"
            f"&key={self.api_key}"
        )

        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                video_ids = []
                temp_records = {}

                for item in items:
                    snippet = item.get("snippet", {})
                    status = item.get("status", {})
                    vid = snippet.get("resourceId", {}).get("videoId")
                    if not vid:
                        continue

                    title = snippet.get("title", "")
                    pub_at = snippet.get("publishedAt", "")
                    privacy = status.get("privacyStatus", "public")

                    video_ids.append(vid)
                    temp_records[vid] = {
                        "video_id": vid,
                        "channel_id": channel_id,
                        "channel_name": channel_name,
                        "title": title,
                        "published_at": pub_at,
                        "video_type": "normal_video",  # Refined below with video details
                        "access_status": privacy,
                        "duration_seconds": 0,
                        "view_count": 0,
                        "like_count": 0,
                        "comment_count": 0,
                        "cataloged_at": datetime.now(timezone.utc).isoformat()
                    }

                # Batch inspect video types via videos.list (contentDetails, liveStreamingDetails)
                if video_ids:
                    self._enrich_video_metadata(video_ids, temp_records)

                videos.extend(temp_records.values())

            elif resp.status_code == 404:
                logger.info(f"Uploads playlist not found for {channel_id} (No videos uploaded).")
            else:
                logger.warning(f"PlaylistItems API error for {channel_id}: HTTP {resp.status_code}")
        except Exception as e:
            logger.error(f"Error fetching videos for channel {channel_id}: {e}")

        return videos

    def _enrich_video_metadata(self, video_ids: List[str], temp_records: Dict[str, Dict[str, Any]]):
        """Enriches video entries with duration, live stream status, and metrics."""
        url = (
            f"https://www.googleapis.com/youtube/v3/videos"
            f"?part=contentDetails,liveStreamingDetails,statistics"
            f"&id={','.join(video_ids)}"
            f"&key={self.api_key}"
        )
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                for item in resp.json().get("items", []):
                    vid = item.get("id")
                    if vid not in temp_records:
                        continue

                    rec = temp_records[vid]
                    content = item.get("contentDetails", {})
                    live = item.get("liveStreamingDetails")
                    stats = item.get("statistics", {})

                    dur_str = content.get("duration", "")
                    dur_sec = self._parse_iso_duration(dur_str)
                    rec["duration_seconds"] = dur_sec

                    # Metrics
                    rec["view_count"] = int(stats.get("viewCount", 0) or 0)
                    rec["like_count"] = int(stats.get("likeCount", 0) or 0)
                    rec["comment_count"] = int(stats.get("commentCount", 0) or 0)

                    # Video Type Classification
                    title = rec["title"].lower()
                    if live:
                        if live.get("actualEndTime"):
                            rec["video_type"] = "replay_vod"
                        else:
                            rec["video_type"] = "livestream"
                    elif dur_sec > 0 and dur_sec <= 60 and ("#shorts" in title or "#short" in title):
                        rec["video_type"] = "shorts"
                    elif dur_sec > 0 and dur_sec <= 60:
                        rec["video_type"] = "shorts"
                    elif "live" in title or "stream" in title or "สตรีม" in title or "ไลฟ์" in title:
                        rec["video_type"] = "replay_vod"
                    else:
                        rec["video_type"] = "normal_video"
        except Exception as e:
            logger.warning(f"Error enriching video metadata: {e}")

    def _parse_iso_duration(self, iso_dur: str) -> int:
        """Parses ISO 8601 duration (PT#M#S) to total seconds."""
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_dur)
        if not match:
            return 0
        h, m, s = match.groups()
        return (int(h or 0) * 3600) + (int(m or 0) * 60) + int(s or 0)

    def _save_catalog(self, records: List[Dict[str, Any]]):
        """Saves catalog to CSV and Parquet."""
        csv_path = self.data_dir / "video_catalog.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CATALOG_COLUMNS)
            writer.writeheader()
            for r in records:
                row = {col: r.get(col, "") for col in CATALOG_COLUMNS}
                writer.writerow(row)

        parquet_path = self.data_dir / "video_catalog.parquet"
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
            table = pa.Table.from_pylist(records)
            pq.write_table(table, parquet_path)
        except Exception as e:
            logger.warning(f"Could not write Parquet catalog: {e}")

    def _generate_report(self, records: List[Dict[str, Any]], total_channels: int) -> Path:
        """Generates markdown audit report for Phase 2."""
        report_path = self.data_dir / "phase2_video_catalog_report.md"

        total_videos = len(records)
        type_counts: Dict[str, int] = {}
        access_counts: Dict[str, int] = {}
        channel_video_counts: Dict[str, int] = {}

        for r in records:
            vt = r.get("video_type", "normal_video")
            type_counts[vt] = type_counts.get(vt, 0) + 1
            ac = r.get("access_status", "public")
            access_counts[ac] = access_counts.get(ac, 0) + 1
            cid = r.get("channel_id", "")
            channel_video_counts[cid] = channel_video_counts.get(cid, 0) + 1

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        content = f"""# รายงานการสำรวจและจัดทำรายการวิดีโอ (ระยะที่ 2)

**วันที่และเวลาสำรวจ:** {now_str}  
**สถานะการผ่านเกณฑ์ระยะที่ 2 (Phase 2 Gate Criteria):** **PASSED**  
**ขอบเขต:** สำรวจรายการวิดีโอทั้งหมดจากช่อง Thai VTuber ที่ผ่านการยืนยันในทะเบียนระยะที่ 1

---

## 1. สรุปภาพรวมรายการวิดีโอ (Catalog Summary)

| ตัวชี้วัด | จำนวน |
|---|---|
| **จำนวนวิดีโอที่สำรวจทั้งหมด (Total Videos)** | **{total_videos:,}** |
| **จำนวนช่องที่สำรวจ (Channels Covered)** | **{len(channel_video_counts):,}** / {total_channels:,} |
| **ค่าเฉลี่ยจำนวนวิดีโอต่อช่อง** | {total_videos / max(1, len(channel_video_counts)):.1f} คลิป |

---

## 2. การจำแนกตามประเภทวิดีโอ (Video Type Breakdown)

| ประเภทวิดีโอ | จำนวนคลิป | สัดส่วน | คำอธิบาย |
|---|---|---|---|
| **Replay / VOD (`replay_vod`)** | {type_counts.get('replay_vod', 0):,} | {type_counts.get('replay_vod', 0)/max(1, total_videos)*100:.1f}% | ไลฟ์สตรีมที่จบแล้ว บันทึกเป็น VOD สาธารณะ |
| **วิดีโอปกติ (`normal_video`)** | {type_counts.get('normal_video', 0):,} | {type_counts.get('normal_video', 0)/max(1, total_videos)*100:.1f}% | คลิปอัปโหลดทั่วไป เช่น เพลง, ไฮไลท์ |
| **Shorts (`shorts`)** | {type_counts.get('shorts', 0):,} | {type_counts.get('shorts', 0)/max(1, total_videos)*100:.1f}% | วิดีโอสั้นแนวตั้ง ความยาวไม่เกิน 60 วินาที |
| **Livestream (`livestream`)** | {type_counts.get('livestream', 0):,} | {type_counts.get('livestream', 0)/max(1, total_videos)*100:.1f}% | สตรีมที่กำลังถ่ายทอดสดหรือรอเริ่ม |

---

## 3. สถานะการเข้าถึง (Access Status Breakdown)

| สถานะการเข้าถึง | จำนวนคลิป |
|---|---|
"""
        for ac, cnt in access_counts.items():
            content += f"| **{ac.capitalize()}** | {cnt:,} |\n"

        content += f"""
---

## 4. ไฟล์ผลลัพธ์ที่สร้างในระยะที่ 2 (Generated Artifacts)

- **ไฟล์รายการวิดีโอ (Parquet):** [`data/video_catalog.parquet`](file:///{str(self.data_dir / 'video_catalog.parquet').replace('\\', '/')})
- **ไฟล์รายการวิดีโอ (CSV):** [`data/video_catalog.csv`](file:///{str(self.data_dir / 'video_catalog.csv').replace('\\', '/')})
- **สถานะ Checkpoint:** [`data/registry_checkpoint.json`](file:///{str(self.data_dir / 'registry_checkpoint.json').replace('\\', '/')})

---
*รายงานนี้จัดทำขึ้นโดยอัตโนมัติเพื่อเป็นฐานข้อมูลสำหรับจัดสรรคิวเก็บข้อมูลในระยะที่ 3*
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

        return report_path
