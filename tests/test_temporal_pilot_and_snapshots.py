"""
Unit & Regression Tests for Phase T2 (Comment Pilot) and Phase T3 (DuckDB Temporal Engine)
Tests directly execute production snapshot functions from scripts/build_duckdb_temporal_snapshots.py.

Regression Cases:
1. Missing interaction timestamp: video_published_at = 2021, interaction_at = None.
   Must be excluded from all temporal slices; never placed based on video_published_at.
2. Old video, modern interaction: video_published_at = 2021, interaction_at = 2025.
   Audience interaction window belongs to 2025, NOT 2021.
3. Cumulative behavior: interaction in 2022 is absent from 2020/2021 cumulative, present in through-2022+.
4. Source separation & strong overlap: verifies independent comment vs live-chat calculation and distinct video thresholds.
5. Coverage: exact mathematical coverage (1.0 vs 0.0) per window based on T1 termination reason and oldest upload.
6. Buddhist Era normalization: Thai BE 2569 -> 2026, while normal CE 2024 remains 2024.
"""
import pytest
from datetime import datetime, timezone
import duckdb
import pyarrow as pa

from core.hasher import PrivacyHasher
from scripts.run_temporal_comment_pilot import parse_iso_dt
from scripts.build_duckdb_temporal_snapshots import (
    build_canonical_events_view,
    compute_window_snapshots,
    calculate_channel_window_coverage
)

def test_comment_timestamp_strict_no_fallback():
    """Missing or corrupted timestamps must yield None, never now()."""
    assert parse_iso_dt(None) is None
    assert parse_iso_dt("") is None
    assert parse_iso_dt("invalid_iso_string") is None

    valid_str = "2023-06-15T14:30:00Z"
    dt = parse_iso_dt(valid_str)
    assert dt is not None
    assert dt.year == 2023
    assert dt.month == 6
    assert dt.day == 15
    assert dt.tzinfo == timezone.utc

def test_privacy_extraction_boundary_no_raw_id_leak():
    """Ensures raw viewer channel ID is transformed to HMAC hash."""
    secret_key = "test_persistent_secret_key_32bytes_12345"
    hasher = PrivacyHasher(secret_key)

    raw_author_id = "UCraw_test_viewer_channel_999"
    viewer_hash = hasher.hash_viewer_id(raw_author_id)

    assert viewer_hash != raw_author_id
    assert len(viewer_hash) == 64
    assert not viewer_hash.startswith("UC")
    assert hasher.hash_viewer_id(raw_author_id) == viewer_hash

def test_regression_case_1_missing_interaction_timestamp_excluded():
    """
    Case 1: Synthetic comment with video_published_at = 2021, but interaction_at = NULL.
    Must NOT be present in 2021 audience-interaction snapshot, nor any other year.
    video_published_at must NEVER be used as interaction_time.
    """
    con = duckdb.connect(":memory:")
    data = [
        {"viewer_hash": "v_missing_1", "vtuber_channel_id": "UC_A", "video_id": "v1", "source_type": "comment", "interaction_at": None, "video_published_at": "2021-06-15T10:00:00Z"},
        {"viewer_hash": "v_missing_1", "vtuber_channel_id": "UC_B", "video_id": "v2", "source_type": "comment", "interaction_at": None, "video_published_at": "2021-06-15T10:00:00Z"},
    ]
    tbl = pa.Table.from_pylist(data)
    con.register("test_raw", tbl)
    build_canonical_events_view(con, "test_raw")

    # Verify canonical columns
    res = con.execute("SELECT viewer_hash, interaction_time, video_published_at, interaction_time_source, timestamp_quality FROM canonical_events").fetchall()
    assert len(res) == 2
    for r in res:
        assert r[1] is None  # interaction_time is NULL
        assert r[2] is not None  # video_published_at is preserved
        assert r[3] == "missing"
        assert r[4] == "missing"

    # Test windows: 2021 yearly, 2022 yearly, All-Time
    cov_map = {}
    snap_2021 = compute_window_snapshots(con, {"type": "yearly", "start": "2021-01-01", "end": "2021-12-31 23:59:59"}, cov_map)
    assert len(snap_2021) == 0, "Missing interaction_at must NOT appear in 2021 slice!"

    snap_2022 = compute_window_snapshots(con, {"type": "yearly", "start": "2022-01-01", "end": "2022-12-31 23:59:59"}, cov_map)
    assert len(snap_2022) == 0, "Missing interaction_at must NOT appear in 2022 slice!"

    snap_all = compute_window_snapshots(con, {"type": "all_time", "start": "2020-01-01", "end": "2026-09-08 23:59:59"}, cov_map)
    assert len(snap_all) == 0, "Missing interaction_at must NOT appear in dated All-Time slice!"

def test_regression_case_2_old_video_modern_interaction():
    """
    Case 2: video_published_at = 2021, interaction_at = 2025.
    Audience interaction belongs to 2025 slice, NOT 2021.
    """
    con = duckdb.connect(":memory:")
    data = [
        {"viewer_hash": "v_lag_1", "vtuber_channel_id": "UC_A", "video_id": "v1", "source_type": "comment", "interaction_at": "2025-08-12T14:00:00Z", "video_published_at": "2021-05-10T12:00:00Z"},
        {"viewer_hash": "v_lag_1", "vtuber_channel_id": "UC_B", "video_id": "v2", "source_type": "comment", "interaction_at": "2025-08-12T15:00:00Z", "video_published_at": "2021-05-10T12:00:00Z"},
    ]
    con.register("test_raw", pa.Table.from_pylist(data))
    build_canonical_events_view(con, "test_raw")

    cov_map = {}
    snap_2021 = compute_window_snapshots(con, {"type": "yearly", "start": "2021-01-01", "end": "2021-12-31 23:59:59"}, cov_map)
    assert len(snap_2021) == 0, "2025 interaction must NOT appear in 2021 slice even if video is from 2021!"

    snap_2025 = compute_window_snapshots(con, {"type": "yearly", "start": "2025-01-01", "end": "2025-12-31 23:59:59"}, cov_map)
    assert len(snap_2025) == 1, "2025 interaction MUST appear in 2025 slice!"
    assert snap_2025[0]["shared_comments"] == 1

def test_regression_case_3_cumulative_behavior():
    """
    Case 3: Interaction in 2022.
    Must NOT be in cumulative through-2021.
    Must BE in cumulative through-2022.
    Must BE in cumulative through-2023+.
    """
    con = duckdb.connect(":memory:")
    data = [
        {"viewer_hash": "v_cum_1", "vtuber_channel_id": "UC_A", "video_id": "v1", "source_type": "comment", "interaction_at": "2022-04-10T08:00:00Z"},
        {"viewer_hash": "v_cum_1", "vtuber_channel_id": "UC_B", "video_id": "v2", "source_type": "comment", "interaction_at": "2022-04-10T09:00:00Z"},
    ]
    con.register("test_raw", pa.Table.from_pylist(data))
    build_canonical_events_view(con, "test_raw")

    cov_map = {}
    cum_2021 = compute_window_snapshots(con, {"type": "cumulative", "start": "2020-01-01", "end": "2021-12-31 23:59:59"}, cov_map)
    assert len(cum_2021) == 0, "2022 interaction must NOT be in cumulative through-2021!"

    cum_2022 = compute_window_snapshots(con, {"type": "cumulative", "start": "2020-01-01", "end": "2022-12-31 23:59:59"}, cov_map)
    assert len(cum_2022) == 1, "2022 interaction MUST be in cumulative through-2022!"

    cum_2025 = compute_window_snapshots(con, {"type": "cumulative", "start": "2020-01-01", "end": "2025-12-31 23:59:59"}, cov_map)
    assert len(cum_2025) == 1, "2022 interaction MUST persist in cumulative through-2025!"

def test_regression_case_4_source_separation_and_strong_overlap():
    """
    Case 4: Preserves evidence separation (comment vs live-chat) and strong overlap (>= 2 distinct videos).
    """
    con = duckdb.connect(":memory:")
    data = [
        # Viewer 1: Weak comment (1 video each)
        {"viewer_hash": "v1", "vtuber_channel_id": "UC_A", "video_id": "vA1", "source_type": "comment", "interaction_at": "2024-03-01T10:00:00Z"},
        {"viewer_hash": "v1", "vtuber_channel_id": "UC_B", "video_id": "vB1", "source_type": "comment", "interaction_at": "2024-03-01T11:00:00Z"},
        # Viewer 2: Strong comment (2 distinct videos each)
        {"viewer_hash": "v2", "vtuber_channel_id": "UC_A", "video_id": "vA1", "source_type": "comment", "interaction_at": "2024-03-02T10:00:00Z"},
        {"viewer_hash": "v2", "vtuber_channel_id": "UC_A", "video_id": "vA2", "source_type": "comment", "interaction_at": "2024-03-03T10:00:00Z"},
        {"viewer_hash": "v2", "vtuber_channel_id": "UC_B", "video_id": "vB1", "source_type": "comment", "interaction_at": "2024-03-02T11:00:00Z"},
        {"viewer_hash": "v2", "vtuber_channel_id": "UC_B", "video_id": "vB2", "source_type": "comment", "interaction_at": "2024-03-03T11:00:00Z"},
        # Viewer 3: Weak live chat (1 stream each)
        {"viewer_hash": "v3", "vtuber_channel_id": "UC_A", "video_id": "vA3", "source_type": "live_chat", "interaction_at": "2024-03-04T12:00:00Z"},
        {"viewer_hash": "v3", "vtuber_channel_id": "UC_B", "video_id": "vB3", "source_type": "live_chat", "interaction_at": "2024-03-04T13:00:00Z"},
        # Viewer 4: Strong live chat (2 distinct streams each)
        {"viewer_hash": "v4", "vtuber_channel_id": "UC_A", "video_id": "vA3", "source_type": "live_chat", "interaction_at": "2024-03-05T12:00:00Z"},
        {"viewer_hash": "v4", "vtuber_channel_id": "UC_A", "video_id": "vA4", "source_type": "live_chat", "interaction_at": "2024-03-06T12:00:00Z"},
        {"viewer_hash": "v4", "vtuber_channel_id": "UC_B", "video_id": "vB3", "source_type": "live_chat", "interaction_at": "2024-03-05T13:00:00Z"},
        {"viewer_hash": "v4", "vtuber_channel_id": "UC_B", "video_id": "vB4", "source_type": "live_chat", "interaction_at": "2024-03-06T13:00:00Z"},
    ]
    con.register("test_raw", pa.Table.from_pylist(data))
    build_canonical_events_view(con, "test_raw")

    cov_map = {}
    snap = compute_window_snapshots(con, {"type": "yearly", "start": "2024-01-01", "end": "2024-12-31 23:59:59"}, cov_map)
    assert len(snap) == 1
    r = snap[0]

    assert r["shared_any"] == 4  # v1, v2, v3, v4
    assert r["shared_comments"] == 2  # v1, v2
    assert r["shared_live_chat"] == 2  # v3, v4
    assert r["strong_shared_any"] == 2  # v2, v4
    assert r["strong_shared_comments"] == 1  # v2 only
    assert r["strong_shared_live_chat"] == 1  # v4 only

def test_regression_case_5_exact_mathematical_channel_coverage():
    """
    Case 5: Mathematical coverage determination.
    - PLAYLIST_EXHAUSTED -> 1.0
    - NO_VIDEOS -> 1.0
    - CUTOFF_REACHED -> 1.0 for window_start >= 2020-01-01
    - CAP_REACHED with oldest <= window_start -> 1.0
    - CAP_REACHED with oldest > window_start -> 0.0
    - Missing channel -> 0.0
    """
    mock_cov = {
        "cid_exhausted": {"termination_reason": "PLAYLIST_EXHAUSTED", "oldest_video_published_at": "2023-05-01"},
        "cid_no_vids": {"termination_reason": "NO_VIDEOS", "oldest_video_published_at": None},
        "cid_cutoff": {"termination_reason": "CUTOFF_REACHED", "oldest_video_published_at": "2019-12-28"},
        "cid_cap_early": {"termination_reason": "CAP_REACHED", "oldest_video_published_at": "2021-06-15"},
        "cid_cap_late": {"termination_reason": "CAP_REACHED", "oldest_video_published_at": "2024-01-10"},
    }

    # PLAYLIST_EXHAUSTED is complete for any window
    assert calculate_channel_window_coverage("cid_exhausted", "2020-01-01", mock_cov) == 1.0
    assert calculate_channel_window_coverage("cid_exhausted", "2024-01-01", mock_cov) == 1.0

    # NO_VIDEOS is complete for any window
    assert calculate_channel_window_coverage("cid_no_vids", "2020-01-01", mock_cov) == 1.0

    # CUTOFF_REACHED is complete for 2020-01-01 onward
    assert calculate_channel_window_coverage("cid_cutoff", "2020-01-01", mock_cov) == 1.0
    assert calculate_channel_window_coverage("cid_cutoff", "2025-01-01", mock_cov) == 1.0

    # CAP_REACHED with oldest = 2021-06-15:
    # In window 2020-01-01: oldest > 2020-01-01, so NOT provably complete (0.0)
    assert calculate_channel_window_coverage("cid_cap_early", "2020-01-01", mock_cov) == 0.0
    # In window 2022-01-01: oldest <= 2022-01-01, so provably complete (1.0)
    assert calculate_channel_window_coverage("cid_cap_early", "2022-01-01", mock_cov) == 1.0

    # CAP_REACHED with oldest = 2024-01-10:
    assert calculate_channel_window_coverage("cid_cap_late", "2023-01-01", mock_cov) == 0.0
    assert calculate_channel_window_coverage("cid_cap_late", "2025-01-01", mock_cov) == 1.0

    # Unknown channel -> 0.0
    assert calculate_channel_window_coverage("cid_unknown", "2024-01-01", mock_cov) == 0.0

def test_regression_case_6_buddhist_era_normalization():
    """
    Case 6: Buddhist Era normalization.
    Thai Windows locale timestamps with year 2569 -> normalized to 2026.
    Normal CE 2024 remains 2024.
    """
    con = duckdb.connect(":memory:")
    data = [
        {"viewer_hash": "v_be", "vtuber_channel_id": "UC_A", "video_id": "v1", "source_type": "comment", "interaction_at": "2569-08-15T12:00:00Z"},
        {"viewer_hash": "v_ce", "vtuber_channel_id": "UC_A", "video_id": "v2", "source_type": "comment", "interaction_at": "2024-08-15T12:00:00Z"},
    ]
    con.register("test_raw", pa.Table.from_pylist(data))
    build_canonical_events_view(con, "test_raw")

    res = con.execute("SELECT viewer_hash, interaction_time FROM canonical_events ORDER BY viewer_hash").fetchall()
    assert len(res) == 2
    # v_be normalized from 2569 to 2026
    assert res[0][0] == "v_be"
    assert res[0][1].year == 2026
    # v_ce preserved at 2024
    assert res[1][0] == "v_ce"
    assert res[1][1].year == 2024
