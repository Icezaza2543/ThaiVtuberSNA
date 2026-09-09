"""
Thai VTuber Audience Network (SNA)
VTuber Discovery Adapter

Ingests candidate VTubers from directory sources, normalizes schema,
and deduplicates strictly by YouTube Channel ID (never by Channel Name).
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
from collector.thai_vtuber_ranking_adapter import ThaiVtuberRankingAdapter
from collector.fandom_thai_adapter import FandomThaiVtuberAdapter

logger = logging.getLogger(__name__)

NORMALIZED_KEYS = [
    "channel_id",
    "handle",
    "name",
    "subscriber_count",
    "source",
    "source_url",
    "last_seen",
    "source_count",
    "description",
    "agency"
]


class DiscoveryAdapter:
    @staticmethod
    def prepare_review_queue(raw_sources, *, candidate_ids, discovered_at):
        """Offline additive review seam; does not fetch or auto-approve directory entries."""
        from core.discovery_review import candidate
        records = [r for source in raw_sources for r in source]
        if len(records) != len(candidate_ids) or len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError('Supply one unique stable candidate ID per source record')
        return [candidate(raw, candidate_id=cid, discovered_at=discovered_at)
                for raw, cid in zip(records, candidate_ids)]

    def __init__(self, seed_file_path: Path = None):
        self.seed_file_path = seed_file_path
        self.ranking_adapter = ThaiVtuberRankingAdapter()
        self.fandom_adapter = FandomThaiVtuberAdapter(limit=30)

    def fetch_from_real_directories(self) -> List[Dict[str, Any]]:
        """
        Fetches Thai VTubers from at least 2 real directory sources
        without crawling general YouTube search.
        Deduplicates strictly by Channel ID and tracks provenance.
        """
        logger.info("Starting candidate discovery from real Thai VTuber directories...")
        ranking_candidates = self.ranking_adapter.fetch_candidates()
        fandom_candidates = self.fandom_adapter.fetch_candidates()
        
        merged = self.discover_and_deduplicate([ranking_candidates, fandom_candidates])
        logger.info(f"Total deduplicated VTubers from real directories: {len(merged)}")
        return merged

    def load_from_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """Loads raw candidate records from a JSON file."""
        if not file_path.exists():
            logger.warning(f"Seed file not found: {file_path}")
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading seeds from {file_path}: {e}")
            return []

    def normalize_candidate(self, raw: Dict[str, Any], default_source: str = "Directory") -> Dict[str, Any]:
        """Normalizes candidate schema according to project requirements."""
        channel_id = str(raw.get("channel_id") or raw.get("id", "")).strip()
        handle = str(raw.get("handle") or "").strip()
        name = str(raw.get("name") or raw.get("title", "")).strip()

        try:
            subs = int(raw.get("subscriber_count") or raw.get("subscribers", 0))
        except (ValueError, TypeError):
            subs = 0

        source = str(raw.get("source") or default_source)
        source_url = str(raw.get("source_url") or "")
        last_seen = raw.get("last_seen") or datetime.now(timezone.utc).isoformat()
        description = str(raw.get("description") or "")
        agency = str(raw.get("agency") or "Independent")

        return {
            "channel_id": channel_id,
            "handle": handle,
            "name": name,
            "subscriber_count": subs,
            "source": source,
            "source_url": source_url,
            "last_seen": last_seen,
            "source_count": 1,
            "description": description,
            "agency": agency
        }

    def discover_and_deduplicate(self, raw_sources: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Deduplicates candidate VTubers by YouTube Channel ID as primary identity.
        Aggregates source_count when the same channel appears in multiple directories.
        """
        merged_candidates: Dict[str, Dict[str, Any]] = {}

        for source_list in raw_sources:
            for item in source_list:
                normalized = self.normalize_candidate(item)
                cid = normalized["channel_id"]
                if not cid:
                    continue  # Skip entries without valid Channel ID

                if cid not in merged_candidates:
                    merged_candidates[cid] = normalized
                else:
                    # Deduplicate: Merge & increment source count
                    existing = merged_candidates[cid]
                    existing["source_count"] += 1
                    # Update subscriber count if new record has higher/newer value
                    if normalized["subscriber_count"] > existing["subscriber_count"]:
                        existing["subscriber_count"] = normalized["subscriber_count"]
                    # Retain description or agency if missing
                    if not existing.get("description") and normalized.get("description"):
                        existing["description"] = normalized["description"]
                    if existing.get("agency") == "Independent" and normalized.get("agency") != "Independent":
                        existing["agency"] = normalized["agency"]

        return list(merged_candidates.values())
