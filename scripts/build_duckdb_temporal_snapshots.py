"""
Phase T3 / PR-5: DuckDB Temporal Snapshot Engine
Builds canonical temporal interaction network slices across time windows (2020 -> 2026):

Schema:
NETWORK_SNAPSHOTS (
    window_type VARCHAR,            -- 'yearly', 'cumulative'
    window_start VARCHAR,           -- e.g. '2020-01-01'
    window_end VARCHAR,             -- e.g. '2020-12-31'
    vtuber_a VARCHAR,               -- channel_id A
    vtuber_b VARCHAR,               -- channel_id B (vtuber_a < vtuber_b)
    shared_any BIGINT,              -- unique viewers in both channels
    shared_comments BIGINT,         -- unique commenters in both
    shared_live_chat BIGINT,        -- unique live chatters in both
    strong_shared_any BIGINT,       -- viewers seen in >= 2 distinct videos on both
    strong_shared_comments BIGINT,  -- commenters seen in >= 2 videos on both
    strong_shared_live_chat BIGINT, -- live chatters seen in >= 2 streams on both
    jaccard_comments DOUBLE,        -- comments Jaccard similarity
    jaccard_live_chat DOUBLE,       -- live chat Jaccard similarity
    overlap_coefficient DOUBLE,     -- Szymkiewicz-Simpson overlap coeff
    size_a BIGINT,                  -- total unique audience for A in window
    size_b BIGINT,                  -- total unique audience for B in window
    coverage_a DOUBLE,              -- catalog coverage ratio for A
    coverage_b DOUBLE,              -- catalog coverage ratio for B
    calculated_at VARCHAR           -- UTC ISO timestamp
)

Exports:
- data/temporal/snapshots/network_snapshots.parquet
- web/data/temporal_snapshots.json
"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DuckDBTemporalEngine")

OUTPUT_DIR = DATA_DIR / "temporal" / "snapshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_PARQUET = OUTPUT_DIR / "network_snapshots.parquet"
WEB_SNAPSHOTS_JSON = BASE_DIR / "web" / "data" / "temporal_snapshots.json"
WEB_SNAPSHOTS_JSON.parent.mkdir(parents=True, exist_ok=True)

# Schema definition for Network Snapshots
NETWORK_SNAPSHOT_SCHEMA = pa.schema([
    ("window_type", pa.string()),
    ("window_start", pa.string()),
    ("window_end", pa.string()),
    ("vtuber_a", pa.string()),
    ("vtuber_b", pa.string()),
    ("shared_any", pa.int64()),
    ("shared_comments", pa.int64()),
    ("shared_live_chat", pa.int64()),
    ("strong_shared_any", pa.int64()),
    ("strong_shared_comments", pa.int64()),
    ("strong_shared_live_chat", pa.int64()),
    ("jaccard_comments", pa.float64()),
    ("jaccard_live_chat", pa.float64()),
    ("overlap_coefficient", pa.float64()),
    ("size_a", pa.int64()),
    ("size_b", pa.int64()),
    ("coverage_a", pa.float64()),
    ("coverage_b", pa.float64()),
    ("calculated_at", pa.string())
])

def collect_available_parquet_sources() -> List[str]:
    """Finds all available event/observation parquet files across temporal and legacy directories."""
    sources = []
    
    # 1. Temporal Pilot / Observations
    pilot_p = DATA_DIR / "temporal" / "pilot" / "temporal_comment_pilot.parquet"
    if pilot_p.exists():
        sources.append(str(pilot_p).replace("\\", "/"))
        
    for p in (DATA_DIR / "temporal" / "observations").rglob("*.parquet"):
        sources.append(str(p).replace("\\", "/"))
        
    # 2. Real Events (if any)
    for p in (DATA_DIR / "real" / "events").rglob("*.parquet"):
        sources.append(str(p).replace("\\", "/"))
        
    # 3. Events (live chat / comments from pilot)
    for p in (DATA_DIR / "events").rglob("*.parquet"):
        sources.append(str(p).replace("\\", "/"))
        
    return sources

def load_channel_coverage_map() -> Dict[str, float]:
    """Loads channel coverage percentages from T1 channel_coverage.parquet."""
    cov_path = DATA_DIR / "temporal" / "catalog" / "channel_coverage.parquet"
    if not cov_path.exists():
        return {}
    try:
        tbl = pq.read_table(cov_path)
        pyd = tbl.to_pylist()
        # Coverage metric: if termination is PLAYLIST_EXHAUSTED or CUTOFF_REACHED, coverage is 1.0 (100%)
        # If CAP_REACHED, ratio of covered span or 1.0
        cov_map = {}
        for r in pyd:
            cid = r.get("channel_id")
            term = r.get("termination_reason")
            if term in ("PLAYLIST_EXHAUSTED", "CUTOFF_REACHED"):
                cov_map[cid] = 1.0
            elif term == "CAP_REACHED":
                cov_map[cid] = 0.95
            else:
                cov_map[cid] = 0.5
        return cov_map
    except Exception as e:
        logger.warning(f"Could not load channel coverage: {e}")
        return {}

def main():
    logger.info("==========================================================")
    logger.info(" PHASE T3: DuckDB Temporal Snapshot Engine                ")
    logger.info("==========================================================")

    sources = collect_available_parquet_sources()
    logger.info(f"Found {len(sources)} Parquet observation sources.")
    if not sources:
        logger.error("No observation sources found! Run Phase T2 Pilot first.")
        sys.exit(1)

    cov_map = load_channel_coverage_map()
    logger.info(f"Loaded coverage stats for {len(cov_map)} channels.")

    con = duckdb.connect(":memory:")

    # Build canonical unified events view
    source_list_sql = ", ".join(f"'{s}'" for s in sources)
    logger.info(f"Registering Parquet union view from {len(sources)} files...")
    
    con.execute(f"""
        CREATE OR REPLACE VIEW unified_raw AS 
        SELECT * FROM read_parquet([{source_list_sql}], union_by_name=True)
    """)

    # Standardize column mappings across schema variants
    cols = {r[0] for r in con.execute("DESCRIBE unified_raw").fetchall()}
    
    inter_expr = "interaction_at" if "interaction_at" in cols else "NULL"
    pub_expr = "video_published_at" if "video_published_at" in cols else "NULL"
    first_seen_expr = "first_seen" if "first_seen" in cols else "NULL"
    timestamp_expr = "timestamp" if "timestamp" in cols else "NULL"
    source_expr = "source_type" if "source_type" in cols else "'comment'"

    con.execute(f"""
        CREATE OR REPLACE VIEW canonical_events AS
        WITH raw_cast AS (
            SELECT
                viewer_hash,
                vtuber_channel_id,
                COALESCE(video_id, 'vid_unknown') AS video_id,
                COALESCE({source_expr}, 'comment') AS source_type,
                COALESCE(
                    try_cast({inter_expr} AS TIMESTAMPTZ),
                    try_cast({first_seen_expr} AS TIMESTAMPTZ),
                    try_cast({pub_expr} AS TIMESTAMPTZ)
                ) AS raw_time,
                try_cast({pub_expr} AS TIMESTAMPTZ) AS video_published_at,
                try_cast({inter_expr} AS TIMESTAMPTZ) AS interaction_at
            FROM unified_raw
            WHERE viewer_hash IS NOT NULL AND viewer_hash != ''
              AND vtuber_channel_id IS NOT NULL AND vtuber_channel_id != ''
        )
        SELECT
            viewer_hash,
            vtuber_channel_id,
            video_id,
            source_type,
            video_published_at,
            interaction_at,
            CASE
                WHEN extract(year from raw_time) > 2500 THEN raw_time - INTERVAL 543 YEAR
                ELSE raw_time
            END AS event_time
        FROM raw_cast
    """)

    total_events = con.execute("SELECT COUNT(*) FROM canonical_events").fetchone()[0]
    logger.info(f"Canonical unified events loaded: {total_events:,} rows.")

    # Define time windows:
    # 1. Yearly: 2020 through 2026 YTD
    # 2. Cumulative: Through 2021, Through 2022, ... Through 2026 YTD
    # 3. All-time baseline
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    windows = [
        # Yearly windows
        {"type": "yearly", "start": "2020-01-01", "end": "2020-12-31 23:59:59"},
        {"type": "yearly", "start": "2021-01-01", "end": "2021-12-31 23:59:59"},
        {"type": "yearly", "start": "2022-01-01", "end": "2022-12-31 23:59:59"},
        {"type": "yearly", "start": "2023-01-01", "end": "2023-12-31 23:59:59"},
        {"type": "yearly", "start": "2024-01-01", "end": "2024-12-31 23:59:59"},
        {"type": "yearly", "start": "2025-01-01", "end": "2025-12-31 23:59:59"},
        {"type": "yearly", "start": "2026-01-01", "end": "2026-09-08 23:59:59"},
        
        # Cumulative windows (Evolution over time)
        {"type": "cumulative", "start": "2020-01-01", "end": "2021-12-31 23:59:59"},
        {"type": "cumulative", "start": "2020-01-01", "end": "2022-12-31 23:59:59"},
        {"type": "cumulative", "start": "2020-01-01", "end": "2023-12-31 23:59:59"},
        {"type": "cumulative", "start": "2020-01-01", "end": "2024-12-31 23:59:59"},
        {"type": "cumulative", "start": "2020-01-01", "end": "2025-12-31 23:59:59"},
        {"type": "cumulative", "start": "2020-01-01", "end": "2026-09-08 23:59:59"},

        # All-time window
        {"type": "all_time", "start": "2020-01-01", "end": "2026-09-08 23:59:59"}
    ]

    all_snapshot_records = []

    for w in windows:
        w_type = w["type"]
        w_start = w["start"]
        w_end = w["end"]

        query = f"""
            WITH filtered_events AS (
                SELECT * FROM canonical_events
                WHERE (event_time IS NULL OR (event_time >= '{w_start}' AND event_time <= '{w_end}'))
            ),
            viewer_channel_stats AS (
                SELECT
                    vtuber_channel_id,
                    viewer_hash,
                    COUNT(DISTINCT video_id) AS videos_seen,
                    COUNT(DISTINCT CASE WHEN source_type = 'live_chat' THEN video_id END) AS live_streams_seen,
                    COUNT(DISTINCT CASE WHEN source_type = 'comment' THEN video_id END) AS comment_videos_seen,
                    BOOL_OR(source_type = 'live_chat') AS in_live_chat,
                    BOOL_OR(source_type = 'comment') AS in_comment
                FROM filtered_events
                GROUP BY vtuber_channel_id, viewer_hash
            ),
            channel_totals AS (
                SELECT
                    vtuber_channel_id,
                    COUNT(DISTINCT viewer_hash) AS total_viewers,
                    COUNT(DISTINCT CASE WHEN in_live_chat THEN viewer_hash END) AS live_chat_viewers,
                    COUNT(DISTINCT CASE WHEN in_comment THEN viewer_hash END) AS comment_viewers
                FROM viewer_channel_stats
                GROUP BY vtuber_channel_id
            ),
            shared_pairs AS (
                SELECT
                    a.vtuber_channel_id AS vtuber_a,
                    b.vtuber_channel_id AS vtuber_b,
                    COUNT(DISTINCT a.viewer_hash) AS shared_any,
                    COUNT(DISTINCT CASE WHEN a.in_comment AND b.in_comment THEN a.viewer_hash END) AS shared_comments,
                    COUNT(DISTINCT CASE WHEN a.in_live_chat AND b.in_live_chat THEN a.viewer_hash END) AS shared_live_chat,
                    COUNT(DISTINCT CASE WHEN a.videos_seen >= 2 AND b.videos_seen >= 2 THEN a.viewer_hash END) AS strong_shared_any,
                    COUNT(DISTINCT CASE WHEN a.comment_videos_seen >= 2 AND b.comment_videos_seen >= 2 THEN a.viewer_hash END) AS strong_shared_comments,
                    COUNT(DISTINCT CASE WHEN a.live_streams_seen >= 2 AND b.live_streams_seen >= 2 THEN a.viewer_hash END) AS strong_shared_live_chat
                FROM viewer_channel_stats a
                JOIN viewer_channel_stats b
                    ON a.viewer_hash = b.viewer_hash
                    AND a.vtuber_channel_id < b.vtuber_channel_id
                GROUP BY a.vtuber_channel_id, b.vtuber_channel_id
                HAVING COUNT(DISTINCT a.viewer_hash) >= 1
            )
            SELECT
                '{w_type}' AS window_type,
                '{w_start}' AS window_start,
                '{w_end}' AS window_end,
                s.vtuber_a,
                s.vtuber_b,
                s.shared_any,
                s.shared_comments,
                s.shared_live_chat,
                s.strong_shared_any,
                s.strong_shared_comments,
                s.strong_shared_live_chat,
                t_a.total_viewers AS size_a,
                t_b.total_viewers AS size_b,
                t_a.comment_viewers AS c_size_a,
                t_b.comment_viewers AS c_size_b,
                t_a.live_chat_viewers AS l_size_a,
                t_b.live_chat_viewers AS l_size_b
            FROM shared_pairs s
            JOIN channel_totals t_a ON s.vtuber_a = t_a.vtuber_channel_id
            JOIN channel_totals t_b ON s.vtuber_b = t_b.vtuber_channel_id
            ORDER BY s.shared_any DESC
        """
        rows = con.execute(query).fetchall()
        logger.info(f"Computed window [{w_type}] {w_start[:10]} -> {w_end[:10]}: {len(rows)} pairwise links.")

        for r in rows:
            shared_any = r[5]
            shared_comments = r[6]
            shared_live_chat = r[7]
            strong_any = r[8]
            strong_comments = r[9]
            strong_live_chat = r[10]
            size_a = r[11]
            size_b = r[12]
            c_size_a = r[13]
            c_size_b = r[14]
            l_size_a = r[15]
            l_size_b = r[16]

            # Jaccard calculations
            c_union = (c_size_a + c_size_b - shared_comments) if (c_size_a + c_size_b - shared_comments) > 0 else 1
            jaccard_comments = round(shared_comments / c_union, 4)

            l_union = (l_size_a + l_size_b - shared_live_chat) if (l_size_a + l_size_b - shared_live_chat) > 0 else 1
            jaccard_live_chat = round(shared_live_chat / l_union, 4)

            # Szymkiewicz-Simpson Overlap Coefficient
            min_size = min(size_a, size_b) if min(size_a, size_b) > 0 else 1
            overlap_coeff = round(shared_any / min_size, 4)

            ca_val = cov_map.get(r[3], 1.0)
            cb_val = cov_map.get(r[4], 1.0)

            all_snapshot_records.append({
                "window_type": r[0],
                "window_start": r[1],
                "window_end": r[2],
                "vtuber_a": r[3],
                "vtuber_b": r[4],
                "shared_any": shared_any,
                "shared_comments": shared_comments,
                "shared_live_chat": shared_live_chat,
                "strong_shared_any": strong_any,
                "strong_shared_comments": strong_comments,
                "strong_shared_live_chat": strong_live_chat,
                "jaccard_comments": jaccard_comments,
                "jaccard_live_chat": jaccard_live_chat,
                "overlap_coefficient": overlap_coeff,
                "size_a": size_a,
                "size_b": size_b,
                "coverage_a": ca_val,
                "coverage_b": cb_val,
                "calculated_at": now_utc
            })

    # Save to Parquet
    if all_snapshot_records:
        snap_tbl = pa.Table.from_pylist(all_snapshot_records, schema=NETWORK_SNAPSHOT_SCHEMA)
        pq.write_table(snap_tbl, SNAPSHOTS_PARQUET, compression="snappy")
        logger.info(f"Saved {len(all_snapshot_records):,} snapshot rows to {SNAPSHOTS_PARQUET}.")

        # Export compact JSON for Web Visualizer Time Slider
        # Group by window slice for rapid UI switching
        slices = {}
        for row in all_snapshot_records:
            w_key = f"{row['window_type']}_{row['window_start'][:4]}" if row['window_type'] == 'yearly' else f"{row['window_type']}_{row['window_end'][:4]}"
            if w_key not in slices:
                slices[w_key] = {
                    "window_type": row["window_type"],
                    "window_start": row["window_start"],
                    "window_end": row["window_end"],
                    "edges": []
                }
            slices[w_key]["edges"].append({
                "source": row["vtuber_a"],
                "target": row["vtuber_b"],
                "shared_any": row["shared_any"],
                "shared_comments": row["shared_comments"],
                "shared_live_chat": row["shared_live_chat"],
                "strong_shared_any": row["strong_shared_any"],
                "jaccard_comments": row["jaccard_comments"],
                "overlap_coefficient": row["overlap_coefficient"]
            })

        web_export = {
            "metadata": {
                "description": "Thai VTuber Dynamic Temporal Network (Observed Commenters & Live Chat Participants)",
                "total_slices": len(slices),
                "generated_at": now_utc,
                "note": "This network measures observed commenters and live chat participants, not all total passive viewers."
            },
            "slices": slices
        }
        with open(WEB_SNAPSHOTS_JSON, "w", encoding="utf-8") as f:
            json.dump(web_export, f, ensure_ascii=False)
        logger.info(f"Saved Web Time Slider snapshot slices to {WEB_SNAPSHOTS_JSON}.")

    logger.info("==========================================================")
    logger.info(" Phase T3 Complete! Dynamic DuckDB Snapshots Ready.       ")
    logger.info("==========================================================")

if __name__ == "__main__":
    main()
