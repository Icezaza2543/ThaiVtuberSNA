"""Production gates for Task 8 Twitch identity resolution."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence" / "creator-registry-review-2026-09-19"
TWITCH_RESEARCH = EVIDENCE / "identity_research_twitch.json"
REVIEW_BUNDLE = EVIDENCE / "review_bundle.json"
LEDGER = ROOT / "data" / "registry" / "identity_resolutions.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_twitch_production_batch_covers_exactly_150_accepted_accounts():
    review = _load(REVIEW_BUNDLE)
    research = _load(TWITCH_RESEARCH)
    ledger = _load(LEDGER)

    selected = {
        row["discovery_id"]: row
        for row in review["rows"]
        if row.get("eligibility") == "vtuber" and row.get("platform") == "twitch"
    }
    assert len(selected) == 150
    assert len(research["rows"]) == 150
    assert {row["discovery_id"] for row in research["rows"]} == set(selected)
    assert research["required_trusted_link_corrections"] == review["required_trusted_link_corrections"]

    resolved = {row["discovery_id"]: row for row in ledger["resolutions"]}
    assert set(selected) <= set(resolved)
    assert not ledger["unresolved"]
    assert not ledger["conflicts"]

    for row in research["rows"]:
        did = row["discovery_id"]
        assert row["reviewer"] == "chatgpt:task-8-twitch-identity-research"
        assert selected[did]["url"] in row["official_account_urls"]
        assert row["evidence"]
        assert all(
            evidence["source_kind"] in {"official_profile", "official_website", "self_statement", "youtube_api"}
            for evidence in row["evidence"]
        )
        if row.get("no_existing_persona_match"):
            search = row["existing_persona_search"]
            assert search["corpora"]
            assert search["official_urls_checked"]
            assert search["result"]
        else:
            # Existing identity may be supplied by a trusted exact account claim;
            # cross-discovery joins must otherwise retain an explicit assertion.
            assert row["assertions"] or resolved[did]["method"] in {
                "exact_platform_id",
                "verified_registry_link",
            }
        assert resolved[did]["platform"] == "twitch"


def test_complete_ledger_seals_corrected_392_account_scope():
    review = _load(REVIEW_BUNDLE)
    ledger = _load(LEDGER)

    assert review["eligibility_counts"]["vtuber"] == 392
    assert ledger["counts"]["accepted"] == 392
    assert ledger["counts"]["resolved"] == 392
    assert ledger["counts"]["unresolved"] == 0
    assert ledger["counts"]["conflicts"] == 0
    assert ledger["counts"]["by_platform"] == {
        "facebook": 6,
        "ganknow": 3,
        "instagram": 7,
        "tiktok": 58,
        "twitch": 150,
        "website": 17,
        "x": 126,
        "youtube": 25,
    }
    assert len({row["discovery_id"] for row in ledger["resolutions"]}) == 392


def test_drako_twitch_joins_verified_drako_persona_not_amilly():
    review = _load(REVIEW_BUNDLE)
    ledger = _load(LEDGER)

    drako = next(
        row
        for row in review["rows"]
        if row.get("eligibility") == "vtuber"
        and row.get("platform") == "twitch"
        and row.get("url", "").rstrip("/").casefold() == "https://www.twitch.tv/drakonyamio"
    )
    resolved = next(row for row in ledger["resolutions"] if row["discovery_id"] == drako["discovery_id"])
    assert resolved["persona_id"] == "vtuber_drakonyamio"
    assert resolved["persona_id"] != "persona_6e9e31346f7b9164ce4b"
