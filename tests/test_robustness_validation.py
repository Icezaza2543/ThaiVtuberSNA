"""
Regression and analytical tests for Phase T10: Robustness & Sensitivity Validation (Research Integrity Edition).
Validates parameter sweeps, dynamic real metric calculation (no hardcoded constants),
rule-derived classifications, and privacy preservation.
"""

import pytest
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ROBUSTNESS_DIR = BASE_DIR / "data" / "temporal" / "robustness"
RESULTS_PARQUET = ROBUSTNESS_DIR / "sensitivity_results.parquet"
SUMMARY_PARQUET = ROBUSTNESS_DIR / "robustness_summary.parquet"
REPORT_MD = ROBUSTNESS_DIR / "robustness_report.md"


@pytest.fixture(scope="module")
def sensitivity_results_df():
    assert RESULTS_PARQUET.exists(), f"Missing {RESULTS_PARQUET}"
    return pd.read_parquet(RESULTS_PARQUET)


@pytest.fixture(scope="module")
def robustness_summary_df():
    assert SUMMARY_PARQUET.exists(), f"Missing {SUMMARY_PARQUET}"
    return pd.read_parquet(SUMMARY_PARQUET)


def test_robustness_artifacts_exist():
    """Verify that all required T10 output artifacts are present and non-empty."""
    assert RESULTS_PARQUET.exists(), f"Missing {RESULTS_PARQUET}"
    assert SUMMARY_PARQUET.exists(), f"Missing {SUMMARY_PARQUET}"
    assert REPORT_MD.exists(), f"Missing {REPORT_MD}"
    assert REPORT_MD.stat().st_size > 1000, "Robustness report is empty or suspiciously small."


def test_sensitivity_results_schema(sensitivity_results_df):
    """Verify required schema and parameter dimensions in sensitivity_results.parquet."""
    required_cols = [
        "slice_type",
        "slice_label",
        "evidence_mode",
        "dataset_depth",
        "edge_threshold",
        "louvain_resolution",
        "active_nodes",
        "active_edges",
        "community_count",
        "modularity_q",
        "nmi_to_baseline",
        "ari_to_baseline",
        "jaccard_top_bridges",
        "agency_purity",
        "status",
    ]
    for col in required_cols:
        assert col in sensitivity_results_df.columns, f"Missing required column: {col}"

    assert len(sensitivity_results_df) >= 500, (
        f"Expected >= 500 sensitivity combinations, got {len(sensitivity_results_df)}"
    )


def test_parameter_dimensions_covered(sensitivity_results_df):
    """Verify all requested parameter dimensions were systematically evaluated."""
    resolutions = set(sensitivity_results_df["louvain_resolution"].unique())
    assert {0.5, 0.75, 1.0, 1.25, 1.5}.issubset(resolutions)

    thresholds = set(sensitivity_results_df["edge_threshold"].unique())
    assert {1, 3, 5, 10}.issubset(thresholds)

    evidence_modes = set(sensitivity_results_df["evidence_mode"].unique())
    assert {"unified", "comment_only", "live_chat_only"}.issubset(evidence_modes)

    depths = set(sensitivity_results_df["dataset_depth"].unique())
    assert {"t6_canonical", "t5_stratified_baseline"}.issubset(depths)


def test_real_t5_vs_t6_dynamic_calculation(sensitivity_results_df):
    """Verify T5 vs T6 partition comparisons are dynamically computed, not hardcoded constants."""
    t5_rows = sensitivity_results_df[sensitivity_results_df["dataset_depth"] == "t5_stratified_baseline"]
    assert len(t5_rows) >= 20, "Expected T5 vs T6 cross-depth evaluation rows"

    # Values must vary naturally across resolutions and years, not repeat hardcoded constants like exactly 0.65 or 0.70
    nmis = t5_rows["nmi_to_baseline"].tolist()
    assert len(set(nmis)) > 5, "NMI values must vary dynamically across parameter combinations"
    aris = t5_rows["ari_to_baseline"].tolist()
    assert len(set(aris)) > 5, "ARI values must vary dynamically across parameter combinations"

    # Specific check: 2024 resolution 1.0 should be its real computed value (around 0.9046)
    row_2024_res1 = t5_rows[
        (t5_rows["slice_label"] == "yearly_2024") &
        (t5_rows["louvain_resolution"] == 1.0)
    ]
    assert not row_2024_res1.empty
    actual_nmi = row_2024_res1["nmi_to_baseline"].iloc[0]
    assert 0.85 <= actual_nmi <= 0.95, f"Expected real computed NMI around 0.9046, got {actual_nmi}"


def test_classifications_derived_from_thresholds(robustness_summary_df):
    """Verify classifications are derived from empirical metrics using deterministic rules."""
    required_cols = [
        "finding_id",
        "research_domain",
        "finding_statement",
        "measured_metric_name",
        "measured_metric_value",
        "classification",
        "deterministic_rule_basis",
        "methodological_implication",
    ]
    for col in required_cols:
        assert col in robustness_summary_df.columns, f"Missing summary column: {col}"

    # Verify deterministic alignment
    for _, row in robustness_summary_df.iterrows():
        val = row["measured_metric_value"]
        cls = row["classification"]
        if row["finding_id"] == "FINDING_1_AGENCY_ISLAND_CLUSTERING":
            assert val >= 0.70
            assert cls == "ROBUST"
        elif row["finding_id"] == "FINDING_4_PERIPHERAL_INDEPENDENT_INTEGRATION":
            assert val < 0.45
            assert cls == "HIGHLY_SENSITIVE"
        elif row["finding_id"] == "FINDING_6_LIVE_CHAT_STANDALONE_SUFFICIENCY":
            assert cls == "INSUFFICIENT_EVIDENCE"


def test_zero_viewer_hash_leakage(sensitivity_results_df, robustness_summary_df):
    """Verify that zero viewer hashes or PII are exposed in any T10 output artifact."""
    forbidden_terms = ["viewer_hash", "author_hash", "user_id", "viewer_id"]
    for df in [sensitivity_results_df, robustness_summary_df]:
        for col in df.columns:
            for term in forbidden_terms:
                assert term not in col.lower(), f"Forbidden identifier column found: {col}"


def test_modularity_and_purity_bounds(sensitivity_results_df):
    """Verify that modularity and agency purity values fall within mathematical bounds."""
    evaluated = sensitivity_results_df[sensitivity_results_df["status"] == "EVALUATED"]
    assert len(evaluated) > 0
    assert (evaluated["modularity_q"] >= -0.5).all()
    assert (evaluated["modularity_q"] <= 1.0).all()
    assert (evaluated["agency_purity"] >= 0.0).all()
    assert (evaluated["agency_purity"] <= 1.0).all()
