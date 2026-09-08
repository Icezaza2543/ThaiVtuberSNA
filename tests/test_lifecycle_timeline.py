"""
Phase T8 Test Suite: Historical Agency & Lifecycle Timeline (Research Integrity Edition)
Verifies:
1. Deterministic resolution of agency_at(channel_id, date)
2. oldest video != verified debut by default (INFERRED_PROXY earliest_observed_content)
3. last video != verified graduation/hiatus by default (INFERRED_PROXY graduation/hiatus_proxy)
4. agency_at_selection is not projected backward as historical agency by default
5. VERIFIED vs INFERRED_PROXY separation
6. Pre-debut queries return pre_debut and Unknown agency
7. Hiatus and graduation states are properly time-bounded
8. Non-overlapping intervals per channel
9. Zero PII (viewer_hash) in lifecycle parquet files
"""

from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
import pytest

from scripts.build_historical_lifecycle import agency_at

LIFECYCLE_DIR = Path("data/temporal/lifecycle")
EVENTS_PARQUET = LIFECYCLE_DIR / "lifecycle_events.parquet"
INTERVALS_PARQUET = LIFECYCLE_DIR / "channel_lifecycle_intervals.parquet"


def test_lifecycle_files_exist():
    assert EVENTS_PARQUET.exists(), "lifecycle_events.parquet missing"
    assert INTERVALS_PARQUET.exists(), "channel_lifecycle_intervals.parquet missing"


def test_no_pii_in_lifecycle_files():
    for p in [EVENTS_PARQUET, INTERVALS_PARQUET]:
        tbl = pq.read_table(p)
        assert "viewer_hash" not in tbl.column_names, f"PII found in {p.name}"
        for col in tbl.column_names:
            assert "author" not in col.lower()


def test_oldest_video_is_not_verified_debut_by_default():
    """Verify that oldest video published at generates INFERRED_PROXY earliest_observed_content, not VERIFIED debut."""
    events_df = pd.read_parquet(EVENTS_PARQUET)
    proxy_debuts = events_df[events_df["event_type"] == "earliest_observed_content"]
    assert len(proxy_debuts) >= 150, "Expected earliest_observed_content proxy events for cohort"
    assert (proxy_debuts["verification_status"] == "INFERRED_PROXY").all()
    assert (proxy_debuts["confidence"] != "HIGH").all()


def test_last_video_is_not_verified_graduation_by_default():
    """Verify that newest video published at generates proxy events, not VERIFIED graduations."""
    events_df = pd.read_parquet(EVENTS_PARQUET)
    grad_proxies = events_df[events_df["event_type"] == "graduation_proxy"]
    assert len(grad_proxies) > 0
    assert (grad_proxies["verification_status"] == "INFERRED_PROXY").all()
    assert (grad_proxies["confidence"] != "HIGH").all()


def test_agency_at_selection_is_not_historical_agency_by_default():
    """Verify that agency_at_selection is not projected backward as historical agency."""
    intervals_df = pd.read_parquet(INTERVALS_PARQUET)
    # Filter for standard active intervals whose debut is an inferred proxy (excluding macro closure tenures)
    proxy_active = intervals_df[
        (intervals_df["verification_status"] == "INFERRED_PROXY") &
        (intervals_df["lifecycle_status"] == "active") &
        (intervals_df["agency_at_selection"] != "Independent") &
        (~intervals_df["provenance"].str.contains("vz|rpg", case=False))
    ]
    assert len(proxy_active) > 0
    # For these historical intervals, effective_agency must be 'Unknown', not projected from agency_at_selection
    assert (proxy_active["effective_agency"] == "Unknown").all()


def test_verified_vs_inferred_proxy_separation():
    """Verify that verification_status strictly separates VERIFIED, INFERRED_PROXY, and UNKNOWN."""
    events_df = pd.read_parquet(EVENTS_PARQUET)
    intervals_df = pd.read_parquet(INTERVALS_PARQUET)
    valid_statuses = {"VERIFIED", "INFERRED_PROXY", "UNKNOWN"}

    assert set(events_df["verification_status"].unique()).issubset(valid_statuses)
    assert set(intervals_df["verification_status"].unique()).issubset(valid_statuses)

    # Check that verified events have HIGH confidence and explicit evidence
    verified_events = events_df[events_df["verification_status"] == "VERIFIED"]
    assert len(verified_events) >= 2, "Expected verified events (traceable closures and streams)"
    assert (verified_events["confidence"] == "HIGH").all()
    assert (verified_events["evidence_source_ref"].notnull()).all()


def test_verified_requires_date_specific_traceable_evidence():
    """Verify that every VERIFIED event has exact date and identifiable traceable reference."""
    events_df = pd.read_parquet(EVENTS_PARQUET)
    verified = events_df[events_df["verification_status"] == "VERIFIED"]
    for _, r in verified.iterrows():
        assert r["event_date"] is not None and len(str(r["event_date"])) == 10
        assert r["evidence_source_ref"] is not None and len(str(r["evidence_source_ref"])) > 5
        # Must trace to an exact video or announcement
        assert any(prefix in str(r["evidence_source_ref"]) for prefix in ["video_catalog", "announcement"])


def test_status_only_evidence_cannot_verify_exact_date():
    """Verify that channels with status-only audit evidence are demoted to INFERRED_PROXY."""
    events_df = pd.read_parquet(EVENTS_PARQUET)
    # Shimonz and Mysterica X have status-only evidence (Retired, Graduated), not verified date
    for cid in ["UCt8vlwt6qi6P1mz5uuStJCA", "UCVogMqMZimg5YbPE48oPrlg"]:
        ch_events = events_df[events_df["channel_id"] == cid]
        assert not ch_events.empty
        assert (ch_events["verification_status"] == "INFERRED_PROXY").all(), f"Channel {cid} must be INFERRED_PROXY"


def test_earliest_observed_content_cannot_create_verified_agency_start():
    """Verify that VZ/RPG agency tenure starting at earliest observed content is INFERRED_PROXY."""
    intervals_df = pd.read_parquet(INTERVALS_PARQUET)
    vz_rpg_tenures = intervals_df[intervals_df["provenance"].str.contains("historical_vz_membership|historical_rpg_membership")]
    assert len(vz_rpg_tenures) > 0
    assert (vz_rpg_tenures["verification_status"] == "INFERRED_PROXY").all(), "Tenure start at earliest observed content cannot be VERIFIED"


def test_pre_debut_query_returns_unknown_and_inactive():
    res = agency_at("UCuZ1ajvlGFUMCHZAPdetKHw", "2019-01-01")
    assert res["effective_agency"] == "Unknown"
    assert res["lifecycle_status"] == "pre_debut"
    assert res["is_active"] is False


def test_active_tenure_query_returns_inferred_proxy():
    # Dacapo in 2023 was observed active, but agency is not projected backward
    res = agency_at("UCuZ1ajvlGFUMCHZAPdetKHw", "2023-06-01")
    assert res["agency_at_selection"] == "Algorhythm Project"
    assert res["effective_agency"] == "Unknown"
    assert res["verification_status"] == "INFERRED_PROXY"
    assert res["lifecycle_status"] == "active"
    assert res["is_active"] is True


def test_post_graduation_query_returns_graduated():
    # Shimonz graduated in 2022 (demoted to INFERRED_PROXY due to status-only audit evidence)
    res = agency_at("UCt8vlwt6qi6P1mz5uuStJCA", "2023-01-01")
    assert res["effective_agency"] == "Graduated"
    assert res["lifecycle_status"] == "graduated"
    assert res["verification_status"] == "INFERRED_PROXY"
    assert res["is_active"] is False


def test_hiatus_query_returns_hiatus():
    # Hinabe HongFei in hiatus
    res = agency_at("UCutz6S1DcEHPnEb_r9ztkzg", "2025-06-01")
    assert res["lifecycle_status"] == "hiatus"
    assert res["is_active"] is False


def test_non_overlapping_intervals_per_channel():
    df_int = pq.read_table(INTERVALS_PARQUET).to_pandas()
    for cid, grp in df_int.groupby("channel_id"):
        dated_intervals = grp[grp["start_date"].notnull()].sort_values("start_date")
        if len(dated_intervals) > 1:
            prev_end = None
            for _, row in dated_intervals.iterrows():
                if pd.notnull(prev_end) and pd.notnull(row["start_date"]):
                    assert str(row["start_date"]) >= str(prev_end), f"Overlap in channel {cid}: {row['start_date']} < {prev_end}"
                prev_end = row["end_date"]
