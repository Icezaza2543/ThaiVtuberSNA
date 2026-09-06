"""
Unit Tests for Thai VTuber Audience Network (SNA)
Tests: Privacy Hasher, First Filter, Priority & PSO, Parquet, DuckDB, SNA Graph
"""
import pytest
from pathlib import Path
from core.hasher import PrivacyHasher, hash_viewer
from core.filter_engine import FirstFilterEngine
from core.priority import (
    get_subscriber_tier, calculate_subscriber_score,
    compute_priority_score
)
from core.scheduler import BaselinePriorityQueueScheduler, PSOScheduler
from analytics.overlap_metrics import (
    jaccard_similarity, overlap_coefficient, cosine_similarity
)
from analytics.network_graph import VTuberNetworkAnalyzer


def test_privacy_hasher_consistency():
    hasher1 = PrivacyHasher("test_salt_secret")
    hasher2 = PrivacyHasher("test_salt_secret")
    raw_id = "UC1234567890_TEST_VIEWER"

    hash_a = hasher1.hash_viewer_id(raw_id)
    hash_b = hasher2.hash_viewer_id(raw_id)

    # Must be deterministic and identical
    assert hash_a == hash_b
    assert len(hash_a) == 64  # SHA-256 hex string length
    # Raw ID must not be in the hash
    assert raw_id not in hash_a
    assert hasher1.verify_hash(raw_id, hash_a) is True


def test_privacy_hasher_different_salts():
    hasher1 = PrivacyHasher("salt_a")
    hasher2 = PrivacyHasher("salt_b")
    raw_id = "UC_SAME_VIEWER"

    assert hasher1.hash_viewer_id(raw_id) != hasher2.hash_viewer_id(raw_id)


def test_first_filter_thai_vtuber():
    filter_engine = FirstFilterEngine()
    
    # Candidate 1: Real Thai VTuber
    thai_candidate = {
        "channel_id": "UC_TEST_THAI",
        "name": "Baabel ARP",
        "description": "Algorhythm Project วีทูปเบอร์ไทย สตรีมเกม",
        "handle": "@BaabelARP",
        "subscriber_count": 120000,
        "agency": "Algorhythm Project",
        "source_count": 2
    }
    status, conf, reason = filter_engine.evaluate_candidate(thai_candidate)
    assert status == "ACCEPT"
    assert conf >= 0.5

    # Candidate 2: Non-Thai Channel
    foreign_candidate = {
        "channel_id": "UC_TEST_FOREIGN",
        "name": "Global Gamer JP",
        "description": "Japanese speedruns and FPS highlights. No other languages.",
        "handle": "@GlobalGamer",
        "subscriber_count": 50000,
        "agency": "None",
        "source_count": 1
    }
    status, conf, reason = filter_engine.evaluate_candidate(foreign_candidate)
    assert status == "REJECT"
    assert conf < 0.2


def test_subscriber_tiers_and_priority():
    assert get_subscriber_tier(150000) == "S"
    assert get_subscriber_tier(60000) == "A"
    assert get_subscriber_tier(25000) == "B"
    assert get_subscriber_tier(5000) == "C"
    assert get_subscriber_tier(500) == "D"

    # Verify that larger subscriber count yields strictly higher subscriber score
    score_small = calculate_subscriber_score(500)
    score_large = calculate_subscriber_score(200000)
    assert score_large > score_small

    # Priority score check
    vtuber_large = {"subscriber_count": 200000, "last_collected": "", "streams_collected": 0}
    vtuber_small = {"subscriber_count": 1000, "last_collected": "", "streams_collected": 0}
    
    p_large = compute_priority_score(vtuber_large, is_live=True)
    p_small = compute_priority_score(vtuber_small, is_live=True)
    assert p_large > p_small


def test_schedulers_baseline_and_pso():
    streams = [
        {"vtuber_channel_id": f"ch_{i}", "video_id": f"vid_{i}", "is_live": True, "vtuber": {"subscriber_count": (i + 1) * 20000, "agency": "Test"}}
        for i in range(10)
    ]
    
    # 1. Baseline Priority Queue
    baseline = BaselinePriorityQueueScheduler(num_workers=3)
    baseline_jobs = baseline.schedule(streams)
    assert len(baseline_jobs) == 3
    # Top 3 should be channels with highest subs (ch_9, ch_8, ch_7)
    selected_ids = [j.vtuber_channel_id for j in baseline_jobs]
    assert "ch_9" in selected_ids
    assert "ch_8" in selected_ids

    # 2. PSO Scheduler
    pso = PSOScheduler(num_workers=3, swarm_size=10, max_iter=15)
    pso_jobs = pso.schedule(streams)
    assert len(pso_jobs) == 3


def test_overlap_mathematical_metrics():
    set_a = {"viewer_1", "viewer_2", "viewer_3", "viewer_4"}
    set_b = {"viewer_3", "viewer_4", "viewer_5", "viewer_6"}

    # Intersection = 2, Union = 6 -> Jaccard = 2/6 = 0.3333
    assert pytest.approx(jaccard_similarity(set_a, set_b), 0.001) == 0.3333

    # Min size = 4 -> Overlap coefficient = 2/4 = 0.5000
    assert pytest.approx(overlap_coefficient(set_a, set_b), 0.001) == 0.5000

    # Test nested subset (small indie channel completely covered by big channel)
    set_small = {"v1", "v2"}
    set_big = {"v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10"}
    # Jaccard is 2/10 = 0.20
    assert pytest.approx(jaccard_similarity(set_small, set_big), 0.001) == 0.20
    # Overlap Coefficient is 2/2 = 1.0 (100% of small channel's viewers watch big channel)
    assert pytest.approx(overlap_coefficient(set_small, set_big), 0.001) == 1.0


def test_network_graph_bridge_and_communities():
    analyzer = VTuberNetworkAnalyzer()
    vtubers = [
        {"channel_id": "A1", "name": "VTuber A1", "subscriber_count": 50000, "agency": "Group A"},
        {"channel_id": "A2", "name": "VTuber A2", "subscriber_count": 40000, "agency": "Group A"},
        {"channel_id": "BRIDGE", "name": "Bridge VTuber", "subscriber_count": 70000, "agency": "Indie"},
        {"channel_id": "B1", "name": "VTuber B1", "subscriber_count": 60000, "agency": "Group B"},
        {"channel_id": "B2", "name": "VTuber B2", "subscriber_count": 30000, "agency": "Group B"}
    ]
    overlap = [
        {"vtuber_a": "A1", "vtuber_b": "A2", "shared_viewers": 50, "jaccard": 0.5, "overlap_coefficient": 0.7},
        {"vtuber_a": "A1", "vtuber_b": "BRIDGE", "shared_viewers": 30, "jaccard": 0.3, "overlap_coefficient": 0.5},
        {"vtuber_a": "B1", "vtuber_b": "B2", "shared_viewers": 55, "jaccard": 0.6, "overlap_coefficient": 0.8},
        {"vtuber_a": "B1", "vtuber_b": "BRIDGE", "shared_viewers": 35, "jaccard": 0.35, "overlap_coefficient": 0.55}
    ]

    graph = analyzer.build_graph(vtubers, overlap)
    assert graph.number_of_nodes() == 5
    assert graph.number_of_edges() == 4

    centralities = analyzer.compute_centralities()
    top_bridges = analyzer.find_top_bridges(top_k=1)
    
    # The BRIDGE node connects Group A and Group B, so it should have highest Betweenness Centrality
    assert top_bridges[0][0] == "BRIDGE"
    assert centralities["BRIDGE"]["betweenness_centrality"] > 0
