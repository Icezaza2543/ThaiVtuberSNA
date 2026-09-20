"""
Step 2 — REVIEW
===============
Processes the evidence queue: accepts / rejects candidates and promotes
them into verified accounts linked to personas.

Core rules (enforced here, NOT relaxed):
  - First-party public evidence only for account_links and persona verification.
  - New persona = new draft. No auto-merge from name/handle similarity.
  - Thai relation + virtual presentation must be separately confirmed.

Entry points used by the worker:
    review.process_pending(path)     — apply pending JSON change files
    review.queue_status(path)        — summary of what needs attention
    review.apply_change(con, change) — apply a validated change dict
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .store import (
    DB_PATH, PLATFORMS, connect, count, fetch_all,
    uid, upsert, utc_now, get_state, set_state,
)

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]

# Tables that appear in change files; insertion order respects FK constraints.
CHANGE_TABLE_ORDER = (
    "evidence",
    "personas",
    "accounts",
    "account_links",
    "lifecycle_events",
    "activity_observations",
    "affiliations",
    "continuity_links",
    "discovery_runs",
    "candidates",
    "discovery_hits",
    "legacy_claims",
    "review_queue",
)

ALLOWED_TABLES = set(CHANGE_TABLE_ORDER)

# ── Validation helpers ───────────────────────────────────────────────────────

def _public_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"Evidence URLs must be public HTTPS: {value!r}")


def _validate_change(change: dict) -> None:
    """Raise ValueError if the change file has structural problems."""
    if not isinstance(change, dict):
        raise ValueError("Change file must be a JSON object")
    unknown = set(change) - ALLOWED_TABLES
    if unknown:
        raise ValueError(f"Unknown tables in change file: {sorted(unknown)}")
    for table, rows in change.items():
        if not isinstance(rows, list):
            raise ValueError(f"{table}: must be a list of row dicts")
        for row in rows:
            if not isinstance(row, dict) or "id" not in row:
                raise ValueError(f"{table}: every row must have an 'id' field")
            if not row["id"] or not isinstance(row["id"], str):
                raise ValueError(f"{table}: id must be a non-empty string")


# ── Apply a change dict ──────────────────────────────────────────────────────

def apply_change(con, change: dict, *, dry_run: bool = False) -> dict:
    """
    Validate and apply a change dict to DuckDB.

    Each table's list is upserted in dependency order.
    If dry_run=True the changes are shown but NOT committed.

    Returns a summary: {'ok': True, 'counts': {'added': N, 'updated': N}}.
    """
    _validate_change(change)

    counts: dict[str, int] = {"added": 0, "updated": 0, "unchanged": 0}
    changes_detail: list[dict] = []

    for table in CHANGE_TABLE_ORDER:
        rows = change.get(table, [])
        for row in rows:
            existing = con.execute(
                f"SELECT * FROM {table} WHERE id = ?", [row["id"]]
            ).fetchone()
            if existing is None:
                action = "added"
            else:
                cols = [d[0] for d in con.description]
                existing_dict = dict(zip(cols, existing))
                if all(existing_dict.get(k) == v for k, v in row.items()):
                    counts["unchanged"] += 1
                    continue
                action = "updated"
            counts[action] += 1
            changes_detail.append({"table": table, "id": row["id"], "action": action})
            if not dry_run:
                upsert(con, table, row)

    return {
        "ok": True,
        "dry_run": dry_run,
        "counts": counts,
        "changes": changes_detail,
    }


# ── Process pending review files ─────────────────────────────────────────────

def process_pending(db_path=None) -> dict:
    """
    Apply all JSON files in reviews/pending/ that have not yet been applied.

    Tracks applied files via worker_state so the same file is never re-applied.
    After successful apply the file is moved to reviews/applied/.
    """
    from .store import DB_PATH
    path = db_path or DB_PATH

    pending_dir = ROOT / "reviews" / "pending"
    applied_dir = ROOT / "reviews" / "applied"
    applied_dir.mkdir(parents=True, exist_ok=True)

    if not pending_dir.exists():
        return {"pending": 0, "applied": 0, "errors": []}

    review_files = sorted(pending_dir.glob("*.json"))
    applied = 0
    errors = []

    for review_file in review_files:
        file_key = f"applied_review:{review_file.name}"
        with connect(path) as con:
            already = get_state(con, file_key)
        if already:
            continue  # already applied in a previous run

        logger.info("Applying review file: %s", review_file.name)
        try:
            change = json.loads(review_file.read_text(encoding="utf-8"))
            with connect(path) as con:
                result = apply_change(con, change)
                set_state(con, file_key, {"applied_at": utc_now(), "counts": result["counts"]})
            # Move to applied/
            dest = applied_dir / review_file.name
            review_file.rename(dest)
            applied += 1
            logger.info(
                "Applied %s: +%d added, ~%d updated",
                review_file.name,
                result["counts"]["added"],
                result["counts"]["updated"],
            )
        except Exception as exc:
            msg = f"{review_file.name}: {exc}"
            logger.error("Review apply failed: %s", msg)
            errors.append(msg)

    with connect(path) as con:
        set_state(con, "last_review_at", utc_now())

    return {
        "pending_files_found": len(review_files),
        "applied": applied,
        "errors": errors,
    }


# ── Queue status ─────────────────────────────────────────────────────────────

def _queue_status_from_con(con) -> dict:
    total_candidates = con.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    pending_candidates = con.execute(
        "SELECT COUNT(*) FROM candidates WHERE review_status = 'needs_evidence'"
    ).fetchone()[0]
    verified_candidates = con.execute(
        "SELECT COUNT(*) FROM candidates WHERE review_status = 'verified'"
    ).fetchone()[0]
    open_queue = con.execute(
        "SELECT COUNT(*) FROM review_queue WHERE status = 'open'"
    ).fetchone()[0]
    verified_personas = con.execute(
        "SELECT COUNT(*) FROM personas WHERE review_status = 'verified'"
    ).fetchone()[0]
    total_accounts = con.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]

    pending_reviews_dir = ROOT / "reviews" / "pending"
    pending_files = (
        len(list(pending_reviews_dir.glob("*.json")))
        if pending_reviews_dir.exists() else 0
    )

    return {
        "verified_personas": verified_personas,
        "total_accounts": total_accounts,
        "candidates": {
            "total": total_candidates,
            "needs_evidence": pending_candidates,
            "verified": verified_candidates,
        },
        "review_queue_open": open_queue,
        "pending_review_files": pending_files,
    }


def queue_status(db_path=None) -> dict:
    """
    Return a summary of outstanding work for human reviewers.
    Does not change any data. Accepts a connection or path.
    """
    if hasattr(db_path, "execute"):
        return _queue_status_from_con(db_path)
    from .store import DB_PATH
    path = db_path or DB_PATH
    with connect(path) as con:
        return _queue_status_from_con(con)


def run(db_path=None) -> dict:
    """Apply pending review files and return queue status."""
    r = process_pending(db_path)
    q = queue_status(db_path)
    return {"process": r, "queue": q}
