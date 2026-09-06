"""
Thai VTuber Audience Network (SNA)
Parquet Storage Manager

Handles partitioning, schema enforcement, and writing of viewer presence events
into compressed Apache Parquet files.
File layout: data/events/{year}/{month}/{video_id}.parquet
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import pyarrow as pa
import pyarrow.parquet as pq
from config.settings import EVENTS_DIR

logger = logging.getLogger(__name__)

# Standard PyArrow Schema for Presence Events
EVENT_SCHEMA = pa.schema([
    ("viewer_hash", pa.string()),
    ("vtuber_channel_id", pa.string()),
    ("video_id", pa.string()),
    ("timestamp", pa.string()),
    ("source_type", pa.string())
])

# Early Aggregated Session Schema (Per-video viewer presence)
AGGREGATED_SCHEMA = pa.schema([
    ("viewer_hash", pa.string()),
    ("vtuber_channel_id", pa.string()),
    ("video_id", pa.string()),
    ("first_seen", pa.string()),
    ("last_seen", pa.string()),
    ("appearances", pa.int64()),
    ("source_type", pa.string())
])


class ParquetStorageManager:
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or EVENTS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_partition_path(self, video_id: str, timestamp_str: str = None) -> Path:
        """Determines target path: data/events/YYYY/MM/{video_id}.parquet"""
        if timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except Exception:
                dt = datetime.utcnow()
        else:
            dt = datetime.utcnow()

        year_str = f"{dt.year:04d}"
        month_str = f"{dt.month:02d}"
        partition_dir = self.base_dir / year_str / month_str
        partition_dir.mkdir(parents=True, exist_ok=True)
        return partition_dir / f"{video_id}.parquet"

    def write_events(self, events: List[Dict[str, Any]]) -> Path:
        """
        Writes a list of event dictionaries to a partitioned Parquet file.
        Uses Snappy compression for maximum read performance and minimal disk footprint.
        """
        if not events:
            raise ValueError("No events provided to write.")

        first_event = events[0]
        video_id = first_event["video_id"]
        timestamp = first_event.get("timestamp") or first_event.get("first_seen")
        target_path = self.get_partition_path(video_id, timestamp)

        # Check if events are aggregated format or raw event format
        is_aggregated = "first_seen" in first_event and "appearances" in first_event
        if is_aggregated:
            arrays = {
                "viewer_hash": [e["viewer_hash"] for e in events],
                "vtuber_channel_id": [e["vtuber_channel_id"] for e in events],
                "video_id": [e["video_id"] for e in events],
                "first_seen": [str(e.get("first_seen", "")) for e in events],
                "last_seen": [str(e.get("last_seen", "")) for e in events],
                "appearances": [int(e.get("appearances", 1)) for e in events],
                "source_type": [str(e.get("source_type", "comment")) for e in events]
            }
            table = pa.Table.from_pydict(arrays, schema=AGGREGATED_SCHEMA)
        else:
            arrays = {
                "viewer_hash": [e["viewer_hash"] for e in events],
                "vtuber_channel_id": [e["vtuber_channel_id"] for e in events],
                "video_id": [e["video_id"] for e in events],
                "timestamp": [str(e.get("timestamp", "")) for e in events],
                "source_type": [str(e.get("source_type", "live_chat")) for e in events]
            }
            table = pa.Table.from_pydict(arrays, schema=EVENT_SCHEMA)

        pq.write_table(table, target_path, compression="snappy")
        logger.info(f"Saved {len(events)} {'aggregated' if is_aggregated else 'raw'} records to {target_path}")
        return target_path

    def get_all_parquet_paths(self) -> List[Path]:
        """Finds all Parquet event files under base_dir."""
        return list(self.base_dir.glob("*/*/*.parquet"))
