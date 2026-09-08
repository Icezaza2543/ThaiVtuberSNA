"""Tests for Phase T15 Coverage, Bias & Evidence Reliability Model.

Verifies:
1. Expected quality artifacts exist.
2. Zero viewer_hash or individual-level PII in schemas or reports.
3. Yearly evidence quality schema, bounds, and deterministic tiers.
4. Channel-level quality metrics and support tier assignments.
5. Perturbation sensitivity scenarios and valid metric bounds.
"""
from pathlib import Path
import re
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def yearly_quality_df():
    path = REPO_ROOT / "data" / "temporal" / "quality" / "yearly_evidence_quality.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def channel_quality_df():
    path = REPO_ROOT / "data" / "temporal" / "quality" / "channel_evidence_quality.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def bias_sensitivity_df():
    path = REPO_ROOT / "data" / "temporal" / "quality" / "bias_sensitivity.parquet"
    assert path.exists(), f"Missing {path}"
    return pd.read_parquet(path)

@pytest.fixture
def quality_report_content():
    path = REPO_ROOT / "data" / "temporal" / "quality" / "evidence_quality_report.md"
    assert path.exists(), f"Missing {path}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def test_quality_artifacts_privacy(yearly_quality_df, channel_quality_df, bias_sensitivity_df, quality_report_content):
    """Verify zero raw viewer hashes or individual identifier columns are exposed."""
    forbidden = ["viewer_hash", "author_hash", "user_id", "author_id"]
    for df in [yearly_quality_df, channel_quality_df, bias_sensitivity_df]:
        for col in df.columns:
            for term in forbidden:
                assert term not in col.lower(), f"Forbidden identifier column in dataframe: {col}"

    sha256_hex_pattern = re.compile(r'\b[a-f0-9]{64}\b')
    matches = sha256_hex_pattern.findall(quality_report_content)
    assert not matches, f"Raw hex string found in quality report: {matches[:3]}"

def test_yearly_evidence_quality_schema_and_tiers(yearly_quality_df):
    """Verify yearly quality metrics schema, rate bounds, and deterministic tiers."""
    expected_cols = [
        "year", "year_label", "is_ytd", "catalog_videos", "sampled_videos",
        "video_sampling_ratio", "total_interactions", "comment_interactions",
        "live_chat_interactions", "live_chat_share", "t6_deepened_interactions",
        "t6_deepened_share", "mean_comments_per_video", "median_comments_per_video",
        "cap_100_hit_videos", "cap_100_exposure_rate", "catalog_channels_active",
        "channels_with_evidence", "channel_coverage_rate", "source_provenance_entropy",
        "evidence_support_tier", "evidence_tier_rationale"
    ]
    for col in expected_cols:
        assert col in yearly_quality_df.columns, f"Missing column: {col}"

    assert len(yearly_quality_df) == 7
    valid_tiers = {"HIGH", "MODERATE", "LOW"}
    assert set(yearly_quality_df["evidence_support_tier"]).issubset(valid_tiers)

    # Rates bounded in [0, 1]
    assert (yearly_quality_df["video_sampling_ratio"] >= 0.0).all() and (yearly_quality_df["video_sampling_ratio"] <= 1.0).all()
    assert (yearly_quality_df["channel_coverage_rate"] >= 0.0).all() and (yearly_quality_df["channel_coverage_rate"] <= 1.0).all()
    assert (yearly_quality_df["cap_100_exposure_rate"] >= 0.0).all() and (yearly_quality_df["cap_100_exposure_rate"] <= 1.0).all()

def test_channel_evidence_quality_schema(channel_quality_df):
    """Verify channel-level quality schema and support tiers."""
    expected_cols = [
        "channel_id", "channel_name", "agency", "catalog_videos_count",
        "sampled_videos_count", "sampling_coverage_rate", "total_interactions",
        "distinct_viewers_count", "t6_deepened_interactions", "t6_deepened_share",
        "cap_100_hit_videos", "cap_100_exposure_rate", "has_live_chat",
        "years_active_count", "lifecycle_verification_status",
        "evidence_support_tier", "evidence_tier_rationale"
    ]
    for col in expected_cols:
        assert col in channel_quality_df.columns, f"Missing column: {col}"

    assert len(channel_quality_df) > 0
    valid_tiers = {"HIGH", "MODERATE", "LOW"}
    assert set(channel_quality_df["evidence_support_tier"]).issubset(valid_tiers)

def test_bias_sensitivity_scenarios(bias_sensitivity_df):
    """Verify perturbation sensitivity scenarios and metric ranges."""
    expected_scenarios = {
        "BASELINE_UNIFIED_TH1", "COMMENT_ONLY_TH1", "LOW_COVERAGE_EXCLUDED",
        "THRESHOLD_TH3", "THRESHOLD_TH5"
    }
    assert expected_scenarios.issubset(set(bias_sensitivity_df["perturbation_scenario"]))
    assert len(bias_sensitivity_df) == 35  # 7 years * 5 scenarios

    for _, r in bias_sensitivity_df.iterrows():
        assert r["density"] >= 0.0 and r["density"] <= 1.0
        assert r["giant_component_share"] >= 0.0 and r["giant_component_share"] <= 1.0
