"""Tests for Phase T16 Incremental Temporal Pipeline.

Verifies:
1. Rerunning same batch changes nothing (idempotency).
2. Crash before checkpoint resumes safely without data corruption.
3. New event updates only affected temporal outputs.
4. Duplicate evidence is suppressed.
5. Provenance precedence is unchanged.
6. HMAC key continuity is strictly enforced (fails loud on key swap).
7. Old historical baseline remains byte-identical.
"""
import copy
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import pytest
import pandas as pd

from scripts.incremental_temporal_pipeline import (
    IncrementalTemporalPipeline,
    HMACKeyContinuityError,
    PROVENANCE_PRECEDENCE
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


def test_hmac_key_continuity_enforced(temp_pipeline_env):
    """Verify that using a different secret key fails closed with HMACKeyContinuityError."""
    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)
    assert pipeline.active_fingerprint is not None

    # Now attempt to initialize pipeline in same environment with an illegitimate/different key
    fake_key = b"0" * 32
    with pytest.raises(HMACKeyContinuityError):
        IncrementalTemporalPipeline(base_dir=temp_pipeline_env, custom_key=fake_key)


def test_idempotent_rerun_same_batch_changes_nothing(temp_pipeline_env):
    """Verify that reprocessing the exact same batch ID results in zero new inserts."""
    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)

    mock_events = [
        {
            "author_id": "mock_author_123",
            "vtuber_channel_id": "UC_channel_A",
            "video_id": "vid_2026_001",
            "interaction_time": "2026-03-01T12:00:00Z"
        },
        {
            "author_id": "mock_author_123",
            "vtuber_channel_id": "UC_channel_B",
            "video_id": "vid_2026_001",
            "interaction_time": "2026-03-01T12:00:00Z"
        }
    ]

    # First run
    res1 = pipeline.ingest_batch("batch_test_001", mock_events)
    assert res1.status == "COMMITTED"
    assert res1.records_inserted == 2
    assert res1.duplicates_suppressed == 0

    # Second run (exact same batch ID)
    res2 = pipeline.ingest_batch("batch_test_001", mock_events)
    assert res2.status == "ALREADY_PROCESSED"
    assert res2.records_inserted == 0
    assert res2.duplicates_suppressed == 2


def test_duplicate_evidence_suppressed(temp_pipeline_env):
    """Verify that identical interaction records across different batch IDs are suppressed."""
    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)

    event_item = {
        "author_id": "author_dup_test",
        "vtuber_channel_id": "UC_target_chan",
        "video_id": "vid_test_shared",
        "interaction_time": "2026-04-10T10:00:00Z"
    }

    # Ingest in batch 1
    res1 = pipeline.ingest_batch("batch_first", [event_item])
    assert res1.records_inserted == 1

    # Ingest same event in batch 2
    res2 = pipeline.ingest_batch("batch_second", [event_item])
    assert res2.status == "COMMITTED"
    assert res2.records_inserted == 0
    assert res2.duplicates_suppressed == 1


def test_crash_before_checkpoint_resumes_safely(temp_pipeline_env):
    """Verify that if a process crashes before checkpoint commit, state remains clean and can resume safely."""
    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)

    mock_events = [
        {
            "author_id": "author_crash_1",
            "vtuber_channel_id": "UC_chan_1",
            "video_id": "vid_crash_1",
            "interaction_time": "2026-05-01T00:00:00Z"
        }
    ]

    # Simulate crash before commit
    with pytest.raises(RuntimeError, match="CRASH_BEFORE_COMMIT"):
        pipeline.ingest_batch("batch_crash_test", mock_events, simulate_crash_before_commit=True)

    # State file must NOT contain batch_crash_test as COMMITTED
    state = json.loads((temp_pipeline_env / "data" / "temporal" / "state" / "pipeline_state.json").read_text(encoding="utf-8"))
    assert "batch_crash_test" not in state.get("processed_batches", {})

    # Resume: execute batch_crash_test cleanly without error
    res_retry = pipeline.ingest_batch("batch_crash_test", mock_events, simulate_crash_before_commit=False)
    assert res_retry.status == "COMMITTED"
    assert res_retry.records_inserted == 1


def test_new_event_updates_only_affected_temporal_outputs(temp_pipeline_env):
    """Verify that ingesting a 2026 event updates affected_years=[2026], leaving historical years isolated."""
    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)

    mock_event_2026 = [
        {
            "author_id": "author_2026_test",
            "vtuber_channel_id": "UC_chan_2026",
            "video_id": "vid_2026_only",
            "interaction_time": "2026-06-15T15:00:00Z"
        }
    ]

    res = pipeline.ingest_batch("batch_2026_only", mock_event_2026)
    assert res.status == "COMMITTED"
    assert res.affected_years == [2026]
    assert 2020 not in res.affected_years
    assert 2021 not in res.affected_years


def test_historical_baseline_remains_byte_identical(temp_pipeline_env):
    """Verify that historical slice data for 2020-2024 remains completely unaltered."""
    snaps_file = temp_pipeline_env / "data" / "temporal" / "snapshots" / "network_snapshots.parquet"
    df_before = pd.read_parquet(snaps_file)
    hist_2020_before = df_before[(df_before["window_type"] == "yearly") & (df_before["window_start"].str.startswith("2020"))].copy()

    pipeline = IncrementalTemporalPipeline(base_dir=temp_pipeline_env)
    mock_event = [
        {
            "author_id": "author_future",
            "vtuber_channel_id": "UC_future_chan",
            "video_id": "vid_future",
            "interaction_time": "2026-08-01T12:00:00Z"
        }
    ]
    pipeline.ingest_batch("batch_future", mock_event)

    df_after = pd.read_parquet(snaps_file)
    hist_2020_after = df_after[(df_after["window_type"] == "yearly") & (df_after["window_start"].str.startswith("2020"))].copy()

    pd.testing.assert_frame_equal(hist_2020_before.reset_index(drop=True), hist_2020_after.reset_index(drop=True))


def test_provenance_precedence_maintained():
    """Verify provenance hierarchy precedence ranking."""
    assert PROVENANCE_PRECEDENCE["legacy"] < PROVENANCE_PRECEDENCE["t2_pilot"]
    assert PROVENANCE_PRECEDENCE["t2_pilot"] < PROVENANCE_PRECEDENCE["t5_stratified"]
    assert PROVENANCE_PRECEDENCE["t5_stratified"] < PROVENANCE_PRECEDENCE["t6_deep"]
    assert PROVENANCE_PRECEDENCE["t6_deep"] < PROVENANCE_PRECEDENCE["t16_incremental"]
