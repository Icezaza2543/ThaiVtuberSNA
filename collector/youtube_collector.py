"""
Thai VTuber Audience Network (SNA)
YouTube Collector Adapter

Collects viewer presence from real YouTube live streams and public VODs.
Dual-backend support:
1. Public VOD / Stream extractor (via yt-dlp, zero API key required)
2. YouTube Data API v3 (when YOUTUBE_API_KEY is configured)

STRICT PRIVACY ENFORCEMENT:
- Author channel IDs are hashed immediately via HMAC-SHA256.
- Raw channel IDs, display names, avatars, emoji, comment/chat text,
  and sentiment are NEVER stored or persisted.
"""
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from collector.base_collector import BaseCollector
from core.hasher import hash_viewer
from config.settings import YOUTUBE_API_KEY

logger = logging.getLogger(__name__)


class YouTubeCollector(BaseCollector):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or YOUTUBE_API_KEY
        self._youtube = None
        if self.api_key:
            try:
                from googleapiclient.discovery import build
                self._youtube = build("youtube", "v3", developerKey=self.api_key)
                logger.info("YouTube API client initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize YouTube API client: {e}")

    def fetch_latest_video_for_channel(self, channel_id: str) -> Optional[str]:
        """
        Finds the latest public video ID for a channel without crawling YouTube search.
        Uses yt-dlp channel video list tab.
        """
        import yt_dlp
        channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
        ydl_opts = {
            "playlist_items": "1",
            "extract_flat": True,
            "skip_download": True,
            "quiet": True,
            "no_warnings": True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                res = ydl.extract_info(channel_url, download=False)
                entries = list(res.get("entries", []))
                if entries and entries[0]:
                    return entries[0].get("id")
        except Exception as e:
            logger.warning(f"Could not fetch latest video for channel {channel_id}: {e}")
        return None

    def collect_events(self, job_dict: Dict[str, Any], max_comments: int = 150) -> List[Dict[str, Any]]:
        """
        Collects viewer presence from a real YouTube video or stream.
        Outputs ONLY:
        - viewer_hash
        - vtuber_channel_id
        - video_id
        - timestamp
        - source_type
        """
        video_id = job_dict["video_id"]
        vtuber_id = job_dict["vtuber_channel_id"]

        # 1. Try YouTube Data API v3 if client available
        if self._youtube:
            api_events = self._collect_via_api(video_id, vtuber_id)
            if api_events:
                return api_events

        # 2. Extract via yt-dlp public comment/chat extractor
        return self._collect_via_ytdlp(video_id, vtuber_id, max_comments=max_comments)

    def collect_aggregated_events(self, job_dict: Dict[str, Any], max_comments: int = 150) -> List[Dict[str, Any]]:
        """
        Outputs aggregated session schema (Requirement 2 & 7):
        - viewer_hash
        - vtuber_channel_id
        - video_id
        - first_seen
        - last_seen
        - appearances
        - source_type
        """
        raw_events = self.collect_events(job_dict, max_comments=max_comments)
        agg_map: Dict[str, Dict[str, Any]] = {}

        for ev in raw_events:
            vh = ev["viewer_hash"]
            t = ev["timestamp"]
            if vh not in agg_map:
                agg_map[vh] = {
                    "viewer_hash": vh,
                    "vtuber_channel_id": ev["vtuber_channel_id"],
                    "video_id": ev["video_id"],
                    "first_seen": t,
                    "last_seen": t,
                    "appearances": 1,
                    "source_type": ev["source_type"]
                }
            else:
                agg_map[vh]["appearances"] += 1
                if t < agg_map[vh]["first_seen"]:
                    agg_map[vh]["first_seen"] = t
                if t > agg_map[vh]["last_seen"]:
                    agg_map[vh]["last_seen"] = t

        return list(agg_map.values())

    def _collect_via_ytdlp(self, video_id: str, vtuber_id: str, max_comments: int = 150) -> List[Dict[str, Any]]:
        """
        Extracts public comments using yt-dlp without API key.
        Applies immediate HMAC-SHA256 hashing on author_id.
        Discards all text, avatars, emojis, and names.
        """
        import yt_dlp
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            "getcomments": True,
            "skip_download": True,
            "max_comments": max_comments,
            "quiet": True,
            "no_warnings": True
        }

        events = []
        try:
            logger.info(f"Extracting viewer presence from public video {video_id}...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                comments = info.get("comments", [])
                
                for c in comments:
                    raw_author_id = c.get("author_id")
                    if not raw_author_id or not str(raw_author_id).startswith("UC"):
                        continue

                    # PRIVACY RULE: Immediate one-way salted hashing
                    viewer_hash = hash_viewer(str(raw_author_id))
                    
                    # Convert timestamp to ISO format
                    ts_raw = c.get("timestamp")
                    if ts_raw:
                        dt = datetime.fromtimestamp(ts_raw, timezone.utc)
                        ts_iso = dt.isoformat()
                    else:
                        ts_iso = datetime.now(timezone.utc).isoformat()

                    # Strictly store only the allowed fields
                    events.append({
                        "viewer_hash": viewer_hash,
                        "vtuber_channel_id": vtuber_id,
                        "video_id": video_id,
                        "timestamp": ts_iso,
                        "source_type": "comment"
                    })

            logger.info(f"Extracted {len(events)} privacy-preserving events from {video_id}.")
        except Exception as e:
            logger.error(f"Error in yt-dlp extraction for video {video_id}: {e}")

        return events

    def _collect_via_api(self, video_id: str, vtuber_id: str) -> List[Dict[str, Any]]:
        """YouTube Data API v3 collection with immediate hashing."""
        try:
            comment_req = self._youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                textFormat="plainText"
            )
            comment_res = comment_req.execute()
            events = []

            for item in comment_res.get("items", []):
                top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                raw_id = top.get("authorChannelId", {}).get("value")
                if not raw_id:
                    continue

                v_hash = hash_viewer(raw_id)
                ts = top.get("publishedAt") or datetime.now(timezone.utc).isoformat()

                events.append({
                    "viewer_hash": v_hash,
                    "vtuber_channel_id": vtuber_id,
                    "video_id": video_id,
                    "timestamp": ts,
                    "source_type": "comment"
                })

            return events
        except Exception as e:
            logger.warning(f"YouTube Data API error for {video_id}: {e}")
            return []
