import copy
import json
from pathlib import Path

import pytest

from core.creator_registry_contract import (
    stable_account_id,
    stable_persona_id,
    validate_registry,
)


FIXTURE = Path(__file__).parent / "fixtures" / "creator_registry" / "baseline.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def mutate_fixture(payload, mutation):
    result = copy.deepcopy(payload)
    if mutation == "duplicate_account":
        duplicate = copy.deepcopy(result["accounts"][0])
        duplicate["account_id"] = "account_duplicate"
        result["accounts"].append(duplicate)
        result["counts"]["accounts"] += 1
        result["evidence"][1]["subject_ids"].append("account_duplicate")
    elif mutation == "missing_persona":
        result["accounts"][0]["persona_id"] = "not_a_creator"
    elif mutation == "two_personas":
        duplicate = copy.deepcopy(result["accounts"][0])
        duplicate["account_id"] = "account_conflict"
        duplicate["persona_id"] = "vtuber_beta"
        result["creators"].append({**result["creators"][0], "persona_id": "vtuber_beta", "canonical_name": "Beta"})
        result["accounts"].append(duplicate)
        result["counts"]["creators"] += 1
        result["counts"]["accounts"] += 1
        result["evidence"][0]["subject_ids"].append("vtuber_beta")
        result["evidence"][1]["subject_ids"].append("account_conflict")
    elif mutation == "missing_evidence":
        result["accounts"][0]["evidence_ids"] = []
    elif mutation == "bad_youtube_id":
        result["accounts"][0]["platform_id"] = "not-a-channel"
    return result


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("duplicate_account", "duplicate account"),
        ("missing_persona", "unknown persona"),
        ("two_personas", "conflicting persona"),
        ("missing_evidence", "evidence"),
        ("bad_youtube_id", "Channel ID"),
    ],
)
def test_invalid_registry_fails_closed(mutation, message):
    with pytest.raises(ValueError, match=message):
        validate_registry(mutate_fixture(load_fixture(), mutation))


def test_same_handle_on_different_platforms_is_not_an_identity_conflict():
    payload = load_fixture()
    beta = copy.deepcopy(payload["creators"][0])
    beta["persona_id"] = "vtuber_beta"
    beta["canonical_name"] = "Beta"
    beta["evidence_ids"] = ["evidence_persona_beta"]
    payload["creators"].append(beta)
    payload["accounts"][0]["platform"] = "twitch"
    payload["accounts"][0]["platform_id"] = "alpha"
    payload["accounts"][0]["url"] = "https://twitch.tv/alpha"
    second = copy.deepcopy(payload["accounts"][0])
    second.update({"account_id": "account_beta_x", "persona_id": "vtuber_beta", "platform": "x", "url": "https://x.com/alpha"})
    payload["accounts"].append(second)
    payload["evidence"].append({**payload["evidence"][0], "evidence_id": "evidence_persona_beta", "subject_ids": ["vtuber_beta"]})
    payload["evidence"].append({**payload["evidence"][1], "evidence_id": "evidence_account_beta", "subject_ids": ["account_beta_x"]})
    second["evidence_ids"] = ["evidence_account_beta"]
    payload["counts"] = {"creators": 2, "accounts": 2, "evidence": 4}
    validate_registry(payload)


def test_aliases_normalize_before_stable_account_identity():
    assert stable_account_id("twitter", "123", "https://example.invalid") == stable_account_id("x", "123", "https://elsewhere.invalid")
    assert stable_account_id("carrd", None, "HTTPS://Example.com/path/") == stable_account_id("website", None, "https://example.com/path")


def test_stable_persona_id_is_deterministic_and_not_seed_text():
    assert stable_persona_id("Alpha official persona") == stable_persona_id("Alpha official persona")
    assert stable_persona_id("Alpha official persona") != stable_persona_id("Beta official persona")


@pytest.mark.parametrize("field", ["creators", "accounts", "evidence"])
def test_count_mismatch_fails_closed(field):
    payload = load_fixture()
    payload["counts"][field] += 1
    with pytest.raises(ValueError, match="count"):
        validate_registry(payload)


def test_unsupported_platform_and_non_vtuber_creator_fail_closed():
    payload = load_fixture()
    payload["accounts"][0]["platform"] = "mastodon"
    with pytest.raises(ValueError, match="unsupported platform"):
        validate_registry(payload)
    payload = load_fixture()
    payload["creators"][0]["eligibility"] = "organization"
    with pytest.raises(ValueError, match="eligibility"):
        validate_registry(payload)


def test_orphaned_creator_and_evidence_fail_closed():
    payload = load_fixture()
    orphan = copy.deepcopy(payload["creators"][0])
    orphan.update({"persona_id": "vtuber_orphan", "canonical_name": "Orphan", "evidence_ids": ["evidence_orphan"]})
    payload["creators"].append(orphan)
    payload["evidence"].append({**payload["evidence"][0], "evidence_id": "evidence_orphan", "subject_ids": ["vtuber_orphan"]})
    payload["counts"] = {"creators": 2, "accounts": 1, "evidence": 3}
    with pytest.raises(ValueError, match="requires an account"):
        validate_registry(payload)

    payload = load_fixture()
    payload["evidence"].append({**payload["evidence"][0], "evidence_id": "evidence_unused"})
    payload["counts"]["evidence"] += 1
    with pytest.raises(ValueError, match="orphan evidence"):
        validate_registry(payload)
