"""
Thai VTuber Audience Network (SNA)
Thai VTuber Ranking Directory Adapter

Fetches real Thai VTuber channels from the Thai VTuber Ranking API (Chuysan).
Endpoint: https://storage.googleapis.com/thaivtuberranking.appspot.com/v2/channel_data/simple_list.json
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

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def fetch_candidates(self) -> List[Dict[str, Any]]:
        """
        Fetches and normalizes candidate Thai VTubers from Thai VTuber Ranking API.
        Returns list of normalized candidate dicts.
        """
        logger.info(f"Fetching Thai VTuber directory from {API_URL}...")
        try:
            resp = requests.get(API_URL, timeout=self.timeout, headers={"User-Agent": "ThaiVtuberSNA/1.0"})
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
            if not cid or not cid.startswith("UC"):
                continue

            title = str(item.get("title", "")).strip()
            subs = int(item.get("subscribers", 0) or 0)
            last_pub = item.get("last_published_video_at") or datetime.now(timezone.utc).isoformat()
            
            # Detect Agency if present in title
            agency = "Independent"
            title_lower = title.lower()
            if "arp" in title_lower or "algorhythm" in title_lower:
                agency = "Algorhythm Project"
            elif "polygon" in title_lower:
                agency = "Polygon Official"
            elif "pixela" in title_lower:
                agency = "Pixela Project"
            elif "lumina" in title_lower:
                agency = "Lumina"
            elif "euphora" in title_lower:
                agency = "Euphora"

            normalized = {
                "channel_id": cid,
                "handle": f"@{re.sub(r'[^a-zA-Z0-9_]', '', title)}",
                "name": title,
                "subscriber_count": subs,
                "source": self.SOURCE_NAME,
                "source_url": f"https://vtuber.chuysan.com/channel/{cid}",
                "last_seen": last_pub,
                "description": f"{title} from {self.SOURCE_NAME}",
                "agency": agency,
                "source_count": 1
            }
            candidates.append(normalized)

        return candidates
