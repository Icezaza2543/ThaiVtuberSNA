"""
Regression tests for Source Provenance and Comment Precedence in ThaiVtuberSNA.

Enforces:
1. T6 suppresses lower-priority comments on same video.
2. T5 suppresses T2/legacy comments when no T6 exists.
3. Legacy live_chat remains preserved even when T6/T5 comments exist for same video.
4. Same viewer/video comment presence is not double counted.
5. Different videos remain independent.
6. Strong overlap still requires >=2 DISTINCT videos (repeated comments do not inflate strong overlap).
7. Temporal timestamps are unchanged and video_published_at is never used as interaction fallback.
"""

import duckdb
import pyarrow as pa
import pytest
from datetime import datetime, timezone

from scripts.build_duckdb_temporal_snapshots import (
    build_canonical_events_view,
    compute_window_snapshots,
)


def test_t6_suppresses_lower_priority_comments_on_same_video():
    """Rule 1: If T6 deep comment data exists for a video, exclude T5/T2/legacy comments for that same video."""
    con = duckdb.connect(":memory:")
    data = [
        # T6 deep comment
        {"viewer_hash": "v1_t6", "vtuber_channel_id": "UC_A", "video_id": "vid_shared_1", "source_type": "comment", "interaction_at": "2023-01-02T10:00:00Z", "provenance": "t6_deep", "priority": 1},
        # T5 shallow comment on same video
        {"viewer_hash": "v2_t5", "vtuber_channel_id": "UC_A", "video_id": "vid_shared_1", "source_type": "comment", "interaction_at": "2023-01-03T10:00:00Z", "provenance": "t5_stratified", "priority": 2},
        # T2 pilot comment on same video
        {"viewer_hash": "v3_t2", "vtuber_channel_id": "UC_A", "video_id": "vid_shared_1", "source_type": "comment", "interaction_at": "2023-01-04T10:00:00Z", "provenance": "t2_pilot", "priority": 3},
        # Legacy comment on same video
        {"viewer_hash": "v4_leg", "vtuber_channel_id": "UC_A", "video_id": "vid_shared_1", "source_type": "comment", "first_seen": "2023-01-05T10:00:00Z", "provenance": "legacy", "priority": 4},
    ]
    con.register("test_raw", pa.Table.from_pylist(data))
    build_canonical_events_view(con, "test_raw")

    rows = con.execute("SELECT viewer_hash, provenance FROM canonical_events").fetchall()
    assert len(rows) == 1, f"Expected exactly 1 row (T6), got {len(rows)}: {rows}"
    assert rows[0][0] == "v1_t6"
    assert rows[0][1] == "t6_deep"


def test_t5_suppresses_t2_and_legacy_comments_when_no_t6_exists():
    """Rule 2: Else if T5 comment data exists, exclude T2/legacy comments for that same channel+video."""
    con = duckdb.connect(":memory:")
    data = [
        # T5 stratified comment
        {"viewer_hash": "v10_t5", "vtuber_channel_id": "UC_A", "video_id": "vid_shared_2", "source_type": "comment", "interaction_at": "2022-05-01T10:00:00Z", "provenance": "t5_stratified", "priority": 2},
        # T2 pilot comment on same video
        {"viewer_hash": "v11_t2", "vtuber_channel_id": "UC_A", "video_id": "vid_shared_2", "source_type": "comment", "interaction_at": "2022-05-02T10:00:00Z", "provenance": "t2_pilot", "priority": 3},
        # Legacy comment on same video
        {"viewer_hash": "v12_leg", "vtuber_channel_id": "UC_A", "video_id": "vid_shared_2", "source_type": "comment", "first_seen": "2022-05-03T10:00:00Z", "provenance": "legacy", "priority": 4},
    ]
    con.register("test_raw", pa.Table.from_pylist(data))
    build_canonical_events_view(con, "test_raw")

    rows = con.execute("SELECT viewer_hash, provenance FROM canonical_events").fetchall()
    assert len(rows) == 1, f"Expected exactly 1 row (T5), got {len(rows)}: {rows}"
    assert rows[0][0] == "v10_t5"
    assert rows[0][1] == "t5_stratified"


def test_legacy_live_chat_preserved_even_when_t6_t5_comments_exist():
    """Rule 3: Preserve legacy/T2 live_chat evidence even when the same video has T5/T6 comment data."""
    con = duckdb.connect(":memory:")
    data = [
        # T6 deep comment
        {"viewer_hash": "v20_t6", "vtuber_channel_id": "UC_A", "video_id": "vid_stream_1", "source_type": "comment", "interaction_at": "2024-02-01T12:00:00Z", "provenance": "t6_deep", "priority": 1},
        # Legacy comment on same stream (must be suppressed by T6 comment)
        {"viewer_hash": "v21_leg_c", "vtuber_channel_id": "UC_A", "video_id": "vid_stream_1", "source_type": "comment", "first_seen": "2024-02-01T13:00:00Z", "provenance": "legacy", "priority": 4},
        # Legacy live chat on same stream (MUST BE PRESERVED)
        {"viewer_hash": "v22_leg_chat", "vtuber_channel_id": "UC_A", "video_id": "vid_stream_1", "source_type": "live_chat", "first_seen": "2024-02-01T10:30:00Z", "provenance": "legacy", "priority": 4},
    ]
    con.register("test_raw", pa.Table.from_pylist(data))
    build_canonical_events_view(con, "test_raw")

    rows = con.execute("SELECT viewer_hash, source_type, provenance FROM canonical_events ORDER BY source_type").fetchall()
    assert len(rows) == 2, f"Expected exactly 2 rows (T6 comment + Legacy live_chat), got {len(rows)}: {rows}"
    
    # 1. T6 comment preserved
    c_row = [r for r in rows if r[1] == "comment"][0]
    assert c_row[0] == "v20_t6"
    assert c_row[2] == "t6_deep"

    # 2. Legacy live chat preserved
    chat_row = [r for r in rows if r[1] == "live_chat"][0]
    assert chat_row[0] == "v22_leg_chat"
    assert chat_row[2] == "legacy"


def test_same_viewer_video_comment_presence_not_double_counted():
    """Rule 4: Same viewer/video comment presence is not double counted; earliest timestamp is preserved."""
    con = duckdb.connect(":memory:")
    data = [
        # Viewer 30 comments twice on the same video in legacy
        {"viewer_hash": "v30", "vtuber_channel_id": "UC_A", "video_id": "vid_rep_1", "source_type": "comment", "first_seen": "2023-03-01T10:00:00Z", "provenance": "legacy", "priority": 4},
        {"viewer_hash": "v30", "vtuber_channel_id": "UC_A", "video_id": "vid_rep_1", "source_type": "comment", "first_seen": "2023-03-01T15:00:00Z", "provenance": "legacy", "priority": 4},
    ]
    con.register("test_raw", pa.Table.from_pylist(data))
    build_canonical_events_view(con, "test_raw")

    rows = con.execute("SELECT viewer_hash, interaction_time FROM canonical_events").fetchall()
    assert len(rows) == 1, f"Expected 1 deduplicated row, got {len(rows)}"
    ts = rows[0][1]
    ts_utc = ts.astimezone(timezone.utc) if hasattr(ts, "astimezone") else ts
    assert "2023-03-01 10:00:00" in str(ts_utc)


def test_different_videos_remain_independent():
    """Rule 5: Precedence filtering on one video does not affect comments on different videos."""
    con = duckdb.connect(":memory:")
    data = [
        # Video Alpha has T6 comments
        {"viewer_hash": "v_alpha", "vtuber_channel_id": "UC_A", "video_id": "vid_alpha", "source_type": "comment", "interaction_at": "2023-01-01T10:00:00Z", "provenance": "t6_deep", "priority": 1},
        # Video Beta has T5 comments
        {"viewer_hash": "v_beta", "vtuber_channel_id": "UC_A", "video_id": "vid_beta", "source_type": "comment", "interaction_at": "2023-02-01T10:00:00Z", "provenance": "t5_stratified", "priority": 2},
        # Video Gamma has Legacy comments
        {"viewer_hash": "v_gamma", "vtuber_channel_id": "UC_A", "video_id": "vid_gamma", "source_type": "comment", "first_seen": "2023-03-01T10:00:00Z", "provenance": "legacy", "priority": 4},
    ]
    con.register("test_raw", pa.Table.from_pylist(data))
    build_canonical_events_view(con, "test_raw")

    rows = con.execute("SELECT video_id, provenance FROM canonical_events ORDER BY video_id").fetchall()
    assert len(rows) == 3
    assert rows[0] == ("vid_alpha", "t6_deep")
    assert rows[1] == ("vid_beta", "t5_stratified")
    assert rows[2] == ("vid_gamma", "legacy")


def test_strong_overlap_requires_at_least_two_distinct_videos():
    """Rule 6: Strong overlap still requires >= 2 DISTINCT videos per channel; repeated comments on 1 video do not count."""
    con = duckdb.connect(":memory:")
    data = [
        # Viewer 40: 3 comments on 1 video for UC_A, 3 comments on 1 video for UC_B
        {"viewer_hash": "v40_repeat", "vtuber_channel_id": "UC_A", "video_id": "vid_A1", "source_type": "comment", "interaction_at": "2024-04-01T10:00:00Z"},
        {"viewer_hash": "v40_repeat", "vtuber_channel_id": "UC_A", "video_id": "vid_A1", "source_type": "comment", "interaction_at": "2024-04-01T11:00:00Z"},
        {"viewer_hash": "v40_repeat", "vtuber_channel_id": "UC_B", "video_id": "vid_B1", "source_type": "comment", "interaction_at": "2024-04-01T12:00:00Z"},
        {"viewer_hash": "v40_repeat", "vtuber_channel_id": "UC_B", "video_id": "vid_B1", "source_type": "comment", "interaction_at": "2024-04-01T13:00:00Z"},

        # Viewer 41: 1 comment on vid_A1 + 1 comment on vid_A2; 1 comment on vid_B1 + 1 comment on vid_B2
        {"viewer_hash": "v41_strong", "vtuber_channel_id": "UC_A", "video_id": "vid_A1", "source_type": "comment", "interaction_at": "2024-04-02T10:00:00Z"},
        {"viewer_hash": "v41_strong", "vtuber_channel_id": "UC_A", "video_id": "vid_A2", "source_type": "comment", "interaction_at": "2024-04-03T10:00:00Z"},
        {"viewer_hash": "v41_strong", "vtuber_channel_id": "UC_B", "video_id": "vid_B1", "source_type": "comment", "interaction_at": "2024-04-02T11:00:00Z"},
        {"viewer_hash": "v41_strong", "vtuber_channel_id": "UC_B", "video_id": "vid_B2", "source_type": "comment", "interaction_at": "2024-04-03T11:00:00Z"},
    ]
    con.register("test_raw", pa.Table.from_pylist(data))
    build_canonical_events_view(con, "test_raw")

    cov_map = {}
    snap = compute_window_snapshots(con, {"type": "yearly", "start": "2024-01-01", "end": "2024-12-31 23:59:59"}, cov_map)
    assert len(snap) == 1
    edge = snap[0]

    assert edge["shared_comments"] == 2  # Both v40 and v41 are shared
    assert edge["strong_shared_comments"] == 1  # ONLY v41 has >= 2 distinct videos on both channels!
    assert edge["strong_shared_any"] == 1


def test_temporal_timestamps_unchanged_and_no_fallback_to_published_at():
    """Rule 7: Temporal timestamps are strictly preserved; video_published_at is NEVER used as fallback."""
    con = duckdb.connect(":memory:")
    data = [
        # Modern interaction on historical 2021 video
        {"viewer_hash": "v50", "vtuber_channel_id": "UC_A", "video_id": "vid_2021", "source_type": "comment", "interaction_at": "2025-06-01T12:00:00Z", "video_published_at": "2021-01-01T00:00:00Z"},
        # Missing interaction timestamp on historical 2021 video
        {"viewer_hash": "v51", "vtuber_channel_id": "UC_A", "video_id": "vid_2021", "source_type": "comment", "interaction_at": None, "video_published_at": "2021-01-01T00:00:00Z"},
    ]
    con.register("test_raw", pa.Table.from_pylist(data))
    build_canonical_events_view(con, "test_raw")

    rows = con.execute("SELECT viewer_hash, interaction_time, video_published_at, interaction_time_source FROM canonical_events ORDER BY viewer_hash").fetchall()
    assert len(rows) == 2

    # v50 has exact 2025 interaction time
    assert "2025-06-01" in str(rows[0][1])
    assert "2021-01-01" in str(rows[0][2])
    assert rows[0][3] == "interaction_at"

    # v51 has NULL interaction time and 'missing' source, NOT video_published_at
    assert rows[1][1] is None
    assert "2021-01-01" in str(rows[1][2])
    assert rows[1][3] == "missing"

    # In window snapshot: 2021 window must have 0 events
    cov_map = {}
    snap_2021 = compute_window_snapshots(con, {"type": "yearly", "start": "2021-01-01", "end": "2021-12-31 23:59:59"}, cov_map)
    assert len(snap_2021) == 0

    # 2025 window must contain v50
    snap_2025 = compute_window_snapshots(con, {"type": "yearly", "start": "2025-01-01", "end": "2025-12-31 23:59:59"}, cov_map)
    # Since only 1 channel exists in data, no pairwise edge, but filtered_events has 1 row
    ev_2025 = con.execute("SELECT COUNT(*) FROM canonical_events WHERE interaction_time >= '2025-01-01' AND interaction_time <= '2025-12-31'").fetchone()[0]
    assert ev_2025 == 1
