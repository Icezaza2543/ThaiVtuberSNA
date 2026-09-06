"""
Thai VTuber Audience Network (SNA)
Parquet Storage Manager

Handles partitioning, schema enforcement, and writing of viewer presence events
into compressed Apache Parquet files.
File layout: data/events/{year}/{month}/{video_id}.parquet
"""
import logging
import re
import os
import uuid
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

        for event in events:
            if event.get("source_type") not in {"live_chat", "comment"}:
                raise ValueError("Explicit source_type live_chat or comment required")
            if not re.fullmatch(r"[A-Za-z0-9_-]+", event.get("video_id", "")):
                raise ValueError("Invalid video_id")
        if len({e["video_id"] for e in events}) != 1:
            raise ValueError("A write must contain exactly one video")
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

        # Separate collection batches by source_type while ensuring idempotency.
        # Naming by {video_id}_{source_type}.parquet prevents comment and live_chat collisions
        # while enabling deterministic reconciliation without appearance inflation.
        target_path = target_path.with_name(f"{video_id}_{first_event['source_type']}.parquet")
        
        # If target file already exists for this video and source, reconcile idempotently
        if target_path.exists():
            try:
                existing_table = pq.read_table(target_path)
                existing_rows = existing_table.to_pylist()
                
                # Index existing records by viewer_hash
                reconciled: Dict[str, Dict[str, Any]] = {}
                for row in existing_rows:
                    vh = row.get("viewer_hash")
                    if not vh:
                        continue
                    reconciled[vh] = {
                        "viewer_hash": vh,
                        "vtuber_channel_id": row.get("vtuber_channel_id", first_event["vtuber_channel_id"]),
                        "video_id": video_id,
                        "first_seen": str(row.get("first_seen") or row.get("timestamp", "")),
                        "last_seen": str(row.get("last_seen") or row.get("timestamp", "")),
                        "appearances": int(row.get("appearances", 1)),
                        "source_type": str(row.get("source_type", first_event["source_type"]))
                    }
                
                # Merge new events
                for e in events:
                    vh = e["viewer_hash"]
                    e_first = str(e.get("first_seen") or e.get("timestamp", ""))
                    e_last = str(e.get("last_seen") or e.get("timestamp", ""))
                    e_app = int(e.get("appearances", 1))
                    
                    if vh in reconciled:
                        # Reconcile timestamps
                        curr = reconciled[vh]
                        if e_first and (not curr["first_seen"] or e_first < curr["first_seen"]):
                            curr["first_seen"] = e_first
                        if e_last and (not curr["last_seen"] or e_last > curr["last_seen"]):
                            curr["last_seen"] = e_last
                        # For snapshot sources (e.g. comments), take max appearances to avoid polling inflation
                        if first_event["source_type"] == "comment":
                            curr["appearances"] = max(curr["appearances"], e_app)
                        else:
                            curr["appearances"] = max(curr["appearances"], e_app)
                    else:
                        reconciled[vh] = {
                            "viewer_hash": vh,
                            "vtuber_channel_id": e["vtuber_channel_id"],
                            "video_id": video_id,
                            "first_seen": e_first,
                            "last_seen": e_last,
                            "appearances": e_app,
                            "source_type": e.get("source_type", first_event["source_type"])
                        }
                
                # Reconstruct table from reconciled dictionary
                merged_events = list(reconciled.values())
                arrays = {
                    "viewer_hash": [m["viewer_hash"] for m in merged_events],
                    "vtuber_channel_id": [m["vtuber_channel_id"] for m in merged_events],
                    "video_id": [m["video_id"] for m in merged_events],
                    "first_seen": [m["first_seen"] for m in merged_events],
                    "last_seen": [m["last_seen"] for m in merged_events],
                    "appearances": [m["appearances"] for m in merged_events],
                    "source_type": [m["source_type"] for m in merged_events]
                }
                table = pa.Table.from_pydict(arrays, schema=AGGREGATED_SCHEMA)
                is_aggregated = True
            except Exception as e:
                logger.warning(f"Could not reconcile existing partition {target_path}: {e}; overwriting atomically")

        temporary = target_path.with_suffix(".tmp")
        try:
            pq.write_table(table, temporary, compression="snappy")
            os.replace(temporary, target_path)
        finally:
            temporary.unlink(missing_ok=True)
        logger.info(f"Saved {len(events)} {'aggregated' if is_aggregated else 'raw'} records to {target_path}")
        return target_path

    def get_all_parquet_paths(self) -> List[Path]:
        """Finds all Parquet event files under base_dir."""
        return list(self.base_dir.glob("*/*/*.parquet"))

    def migrate_legacy_partitions(self) -> int:
        """
        Explicit testable migration:
        Finds legacy UUID-named files ({video_id}-{uuid}.parquet), merges their records
        idempotently into deterministic source partitions ({video_id}_{source_type}.parquet),
        and removes the redundant legacy files.
        """
        migrated_count = 0
        all_files = self.get_all_parquet_paths()
        
        for p in all_files:
            # Check if file has legacy hyphen-uuid pattern (e.g. VID-75b8e239e199...)
            # but is not a deterministic source partition ending in _comment or _live_chat
            stem = p.stem
            if "-" in stem and not (stem.endswith("_comment") or stem.endswith("_live_chat")):
                try:
                    table = pq.read_table(p)
                    rows = table.to_pylist()
                    if rows:
                        # Normalize and write into deterministic partition
                        self.write_events(rows)
                    # Once merged safely into deterministic partition, remove legacy file
                    p.unlink(missing_ok=True)
                    migrated_count += 1
                    logger.info(f"Migrated legacy partition {p.name} into deterministic source partition.")
                except Exception as e:
                    logger.error(f"Error migrating legacy file {p}: {e}")

        return migrated_count
