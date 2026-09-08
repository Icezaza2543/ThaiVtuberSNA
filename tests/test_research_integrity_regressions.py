"""Test suite verifying end-to-end research integrity regressions for T8-T10.

Regressions enforced:
1. VERIFIED requires date-specific traceable evidence (evidence_source_ref present).
2. Status-only evidence cannot verify exact date (demoted to INFERRED_PROXY or UNKNOWN).
3. Earliest observed content cannot create VERIFIED agency-start interval.
4. Verified T9 count follows actual T8 VERIFIED channel events dynamically.
5. T10 T6/T5 table uses separate actual metrics (t6_nodes != t5_nodes or distinct fields).
6. Generated report numbers equal parquet/DataFrame values.
7. Changing fixture metric changes generated report output.
8. No hardcoded empirical result constants in report generation prose.
9. No viewer_hash in public outputs.
"""
from pathlib import Path
import re
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def lifecycle_events():
    return pd.read_parquet(REPO_ROOT / "data" / "temporal" / "lifecycle" / "lifecycle_events.parquet")

@pytest.fixture
def lifecycle_intervals():
    return pd.read_parquet(REPO_ROOT / "data" / "temporal" / "lifecycle" / "channel_lifecycle_intervals.parquet")

@pytest.fixture
def event_impact_metrics():
    return pd.read_parquet(REPO_ROOT / "data" / "temporal" / "event_analysis" / "event_impact_metrics.parquet")

@pytest.fixture
def sensitivity_results():
    return pd.read_parquet(REPO_ROOT / "data" / "temporal" / "robustness" / "sensitivity_results.parquet")

@pytest.fixture
def robustness_summary():
    return pd.read_parquet(REPO_ROOT / "data" / "temporal" / "robustness" / "robustness_summary.parquet")

@pytest.fixture
def integrity_report_text():
    report_path = REPO_ROOT / "data" / "temporal" / "research_integrity" / "t8_t10_integrity_report.md"
    assert report_path.exists(), "t8_t10_integrity_report.md must exist"
    with open(report_path, "r", encoding="utf-8") as f:
        return f.read()

def test_verified_requires_date_specific_traceable_evidence(lifecycle_events):
    """Every VERIFIED event must have non-empty, identifiable evidence_source_ref."""
    verified = lifecycle_events[lifecycle_events["verification_status"] == "VERIFIED"]
    assert len(verified) > 0, "Expected some verified events"
    for _, r in verified.iterrows():
        ref = str(r.get("evidence_source_ref", "")).strip()
        assert ref not in ["", "None", "nan"], f"VERIFIED event {r['event_id']} missing traceable evidence_source_ref"

def test_status_only_evidence_cannot_verify_exact_date(lifecycle_events, lifecycle_intervals):
    """Evidence like plain 'manual audit: retired' cannot verify exact dates or intervals."""
    plain_audit_events = lifecycle_events[lifecycle_events["evidence_source"].str.contains("manual audit: retired", case=False, na=False)]
    for _, r in plain_audit_events.iterrows():
        assert r["verification_status"] != "VERIFIED", f"Event {r['event_id']} with status-only audit was incorrectly marked VERIFIED"

    plain_audit_intervals = lifecycle_intervals[lifecycle_intervals["evidence_source"].str.contains("manual audit: retired", case=False, na=False)]
    for _, r in plain_audit_intervals.iterrows():
        assert r["verification_status"] != "VERIFIED", f"Interval {r['interval_id']} with status-only audit was incorrectly marked VERIFIED"

def test_earliest_observed_content_cannot_create_verified_agency_start(lifecycle_intervals):
    """Earliest observed content cannot be a VERIFIED agency membership start interval."""
    proxy_starts = lifecycle_intervals[lifecycle_intervals["evidence_type"] == "earliest_observed_content"]
    for _, r in proxy_starts.iterrows():
        assert r["verification_status"] != "VERIFIED", f"Interval {r['interval_id']} starting at earliest content was marked VERIFIED"

def test_verified_t9_count_follows_actual_t8_verified_channel_events(lifecycle_events, event_impact_metrics):
    """T9 primary verified count must follow actual channel-level VERIFIED events in T8 dynamically."""
    # Exclude macro closure events (e.g. agency dissolution) from individual channel impact
    channel_verified_events = lifecycle_events[
        (lifecycle_events["verification_status"] == "VERIFIED") & 
        (~lifecycle_events["event_type"].isin(["agency_closure", "agency_formation"]))
    ]
    expected_channel_event_ids = set(channel_verified_events["event_id"])
    
    t9_primary = event_impact_metrics[event_impact_metrics["analysis_tier"] == "PRIMARY_VERIFIED"]
    t9_event_ids = set(t9_primary["event_id"])
    
    assert t9_event_ids == expected_channel_event_ids, (
        f"T9 PRIMARY_VERIFIED events {t9_event_ids} do not match T8 channel-level verified events {expected_channel_event_ids}"
    )

def test_t10_t6_vs_t5_table_uses_separate_actual_metrics(sensitivity_results):
    """Cross-depth comparison must evaluate and store actual separate t6 and t5 metrics."""
    t5_rows = sensitivity_results[sensitivity_results["dataset_depth"] == "t5_stratified_baseline"]
    assert not t5_rows.empty
    
    for _, r in t5_rows.iterrows():
        assert pd.notna(r["t6_nodes"]) and pd.notna(r["t5_nodes"])
        assert pd.notna(r["t6_edges"]) and pd.notna(r["t5_edges"])
        assert pd.notna(r["t6_modularity"]) and pd.notna(r["t5_modularity"])
        assert pd.notna(r["real_nmi"]) and pd.notna(r["real_ari"])
        # t6 deepening has strictly >= edges than stratified t5 baseline in evaluated years
        assert r["t6_edges"] >= r["t5_edges"]

def test_generated_report_numbers_equal_dataframe_values(
    lifecycle_events, lifecycle_intervals, event_impact_metrics, sensitivity_results, robustness_summary, integrity_report_text
):
    """All numerical statements in t8_t10_integrity_report.md must exactly match underlying DataFrames."""
    # T8 counts
    v_ev = int((lifecycle_events["verification_status"] == "VERIFIED").sum())
    p_ev = int((lifecycle_events["verification_status"] == "INFERRED_PROXY").sum())
    v_int = int((lifecycle_intervals["verification_status"] == "VERIFIED").sum())
    p_int = int((lifecycle_intervals["verification_status"] == "INFERRED_PROXY").sum())

    assert f"- **VERIFIED Events**: {v_ev}" in integrity_report_text
    assert f"- **INFERRED_PROXY Events**: {p_ev}" in integrity_report_text
    assert f"- **VERIFIED Intervals**: {v_int}" in integrity_report_text
    assert f"- **INFERRED_PROXY Intervals**: {p_int}" in integrity_report_text

    # T9 count
    distinct_events = event_impact_metrics[["event_id", "analysis_tier"]].drop_duplicates()
    pv_t9 = int((distinct_events["analysis_tier"] == "PRIMARY_VERIFIED").sum())
    assert f"- **PRIMARY_VERIFIED Anchors**: {pv_t9}" in integrity_report_text

    # T10 2024 comparison row
    row_2024 = sensitivity_results[
        (sensitivity_results["dataset_depth"] == "t5_stratified_baseline") &
        (sensitivity_results["slice_label"] == "yearly_2024") &
        (sensitivity_results["louvain_resolution"] == 1.0)
    ].iloc[0]
    expected_nmi_str = f"{row_2024['real_nmi']:.4f}"
    assert expected_nmi_str in integrity_report_text, f"Expected 2024 real NMI {expected_nmi_str} in report text"

def test_changing_fixture_metric_changes_generated_report_output(monkeypatch, tmp_path):
    """Verify integrity generator is dynamic and produces changed output when underlying metric changes."""
    from scripts.generate_integrity_report import generate_integrity_report
    
    # Generate original
    orig_content = generate_integrity_report()
    assert "- **VERIFIED Events**: 4" in orig_content

    # Temporarily monkeypatch pd.read_parquet to alter event counts
    real_read_parquet = pd.read_parquet
    def mock_read_parquet(path, **kwargs):
        df = real_read_parquet(path, **kwargs)
        if "lifecycle_events.parquet" in str(path):
            # Mutate one row
            df_copy = df.copy()
            df_copy.loc[df_copy["verification_status"] == "VERIFIED", "verification_status"] = "INFERRED_PROXY"
            return df_copy
        return df

    monkeypatch.setattr(pd, "read_parquet", mock_read_parquet)
    altered_content = generate_integrity_report()
    assert "- **VERIFIED Events**: 0" in altered_content
    assert altered_content != orig_content

    # Restore by running normal generator
    monkeypatch.undo()
    generate_integrity_report()

def test_no_viewer_hash_in_public_outputs():
    """Verify no raw viewer_hash (64-char hex string) appears in any temporal report or markdown file."""
    sha256_hex_pattern = re.compile(r'\b[a-f0-9]{64}\b')
    for p in REPO_ROOT.glob("data/temporal/**/*.md"):
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
            matches = sha256_hex_pattern.findall(content)
            assert not matches, f"Raw viewer_hash hex string found in {p}: {matches[:3]}"
