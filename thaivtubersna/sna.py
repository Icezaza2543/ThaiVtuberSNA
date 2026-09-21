"""
Step 3 — SNA
============
Computes pairwise audience overlap directly from DuckDB interactions.

Strong overlap means the same viewer appeared in at least 2 distinct videos
for both creators. Source-specific strong metrics apply the same rule to
live_chat or comment interactions separately.
"""
from __future__ import annotations

import logging

from .store import DB_PATH, connect, get_state, set_state, uid, upsert, utc_now

logger = logging.getLogger(__name__)

MIN_SHARED = 1
STRONG_VIDEO_THRESHOLD = 2

_OVERLAP_SQL = """
WITH
shared_viewers AS (
    SELECT viewer_hash
    FROM interactions
    WHERE viewer_hash IS NOT NULL
      AND trim(viewer_hash) <> ''
      AND creator_id IS NOT NULL
    GROUP BY viewer_hash
    HAVING COUNT(DISTINCT creator_id) >= 2
),
any_presence AS (
    SELECT
        i.creator_id,
        i.viewer_hash,
        COUNT(DISTINCT i.video_id) AS video_count
    FROM interactions i
    JOIN shared_viewers s ON i.viewer_hash = s.viewer_hash
    GROUP BY i.creator_id, i.viewer_hash
),
any_pairs AS (
    SELECT
        a.creator_id AS creator_a,
        b.creator_id AS creator_b,
        COUNT(*) AS shared_any,
        SUM(
            CASE
                WHEN a.video_count >= ? AND b.video_count >= ? THEN 1
                ELSE 0
            END
        ) AS strong_shared_any
    FROM any_presence a
    JOIN any_presence b
      ON a.viewer_hash = b.viewer_hash
     AND a.creator_id < b.creator_id
    GROUP BY a.creator_id, b.creator_id
),
source_presence AS (
    SELECT
        i.creator_id,
        i.viewer_hash,
        i.source_type,
        COUNT(DISTINCT i.video_id) AS video_count
    FROM interactions i
    JOIN shared_viewers s ON i.viewer_hash = s.viewer_hash
    WHERE i.source_type IN ('live_chat', 'comment')
    GROUP BY i.creator_id, i.viewer_hash, i.source_type
),
source_pairs AS (
    SELECT
        a.creator_id AS creator_a,
        b.creator_id AS creator_b,
        a.source_type,
        COUNT(*) AS shared_source,
        SUM(
            CASE
                WHEN a.video_count >= ? AND b.video_count >= ? THEN 1
                ELSE 0
            END
        ) AS strong_shared_source
    FROM source_presence a
    JOIN source_presence b
      ON a.viewer_hash = b.viewer_hash
     AND a.source_type = b.source_type
     AND a.creator_id < b.creator_id
    GROUP BY a.creator_id, b.creator_id, a.source_type
),
source_agg AS (
    SELECT
        creator_a,
        creator_b,
        MAX(CASE WHEN source_type = 'live_chat' THEN shared_source ELSE 0 END) AS shared_live_chat,
        MAX(CASE WHEN source_type = 'comment' THEN shared_source ELSE 0 END) AS shared_comments,
        MAX(CASE WHEN source_type = 'live_chat' THEN strong_shared_source ELSE 0 END) AS strong_shared_live_chat,
        MAX(CASE WHEN source_type = 'comment' THEN strong_shared_source ELSE 0 END) AS strong_shared_comments
    FROM source_pairs
    GROUP BY creator_a, creator_b
)
SELECT
    p.creator_a,
    p.creator_b,
    CAST(p.shared_any AS INTEGER) AS shared_any,
    CAST(COALESCE(s.shared_live_chat, 0) AS INTEGER) AS shared_live_chat,
    CAST(COALESCE(s.shared_comments, 0) AS INTEGER) AS shared_comments,
    CAST(p.strong_shared_any AS INTEGER) AS strong_shared_any,
    CAST(COALESCE(s.strong_shared_live_chat, 0) AS INTEGER) AS strong_shared_live_chat,
    CAST(COALESCE(s.strong_shared_comments, 0) AS INTEGER) AS strong_shared_comments
FROM any_pairs p
LEFT JOIN source_agg s USING (creator_a, creator_b)
WHERE p.shared_any >= ?
ORDER BY p.shared_any DESC, p.creator_a, p.creator_b
"""

_AUDIENCE_SQL = """
SELECT creator_id, COUNT(DISTINCT viewer_hash) AS unique_viewers
FROM interactions
WHERE viewer_hash IS NOT NULL AND trim(viewer_hash) <> ''
GROUP BY creator_id
"""


def _interaction_stats(con) -> tuple[int, str | None]:
    row = con.execute(
        "SELECT COUNT(*), CAST(MAX(observed_at) AS VARCHAR) FROM interactions"
    ).fetchone()
    return int(row[0]), row[1]


def compute_pairwise_overlap(db_path=None) -> int:
    """Recompute fresh overlap edges from DuckDB interactions."""
    path = db_path or DB_PATH
    threshold = STRONG_VIDEO_THRESHOLD
    now = utc_now()

    with connect(path) as con:
        interaction_count, _ = _interaction_stats(con)
        if interaction_count == 0:
            logger.info("sna: no interactions yet; preserving legacy_seed edges")
            return 0

        rows = con.execute(
            _OVERLAP_SQL,
            [threshold, threshold, threshold, threshold, MIN_SHARED],
        ).fetchall()
        audience = {
            creator_id: n
            for creator_id, n in con.execute(_AUDIENCE_SQL).fetchall()
        }

        # Fresh SNA results are authoritative for pairs derived from interactions.
        con.execute("DELETE FROM network_edges WHERE calculation_source = 'live_interactions'")

        written = 0
        for (
            creator_a,
            creator_b,
            shared_any,
            shared_live_chat,
            shared_comments,
            strong_shared_any,
            strong_shared_live_chat,
            strong_shared_comments,
        ) in rows:
            n_a = audience.get(creator_a, shared_any)
            n_b = audience.get(creator_b, shared_any)
            union = n_a + n_b - shared_any
            jaccard = shared_any / union if union > 0 else None
            smaller = min(n_a, n_b)
            simpson = shared_any / smaller if smaller > 0 else None

            upsert(
                con,
                "network_edges",
                {
                    "id": uid("edge", f"{creator_a}:{creator_b}"),
                    "creator_a": creator_a,
                    "creator_b": creator_b,
                    "shared_any": shared_any,
                    "shared_live_chat": shared_live_chat,
                    "shared_comments": shared_comments,
                    "strong_shared_any": strong_shared_any,
                    "strong_shared_live_chat": strong_shared_live_chat,
                    "strong_shared_comments": strong_shared_comments,
                    "jaccard": jaccard,
                    "simpson": simpson,
                    "agency_a": None,
                    "agency_b": None,
                    "calculated_at": now,
                    "calculation_source": "live_interactions",
                },
            )
            written += 1

        interaction_count, interaction_max = _interaction_stats(con)
        set_state(con, "last_sna_at", now)
        set_state(con, "last_sna_interaction_count", interaction_count)
        set_state(con, "last_sna_interaction_max", interaction_max)

    logger.info("sna: wrote %d live interaction edges", written)
    return written


def recalculate_if_needed(db_path=None) -> dict:
    """Recalculate only when the interactions table has changed."""
    path = db_path or DB_PATH

    with connect(path) as con:
        interaction_count, interaction_max = _interaction_stats(con)
        if interaction_count == 0:
            edges = con.execute("SELECT COUNT(*) FROM network_edges").fetchone()[0]
            return {"skipped": True, "reason": "no_interactions", "edges": edges}

        last_count = int(get_state(con, "last_sna_interaction_count", -1) or -1)
        last_max = get_state(con, "last_sna_interaction_max")

    if interaction_count == last_count and interaction_max == last_max:
        return {
            "skipped": True,
            "reason": "interactions_unchanged",
            "edges": _edge_count(path),
        }

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
        max_shared = con.execute("SELECT MAX(shared_any) FROM network_edges").fetchone()[0] or 0
        last_calc = con.execute("SELECT MAX(calculated_at) FROM network_edges").fetchone()[0]
        unique_creators = con.execute(
            """
            SELECT COUNT(DISTINCT creator_id)
            FROM (
                SELECT creator_a AS creator_id FROM network_edges
                UNION ALL
                SELECT creator_b AS creator_id FROM network_edges
            )
            """
        ).fetchone()[0]
        interactions = con.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        live_edges = con.execute(
            "SELECT COUNT(*) FROM network_edges WHERE calculation_source = 'live_interactions'"
        ).fetchone()[0]
        seed_edges = con.execute(
            "SELECT COUNT(*) FROM network_edges WHERE calculation_source = 'legacy_seed'"
        ).fetchone()[0]

    return {
        "total_edges": total_edges,
        "live_edges": live_edges,
        "legacy_seed_edges": seed_edges,
        "max_shared_viewers": max_shared,
        "unique_creators_in_network": unique_creators,
        "interaction_rows": interactions,
        "last_calculated_at": last_calc,
    }


def run(db_path=None) -> dict:
    result = recalculate_if_needed(db_path)
    return {"recalculate": result, "summary": summary(db_path)}
