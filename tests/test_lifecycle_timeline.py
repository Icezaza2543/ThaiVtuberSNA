"""
Phase T8 Test Suite: Historical Agency & Lifecycle Timeline
Verifies:
1. Deterministic resolution of agency_at(channel_id, date)
2. Pre-debut queries return pre_debut and Unknown agency
3. Active intervals return correct historical agency
4. Hiatus and graduation states are properly time-bounded
5. Non-overlapping intervals per channel
6. Zero PII (viewer_hash) in lifecycle parquet files
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


def test_pre_debut_query_returns_unknown_and_inactive():
    # Dacapo debuted in 2021
    res = agency_at("UCuZ1ajvlGFUMCHZAPdetKHw", "2019-01-01")
    assert res["effective_agency"] == "Unknown"
    assert res["lifecycle_status"] == "pre_debut"
    assert res["is_active"] is False


def test_active_tenure_query_returns_agency():
    # Dacapo in 2023 was active in Algorhythm Project
    res = agency_at("UCuZ1ajvlGFUMCHZAPdetKHw", "2023-06-01")
    assert res["effective_agency"] == "Algorhythm Project"
    assert res["lifecycle_status"] == "active"
    assert res["is_active"] is True


def test_post_graduation_query_returns_graduated():
    # Ice Shirakoi graduated in 2025
    res = agency_at("UCfe7Lxdn2PDp_xnnrC_RSzA", "2025-06-01")
    assert res["effective_agency"] == "Graduated"
    assert res["lifecycle_status"] == "graduated"
    assert res["is_active"] is False


def test_hiatus_query_returns_hiatus():
    # Hinabe HongFei in hiatus
    res = agency_at("UCutz6S1DcEHPnEb_r9ztkzg", "2025-06-01")
    assert res["lifecycle_status"] == "hiatus"
    assert res["is_active"] is False


def test_agency_at_selection_preserved():
    df_int = pq.read_table(INTERVALS_PARQUET).to_pandas()
    assert "agency_at_selection" in df_int.columns
    assert "effective_agency" in df_int.columns
    # Check that agency_at_selection matches for all intervals of a channel
    for cid, grp in df_int.groupby("channel_id"):
        assert grp["agency_at_selection"].nunique() == 1


def test_non_overlapping_intervals_per_channel():
    df_int = pq.read_table(INTERVALS_PARQUET).to_pandas()
    for cid, grp in df_int.groupby("channel_id"):
        dated_intervals = grp[grp["start_date"].notnull()].sort_values("start_date")
        if len(dated_intervals) > 1:
            prev_end = None
            for _, row in dated_intervals.iterrows():
                if prev_end is not None and row["start_date"] is not None:
                    assert row["start_date"] >= prev_end, f"Overlap in channel {cid}: {row['start_date']} < {prev_end}"
                prev_end = row["end_date"]
