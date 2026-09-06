"""
Unit tests for Real Thai VTuber Directory Adapters and YouTube Collector
"""
import pytest
from collector.thai_vtuber_ranking_adapter import ThaiVtuberRankingAdapter
from collector.fandom_thai_adapter import FandomThaiVtuberAdapter
from collector.discovery_adapter import DiscoveryAdapter
from collector.youtube_collector import YouTubeCollector


def test_thai_vtuber_ranking_adapter():
    adapter = ThaiVtuberRankingAdapter()
    candidates = adapter.fetch_candidates()
    
    assert len(candidates) > 500
    first = candidates[0]
    # Check normalized schema keys
    assert "channel_id" in first
    assert first["channel_id"].startswith("UC")
    assert "name" in first
    assert "subscriber_count" in first
    assert "source" in first
    assert first["source"] == "Thai VTuber Ranking"
    assert "source_url" in first


def test_discovery_adapter_deduplication_and_provenance():
    discovery = DiscoveryAdapter()
    
    # Mock two source inputs with overlapping channel ID
    source_1 = [
        {"channel_id": "UC_TEST_1", "name": "VTuber One", "subscriber_count": 10000, "source": "Directory A"},
        {"channel_id": "UC_TEST_2", "name": "VTuber Two", "subscriber_count": 20000, "source": "Directory A"}
    ]
    source_2 = [
        {"channel_id": "UC_TEST_1", "name": "VTuber One Updated", "subscriber_count": 12000, "source": "Directory B"},
        {"channel_id": "UC_TEST_3", "name": "VTuber Three", "subscriber_count": 5000, "source": "Directory B"}
    ]

    deduped = discovery.discover_and_deduplicate([source_1, source_2])
    assert len(deduped) == 3
    
    # Check UC_TEST_1 has source_count = 2 and updated subs = 12000
    c1 = next(c for c in deduped if c["channel_id"] == "UC_TEST_1")
    assert c1["source_count"] == 2
    assert c1["subscriber_count"] == 12000


def test_youtube_collector_output_schema_and_privacy():
    collector = YouTubeCollector()
    
    # Test with real public video from Aisha Channel (G1LXXzZx48c)
    job = {
        "video_id": "G1LXXzZx48c",
        "vtuber_channel_id": "UCqhhWjpw23dWhJ5rRwCCrMA"
    }
    
    # Fetch limited sample (max 10 comments)
    agg_events = collector.collect_aggregated_events(job, max_comments=10)
    assert len(agg_events) > 0

    first_agg = agg_events[0]
    expected_keys = {
        "viewer_hash",
        "vtuber_channel_id",
        "video_id",
        "first_seen",
        "last_seen",
        "appearances",
        "source_type"
    }
    
    # Must only contain the required keys
    assert set(first_agg.keys()) == expected_keys
    # viewer_hash must be a 64-character SHA-256 hex string
    assert len(first_agg["viewer_hash"]) == 64
    # Must NOT contain forbidden fields
    for forbidden in ["text", "comment", "message", "author", "author_thumbnail", "avatar", "emoji", "sentiment"]:
        assert forbidden not in first_agg
