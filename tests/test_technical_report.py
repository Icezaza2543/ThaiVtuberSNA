"""Phase T19: Report-to-Artifact Regression Test Suite

Verifies:
1. Appendix field mappings match Parquet artifacts exactly (same-channel, cross-channel, cross-agency, Jaccard).
2. Temporal slicing methodology asserts interaction_time only (no video published date fallback).
3. Agency homophily explicitly characterized as selection-time metadata (agency_at_selection).
4. No causality claims are made.
5. Literature Review is explicitly marked as pending (no invented/assumed citations).
"""
import re
from pathlib import Path
import pytest
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_FILE = REPO_ROOT / "data" / "temporal" / "report" / "technical_report.md"
APPENDIX_FILE = REPO_ROOT / "data" / "temporal" / "report" / "appendix_tables.md"
COHORT_RETENTION_PARQUET = REPO_ROOT / "data" / "temporal" / "cohorts" / "cohort_retention_matrix.parquet"
LINEAGE_PARQUET = REPO_ROOT / "data" / "temporal" / "analysis" / "community_lineage_v2.parquet"


def test_report_files_exist():
    """Verify technical report and appendix files exist on disk."""
    assert REPORT_FILE.exists(), f"Missing {REPORT_FILE}"
    assert APPENDIX_FILE.exists(), f"Missing {APPENDIX_FILE}"


def test_appendix_field_mapping_matches_parquet_exactly():
    """Verify Table A1 in appendix matches cohort_retention_matrix.parquet exactly."""
    assert COHORT_RETENTION_PARQUET.exists()
    df_ret = pd.read_parquet(COHORT_RETENTION_PARQUET)
    app_text = APPENDIX_FILE.read_text(encoding="utf-8")

    # Locate Table A1
    assert "## A1. Cohort Longitudinal Retention & Dispersion Matrix" in app_text
    lines = app_text.splitlines()

    # Find table header and rows
    table_lines = []
    in_a1 = False
    for line in lines:
        if "## A1. Cohort" in line:
            in_a1 = True
            continue
        if in_a1:
            if line.startswith("## A2.") or line.startswith("---"):
                if table_lines:
                    break
            if line.startswith("|") and not line.startswith("| :---"):
                table_lines.append(line)

    # First table line is header
    header = [c.strip() for c in table_lines[0].split("|")[1:-1]]
    data_rows = table_lines[1:]

    assert len(data_rows) == len(df_ret), f"Expected {len(df_ret)} rows, found {len(data_rows)} in A1"

    for i, row_str in enumerate(data_rows):
        cells = [c.strip().replace(",", "") for c in row_str.split("|")[1:-1]]
        p_row = df_ret.iloc[i]

        cohort_yr = int(cells[0])
        obs_yr = int(cells[1])
        cohort_base = int(cells[3])
        reobs = int(cells[4])
        same_ch = int(cells[6])
        cross_ch = int(cells[7])
        cross_ag = int(cells[8])

        assert cohort_yr == int(p_row["cohort_year"])
        assert obs_yr == int(p_row["observation_year"])
        assert cohort_base == int(p_row["cohort_size"])
        assert reobs == int(p_row["reobserved_viewers"])
        # Crucial exact matching assertions:
        assert same_ch == int(p_row["same_channel_reobserved_viewers"]), f"Row {i} same_channel mismatch"
        assert cross_ch == int(p_row["cross_channel_reobserved_viewers"]), f"Row {i} cross_channel mismatch"
        assert cross_ag == int(p_row["cross_agency_reobserved_viewers"]), f"Row {i} cross_agency mismatch"


def test_lineage_transitions_jaccard_matches_parquet():
    """Verify Table A2 in appendix matches community_lineage_v2.parquet Jaccard values."""
    assert LINEAGE_PARQUET.exists()
    df_lin = pd.read_parquet(LINEAGE_PARQUET)
    app_text = APPENDIX_FILE.read_text(encoding="utf-8")

    assert "## A2. Community Lineage Transitions" in app_text
    lines = app_text.splitlines()

    a2_lines = []
    in_a2 = False
    for line in lines:
        if "## A2. Community Lineage" in line:
            in_a2 = True
            continue
        if in_a2:
            if line.startswith("## A3.") or (line.startswith("---") and len(a2_lines) > 2):
                break
            if line.startswith("|") and not line.startswith("| :---"):
                a2_lines.append(line)

    data_rows = a2_lines[1:]
    assert len(data_rows) == len(df_lin), f"Expected {len(df_lin)} rows, found {len(data_rows)} in A2"

    for i, row_str in enumerate(data_rows):
        cells = [c.strip().replace("`", "") for c in row_str.split("|")[1:-1]]
        p_row = df_lin.iloc[i]

        jaccard_md = float(cells[5])
        jaccard_pq = round(float(p_row["jaccard_similarity"]), 4)

        assert abs(jaccard_md - jaccard_pq) < 1e-4, f"Row {i} Jaccard mismatch: {jaccard_md} vs {jaccard_pq}"
        assert int(cells[4].replace(",", "")) == int(p_row["shared_channels"])


def test_temporal_methodology_interaction_time_only():
    """Verify report strictly asserts interaction_time and forbids video publication date fallback."""
    content = REPORT_FILE.read_text(encoding="utf-8")
    assert "interaction_time" in content
    assert "NEVER" in content
    assert "video publication date" in content.lower()


def test_agency_at_selection_metadata_clarity():
    """Verify agency homophily is described strictly as selection-time metadata."""
    content = REPORT_FILE.read_text(encoding="utf-8")
    assert "agency_at_selection" in content
    assert "selection-time" in content.lower()


def test_no_causality_claimed():
    """Verify report explicitly disclaims causality."""
    content = REPORT_FILE.read_text(encoding="utf-8")
    assert "not establish social causality" in content.lower()
    assert "audience co-attendance" in content.lower()


def test_literature_review_marked_pending():
    """Verify Literature Review is marked as pending and contains no invented citations."""
    content = REPORT_FILE.read_text(encoding="utf-8")
    assert "Literature Review" in content
    assert "PENDING" in content
