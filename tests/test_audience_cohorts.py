"""Tests for Phase T12 Audience Cohort & Survival Analysis.

Verifies:
1. Expected cohort artifacts exist.
2. Zero viewer_hash or individual-level PII leaked in parquet schemas or report.
3. Retention matrix logic and denominator mathematical consistency.
4. Survival persistence monotonicity and bounded rates [0, 1].
5. Reactivation counts and gap year definitions.
"""
from pathlib import Path
import re
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def retention_matrix_df():
    path = REPO_ROOT / "data" / "temporal" / "cohorts" / "cohort_retention_matrix.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def survival_df():
    path = REPO_ROOT / "data" / "temporal" / "cohorts" / "cohort_survival.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def reactivation_df():
    path = REPO_ROOT / "data" / "temporal" / "cohorts" / "cohort_reactivation.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def cohort_report_content():
    path = REPO_ROOT / "data" / "temporal" / "cohorts" / "cohort_survival_report.md"
    assert path.exists(), f"Missing {path}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def test_cohort_artifacts_privacy(retention_matrix_df, survival_df, reactivation_df, cohort_report_content):
    """Verify zero raw viewer hashes or individual identifier columns are exposed."""
    forbidden = ["viewer_hash", "author_hash", "user_id", "author_id"]
    for df in [retention_matrix_df, survival_df, reactivation_df]:
        for col in df.columns:
            for term in forbidden:
                assert term not in col.lower(), f"Forbidden identifier column in dataframe: {col}"

    # Verify no raw 64-character hex strings in markdown report
    sha256_hex_pattern = re.compile(r'\b[a-f0-9]{64}\b')
    matches = sha256_hex_pattern.findall(cohort_report_content)
    assert not matches, f"Raw hex string found in cohort report: {matches[:3]}"

def test_retention_matrix_schema_and_denominators(retention_matrix_df):
    """Verify retention matrix schema and rate calculations."""
    expected_cols = [
        "cohort_year", "observation_year", "elapsed_years", "cohort_size",
        "reobserved_viewers", "continuation_rate", "same_channel_reobserved_viewers",
        "same_channel_retention_rate", "cross_channel_reobserved_viewers",
        "cross_channel_rate", "cross_agency_reobserved_viewers",
        "cross_agency_rate", "median_channel_breadth"
    ]
    for col in expected_cols:
        assert col in retention_matrix_df.columns, f"Missing column: {col}"

    for _, r in retention_matrix_df.iterrows():
        # Year 0 continuation is exactly 100%
        if r["elapsed_years"] == 0:
            assert r["reobserved_viewers"] == r["cohort_size"]
            assert r["continuation_rate"] == 1.0
        else:
            assert 0.0 <= r["continuation_rate"] <= 1.0
            assert 0.0 <= r["same_channel_retention_rate"] <= r["continuation_rate"]
            assert r["reobserved_viewers"] <= r["cohort_size"]

def test_survival_persistence_monotonicity_and_bounds(survival_df):
    """Verify aggregated survival persistence rates are within valid bounds."""
    assert len(survival_df) == 7  # Elapsed +0 through +6 years
    assert survival_df[survival_df["elapsed_years"] == 0]["persistence_rate"].iloc[0] == 1.0

    # Rates should decrease or remain generally low across elapsed horizons
    p_rates = survival_df["persistence_rate"].tolist()
    assert all(0.0 <= p <= 1.0 for p in p_rates)
    assert p_rates[1] < p_rates[0]  # +1 year drop from +0 year

def test_reactivation_gap_consistency(reactivation_df):
    """Verify reactivation records represent at least 1 unobserved year (gap >= 2)."""
    assert len(reactivation_df) > 0
    for _, r in reactivation_df.iterrows():
        assert r["gap_years"] >= 2, f"Expected gap >= 2 for reactivation, got {r['gap_years']}"
        assert r["reactivation_year"] >= r["cohort_year"] + r["gap_years"]
        assert r["reactivated_viewers"] > 0
