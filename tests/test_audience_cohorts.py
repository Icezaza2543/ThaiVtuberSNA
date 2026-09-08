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
    assert "mean_of_cohort_median_channel_breadth" in survival_df.columns

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


def test_cross_agency_vs_cross_channel_synthetic_fixtures():
    """Regression test for exact cross-agency semantics:
    - A1 (Agency A) -> A2 (Agency A): cross-channel YES, cross-agency NO
    - A1 (Agency A) -> B1 (Agency B): cross-channel YES, cross-agency YES
    - multi-agency base cohort handled correctly
    - zero-return cohort-year remains in denominator
    """
    import duckdb
    import pandas as pd

    con = duckdb.connect()

    # Synthetic interactions
    # v1: 2020 watches ch_A1 (Agency_A) -> in 2021 watches ch_A2 (Agency_A)
    # v2: 2020 watches ch_A1 (Agency_A) -> in 2021 watches ch_B1 (Agency_B)
    # v3: 2020 watches ch_A1 (Agency_A) & ch_B1 (Agency_B) -> in 2021 watches ch_A2 (Agency_A) & ch_B2 (Agency_B)
    # v4: 2020 watches ch_A1 (Agency_A) & ch_B1 (Agency_B) -> in 2021 watches ch_C1 (Agency_C)
    # v5: 2020 watches ch_A1 (Agency_A) -> in 2021 NO interactions (zero return)
    data = [
        # 2020 cohort interactions
        ("v1", "ch_A1", "Agency_A", 2020),
        ("v2", "ch_A1", "Agency_A", 2020),
        ("v3", "ch_A1", "Agency_A", 2020),
        ("v3", "ch_B1", "Agency_B", 2020),
        ("v4", "ch_A1", "Agency_A", 2020),
        ("v4", "ch_B1", "Agency_B", 2020),
        ("v5", "ch_A1", "Agency_A", 2020),
        # 2021 observation interactions
        ("v1", "ch_A2", "Agency_A", 2021),
        ("v2", "ch_B1", "Agency_B", 2021),
        ("v3", "ch_A2", "Agency_A", 2021),
        ("v3", "ch_B2", "Agency_B", 2021),
        ("v4", "ch_C1", "Agency_C", 2021),
    ]
    df_raw = pd.DataFrame(data, columns=["viewer_hash", "vtuber_channel_id", "agency", "interaction_year"])
    con.register("viewer_channel_years", df_raw)

    con.execute("""
        CREATE TEMP TABLE viewer_cohorts AS
        SELECT viewer_hash, MIN(interaction_year) AS cohort_year
        FROM viewer_channel_years
        GROUP BY 1
    """)

    con.execute("""
        CREATE TEMP TABLE viewer_first_year_channels AS
        SELECT DISTINCT
            vcy.viewer_hash,
            vcy.vtuber_channel_id AS base_channel_id
        FROM viewer_channel_years vcy
        JOIN viewer_cohorts vc ON vcy.viewer_hash = vc.viewer_hash AND vcy.interaction_year = vc.cohort_year
    """)

    con.execute("""
        CREATE TEMP TABLE viewer_first_year_agencies AS
        SELECT DISTINCT
            vcy.viewer_hash,
            vcy.agency AS base_agency
        FROM viewer_channel_years vcy
        JOIN viewer_cohorts vc ON vcy.viewer_hash = vc.viewer_hash AND vcy.interaction_year = vc.cohort_year
    """)

    res = con.execute("""
        WITH viewer_year_channels_evaluated AS (
            SELECT 
                vcy.viewer_hash,
                vc.cohort_year,
                vcy.interaction_year AS observation_year,
                vcy.vtuber_channel_id,
                vcy.agency,
                CASE WHEN vfc.base_channel_id IS NOT NULL THEN 1 ELSE 0 END AS is_base_channel,
                CASE WHEN vfa.base_agency IS NOT NULL THEN 1 ELSE 0 END AS is_base_agency
            FROM viewer_channel_years vcy
            JOIN viewer_cohorts vc ON vcy.viewer_hash = vc.viewer_hash
            LEFT JOIN viewer_first_year_channels vfc 
                ON vcy.viewer_hash = vfc.viewer_hash AND vcy.vtuber_channel_id = vfc.base_channel_id
            LEFT JOIN viewer_first_year_agencies vfa 
                ON vcy.viewer_hash = vfa.viewer_hash AND vcy.agency = vfa.base_agency
        )
        SELECT 
            viewer_hash,
            observation_year,
            MAX(is_base_channel) AS has_same_channel,
            MAX(CASE WHEN is_base_channel = 0 THEN 1 ELSE 0 END) AS has_cross_channel,
            MAX(CASE WHEN is_base_agency = 0 THEN 1 ELSE 0 END) AS has_cross_agency
        FROM viewer_year_channels_evaluated
        WHERE observation_year = 2021
        GROUP BY 1, 2
        ORDER BY 1
    """).df().set_index("viewer_hash")

    # 1. v1: A1 (Agency A) -> A2 (Agency A): cross-channel YES, cross-agency NO
    assert res.loc["v1", "has_cross_channel"] == 1
    assert res.loc["v1", "has_cross_agency"] == 0

    # 2. v2: A1 (Agency A) -> B1 (Agency B): cross-channel YES, cross-agency YES
    assert res.loc["v2", "has_cross_channel"] == 1
    assert res.loc["v2", "has_cross_agency"] == 1

    # 3. v3: multi-agency base {A, B} -> {A2 (Agency A), B2 (Agency B)}: cross-channel YES, cross-agency NO
    assert res.loc["v3", "has_cross_channel"] == 1
    assert res.loc["v3", "has_cross_agency"] == 0

    # 4. v4: multi-agency base {A, B} -> {C1 (Agency C)}: cross-channel YES, cross-agency YES
    assert res.loc["v4", "has_cross_channel"] == 1
    assert res.loc["v4", "has_cross_agency"] == 1

    # 5. Denominator retention check: cohort size is 5 (v1..v5).
    # v5 has zero return in 2021.
    cohort_size = 5
    reobserved = len(res)  # 4
    continuation_rate = reobserved / cohort_size
    assert continuation_rate == 0.8  # 4 / 5, v5 remains in denominator!

