"""Task 9 invariants for deterministic canonical registry construction."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from core.creator_catalog import CreatorCatalog
from core.creator_registry_contract import validate_registry
from scripts.build_creator_registry import build_registry, write_registry_atomic

A = "UC" + "A" * 22
B = "UC" + "B" * 22


def baseline():
    return [
        {
            "channel_id": A,
            "channel_url": f"https://www.youtube.com/channel/{A}",
            "person_id": "vtuber_alpha",
            "canonical_name": "Alpha",
            "name": "Alpha main",
            "handle": "@alpha",
            "agency": "Independent",
            "activity_status": "active",
            "subscriber_count": None,
            "video_count": 3,
            "view_count": None,
            "enabled": True,
            "checked_date": "2026-09-19T00:00:00Z",
        },
        {
            "channel_id": B,
            "channel_url": f"https://www.youtube.com/channel/{B}",
            "person_id": "vtuber_alpha",
            "canonical_name": "Alpha",
            "name": "Alpha archive",
            "handle": "@alpha_archive",
            "agency": "Independent",
            "activity_status": "hiatus",
            "subscriber_count": 7,
            "video_count": None,
            "view_count": 12,
            "enabled": True,
            "checked_date": "2026-09-19T00:00:00Z",
        },
    ]


def review():
    return {
        "schema_version": 1,
        "rows": [
            {
                "discovery_id": "accepted_x",
                "platform": "x",
                "display_name": "Alpha",
                "original_name": "alpha",
                "url": "https://x.com/alpha",
                "eligibility": "vtuber",
            },
            {
                "discovery_id": "old_duplicate",
                "platform": "youtube",
                "display_name": "Alpha main",
                "url": f"https://www.youtube.com/channel/{A}",
                "channel_id": A,
                "eligibility": "trusted_baseline",
            },
            {
                "discovery_id": "excluded",
                "platform": "x",
                "display_name": "Alpha clips",
                "url": "https://x.com/alpha_clips",
                "eligibility": "exclude_non_persona",
            },
            {
                "discovery_id": "unavailable",
                "platform": "twitch",
                "display_name": "Gone",
                "url": "https://www.twitch.tv/gone",
                "eligibility": "unavailable",
            },
        ],
    }


def resolutions():
    return {
        "schema_version": 1,
        "resolutions": [
            {
                "discovery_id": "accepted_x",
                "platform": "x",
                "platform_id": None,
                "url": "https://x.com/alpha",
                "outcome": "existing_persona",
                "persona_id": "vtuber_alpha",
                "canonical_name": "Alpha",
                "method": "official_crosslink",
                "conflict": False,
                "reviewer": "fixture",
                "evidence": [
                    {
                        "source_url": "https://x.com/alpha",
                        "source_kind": "official_profile",
                        "observed_at": "2026-09-19T00:00:00Z",
                        "summary": "Alpha's official X profile identifies the persona and account.",
                        "supports": ["account_ownership", "persona_identity"],
                    }
                ],
            }
        ],
        "unresolved": [],
        "conflicts": [],
    }


def test_build_preserves_baseline_and_accepted_accounts():
    payload = build_registry(baseline(), review(), resolutions())
    validate_registry(payload)
    youtube_ids = {row["platform_id"] for row in payload["accounts"] if row["platform"] == "youtube"}
    represented = {
        did for row in payload["accounts"] for did in row["metadata"].get("discovery_ids", [])
    }
    assert {A, B} <= youtube_ids
    assert {"accepted_x"} <= represented
    assert not {"excluded", "unavailable"} & represented


def test_baseline_rows_with_same_person_id_share_one_creator():
    payload = build_registry(baseline(), review(), resolutions())
    assert sum(row["persona_id"] == "vtuber_alpha" for row in payload["creators"]) == 1
    assert sum(row["persona_id"] == "vtuber_alpha" for row in payload["accounts"]) == 3


def test_trusted_baseline_discovery_adds_zero_accounts():
    payload = build_registry(baseline(), review(), resolutions())
    assert len(payload["accounts"]) == 3
    account = next(row for row in payload["accounts"] if row["platform_id"] == A)
    assert account["metadata"]["trusted_baseline_discovery_ids"] == ["old_duplicate"]


def test_null_metrics_remain_null():
    payload = build_registry(baseline(), review(), resolutions())
    account = next(row for row in payload["accounts"] if row["platform_id"] == A)
    assert account["metadata"]["subscriber_count"] is None
    assert account["metadata"]["view_count"] is None
    second = next(row for row in payload["accounts"] if row["platform_id"] == B)
    assert second["metadata"]["video_count"] is None


def test_build_is_byte_deterministic_across_input_order(tmp_path):
    first = build_registry(baseline(), review(), resolutions())
    shuffled_baseline = list(reversed(baseline()))
    shuffled_review = review()
    shuffled_review["rows"].reverse()
    shuffled_resolutions = resolutions()
    shuffled_resolutions["resolutions"].reverse()
    second = build_registry(shuffled_baseline, shuffled_review, shuffled_resolutions)
    one = write_registry_atomic(first, tmp_path / "one.json")
    two = write_registry_atomic(second, tmp_path / "two.json")
    assert one.read_bytes() == two.read_bytes()


def test_accepted_duplicate_account_does_not_add_account_but_keeps_discovery():
    r = review()
    r["rows"][0] = {
        "discovery_id": "accepted_existing_youtube",
        "platform": "youtube",
        "display_name": "Alpha main",
        "url": f"https://www.youtube.com/channel/{A}",
        "channel_id": A,
        "eligibility": "vtuber",
    }
    res = resolutions()
    row = res["resolutions"][0]
    row.update(
        discovery_id="accepted_existing_youtube",
        platform="youtube",
        platform_id=A,
        url=f"https://www.youtube.com/channel/{A}",
        method="exact_platform_id",
    )
    row["evidence"][0].update(source_url=f"https://www.youtube.com/channel/{A}")
    payload = build_registry(baseline(), r, res)
    assert len(payload["accounts"]) == 2
    account = next(row for row in payload["accounts"] if row["platform_id"] == A)
    assert account["metadata"]["discovery_ids"] == ["accepted_existing_youtube"]


def test_conflicting_duplicate_account_fails_closed():
    r = review()
    r["rows"][0] = {
        "discovery_id": "accepted_existing_youtube",
        "platform": "youtube",
        "display_name": "Beta impostor",
        "url": f"https://www.youtube.com/channel/{A}",
        "channel_id": A,
        "eligibility": "vtuber",
    }
    res = resolutions()
    row = res["resolutions"][0]
    row.update(
        discovery_id="accepted_existing_youtube",
        platform="youtube",
        platform_id=A,
        url=f"https://www.youtube.com/channel/{A}",
        persona_id="vtuber_beta",
        canonical_name="Beta",
        method="exact_platform_id",
    )
    row["evidence"][0].update(source_url=f"https://www.youtube.com/channel/{A}")
    with pytest.raises(ValueError, match="conflicting persona"):
        build_registry(baseline(), r, res)


def test_resolution_coverage_must_equal_final_vtuber_decisions():
    res = resolutions()
    res["resolutions"] = []
    with pytest.raises(ValueError, match="coverage mismatch"):
        build_registry(baseline(), review(), res)


def test_write_failure_preserves_original_target(tmp_path, monkeypatch):
    target = tmp_path / "creators.json"
    target.write_bytes(b"original")
    payload = build_registry(baseline(), review(), resolutions())
    original_replace = Path.replace

    def fail_replace(self, target_path):
        if self.name.endswith(".tmp"):
            raise OSError("simulated replace failure")
        return original_replace(self, target_path)

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        write_registry_atomic(payload, target)
    assert target.read_bytes() == b"original"
    assert not (tmp_path / "creators.json.tmp").exists()


def test_catalog_loads_written_registry(tmp_path):
    payload = build_registry(baseline(), review(), resolutions())
    target = write_registry_atomic(payload, tmp_path / "creators.json")
    catalog = CreatorCatalog.from_path(target)
    assert {row["platform_id"] for row in catalog.youtube_accounts()} == {A, B}
    assert catalog.account_by_url("https://x.com/alpha")["persona_id"] == "vtuber_alpha"
