"""
Thai VTuber Audience Network (SNA)
Registry & Workflow Checkpoint Manager

Provides persistent checkpointing for multi-stage pipelines:
- Saves processed channel IDs and source statuses incrementally.
- Enables resume from interruption without starting over.
- Tracks inaccessible sources and audit logs.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger(__name__)


class PipelineCheckpointManager:
    def __init__(self, checkpoint_path: Path):
        self.checkpoint_path = checkpoint_path
        self.state: Dict[str, Any] = {
            "version": "1.0",
            "last_updated": "",
            "phase": "phase_1_registry",
            "completed_sources": {},
            "inaccessible_sources": [],
            "processed_channel_ids": [],
            "unconfirmed_channel_ids": [],
            "video_catalog_completed_channels": []
        }
        self.load()

    def load(self):
        """Loads state from checkpoint JSON file if exists."""
        if self.checkpoint_path.exists():
            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.state.update(data)
                logger.info(f"Loaded checkpoint from {self.checkpoint_path} (Processed {len(self.state['processed_channel_ids'])} channels).")
            except Exception as e:
                logger.warning(f"Failed to load checkpoint from {self.checkpoint_path}: {e}")

    def save(self):
        """Persists current state to JSON atomically."""
        self.state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.checkpoint_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
        tmp_path.replace(self.checkpoint_path)

    def is_channel_processed(self, channel_id: str) -> bool:
        return channel_id in self.state["processed_channel_ids"]

    def mark_channel_processed(self, channel_id: str, is_unconfirmed: bool = False):
        if channel_id not in self.state["processed_channel_ids"]:
            self.state["processed_channel_ids"].append(channel_id)
        if is_unconfirmed and channel_id not in self.state["unconfirmed_channel_ids"]:
            self.state["unconfirmed_channel_ids"].append(channel_id)

    def mark_source_completed(self, source_name: str, count: int, metadata: Optional[Dict[str, Any]] = None):
        self.state["completed_sources"][source_name] = {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "count": count,
            "metadata": metadata or {}
        }
        self.save()

    def log_inaccessible_source(self, source_name: str, url: str, reason: str, status_code: Optional[int] = None):
        entry = {
            "source_name": source_name,
            "url": url,
            "reason": reason,
            "status_code": status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        # Avoid duplicate logs
        if not any(x["source_name"] == source_name and x["url"] == url for x in self.state["inaccessible_sources"]):
            self.state["inaccessible_sources"].append(entry)
            self.save()

    def mark_video_catalog_completed(self, channel_id: str):
        if channel_id not in self.state["video_catalog_completed_channels"]:
            self.state["video_catalog_completed_channels"].append(channel_id)
            self.save()

    def is_video_catalog_completed(self, channel_id: str) -> bool:
        return channel_id in self.state["video_catalog_completed_channels"]
