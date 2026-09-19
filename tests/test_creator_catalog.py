import hashlib
from pathlib import Path

from core.creator_catalog import CreatorCatalog


FIXTURE = Path(__file__).parent / "fixtures" / "creator_registry" / "baseline.json"


def test_valid_registry_indexes_personas_accounts_and_youtube():
    catalog = CreatorCatalog.from_path(FIXTURE)
    assert catalog.creator("vtuber_alpha")["canonical_name"] == "Alpha"
    assert catalog.account_by_platform_id("youtube", "UC" + "A" * 22)["persona_id"] == "vtuber_alpha"
    assert [row["channel_id"] for row in catalog.youtube_rows()] == ["UC" + "A" * 22]


def test_catalog_returns_defensive_views_and_deterministic_legacy_rows():
    catalog = CreatorCatalog.from_path(FIXTURE)
    creator = catalog.creator("vtuber_alpha")
    creator["canonical_name"] = "Mutated"
    account = catalog.youtube_accounts()[0]
    account["metadata"]["subscriber_count"] = 0
    assert catalog.creator("vtuber_alpha")["canonical_name"] == "Alpha"
    assert catalog.youtube_rows()[0] == {
        "channel_id": "UC" + "A" * 22,
        "name": "Alpha Channel",
        "handle": "@alpha",
        "channel_url": "https://www.youtube.com/channel/UC" + "A" * 22,
        "agency": "Independent",
        "activity_status": "active",
        "vtuber_status": "CONFIRMED",
        "person_id": "vtuber_alpha",
        "canonical_name": "Alpha",
        "channel_type": "main",
        "subscriber_count": 42,
        "video_count": 3,
        "view_count": 100,
        "last_video_published_at": None,
        "country": None,
        "thai_confidence": 0.9,
        "reference_sources": None,
        "checked_date": None,
        "evidence_notes": None,
        "enabled": True,
    }


def test_catalog_fingerprint_hashes_exact_source_bytes():
    assert CreatorCatalog.from_path(FIXTURE).source_fingerprint() == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
