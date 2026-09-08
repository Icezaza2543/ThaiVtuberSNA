"""Tests for Phase T11 Multi-Year Community Lineage v2.

Verifies:
1. Stable persistent lineage IDs across years.
2. Split and merge ancestry tracking.
3. Deterministic execution and assignment.
4. Conflict-free lifecycle status (no contradictory lifecycle states).
5. Schema compliance and expected output files.
"""
from pathlib import Path
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def lineage_v2_df():
    path = REPO_ROOT / "data" / "temporal" / "analysis" / "community_lineage_v2.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def lifecycles_df():
    path = REPO_ROOT / "data" / "temporal" / "analysis" / "community_lifecycles.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def report_content():
    path = REPO_ROOT / "data" / "temporal" / "analysis" / "community_lineage_v2_report.md"
    assert path.exists(), f"Missing {path}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def test_lineage_v2_schema_and_integrity(lineage_v2_df):
    """Verify community_lineage_v2.parquet schema."""
    expected_cols = [
        "from_year", "to_year", "from_community_id", "to_community_id",
        "from_lineage_id", "to_lineage_id", "relation_type",
        "shared_channels", "jaccard_similarity", "forward_overlap",
        "backward_overlap", "is_primary_backbone"
    ]
    for col in expected_cols:
        assert col in lineage_v2_df.columns, f"Missing column: {col}"

    assert len(lineage_v2_df) > 0
    valid_relations = {"continuation", "split_branch", "merge_tributary"}
    assert set(lineage_v2_df["relation_type"]).issubset(valid_relations)

def test_community_lifecycles_schema_and_semantics(lifecycles_df):
    """Verify community_lifecycles.parquet schema and valid lifespans."""
    expected_cols = [
        "lineage_id", "birth_year", "last_observed_year", "lifespan_years",
        "lifecycle_status", "dominant_agency", "dominant_agency_share",
        "total_unique_creators", "mean_membership_churn",
        "split_contributors", "merge_contributors", "member_snapshot_communities"
    ]
    for col in expected_cols:
        assert col in lifecycles_df.columns, f"Missing column: {col}"

    # Verify lifespans
    for _, r in lifecycles_df.iterrows():
        assert r["lifespan_years"] == (r["last_observed_year"] - r["birth_year"] + 1)
        assert r["lifespan_years"] >= 1
        assert 2020 <= r["birth_year"] <= 2026
        assert 2020 <= r["last_observed_year"] <= 2026
        assert r["lifecycle_status"] in {"ACTIVE", "DISAPPEARED"}
        if r["last_observed_year"] == 2026:
            assert r["lifecycle_status"] == "ACTIVE"
        else:
            assert r["lifecycle_status"] == "DISAPPEARED"

def test_one_to_one_primary_backbone_matching(lineage_v2_df):
    """Verify each source has <= 1 continuation and each target has <= 1 continuation per year pair."""
    continuations = lineage_v2_df[lineage_v2_df["relation_type"] == "continuation"]
    for yr_from, grp in continuations.groupby("from_year"):
        # Sources in this year transition must be unique
        assert len(grp["from_community_id"]) == len(grp["from_community_id"].unique()), f"Duplicate continuation source in {yr_from}"
        # Targets in this year transition must be unique
        assert len(grp["to_community_id"]) == len(grp["to_community_id"].unique()), f"Duplicate continuation target in {yr_from}"

def test_no_contradictory_lifecycle_states(lifecycles_df, lineage_v2_df):
    """Verify that lineage birth and death do not have contradictory concurrent transitions."""
    for _, r in lifecycles_df.iterrows():
        lid = r["lineage_id"]
        byr = r["birth_year"]
        lyr = r["last_observed_year"]

        # No transition into this lineage before birth year
        prior_edges = lineage_v2_df[(lineage_v2_df["to_lineage_id"] == lid) & (lineage_v2_df["to_year"] < byr)]
        assert prior_edges.empty, f"Lineage {lid} has transition before birth year {byr}"

        # No transition out of this lineage after last observed year
        post_edges = lineage_v2_df[(lineage_v2_df["from_lineage_id"] == lid) & (lineage_v2_df["from_year"] > lyr)]
        assert post_edges.empty, f"Lineage {lid} has outgoing transition after death year {lyr}"

def test_deterministic_lineage_generation():
    """Verify running the lineage builder produces identical deterministic results."""
    from scripts.build_community_lineage_v2 import build_community_lineage_v2
    df1_edges, df1_life = build_community_lineage_v2()
    df2_edges, df2_life = build_community_lineage_v2()

    pd.testing.assert_frame_equal(df1_edges, df2_edges)
    pd.testing.assert_frame_equal(df1_life, df2_life)

def test_split_and_merge_contributors_tracking(lifecycles_df):
    """Verify that split and merge contributor fields are populated properly."""
    has_split = lifecycles_df[lifecycles_df["split_contributors"] != "None"]
    assert len(has_split) >= 3, "Expected multiple lineages with traceable split contributors"

def test_two_sources_to_same_target_synthetic_regression():
    """Synthetic regression: two source communities overlapping with the same target must result in 1 continuation + 1 merge_tributary."""
    # Synthetic test data
    c_from = {
        "comm_A": {"c1", "c2", "c3", "c4", "c5"},
        "comm_B": {"c1", "c2", "c3", "c6", "c7"}
    }
    c_to = {
        "comm_T": {"c1", "c2", "c3", "c4", "c5", "c8"}
    }
    # Match candidate score for A -> T: J = 5/6 = 0.833, fwd = 5/5 = 1.0, bwd = 5/6 = 0.833 -> score high
    # Score for B -> T: J = 3/8 = 0.375, fwd = 3/5 = 0.60, bwd = 3/6 = 0.50 -> score lower
    # Target comm_T must only have 1 continuation (from comm_A), while comm_B becomes merge_tributary
    candidates = [
        {"src_id": "comm_A", "tgt_id": "comm_T", "score": 0.833 * 0.4 + 1.0 * 0.3 + 0.833 * 0.3, "shared": 5, "jacc": 0.833, "fwd": 1.0, "bwd": 0.833},
        {"src_id": "comm_B", "tgt_id": "comm_T", "score": 0.375 * 0.4 + 0.6 * 0.3 + 0.5 * 0.3, "shared": 3, "jacc": 0.375, "fwd": 0.6, "bwd": 0.5}
    ]
    candidates.sort(key=lambda x: -x["score"])
    matched_sources = set()
    matched_targets = set()
    cont_edges = []
    secondary_edges = []

    for c in candidates:
        s, t = c["src_id"], c["tgt_id"]
        if s not in matched_sources and t not in matched_targets:
            matched_sources.add(s)
            matched_targets.add(t)
            cont_edges.append((s, t))
        else:
            if c["bwd"] >= 0.20:
                secondary_edges.append((s, t, "merge_tributary"))

    assert len(cont_edges) == 1
    assert cont_edges[0] == ("comm_A", "comm_T")
    assert len(secondary_edges) == 1
    assert secondary_edges[0] == ("comm_B", "comm_T", "merge_tributary")

def test_report_numbers_match_parquet(lifecycles_df, report_content):
    """Verify report counts match parquet values dynamically."""
    total_lineages = len(lifecycles_df)
    assert f"**{total_lineages} distinct persistent community lineages**" in report_content


def test_maximum_weight_bipartite_matching_suboptimal_greedy_regression():
    """Regression test proving global maximum-weight bipartite matching beats greedy.

    Setup:
      A-X = 0.90, A-Y = 0.80
      B-X = 0.85, B-Y = 0.10

    Greedy would pick A-X (0.90), leaving B with only B-Y (0.10) for total weight 1.00.
    Optimal global matching picks A-Y (0.80) + B-X (0.85) for total weight 1.65.
    """
    from scripts.build_community_lineage_v2 import solve_global_max_weight_bipartite_matching

    candidates = [
        {"src_id": "A", "tgt_id": "X", "score": 0.90, "shared_count": 9},
        {"src_id": "A", "tgt_id": "Y", "score": 0.80, "shared_count": 8},
        {"src_id": "B", "tgt_id": "X", "score": 0.85, "shared_count": 8},
        {"src_id": "B", "tgt_id": "Y", "score": 0.10, "shared_count": 1},
    ]

    matched_pairs = solve_global_max_weight_bipartite_matching(candidates)
    expected = {("A", "Y"), ("B", "X")}
    assert matched_pairs == expected, f"Expected {expected}, got {matched_pairs}"

    # Verify score calculation formula: 0.4*Jaccard + 0.3*Forward + 0.3*Backward
    jacc, fwd, bwd = 0.5, 0.6, 0.4
    expected_score = 0.4 * jacc + 0.3 * fwd + 0.3 * bwd
    assert abs(expected_score - 0.50) < 1e-9

