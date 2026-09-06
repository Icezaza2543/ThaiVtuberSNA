"""
Regression Tests for Continuous Lightweight Collection Foundations:
- Idempotent persistence & reconciliation (no appearance inflation on repeated polls)
- Durable collection state & atomic claims (JobJournal)
- Crash recovery of abandoned in-flight jobs
- Privacy checkpoint enforcement
- Mixed live-chat vs comment evidence separation for the same video
- One-video repetition versus two distinct videos (evidence contract)
- Bounded continuous collection cycle
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from storage.parquet_manager import ParquetStorageManager
from storage.duckdb_engine import DuckDBAnalyticsEngine
from core.job_journal import JobJournal
from core.hasher import PrivacyHasher
from collector.continuous_collector import ContinuousCollector
from collector.live_chat_adapter import LiveChatAdapter


@pytest.fixture
def temp_dir():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_idempotent_persistence_no_appearance_inflation(temp_dir):
    """
    Verifies that repeatedly collecting/writing the exact same video/source
    does NOT duplicate rows or inflate appearances in Parquet & DuckDB.
    """
    events_dir = temp_dir / "events"
    mgr = ParquetStorageManager(base_dir=events_dir)

    events_snapshot = [
        {
            "viewer_hash": "hash_viewer_1",
            "vtuber_channel_id": "CH_A",
            "video_id": "VID_01",
            "first_seen": "2026-09-01T10:00:00Z",
            "last_seen": "2026-09-01T10:00:00Z",
            "appearances": 2,
            "source_type": "comment"
        },
        {
            "viewer_hash": "hash_viewer_2",
            "vtuber_channel_id": "CH_A",
            "video_id": "VID_01",
            "first_seen": "2026-09-01T10:05:00Z",
            "last_seen": "2026-09-01T10:05:00Z",
            "appearances": 1,
            "source_type": "comment"
        }
    ]

    # Poll 1
    p1 = mgr.write_events(events_snapshot)
    assert p1.exists()

    engine = DuckDBAnalyticsEngine(db_path=temp_dir / "test.duckdb", events_dir=events_dir)
    summary_1 = engine.get_viewer_presence_summary()
    assert len(summary_1) == 2
    v1_sum = next(s for s in summary_1 if s["viewer_hash"] == "hash_viewer_1")
    assert v1_sum["appearances"] == 2
    assert v1_sum["videos_seen"] == 1

    # Poll 2: Repeated collection with identical data
    p2 = mgr.write_events(events_snapshot)
    assert p1 == p2  # Deterministic source partition

    engine.refresh_views()
    summary_2 = engine.get_viewer_presence_summary()
    assert len(summary_2) == 2
    v1_sum_2 = next(s for s in summary_2 if s["viewer_hash"] == "hash_viewer_1")
    # CRITICAL: Appearances MUST NOT double to 4!
    assert v1_sum_2["appearances"] == 2
    assert v1_sum_2["videos_seen"] == 1
    engine.close()


def test_job_journal_atomic_claims_and_lifecycle(temp_dir):
    """
    Verifies that two concurrent workers cannot claim the same job.
    """
    journal = JobJournal(db_path=temp_dir / "jobs.sqlite3")
    
    # Register 2 jobs
    j1 = journal.register_job("CH_1", "V_1", "comment", priority=2.0)
    j2 = journal.register_job("CH_2", "V_2", "comment", priority=1.0)

    # Worker 1 claims highest priority job
    claimed_1 = journal.claim_next_job(worker_id="worker_alpha")
    assert claimed_1 is not None
    assert claimed_1["job_id"] == j1

    # Worker 2 claims next job (MUST NOT be j1)
    claimed_2 = journal.claim_next_job(worker_id="worker_beta")
    assert claimed_2 is not None
    assert claimed_2["job_id"] == j2

    # Worker 3 has nothing pending
    claimed_3 = journal.claim_next_job(worker_id="worker_gamma")
    assert claimed_3 is None

    # Worker 1 completes job
    assert journal.commit_job(j1, records_committed=50, claim_token=claimed_1['claim_token']) is True
    job_status = journal.get_job(j1)
    assert job_status["state"] == "COMPLETED"
    assert job_status["records_committed"] == 50


def test_job_journal_crash_recovery(temp_dir):
    """
    Verifies that if a worker crashes while holding a CLAIMED job,
    recover_abandoned_jobs resets it to PENDING without data loss.
    """
    journal = JobJournal(db_path=temp_dir / "jobs.sqlite3")
    j1 = journal.register_job("CH_1", "V_1", "comment")

    claimed = journal.claim_next_job(worker_id="crashed_worker")
    assert claimed is not None
    assert journal.get_job(j1)["state"] == "CLAIMED"

    # Simulate timeout recovery (timeout=0 for test)
    recovered = journal.recover_abandoned_jobs(timeout_seconds=0)
    assert recovered == 1
    assert journal.get_job(j1)["state"] == "PENDING"

    # Now a healthy worker can reclaim it
    reclaimed = journal.claim_next_job(worker_id="healthy_worker")
    assert reclaimed is not None
    assert reclaimed["job_id"] == j1


def test_job_journal_privacy_guard(temp_dir):
    """
    Verifies that checkpoints reject raw channel IDs or message text.
    """
    journal = JobJournal(db_path=temp_dir / "jobs.sqlite3")
    j1 = journal.register_job("CH_1", "V_1", "comment")
    claim = journal.claim_next_job(worker_id="w1")

    # Forbidden: raw YouTube channel ID in checkpoint
    with pytest.raises(ValueError, match="Privacy violation"):
        journal.commit_job(j1, records_committed=10, checkpoint='{"last_author": "UC12345"}', claim_token=claim['claim_token'])

    # Forbidden: message text in checkpoint
    with pytest.raises(ValueError, match="Privacy violation"):
        journal.commit_job(j1, records_committed=10, checkpoint='{"text": "hello stream"}', claim_token=claim['claim_token'])

    # Allowed: safe token
    assert journal.commit_job(j1, records_committed=10, checkpoint='{"page": 2, "token": "abc"}', claim_token=claim['claim_token']) is True


def test_mixed_evidence_same_viewer_same_video(temp_dir):
    """
    Verifies that a viewer who commented AND chatted in the same video
    has both evidence sources stored separately without collision.
    """
    events_dir = temp_dir / "events"
    mgr = ParquetStorageManager(base_dir=events_dir)

    comment_event = [{
        "viewer_hash": "viewer_mixed_1",
        "vtuber_channel_id": "CH_A",
        "video_id": "VID_STREAM_1",
        "first_seen": "2026-09-01T10:00:00Z",
        "last_seen": "2026-09-01T10:00:00Z",
        "appearances": 1,
        "source_type": "comment"
    }]

    live_event = [{
        "viewer_hash": "viewer_mixed_1",
        "vtuber_channel_id": "CH_A",
        "video_id": "VID_STREAM_1",
        "first_seen": "2026-09-01T08:00:00Z",
        "last_seen": "2026-09-01T09:00:00Z",
        "appearances": 5,
        "source_type": "live_chat"
    }]

    p_comment = mgr.write_events(comment_event)
    p_live = mgr.write_events(live_event)

    assert p_comment != p_live
    assert p_comment.exists() and p_live.exists()

    engine = DuckDBAnalyticsEngine(db_path=temp_dir / "test.duckdb", events_dir=events_dir)
    summary = engine.get_viewer_presence_summary()[0]
    # videos_seen counts distinct video_id = 1
    # live_streams_seen counts live_chat video_id = 1
    assert summary["videos_seen"] == 1
    assert summary["live_streams_seen"] == 1
    assert summary["comment_videos_seen"] == 1
    assert summary["appearances"] == 6  # 1 comment + 5 chats
    engine.close()


def test_one_video_repetition_vs_two_distinct_videos_evidence(temp_dir):
    """
    Verifies the Strong Evidence contract:
    - Polling the same video multiple times NEVER creates strong evidence.
    - Strong evidence strictly requires >=2 distinct video IDs on BOTH channels.
    """
    events_dir = temp_dir / "events"
    mgr = ParquetStorageManager(base_dir=events_dir)

    # Viewer watches 1 video on Channel A and 1 video on Channel B
    # Repeated 5 times
    for _ in range(5):
        mgr.write_events([{
            "viewer_hash": "shared_viewer_test",
            "vtuber_channel_id": "CH_A",
            "video_id": "VID_A1",
            "first_seen": "2026-09-01T10:00:00Z",
            "last_seen": "2026-09-01T10:00:00Z",
            "appearances": 1,
            "source_type": "comment"
        }])
        mgr.write_events([{
            "viewer_hash": "shared_viewer_test",
            "vtuber_channel_id": "CH_B",
            "video_id": "VID_B1",
            "first_seen": "2026-09-01T10:00:00Z",
            "last_seen": "2026-09-01T10:00:00Z",
            "appearances": 1,
            "source_type": "comment"
        }])

    engine = DuckDBAnalyticsEngine(db_path=temp_dir / "test.duckdb", events_dir=events_dir)
    overlap_1 = engine.compute_pairwise_overlap(min_shared_viewers=1, min_evidence_threshold=2)
    assert len(overlap_1) == 1
    pair_1 = overlap_1[0]
    assert pair_1["shared_any"] == 1
    # MUST BE ZERO because only 1 distinct video on each channel
    assert pair_1["strong_shared_any"] == 0
    assert pair_1["strong_shared_comments"] == 0

    # Now add a SECOND distinct video on both channels
    mgr.write_events([{
        "viewer_hash": "shared_viewer_test",
        "vtuber_channel_id": "CH_A",
        "video_id": "VID_A2",
        "first_seen": "2026-09-02T10:00:00Z",
        "last_seen": "2026-09-02T10:00:00Z",
        "appearances": 1,
        "source_type": "comment"
    }])
    mgr.write_events([{
        "viewer_hash": "shared_viewer_test",
        "vtuber_channel_id": "CH_B",
        "video_id": "VID_B2",
        "first_seen": "2026-09-02T10:00:00Z",
        "last_seen": "2026-09-02T10:00:00Z",
        "appearances": 1,
        "source_type": "comment"
    }])

    engine.refresh_views()
    overlap_2 = engine.compute_pairwise_overlap(min_shared_viewers=1, min_evidence_threshold=2)
    pair_2 = overlap_2[0]
    assert pair_2["shared_any"] == 1
    # NOW satisfied >= 2 distinct videos on BOTH channels
    assert pair_2["strong_shared_any"] == 1
    assert pair_2["strong_shared_comments"] == 1
    engine.close()


def test_live_chat_adapter_memory_only_privacy(temp_dir):
    """
    Verifies that LiveChatAdapter:
    1. Operates 100% in memory with ZERO disk writes
    2. Hashes author channel IDs immediately
    3. Fails closed with explicit status when no key is configured
    """
    hasher = PrivacyHasher("test_salt_secret")
    adapter_no_key = LiveChatAdapter(hasher=hasher, api_key="")
    
    # Without key: fails closed safely without crashing
    res = adapter_no_key.collect_live_chat_events({"vtuber_channel_id": "CH_A", "video_id": "VID_1"})
    assert res["status"] == "LIVE_CHAT_UNAVAILABLE"
    assert res["reason"] == "NO_API_KEY_CONFIGURED"

    # Mocking API response in memory
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [{
            "id": "msg_001",
            "authorDetails": {"channelId": "UC_REAL_AUTHOR_12345", "displayName": "Secret User"},
            "snippet": {"displayMessage": "Hello VTuber!", "publishedAt": "2026-09-01T12:00:00Z"}
        }]
    }

    adapter_with_key = LiveChatAdapter(hasher=hasher, api_key="test_api_key")
    with patch("requests.get", return_value=mock_resp):
        res_live = adapter_with_key.collect_live_chat_events(
            {"vtuber_channel_id": "CH_A", "video_id": "VID_1", "active_live_chat_id": "chat_123"}
        )
        assert res_live["status"] == "SUCCESS"
        events = res_live["events"]
        assert len(events) == 1
        e = events[0]
        # Verified: Author ID was immediately hashed
        assert e["viewer_hash"] == hasher.hash_viewer_id("UC_REAL_AUTHOR_12345")
        assert "UC_REAL_AUTHOR_12345" not in str(e)
        assert "Secret User" not in str(e)
        assert "Hello VTuber!" not in str(e)
        assert e["source_type"] == "live_chat"


class SyntheticComments:
    def collect_aggregated_events(self, job, max_comments=150):
        return [{**{k: job[k] for k in ('vtuber_channel_id', 'video_id', 'source_type')},
                 'viewer_hash': PrivacyHasher('test_salt_continuous').hash_viewer_id('synthetic'),
                 'first_seen': '2026-09-01T12:00:00Z',
                 'last_seen': '2026-09-01T12:00:00Z', 'appearances': 1}]


def test_continuous_collector_bounded_cycle_execution(temp_dir):
    """
    Verifies that ContinuousCollector respects bounded cycle limits,
    processes claimed jobs, and updates journal states honestly.
    """
    storage_dir = temp_dir / "events"
    journal_path = temp_dir / "journal.sqlite3"
    hasher = PrivacyHasher("test_salt_continuous")

    collector = ContinuousCollector(
        storage_dir=storage_dir,
        journal_path=journal_path,
        max_workers=2,
        hasher=hasher,
        comment_collector=SyntheticComments()
    )

    candidates = [
        {"channel_id": "CH_TEST_1", "video_id": "VID_01", "name": "VTuber 1"},
        {"channel_id": "CH_TEST_2", "video_id": "VID_02", "name": "VTuber 2"}
    ]

    registered = collector.plan_and_register_jobs(candidates, sources=["comment"])
    assert len(registered) == 2

    # Run bounded cycle with max_jobs=1
    summary = collector.run_bounded_cycle(max_jobs_to_process=1)
    assert summary["jobs_processed"] == 1
    assert summary["total_records_persisted"] == 1
    assert summary["status_breakdown"].get("SUCCESS") == 1

    # Check journal state
    journal_sum = collector.journal.get_summary()
    assert journal_sum["states"].get("COMPLETED") == 1
    assert journal_sum["states"].get("PENDING") == 1


def test_continuous_collector_missing_key_fails_closed(tmp_path, monkeypatch):
    """
    Verifies that ContinuousCollector fails closed if the key is missing.
    """
    monkeypatch.setattr("core.hasher.SECRET_KEY_PATH", tmp_path / "nonexistent.key")
    monkeypatch.setattr("core.hasher.SECRET_FINGERPRINT_PATH", tmp_path / "nonexistent.fp")
    monkeypatch.setattr("core.hasher.SALT_SECRET", "")

    with pytest.raises(RuntimeError, match="missing"):
        ContinuousCollector()


def test_legacy_migration_to_deterministic_partitions(temp_dir):
    """
    Verifies explicit migration from legacy UUID files to deterministic source partitions.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq
    from storage.parquet_manager import AGGREGATED_SCHEMA

    events_dir = temp_dir / "events" / "2026" / "08"
    events_dir.mkdir(parents=True, exist_ok=True)

    # Create a legacy UUID file
    legacy_file = events_dir / "VID99-abcd1234uuid.parquet"
    records = [{
        "viewer_hash": "vh_legacy_1",
        "vtuber_channel_id": "CH_LEGACY",
        "video_id": "VID99",
        "first_seen": "2026-08-01T12:00:00Z",
        "last_seen": "2026-08-01T12:00:00Z",
        "appearances": 2,
        "source_type": "comment"
    }]
    arrays = {k: [r[k] for r in records] for k in records[0]}
    tab = pa.Table.from_pydict(arrays, schema=AGGREGATED_SCHEMA)
    pq.write_table(tab, legacy_file)

    mgr = ParquetStorageManager(base_dir=temp_dir / "events")
    assert legacy_file.exists()

    # Run migration
    migrated_count = mgr.migrate_legacy_partitions()
    assert migrated_count == 1
    # Legacy file was removed
    assert not legacy_file.exists()

    # Deterministic partition was created
    det_file = temp_dir / 'events' / 'canonical' / 'CH_LEGACY' / "VID99_comment.parquet"
    assert det_file.exists()
    migrated_tab = pq.read_table(det_file)
    assert len(migrated_tab) == 1
    assert migrated_tab["viewer_hash"][0].as_py() == "vh_legacy_1"


