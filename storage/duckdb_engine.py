"""
Thai VTuber Audience Network (SNA)
DuckDB Analytical Engine

Performs in-process OLAP analytics directly on Parquet files.
Computes audience presence aggregation and pairwise overlap projections:
- Shared Viewers: |A ∩ B|
- Jaccard Similarity: |A ∩ B| / |A ∪ B|
- Simpson Overlap Coefficient: |A ∩ B| / min(|A|, |B|)
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
import duckdb
from config.settings import EVENTS_DIR, DATA_DIR

logger = logging.getLogger(__name__)


class DuckDBAnalyticsEngine:
    def __init__(self, db_path: Path = None, events_dir: Path = None):
        self.events_dir = events_dir or EVENTS_DIR
        self.db_path = db_path or (DATA_DIR / "analytics.duckdb")
        # Initialize connection (can be in-memory or persistent file)
        self.con = duckdb.connect(str(self.db_path))
        self._init_views()

    def _init_views(self):
        """Creates views on top of the Parquet directory structure."""
        files = sorted(self.events_dir.rglob("*.parquet"))
        if not files:
            self.con.execute("""CREATE OR REPLACE VIEW raw_events AS SELECT
                ''::VARCHAR AS viewer_hash, ''::VARCHAR AS vtuber_channel_id,
                ''::VARCHAR AS video_id, ''::VARCHAR AS source_type,
                ''::VARCHAR AS first_seen, ''::VARCHAR AS last_seen,
                0::BIGINT AS appearances WHERE FALSE""")
            return
        glob_pattern = str(self.events_dir / "**" / "*.parquet").replace("\\", "/").replace("'", "''")
        source = f"read_parquet('{glob_pattern}', union_by_name=True)"
        columns = {row[0] for row in self.con.execute(f"DESCRIBE SELECT * FROM {source}").fetchall()}
        required = {"viewer_hash", "vtuber_channel_id", "video_id", "source_type"}
        if not required <= columns:
            raise ValueError("Presence schema missing identity or source columns")
        def expr(name, fallback):
            return f"COALESCE({name}, {fallback})" if name in columns else fallback
        timestamp = "timestamp" if "timestamp" in columns else "NULL::VARCHAR"
        self.con.execute(f"""CREATE OR REPLACE VIEW raw_events AS SELECT
            viewer_hash, vtuber_channel_id, video_id, source_type,
            {expr('first_seen', timestamp)} AS first_seen,
            {expr('last_seen', timestamp)} AS last_seen,
            {expr('appearances', '1::BIGINT')} AS appearances
            FROM {source}""")
        invalid = self.con.execute("""SELECT COUNT(*) FROM raw_events WHERE
            source_type IS NULL OR source_type NOT IN ('live_chat', 'comment')
            OR video_id IS NULL OR trim(video_id) = ''""").fetchone()[0]
        if invalid:
            raise ValueError("Invalid or missing source_type/video_id in presence data")

    def refresh_views(self):
        """Refreshes view after new Parquet files are written."""
        self._init_views()

    def get_viewer_presence_summary(self) -> List[Dict[str, Any]]:
        """
        Viewer presence summary with precise terminology:
        - videos_seen: distinct video_id across any source
        - live_streams_seen: distinct video_id specifically from live_chat
        - appearances: total count or sum of appearances
        - first_seen / last_seen timestamps
        """
        query = """
            SELECT 
                viewer_hash,
                vtuber_channel_id,
                COUNT(DISTINCT video_id) AS videos_seen,
                COUNT(DISTINCT CASE WHEN source_type = 'live_chat' THEN video_id END) AS live_streams_seen,
                COUNT(DISTINCT CASE WHEN source_type = 'comment' THEN video_id END) AS comment_videos_seen,
                SUM(COALESCE(appearances, 1)) AS appearances,
                MIN(first_seen) AS first_seen,
                MAX(last_seen) AS last_seen
            FROM raw_events
            WHERE viewer_hash != ''
            GROUP BY viewer_hash, vtuber_channel_id
        """
        df = self.con.execute(query).df()
        return df.to_dict(orient="records")

    def get_channel_audience_sizes(self) -> Dict[str, int]:
        """Calculates total unique viewers per VTuber channel."""
        query = """
            SELECT 
                vtuber_channel_id,
                COUNT(DISTINCT viewer_hash) AS unique_viewers
            FROM raw_events
            WHERE viewer_hash != ''
            GROUP BY vtuber_channel_id
        """
        results = self.con.execute(query).fetchall()
        return {r[0]: r[1] for r in results}

    def compute_pairwise_overlap(
        self,
        min_shared_viewers: int = 1,
        min_evidence_threshold: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Calculates VTuber Audience Overlap Matrix with evidence separation:
        - shared_any: All shared viewers across any source
        - shared_live_chat: Viewers observed in live_chat on BOTH channels
        - shared_comments: Viewers observed in comments on BOTH channels
        - strong_shared_any: Viewers appearing in >= min_evidence_threshold distinct videos on BOTH channels
        - strong_shared_live_chat: Viewers appearing in live_chat for >= min_evidence_threshold distinct live streams on BOTH channels (strongest evidence)
        - strong_shared_comments: Viewers appearing in comments for >= min_evidence_threshold distinct videos on BOTH channels
        """
        self.refresh_views()
        
        if type(min_evidence_threshold) is not int or min_evidence_threshold != 2:
            raise ValueError("Strong evidence is defined as at least 2 distinct videos per channel")
        if type(min_shared_viewers) is not int or min_shared_viewers < 1:
            raise ValueError("min_shared_viewers must be a positive integer")
        threshold = 2

        count = self.con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
        if count == 0:
            logger.warning("No events available for overlap computation.")
            return []

        query = f"""
            WITH viewer_channel_stats AS (
                SELECT 
                    vtuber_channel_id,
                    viewer_hash,
                    COUNT(DISTINCT video_id) AS videos_seen,
                    COUNT(DISTINCT CASE WHEN source_type = 'live_chat' THEN video_id END) AS live_streams_seen,
                    COUNT(DISTINCT CASE WHEN source_type = 'comment' THEN video_id END) AS comment_videos_seen,
                    SUM(COALESCE(appearances, 1)) AS total_appearances,
                    BOOL_OR(source_type = 'live_chat') AS in_live_chat,
                    BOOL_OR(source_type = 'comment') AS in_comment,
                    MIN(first_seen) AS first_seen,
                    MAX(last_seen) AS last_seen
                FROM raw_events
                WHERE viewer_hash != ''
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
                    -- Standard overlap by source
                    COUNT(DISTINCT a.viewer_hash) AS shared_any,
                    COUNT(DISTINCT CASE WHEN a.in_live_chat AND b.in_live_chat THEN a.viewer_hash END) AS shared_live_chat,
                    COUNT(DISTINCT CASE WHEN a.in_comment AND b.in_comment THEN a.viewer_hash END) AS shared_comments,
                    
                    -- Strong evidence by source (distinct videos/streams >= threshold on both A and B)
                    COUNT(DISTINCT CASE WHEN a.videos_seen >= {threshold} AND b.videos_seen >= {threshold} THEN a.viewer_hash END) AS strong_shared_any,
                    COUNT(DISTINCT CASE WHEN a.live_streams_seen >= {threshold} AND b.live_streams_seen >= {threshold} THEN a.viewer_hash END) AS strong_shared_live_chat,
                    COUNT(DISTINCT CASE WHEN a.comment_videos_seen >= {threshold} AND b.comment_videos_seen >= {threshold} THEN a.viewer_hash END) AS strong_shared_comments,
                    
                    ROUND(AVG(a.videos_seen), 2) AS avg_videos_a,
                    ROUND(AVG(b.videos_seen), 2) AS avg_videos_b,
                    ROUND(AVG(a.live_streams_seen), 2) AS avg_live_streams_a,
                    ROUND(AVG(b.live_streams_seen), 2) AS avg_live_streams_b,
                    ROUND(AVG(a.total_appearances), 2) AS avg_appearances_a,
                    ROUND(AVG(b.total_appearances), 2) AS avg_appearances_b
                FROM viewer_channel_stats a
                JOIN viewer_channel_stats b 
                    ON a.viewer_hash = b.viewer_hash 
                    AND a.vtuber_channel_id < b.vtuber_channel_id
                GROUP BY a.vtuber_channel_id, b.vtuber_channel_id
                HAVING COUNT(DISTINCT a.viewer_hash) >= {min_shared_viewers}
            )
            SELECT 
                s.vtuber_a,
                s.vtuber_b,
                s.shared_any,
                s.shared_live_chat,
                s.shared_comments,
                s.strong_shared_any,
                s.strong_shared_live_chat,
                s.strong_shared_comments,
                -- Legacy alias
                s.strong_shared_any AS shared_strong,
                s.avg_videos_a,
                s.avg_videos_b,
                s.avg_live_streams_a,
                s.avg_live_streams_b,
                s.avg_appearances_a,
                s.avg_appearances_b,
                t_a.total_viewers AS size_a,
                t_b.total_viewers AS size_b,
                -- Legacy / primary weight alias for backward compatibility
                s.shared_any AS shared_viewers,
                -- Jaccard & Overlap for Any
                ROUND(s.shared_any * 1.0 / (t_a.total_viewers + t_b.total_viewers - s.shared_any), 4) AS jaccard,
                ROUND(s.shared_any * 1.0 / (t_a.total_viewers + t_b.total_viewers - s.shared_any), 4) AS jaccard_any,
                ROUND(s.shared_any * 1.0 / LEAST(t_a.total_viewers, t_b.total_viewers), 4) AS overlap_coefficient,
                ROUND(s.shared_any * 1.0 / LEAST(t_a.total_viewers, t_b.total_viewers), 4) AS overlap_coeff_any,
                -- Jaccard for Live Chat
                ROUND(CASE WHEN (t_a.live_chat_viewers + t_b.live_chat_viewers - s.shared_live_chat) > 0 
                           THEN s.shared_live_chat * 1.0 / (t_a.live_chat_viewers + t_b.live_chat_viewers - s.shared_live_chat) 
                           ELSE 0.0 END, 4) AS jaccard_live_chat,
                -- Jaccard for Comments
                ROUND(CASE WHEN (t_a.comment_viewers + t_b.comment_viewers - s.shared_comments) > 0 
                           THEN s.shared_comments * 1.0 / (t_a.comment_viewers + t_b.comment_viewers - s.shared_comments) 
                           ELSE 0.0 END, 4) AS jaccard_comments
            FROM shared_pairs s
            JOIN channel_totals t_a ON s.vtuber_a = t_a.vtuber_channel_id
            JOIN channel_totals t_b ON s.vtuber_b = t_b.vtuber_channel_id
            ORDER BY s.shared_any DESC
        """

        df = self.con.execute(query).df()
        now_str = datetime.now(timezone.utc).isoformat()
        df["calculated_at"] = now_str
        return df.to_dict(orient="records")

    def close(self):
        self.con.close()
