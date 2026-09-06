"""
Thai VTuber Audience Network (SNA)
Memory-Only Live Chat Adapter

Extracts pseudonymous viewer presence from YouTube Live Streams via direct HTTPS REST API.
STRICT PRIVACY ENFORCEMENT:
- Operates 100% in memory; NEVER writes raw chat text, subtitles, or dumps to disk.
- Hashes stable author channel IDs immediately via HMAC-SHA256.
- Discards all message bodies, avatars, emojis, display names, and sentiment.
- Bounded collection limits prevent memory exhaustion.
- Fails closed when live chat is unavailable or unconfigured.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import requests

from core.hasher import PrivacyHasher
from config.settings import YOUTUBE_API_KEY

logger = logging.getLogger(__name__)


class LiveChatAdapter:
    def __init__(self, hasher: Optional[PrivacyHasher] = None, api_key: Optional[str] = None):
        self.hasher = hasher or PrivacyHasher()
        self.api_key = api_key if api_key is not None else YOUTUBE_API_KEY

    def is_available(self) -> bool:
        """Returns True if live chat extraction backend is configured."""
        return bool(self.api_key and self.api_key.strip())

    def collect_live_chat_events(
        self,
        job_dict: Dict[str, Any],
        max_messages: int = 150,
        continuation_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Collects bounded live chat presence from an active live stream directly in memory.
        Returns outcome dictionary:
        {
            "status": "SUCCESS" | "LIVE_CHAT_UNAVAILABLE" | "RATE_LIMITED" | "EXTRACTION_FAILURE",
            "events": List[Dict[str, Any]],
            "continuation_token": Optional[str],
            "reason": Optional[str]
        }
        """
        video_id = job_dict.get("video_id", "")
        vtuber_id = job_dict.get("vtuber_channel_id", "")

        if not re.fullmatch(r"[A-Za-z0-9_-]+", video_id):
            raise ValueError(f"Invalid video_id: {video_id}")

        if not self.is_available():
            logger.info("Live chat collection unavailable: No YouTube Data API key configured.")
            return {
                "status": "LIVE_CHAT_UNAVAILABLE",
                "events": [],
                "continuation_token": None,
                "reason": "NO_API_KEY_CONFIGURED"
            }

        try:
            # 1. Discover active live chat ID for video
            chat_id = job_dict.get("active_live_chat_id")
            if not chat_id:
                details_url = f"https://www.googleapis.com/youtube/v3/videos?part=liveStreamingDetails&id={video_id}&key={self.api_key}"
                resp = requests.get(details_url, timeout=10.0)
                if resp.status_code == 429:
                    return {"status": "RATE_LIMITED", "events": [], "continuation_token": None, "reason": "HTTP_429"}
                if resp.status_code != 200:
                    return {"status": "EXTRACTION_FAILURE", "events": [], "continuation_token": None, "reason": f"HTTP_{resp.status_code}"}

                items = resp.json().get("items", [])
                if not items:
                    return {"status": "LIVE_CHAT_UNAVAILABLE", "events": [], "continuation_token": None, "reason": "VIDEO_NOT_FOUND"}

                chat_id = items[0].get("liveStreamingDetails", {}).get("activeLiveChatId")
                if not chat_id:
                    return {"status": "LIVE_CHAT_UNAVAILABLE", "events": [], "continuation_token": None, "reason": "NO_ACTIVE_LIVE_CHAT"}

            # 2. Fetch live chat messages in memory
            params = {
                "liveChatId": chat_id,
                "part": "snippet,authorDetails",
                "maxResults": min(max_messages, 200),
                "key": self.api_key
            }
            if continuation_token:
                params["pageToken"] = continuation_token

            chat_url = "https://www.googleapis.com/youtube/v3/liveChatMessages"
            chat_resp = requests.get(chat_url, params=params, timeout=10.0)
            if chat_resp.status_code == 429:
                return {"status": "RATE_LIMITED", "events": [], "continuation_token": None, "reason": "HTTP_429"}
            if chat_resp.status_code != 200:
                return {"status": "EXTRACTION_FAILURE", "events": [], "continuation_token": None, "reason": f"HTTP_{chat_resp.status_code}"}

            data = chat_resp.json()
            items = data.get("items", [])
            next_token = data.get("nextPageToken")

            # 3. Privacy Transformation: Hash authorChannelId immediately in-memory
            events = []
            for item in items[:max_messages]:
                author_details = item.get("authorDetails", {})
                raw_author_id = author_details.get("channelId")
                if not raw_author_id or not str(raw_author_id).startswith("UC"):
                    continue

                viewer_hash = self.hasher.hash_viewer_id(str(raw_author_id))
                ts = item.get("snippet", {}).get("publishedAt") or datetime.now(timezone.utc).isoformat()

                # ONLY approved pseudonymous presence fields are recorded
                events.append({
                    "viewer_hash": viewer_hash,
                    "vtuber_channel_id": vtuber_id,
                    "video_id": video_id,
                    "timestamp": ts,
                    "source_type": "live_chat"
                })

            logger.info(f"Memory-only live chat extracted {len(events)} events for video {video_id}.")
            return {
                "status": "SUCCESS",
                "events": events,
                "continuation_token": next_token,
                "reason": None
            }

        except Exception as e:
            logger.error(f"Error in memory-only live chat collection for {video_id}: {e}")
            return {
                "status": "EXTRACTION_FAILURE",
                "events": [],
                "continuation_token": None,
                "reason": str(e)
            }
