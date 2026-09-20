"""
Tests for DuckDB Store, Interactions, and Worker State
"""
import pytest
from datetime import datetime, timezone
from pathlib import Path

from thaivtubersna.store import (
    open_db,
    record_interaction,
    count,
    get_state,
    set_state,
    upsert,
    verify_parity,
)


@pytest.fixture
def mem_db():
    con = open_db(Path(":memory:"))
    yield con
    con.close()


def test_record_interaction_idempotent(mem_db):
    assert count(mem_db, "interactions") == 0

    # Insert interaction
    record_interaction(
        mem_db,
        creator_id="UC_creator_1",
        video_id="vid_123",
        viewer_hash="hash_viewer_abc",
        source_type="live_chat",
        observed_at="2026-09-20T10:00:00Z",
    )
    assert count(mem_db, "interactions") == 1

    # Insert exact duplicate -> skipped due to UNIQUE constraint
    record_interaction(
        mem_db,
        creator_id="UC_creator_1",
        video_id="vid_123",
        viewer_hash="hash_viewer_abc",
        source_type="live_chat",
        observed_at="2026-09-20T10:05:00Z",
    )
    assert count(mem_db, "interactions") == 1

    # Insert different source_type -> distinct interaction
    record_interaction(
        mem_db,
        creator_id="UC_creator_1",
        video_id="vid_123",
        viewer_hash="hash_viewer_abc",
        source_type="comment",
        observed_at="2026-09-20T10:00:00Z",
    )
    assert count(mem_db, "interactions") == 2


def test_worker_state_persistence(mem_db):
    assert get_state(mem_db, "consecutive_failures") is None

    set_state(mem_db, "consecutive_failures", 0)
    assert get_state(mem_db, "consecutive_failures") == 0

    set_state(mem_db, "last_collect_at", "2026-09-20T12:00:00Z")
    assert get_state(mem_db, "last_collect_at") == "2026-09-20T12:00:00Z"

    set_state(mem_db, "consecutive_failures", 3)
    assert get_state(mem_db, "consecutive_failures") == 3


def test_network_edges_calculation_source_default(mem_db):
    upsert(mem_db, "network_edges", {
        "id": "edge_test",
        "creator_a": "creator_1",
        "creator_b": "creator_2",
        "shared_any": 5,
        "shared_live_chat": 3,
        "shared_comments": 2,
        "strong_shared_any": 1,
        "strong_shared_live_chat": 1,
        "strong_shared_comments": 0,
        "calculated_at": "2026-09-20T12:00:00Z",
        "calculation_source": "legacy_seed",
    })
    row = mem_db.execute("SELECT calculation_source FROM network_edges WHERE id = 'edge_test'").fetchone()
    assert row[0] == "legacy_seed"
