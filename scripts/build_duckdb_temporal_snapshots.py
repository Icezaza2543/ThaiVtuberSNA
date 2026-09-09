"""
Phase T3 / PR-5 & Hotfix 1-3: DuckDB Temporal Snapshot Engine
Builds canonical temporal interaction network slices across time windows (2020 -> 2026):

Schema:
NETWORK_SNAPSHOTS (
    window_type VARCHAR,            -- 'yearly', 'cumulative', 'all_time'
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
    coverage_a DOUBLE,              -- mathematical channel coverage (1.0 or 0.0)
    coverage_b DOUBLE,              -- mathematical channel coverage (1.0 or 0.0)
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
from typing import Dict, Any, List, Optional, Tuple, Union

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
WEB_APP_JS = BASE_DIR / "web" / "app.js"

BEGIN_MARKER = "// BEGIN GENERATED TEMPORAL SNAPSHOTS"
END_MARKER = "// END GENERATED TEMPORAL SNAPSHOTS"


def update_web_app_embedded_snapshots(web_export: dict, app_js_path: Path = WEB_APP_JS) -> None:
    """Deterministically and idempotently updates the embedded temporal snapshots in web/app.js.

    Replaces the block enclosed by:
    // BEGIN GENERATED TEMPORAL SNAPSHOTS
    const EMBEDDED_TEMPORAL_SLICES = {...};
    // END GENERATED TEMPORAL SNAPSHOTS

    If markers are not yet present, locates existing const EMBEDDED_TEMPORAL_SLICES declaration
    and wraps it cleanly with the markers.
    Guarantees that exactly ONE const EMBEDDED_TEMPORAL_SLICES declaration exists.
    """
    if not app_js_path.exists():
        logger.warning(f"{app_js_path} does not exist, skipping embedded update.")
        return

    content = app_js_path.read_text(encoding="utf-8")
    json_payload = json.dumps(web_export, ensure_ascii=False, sort_keys=True)
    generated_block = f"{BEGIN_MARKER}\nconst EMBEDDED_TEMPORAL_SLICES = {json_payload};\n{END_MARKER}"

    if BEGIN_MARKER in content and END_MARKER in content:
        start_idx = content.find(BEGIN_MARKER)
        end_idx = content.find(END_MARKER) + len(END_MARKER)
        new_content = content[:start_idx] + generated_block + content[end_idx:]
    else:
        import re
        pattern = re.compile(
            r"(?://[^\n]*\n)?const\s+EMBEDDED_TEMPORAL_SLICES\s*=\s*[\s\S]*?;\s*\n"
        )
        match = pattern.search(content)
        if match:
            new_content = content[:match.start()] + generated_block + "\n" + content[match.end():]
        else:
            data_match = re.search(r"const\s+EMBEDDED_DATA\s*=\s*[\s\S]*?;\s*\n", content)
            if data_match:
                insert_pos = data_match.end()
                new_content = content[:insert_pos] + "\n" + generated_block + "\n" + content[insert_pos:]
            else:
                new_content = generated_block + "\n\n" + content

    count = new_content.count("const EMBEDDED_TEMPORAL_SLICES")
    if count != 1:
        raise ValueError(
            f"Embedded temporal snapshot update failed: expected exactly 1 declaration, found {count}"
        )

    app_js_path.write_text(new_content, encoding="utf-8")
    logger.info(f"Updated embedded temporal snapshots in {app_js_path} (idempotent, 1 declaration verified).")

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

def get_sources_by_provenance(
    base_dir: Optional[Path] = None,
    extra_incremental_files: Optional[List[str]] = None
) -> Dict[str, List[str]]:
    """
    Categorizes all available event/observation parquet files by explicit provenance tier:
      - t16_incremental: Incremental append-only batches from Phase T16
      - t6_deep: Exhaustive comments from Phase T6
      - t5_stratified: Stratified comment backfill from Phase T5
      - t2_pilot: Initial temporal pilot dataset
      - legacy: Historical real pipeline and legacy events (comment + live chat)
    """
    target_data_dir = (base_dir / "data") if base_dir else DATA_DIR
    fallback_data_dir = DATA_DIR

    def resolve_dir(subpath: str) -> Path:
        p1 = target_data_dir / subpath
        if p1.exists():
            return p1
        return p1 if base_dir is not None else fallback_data_dir / subpath

    deep_dir = resolve_dir("temporal/deep_observations")
    deep_sources = sorted(str(p).replace("\\", "/") for p in deep_dir.rglob("*.parquet")) if deep_dir.exists() else []

    t5_dir = resolve_dir("temporal/observations")
    t5_sources = sorted(str(p).replace("\\", "/") for p in t5_dir.rglob("*.parquet")) if t5_dir.exists() else []

    pilot_dir = resolve_dir("temporal/pilot")
    pilot_p = pilot_dir / "temporal_comment_pilot.parquet"
    t2_sources = [str(pilot_p).replace("\\", "/")] if pilot_p.exists() else []

    real_dir = resolve_dir("real/events")
    real_sources = sorted(str(p).replace("\\", "/") for p in real_dir.rglob("*.parquet")) if real_dir.exists() else []

    legacy_dir = resolve_dir("events")
    legacy_sources = sorted(str(p).replace("\\", "/") for p in legacy_dir.rglob("*.parquet")) if legacy_dir.exists() else []

    # Incremental sources: only from target incremental dir
    inc_dir = target_data_dir / "temporal" / "incremental"
    inc_sources = sorted(str(p).replace("\\", "/") for p in inc_dir.glob("batch_*.parquet") if not p.name.endswith(".tmp")) if inc_dir.exists() else []

    if extra_incremental_files:
        for ef in extra_incremental_files:
            ef_str = str(ef).replace("\\", "/")
            if ef_str not in inc_sources and Path(ef_str).exists():
                inc_sources.append(ef_str)

    return {
        "t16_incremental": inc_sources,
        "t6_deep": deep_sources,
        "t5_stratified": t5_sources,
        "t2_pilot": t2_sources,
        "legacy": real_sources + legacy_sources,
    }

def collect_available_parquet_sources(
    base_dir: Optional[Path] = None,
    extra_incremental_files: Optional[List[str]] = None
) -> List[str]:
    """
    Finds all available event/observation parquet files across temporal and legacy directories.
    Returns full list across all provenance tiers.
    """
    by_prov = get_sources_by_provenance(base_dir=base_dir, extra_incremental_files=extra_incremental_files)
    return (
        by_prov.get("t16_incremental", []) +
        by_prov["t6_deep"] +
        by_prov["t5_stratified"] +
        by_prov["t2_pilot"] +
        by_prov["legacy"]
    )

def build_unified_raw_view(con: duckdb.DuckDBPyConnection, sources_by_prov: Optional[Dict[str, List[str]]] = None) -> None:
    """
    Constructs the unified_raw view from all available parquet sources,
    attaching explicit provenance and priority to each source tier:
      - t16_incremental (priority 0, additive overlay)
      - t6_deep (priority 1)
      - t5_stratified (priority 2)
      - t2_pilot (priority 3)
      - legacy (priority 4)
    """
    if sources_by_prov is None:
        from storage.private_sheet_analytics import build_sheet_unified_raw
        build_sheet_unified_raw(con)
        return
    by_prov = sources_by_prov
    union_queries = []

    if by_prov.get("t16_incremental"):
        t16_list = ", ".join(f"'{s}'" for s in by_prov["t16_incremental"])
        union_queries.append(f"""
            SELECT viewer_hash, vtuber_channel_id, video_id,
                   COALESCE(source_type, 'comment') AS source_type,
                   COALESCE(try_cast(interaction_time AS TIMESTAMPTZ), try_cast(interaction_at AS TIMESTAMPTZ)) AS interaction_at,
                   CAST(NULL AS TIMESTAMPTZ) AS first_seen,
                   CAST(NULL AS TIMESTAMPTZ) AS timestamp,
                   CAST(NULL AS TIMESTAMPTZ) AS video_published_at,
                   't16_incremental' AS provenance,
                   0 AS priority
            FROM read_parquet([{t16_list}], union_by_name=True)
        """)

    if by_prov.get("t6_deep"):
        t6_list = ", ".join(f"'{s}'" for s in by_prov["t6_deep"])
        union_queries.append(f"""
            SELECT viewer_hash, vtuber_channel_id, video_id,
                   COALESCE(source_type, 'comment') AS source_type,
                   try_cast(interaction_at AS TIMESTAMPTZ) AS interaction_at,
                   CAST(NULL AS TIMESTAMPTZ) AS first_seen,
                   CAST(NULL AS TIMESTAMPTZ) AS timestamp,
                   try_cast(video_published_at AS TIMESTAMPTZ) AS video_published_at,
                   't6_deep' AS provenance,
                   1 AS priority
            FROM read_parquet([{t6_list}], union_by_name=True)
        """)

    if by_prov.get("t5_stratified"):
        t5_list = ", ".join(f"'{s}'" for s in by_prov["t5_stratified"])
        union_queries.append(f"""
            SELECT viewer_hash, vtuber_channel_id, video_id,
                   COALESCE(source_type, 'comment') AS source_type,
                   try_cast(interaction_at AS TIMESTAMPTZ) AS interaction_at,
                   CAST(NULL AS TIMESTAMPTZ) AS first_seen,
                   CAST(NULL AS TIMESTAMPTZ) AS timestamp,
                   try_cast(video_published_at AS TIMESTAMPTZ) AS video_published_at,
                   't5_stratified' AS provenance,
                   2 AS priority
            FROM read_parquet([{t5_list}], union_by_name=True)
        """)

    if by_prov.get("t2_pilot"):
        t2_list = ", ".join(f"'{s}'" for s in by_prov["t2_pilot"])
        union_queries.append(f"""
            SELECT viewer_hash, vtuber_channel_id, video_id,
                   COALESCE(source_type, 'comment') AS source_type,
                   try_cast(interaction_at AS TIMESTAMPTZ) AS interaction_at,
                   CAST(NULL AS TIMESTAMPTZ) AS first_seen,
                   CAST(NULL AS TIMESTAMPTZ) AS timestamp,
                   try_cast(video_published_at AS TIMESTAMPTZ) AS video_published_at,
                   't2_pilot' AS provenance,
                   3 AS priority
            FROM read_parquet([{t2_list}], union_by_name=True)
        """)

    if by_prov.get("legacy"):
        legacy_list = ", ".join(f"'{s}'" for s in by_prov["legacy"])
        union_queries.append(f"""
            SELECT viewer_hash, vtuber_channel_id, video_id,
                   COALESCE(source_type, 'comment') AS source_type,
                   CAST(NULL AS TIMESTAMPTZ) AS interaction_at,
                   try_cast(first_seen AS TIMESTAMPTZ) AS first_seen,
                   try_cast(timestamp AS TIMESTAMPTZ) AS timestamp,
                   CAST(NULL AS TIMESTAMPTZ) AS video_published_at,
                   'legacy' AS provenance,
                   4 AS priority
            FROM read_parquet([{legacy_list}], union_by_name=True)
        """)

    if not union_queries:
        raise RuntimeError("No parquet sources available to build unified_raw view!")

    full_sql = " UNION ALL ".join(union_queries)
    con.execute(f"CREATE OR REPLACE VIEW unified_raw AS {full_sql}")

def load_channel_coverage_records(base_dir: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Loads coverage records by channel_id from T1 channel_coverage.parquet."""
    target_data_dir = (base_dir / "data") if base_dir else DATA_DIR
    cov_path = target_data_dir / "temporal" / "catalog" / "channel_coverage.parquet"
    if not cov_path.exists() and base_dir is None:
        cov_path = DATA_DIR / "temporal" / "catalog" / "channel_coverage.parquet"
    if not cov_path.exists():
        return {}
    try:
        tbl = pq.read_table(cov_path)
        return {r["channel_id"]: r for r in tbl.to_pylist() if r.get("channel_id")}
    except Exception as e:
        logger.warning(f"Could not load channel coverage: {e}")
        return {}

def calculate_channel_window_coverage(
    channel_id: str,
    window_start: Union[str, datetime],
    coverage_by_cid: Dict[str, Dict[str, Any]]
) -> float:
    """
    Calculates exact mathematical coverage (1.0 or 0.0) for a channel within a window starting at window_start.

    Principles (aligned with scripts/generate_catalog_audit_report.py):
    - PLAYLIST_EXHAUSTED: 1.0 (entire channel history captured down to first upload)
    - NO_VIDEOS: 1.0 (proven zero-history channel)
    - CUTOFF_REACHED: 1.0 if window_start >= 2020-01-01T00:00:00Z (proven complete from cutoff onward)
    - CAP_REACHED: 1.0 if oldest_video_published_at <= window_start_dt, else 0.0
    - Otherwise: 0.0 (incomplete, not provably complete)
    """
    cov = coverage_by_cid.get(channel_id)
    if not cov:
        return 0.0

    if isinstance(window_start, str):
        dt_str = window_start.split()[0]
        window_start_dt = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
    else:
        window_start_dt = window_start.astimezone(timezone.utc) if window_start.tzinfo else window_start.replace(tzinfo=timezone.utc)

    term = cov.get("termination_reason")
    oldest = cov.get("oldest_video_published_at")

    if oldest is not None:
        if isinstance(oldest, str):
            oldest_dt = datetime.fromisoformat(oldest.replace("Z", "+00:00"))
        elif isinstance(oldest, datetime):
            oldest_dt = oldest
        else:
            oldest_dt = None

        if oldest_dt is not None and oldest_dt.tzinfo is None:
            oldest_dt = oldest_dt.replace(tzinfo=timezone.utc)
    else:
        oldest_dt = None

    if term == "PLAYLIST_EXHAUSTED":
        return 1.0
    elif term == "NO_VIDEOS":
        return 1.0
    elif term == "CUTOFF_REACHED":
        cutoff_boundary = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        if window_start_dt >= cutoff_boundary:
            return 1.0
        return 1.0 if (oldest_dt and oldest_dt <= window_start_dt) else 0.0
    elif term == "CAP_REACHED":
        return 1.0 if (oldest_dt and oldest_dt <= window_start_dt) else 0.0
    else:
        return 0.0

def build_canonical_events_view(con: duckdb.DuckDBPyConnection, source_table_or_view: str = "unified_raw") -> None:
    """
    Constructs the canonical_events view from the unified raw table/view with source precedence:
    - Precedence for same (vtuber_channel_id, video_id, source_type='comment'):
        t6_deep (priority 1) > t5_stratified (priority 2) > t2_pilot (priority 3) > legacy (priority 4)
    - If T6 deep comment data exists for a video, excludes T5/T2/legacy comment data for that video.
    - Else if T5 comment data exists, excludes T2/legacy comment data for that video.
    - Preserves legacy/T2 live_chat evidence even when the same video has T5/T6 comment data.
    - Deduplicates same (viewer_hash, vtuber_channel_id, video_id, source_type) taking MIN(interaction_time).
    - Strict Temporal Contract:
      - interaction_time MUST only come from interaction_at, first_seen, or timestamp.
      - video_published_at MUST NEVER be used as fallback for interaction_time.
      - Missing interaction timestamps yield interaction_time = NULL and interaction_time_source = 'missing'.
      - Buddhist Era dates (> 2500) are normalized by subtracting 543 years.
    """
    con.execute("SET Calendar = 'gregorian'")
    cols = {r[0] for r in con.execute(f"DESCRIBE {source_table_or_view}").fetchall()}

    append_expr = "COALESCE(append_only, FALSE)" if "append_only" in cols else "FALSE"
    inter_expr = "interaction_at" if "interaction_at" in cols else "NULL"
    first_seen_expr = "first_seen" if "first_seen" in cols else "NULL"
    timestamp_expr = "timestamp" if "timestamp" in cols else "NULL"
    pub_expr = "video_published_at" if "video_published_at" in cols else "NULL"
    source_expr = "source_type" if "source_type" in cols else "'comment'"

    # Support explicit provenance or infer from signature columns
    if "provenance" in cols:
        prov_expr = "provenance"
    else:
        conds = []
        if "pages_fetched" in cols:
            conds.append("WHEN pages_fetched IS NOT NULL THEN 't6_deep'")
        if "sampling_manifest_version" in cols:
            conds.append("WHEN sampling_manifest_version IS NOT NULL THEN 't5_stratified'")
        if "page_number" in cols:
            conds.append("WHEN page_number IS NOT NULL THEN 't2_pilot'")
        if conds:
            prov_expr = f"CASE {' '.join(conds)} ELSE 'legacy' END"
        else:
            prov_expr = "'unspecified'"

    if "priority" in cols:
        prio_expr = "priority"
    else:
        prio_expr = f"""
            CASE
                WHEN {prov_expr} = 't16_incremental' THEN 0
                WHEN {prov_expr} = 't6_deep' THEN 1
                WHEN {prov_expr} = 't5_stratified' THEN 2
                WHEN {prov_expr} = 't2_pilot' THEN 3
                WHEN {prov_expr} = 'legacy' THEN 4
                ELSE 1
            END
        """

    con.execute(f"""
        CREATE OR REPLACE VIEW canonical_events AS
        WITH raw_data AS (
            SELECT
                viewer_hash,
                vtuber_channel_id,
                COALESCE(video_id, 'vid_unknown') AS video_id,
                COALESCE({source_expr}, 'comment') AS source_type,
                try_cast({inter_expr} AS TIMESTAMPTZ) AS parsed_interaction_at,
                try_cast({first_seen_expr} AS TIMESTAMPTZ) AS parsed_first_seen,
                try_cast({timestamp_expr} AS TIMESTAMPTZ) AS parsed_timestamp,
                try_cast({pub_expr} AS TIMESTAMPTZ) AS parsed_video_published_at,
                {prov_expr} AS provenance,
                CAST({prio_expr} AS INT) AS priority,
                {append_expr} AS append_only
            FROM {source_table_or_view}
            WHERE viewer_hash IS NOT NULL AND viewer_hash != ''
              AND vtuber_channel_id IS NOT NULL AND vtuber_channel_id != ''
        ),
        classified AS (
            SELECT
                viewer_hash,
                vtuber_channel_id,
                video_id,
                source_type,
                CASE
                    WHEN parsed_interaction_at IS NOT NULL THEN parsed_interaction_at
                    WHEN parsed_first_seen IS NOT NULL THEN parsed_first_seen
                    WHEN parsed_timestamp IS NOT NULL THEN parsed_timestamp
                    ELSE NULL
                END AS raw_interaction_time,
                CASE
                    WHEN parsed_interaction_at IS NOT NULL THEN 'interaction_at'
                    WHEN parsed_first_seen IS NOT NULL THEN 'first_seen'
                    WHEN parsed_timestamp IS NOT NULL THEN 'timestamp'
                    ELSE 'missing'
                END AS interaction_time_source,
                CASE
                    WHEN parsed_interaction_at IS NOT NULL THEN 'verified'
                    WHEN parsed_first_seen IS NOT NULL THEN 'legacy'
                    WHEN parsed_timestamp IS NOT NULL THEN 'legacy'
                    ELSE 'missing'
                END AS timestamp_quality,
                parsed_video_published_at AS raw_video_published_at,
                provenance,
                priority,
                append_only
            FROM raw_data
        ),
        normalized AS (
            SELECT
                viewer_hash,
                vtuber_channel_id,
                video_id,
                source_type,
                CASE
                    WHEN raw_interaction_time IS NOT NULL AND extract(year from raw_interaction_time) > 2500
                        THEN raw_interaction_time - INTERVAL 543 YEAR
                    ELSE raw_interaction_time
                END AS interaction_time,
                CASE
                    WHEN raw_video_published_at IS NOT NULL AND extract(year from raw_video_published_at) > 2500
                        THEN raw_video_published_at - INTERVAL 543 YEAR
                    ELSE raw_video_published_at
                END AS video_published_at,
                interaction_time_source,
                timestamp_quality,
                provenance,
                priority,
                append_only
            FROM classified
        ),
        comment_video_priority AS (
            SELECT
                vtuber_channel_id,
                video_id,
                MIN(priority) AS best_comment_priority
            FROM normalized
            WHERE source_type = 'comment' AND provenance != 't16_incremental' AND NOT append_only
            GROUP BY vtuber_channel_id, video_id
        ),
        precedence_filtered AS (
            SELECT
                n.*
            FROM normalized n
            LEFT JOIN comment_video_priority cvp
              ON n.vtuber_channel_id = cvp.vtuber_channel_id
             AND n.video_id = cvp.video_id
            WHERE (n.source_type != 'comment')
               OR (n.provenance = 't16_incremental')
               OR n.append_only
               OR (n.source_type = 'comment' AND n.priority = cvp.best_comment_priority)
        ),
        deduplicated AS (
            SELECT
                viewer_hash,
                vtuber_channel_id,
                video_id,
                source_type,
                MIN(interaction_time) AS interaction_time,
                MIN(video_published_at) AS video_published_at,
                FIRST(interaction_time_source) AS interaction_time_source,
                FIRST(timestamp_quality) AS timestamp_quality,
                FIRST(provenance) AS provenance
            FROM precedence_filtered
            GROUP BY viewer_hash, vtuber_channel_id, video_id, source_type
        )
        SELECT
            viewer_hash,
            vtuber_channel_id,
            video_id,
            source_type,
            interaction_time,
            video_published_at,
            interaction_time_source,
            timestamp_quality,
            provenance
        FROM deduplicated
    """)

def build_expanded_window(con, window, creators, identity_evidence, *, snapshot_id,
                          cohort_version, collected_through, collected_at, generated_at,
                          coverage_by_cid=None, canonical_view='canonical_events'):
    """Reuse canonical event metrics; add independently evidenced node membership."""
    from analytics.expanded_snapshot import build_snapshot
    from core.expanded_contracts import instant
    if instant(window['end']) > instant(collected_through):
        raise ValueError('Aggregate window extends beyond collected evidence cutoff')
    rows = compute_window_snapshots(con, window, coverage_by_cid or {},
                                    canonical_view=canonical_view, calculated_at=generated_at)
    edges = [{**row, 'source': row['vtuber_a'], 'target': row['vtuber_b'],
              'edge_type': 'audience_overlap', 'window_start': window['start'],
              'window_end': window['end'], 'coverage_a': None, 'coverage_b': None} for row in rows]
    snapshot = build_snapshot(creators=creators, evidence=identity_evidence, edges=edges,
                          snapshot_id=snapshot_id, cohort_version=cohort_version,
                          window_start=window['start'], window_end=window['end'],
                          collected_through=collected_through, collected_at=collected_at,
                          generated_at=generated_at)
    # Legacy numerical catalog coverage is not interaction completion. Preserve the
    # existing metric calculation but expose independent expanded source states.
    for node in snapshot['nodes']:
        coverage = (coverage_by_cid or {}).get(node['id'], {})
        node['coverage'] = {name + '_status': coverage.get(name + '_status', 'UNKNOWN')
                            for name in ('catalog', 'comment', 'reply', 'live_chat')}
    return snapshot


def export_expanded_snapshots(snapshots, output_path, *, synthetic=False):
    """Explicit expanded export only; never mutate frozen slices, embeds or pointers.

    Callers supply reviewed membership plus existing window aggregates. Production
    collection and promotion remain guarded by their existing entry points.
    """
    from analytics.expanded_snapshot import snapshot_bundle
    from core.data_security import assert_public
    path = Path(output_path)
    if 'expanded-v1' not in path.parts:
        raise ValueError('Expanded outputs require their own version namespace')
    if synthetic and 'synthetic' not in path.stem:
        raise ValueError('Synthetic exports must be visibly named synthetic')
    bundle = snapshot_bundle(snapshots, synthetic=synthetic)
    assert_public(bundle, ())
    content = json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    if path.exists() and path.read_text(encoding='utf-8') != content:
        raise ValueError('Versioned snapshot exists; choose a new versioned filename')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return bundle


def compute_window_snapshots(
    con: duckdb.DuckDBPyConnection,
    window: Dict[str, str],
    coverage_by_cid: Dict[str, Dict[str, Any]],
    canonical_view: str = "canonical_events",
    calculated_at: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Computes pairwise audience overlap snapshots for a specific time window.
    Strictly filters out events where interaction_time IS NULL.
    """
    w_type = window["type"]
    w_start = window["start"]
    w_end = window["end"]
    ts_now = calculated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    query = f"""
        WITH filtered_events AS (
            SELECT * FROM {canonical_view}
            WHERE interaction_time IS NOT NULL
              AND interaction_time >= '{w_start}'
              AND interaction_time <= '{w_end}'
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
        ORDER BY s.shared_any DESC, s.vtuber_a, s.vtuber_b
    """
    rows = con.execute(query).fetchall()
    results = []

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

        ca_val = calculate_channel_window_coverage(r[3], w_start, coverage_by_cid)
        cb_val = calculate_channel_window_coverage(r[4], w_start, coverage_by_cid)

        results.append({
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
            "calculated_at": ts_now
        })

    return results

def load_dataset_maturity_metadata(con: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    """Extracts dataset maturity metadata from sampling manifest, checkpoint, and DuckDB canonical events."""
    manifest_path = DATA_DIR / "temporal" / "backfill" / "sampling_manifest.parquet"
    sampling_manifest_total = 0
    if manifest_path.exists():
        try:
            tbl = pq.read_table(manifest_path)
            sampling_manifest_total = len(tbl)
        except Exception as e:
            logger.warning(f"Could not read sampling manifest length: {e}")

    checkpoint_db = DATA_DIR / "temporal" / "backfill" / "backfill_checkpoint.sqlite3"
    terminal_jobs = 0
    pending_jobs = 0
    completed_with_obs = 0
    no_comments_cnt = 0
    comments_disabled_cnt = 0
    video_unavail_cnt = 0
    failed_cnt = 0

    if checkpoint_db.exists():
        import sqlite3
        try:
            scon = sqlite3.connect(str(checkpoint_db))
            rows = scon.execute("SELECT status, COUNT(*) FROM backfill_jobs GROUP BY status").fetchall()
            status_map = {r[0]: r[1] for r in rows}
            completed_with_obs = status_map.get("COMPLETED", 0)
            no_comments_cnt = status_map.get("NO_COMMENTS", 0)
            comments_disabled_cnt = status_map.get("COMMENTS_DISABLED", 0)
            video_unavail_cnt = status_map.get("VIDEO_UNAVAILABLE", 0)
            failed_cnt = status_map.get("FAILED", 0)
            pending_jobs = status_map.get("PENDING", 0) + status_map.get("RETRYABLE", 0)
            terminal_jobs = completed_with_obs + no_comments_cnt + comments_disabled_cnt + video_unavail_cnt + failed_cnt
            scon.close()
        except Exception as e:
            logger.warning(f"Could not read checkpoint count: {e}")

    dated_events = con.execute("SELECT COUNT(*) FROM canonical_events WHERE interaction_time IS NOT NULL").fetchone()[0]
    channels_with_temporal_evidence = con.execute(
        "SELECT COUNT(DISTINCT vtuber_channel_id) FROM canonical_events WHERE interaction_time IS NOT NULL"
    ).fetchone()[0]

    year_cov_rows = con.execute("""
        SELECT
            CAST(extract(year FROM interaction_time) AS INT) AS yr,
            COUNT(DISTINCT vtuber_channel_id) AS channels_with_evidence,
            COUNT(DISTINCT video_id) AS videos_with_evidence,
            COUNT(*) AS dated_interactions
        FROM canonical_events
        WHERE interaction_time IS NOT NULL
          AND extract(year FROM interaction_time) BETWEEN 2020 AND 2026
        GROUP BY yr
        ORDER BY yr
    """).fetchall()

    year_coverage = {
        str(r[0]): {
            "channels_with_evidence": r[1],
            "videos_with_evidence": r[2],
            "dated_interactions": r[3]
        }
        for r in year_cov_rows
    }

    completion_ratio = round(terminal_jobs / sampling_manifest_total, 4) if sampling_manifest_total > 0 else 0.0

    deep_checkpoint_db = DATA_DIR / "temporal" / "deep_backfill" / "deep_backfill_checkpoint.sqlite3"
    t6_manifest_total = 0
    t6_terminal_jobs = 0
    t6_pending_jobs = 0
    if deep_checkpoint_db.exists():
        try:
            dcon = sqlite3.connect(str(deep_checkpoint_db))
            drows = dcon.execute("SELECT status, COUNT(*) FROM deep_backfill_jobs GROUP BY status").fetchall()
            dstatus_map = {r[0]: r[1] for r in drows}
            dcon.close()
            t6_manifest_total = sum(dstatus_map.values())
            t6_pending_jobs = dstatus_map.get("PENDING", 0) + dstatus_map.get("RETRYABLE", 0) + dstatus_map.get("RUNNING", 0)
            t6_terminal_jobs = t6_manifest_total - t6_pending_jobs
        except Exception as e:
            logger.warning(f"Could not read deep checkpoint: {e}")

    if t6_manifest_total > 0 and t6_pending_jobs == 0 and t6_terminal_jobs >= t6_manifest_total:
        stage = "deep_historical_backfill_complete"
    elif t6_terminal_jobs > 0:
        stage = "deep_historical_backfill_partial"
    elif pending_jobs == 0 and terminal_jobs >= sampling_manifest_total and sampling_manifest_total > 0:
        stage = "historical_stratified_backfill_complete"
    else:
        stage = "historical_stratified_backfill_partial"

    return {
        "temporal_dataset_stage": stage,
        "sampling_strategy": "deterministic SHA-256 hash ranking; first-ranked candidate per temporal bin",
        "sampling_manifest_total": sampling_manifest_total,
        "sampled_videos_total": sampling_manifest_total,
        "terminal_jobs": terminal_jobs,
        "pending_jobs": pending_jobs,
        "completion_ratio": completion_ratio,
        "completed_with_observations": completed_with_obs,
        "no_comments": no_comments_cnt,
        "comments_disabled": comments_disabled_cnt,
        "video_unavailable": video_unavail_cnt,
        "failed": failed_cnt,
        "sampled_videos_processed": terminal_jobs,
        "t6_manifest_total": t6_manifest_total,
        "t6_terminal_jobs": t6_terminal_jobs,
        "t6_pending_jobs": t6_pending_jobs,
        "dated_interactions": dated_events,
        "channels_with_temporal_evidence": channels_with_temporal_evidence,
        "year_coverage": year_coverage
    }


def main():
    logger.info("==========================================================")
    logger.info(" PHASE T3: DuckDB Temporal Snapshot Engine (Hotfix 1-3)   ")
    logger.info("==========================================================")

    sources = []  # Private observations are read from the workbook, never local files.

    cov_records = load_channel_coverage_records()
    logger.info(f"Loaded coverage records for {len(cov_records)} channels.")

    con = duckdb.connect(":memory:")

    # Build canonical unified events view with explicit provenance
    logger.info(f"Registering Parquet union view from {len(sources)} files with tier provenance...")
    from storage.private_sheet_analytics import build_sheet_unified_raw
    build_sheet_unified_raw(con)
    build_canonical_events_view(con, "unified_raw")

    # Audit loaded events
    total_events = con.execute("SELECT COUNT(*) FROM canonical_events").fetchone()[0]
    dated_events = con.execute("SELECT COUNT(*) FROM canonical_events WHERE interaction_time IS NOT NULL").fetchone()[0]
    undated_events = con.execute("SELECT COUNT(*) FROM canonical_events WHERE interaction_time IS NULL").fetchone()[0]
    invalid_raw = con.execute("SELECT COUNT(*) FROM unified_raw WHERE viewer_hash IS NULL OR viewer_hash = '' OR vtuber_channel_id IS NULL OR vtuber_channel_id = ''").fetchone()[0]

    logger.info(f"Total Canonical Events: {total_events:,}")
    logger.info(f"Dated Interaction Events (Accepted for Slicing): {dated_events:,}")
    logger.info(f"Undated Interaction Events (Strictly Excluded): {undated_events:,}")
    logger.info(f"Invalid Rows Rejected: {invalid_raw:,}")

    # Log per-source profiling
    source_stats = []
    for s in sources:
        try:
            s_total = con.execute(f"SELECT COUNT(*) FROM read_parquet('{s}')").fetchone()[0]
            source_stats.append({
                "source": s.split("/")[-1],
                "rows": s_total
            })
        except Exception:
            pass

    # Define time windows:
    # 1. Yearly: 2020 through 2026 YTD
    # 2. Cumulative: Through 2021, Through 2022, ... Through 2026 YTD
    # 3. All-time window (dated evidence only)
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

        # All-time window (dated evidence only)
        {"type": "all_time", "start": "2020-01-01", "end": "2026-09-08 23:59:59"}
    ]

    all_snapshot_records = []

    for w in windows:
        snap_rows = compute_window_snapshots(con, w, cov_records, "canonical_events", now_utc)
        logger.info(f"Computed window [{w['type']}] {w['start'][:10]} -> {w['end'][:10]}: {len(snap_rows)} pairwise links.")
        all_snapshot_records.extend(snap_rows)

    # Save to Parquet
    if all_snapshot_records:
        snap_tbl = pa.Table.from_pylist(all_snapshot_records, schema=NETWORK_SNAPSHOT_SCHEMA)
        pq.write_table(snap_tbl, SNAPSHOTS_PARQUET, compression="snappy")
        logger.info(f"Saved {len(all_snapshot_records):,} snapshot rows to {SNAPSHOTS_PARQUET}.")

        # Export compact JSON for Web Visualizer Time Slider
        slices = {}
        for row in all_snapshot_records:
            if row["window_type"] == "yearly":
                w_key = f"yearly_{row['window_start'][:4]}"
            elif row["window_type"] == "cumulative":
                w_key = f"cumulative_{row['window_end'][:4]}"
            else:
                w_key = "all_time"

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
                "strong_shared_comments": row["strong_shared_comments"],
                "strong_shared_live_chat": row["strong_shared_live_chat"],
                "jaccard_comments": row["jaccard_comments"],
                "jaccard_live_chat": row["jaccard_live_chat"],
                "overlap_coefficient": row["overlap_coefficient"],
                "coverage_a": row["coverage_a"],
                "coverage_b": row["coverage_b"]
            })

        maturity = load_dataset_maturity_metadata(con)
        web_export = {
            "metadata": {
                "description": "Thai VTuber Dynamic Temporal Network (Observed Commenters & Live Chat Participants with Dated Interaction Evidence)",
                "temporal_dataset_stage": maturity["temporal_dataset_stage"],
                "sampling_strategy": maturity["sampling_strategy"],
                "sampling_manifest_total": maturity["sampling_manifest_total"],
                "sampled_videos_total": maturity["sampled_videos_total"],
                "terminal_jobs": maturity["terminal_jobs"],
                "pending_jobs": maturity["pending_jobs"],
                "completion_ratio": maturity["completion_ratio"],
                "completed_with_observations": maturity["completed_with_observations"],
                "no_comments": maturity["no_comments"],
                "comments_disabled": maturity["comments_disabled"],
                "video_unavailable": maturity["video_unavailable"],
                "failed": maturity["failed"],
                "sampled_videos_processed": maturity["sampled_videos_processed"],
                "dated_interactions": maturity["dated_interactions"],
                "channels_with_temporal_evidence": maturity["channels_with_temporal_evidence"],
                "year_coverage": maturity["year_coverage"],
                "total_slices": len(slices),
                "total_events_loaded": total_events,
                "dated_events_accepted": dated_events,
                "undated_events_excluded": undated_events,
                "invalid_events_rejected": invalid_raw,
                "generated_at": now_utc,
                "note": "Historical audience network based on stratified samples of dated commenter/chat interaction evidence. It does not represent all YouTube viewers or exhaustive comment history. Undated observations are excluded from temporal slices. Video publication date is never substituted for audience interaction time."
            },
            "slices": slices
        }
        with open(WEB_SNAPSHOTS_JSON, "w", encoding="utf-8") as f:
            json.dump(web_export, f, ensure_ascii=False)
        logger.info(f"Saved Web Time Slider snapshot slices to {WEB_SNAPSHOTS_JSON}.")

        # Deterministically update embedded fallback in web/app.js
        update_web_app_embedded_snapshots(web_export, WEB_APP_JS)

    logger.info("==========================================================")
    logger.info(" Phase T3 / Hotfix 1-3 Complete! Dynamic Snapshots Ready. ")
    logger.info("==========================================================")

if __name__ == "__main__":
    main()
