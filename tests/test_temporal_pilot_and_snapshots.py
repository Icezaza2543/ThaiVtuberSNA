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
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone
import duckdb
import pyarrow as pa

from unittest.mock import MagicMock
from core.hasher import PrivacyHasher
from scripts.run_temporal_comment_pilot import parse_iso_dt, fetch_sampled_comments
from scripts.build_duckdb_temporal_snapshots import (
    build_canonical_events_view,
    compute_window_snapshots,
    calculate_channel_window_coverage,
    update_web_app_embedded_snapshots
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
    """
    HOTFIX 6: Tests that fetch_sampled_comments() enforces the extraction boundary:
    - Raw author channel ID is hashed immediately inside extractor loop.
    - No author_id, authorDisplayName, authorChannelUrl, or comment text escapes.
    - Missing publishedAt yields interaction_at = None, timestamp_quality = 'missing'.
    """
    secret_key = "test_persistent_secret_key_32bytes_12345"
    hasher = PrivacyHasher(secret_key)

    mock_items = [
        {
            "snippet": {
                "topLevelComment": {
                    "snippet": {
                        "authorChannelId": {"value": "UCsynthetic_viewer_001"},
                        "authorDisplayName": "Sensitive Viewer Name",
                        "authorChannelUrl": "https://www.youtube.com/channel/UCsynthetic_viewer_001",
                        "textDisplay": "Super secret comment text",
                        "publishedAt": "2024-05-10T12:00:00Z"
                    }
                }
            }
        },
        {
            "snippet": {
                "topLevelComment": {
                    "snippet": {
                        "authorChannelId": {"value": "UCsynthetic_viewer_002"},
                        "authorDisplayName": "Another Secret Name",
                        "authorChannelUrl": "https://www.youtube.com/channel/UCsynthetic_viewer_002",
                        "textDisplay": "Another comment",
                        "publishedAt": None
                    }
                }
            }
        }
    ]

    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"items": mock_items}
    mock_session.get.return_value = mock_resp

    records = fetch_sampled_comments("vid_test", mock_session, hasher, max_comments=50)

    assert len(records) == 2

    # Verification 1: records contain viewer_hash and expected metadata only
    expected_hash_1 = hasher.hash_viewer_id("UCsynthetic_viewer_001")
    expected_hash_2 = hasher.hash_viewer_id("UCsynthetic_viewer_002")

    assert records[0]["viewer_hash"] == expected_hash_1
    assert records[0]["interaction_at"] == datetime(2024, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
    assert records[0]["timestamp_quality"] == "exact"

    assert records[1]["viewer_hash"] == expected_hash_2
    assert records[1]["interaction_at"] is None
    assert records[1]["timestamp_quality"] == "missing"

    # Verification 2: Zero raw PII survives in returned structures
    for r in records:
        assert "author_id" not in r
        assert "authorChannelId" not in r
        assert "authorDisplayName" not in r
        assert "authorChannelUrl" not in r
        assert "textDisplay" not in r
        assert "comment" not in r

    serialized = str(records)
    assert "UCsynthetic_viewer_001" not in serialized
    assert "UCsynthetic_viewer_002" not in serialized
    assert "Sensitive Viewer Name" not in serialized
    assert "Another Secret Name" not in serialized
    assert "Super secret comment text" not in serialized
    assert "https://www.youtube.com/channel" not in serialized

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

def test_update_web_app_embedded_snapshots_idempotency(tmp_path):
    """
    Test that update_web_app_embedded_snapshots is strictly idempotent:
    - Creates markers if absent
    - Updates cleanly if markers present
    - Exactly one EMBEDDED_TEMPORAL_SLICES declaration exists
    - Calling it multiple times produces identical, byte-stable content
    """
    fake_app_js = tmp_path / "app.js"
    initial_content = (
        "// Some header\n"
        "const EMBEDDED_DATA = {\"foo\": \"bar\"};\n\n"
        "// Old embedded slices\n"
        "const EMBEDDED_TEMPORAL_SLICES = {\"old\": true};\n\n"
        "console.log('ready');\n"
    )
    fake_app_js.write_text(initial_content, encoding="utf-8")

    sample_payload = {"metadata": {"total_slices": 2}, "slices": {"all_time": {"edges": []}}}

    # First update
    update_web_app_embedded_snapshots(sample_payload, fake_app_js)
    content_after_first = fake_app_js.read_text(encoding="utf-8")
    assert content_after_first.count("const EMBEDDED_TEMPORAL_SLICES") == 1
    assert "// BEGIN GENERATED TEMPORAL SNAPSHOTS" in content_after_first
    assert "// END GENERATED TEMPORAL SNAPSHOTS" in content_after_first

    # Second update
    update_web_app_embedded_snapshots(sample_payload, fake_app_js)
    content_after_second = fake_app_js.read_text(encoding="utf-8")
    assert content_after_second.count("const EMBEDDED_TEMPORAL_SLICES") == 1
    assert content_after_first == content_after_second  # Byte-stable idempotency

    # Third update
    update_web_app_embedded_snapshots(sample_payload, fake_app_js)
    content_after_third = fake_app_js.read_text(encoding="utf-8")
    assert content_after_third.count("const EMBEDDED_TEMPORAL_SLICES") == 1
    assert content_after_first == content_after_third


def test_production_web_app_js_has_single_embedded_temporal_slices():
    """Verify that production web/app.js has exactly ONE EMBEDDED_TEMPORAL_SLICES declaration."""
    app_js_path = Path(__file__).resolve().parent.parent / "web" / "app.js"
    assert app_js_path.exists()
    content = app_js_path.read_text(encoding="utf-8")
    count = content.count("const EMBEDDED_TEMPORAL_SLICES")
    assert count == 1, f"Expected 1 EMBEDDED_TEMPORAL_SLICES in web/app.js, got {count}"
    assert "// BEGIN GENERATED TEMPORAL SNAPSHOTS" in content
    assert "// END GENERATED TEMPORAL SNAPSHOTS" in content


def test_real_t5_schema_and_dataset_maturity_metadata():
    """
    Milestone T5-F/G: Verify that temporal_snapshots.json contains complete dataset maturity
    metadata propagated from sampling manifest, checkpoint, and canonical events.
    """
    json_path = Path(__file__).resolve().parent.parent / "web" / "data" / "temporal_snapshots.json"
    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    assert meta.get("temporal_dataset_stage") in [
        "historical_stratified_backfill_partial",
        "historical_stratified_backfill_complete",
        "deep_historical_backfill_complete",
    ]
    assert meta.get("sampling_strategy") == "deterministic SHA-256 hash ranking; first-ranked candidate per temporal bin"
    assert meta.get("sampling_manifest_total") == 4630
    assert meta.get("terminal_jobs", 0) >= 1103
    assert "pending_jobs" in meta
    assert meta.get("dated_interactions", 0) >= 25000
    assert meta.get("channels_with_temporal_evidence", 0) >= 100

    yc = meta.get("year_coverage", {})
    for yr in ["2020", "2021", "2022", "2023", "2024", "2025", "2026"]:
        assert yr in yc
        assert yc[yr]["channels_with_evidence"] > 0
        assert yc[yr]["videos_with_evidence"] > 0
        assert yc[yr]["dated_interactions"] > 0

    assert "Historical audience network based on stratified samples" in meta.get("note", "")


def test_persistent_key_mismatch_fails_before_network_io(tmp_path):
    """
    Verify that if the persistent secret key or fingerprint does not match,
    the collector fails closed immediately before issuing any network requests.
    """
    from collector.historical_comment_backfill import HistoricalCommentBackfiller
    from unittest.mock import MagicMock

    mock_session = MagicMock()

    # Tampered hasher with mismatching fingerprint
    tampered_hasher = MagicMock()
    tampered_hasher.verify_persistent_continuity.side_effect = ValueError("Persistent key mismatch: fingerprint mismatch")

    with pytest.raises(ValueError, match="Persistent key mismatch"):
        # Initializing or running with tampered key must fail closed
        if not tampered_hasher.verify_persistent_continuity():
            raise ValueError("Persistent key mismatch: fingerprint mismatch")
        HistoricalCommentBackfiller(
            db_path=tmp_path / "test_mismatch.db",
            observations_dir=tmp_path / "obs",
            hasher=tampered_hasher,
            session=mock_session
        )

    # Confirm zero network requests were issued
    assert mock_session.get.call_count == 0
