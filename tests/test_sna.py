"""Tests for thaivtubersna.sna"""
import tempfile
from pathlib import Path

from thaivtubersna import sna
from thaivtubersna.store import open_db, record_interaction


def _fresh_tmp_db():
    f = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
    path = Path(f.name)
    f.close()
    path.unlink(missing_ok=True)
    return path


def test_summary_on_empty_db():
    path = _fresh_tmp_db()
    try:
        summary = sna.summary(path)
        assert summary["total_edges"] == 0
        assert summary["interaction_rows"] == 0
        assert summary["live_edges"] == 0
    finally:
        path.unlink(missing_ok=True)


def test_sna_uses_distinct_videos_for_strong_overlap():
    path = _fresh_tmp_db()
    try:
        con = open_db(path)

        # Viewer x: live chat in 2 distinct videos on both creators => strong live.
        for creator, videos in {
            "A": ["a1", "a2"],
            "B": ["b1", "b2"],
        }.items():
            for video in videos:
                record_interaction(con, creator, video, "viewer_x", "live_chat")

        # Viewer y: comments in 2 distinct videos on both creators => strong comments.
        for creator, videos in {
            "A": ["a3", "a4"],
            "B": ["b3", "b4"],
        }.items():
            for video in videos:
                record_interaction(con, creator, video, "viewer_y", "comment")

        # Viewer z: shared live viewer but only one video each => not strong.
        record_interaction(con, "A", "a5", "viewer_z", "live_chat")
        record_interaction(con, "B", "b5", "viewer_z", "live_chat")
        con.close()

        written = sna.compute_pairwise_overlap(path)
        assert written == 1

        con = open_db(path)
        row = con.execute(
            """
            SELECT
                shared_any,
                shared_live_chat,
                shared_comments,
                strong_shared_any,
                strong_shared_live_chat,
                strong_shared_comments,
                calculation_source
            FROM network_edges
            WHERE creator_a = 'A' AND creator_b = 'B'
            """
        ).fetchone()
        con.close()

        assert row == (3, 2, 1, 2, 1, 1, "live_interactions")
    finally:
        path.unlink(missing_ok=True)


def test_recalculate_skips_when_interactions_unchanged():
    path = _fresh_tmp_db()
    try:
        con = open_db(path)
        record_interaction(con, "A", "a1", "viewer_x", "comment")
        record_interaction(con, "B", "b1", "viewer_x", "comment")
        con.close()

        first = sna.recalculate_if_needed(path)
        second = sna.recalculate_if_needed(path)

        assert first["skipped"] is False
        assert second["skipped"] is True
        assert second["reason"] == "interactions_unchanged"
    finally:
        path.unlink(missing_ok=True)


def test_recalculate_preserves_legacy_seed_without_interactions():
    path = _fresh_tmp_db()
    try:
        con = open_db(path)
        con.execute(
            """
            INSERT INTO network_edges (
                id, creator_a, creator_b, shared_any, calculated_at, calculation_source
            ) VALUES ('legacy', 'A', 'B', 10, '2026-09-20T00:00:00Z', 'legacy_seed')
            """
        )
        con.close()

        result = sna.recalculate_if_needed(path)
        assert result["skipped"] is True
        assert result["reason"] == "no_interactions"
        assert result["edges"] == 1
    finally:
        path.unlink(missing_ok=True)
