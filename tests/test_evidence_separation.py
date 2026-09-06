"""
Unit Tests for Evidence Separation and Strong Evidence Filtering:
- shared_live_chat, shared_comments, shared_any
- videos_seen, live_streams_seen
- strong_shared_any, strong_shared_live_chat, strong_shared_comments
- Persistent HMAC continuity check & loud failure
"""
import pytest
import tempfile
import shutil
from pathlib import Path
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from storage.parquet_manager import AGGREGATED_SCHEMA
from storage.duckdb_engine import DuckDBAnalyticsEngine
from core.hasher import (
    compute_key_fingerprint,
    load_persistent_secret_key,
    PrivacyHasher
)


@pytest.fixture
def temp_env():
    temp_dir = Path(tempfile.mkdtemp())
    events_dir = temp_dir / "events" / "2026" / "09"
    events_dir.mkdir(parents=True, exist_ok=True)
    yield temp_dir, events_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_evidence_separation_and_strong_overlap(temp_env):
    temp_dir, events_dir = temp_env

    # We set up 2 VTubers: V_A and V_B
    # We construct distinct viewers with different patterns:
    # 1. viewer_both_live_strong:
    #    - Appears in live_chat on 2 distinct streams of V_A (stream_a1, stream_a2)
    #    - Appears in live_chat on 2 distinct streams of V_B (stream_b1, stream_b2)
    #    -> Should be in: shared_any, shared_live_chat, strong_shared_any, strong_shared_live_chat
    #
    # 2. viewer_comment_only:
    #    - Appears in comment on 2 distinct videos of V_A (vid_a1, vid_a2)
    #    - Appears in comment on 2 distinct videos of V_B (vid_b1, vid_b2)
    #    -> Should be in: shared_any, shared_comments, strong_shared_any, strong_shared_comments
    #    -> MUST NOT be in: shared_live_chat, strong_shared_live_chat!
    #
    # 3. viewer_weak_mixed:
    #    - Appears in live_chat on 1 stream of V_A (stream_a1)
    #    - Appears in comment on 1 video of V_B (vid_b1)
    #    -> Should be in: shared_any
    #    -> MUST NOT be in: shared_live_chat, shared_comments, strong_shared_* (only 1 video on each)

    records = [
        # viewer_both_live_strong
        {"viewer_hash": "h_live_strong", "vtuber_channel_id": "V_A", "video_id": "stream_a1", "first_seen": "2026-09-01", "last_seen": "2026-09-01", "appearances": 5, "source_type": "live_chat"},
        {"viewer_hash": "h_live_strong", "vtuber_channel_id": "V_A", "video_id": "stream_a2", "first_seen": "2026-09-02", "last_seen": "2026-09-02", "appearances": 3, "source_type": "live_chat"},
        {"viewer_hash": "h_live_strong", "vtuber_channel_id": "V_B", "video_id": "stream_b1", "first_seen": "2026-09-01", "last_seen": "2026-09-01", "appearances": 4, "source_type": "live_chat"},
        {"viewer_hash": "h_live_strong", "vtuber_channel_id": "V_B", "video_id": "stream_b2", "first_seen": "2026-09-02", "last_seen": "2026-09-02", "appearances": 2, "source_type": "live_chat"},

        # viewer_comment_only
        {"viewer_hash": "h_comment_strong", "vtuber_channel_id": "V_A", "video_id": "vid_a1", "first_seen": "2026-09-03", "last_seen": "2026-09-03", "appearances": 1, "source_type": "comment"},
        {"viewer_hash": "h_comment_strong", "vtuber_channel_id": "V_A", "video_id": "vid_a2", "first_seen": "2026-09-04", "last_seen": "2026-09-04", "appearances": 1, "source_type": "comment"},
        {"viewer_hash": "h_comment_strong", "vtuber_channel_id": "V_B", "video_id": "vid_b1", "first_seen": "2026-09-03", "last_seen": "2026-09-03", "appearances": 1, "source_type": "comment"},
        {"viewer_hash": "h_comment_strong", "vtuber_channel_id": "V_B", "video_id": "vid_b2", "first_seen": "2026-09-04", "last_seen": "2026-09-04", "appearances": 1, "source_type": "comment"},

        # viewer_weak_mixed
        {"viewer_hash": "h_weak_mixed", "vtuber_channel_id": "V_A", "video_id": "stream_a1", "first_seen": "2026-09-01", "last_seen": "2026-09-01", "appearances": 1, "source_type": "live_chat"},
        {"viewer_hash": "h_weak_mixed", "vtuber_channel_id": "V_B", "video_id": "vid_b1", "first_seen": "2026-09-03", "last_seen": "2026-09-03", "appearances": 1, "source_type": "comment"}
    ]

    table = pa.Table.from_pydict({
        "viewer_hash": [r["viewer_hash"] for r in records],
        "vtuber_channel_id": [r["vtuber_channel_id"] for r in records],
        "video_id": [r["video_id"] for r in records],
        "first_seen": [r["first_seen"] for r in records],
        "last_seen": [r["last_seen"] for r in records],
        "appearances": [r["appearances"] for r in records],
        "source_type": [r["source_type"] for r in records]
    }, schema=AGGREGATED_SCHEMA)

    parquet_file = events_dir / "sample_events.parquet"
    pq.write_table(table, parquet_file)

    engine = DuckDBAnalyticsEngine(db_path=temp_dir / "test.duckdb", events_dir=temp_dir / "events")
    overlap = engine.compute_pairwise_overlap(min_shared_viewers=1, min_evidence_threshold=2)

    assert len(overlap) == 1
    pair = overlap[0]

    # Total shared viewers of any kind
    assert pair["shared_any"] == 3

    # Live chat only
    assert pair["shared_live_chat"] == 1  # only h_live_strong

    # Comments only
    assert pair["shared_comments"] == 1  # only h_comment_strong

    # Strong evidence checks (threshold >= 2 videos)
    assert pair["strong_shared_any"] == 2  # h_live_strong and h_comment_strong
    assert pair["strong_shared_live_chat"] == 1  # ONLY h_live_strong
    assert pair["strong_shared_comments"] == 1  # ONLY h_comment_strong

    # Terminology verification: live stream counts
    summary = engine.get_viewer_presence_summary()
    live_strong_summary = next(s for s in summary if s["viewer_hash"] == "h_live_strong" and s["vtuber_channel_id"] == "V_A")
    assert live_strong_summary["videos_seen"] == 2
    assert live_strong_summary["live_streams_seen"] == 2
    assert live_strong_summary["comment_videos_seen"] == 0

    comment_summary = next(s for s in summary if s["viewer_hash"] == "h_comment_strong" and s["vtuber_channel_id"] == "V_A")
    assert comment_summary["videos_seen"] == 2
    assert comment_summary["live_streams_seen"] == 0
    assert comment_summary["comment_videos_seen"] == 2


def test_persistent_hmac_continuity_check(tmp_path, monkeypatch):
    """Verifies that missing or altered secret keys fail loudly as a continuity check."""
    key_file = tmp_path / "secret.key"
    fp_file = tmp_path / "secret.fingerprint"

    monkeypatch.setattr("core.hasher.SECRET_KEY_PATH", key_file)
    monkeypatch.setattr("core.hasher.SECRET_FINGERPRINT_PATH", fp_file)
    monkeypatch.setattr("core.hasher.SALT_SECRET", "")

    # 1. Fail loudly if key is missing
    with pytest.raises(RuntimeError) as exc_info:
        load_persistent_secret_key()
    assert "FATAL ERROR: Persistent secret key missing" in str(exc_info.value)

    # 2. Setup key & fingerprint
    key_bytes = b"0123456789abcdef0123456789abcdef"
    key_file.write_text(key_bytes.decode("utf-8"))
    fp = compute_key_fingerprint(key_bytes)
    fp_file.write_text(fp)

    loaded_key = load_persistent_secret_key()
    assert loaded_key == key_bytes

    # 3. Fail loudly if key is swapped / fingerprint mismatch
    key_file.write_text("tampered_key_value_999999999999")
    with pytest.raises(RuntimeError) as exc_info:
        load_persistent_secret_key()
    assert "FATAL CONTINUITY CHECK ERROR: Key fingerprint mismatch" in str(exc_info.value)
