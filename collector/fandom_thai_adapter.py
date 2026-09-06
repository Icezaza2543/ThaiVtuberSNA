"""
Thai VTuber Audience Network (SNA)
Fandom Virtual YouTuber Wiki Adapter (Enhanced & Paginated)

Fetches Thai VTuber profiles from the Virtual YouTuber Fandom MediaWiki API:
- Categories: Category:Thai, Category:Algorhythm Project, Category:Pixela
- Implements complete MediaWiki pagination (cmcontinue)
- Batch-fetches wikitext (up to 35 pages per request) for high performance
- Extracts YouTube Channel IDs, @handles, affiliations, and graduation/retirement status
"""
import logging
import re
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any, Set, Optional
import requests

logger = logging.getLogger(__name__)

API_BASE = "https://virtualyoutuber.fandom.com/api.php"


class FandomThaiVtuberAdapter:
    SOURCE_NAME = "Virtual YouTuber Fandom Wiki"
    CATEGORIES = [
        "Category:Thai",
        "Category:Algorhythm Project",
        "Category:Pixela"
    ]

    def __init__(self, timeout: int = 15, limit: Optional[int] = None):
        self.timeout = timeout
        self.limit = limit
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ThaiVtuberSNA/2.0 (Academic Research Pipeline)"})

    def fetch_all_category_members(self) -> List[str]:
        """
        Fetches all member page titles across target categories using pagination.
        Filters out category subpages, galleries, user pages, and discographies.
        """
        all_titles: Set[str] = set()

        for cat in self.CATEGORIES:
            logger.info(f"Fetching members for {cat} from Fandom...")
            cmcontinue = None
            cat_count = 0
            while True:
                params = {
                    "action": "query",
                    "list": "categorymembers",
                    "cmtitle": cat,
                    "cmlimit": 500,
                    "format": "json"
                }
                if cmcontinue:
                    params["cmcontinue"] = cmcontinue

                try:
                    resp = self.session.get(API_BASE, params=params, timeout=self.timeout)
                    resp.raise_for_status()
                    data = resp.json()
                    members = data.get("query", {}).get("categorymembers", [])
                    for m in members:
                        title = m.get("title", "")
                        # Filter out non-person pages
                        if any(skip in title for skip in ["Category:", "Discography", "Gallery", "User:", "Template:"]):
                            continue
                        all_titles.add(title)
                        cat_count += 1

                    if "continue" in data and "cmcontinue" in data["continue"]:
                        cmcontinue = data["continue"]["cmcontinue"]
                    else:
                        break
                except Exception as e:
                    logger.error(f"Error fetching category {cat}: {e}")
                    break

            logger.info(f"Retrieved {cat_count} members from {cat}.")

        logger.info(f"Total unique Fandom candidate pages: {len(all_titles)}")
        return sorted(list(all_titles))

    def fetch_candidates(self) -> List[Dict[str, Any]]:
        """
        Fetches all members and resolves YouTube channel metadata in batches.
        """
        titles = self.fetch_all_category_members()
        candidates = []
        batch_size = 35

        logger.info(f"Parsing wikitext for {len(titles)} candidate pages in batches of {batch_size}...")
        for i in range(0, len(titles), batch_size):
            batch = titles[i : i + batch_size]
            batch_candidates = self._parse_pages_batch(batch)
            candidates.extend(batch_candidates)

        logger.info(f"Fandom adapter extracted {len(candidates)} candidates with channel references.")
        return candidates

    def _parse_pages_batch(self, page_titles: List[str]) -> List[Dict[str, Any]]:
        """Batch-fetches wikitext for multiple pages using MediaWiki API."""
        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(page_titles),
            "format": "json"
        }
        candidates = []
        try:
            resp = self.session.get(API_BASE, params=params, timeout=self.timeout)
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})

            for pid, pdata in pages.items():
                title = pdata.get("title", "")
                revs = pdata.get("revisions", [])
                content = revs[0].get("slots", {}).get("main", {}).get("*", "") if revs else ""
                if not content:
                    continue

                parsed = self._extract_metadata_from_wikitext(title, content)
                if parsed:
                    candidates.append(parsed)
        except Exception as e:
            logger.error(f"Error parsing batch {page_titles[:3]}...: {e}")

        return candidates

    def _extract_metadata_from_wikitext(self, title: str, wikitext: str) -> Dict[str, Any]:
        """Extracts Channel ID, handle, affiliation, and status from wikitext."""
        # Find YouTube Channel IDs
        cids = re.findall(r"UC[a-zA-Z0-9_-]{22}", wikitext)
        channel_id = cids[0] if cids else ""

        # Find YouTube Handles or URLs if channel_id not directly in text
        handle = ""
        handle_match = re.findall(r"youtube\.com/(?:channel/|c/|user/|@)?([a-zA-Z0-9_\-\.]+)", wikitext)
        if handle_match:
            for h in handle_match:
                if h.startswith("UC") and len(h) == 24 and not channel_id:
                    channel_id = h
                elif not handle:
                    handle = f"@{h}"

        # Detect graduation/retirement status
        status_match = re.findall(r"\|status\s*=\s*([^\n\|}]+)", wikitext, re.IGNORECASE)
        status_text = status_match[0].strip().lower() if status_match else ""
        is_graduated = any(w in status_text for w in ["retired", "graduated", "inactive", "terminated"])

        # Detect affiliation
        affil_match = re.findall(r"\|affiliation\s*=\s*([^\n\|}]+)", wikitext, re.IGNORECASE)
        affiliation = "Independent"
        if affil_match:
            raw_affil = affil_match[0].strip()
            for ag in ["Algorhythm Project", "Polygon", "Pixela", "Lumina", "Euphora"]:
                if ag.lower() in raw_affil.lower():
                    affiliation = ag
                    break

        encoded_title = urllib.parse.quote(title.replace(" ", "_"))
        return {
            "channel_id": channel_id,
            "handle": handle,
            "name": title,
            "source": self.SOURCE_NAME,
            "source_url": f"https://virtualyoutuber.fandom.com/wiki/{encoded_title}",
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "description": f"{title} from {self.SOURCE_NAME}",
            "agency": affiliation,
            "is_graduated_hint": is_graduated,
            "source_count": 1
        }
