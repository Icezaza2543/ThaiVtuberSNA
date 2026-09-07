"""
Unit and Integration Test Suite for Historical Catalog Builder (Phase T1)
Validates:
1. Pagination loop (fetching across multiple 50-result pages).
2. Cutoff boundary (stopping at 2020-01-01T00:00:00Z with CUTOFF_REACHED).
3. Cap boundary (stopping at exactly 1,000 videos with CAP_REACHED).
4. Missing timestamp handling (NULL published date, timestamp_quality='missing').
5. Crash recovery and resume idempotency (zero duplicates after restart).
"""
import sys
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
import pyarrow.parquet as pq

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from collector.historical_catalog_builder import (
    HistoricalCatalogBuilder,
    DEFAULT_CUTOFF_DATE,
    _atomic_replace_with_retry
)


@pytest.fixture
def temp_catalog_dir():
    temp_dir = Path(tempfile.mkdtemp(prefix="test_historical_catalog_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def create_mock_api_item(video_id: str, published_at: str, added_at: str = "2024-01-01T00:00:00Z"):
    return {
        "contentDetails": {
            "videoId": video_id,
            "videoPublishedAt": published_at
        },
        "snippet": {
            "publishedAt": added_at,
            "title": f"Video {video_id}"
        }
    }


def test_pagination_loop(temp_catalog_dir):
    """Verifies pagination across 3 pages (50, 50, 20 = 120 items)."""
    builder = HistoricalCatalogBuilder(output_dir=temp_catalog_dir, max_videos_per_channel=200, api_key="test_key")

    page1_items = [create_mock_api_item(f"vid_p1_{i}", "2024-05-01T10:00:00Z") for i in range(50)]
    page2_items = [create_mock_api_item(f"vid_p2_{i}", "2023-05-01T10:00:00Z") for i in range(50)]
    page3_items = [create_mock_api_item(f"vid_p3_{i}", "2022-05-01T10:00:00Z") for i in range(20)]

    def mock_fetch(playlist_id, page_token=None):
        if page_token is None:
            return page1_items, "token_page_2", 200
        elif page_token == "token_page_2":
            return page2_items, "token_page_3", 200
        elif page_token == "token_page_3":
            return page3_items, None, 200
        return [], None, 404

    with patch.object(builder, "fetch_page_api", side_effect=mock_fetch):
        res = builder.crawl_channel("UC_test_channel_01", target_reason="test_pagination")

    assert res["videos_collected"] == 120
    assert res["api_calls"] == 3
    assert res["termination_reason"] == "PLAYLIST_EXHAUSTED"
    assert res["status"] == "completed"

    # Verify parquet contents
    tbl = pq.read_table(builder.video_catalog_path)
    assert len(tbl) == 120
    assert len(set(tbl["video_id"].to_pylist())) == 120


def test_cutoff_boundary(temp_catalog_dir):
    """Verifies stopping at 2020-01-01 cutoff with CUTOFF_REACHED."""
    builder = HistoricalCatalogBuilder(output_dir=temp_catalog_dir, max_videos_per_channel=500, api_key="test_key")

    # Page 1: 3 videos from 2021, followed by 1 video from 2019-12-31 (pre-cutoff)
    page_items = [
        create_mock_api_item("vid_2022", "2022-06-01T00:00:00Z"),
        create_mock_api_item("vid_2021", "2021-06-01T00:00:00Z"),
        create_mock_api_item("vid_2020", "2020-02-01T00:00:00Z"),
        create_mock_api_item("vid_2019_pre_cutoff", "2019-12-31T23:59:59Z"),
    ]

    with patch.object(builder, "fetch_page_api", return_value=(page_items, "token_unused", 200)):
        res = builder.crawl_channel("UC_test_cutoff_02", target_reason="test_cutoff")

    assert res["termination_reason"] == "CUTOFF_REACHED"
    assert res["videos_collected"] == 3  # Pre-cutoff video is excluded
    assert res["status"] == "completed"

    tbl = pq.read_table(builder.video_catalog_path)
    assert len(tbl) == 3
    assert "vid_2019_pre_cutoff" not in tbl["video_id"].to_pylist()


def test_cap_boundary(temp_catalog_dir):
    """Verifies stopping at exact cap of 1,000 videos with CAP_REACHED."""
    builder = HistoricalCatalogBuilder(output_dir=temp_catalog_dir, max_videos_per_channel=1000, api_key="test_key")

    # Mock generator for 25 pages of 50 items (1,250 items total)
    def mock_fetch(playlist_id, page_token=None):
        page_num = int(page_token.split("_")[-1]) if page_token else 1
        items = [
            create_mock_api_item(f"vid_{page_num}_{i}", "2023-01-01T00:00:00Z")
            for i in range(50)
        ]
        next_tok = f"token_{page_num + 1}" if page_num < 25 else None
        return items, next_tok, 200

    with patch.object(builder, "fetch_page_api", side_effect=mock_fetch):
        res = builder.crawl_channel("UC_test_cap_03", target_reason="test_cap")

    assert res["videos_collected"] == 1000
    assert res["api_calls"] == 20  # Exactly 20 calls to reach 1,000
    assert res["termination_reason"] == "CAP_REACHED"
    assert res["hit_cap"] is True

    tbl = pq.read_table(builder.video_catalog_path)
    assert len(tbl) == 1000


def test_missing_timestamp_handling(temp_catalog_dir):
    """Verifies missing videoPublishedAt is stored as NULL with timestamp_quality='missing'."""
    builder = HistoricalCatalogBuilder(output_dir=temp_catalog_dir, max_videos_per_channel=10, api_key="test_key")

    items = [
        create_mock_api_item("vid_normal", "2023-06-01T12:00:00Z"),
        {
            "contentDetails": {"videoId": "vid_missing_date"},
            "snippet": {"publishedAt": "2024-01-01T00:00:00Z", "title": "Missing Date Vid"}
        }
    ]

    with patch.object(builder, "fetch_page_api", return_value=(items, None, 200)):
        res = builder.crawl_channel("UC_test_missing_ts_04")

    assert res["videos_collected"] == 2
    tbl = pq.read_table(builder.video_catalog_path)
    records = tbl.to_pylist()

    normal_rec = [r for r in records if r["video_id"] == "vid_normal"][0]
    missing_rec = [r for r in records if r["video_id"] == "vid_missing_date"][0]

    assert normal_rec["timestamp_quality"] == "exact"
    assert normal_rec["video_published_at"] is not None

    assert missing_rec["timestamp_quality"] == "missing"
    assert missing_rec["video_published_at"] is None


def test_crash_recovery_and_resume(temp_catalog_dir):
    """Verifies atomic page persistence and resume without duplicate entries."""
    builder1 = HistoricalCatalogBuilder(output_dir=temp_catalog_dir, max_videos_per_channel=100, api_key="test_key")

    page1_items = [create_mock_api_item(f"vid_cr_{i}", "2023-01-01T00:00:00Z") for i in range(50)]
    page2_items = [create_mock_api_item(f"vid_cr_{i}", "2022-01-01T00:00:00Z") for i in range(50, 100)]

    # Page 1 completes, then simulated crash before page 2
    with patch.object(builder1, "fetch_page_api", side_effect=[
        (page1_items, "token_for_page_2", 200),
        ([], None, 500)  # Crash / 500 error on page 2
    ]):
        res1 = builder1.crawl_channel("UC_test_crash_05")

    assert res1["status"] == "failed"
    assert res1["videos_collected"] == 50

    # Instantiate fresh builder to simulate process restart
    builder2 = HistoricalCatalogBuilder(output_dir=temp_catalog_dir, max_videos_per_channel=100, api_key="test_key")
    assert "UC_test_crash_05" in builder2.checkpoint["in_progress_channels"]
    assert builder2.checkpoint["in_progress_channels"]["UC_test_crash_05"]["next_page_token"] == "token_for_page_2"

    # Resume with page 2 completing
    with patch.object(builder2, "fetch_page_api", return_value=(page2_items, None, 200)):
        res2 = builder2.crawl_channel("UC_test_crash_05")

    assert res2["status"] == "completed"
    assert res2["videos_collected"] == 100

    # Ensure parquet output contains exactly 100 distinct items (zero duplicates)
    tbl = pq.read_table(builder2.video_catalog_path)
    vids = tbl["video_id"].to_pylist()
    assert len(vids) == 100
    assert len(set(vids)) == 100


def test_atomic_replace_fails_all_attempts_fails_closed(temp_catalog_dir):
    """
    Test A: Replacement fails all 5 attempts.
    Must raise exception, target file remains unchanged, seen_video_ids is NOT updated,
    and temporary file is cleaned up.
    """
    builder = HistoricalCatalogBuilder(output_dir=temp_catalog_dir, api_key="test_key")

    # Initial write of 1 good record
    initial_rec = {
        "channel_id": "UC_initial",
        "video_id": "vid_init",
        "video_published_at": datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        "playlist_added_at": datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        "timestamp_quality": "exact",
        "fetched_at": datetime(2026, 9, 8, 0, 0, 0, tzinfo=timezone.utc),
        "page_index": 0,
        "source": "youtube_api_v3",
        "schema_version": "2.0"
    }
    builder._append_video_records_atomic([initial_rec])
    assert "vid_init" in builder.seen_video_ids
    assert len(builder.seen_video_ids) == 1

    # Attempt to append bad record with Path.replace raising PermissionError
    bad_rec = {
        "channel_id": "UC_initial",
        "video_id": "vid_bad_failed_write",
        "video_published_at": datetime(2023, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        "playlist_added_at": datetime(2023, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        "timestamp_quality": "exact",
        "fetched_at": datetime(2026, 9, 8, 0, 0, 0, tzinfo=timezone.utc),
        "page_index": 1,
        "source": "youtube_api_v3",
        "schema_version": "2.0"
    }

    with patch("pathlib.Path.replace", side_effect=PermissionError("Simulated WinError 5 Access is denied")):
        with pytest.raises(PermissionError):
            builder._append_video_records_atomic([bad_rec])

    # In-memory state must NOT have updated
    assert "vid_bad_failed_write" not in builder.seen_video_ids
    assert len(builder.seen_video_ids) == 1

    # Target parquet must remain intact with only initial record
    tbl = pq.read_table(builder.video_catalog_path)
    vids = tbl["video_id"].to_pylist()
    assert vids == ["vid_init"]

    # Temporary file must be cleaned up
    tmp_file = builder.video_catalog_path.with_suffix(".tmp")
    assert not tmp_file.exists()


def test_atomic_replace_eventual_success_after_retries(temp_catalog_dir):
    """
    Test B: Replacement fails twice with PermissionError and succeeds on third attempt.
    Must succeed without error, target updated, and in-memory state updated once.
    """
    builder = HistoricalCatalogBuilder(output_dir=temp_catalog_dir, api_key="test_key")

    rec = {
        "channel_id": "UC_retry",
        "video_id": "vid_retry_success",
        "video_published_at": datetime(2023, 2, 1, 0, 0, 0, tzinfo=timezone.utc),
        "playlist_added_at": datetime(2023, 2, 1, 0, 0, 0, tzinfo=timezone.utc),
        "timestamp_quality": "exact",
        "fetched_at": datetime(2026, 9, 8, 0, 0, 0, tzinfo=timezone.utc),
        "page_index": 0,
        "source": "youtube_api_v3",
        "schema_version": "2.0"
    }

    call_count = 0
    orig_replace = Path.replace

    def mock_replace_flaky(self, target):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise PermissionError(f"Simulated Windows file lock attempt {call_count}")
        return orig_replace(self, target)

    with patch("pathlib.Path.replace", autospec=True, side_effect=mock_replace_flaky):
        builder._append_video_records_atomic([rec])

    assert call_count == 3
    assert "vid_retry_success" in builder.seen_video_ids

    # Target parquet updated cleanly
    tbl = pq.read_table(builder.video_catalog_path)
    vids = tbl["video_id"].to_pylist()
    assert vids == ["vid_retry_success"]
