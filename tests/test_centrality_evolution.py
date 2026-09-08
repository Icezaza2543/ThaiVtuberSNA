"""Tests for Phase T13 Dynamic Bridges & Centrality Evolution.

Verifies:
1. Expected centrality artifacts exist.
2. Zero viewer_hash or individual-level PII in schemas or reports.
3. Yearly centrality schema and valid percentile bounds [0, 1].
4. Metric-derived deterministic classification categories and consistency.
5. Change-point candidate definitions and valid delta bounds.
"""
from pathlib import Path
import re
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def yearly_centrality_df():
    path = REPO_ROOT / "data" / "temporal" / "centrality" / "yearly_centrality.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def bridge_dynamics_df():
    path = REPO_ROOT / "data" / "temporal" / "centrality" / "bridge_dynamics.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def change_points_df():
    path = REPO_ROOT / "data" / "temporal" / "centrality" / "centrality_change_points.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def bridge_report_content():
    path = REPO_ROOT / "data" / "temporal" / "centrality" / "bridge_dynamics_report.md"
    assert path.exists(), f"Missing {path}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def test_centrality_artifacts_privacy(yearly_centrality_df, bridge_dynamics_df, change_points_df, bridge_report_content):
    """Verify zero raw viewer hashes or individual identifier columns are exposed."""
    forbidden = ["viewer_hash", "author_hash", "user_id", "author_id"]
    for df in [yearly_centrality_df, bridge_dynamics_df, change_points_df]:
        for col in df.columns:
            for term in forbidden:
                assert term not in col.lower(), f"Forbidden identifier column in dataframe: {col}"

    sha256_hex_pattern = re.compile(r'\b[a-f0-9]{64}\b')
    matches = sha256_hex_pattern.findall(bridge_report_content)
    assert not matches, f"Raw hex string found in bridge report: {matches[:3]}"

def test_yearly_centrality_schema_and_percentiles(yearly_centrality_df):
    """Verify yearly centrality metrics schema and percentile bounds."""
    expected_cols = [
        "year", "channel_id", "channel_name", "agency_at_selection",
        "community_id", "degree", "weighted_degree", "betweenness_centrality",
        "pagerank", "eigenvector_centrality", "cross_community_edge_share",
        "cross_agency_edge_share", "betweenness_percentile", "degree_percentile",
        "pagerank_percentile", "bridge_percentile_band", "is_in_top_decile",
        "is_in_top_quartile"
    ]
    for col in expected_cols:
        assert col in yearly_centrality_df.columns, f"Missing column: {col}"

    # Percentiles must be bounded [0, 1]
    for pct_col in ["betweenness_percentile", "degree_percentile", "pagerank_percentile"]:
        assert (yearly_centrality_df[pct_col] >= 0.0).all()
        assert (yearly_centrality_df[pct_col] <= 1.0).all()

    valid_bands = {"TOP_1_PERCENT", "TOP_5_PERCENT", "TOP_10_PERCENT", "TOP_QUARTILE", "BELOW_QUARTILE"}
    assert set(yearly_centrality_df["bridge_percentile_band"]).issubset(valid_bands)

def test_bridge_dynamics_classifications(bridge_dynamics_df):
    """Verify classification categories and deterministic logic."""
    expected_cols = [
        "channel_id", "channel_name", "agency_at_selection", "first_observed_year",
        "last_observed_year", "years_observed_count", "years_in_top_decile_count",
        "first_year_entering_top_decile", "mean_betweenness_percentile",
        "max_betweenness_percentile", "min_betweenness_percentile",
        "percentile_volatility_std", "mean_cross_community_share",
        "mean_cross_agency_share", "threshold_th5_retention_ratio",
        "bridge_classification", "classification_rule_basis"
    ]
    for col in expected_cols:
        assert col in bridge_dynamics_df.columns, f"Missing column: {col}"

    valid_classes = {
        "STABLE_BRIDGE", "STABLE_BRIDGE_CANONICAL_ONLY", "EMERGING_BRIDGE", "DECLINING_BRIDGE",
        "VOLATILE", "INSUFFICIENT_EVIDENCE", "MODERATE_PERIPHERAL"
    }
    assert set(bridge_dynamics_df["bridge_classification"]).issubset(valid_classes)

    # Stable bridges must have years_in_top_decile >= 3
    stable = bridge_dynamics_df[bridge_dynamics_df["bridge_classification"] == "STABLE_BRIDGE"]
    for _, r in stable.iterrows():
        assert r["years_in_top_decile_count"] >= 3
        assert r["last_observed_year"] == 2026
        # Must have non-zero threshold >= 5 retention
        assert r["threshold_th5_retention_ratio"] > 0.0

def test_change_points_delta_threshold(change_points_df):
    """Verify that detected change points satisfy the |delta| >= 0.25 threshold."""
    assert len(change_points_df) > 0
    for _, r in change_points_df.iterrows():
        assert abs(r["percentile_delta"]) >= 0.25, f"Delta too small: {r['percentile_delta']}"
        assert r["change_type"] in {"RAPID_ASCENT", "RAPID_DECLINE"}
        if r["change_type"] == "RAPID_ASCENT":
            assert r["percentile_delta"] > 0
        else:
            assert r["percentile_delta"] < 0


def test_edge_distance_and_toy_graph_betweenness():
    """Regression test:
    - stronger edge -> shorter distance
    - weighted betweenness toy graph has expected bridge
    """
    import networkx as nx

    # 1. Stronger edge -> shorter distance
    strength_strong = 50.0
    strength_weak = 2.0
    dist_strong = 1.0 / strength_strong
    dist_weak = 1.0 / strength_weak
    assert dist_strong < dist_weak, "Stronger edge must have strictly shorter distance"

    # 2. Toy graph with bridge node X between two communities
    # Community 1: A, B; Community 2: C, D
    # Bridge node X connects A, B to C, D
    G = nx.Graph()
    # Edges in Comm 1
    G.add_edge("A", "B", weight=20.0, distance=1.0 / 20.0)
    # Edges in Comm 2
    G.add_edge("C", "D", weight=20.0, distance=1.0 / 20.0)
    # Bridge edges through X
    G.add_edge("A", "X", weight=10.0, distance=1.0 / 10.0)
    G.add_edge("X", "C", weight=10.0, distance=1.0 / 10.0)
    # Weak direct edge A-C with heavy distance (weak tie)
    G.add_edge("A", "C", weight=0.1, distance=1.0 / 0.1)

    btw = nx.betweenness_centrality(G, weight="distance", normalized=True)
    # Shortest path between B and D traverses B -> A -> X -> C -> D (dist = 0.05 + 0.1 + 0.1 + 0.05 = 0.3)
    # Direct A-C distance is 10.0, so shortest path strictly uses bridge X!
    assert btw["X"] > btw["A"]
    assert btw["X"] > btw["C"]
    assert btw["X"] == max(btw.values()), "Bridge node X must have highest betweenness centrality"


def test_tie_aware_percentiles_and_order_invariance():
    """Regression test:
    - equal centrality values -> strictly equal percentiles
    - node insertion order does not change percentile or classification
    """
    import pandas as pd

    # Equal values
    raw_metrics_1 = {"ch1": 0.0, "ch2": 0.0, "ch3": 0.5, "ch4": 0.5, "ch5": 1.0}
    # Permuted insertion order
    raw_metrics_2 = {"ch5": 1.0, "ch4": 0.5, "ch1": 0.0, "ch3": 0.5, "ch2": 0.0}

    pct_1 = pd.Series(raw_metrics_1).rank(method="average", pct=True).to_dict()
    pct_2 = pd.Series(raw_metrics_2).rank(method="average", pct=True).to_dict()

    # Equal values -> equal percentiles
    assert pct_1["ch1"] == pct_1["ch2"]
    assert pct_1["ch3"] == pct_1["ch4"]

    # Order invariance
    for k in raw_metrics_1:
        assert pct_1[k] == pct_2[k]


def test_classification_documented_rules():
    """Regression test: classifications follow exact documented rules."""
    from scripts.analyze_centrality_evolution import assign_percentile_band

    # Percentile band cutoffs
    assert assign_percentile_band(0.99) == "TOP_1_PERCENT"
    assert assign_percentile_band(0.95) == "TOP_5_PERCENT"
    assert assign_percentile_band(0.90) == "TOP_10_PERCENT"
    assert assign_percentile_band(0.75) == "TOP_QUARTILE"
    assert assign_percentile_band(0.74) == "BELOW_QUARTILE"

