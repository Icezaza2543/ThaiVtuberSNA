"""
Thai VTuber Audience Network (SNA)
Fandom Virtual YouTuber Wiki Adapter

Fetches real Thai VTuber profiles from the Virtual YouTuber Fandom MediaWiki API.
Category: Category:Thai
API Endpoint: https://virtualyoutuber.fandom.com/api.php
"""
import logging
import re
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any
import requests

logger = logging.getLogger(__name__)

API_BASE = "https://virtualyoutuber.fandom.com/api.php"


class FandomThaiVtuberAdapter:
    SOURCE_NAME = "Virtual YouTuber Fandom Wiki"

    def __init__(self, limit: int = 50, timeout: int = 15):
        self.limit = limit
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ThaiVtuberSNA/1.0 (Research Pipeline)"})

    def fetch_candidates(self) -> List[Dict[str, Any]]:
        """
        Fetches category members from Category:Thai and resolves official YouTube Channel IDs.
        """
        logger.info(f"Fetching Category:Thai from {self.SOURCE_NAME}...")
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Thai",
            "cmlimit": self.limit,
            "format": "json"
        }
        try:
            resp = self.session.get(API_BASE, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            members = data.get("query", {}).get("categorymembers", [])
            logger.info(f"Found {len(members)} pages in Category:Thai on Fandom.")
        except Exception as e:
            logger.error(f"Failed to fetch Fandom Category:Thai: {e}")
            return []

        candidates = []
        for member in members:
            page_title = member.get("title", "")
            # Filter out non-person pages (categories, discographies, projects)
            if any(skip in page_title for skip in ["Category:", "Discography", "Gallery", "User:"]):
                continue

            channel_id = self._resolve_youtube_id(page_title)
            if not channel_id:
                continue

            encoded_title = urllib.parse.quote(page_title.replace(" ", "_"))
            normalized = {
                "channel_id": channel_id,
                "handle": f"@{re.sub(r'[^a-zA-Z0-9_]', '', page_title)}",
                "name": page_title,
                "subscriber_count": 0,  # Fandom wikitext doesn't always have live subscriber count
                "source": self.SOURCE_NAME,
                "source_url": f"https://virtualyoutuber.fandom.com/wiki/{encoded_title}",
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "description": f"{page_title} - Thai VTuber on Virtual YouTuber Wiki",
                "agency": "Independent",
                "source_count": 1
            }
            candidates.append(normalized)

        logger.info(f"Successfully resolved {len(candidates)} VTubers with Channel IDs from Fandom.")
        return candidates

    def _resolve_youtube_id(self, page_title: str) -> str:
        """Parses page wikitext to extract official YouTube channel ID (UC...)."""
        params = {
            "action": "parse",
            "page": page_title,
            "prop": "wikitext",
            "format": "json"
        }
        try:
            resp = self.session.get(API_BASE, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                return ""
            wikitext = resp.json().get("parse", {}).get("wikitext", {}).get("*", "")
            # Look for YouTube channel ID pattern: UC followed by 22 alphanumeric characters
            matches = re.findall(r"UC[a-zA-Z0-9_-]{22}", wikitext)
            if matches:
                # Return the most frequent or first match
                return matches[0]
        except Exception:
            pass
        return ""
