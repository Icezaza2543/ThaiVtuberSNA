"""Deterministic, auditable incremental discovery checks.

Provides query-level freshness checks wired into the discovery orchestrator
to skip recently completed queries without hiding state or certifying identity claims.
Also provides library helpers for deterministic source content hashing.
"""

from datetime import datetime, timezone, timedelta
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union


def compute_content_hash(source: Union[str, bytes, Path]) -> str:
    """Compute deterministic SHA256 hex digest of source string, bytes, or file."""
    if isinstance(source, Path):
        return hashlib.sha256(source.read_bytes()).hexdigest()
    if isinstance(source, str):
        return hashlib.sha256(source.encode('utf-8')).hexdigest()
    return hashlib.sha256(source).hexdigest()


def get_last_run(db: Any, platform: str, query: str, method: str) -> Optional[Dict[str, Any]]:
    """Retrieve the most recent discovery run matching platform, query, and method."""
    cursor = db.execute(
        """
        SELECT id, platform, method, query, observed_at, stop_reason, pages, records_seen
        FROM discovery_runs
        WHERE platform = ? AND query = ? AND method = ?
        ORDER BY observed_at DESC
        LIMIT 1
        """,
        (platform, query, method),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return dict(row)


def is_source_unchanged(db: Any, source_url: str, current_hash: str) -> bool:
    """Check if the source URL has previously been observed with the identical content hash."""
    cursor = db.execute(
        """
        SELECT sha256
        FROM evidence
        WHERE url = ? AND sha256 IS NOT NULL
        ORDER BY observed_at DESC
        LIMIT 1
        """,
        (source_url,),
    )
    row = cursor.fetchone()
    if not row or not row["sha256"]:
        return False
    return row["sha256"] == current_hash


def should_skip_discovery(
    db: Any,
    *,
    platform: str,
    query: str,
    method: str,
    as_of: Optional[str] = None,
    freshness_days: int = 7,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Determine if a discovery query on a platform should be skipped under incremental mode.

    Returns:
        (should_skip: bool, reason: str, last_run: Optional[dict])
    """
    last_run = get_last_run(db, platform, query, method)
    if not last_run:
        return False, "no_previous_run", None

    if last_run["stop_reason"] not in ("completed", "import_complete"):
        return False, f"previous_run_{last_run['stop_reason']}", last_run

    ref_date = datetime.fromisoformat(as_of) if as_of else datetime.now(timezone.utc)
    try:
        last_obs = datetime.fromisoformat(last_run["observed_at"])
        if last_obs.tzinfo is None:
            last_obs = last_obs.replace(tzinfo=timezone.utc)
        if ref_date.tzinfo is None:
            ref_date = ref_date.replace(tzinfo=timezone.utc)
    except Exception:
        return False, "invalid_timestamp", last_run

    age = ref_date - last_obs
    if age < timedelta(days=freshness_days):
        return True, f"recently_checked_age_{age.days}d", last_run

    return False, f"stale_age_{age.days}d", last_run
