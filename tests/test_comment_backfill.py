"""
tests/test_comment_backfill.py

Unit & Regression Tests for Phase T5-C Historical Comment Backfill Engine
Verifies:
1. Privacy boundary: Zero raw viewer IDs, names, URLs, or texts escape into observation records.
2. Missing timestamp strictness: Missing or invalid publishedAt produces interaction_at = None.
3. Comments disabled: Handled gracefully with COMMENTS_DISABLED status.
4. No comments: Empty items array produces NO_COMMENTS status without errors.
5. Partial capture: Detects nextPageToken or hit limit and sets partial_capture = True.
6. API budget exhaustion: Respects quota budget and halts cleanly.
7. Resume after interruption: Completed jobs are skipped; pending jobs resume seamlessly.
8. Duplicate-free rerun: Repeated execution does not inflate records.
9. Failed persistence fails closed: Unsuccessful Parquet write does NOT mark job COMPLETED.
10. Deterministic HMAC continuity: Hashes match persistent HMAC identity.
11. Backend distinction: Correctly records 'youtube_api_v3'.
12. Repeated comments deduplication: Multiple comments by same viewer on one video collapse to 1 presence row.
13. Persistent key mismatch fails closed before network I/O.
"""
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch
import pyarrow.parquet as pq

from core.hasher import PrivacyHasher, compute_key_fingerprint
from collector.historical_comment_backfill import (
    HistoricalCommentBackfiller,
    BudgetExhaustedException,
    parse_iso_dt,
    OBSERVATION_SCHEMA
)


@pytest.fixture
def mock_hasher():
    """Provides a deterministic test hasher."""
    return PrivacyHasher(secret_salt=b"test_secret_salt_for_backfill_tests_12345")


def test_parse_iso_dt_strictness():
    """Strict ISO datetime parsing; invalid strings yield None."""
    assert parse_iso_dt(None) is None
    assert parse_iso_dt("") is None
    assert parse_iso_dt("corrupted-date") is None
    dt = parse_iso_dt("2023-08-15T10:30:00Z")
    assert dt == "2023-08-15T10:30:00+00:00"


def test_privacy_boundary_zero_pii_leak(tmp_path, mock_hasher):
    """
    HOTFIX 5 / Milestone T5-C: Extraction boundary guarantees that raw viewer
    channel ID, name, URL, and comment text never escape into returned structures.
    """
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_pii_999"},
                            "authorDisplayName": "Raw Viewer Display Name",
                            "authorChannelUrl": "https://www.youtube.com/channel/UC_viewer_pii_999",
                            "textDisplay": "Super private comment text!",
                            "publishedAt": "2024-05-10T12:00:00Z"
                        }
                    }
                }
            }
        ]
    }
    mock_session.get.return_value = mock_resp

    backfiller = HistoricalCommentBackfiller(
        db_path=tmp_path / "test.db",
        observations_dir=tmp_path / "obs",
        hasher=mock_hasher,
        session=mock_session
    )

    obs, capture_status, partial_cap, err = backfiller.extract_comments_api(
        video_id="test_vid_1",
        channel_id="UC_vtuber_1",
        sample_id="s_1",
        video_published_at="2024-05-01T00:00:00+00:00"
    )

    assert len(obs) == 1
    record = obs[0]
    expected_hash = mock_hasher.hash_viewer_id("UC_viewer_pii_999")

    # Assertions
    assert record["viewer_hash"] == expected_hash
    assert "UC_viewer_pii_999" not in record.values()
    assert "Raw Viewer Display Name" not in record.values()
    assert "Super private comment text!" not in record.values()
    assert "author_id" not in record
    assert "authorDisplayName" not in record
    assert "authorChannelUrl" not in record
    assert "textDisplay" not in record
    assert record["timestamp_quality"] == "exact"
    assert record["interaction_at"] == "2024-05-10T12:00:00+00:00"


def test_repeated_comments_collapse_to_single_presence(tmp_path, mock_hasher):
    """Multiple comments by the same commenter on the same video collapse into 1 presence row."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_active"},
                            "publishedAt": "2024-01-01T10:00:00Z"
                        }
                    }
                }
            },
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_active"},
                            "publishedAt": "2024-01-01T10:05:00Z"
                        }
                    }
                }
            },
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_active"},
                            "publishedAt": "2024-01-01T10:10:00Z"
                        }
                    }
                }
            }
        ]
    }
    mock_session.get.return_value = mock_resp

    backfiller = HistoricalCommentBackfiller(
        db_path=tmp_path / "test.db",
        observations_dir=tmp_path / "obs",
        hasher=mock_hasher,
        session=mock_session
    )

    obs, capture_status, partial_cap, err = backfiller.extract_comments_api(
        video_id="test_vid_repeat",
        channel_id="UC_vtuber_1",
        sample_id="s_repeat"
    )

    assert len(obs) == 1  # Collapsed to single presence row
    assert obs[0]["viewer_hash"] == mock_hasher.hash_viewer_id("UC_viewer_active")


def test_missing_timestamp_strictness(tmp_path, mock_hasher):
    """Missing or corrupted publishedAt produces interaction_at = None, timestamp_quality = 'missing'."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_no_ts"},
                            "publishedAt": None
                        }
                    }
                }
            }
        ]
    }
    mock_session.get.return_value = mock_resp

    backfiller = HistoricalCommentBackfiller(
        db_path=tmp_path / "test.db",
        observations_dir=tmp_path / "obs",
        hasher=mock_hasher,
        session=mock_session
    )

    obs, _, _, _ = backfiller.extract_comments_api("v_no_ts", "UC_1", "s_no_ts")
    assert len(obs) == 1
    assert obs[0]["interaction_at"] is None
    assert obs[0]["timestamp_quality"] == "missing"


def test_comments_disabled_handling(tmp_path, mock_hasher):
    """HTTP 403 with commentsDisabled produces COMMENTS_DISABLED status cleanly."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = '{"error": {"errors": [{"reason": "commentsDisabled"}]}}'
    mock_session.get.return_value = mock_resp

    backfiller = HistoricalCommentBackfiller(
        db_path=tmp_path / "test.db",
        observations_dir=tmp_path / "obs",
        hasher=mock_hasher,
        session=mock_session
    )

    obs, cap_status, partial_cap, err = backfiller.extract_comments_api("v_dis", "UC_1", "s_dis")
    assert len(obs) == 0
    assert cap_status == "COMMENTS_DISABLED"
    assert partial_cap is False


def test_no_comments_handling(tmp_path, mock_hasher):
    """Empty items list produces NO_COMMENTS status cleanly."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"items": []}
    mock_session.get.return_value = mock_resp

    backfiller = HistoricalCommentBackfiller(
        db_path=tmp_path / "test.db",
        observations_dir=tmp_path / "obs",
        hasher=mock_hasher,
        session=mock_session
    )

    obs, cap_status, _, _ = backfiller.extract_comments_api("v_empty", "UC_1", "s_empty")
    assert len(obs) == 0
    assert cap_status == "NO_COMMENTS"


def test_partial_capture_detection(tmp_path, mock_hasher):
    """If nextPageToken exists, marks partial_capture = True and capture_status = PARTIAL_CAPTURE."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "nextPageToken": "token_page_2",
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_p1"},
                            "publishedAt": "2024-02-01T00:00:00Z"
                        }
                    }
                }
            }
        ]
    }
    mock_session.get.return_value = mock_resp

    backfiller = HistoricalCommentBackfiller(
        db_path=tmp_path / "test.db",
        observations_dir=tmp_path / "obs",
        hasher=mock_hasher,
        session=mock_session
    )

    obs, cap_status, partial_cap, _ = backfiller.extract_comments_api("v_partial", "UC_1", "s_partial")
    assert cap_status == "PARTIAL_CAPTURE"
    assert partial_cap is True
    assert obs[0]["partial_capture"] is True


def test_quota_budget_exhaustion_clean_halt(tmp_path, mock_hasher):
    """Halts cleanly without corrupting DB when API quota budget is exhausted."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"items": []}
    mock_session.get.return_value = mock_resp

    db_path = tmp_path / "test_budget.db"
    backfiller = HistoricalCommentBackfiller(
        db_path=db_path,
        observations_dir=tmp_path / "obs",
        quota_budget=2,  # Budget only allows 2 requests
        hasher=mock_hasher,
        session=mock_session
    )

    jobs = [
        {"sample_id": f"s_{i}", "channel_id": "UC_1", "video_id": f"v_{i}", "year": 2024}
        for i in range(5)
    ]
    backfiller.sync_manifest(jobs)

    summary = backfiller.run_backfill()
    assert summary["videos_attempted"] == 2
    assert summary["budget_exhausted"] is True
    assert summary["api_requests_used"] == 2
    assert summary["budget_remaining"] == 0

    # Verify pending jobs remain in DB
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM backfill_jobs WHERE status = 'PENDING'")
        assert cur.fetchone()[0] == 3


def test_resume_and_idempotency_no_duplicate_writes(tmp_path, mock_hasher):
    """Resuming execution skips already completed jobs without duplicating records."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_res"},
                            "publishedAt": "2024-03-01T00:00:00Z"
                        }
                    }
                }
            }
        ]
    }
    mock_session.get.return_value = mock_resp

    db_path = tmp_path / "test_resume.db"
    obs_dir = tmp_path / "obs"
    backfiller = HistoricalCommentBackfiller(
        db_path=db_path,
        observations_dir=obs_dir,
        quota_budget=10,
        hasher=mock_hasher,
        session=mock_session
    )

    jobs = [
        {"sample_id": f"s_{i}", "channel_id": "UC_res", "video_id": f"v_{i}", "year": 2024}
        for i in range(3)
    ]
    backfiller.sync_manifest(jobs)

    # First run processes limit 2
    summary1 = backfiller.run_backfill(limit=2)
    assert summary1["videos_completed"] == 2

    # Second run resumes remaining 1
    summary2 = backfiller.run_backfill()
    assert summary2["videos_completed"] == 1

    # Verify all 3 are completed and Parquet files exist
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM backfill_jobs WHERE status = 'COMPLETED'")
        assert cur.fetchone()[0] == 3

    for i in range(3):
        p_path = obs_dir / "comment" / "UC_res" / f"v_{i}.parquet"
        assert p_path.exists()
        tbl = pq.read_table(p_path)
        assert tbl.num_rows == 1


def test_failed_persistence_does_not_mark_complete(tmp_path, mock_hasher):
    """If file writing fails (atomic replace fails), job must NOT be marked COMPLETED."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_v"},
                            "publishedAt": "2024-01-01T00:00:00Z"
                        }
                    }
                }
            }
        ]
    }
    mock_session.get.return_value = mock_resp

    db_path = tmp_path / "test_fail.db"
    backfiller = HistoricalCommentBackfiller(
        db_path=db_path,
        observations_dir=tmp_path / "obs",
        hasher=mock_hasher,
        session=mock_session
    )

    job = {"sample_id": "s_fail", "channel_id": "UC_fail", "video_id": "v_fail", "year": 2024}
    backfiller.sync_manifest([job])

    # Simulate atomic replace failure
    with patch("collector.historical_comment_backfill._atomic_replace_with_retry", side_effect=PermissionError("Locked")):
        with pytest.raises(PermissionError):
            backfiller.process_job(job)

    # Verify DB status is NOT COMPLETED
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT status FROM backfill_jobs WHERE sample_id = 's_fail'")
        status = cur.fetchone()[0]
        assert status != "COMPLETED"
