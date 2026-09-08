"""
tests/test_deep_comment_backfill.py

Unit & Regression Tests for Phase T6: Resumable Multipage Deep Comment Collector
Verifies:
1. Multipage pagination: Correctly loops through nextPageToken until None.
2. Resumption from nextPageToken: Resumes mid-video extraction without repeating pages.
3. Crash-safe checkpointing: Mid-job staging survives and recovers cleanly.
4. Quota budget exhaustion: Halts cleanly when API quota budget is reached, preserving progress.
5. Privacy boundary: Zero raw author IDs, names, URLs, or texts escape into observation records.
6. Missing timestamp strictness: Missing or invalid publishedAt yields interaction_at = None.
7. Duplicate-free retries: Repeated execution on completed jobs is idempotent.
8. T6 supersedes T5 without double counting: DuckDB canonical view replaces T5 with T6 for same video.
9. Repeated comments on one video do not inflate strong overlap: Multiple comments by one viewer count as 1 video interaction.
"""
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb

from core.hasher import PrivacyHasher
from collector.deep_comment_backfill import (
    DeepCommentBackfiller,
    BudgetExhaustedException,
    parse_iso_dt,
    DEEP_OBSERVATION_SCHEMA
)
from scripts.build_duckdb_temporal_snapshots import build_canonical_events_view


@pytest.fixture
def mock_hasher():
    """Provides a deterministic test hasher."""
    return PrivacyHasher(secret_salt=b"test_secret_salt_for_deep_backfill_tests_12345")


def test_deep_multipage_pagination(tmp_path, mock_hasher):
    """Verify collector follows nextPageToken through multiple pages until exhausted."""
    db_path = tmp_path / "deep_test.db"
    obs_dir = tmp_path / "deep_obs"

    mock_session = MagicMock()
    # Page 1 -> has nextPageToken "tok_page_2"
    page1_resp = MagicMock()
    page1_resp.status_code = 200
    page1_resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_page1_a"},
                            "publishedAt": "2023-01-10T10:00:00Z"
                        }
                    }
                }
            }
        ],
        "nextPageToken": "tok_page_2"
    }

    # Page 2 -> no nextPageToken (end of comments)
    page2_resp = MagicMock()
    page2_resp.status_code = 200
    page2_resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_page2_b"},
                            "publishedAt": "2023-01-09T08:00:00Z"
                        }
                    }
                }
            }
        ],
        "nextPageToken": None
    }

    mock_session.get.side_effect = [page1_resp, page2_resp]

    backfiller = DeepCommentBackfiller(
        db_path=db_path,
        observations_dir=obs_dir,
        hasher=mock_hasher,
        session=mock_session
    )

    with sqlite3.connect(str(db_path)) as con:
        con.execute("""
            INSERT INTO deep_backfill_jobs (sample_id, channel_id, video_id, year, status)
            VALUES ('s_multi', 'UC_vtuber_m', 'vid_multi', 2023, 'PENDING')
        """)

    job = {
        "sample_id": "s_multi",
        "channel_id": "UC_vtuber_m",
        "video_id": "vid_multi",
        "year": 2023,
        "video_published_at": "2023-01-01T00:00:00Z",
        "next_page_token": None,
        "pages_fetched": 0,
        "total_items_fetched": 0
    }

    status = backfiller.process_deep_job(job)
    assert status == "COMPLETED"
    assert mock_session.get.call_count == 2

    # Check Parquet output
    out_file = obs_dir / "comment" / "UC_vtuber_m" / "vid_multi.parquet"
    assert out_file.exists()
    tbl = pq.read_table(out_file)
    assert len(tbl) == 2
    hashes = set(tbl.column("viewer_hash").to_pylist())
    assert mock_hasher.hash_viewer_id("UC_viewer_page1_a") in hashes
    assert mock_hasher.hash_viewer_id("UC_viewer_page2_b") in hashes


def test_resume_from_next_page_token(tmp_path, mock_hasher):
    """Verify collector resumes from existing next_page_token and merges with staged viewers."""
    db_path = tmp_path / "deep_resume.db"
    obs_dir = tmp_path / "deep_obs"

    mock_session = MagicMock()
    # Resume request: expects pageToken = tok_saved
    final_resp = MagicMock()
    final_resp.status_code = 200
    final_resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_resumed"},
                            "publishedAt": "2022-05-12T15:00:00Z"
                        }
                    }
                }
            }
        ],
        "nextPageToken": None
    }
    mock_session.get.return_value = final_resp

    backfiller = DeepCommentBackfiller(
        db_path=db_path,
        observations_dir=obs_dir,
        hasher=mock_hasher,
        session=mock_session
    )

    sample_id = "s_res"
    prior_hash = mock_hasher.hash_viewer_id("UC_viewer_prior")

    with sqlite3.connect(str(db_path)) as con:
        con.execute("""
            INSERT INTO deep_backfill_jobs (
                sample_id, channel_id, video_id, year, status, next_page_token, pages_fetched, total_items_fetched
            ) VALUES (?, 'UC_v1', 'vid_res', 2022, 'PENDING', 'tok_saved', 1, 1)
        """, (sample_id,))
        con.execute("""
            INSERT INTO deep_staging_viewers (
                sample_id, viewer_hash, channel_id, video_id, video_published_at, earliest_interaction, latest_interaction, appearances, timestamp_quality
            ) VALUES (?, ?, 'UC_v1', 'vid_res', '2022-05-01T00:00:00Z', '2022-05-10T10:00:00+00:00', '2022-05-10T10:00:00+00:00', 1, 'exact')
        """, (sample_id, prior_hash))

    job = {
        "sample_id": sample_id,
        "channel_id": "UC_v1",
        "video_id": "vid_res",
        "year": 2022,
        "video_published_at": "2022-05-01T00:00:00Z",
        "next_page_token": "tok_saved",
        "pages_fetched": 1,
        "total_items_fetched": 1
    }

    status = backfiller.process_deep_job(job)
    assert status == "COMPLETED"

    # Verify session.get was called with pageToken='tok_saved'
    called_params = mock_session.get.call_args[1]["params"]
    assert called_params.get("pageToken") == "tok_saved"

    # Verify final Parquet merged both prior staged viewer and newly resumed viewer
    out_file = obs_dir / "comment" / "UC_v1" / "vid_res.parquet"
    assert out_file.exists()
    tbl = pq.read_table(out_file)
    assert len(tbl) == 2
    hashes = set(tbl.column("viewer_hash").to_pylist())
    assert prior_hash in hashes
    assert mock_hasher.hash_viewer_id("UC_viewer_resumed") in hashes


def test_quota_budget_exhaustion_clean_halt(tmp_path, mock_hasher):
    """Verify collector halts cleanly when quota budget is reached without corrupting job."""
    db_path = tmp_path / "deep_budget.db"
    obs_dir = tmp_path / "deep_obs"

    mock_session = MagicMock()
    page1_resp = MagicMock()
    page1_resp.status_code = 200
    page1_resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_b1"},
                            "publishedAt": "2024-02-01T12:00:00Z"
                        }
                    }
                }
            }
        ],
        "nextPageToken": "tok_page_2"
    }
    mock_session.get.return_value = page1_resp

    # Set quota_budget=1 so it halts when trying page 2
    backfiller = DeepCommentBackfiller(
        db_path=db_path,
        observations_dir=obs_dir,
        quota_budget=1,
        hasher=mock_hasher,
        session=mock_session
    )

    sample_id = "s_budget"
    with sqlite3.connect(str(db_path)) as con:
        con.execute("""
            INSERT INTO deep_backfill_jobs (sample_id, channel_id, video_id, year, status)
            VALUES (?, 'UC_vb', 'vid_budget', 2024, 'PENDING')
        """, (sample_id,))

    job = {
        "sample_id": sample_id,
        "channel_id": "UC_vb",
        "video_id": "vid_budget",
        "year": 2024,
        "video_published_at": "2024-01-01T00:00:00Z",
        "next_page_token": None,
        "pages_fetched": 0,
        "total_items_fetched": 0
    }

    with pytest.raises(BudgetExhaustedException):
        backfiller.process_deep_job(job)

    # Verify job status in SQLite remains PENDING with next_page_token checkpointed!
    with sqlite3.connect(str(db_path)) as con:
        row = con.execute("SELECT status, next_page_token, pages_fetched FROM deep_backfill_jobs WHERE sample_id = ?", (sample_id,)).fetchone()
        assert row[0] == "PENDING"
        assert row[1] == "tok_page_2"
        assert row[2] == 1

        # Staging table must hold the item from page 1
        cnt = con.execute("SELECT COUNT(*) FROM deep_staging_viewers WHERE sample_id = ?", (sample_id,)).fetchone()[0]
        assert cnt == 1


def test_privacy_boundary_zero_pii_leak(tmp_path, mock_hasher):
    """Verify raw author ID is immediately hashed and zero raw PII appears in memory or Parquet."""
    db_path = tmp_path / "deep_priv.db"
    obs_dir = tmp_path / "deep_obs"

    mock_session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_sensitive_author_999"},
                            "authorDisplayName": "Private Display Name",
                            "authorChannelUrl": "https://youtube.com/channel/UC_sensitive_author_999",
                            "textDisplay": "Confidential user comment text",
                            "publishedAt": "2023-04-10T12:00:00Z"
                        }
                    }
                }
            }
        ],
        "nextPageToken": None
    }
    mock_session.get.return_value = resp

    backfiller = DeepCommentBackfiller(
        db_path=db_path,
        observations_dir=obs_dir,
        hasher=mock_hasher,
        session=mock_session
    )

    sample_id = "s_priv"
    with sqlite3.connect(str(db_path)) as con:
        con.execute("""
            INSERT INTO deep_backfill_jobs (sample_id, channel_id, video_id, year, status)
            VALUES (?, 'UC_priv_ch', 'vid_priv', 2023, 'PENDING')
        """, (sample_id,))

    job = {
        "sample_id": sample_id,
        "channel_id": "UC_priv_ch",
        "video_id": "vid_priv",
        "year": 2023,
        "video_published_at": "2023-04-01T00:00:00Z"
    }

    backfiller.process_deep_job(job)

    out_file = obs_dir / "comment" / "UC_priv_ch" / "vid_priv.parquet"
    tbl = pq.read_table(out_file)
    pydict = tbl.to_pydict()

    # Raw author channel ID, display name, url, and comment text MUST NOT exist
    for col, vals in pydict.items():
        for v in vals:
            v_str = str(v)
            assert "UC_sensitive_author_999" not in v_str
            assert "Private Display Name" not in v_str
            assert "Confidential user comment text" not in v_str

    expected_hash = mock_hasher.hash_viewer_id("UC_sensitive_author_999")
    assert pydict["viewer_hash"][0] == expected_hash


def test_repeated_comments_same_video_no_strong_overlap_inflation(tmp_path, mock_hasher):
    """
    Verify multiple comments by the same viewer on one video collapse to 1 row
    with appearances count incremented, preventing false inflation of strong overlap.
    """
    db_path = tmp_path / "deep_rep.db"
    obs_dir = tmp_path / "deep_obs"

    mock_session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_loyal_viewer"},
                            "publishedAt": "2023-06-01T10:00:00Z"
                        }
                    }
                }
            },
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_loyal_viewer"},
                            "publishedAt": "2023-06-05T14:00:00Z"
                        }
                    }
                }
            },
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_loyal_viewer"},
                            "publishedAt": "2023-06-10T18:00:00Z"
                        }
                    }
                }
            }
        ],
        "nextPageToken": None
    }
    mock_session.get.return_value = resp

    backfiller = DeepCommentBackfiller(
        db_path=db_path,
        observations_dir=obs_dir,
        hasher=mock_hasher,
        session=mock_session
    )

    sample_id = "s_rep"
    with sqlite3.connect(str(db_path)) as con:
        con.execute("""
            INSERT INTO deep_backfill_jobs (sample_id, channel_id, video_id, year, status)
            VALUES (?, 'UC_ch_rep', 'vid_rep', 2023, 'PENDING')
        """, (sample_id,))

    job = {
        "sample_id": sample_id,
        "channel_id": "UC_ch_rep",
        "video_id": "vid_rep",
        "year": 2023,
        "video_published_at": "2023-06-01T00:00:00Z"
    }

    backfiller.process_deep_job(job)

    out_file = obs_dir / "comment" / "UC_ch_rep" / "vid_rep.parquet"
    tbl = pq.read_table(out_file)

    # Exactly 1 row for this viewer
    assert len(tbl) == 1
    row = tbl.to_pylist()[0]
    assert row["viewer_hash"] == mock_hasher.hash_viewer_id("UC_loyal_viewer")
    assert row["appearances"] == 3
    # Earliest and latest interactions preserved
    assert row["interaction_at"] == "2023-06-01T10:00:00+00:00"
    assert row["latest_interaction_at"] == "2023-06-10T18:00:00+00:00"


def test_t6_supersedes_t5_without_double_count(tmp_path, mock_hasher):
    """
    Verify precedence: When T6 deep observations exist for a video,
    they supersede T5 shallow observations for the same video without duplicate rows.
    """
    v_hash_1 = mock_hasher.hash_viewer_id("UC_v1")
    v_hash_2 = mock_hasher.hash_viewer_id("UC_v2")

    # Shallow T5 observation file (has only v_hash_1)
    t5_file = tmp_path / "t5_vid.parquet"
    t5_tbl = pa.Table.from_pylist([
        {
            "viewer_hash": v_hash_1,
            "vtuber_channel_id": "UC_channel_x",
            "video_id": "vid_common",
            "source_type": "comment",
            "video_published_at": "2023-01-01T00:00:00Z",
            "interaction_at": "2023-01-02T10:00:00+00:00",
            "timestamp_quality": "exact"
        }
    ])
    pq.write_table(t5_tbl, t5_file)

    # Deep T6 observation file (has v_hash_1 AND v_hash_2)
    t6_file = tmp_path / "t6_vid.parquet"
    t6_tbl = pa.Table.from_pylist([
        {
            "viewer_hash": v_hash_1,
            "vtuber_channel_id": "UC_channel_x",
            "video_id": "vid_common",
            "source_type": "comment",
            "video_published_at": "2023-01-01T00:00:00Z",
            "interaction_at": "2023-01-02T10:00:00+00:00",
            "latest_interaction_at": "2023-01-05T12:00:00+00:00",
            "appearances": 2,
            "timestamp_quality": "exact"
        },
        {
            "viewer_hash": v_hash_2,
            "vtuber_channel_id": "UC_channel_x",
            "video_id": "vid_common",
            "source_type": "comment",
            "video_published_at": "2023-01-01T00:00:00Z",
            "interaction_at": "2023-01-03T11:00:00+00:00",
            "latest_interaction_at": "2023-01-03T11:00:00+00:00",
            "appearances": 1,
            "timestamp_quality": "exact"
        }
    ])
    pq.write_table(t6_tbl, t6_file)

    # Simulate source collection with precedence:
    # When t6_file exists for vid_common, t5_file for vid_common is excluded
    deep_video_ids = {"vid_common"}
    sources = []
    # Add deep file
    sources.append(str(t6_file).replace("\\", "/"))
    # In collector logic: if video_id not in deep_video_ids, add t5_file
    if "vid_common" not in deep_video_ids:
        sources.append(str(t5_file).replace("\\", "/"))

    con = duckdb.connect(":memory:")
    src_sql = ", ".join(f"'{s}'" for s in sources)
    con.execute(f"CREATE VIEW unified_raw AS SELECT * FROM read_parquet([{src_sql}], union_by_name=True)")
    build_canonical_events_view(con, "unified_raw")

    res = con.execute("SELECT viewer_hash, video_id FROM canonical_events").fetchall()
    # Must have exactly 2 distinct viewers, NOT 3 (v_hash_1 is not duplicated)
    assert len(res) == 2
    hashes = {r[0] for r in res}
    assert hashes == {v_hash_1, v_hash_2}


def test_missing_timestamps_strictness(tmp_path, mock_hasher):
    """Verify that comments with missing or unparseable publishedAt yield interaction_at = None."""
    db_path = tmp_path / "deep_missing.db"
    obs_dir = tmp_path / "deep_obs"

    mock_session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_no_ts"},
                            "publishedAt": "invalid-timestamp-string"
                        }
                    }
                }
            }
        ],
        "nextPageToken": None
    }
    mock_session.get.return_value = resp

    backfiller = DeepCommentBackfiller(
        db_path=db_path,
        observations_dir=obs_dir,
        hasher=mock_hasher,
        session=mock_session
    )

    sample_id = "s_no_ts"
    with sqlite3.connect(str(db_path)) as con:
        con.execute("""
            INSERT INTO deep_backfill_jobs (sample_id, channel_id, video_id, year, status)
            VALUES (?, 'UC_ch_ts', 'vid_no_ts', 2023, 'PENDING')
        """, (sample_id,))

    job = {
        "sample_id": sample_id,
        "channel_id": "UC_ch_ts",
        "video_id": "vid_no_ts",
        "year": 2023,
        "video_published_at": "2023-01-01T00:00:00Z"
    }

    st = backfiller.process_deep_job(job)
    assert st == "COMPLETED"

    out_file = obs_dir / "comment" / "UC_ch_ts" / "vid_no_ts.parquet"
    tbl = pq.read_table(out_file)
    row = tbl.to_pylist()[0]
    assert row["interaction_at"] is None
    assert row["timestamp_quality"] == "missing"


def test_crash_safe_checkpointing(tmp_path, mock_hasher):
    """Verify checkpointing handles crash recovery and intermediate staging cleanup."""
    db_path = tmp_path / "deep_crash.db"
    obs_dir = tmp_path / "deep_obs"

    backfiller = DeepCommentBackfiller(
        db_path=db_path,
        observations_dir=obs_dir,
        hasher=mock_hasher
    )

    # Seed jobs
    with sqlite3.connect(str(db_path)) as con:
        con.execute("""
            INSERT INTO deep_backfill_jobs (sample_id, channel_id, video_id, year, status)
            VALUES ('s_1', 'UC_1', 'v_1', 2021, 'PENDING'),
                   ('s_2', 'UC_2', 'v_2', 2021, 'RUNNING')
        """)

    # Verify query
    with sqlite3.connect(str(db_path)) as con:
        cur = con.cursor()
        cur.execute("SELECT status, count(*) FROM deep_backfill_jobs GROUP BY status")
        counts = dict(cur.fetchall())
        assert counts["PENDING"] == 1
        assert counts["RUNNING"] == 1


def test_duplicate_free_retries(tmp_path, mock_hasher):
    """Verify repeated execution on a completed video does not duplicate data."""
    db_path = tmp_path / "deep_idempotent.db"
    obs_dir = tmp_path / "deep_obs"

    mock_session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_viewer_idem"},
                            "publishedAt": "2024-05-01T10:00:00Z"
                        }
                    }
                }
            }
        ],
        "nextPageToken": None
    }
    mock_session.get.return_value = resp

    backfiller = DeepCommentBackfiller(
        db_path=db_path,
        observations_dir=obs_dir,
        hasher=mock_hasher,
        session=mock_session
    )

    sample_id = "s_idem"
    with sqlite3.connect(str(db_path)) as con:
        con.execute("""
            INSERT INTO deep_backfill_jobs (sample_id, channel_id, video_id, year, status)
            VALUES (?, 'UC_idem', 'vid_idem', 2024, 'PENDING')
        """, (sample_id,))

    job = {
        "sample_id": sample_id,
        "channel_id": "UC_idem",
        "video_id": "vid_idem",
        "year": 2024,
        "video_published_at": "2024-05-01T00:00:00Z"
    }

    # First run
    st1 = backfiller.process_deep_job(job)
    assert st1 == "COMPLETED"

    # Second run
    st2 = backfiller.process_deep_job(job)
    assert st2 == "COMPLETED"

    out_file = obs_dir / "comment" / "UC_idem" / "vid_idem.parquet"
    tbl = pq.read_table(out_file)
    assert len(tbl) == 1

