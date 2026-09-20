"""
Step 3 — SNA (Social Network Analysis)
=======================================
Computes pairwise audience-overlap between verified Thai VTuber accounts.

The single question we answer: does VTuber A share viewers with VTuber B,
and how many / how strongly?

Metrics:
  shared_any          — viewers who appeared in both channels (any source)
  shared_live_chat    — live-chat-only overlap
  shared_comments     — comment-only overlap
  strong_shared_*     — viewers who appeared ≥ 3 times in both channels
  jaccard             — |A∩B| / |A∪B|
  simpson             — |A∩B| / min(|A|, |B|)

Data source: data/events/**/*.parquet  (gitignored, collected offline)
Fallback:    network_edges already in DuckDB (seeded from web/data.json)

Entry points used by the worker:
    sna.recalculate_if_needed(path)
    sna.compute_pairwise_overlap(path)
    sna.summary(path)
"""
from __future__ import annotations

import logging
from pathlib import Path

from .store import DB_PATH, connect, count, set_state, get_state, utc_now

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
EVENTS_DIR = ROOT / "data" / "events"

# Minimum shared viewers to include an edge in the output
MIN_SHARED = 1
# A viewer is "strong" if they appear in ≥ this many sessions per channel
STRONG_THRESHOLD = 3


# ── DuckDB-based overlap computation ─────────────────────────────────────────

_OVERLAP_SQL = """
WITH
presence AS (
    SELECT
        viewer_hash,
        vtuber_channel_id  AS channel,
        source_type,
        COALESCE(appearances, 1)  AS appearances
    FROM raw_events
    WHERE viewer_hash IS NOT NULL
      AND trim(viewer_hash) <> ''
      AND vtuber_channel_id IS NOT NULL
),
per_viewer_channel AS (
    SELECT channel, viewer_hash, source_type,
           SUM(appearances) AS total_appearances
    FROM presence
    GROUP BY channel, viewer_hash, source_type
),
pairs AS (
    SELECT
        LEAST(a.channel, b.channel)    AS creator_a,
        GREATEST(a.channel, b.channel) AS creator_b,
        a.viewer_hash,
        a.source_type  AS source_a,
        b.source_type  AS source_b,
        a.total_appearances AS app_a,
        b.total_appearances AS app_b
    FROM per_viewer_channel a
    JOIN per_viewer_channel b
      ON a.viewer_hash = b.viewer_hash
     AND a.channel < b.channel
)
SELECT
    creator_a,
    creator_b,
    COUNT(DISTINCT viewer_hash)                          AS shared_any,
    COUNT(DISTINCT CASE WHEN source_a='live_chat' AND source_b='live_chat'
                        THEN viewer_hash END)             AS shared_live_chat,
    COUNT(DISTINCT CASE WHEN source_a='comment' AND source_b='comment'
                        THEN viewer_hash END)             AS shared_comments,
    COUNT(DISTINCT CASE WHEN app_a >= ? AND app_b >= ?
                        THEN viewer_hash END)             AS strong_shared_any,
    COUNT(DISTINCT CASE WHEN source_a='live_chat' AND source_b='live_chat'
                             AND app_a >= ? AND app_b >= ?
                        THEN viewer_hash END)             AS strong_shared_live_chat,
    COUNT(DISTINCT CASE WHEN source_a='comment' AND source_b='comment'
                             AND app_a >= ? AND app_b >= ?
                        THEN viewer_hash END)             AS strong_shared_comments
FROM pairs
GROUP BY creator_a, creator_b
HAVING shared_any >= ?
"""

_AUDIENCE_SQL = """
SELECT channel, COUNT(DISTINCT viewer_hash) AS unique_viewers
FROM (
    SELECT vtuber_channel_id AS channel, viewer_hash
    FROM raw_events
    WHERE viewer_hash IS NOT NULL AND trim(viewer_hash) <> ''
)
GROUP BY channel
"""


def _has_parquet_data() -> bool:
    return EVENTS_DIR.exists() and any(EVENTS_DIR.rglob("*.parquet"))


def _create_view(con) -> bool:
    """Create raw_events view over Parquet files. Returns True if data exists."""
    import duckdb
    if not _has_parquet_data():
        return False
    pattern = str(EVENTS_DIR / "**" / "*.parquet").replace("\\", "/")
    con.execute(
        f"CREATE OR REPLACE VIEW raw_events AS "
        f"SELECT * FROM read_parquet('{pattern}', union_by_name=True)"
    )
    return True


def compute_pairwise_overlap(db_path=None) -> int:
    """
    Compute all pairwise viewer-overlap edges from Parquet event files.
    Upserts results into network_edges table.
    Returns number of edges written.
    """
    from .store import upsert, uid
    path = db_path or DB_PATH

    if not _has_parquet_data():
        logger.info("sna: no Parquet event files found in %s; skipping computation", EVENTS_DIR)
        return 0

    import duckdb

    # Use a separate in-process DuckDB connection to read Parquet
    analytics_con = duckdb.connect(":memory:")
    if not _create_view(analytics_con):
        return 0

    st = STRONG_THRESHOLD
    rows = analytics_con.execute(
        _OVERLAP_SQL,
        [st, st, st, st, st, st, MIN_SHARED]
    ).fetchall()
    analytics_con.close()

    if not rows:
        return 0

    # Compute per-channel audience sizes for Jaccard / Simpson
    audience_con = duckdb.connect(":memory:")
    _create_view(audience_con)
    audience_rows = audience_con.execute(_AUDIENCE_SQL).fetchall()
    audience_con.close()
    audience = {ch: n for ch, n in audience_rows}

    now = utc_now()
    written = 0
    with connect(path) as con:
        for row in rows:
            (a, b, shared_any, shared_live, shared_comm,
             strong_any, strong_live, strong_comm) = row
            n_a = audience.get(a, shared_any)
            n_b = audience.get(b, shared_any)
            union = n_a + n_b - shared_any
            jaccard = shared_any / union if union > 0 else None
            simpson = shared_any / min(n_a, n_b) if min(n_a, n_b) > 0 else None
            edge_id = uid("edge", a + ":" + b)
            upsert(con, "network_edges", {
                "id": edge_id,
                "creator_a": a, "creator_b": b,
                "shared_any": shared_any,
                "shared_live_chat": shared_live,
                "shared_comments": shared_comm,
                "strong_shared_any": strong_any,
                "strong_shared_live_chat": strong_live,
                "strong_shared_comments": strong_comm,
                "jaccard": jaccard,
                "simpson": simpson,
                "agency_a": None,
                "agency_b": None,
                "calculated_at": now,
            })
            written += 1
        set_state(con, "last_sna_at", now)

    logger.info("sna: wrote %d network edges", written)
    return written


def recalculate_if_needed(db_path=None) -> dict:
    """
    Recalculate SNA only if new event data is available since the last run.
    Returns a summary dict.
    """
    path = db_path or DB_PATH

    if not _has_parquet_data():
        logger.info("sna: no Parquet data; keeping existing %d seeded edges", _edge_count(path))
        return {"skipped": True, "reason": "no_parquet_data", "edges": _edge_count(path)}

    # Check if Parquet files are newer than last SNA run
    with connect(path) as con:
        last_sna = get_state(con, "last_sna_at")

    parquet_files = list(EVENTS_DIR.rglob("*.parquet"))
    if last_sna and parquet_files:
        import os
        latest_parquet = max(os.path.getmtime(f) for f in parquet_files)
        from datetime import datetime, timezone
        last_ts = datetime.fromisoformat(last_sna.replace("Z", "+00:00")).timestamp()
        if latest_parquet <= last_ts:
            logger.info("sna: Parquet files unchanged since last run; skipping")
            return {"skipped": True, "reason": "data_unchanged", "edges": _edge_count(path)}

    edges = compute_pairwise_overlap(path)
    return {"skipped": False, "edges": edges}


def _edge_count(path) -> int:
    with connect(path) as con:
        return con.execute("SELECT COUNT(*) FROM network_edges").fetchone()[0]


def summary(db_path=None) -> dict:
    """Return SNA statistics without modifying anything."""
    path = db_path or DB_PATH
    with connect(path) as con:
        total_edges = con.execute("SELECT COUNT(*) FROM network_edges").fetchone()[0]
        max_shared = con.execute(
            "SELECT MAX(shared_any) FROM network_edges"
        ).fetchone()[0] or 0
        last_calc = con.execute(
            "SELECT MAX(calculated_at) FROM network_edges"
        ).fetchone()[0]
        unique_creators = con.execute(
            "SELECT COUNT(DISTINCT creator_a) + COUNT(DISTINCT creator_b) FROM network_edges"
        ).fetchone()[0]
    return {
        "total_edges": total_edges,
        "max_shared_viewers": max_shared,
        "unique_creators_in_network": unique_creators,
        "last_calculated_at": last_calc,
        "parquet_data_present": _has_parquet_data(),
    }


def run(db_path=None) -> dict:
    """Main entry point: recalculate if needed, return summary."""
    result = recalculate_if_needed(db_path)
    s = summary(db_path)
    return {"recalculate": result, "summary": s}
