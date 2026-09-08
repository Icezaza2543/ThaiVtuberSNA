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
        "STABLE_BRIDGE", "EMERGING_BRIDGE", "DECLINING_BRIDGE",
        "VOLATILE", "INSUFFICIENT_EVIDENCE", "MODERATE_PERIPHERAL"
    }
    assert set(bridge_dynamics_df["bridge_classification"]).issubset(valid_classes)

    # Stable bridges must have years_in_top_decile >= 3
    stable = bridge_dynamics_df[bridge_dynamics_df["bridge_classification"] == "STABLE_BRIDGE"]
    for _, r in stable.iterrows():
        assert r["years_in_top_decile_count"] >= 3
        assert r["last_observed_year"] == 2026

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
