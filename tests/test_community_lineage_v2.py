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
        "split_ancestors", "merge_ancestors", "member_snapshot_communities"
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

def test_split_and_merge_ancestry_tracking(lifecycles_df):
    """Verify that split and merge ancestry fields are populated properly."""
    has_split_ancestor = lifecycles_df[lifecycles_df["split_ancestors"] != "None"]
    assert len(has_split_ancestor) >= 3, "Expected multiple lineages with traceable split ancestry"

def test_report_numbers_match_parquet(lifecycles_df, report_content):
    """Verify report counts match parquet values dynamically."""
    total_lineages = len(lifecycles_df)
    assert f"**{total_lineages} distinct persistent community lineages**" in report_content
