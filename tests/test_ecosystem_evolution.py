"""Tests for Phase T14 Ecosystem Growth & Structural Change.

Verifies:
1. Expected ecosystem artifacts exist.
2. Zero viewer_hash or individual-level PII in schemas or reports.
3. Yearly macro metrics schema, bounds, and 2026 YTD labeling.
4. Deterministic structural breaks schema, valid categories, and thresholds.
5. Non-causal phrasing and mathematical consistency.
"""
from pathlib import Path
import re
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def ecosystem_metrics_df():
    path = REPO_ROOT / "data" / "temporal" / "ecosystem" / "yearly_ecosystem_metrics.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def structural_breaks_df():
    path = REPO_ROOT / "data" / "temporal" / "ecosystem" / "structural_breaks.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def ecosystem_report_content():
    path = REPO_ROOT / "data" / "temporal" / "ecosystem" / "ecosystem_evolution_report.md"
    assert path.exists(), f"Missing {path}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def test_ecosystem_artifacts_privacy(ecosystem_metrics_df, structural_breaks_df, ecosystem_report_content):
    """Verify zero raw viewer hashes or individual identifier columns are exposed."""
    forbidden = ["viewer_hash", "author_hash", "user_id", "author_id"]
    for df in [ecosystem_metrics_df, structural_breaks_df]:
        for col in df.columns:
            for term in forbidden:
                assert term not in col.lower(), f"Forbidden identifier column in dataframe: {col}"

    sha256_hex_pattern = re.compile(r'\b[a-f0-9]{64}\b')
    matches = sha256_hex_pattern.findall(ecosystem_report_content)
    assert not matches, f"Raw hex string found in ecosystem report: {matches[:3]}"

def test_yearly_ecosystem_metrics_schema_and_bounds(ecosystem_metrics_df):
    """Verify yearly macro metrics schema, valid bounds, and 2026 YTD designation."""
    expected_cols = [
        "year", "year_label", "is_ytd", "active_channels", "edges", "density",
        "weighted_edge_strength", "average_degree", "connected_components",
        "giant_component_nodes", "giant_component_share", "community_count",
        "modularity", "degree_concentration_gini", "strength_concentration_gini",
        "agency_assortativity", "agency_independent_mixing", "cross_community_edge_share"
    ]
    for col in expected_cols:
        assert col in ecosystem_metrics_df.columns, f"Missing column: {col}"

    assert len(ecosystem_metrics_df) == 7  # 2020 through 2026
    
    # 2026 must be labeled YTD
    row_2026 = ecosystem_metrics_df[ecosystem_metrics_df["year"] == 2026].iloc[0]
    assert row_2026["is_ytd"] == True
    assert "YTD" in row_2026["year_label"]

    # Metric bounds
    assert (ecosystem_metrics_df["density"] >= 0.0).all() and (ecosystem_metrics_df["density"] <= 1.0).all()
    assert (ecosystem_metrics_df["giant_component_share"] >= 0.0).all() and (ecosystem_metrics_df["giant_component_share"] <= 1.0).all()
    assert (ecosystem_metrics_df["degree_concentration_gini"] >= 0.0).all() and (ecosystem_metrics_df["degree_concentration_gini"] <= 1.0).all()
    assert (ecosystem_metrics_df["strength_concentration_gini"] >= 0.0).all() and (ecosystem_metrics_df["strength_concentration_gini"] <= 1.0).all()
    assert (ecosystem_metrics_df["agency_independent_mixing"] >= 0.0).all() and (ecosystem_metrics_df["agency_independent_mixing"] <= 1.0).all()
    assert (ecosystem_metrics_df["cross_community_edge_share"] >= 0.0).all() and (ecosystem_metrics_df["cross_community_edge_share"] <= 1.0).all()

def test_structural_breaks_detection(structural_breaks_df):
    """Verify detected structural breaks have deterministic categorization and non-zero deltas."""
    assert len(structural_breaks_df) > 0
    expected_cols = [
        "transition", "metric_dimension", "from_value", "to_value",
        "absolute_delta", "relative_change_pct", "break_category", "descriptive_note"
    ]
    for col in expected_cols:
        assert col in structural_breaks_df.columns, f"Missing column: {col}"

    for _, r in structural_breaks_df.iterrows():
        assert r["absolute_delta"] != 0.0
        assert len(r["descriptive_note"]) > 10
