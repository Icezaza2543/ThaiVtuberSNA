"""
Tests for Step 2 — Review
"""
import pytest
from pathlib import Path
from unittest.mock import patch

from thaivtubersna.store import open_db, count
from thaivtubersna.review import (
    _validate_change,
    apply_change,
    queue_status,
)


@pytest.fixture
def mem_db():
    con = open_db(Path(":memory:"))
    yield con
    con.close()


def test_validate_change_rejects_non_dict():
    with pytest.raises(ValueError, match="JSON object"):
        _validate_change(["not", "a", "dict"])


def test_validate_change_rejects_unknown_table():
    with pytest.raises(ValueError, match="Unknown tables"):
        _validate_change({"hackers_table": []})


def test_validate_change_rejects_missing_id():
    with pytest.raises(ValueError, match="every row must have an 'id' field"):
        _validate_change({"candidates": [{"name": "Foo"}]})


def test_validate_change_accepts_valid_payload():
    _validate_change({
        "candidates": [{"id": "c1", "name": "VTuber A", "platform": "twitch", "url": "https://twitch.tv/vtuber_a", "review_status": "needs_evidence", "evidence_id": "e1"}],
        "evidence": [{"id": "e1", "url": "https://twitch.tv/vtuber_a", "kind": "first_party_profile", "observed_at": "2026-09-20T00:00:00Z", "summary": "bio"}],
    })


def test_apply_change_dry_run_does_not_commit(mem_db):
    change = {
        "evidence": [{
            "id": "evi_test_1",
            "url": "https://twitch.tv/test_vtuber",
            "kind": "first_party_profile",
            "observed_at": "2026-09-20T00:00:00Z",
            "summary": "bio test",
        }]
    }
    result = apply_change(mem_db, change, dry_run=True)
    assert result["ok"] is True
    assert result["counts"]["added"] == 1
    assert count(mem_db, "evidence") == 0  # not committed


def test_apply_change_writes_records(mem_db):
    change = {
        "evidence": [{
            "id": "evi_test_2",
            "url": "https://youtube.com/@test_vtuber",
            "kind": "first_party_profile",
            "observed_at": "2026-09-20T00:00:00Z",
            "summary": "channel about",
        }]
    }
    result = apply_change(mem_db, change, dry_run=False)
    assert result["ok"] is True
    assert result["counts"]["added"] == 1
    assert count(mem_db, "evidence") == 1


def test_apply_change_idempotent(mem_db):
    change = {
        "evidence": [{
            "id": "evi_test_3",
            "url": "https://youtube.com/@test_vtuber3",
            "kind": "first_party_profile",
            "observed_at": "2026-09-20T00:00:00Z",
            "summary": "channel about",
        }]
    }
    apply_change(mem_db, change, dry_run=False)
    assert count(mem_db, "evidence") == 1

    # Apply same change again
    res2 = apply_change(mem_db, change, dry_run=False)
    assert res2["counts"]["unchanged"] == 1
    assert res2["counts"]["added"] == 0
    assert count(mem_db, "evidence") == 1


def test_queue_status_returns_dict(mem_db):
    status = queue_status(mem_db)
    assert "candidates" in status
    assert "review_queue_open" in status
    assert "verified_personas" in status
