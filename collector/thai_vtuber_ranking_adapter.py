"""
Thai VTuber Audience Network (SNA)
Thai VTuber Ranking Directory Adapter (Chuysan)

Fetches full directory dump from Thai VTuber Ranking API:
Endpoint: https://storage.googleapis.com/thaivtuberranking.appspot.com/v2/channel_data/simple_list.json
Over 1,300 real Thai VTuber channels with subscriber counts, views, and video upload dates.
"""
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any
import requests

logger = logging.getLogger(__name__)

API_URL = "https://storage.googleapis.com/thaivtuberranking.appspot.com/v2/channel_data/simple_list.json"


class ThaiVtuberRankingAdapter:
    SOURCE_NAME = "Thai VTuber Ranking"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def fetch_candidates(self) -> List[Dict[str, Any]]:
        """
        Fetches full dump of Thai VTuber channels from Chuysan Ranking API.
        Returns list of normalized candidate dicts.
        """
        logger.info(f"Fetching complete Thai VTuber directory from {API_URL}...")
        try:
            resp = requests.get(
                API_URL,
                timeout=self.timeout,
                headers={"User-Agent": "ThaiVtuberSNA/2.0 (Academic Research Pipeline)"}
            )
            resp.raise_for_status()
            data = resp.json()
            raw_list = data.get("result", [])
            logger.info(f"Received {len(raw_list)} raw channel records from {self.SOURCE_NAME}.")
        except Exception as e:
            logger.error(f"Failed to fetch from {self.SOURCE_NAME}: {e}")
            return []

        candidates = []
        for item in raw_list:
            cid = str(item.get("channel_id", "")).strip()
            if not cid or not cid.startswith("UC") or len(cid) != 24:
                continue

            title = str(item.get("title", "")).strip()
            subs = int(item.get("subscribers", 0) or 0)
            views = int(item.get("views", 0) or 0)
            published_at = item.get("published_at") or ""
            last_pub = item.get("last_published_video_at") or ""
            is_rebranded = bool(item.get("is_rebranded", False))

            # Infer Agency if present in title
            agency = "Independent"
            title_lower = title.lower()
            if "arp" in title_lower or "algorhythm" in title_lower:
                agency = "Algorhythm Project"
            elif "polygon" in title_lower:
                agency = "Polygon Official"
            elif "pixela" in title_lower:
                agency = "Pixela Project"
            elif "lumina" in title_lower:
                agency = "Lumina Live"
            elif "euphora" in title_lower:
                agency = "Euphora Project"
            elif "myriad" in title_lower:
                agency = "Myriad Colors"
            elif "virtual union" in title_lower:
                agency = "Virtual Union"
            elif "horganice" in title_lower:
                agency = "Horganice"

            normalized = {
                "channel_id": cid,
                "handle": f"@{re.sub(r'[^a-zA-Z0-9_]', '', title)}",
                "name": title,
                "subscriber_count": subs,
                "view_count": views,
                "source": self.SOURCE_NAME,
                "source_url": f"https://vtuber.chuysan.com/channel/{cid}",
                "channel_created_at": published_at,
                "last_published_video_at": last_pub,
                "last_seen": last_pub or datetime.now(timezone.utc).isoformat(),
                "description": f"{title} from {self.SOURCE_NAME}",
                "agency": agency,
                "is_rebranded": is_rebranded,
                "source_count": 1
            }
            candidates.append(normalized)

        logger.info(f"Normalized {len(candidates)} valid channels from {self.SOURCE_NAME}.")
        return candidates
