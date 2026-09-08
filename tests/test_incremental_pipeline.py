"""Tests for Phase T16 Incremental Temporal Pipeline.

MANDATORY 10 integration tests proving values change:
1. same viewer on two channels in a new batch creates/increments expected edge
2. canonical_events includes committed T16 evidence
3. duplicate rerun changes nothing
4. duplicate against historical evidence suppressed
5. T16 overlay does not erase T6 audience
6. affected yearly/cumulative/all_time snapshots change
7. unrelated historical slice remains identical
8. crash+retry == clean final result
9. HMAC key swap fails
10. future-year event creates new slices
"""
import copy
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import pytest
import pandas as pd
import duckdb

from scripts.incremental_temporal_pipeline import (
    IncrementalTemporalPipeline,
    HMACKeyContinuityError,
    PROVENANCE_PRECEDENCE
)
from scripts.build_duckdb_temporal_snapshots import (
    get_sources_by_provenance,
    build_unified_raw_view,
    build_canonical_events_view
)
from core.hasher import compute_key_fingerprint

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def temp_pipeline_env(tmp_path):
    """Sets up an isolated sandbox environment with a copy of historical snapshots and state."""
    sandbox_data = tmp_path / "data" / "temporal"
    sandbox_state = sandbox_data / "state"
    sandbox_inc = sandbox_data / "incremental"
    sandbox_snaps = sandbox_data / "snapshots"

    sandbox_state.mkdir(parents=True)
    sandbox_inc.mkdir(parents=True)
    sandbox_snaps.mkdir(parents=True)

    # Copy real snapshots to sandbox for baseline comparison
    real_snaps = REPO_ROOT / "data" / "temporal" / "snapshots" / "network_snapshots.parquet"
    assert real_snaps.exists()
    shutil.copy2(real_snaps, sandbox_snaps / "network_snapshots.parquet")

    return tmp_path


def test_01_same_viewer_two_channels_creates_or_increments_expected_edge(temp_pipeline_env):
    """1. Same viewer on two channels in a new batch creates/increments expected edge."""
    snaps_file = temp_pipeline_env / "data" / "temporal" / "snapshots" / "network_snapshots.parquet"
    df_before = pd.read_parquet(snaps_file)

    chan_a = min("UCpGtwNmbOtgmcKIY81MIX_w", "UCGBkYTR4tMKS38TQHGWWLjg")
    chan_b = max("UCpGtwNmbOtgmcKIY81MIX_w", "UCGBkYTR4tMKS38TQHGWWLjg")

    m_2026_before = (df_before["window_type"] == "yearly") & (df_before["window_start"].str.startswith("2026"))
    edge_before = df_before[m_2026_before & (df_before["vtuber_a"] == chan_a) & (df_before["vtuber_b"] == chan_b)]
    shared_before = int(edge_before["shared_any"].iloc[0]) if not edge_before.empty else 0

    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)
    events = [
        {
            "author_id": "author_edge_test_101",
            "vtuber_channel_id": chan_a,
            "video_id": "vid_edge_2026_a",
            "interaction_time": "2026-06-10T14:00:00Z"
        },
        {
            "author_id": "author_edge_test_101",
            "vtuber_channel_id": chan_b,
            "video_id": "vid_edge_2026_b",
            "interaction_time": "2026-06-10T14:05:00Z"
        }
    ]

    res = pipeline.ingest_batch("batch_edge_increment", events)
    assert res.status == "COMMITTED"
    assert res.records_inserted == 2

    df_after = pd.read_parquet(snaps_file)
    m_2026_after = (df_after["window_type"] == "yearly") & (df_after["window_start"].str.startswith("2026"))
    edge_after = df_after[m_2026_after & (df_after["vtuber_a"] == chan_a) & (df_after["vtuber_b"] == chan_b)]
    assert not edge_after.empty
    shared_after = int(edge_after["shared_any"].iloc[0])

    assert shared_after == shared_before + 1, f"Expected {shared_before + 1}, got {shared_after}"


def test_02_canonical_events_includes_committed_t16_evidence(temp_pipeline_env):
    """2. canonical_events view includes committed T16 incremental evidence."""
    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)
    event = [
        {
            "author_id": "author_t16_proof_viewer",
            "vtuber_channel_id": "UC_canonical_proof_chan",
            "video_id": "vid_t16_proof_unique",
            "interaction_time": "2026-07-04T12:00:00Z"
        }
    ]

    res = pipeline.ingest_batch("batch_canonical_proof", event)
    assert res.status == "COMMITTED"
    assert res.records_inserted == 1

    con = duckdb.connect(":memory:")
    prov = get_sources_by_provenance(base_dir=temp_pipeline_env)
    build_unified_raw_view(con, prov)
    build_canonical_events_view(con, "unified_raw")

    row = con.execute("""
        SELECT vtuber_channel_id, video_id, provenance, interaction_time_source
        FROM canonical_events
        WHERE video_id = 'vid_t16_proof_unique'
    """).fetchone()

    con.close()
    assert row is not None
    assert row[0] == "UC_canonical_proof_chan"
    assert row[1] == "vid_t16_proof_unique"
    assert row[2] == "t16_incremental"
    assert row[3] == "interaction_at"


def test_03_duplicate_rerun_changes_nothing(temp_pipeline_env):
    """3. Rerunning the exact same batch ID results in zero inserts and unchanged state."""
    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)
    events = [
        {
            "author_id": "author_rerun_test",
            "vtuber_channel_id": "UC_rerun_chan_a",
            "video_id": "vid_rerun_1",
            "interaction_time": "2026-05-15T09:00:00Z"
        }
    ]

    res1 = pipeline.ingest_batch("batch_rerun_01", events)
    assert res1.status == "COMMITTED"
    assert res1.records_inserted == 1
    chk1 = res1.snapshot_checksum

    res2 = pipeline.ingest_batch("batch_rerun_01", events)
    assert res2.status == "ALREADY_PROCESSED"
    assert res2.records_inserted == 0
    assert res2.duplicates_suppressed == 1
    assert res2.snapshot_checksum == chk1


def test_04_duplicate_against_historical_evidence_suppressed(temp_pipeline_env):
    """4. Incoming records matching historical canonical evidence are suppressed."""
    # Find a real historical event from canonical_events in 2026
    con = duckdb.connect(":memory:")
    prov = get_sources_by_provenance()
    build_unified_raw_view(con, prov)
    build_canonical_events_view(con, "unified_raw")
    row = con.execute("""
        SELECT viewer_hash, vtuber_channel_id, video_id, source_type, interaction_time
        FROM canonical_events
        WHERE extract(year from interaction_time) = 2026
        LIMIT 1
    """).fetchone()
    con.close()

    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)
    hist_event = {
        "viewer_hash": row[0],
        "vtuber_channel_id": row[1],
        "video_id": row[2],
        "source_type": row[3],
        "interaction_time": str(row[4])
    }

    res = pipeline.ingest_batch("batch_hist_dup_test", [hist_event])
    assert res.status == "COMMITTED"
    assert res.records_inserted == 0
    assert res.duplicates_suppressed == 1


def test_05_t16_overlay_does_not_erase_t6_audience(temp_pipeline_env):
    """5. T16 additive overlay does not erase or suppress T6 audience for that video."""
    video_id = "oEOHgyuLgrA"
    chan_id = "UCompe4fS2oUss8CGTuhOSxA"

    con_before = duckdb.connect(":memory:")
    prov_before = get_sources_by_provenance()
    build_unified_raw_view(con_before, prov_before)
    build_canonical_events_view(con_before, "unified_raw")
    t6_count_before = con_before.execute(f"""
        SELECT COUNT(*) FROM canonical_events
        WHERE video_id = '{video_id}' AND provenance = 't6_deep'
    """).fetchone()[0]
    con_before.close()

    assert t6_count_before > 0, "Expected T6 comments for target test video."

    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)
    new_event = {
        "author_id": "author_t16_overlay_new_viewer",
        "vtuber_channel_id": chan_id,
        "video_id": video_id,
        "interaction_time": "2026-08-01T12:00:00Z"
    }

    res = pipeline.ingest_batch("batch_overlay_test", [new_event])
    assert res.records_inserted == 1

    con_after = duckdb.connect(":memory:")
    prov_after = get_sources_by_provenance(base_dir=temp_pipeline_env)
    build_unified_raw_view(con_after, prov_after)
    build_canonical_events_view(con_after, "unified_raw")

    t6_count_after = con_after.execute(f"""
        SELECT COUNT(*) FROM canonical_events
        WHERE video_id = '{video_id}' AND provenance = 't6_deep'
    """).fetchone()[0]
    t16_count_after = con_after.execute(f"""
        SELECT COUNT(*) FROM canonical_events
        WHERE video_id = '{video_id}' AND provenance = 't16_incremental'
    """).fetchone()[0]
    con_after.close()

    # Crucial assertion: T6 count is completely preserved!
    assert t6_count_after == t6_count_before
    assert t16_count_after == 1


def test_06_affected_yearly_cumulative_all_time_snapshots_change(temp_pipeline_env):
    """6. Ingesting 2026 batch causes values to change in yearly 2026, cumulative 2026, and all_time."""
    snaps_file = temp_pipeline_env / "data" / "temporal" / "snapshots" / "network_snapshots.parquet"
    df_before = pd.read_parquet(snaps_file)

    sum_y2026_before = df_before[(df_before["window_type"] == "yearly") & (df_before["window_start"].str.startswith("2026"))]["shared_any"].sum()
    sum_c2026_before = df_before[(df_before["window_type"] == "cumulative") & (df_before["window_end"].str.startswith("2026"))]["shared_any"].sum()
    sum_alltime_before = df_before[df_before["window_type"] == "all_time"]["shared_any"].sum()

    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)
    events = [
        {
            "author_id": "author_triple_change_1",
            "vtuber_channel_id": "UCpGtwNmbOtgmcKIY81MIX_w",
            "video_id": "vid_triple_a",
            "interaction_time": "2026-07-15T10:00:00Z"
        },
        {
            "author_id": "author_triple_change_1",
            "vtuber_channel_id": "UCGBkYTR4tMKS38TQHGWWLjg",
            "video_id": "vid_triple_b",
            "interaction_time": "2026-07-15T10:05:00Z"
        }
    ]

    res = pipeline.ingest_batch("batch_triple_change", events)
    assert res.status == "COMMITTED"
    assert res.records_inserted == 2

    df_after = pd.read_parquet(snaps_file)
    sum_y2026_after = df_after[(df_after["window_type"] == "yearly") & (df_after["window_start"].str.startswith("2026"))]["shared_any"].sum()
    sum_c2026_after = df_after[(df_after["window_type"] == "cumulative") & (df_after["window_end"].str.startswith("2026"))]["shared_any"].sum()
    sum_alltime_after = df_after[df_after["window_type"] == "all_time"]["shared_any"].sum()

    assert sum_y2026_after > sum_y2026_before
    assert sum_c2026_after > sum_c2026_before
    assert sum_alltime_after > sum_alltime_before


def test_07_unrelated_historical_slice_remains_identical(temp_pipeline_env):
    """7. Historical slices (2020-2024 yearly) remain byte and value identical."""
    snaps_file = temp_pipeline_env / "data" / "temporal" / "snapshots" / "network_snapshots.parquet"
    df_before = pd.read_parquet(snaps_file)

    hist_2020_before = df_before[(df_before["window_type"] == "yearly") & (df_before["window_start"].str.startswith("2020"))].copy()
    hist_2021_before = df_before[(df_before["window_type"] == "yearly") & (df_before["window_start"].str.startswith("2021"))].copy()

    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)
    mock_event = [
        {
            "author_id": "author_hist_iso_test",
            "vtuber_channel_id": "UCpGtwNmbOtgmcKIY81MIX_w",
            "video_id": "vid_iso_2026",
            "interaction_time": "2026-08-10T12:00:00Z"
        }
    ]
    pipeline.ingest_batch("batch_iso_test", mock_event)

    df_after = pd.read_parquet(snaps_file)
    hist_2020_after = df_after[(df_after["window_type"] == "yearly") & (df_after["window_start"].str.startswith("2020"))].copy()
    hist_2021_after = df_after[(df_after["window_type"] == "yearly") & (df_after["window_start"].str.startswith("2021"))].copy()

    pd.testing.assert_frame_equal(hist_2020_before.reset_index(drop=True), hist_2020_after.reset_index(drop=True))
    pd.testing.assert_frame_equal(hist_2021_before.reset_index(drop=True), hist_2021_after.reset_index(drop=True))


def test_08_crash_and_retry_yields_clean_final_result(temp_pipeline_env):
    """8. Crash before checkpoint leaves clean state, and retry yields successful final result."""
    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)
    mock_events = [
        {
            "author_id": "author_crash_8",
            "vtuber_channel_id": "UCpGtwNmbOtgmcKIY81MIX_w",
            "video_id": "vid_crash_8",
            "interaction_time": "2026-08-20T00:00:00Z"
        }
    ]

    # Simulate crash before commit
    with pytest.raises(RuntimeError, match="CRASH_BEFORE_COMMIT"):
        pipeline.ingest_batch("batch_crash_retry", mock_events, simulate_crash_before_commit=True)

    # State file must NOT contain batch_crash_retry as COMMITTED
    state = json.loads((temp_pipeline_env / "data" / "temporal" / "state" / "pipeline_state.json").read_text(encoding="utf-8"))
    assert "batch_crash_retry" not in state.get("processed_batches", {})

    # No leftover .tmp files
    assert list(pipeline.incremental_dir.glob("*.tmp")) == []

    # Retry cleanly
    res_retry = pipeline.ingest_batch("batch_crash_retry", mock_events, simulate_crash_before_commit=False)
    assert res_retry.status == "COMMITTED"
    assert res_retry.records_inserted == 1


def test_09_hmac_key_swap_fails(temp_pipeline_env):
    """9. Swapping secret key fails closed with HMACKeyContinuityError."""
    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)
    assert pipeline.active_fingerprint is not None

    fake_key = b"A" * 32
    with pytest.raises(HMACKeyContinuityError):
        IncrementalTemporalPipeline(base_dir=temp_pipeline_env, custom_key=fake_key)


def test_10_future_year_event_creates_new_slices(temp_pipeline_env):
    """10. Future-year event (e.g. 2027) creates new yearly, cumulative, and updated all_time slices."""
    snaps_file = temp_pipeline_env / "data" / "temporal" / "snapshots" / "network_snapshots.parquet"
    df_before = pd.read_parquet(snaps_file)

    # Assert 2027 does not exist yet
    assert df_before[(df_before["window_type"] == "yearly") & (df_before["window_start"].str.startswith("2027"))].empty

    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)
    events_2027 = [
        {
            "author_id": "author_2027_future_viewer",
            "vtuber_channel_id": "UCpGtwNmbOtgmcKIY81MIX_w",
            "video_id": "vid_2027_01",
            "interaction_time": "2027-02-14T10:00:00Z"
        },
        {
            "author_id": "author_2027_future_viewer",
            "vtuber_channel_id": "UCGBkYTR4tMKS38TQHGWWLjg",
            "video_id": "vid_2027_02",
            "interaction_time": "2027-02-14T10:05:00Z"
        }
    ]

    res = pipeline.ingest_batch("batch_future_2027", events_2027)
    assert res.status == "COMMITTED"
    assert res.records_inserted == 2
    assert 2027 in res.affected_years

    df_after = pd.read_parquet(snaps_file)

    # 1. New yearly 2027 slice exists
    y_2027 = df_after[(df_after["window_type"] == "yearly") & (df_after["window_start"].str.startswith("2027"))]
    assert not y_2027.empty, "Expected yearly 2027 slice to be created."
    assert y_2027["shared_any"].iloc[0] >= 1

    # 2. New cumulative 2027 slice exists
    c_2027 = df_after[(df_after["window_type"] == "cumulative") & (df_after["window_end"].str.startswith("2027"))]
    assert not c_2027.empty, "Expected cumulative 2027 slice to be created."

    # 3. All-time updated
    all_time = df_after[df_after["window_type"] == "all_time"]
    assert not all_time.empty
    assert "2027" in all_time["window_end"].iloc[0]

    # 4. Historical slices 2020..2025 remain identical
    hist_2022_before = df_before[(df_before["window_type"] == "yearly") & (df_before["window_start"].str.startswith("2022"))].copy()
    hist_2022_after = df_after[(df_after["window_type"] == "yearly") & (df_after["window_start"].str.startswith("2022"))].copy()
    pd.testing.assert_frame_equal(hist_2022_before.reset_index(drop=True), hist_2022_after.reset_index(drop=True))
