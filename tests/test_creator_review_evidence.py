import json
from pathlib import Path

import pytest

from scripts.package_creator_review_evidence import package_review_evidence


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture
def review_inputs(tmp_path):
    screening = write_json(
        tmp_path / "screening.json",
        {
            "rows": [
                {
                    "discovery_id": "automated-vtuber",
                    "platform": "youtube",
                    "name": "Automated VTuber",
                    "original_name": "automated",
                    "url": "https://example.test/automated",
                    "channel_id": "UCautomated",
                    "decision": "VTUBER",
                    "reason": "automated evidence",
                    "evidence_urls": ["https://example.test/automated/about"],
                    "raw_review_file": "C:\\Users\\example\\private-cache.json",
                },
                {
                    "discovery_id": "human-vtuber",
                    "platform": "youtube",
                    "name": "Human VTuber",
                    "original_name": "human",
                    "url": "https://example.test/human",
                    "channel_id": "UChuman",
                    "decision": "UNRESOLVED",
                    "reason": "needs human review",
                    "evidence_urls": ["https://example.test/human/about"],
                },
                {
                    "discovery_id": "trusted-baseline",
                    "platform": "youtube",
                    "name": "Trusted Baseline",
                    "original_name": "trusted",
                    "url": "https://example.test/trusted",
                    "channel_id": "UCtrusted",
                    "decision": "TRUSTED_BASELINE",
                    "reason": "trusted",
                    "evidence_urls": [],
                },
                {
                    "discovery_id": "excluded",
                    "platform": "youtube",
                    "name": "Excluded",
                    "original_name": "excluded",
                    "url": "https://example.test/excluded",
                    "channel_id": "UCexcluded",
                    "decision": "NON_VTUBER",
                    "reason": "not a persona",
                    "evidence_urls": [],
                },
                {
                    "discovery_id": "human-unrelated",
                    "platform": "youtube",
                    "name": "Unrelated",
                    "original_name": "unrelated",
                    "url": "https://example.test/unrelated",
                    "channel_id": "UCunrelated",
                    "decision": "UNRESOLVED",
                    "reason": "needs human review",
                    "evidence_urls": [],
                },
                {
                    "discovery_id": "human-unavailable",
                    "platform": "youtube",
                    "name": "Unavailable",
                    "original_name": "unavailable",
                    "url": "https://example.test/unavailable",
                    "channel_id": "UCunavailable",
                    "decision": "UNRESOLVED",
                    "reason": "needs human review",
                    "evidence_urls": [],
                },
            ]
        },
    )
    human = write_json(
        tmp_path / "human.json",
        {
            "decisions": ["human-vtuber", "human-unrelated", "human-unavailable"],
            "history": [
                {"discovery_id": "human-vtuber", "decision": "vtuber", "reviewed_at": "2026-09-19T00:00:00Z"},
                {"discovery_id": "human-unrelated", "decision": "unrelated", "reviewed_at": "2026-09-19T00:01:00Z"},
                {"discovery_id": "human-unavailable", "decision": "unavailable", "reviewed_at": "2026-09-19T00:02:00Z"},
            ],
        },
    )
    return screening, human


def test_final_human_decision_overrides_unresolved_and_paths_are_sanitized(review_inputs):
    screening, human = review_inputs
    bundle = package_review_evidence(screening, human)

    rows = {row["discovery_id"]: row for row in bundle["rows"]}
    assert rows["human-vtuber"]["eligibility"] == "vtuber"
    assert rows["human-unrelated"]["eligibility"] == "exclude_unrelated"
    assert rows["human-unavailable"]["eligibility"] == "unavailable"
    assert "raw_review_file" not in json.dumps(bundle)
    assert "C:\\Users\\" not in json.dumps(bundle)


def test_excluded_legacy_new_persona_cannot_reenter_catalog(review_inputs):
    screening, human = review_inputs
    payload = json.loads(screening.read_text(encoding="utf-8"))
    excluded = next(row for row in payload["rows"] if row["discovery_id"] == "excluded")
    excluded["legacy_identity_decision"] = "new_persona"
    write_json(screening, payload)

    bundle = package_review_evidence(screening, human)

    row = next(row for row in bundle["rows"] if row["discovery_id"] == "excluded")
    assert row["eligibility"].startswith("exclude_")


def test_rejects_human_decision_for_non_unresolved_row(review_inputs, tmp_path):
    screening, _ = review_inputs
    human = write_json(
        tmp_path / "invalid-human.json",
        {
            "decisions": ["automated-vtuber"],
            "history": [{"discovery_id": "automated-vtuber", "decision": "vtuber", "reviewed_at": "2026-09-19T00:00:00Z"}],
        },
    )

    with pytest.raises(ValueError, match="non-UNRESOLVED"):
        package_review_evidence(screening, human)
