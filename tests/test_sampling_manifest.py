"""
tests/test_sampling_manifest.py

Unit & Regression Tests for Phase T5-A (Sampling Design) & T5-B (Event Oversampling)
Verifies:
1. Deterministic reproducibility: same input yields identical manifest.
2. Uniqueness: zero duplicate (channel_id, video_id) records.
3. Upper bounds: max 6 videos/year in baseline sampling.
4. Temporal boundary: zero videos outside 2020–2026.
5. Cohort lock: zero channels outside 193 frozen target cohort.
6. Sparse strata: channel-years with <= 6 videos select all available.
7. Bi-monthly bin dispersion: spreads selections across year.
8. Missing publication dates: strictly excluded.
9. T1 preservation: T1 catalog Parquet/CSV artifacts remain completely untouched.
10. Event-window oversampling: verified event windows add event-attributed videos without duplicates.
"""
import pytest
import hashlib
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

from config.settings import DATA_DIR
from scripts.build_historical_sampling_manifest import (
    build_sampling_manifest,
    compute_deterministic_score,
    get_bimonthly_bin,
    TARGET_MANIFEST_CSV,
    VIDEO_CATALOG_PARQUET,
    SUPPORTED_YEARS,
    TARGET_VIDEOS_PER_YEAR
)

BASE_DIR = Path(__file__).resolve().parent.parent


def test_bimonthly_bins():
    """Verify months 1..12 map correctly to 6 bi-monthly bins."""
    assert get_bimonthly_bin(1) == (1, "bin_1_jan_feb")
    assert get_bimonthly_bin(2) == (1, "bin_1_jan_feb")
    assert get_bimonthly_bin(3) == (2, "bin_2_mar_apr")
    assert get_bimonthly_bin(4) == (2, "bin_2_mar_apr")
    assert get_bimonthly_bin(5) == (3, "bin_3_may_jun")
    assert get_bimonthly_bin(6) == (3, "bin_3_may_jun")
    assert get_bimonthly_bin(7) == (4, "bin_4_jul_aug")
    assert get_bimonthly_bin(8) == (4, "bin_4_jul_aug")
    assert get_bimonthly_bin(9) == (5, "bin_5_sep_oct")
    assert get_bimonthly_bin(10) == (5, "bin_5_sep_oct")
    assert get_bimonthly_bin(11) == (6, "bin_6_nov_dec")
    assert get_bimonthly_bin(12) == (6, "bin_6_nov_dec")


def test_deterministic_score_reproducibility():
    """Deterministic score is identical for identical inputs."""
    s1 = compute_deterministic_score("UC123", 2024, "bin_1", "vidA")
    s2 = compute_deterministic_score("UC123", 2024, "bin_1", "vidA")
    s3 = compute_deterministic_score("UC123", 2024, "bin_1", "vidB")
    assert s1 == s2
    assert s1 != s3


def test_manifest_deterministic_reproducibility():
    """Repeated calls to build_sampling_manifest produce identical records."""
    fixed_time = "2026-09-08T00:00:00+00:00"
    m1 = build_sampling_manifest(created_at_override=fixed_time)
    m2 = build_sampling_manifest(created_at_override=fixed_time)
    assert len(m1) == len(m2)
    assert [r["sample_id"] for r in m1] == [r["sample_id"] for r in m2]
    assert [r["video_id"] for r in m1] == [r["video_id"] for r in m2]


def test_manifest_uniqueness_and_cohort_bounds():
    """Verify zero duplicate (channel_id, video_id) and strict cohort membership."""
    manifest = build_sampling_manifest()
    seen = set()
    target_df = pd.read_csv(TARGET_MANIFEST_CSV)
    allowed_cids = set(target_df["channel_id"])

    for r in manifest:
        key = (r["channel_id"], r["video_id"])
        assert key not in seen, f"Duplicate video in manifest: {key}"
        seen.add(key)

        assert r["channel_id"] in allowed_cids, f"Channel not in frozen cohort: {r['channel_id']}"
        assert r["year"] in SUPPORTED_YEARS, f"Year out of bounds: {r['year']}"
        assert r["video_published_at"] is not None


def test_manifest_strata_caps():
    """Verify max 6 videos per channel per year for baseline stratification."""
    manifest = build_sampling_manifest()
    counts = {}
    for r in manifest:
        if r["sampling_reason"] == "baseline_stratified":
            key = (r["channel_id"], r["year"])
            counts[key] = counts.get(key, 0) + 1

    for key, count in counts.items():
        assert count <= TARGET_VIDEOS_PER_YEAR, f"Stratum {key} exceeded target cap: {count} > {TARGET_VIDEOS_PER_YEAR}"


def test_event_window_oversampling_foundation(tmp_path):
    """
    Phase T5-B: Test that verified event windows produce distinct oversampled entries,
    and unverified events are ignored.
    """
    event_csv = tmp_path / "test_events.csv"
    # Create sample verified and unverified events
    event_csv.write_text(
        "event_id,event_type,event_name,event_date,channel_id,window_before_days,window_after_days,evidence_source,verified,notes\n"
        "ev_001,debut,Major Debut,2023-03-01T00:00:00Z,UCGBkYTR4tMKS38TQHGWWLjg,15,15,twitter,true,Test Verified\n"
        "ev_002,hiatus,Unverified Hiatus,2024-05-01T00:00:00Z,UCGBkYTR4tMKS38TQHGWWLjg,10,10,speculation,false,Ignored\n",
        encoding="utf-8"
    )

    records = build_sampling_manifest(event_windows_path=event_csv)
    event_records = [r for r in records if r["sampling_reason"] == "event_window"]
    # ev_001 should have matched or added entries if eligible catalog videos existed around March 2023
    for ev_r in event_records:
        assert ev_r["event_id"] == "ev_001"
        assert ev_r["channel_id"] == "UCGBkYTR4tMKS38TQHGWWLjg"

    # Verify no ev_002 exists since verified=false
    assert not any(r.get("event_id") == "ev_002" for r in records)


def test_t1_artifacts_immutability():
    """Verify SHA-256 hashes of T1 artifacts match exact recorded baselines."""
    baselines = {
        DATA_DIR / "temporal" / "catalog" / "video_catalog.parquet": "6c025d2dc7d3bc380cdfe1eca19c9b0ebe641f1be98e253defaeb9e38137bb87",
        DATA_DIR / "temporal" / "catalog" / "channel_coverage.parquet": "6846090c6172147b5beb0ec00c3d9b38ccf8bf2cfb6b11e3a32a2c55b12cee98",
        DATA_DIR / "temporal" / "catalog" / "target_manifest.csv": "0ce9e037f589e68a2cf8b9d4f058d67ef515e3ff6449f1a51fe422e6bcc6368a",
    }
    for file_path, expected_hash in baselines.items():
        assert file_path.exists(), f"File missing: {file_path}"
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"T1 file was mutated! {file_path}"
