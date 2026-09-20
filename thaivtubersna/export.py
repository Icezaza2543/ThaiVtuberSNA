"""
Step 4 — EXPORT
===============
Exports verified registry data as CSV files for ThaiVtuberMaster.

Outputs (all read directly from DuckDB):
  VTUBERS.csv           — verified YouTube accounts linked to personas
  NETWORK_RESULT.csv    — pairwise audience-overlap network edges
  TIKTOK_VERIFIED.csv   — verified TikTok accounts
  TWITCH_VERIFIED.csv   — verified Twitch accounts
  ANALYTICS_METRICS.csv — account-level subscriber/view metrics

Entry points used by the worker:
    export.run_if_changed(output_dir, db_path)
    export.export_all(output_dir, db_path)
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from .store import DB_PATH, connect, get_state, set_state, utc_now

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / "export"

# ── CSV writers ──────────────────────────────────────────────────────────────

def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# ── Export functions ─────────────────────────────────────────────────────────

def export_vtubers(con, output_file: Path) -> int:
    """VTUBERS.csv — YouTube accounts with a verified persona link."""
    # Join accounts ← account_links ← personas
    rows_raw = con.execute("""
        SELECT
            a.platform_id   AS channel_id,
            a.handle        AS handle,
            p.canonical_name AS name,
            a.name          AS raw_name,
            af.organization AS agency,
            p.review_status AS persona_status,
            al.reviewed_at  AS last_verified,
            p.id            AS persona_id
        FROM accounts a
        JOIN account_links al ON al.account_id = a.id AND al.review_status = 'verified'
        JOIN personas p       ON p.id = al.persona_id AND p.review_status = 'verified'
        LEFT JOIN (
            SELECT persona_id, organization,
                   ROW_NUMBER() OVER (PARTITION BY persona_id ORDER BY id) AS rn
            FROM affiliations WHERE review_status = 'verified'
        ) af ON af.persona_id = p.id AND af.rn = 1
        WHERE a.platform = 'youtube'
        ORDER BY LOWER(COALESCE(p.canonical_name, a.name))
    """).fetchall()
    cols = [d[0] for d in con.description]
    rows = []
    for r in rows_raw:
        d = dict(zip(cols, r))
        rows.append({
            "channel_id": d["channel_id"],
            "handle": d["handle"] or "",
            "name": d["name"] or d["raw_name"],
            "subscriber_count": 0,  # not stored in registry; filled by collect step later
            "agency": d["agency"] or "Independent",
            "status": "ACCEPT",
            "last_activity": "",
            "last_collected": d["last_verified"] or "",
            "persona_id": d["persona_id"],
        })
    fieldnames = ["channel_id", "handle", "name", "subscriber_count",
                  "agency", "status", "last_activity", "last_collected", "persona_id"]
    return _write_csv(output_file, fieldnames, rows)


def export_network(con, output_file: Path) -> int:
    """NETWORK_RESULT.csv — pairwise audience-overlap edges."""
    rows_raw = con.execute("""
        SELECT
            ne.creator_a    AS channel_a_id,
            ne.creator_b    AS channel_b_id,
            ne.shared_any,
            ne.strong_shared_any,
            ne.calculated_at,
            ne.agency_a,
            ne.agency_b,
            pa.name         AS name_a,
            pb.name         AS name_b
        FROM network_edges ne
        LEFT JOIN accounts pa ON pa.platform_id = ne.creator_a AND pa.platform = 'youtube'
        LEFT JOIN accounts pb ON pb.platform_id = ne.creator_b AND pb.platform = 'youtube'
        WHERE ne.shared_any > 0
        ORDER BY ne.shared_any DESC
    """).fetchall()
    cols = [d[0] for d in con.description]
    rows = []
    for r in rows_raw:
        d = dict(zip(cols, r))
        rows.append({
            "Channel A": d["name_a"] or d["channel_a_id"],
            "Agency A": d["agency_a"] or "Independent",
            "Channel B": d["name_b"] or d["channel_b_id"],
            "Agency B": d["agency_b"] or "Independent",
            "Shared Viewers": d["shared_any"],
            "Strong Shared": d["strong_shared_any"],
            "Calculated At": d["calculated_at"],
        })
    fieldnames = ["Channel A", "Agency A", "Channel B", "Agency B",
                  "Shared Viewers", "Strong Shared", "Calculated At"]
    return _write_csv(output_file, fieldnames, rows)


def export_platform_verified(con, platform: str, output_file: Path) -> int:
    """TIKTOK_VERIFIED.csv or TWITCH_VERIFIED.csv."""
    rows_raw = con.execute("""
        SELECT
            a.handle        AS handle,
            p.canonical_name AS persona_name,
            a.platform_id   AS platform_id,
            a.url           AS url,
            p.id            AS persona_id,
            al.reviewed_at  AS observed_at
        FROM accounts a
        JOIN account_links al ON al.account_id = a.id AND al.review_status = 'verified'
        JOIN personas p       ON p.id = al.persona_id AND p.review_status = 'verified'
        WHERE a.platform = ?
        ORDER BY LOWER(a.handle)
    """, [platform]).fetchall()
    cols = [d[0] for d in con.description]
    rows = []
    for r in rows_raw:
        d = dict(zip(cols, r))
        rows.append({
            "handle": d["handle"] or "",
            "name": d["persona_name"] or d["handle"],
            "platform_id": d["platform_id"],
            "url": d["url"],
            "persona_name": d["persona_name"] or "",
            "persona_id": d["persona_id"],
            "observed_at": d["observed_at"] or "",
        })
    fieldnames = ["handle", "name", "platform_id", "url", "persona_name", "persona_id", "observed_at"]
    return _write_csv(output_file, fieldnames, rows)


def export_metrics(con, output_file: Path) -> int:
    """ANALYTICS_METRICS.csv — account-level metrics (subscriber counts if available)."""
    rows_raw = con.execute("""
        SELECT
            a.platform, a.platform_id, a.name,
            al.reviewed_at AS observed_at,
            a.url
        FROM accounts a
        JOIN account_links al ON al.account_id = a.id AND al.review_status = 'verified'
        WHERE a.platform = 'youtube'
        ORDER BY LOWER(a.name)
    """).fetchall()
    cols = [d[0] for d in con.description]
    rows = []
    for r in rows_raw:
        d = dict(zip(cols, r))
        rows.append({
            "platform": d["platform"],
            "platform_id": d["platform_id"],
            "name": d["name"],
            "scope": "reviewed_persona_link",
            "followers_or_subscribers": 0,
            "views": 0,
            "likes_received": "",
            "metric_time": "",
            "time_basis": "unknown",
            "observed_at": d["observed_at"] or utc_now(),
            "source": "ThaiVtuberSNA registry",
            "source_url": d["url"],
            "account_url": d["url"],
        })
    fieldnames = [
        "platform", "platform_id", "name", "scope",
        "followers_or_subscribers", "views", "likes_received",
        "metric_time", "time_basis", "observed_at",
        "source", "source_url", "account_url",
    ]
    return _write_csv(output_file, fieldnames, rows)


# ── Change detection ─────────────────────────────────────────────────────────

def _db_fingerprint(con) -> str:
    """Hash of key registry counts to detect changes since last export."""
    rows = con.execute("""
        SELECT
            (SELECT COUNT(*) FROM personas WHERE review_status='verified') AS vp,
            (SELECT COUNT(*) FROM accounts) AS acc,
            (SELECT COUNT(*) FROM network_edges) AS ne,
            (SELECT MAX(reviewed_at) FROM personas WHERE review_status='verified') AS last_rev
    """).fetchone()
    return hashlib.sha256(str(rows).encode()).hexdigest()[:16]


# ── Entry points ─────────────────────────────────────────────────────────────

def export_all(output_dir: Path | None = None, db_path=None) -> dict[str, int]:
    """Run all 5 exports. Returns a dict of {filename: row_count}."""
    out = output_dir or DEFAULT_OUTPUT
    path = db_path or DB_PATH

    with connect(path) as con:
        counts = {
            "VTUBERS.csv":           export_vtubers(con, out / "VTUBERS.csv"),
            "NETWORK_RESULT.csv":    export_network(con, out / "NETWORK_RESULT.csv"),
            "TIKTOK_VERIFIED.csv":   export_platform_verified(con, "tiktok", out / "TIKTOK_VERIFIED.csv"),
            "TWITCH_VERIFIED.csv":   export_platform_verified(con, "twitch", out / "TWITCH_VERIFIED.csv"),
            "ANALYTICS_METRICS.csv": export_metrics(con, out / "ANALYTICS_METRICS.csv"),
        }
        fingerprint = _db_fingerprint(con)
        set_state(con, "last_export_at", utc_now())
        set_state(con, "last_export_fingerprint", fingerprint)

    logger.info("export_all: wrote %d files to %s", len(counts), out)
    return counts


def run_if_changed(output_dir: Path | None = None, db_path=None) -> dict:
    """Export only if the registry has changed since the last export."""
    path = db_path or DB_PATH
    out = output_dir or DEFAULT_OUTPUT

    with connect(path) as con:
        current_fp = _db_fingerprint(con)
        last_fp = get_state(con, "last_export_fingerprint")

    if current_fp == last_fp:
        logger.info("export: no changes since last export; skipping")
        return {"skipped": True, "reason": "no_changes"}

    counts = export_all(out, path)
    total = sum(counts.values())
    logger.info("export: exported %d total rows across %d files", total, len(counts))
    return {"skipped": False, "files": counts, "total_rows": total}


def run(output_dir: Path | None = None, db_path=None) -> dict:
    """Main entry point: export if changed."""
    return run_if_changed(output_dir, db_path)
