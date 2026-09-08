"""
Regression and analytical tests for Phase T9: Event Impact Analysis (Research Integrity Edition).
Validates verified vs proxy result separation, non-causal reporting, privacy preservation,
and evidence stratification.
"""

import re
import pytest
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EVENT_ANALYSIS_DIR = BASE_DIR / "data" / "temporal" / "event_analysis"
METRICS_PARQUET = EVENT_ANALYSIS_DIR / "event_impact_metrics.parquet"
REPORT_MD = EVENT_ANALYSIS_DIR / "event_impact_report.md"


@pytest.fixture(scope="module")
def impact_metrics_df():
    assert METRICS_PARQUET.exists(), f"Missing {METRICS_PARQUET}"
    return pd.read_parquet(METRICS_PARQUET)


def test_event_impact_artifacts_exist():
    """Verify that all required T9 output artifacts are present."""
    assert METRICS_PARQUET.exists(), f"Missing {METRICS_PARQUET}"
    assert REPORT_MD.exists(), f"Missing {REPORT_MD}"
    assert REPORT_MD.stat().st_size > 500, "Event impact report is empty or suspiciously small."


def test_event_impact_schema_and_columns(impact_metrics_df):
    """Verify all required metric and contract columns are present."""
    required_cols = [
        "event_id",
        "channel_id",
        "channel_name",
        "event_type",
        "event_date",
        "agency_at_event",
        "agency_at_selection",
        "verification_status",
        "confidence",
        "analysis_tier",
        "window_days",
        "pre_start",
        "pre_end",
        "post_start",
        "post_end",
        "pre_focal_viewers",
        "post_focal_viewers",
        "delta_focal_viewers",
        "continuing_focal_viewers",
        "focal_retention_rate",
        "pre_viewers_seen_other_post",
        "same_agency_other_viewers",
        "cross_agency_other_viewers",
        "distinct_other_channels_engaged",
        "top_post_associated_channels",
        "pre_focal_degree",
        "post_focal_degree",
        "evidence_status",
        "evidence_note",
    ]
    for col in required_cols:
        assert col in impact_metrics_df.columns, f"Missing required column: {col}"


def test_verified_vs_proxy_separation(impact_metrics_df):
    """Verify that primary verified events and exploratory proxy events are strictly partitioned."""
    assert set(impact_metrics_df["analysis_tier"].unique()) == {"PRIMARY_VERIFIED", "EXPLORATORY_PROXY"}
    
    verified_rows = impact_metrics_df[impact_metrics_df["analysis_tier"] == "PRIMARY_VERIFIED"]
    proxy_rows = impact_metrics_df[impact_metrics_df["analysis_tier"] == "EXPLORATORY_PROXY"]

    assert len(verified_rows) > 0, "Expected verified events in primary tier"
    assert (verified_rows["verification_status"] == "VERIFIED").all()
    assert (verified_rows["confidence"] == "HIGH").all()

    assert len(proxy_rows) > 0, "Expected proxy events in exploratory tier"
    assert (proxy_rows["verification_status"] == "INFERRED_PROXY").all()
    assert (proxy_rows["confidence"] != "HIGH").all()


def test_event_impact_windows(impact_metrics_df):
    """Verify metrics exist for both 30-day and 90-day observation windows."""
    windows = set(impact_metrics_df["window_days"].unique())
    assert windows == {30, 90}, f"Expected windows {{30, 90}}, got {windows}"
    
    count_30 = (impact_metrics_df["window_days"] == 30).sum()
    count_90 = (impact_metrics_df["window_days"] == 90).sum()
    assert count_30 == count_90, "Event count must match between 30d and 90d window analyses"


def test_zero_viewer_hash_leakage(impact_metrics_df):
    """Verify that zero viewer hashes or individual identifier columns exist."""
    forbidden_terms = ["viewer_hash", "author_hash", "user_id", "viewer_id"]
    for col in impact_metrics_df.columns:
        for term in forbidden_terms:
            assert term not in col.lower(), f"Forbidden identifier column found: {col}"


def test_evidence_stratification_logic(impact_metrics_df):
    """Verify that events with low interaction (< 5 viewers pre and post) are flagged as INSUFFICIENT_EVIDENCE."""
    for _, row in impact_metrics_df.iterrows():
        pre_v = row["pre_focal_viewers"]
        post_v = row["post_focal_viewers"]
        status = row["evidence_status"]
        if pre_v < 5 and post_v < 5:
            assert status == "INSUFFICIENT_EVIDENCE", (
                f"Event {row['event_id']} has pre={pre_v}, post={post_v} but status={status}"
            )
        else:
            assert status == "SUFFICIENT_EVIDENCE", (
                f"Event {row['event_id']} has pre={pre_v}, post={post_v} but status={status}"
            )


def test_non_causal_report_framing():
    """Verify that the generated report strictly complies with non-causal language constraints."""
    text = REPORT_MD.read_text(encoding="utf-8").lower()
    
    # Required framing concepts
    assert "observed change around event" in text or "observed" in text
    assert "temporal" in text
    
    # Strictly forbidden causal assertions
    forbidden_causal_phrases = [
        "caused viewers to migrate",
        "caused audience to migrate",
        "event caused viewers to",
        "fans migrated",
        "audience migrated because",
        "proves causality",
    ]
    for phrase in forbidden_causal_phrases:
        assert phrase not in text, f"Forbidden causal assertion found in report: '{phrase}'"
