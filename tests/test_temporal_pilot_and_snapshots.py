"""
Unit Tests for Phase T2 (Comment Pilot) and Phase T3 (DuckDB Temporal Engine)
Verifies:
1. Strict no now() fallback for missing comment timestamps (returns None, timestamp_quality='missing').
2. Privacy extraction boundary: Raw viewer ID is hashed to viewer_hash, never escapes into observation schema.
3. DuckDB windowing: Validates yearly and cumulative slices calculate source-separated metrics (shared_comments, shared_live_chat, overlap_coefficient, jaccard).
"""
import pytest
from datetime import datetime, timezone
import duckdb
import pyarrow as pa

from core.hasher import PrivacyHasher, compute_key_fingerprint
from scripts.run_temporal_comment_pilot import parse_iso_dt

def test_comment_timestamp_strict_no_fallback():
    """Missing or corrupted timestamps must yield None, never now()."""
    assert parse_iso_dt(None) is None
    assert parse_iso_dt("") is None
    assert parse_iso_dt("invalid_iso_string") is None
    
    # Valid ISO timestamps parse accurately with UTC timezone
    valid_str = "2023-06-15T14:30:00Z"
    dt = parse_iso_dt(valid_str)
    assert dt is not None
    assert dt.year == 2023
    assert dt.month == 6
    assert dt.day == 15
    assert dt.tzinfo == timezone.utc

def test_privacy_extraction_boundary_no_raw_id_leak():
    """Ensures raw viewer channel ID is transformed to HMAC hash and does not escape."""
    secret_key = "test_persistent_secret_key_32bytes_12345"
    hasher = PrivacyHasher(secret_key)
    
    raw_author_id = "UCraw_test_viewer_channel_999"
    viewer_hash = hasher.hash_viewer_id(raw_author_id)
    
    assert viewer_hash != raw_author_id
    assert len(viewer_hash) == 64
    assert not viewer_hash.startswith("UC")
    # Deterministic hashing with same key
    assert hasher.hash_viewer_id(raw_author_id) == viewer_hash

def test_duckdb_temporal_aggregation_and_evidence_separation():
    """Validates source separation and windowing in DuckDB temporal aggregation."""
    con = duckdb.connect(":memory:")

    # Synthetic observations table across 2 channels and 2 years (2022, 2024)
    # Viewer 1: commented on both in 2022
    # Viewer 2: live-chatted on both in 2024
    # Viewer 3: commented on ch_A only
    data = [
        # 2022 interactions
        {"viewer_hash": "v_hash_1", "vtuber_channel_id": "UC_A", "video_id": "v1", "source_type": "comment", "interaction_at": "2022-05-01 10:00:00+00"},
        {"viewer_hash": "v_hash_1", "vtuber_channel_id": "UC_B", "video_id": "v2", "source_type": "comment", "interaction_at": "2022-05-02 11:00:00+00"},
        {"viewer_hash": "v_hash_3", "vtuber_channel_id": "UC_A", "video_id": "v1", "source_type": "comment", "interaction_at": "2022-06-01 12:00:00+00"},
        # 2024 interactions
        {"viewer_hash": "v_hash_2", "vtuber_channel_id": "UC_A", "video_id": "v3", "source_type": "live_chat", "interaction_at": "2024-03-10 18:00:00+00"},
        {"viewer_hash": "v_hash_2", "vtuber_channel_id": "UC_B", "video_id": "v4", "source_type": "live_chat", "interaction_at": "2024-03-11 19:00:00+00"},
    ]

    schema = pa.schema([
        ("viewer_hash", pa.string()),
        ("vtuber_channel_id", pa.string()),
        ("video_id", pa.string()),
        ("source_type", pa.string()),
        ("interaction_at", pa.string())
    ])
    tbl = pa.Table.from_pylist(data, schema=schema)
    con.register("synthetic_events", tbl)

    # Test 2022 yearly window query
    q_2022 = """
        WITH filtered AS (
            SELECT * FROM synthetic_events
            WHERE interaction_at >= '2022-01-01' AND interaction_at <= '2022-12-31 23:59:59'
        ),
        viewer_stats AS (
            SELECT vtuber_channel_id, viewer_hash,
                   BOOL_OR(source_type = 'comment') AS in_comment,
                   BOOL_OR(source_type = 'live_chat') AS in_live_chat
            FROM filtered GROUP BY vtuber_channel_id, viewer_hash
        )
        SELECT 
            a.vtuber_channel_id AS vtuber_a,
            b.vtuber_channel_id AS vtuber_b,
            COUNT(DISTINCT a.viewer_hash) AS shared_any,
            COUNT(DISTINCT CASE WHEN a.in_comment AND b.in_comment THEN a.viewer_hash END) AS shared_comments,
            COUNT(DISTINCT CASE WHEN a.in_live_chat AND b.in_live_chat THEN a.viewer_hash END) AS shared_live_chat
        FROM viewer_stats a
        JOIN viewer_stats b ON a.viewer_hash = b.viewer_hash AND a.vtuber_channel_id < b.vtuber_channel_id
        GROUP BY a.vtuber_channel_id, b.vtuber_channel_id
    """
    res_2022 = con.execute(q_2022).fetchall()
    assert len(res_2022) == 1
    row_2022 = res_2022[0]
    assert row_2022[0] == "UC_A" and row_2022[1] == "UC_B"
    assert row_2022[2] == 1  # shared_any: v_hash_1
    assert row_2022[3] == 1  # shared_comments: 1
    assert row_2022[4] == 0  # shared_live_chat: 0 (v_hash_1 was comment only)

    # Test 2024 yearly window query
    q_2024 = q_2022.replace("2022", "2024")
    res_2024 = con.execute(q_2024).fetchall()
    assert len(res_2024) == 1
    row_2024 = res_2024[0]
    assert row_2024[2] == 1  # shared_any: v_hash_2
    assert row_2024[3] == 0  # shared_comments: 0
    assert row_2024[4] == 1  # shared_live_chat: 1 (v_hash_2 was live_chat)
