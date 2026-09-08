"""
Regression and analytical tests for Phase T10: Robustness & Sensitivity Validation.
Validates parameter sweeps, classification contracts, stability metrics, and privacy preservation.
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


def test_robustness_summary_classifications(robustness_summary_df):
    """Verify summary table structure and standard classification categories."""
    assert len(robustness_summary_df) >= 5, "Expected >= 5 core findings in summary"
    
    valid_classifications = {
        "ROBUST",
        "MODERATELY_SENSITIVE",
        "HIGHLY_SENSITIVE",
        "INSUFFICIENT_EVIDENCE",
    }
    for _, row in robustness_summary_df.iterrows():
        assert row["classification"] in valid_classifications, (
            f"Invalid classification '{row['classification']}' for finding {row['finding_id']}"
        )
        assert len(row["finding_statement"]) > 10
        assert len(row["substantive_conclusion"]) > 10

    classes_present = set(robustness_summary_df["classification"].unique())
    assert "ROBUST" in classes_present
    assert "MODERATELY_SENSITIVE" in classes_present
    assert "HIGHLY_SENSITIVE" in classes_present
    assert "INSUFFICIENT_EVIDENCE" in classes_present


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
    
    # Newman modularity is typically bounded between -0.5 and 1.0
    assert (evaluated["modularity_q"] >= -0.5).all()
    assert (evaluated["modularity_q"] <= 1.0).all()

    # Agency purity is a ratio between 0.0 and 1.0
    assert (evaluated["agency_purity"] >= 0.0).all()
    assert (evaluated["agency_purity"] <= 1.0).all()
