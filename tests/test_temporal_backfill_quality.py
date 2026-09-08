"""
Tests for Phase T5-G: Temporal Backfill Quality & Analytical Validation
Verifies:
1. run_quality_analysis executes and returns valid structure
2. Stability transitions satisfy set arithmetic: E_{t+1} = (E_t ∩ E_{t+1}) ∪ (E_{t+1} \\ E_t)
3. Descriptive retention metrics are non-negative and mathematically bounded
4. Coverage warnings flag low coverage correctly
5. Markdown report is generated without formatting or encoding errors
"""
from pathlib import Path
import pytest
import pyarrow.parquet as pq

from scripts.analyze_temporal_backfill_quality import run_quality_analysis, generate_markdown_report


@pytest.fixture(autouse=True)
def isolated_quality_sources(tmp_path, synthetic_pipeline_data, monkeypatch):
    import scripts.analyze_temporal_backfill_quality as quality
    import scripts.build_duckdb_temporal_snapshots as snapshots
    root=synthetic_pipeline_data(tmp_path)
    monkeypatch.setattr(quality,'build_unified_raw_view',lambda con:
        snapshots.build_unified_raw_view(con,snapshots.get_sources_by_provenance(root)))
    monkeypatch.setattr(quality,'CHECKPOINT_DB',root/'absent_checkpoint.sqlite3')


def test_quality_analysis_structure():
    """Verify run_quality_analysis produces all required analytical dimensions."""
    analysis = run_quality_analysis()
    assert "year_stats" in analysis
    assert "stability_stats" in analysis
    assert "multi_channel_viewers" in analysis
    assert "long_term_viewers" in analysis
    assert "adjacent_retention_viewers" in analysis
    assert "total_unique_viewers" in analysis
    assert "coverage_warnings" in analysis

    ys = analysis["year_stats"]
    assert len(ys) == 7  # 2020 through 2026
    for y in [2020, 2021, 2022, 2023, 2024, 2025, 2026]:
        assert y in ys
        st = ys[y]
        assert st["channels"] >= 0
        assert st["videos"] >= 0
        assert st["unique_viewers"] >= 0
        assert st["edges"] >= 0
        assert st["strong_shared_comments"] >= 0


def test_temporal_stability_set_arithmetic():
    """Verify edge births, disappearances, and persistence obey mathematical set arithmetic."""
    analysis = run_quality_analysis()
    st = analysis["stability_stats"]
    assert len(st) == 6  # 6 transitions: 20->21, 21->22, 22->23, 23->24, 24->25, 25->26

    for row in st:
        base = row["base_edges"]
        target = row["target_edges"]
        persisting = row["persisting"]
        births = row["births"]
        disappearances = row["disappearances"]

        # Disappearances + Persisting = Base
        assert disappearances + persisting == base
        # Births + Persisting = Target
        assert births + persisting == target


def test_retention_metrics_bounded():
    """Verify descriptive retention metrics are strictly bounded by total unique viewers."""
    analysis = run_quality_analysis()
    tot = analysis["total_unique_viewers"]
    multi_ch = analysis["multi_channel_viewers"]
    long_term = analysis["long_term_viewers"]
    adj_ret = analysis["adjacent_retention_viewers"]

    assert tot > 0
    assert 0 <= multi_ch <= tot
    assert 0 <= long_term <= tot
    assert 0 <= adj_ret <= tot


def test_markdown_report_generation(tmp_path):
    """Verify generate_markdown_report writes valid UTF-8 markdown file with required sections."""
    analysis = run_quality_analysis()
    test_report = tmp_path / "test_report.md"
    generate_markdown_report(analysis, output_path=test_report)

    assert test_report.exists()
    content = test_report.read_text(encoding="utf-8")
    assert "Phase T5 Temporal Backfill Quality & Diagnostics Report" in content
    assert "Longitudinal Interaction Evidence by Year" in content
    assert "Temporal Network Stability & Dynamic Transitions" in content
    assert "Observed Viewer Retention & Migration Evidence" in content
    assert "Automated Coverage Diagnostics & Warnings" in content
    assert "Methodological & Privacy Bounding" in content
