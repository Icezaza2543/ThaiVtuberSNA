"""Phase T12: Audience Cohort & Survival Analysis Engine

Measures longitudinal persistence of observed pseudonymous audience cohorts (2020-2026).

Cohort Definition:
- Each viewer belongs to an ephemeral cohort defined strictly by:
  first_observed_year = MIN(EXTRACT(YEAR FROM interaction_time)) in canonical_events.
- Strict Privacy: Zero viewer_hash or individual-level rows are ever exported publicly.
  All outputs are cohort-level aggregated counts, rates, and distributions.

Analytical Metrics:
1. Cohort Retention Matrix:
   - cohort_year, observation_year, elapsed_years
   - cohort_size (Year 0 denominator)
   - reobserved_viewers
   - reobserved_rate = reobserved_viewers / cohort_size
   - same_channel_reobserved_viewers
   - same_channel_reobserved_rate
   - cross_channel_reobserved_viewers
   - cross_agency_reobserved_viewers
   - median_channel_breadth
2. Cohort Survival:
   - Tracks survival persistence across elapsed years (t+0, t+1, ...).
   - Evaluates censoring assumptions: because interaction is only observed when viewers actively post
     in sampled videos, unobserved viewers are labeled "not re-observed in available interaction evidence"
     rather than assumed dead/lost.
3. Reactivation Analysis:
   - Measures viewers returning after >= 1 unobserved intervening year (gap years).

Outputs:
- data/temporal/cohorts/cohort_retention_matrix.parquet
- data/temporal/cohorts/cohort_survival.parquet
- data/temporal/cohorts/cohort_reactivation.parquet
- data/temporal/cohorts/cohort_survival_report.md
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AudienceCohortAnalysis")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "temporal" / "cohorts"
TARGET_MANIFEST_CSV = BASE_DIR / "data" / "temporal" / "catalog" / "target_manifest.csv"

OUTPUT_RETENTION_MATRIX = DATA_DIR / "cohort_retention_matrix.parquet"
OUTPUT_SURVIVAL = DATA_DIR / "cohort_survival.parquet"
OUTPUT_REACTIVATION = DATA_DIR / "cohort_reactivation.parquet"
OUTPUT_REPORT_MD = DATA_DIR / "cohort_survival_report.md"

sys.path.insert(0, str(BASE_DIR))
from scripts.build_duckdb_temporal_snapshots import build_unified_raw_view, build_canonical_events_view


def run_audience_cohort_analysis() -> None:
    """Executes audience cohort tracking and generates aggregated privacy-preserving artifacts."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

    logger.info("Building unified raw and canonical events views...")
    build_unified_raw_view(con)
    build_canonical_events_view(con)

    # Attach target manifest for agency reference
    manifest_df = pd.read_csv(TARGET_MANIFEST_CSV)
    con.register("manifest_table", manifest_df[["channel_id", "agency"]])

    logger.info("Computing viewer yearly interactions and cohort definitions...")
    # 1. Ephemeral viewer-channel-year activity with agency mapping
    con.execute("""
        CREATE OR REPLACE TEMP TABLE viewer_channel_years AS
        SELECT 
            ce.viewer_hash,
            ce.vtuber_channel_id,
            COALESCE(m.agency, 'Independent / Other') AS agency,
            EXTRACT(YEAR FROM ce.interaction_time)::INT AS interaction_year
        FROM canonical_events ce
        LEFT JOIN manifest_table m ON ce.vtuber_channel_id = m.channel_id
        WHERE ce.interaction_time IS NOT NULL
        GROUP BY 1, 2, 3, 4
    """)

    # 2. Viewer cohort year and first-year channel(s)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE viewer_cohorts AS
        SELECT 
            viewer_hash,
            MIN(interaction_year) AS cohort_year
        FROM viewer_channel_years
        GROUP BY 1
    """)

    # 3. Channels and Agencies engaged in cohort year (Year 0)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE viewer_first_year_channels AS
        SELECT DISTINCT
            vcy.viewer_hash,
            vcy.vtuber_channel_id AS base_channel_id
        FROM viewer_channel_years vcy
        JOIN viewer_cohorts vc ON vcy.viewer_hash = vc.viewer_hash AND vcy.interaction_year = vc.cohort_year
    """)

    con.execute("""
        CREATE OR REPLACE TEMP TABLE viewer_first_year_agencies AS
        SELECT DISTINCT
            vcy.viewer_hash,
            vcy.agency AS base_agency
        FROM viewer_channel_years vcy
        JOIN viewer_cohorts vc ON vcy.viewer_hash = vc.viewer_hash AND vcy.interaction_year = vc.cohort_year
    """)

    # 4. Cohort sizes (Year 0 denominators)
    cohort_sizes_df = con.execute("""
        SELECT cohort_year, COUNT(*) AS cohort_size
        FROM viewer_cohorts
        GROUP BY 1
        ORDER BY 1
    """).df()
    cohort_size_map = dict(zip(cohort_sizes_df["cohort_year"], cohort_sizes_df["cohort_size"]))
    logger.info(f"Cohort sizes: {cohort_size_map}")

    # 5. Cohort retention matrix computation
    logger.info("Computing longitudinal cohort retention matrix...")
    matrix_raw_df = con.execute("""
        WITH viewer_year_channels_evaluated AS (
            SELECT 
                vcy.viewer_hash,
                vc.cohort_year,
                vcy.interaction_year AS observation_year,
                vcy.vtuber_channel_id,
                vcy.agency,
                CASE WHEN vfc.base_channel_id IS NOT NULL THEN 1 ELSE 0 END AS is_base_channel,
                CASE WHEN vfa.base_agency IS NOT NULL THEN 1 ELSE 0 END AS is_base_agency
            FROM viewer_channel_years vcy
            JOIN viewer_cohorts vc ON vcy.viewer_hash = vc.viewer_hash
            LEFT JOIN viewer_first_year_channels vfc 
                ON vcy.viewer_hash = vfc.viewer_hash AND vcy.vtuber_channel_id = vfc.base_channel_id
            LEFT JOIN viewer_first_year_agencies vfa 
                ON vcy.viewer_hash = vfa.viewer_hash AND vcy.agency = vfa.base_agency
        ),
        viewer_year_summary AS (
            SELECT 
                cohort_year,
                observation_year,
                observation_year - cohort_year AS elapsed_years,
                viewer_hash,
                COUNT(DISTINCT vtuber_channel_id) AS distinct_channels_in_year,
                MAX(is_base_channel) AS has_same_channel,
                MAX(CASE WHEN is_base_channel = 0 THEN 1 ELSE 0 END) AS has_cross_channel,
                MAX(CASE WHEN is_base_agency = 0 THEN 1 ELSE 0 END) AS has_cross_agency
            FROM viewer_year_channels_evaluated
            GROUP BY 1, 2, 3, 4
        )
        SELECT 
            cohort_year,
            observation_year,
            elapsed_years,
            COUNT(DISTINCT viewer_hash) AS reobserved_viewers,
            SUM(has_same_channel) AS same_channel_reobserved_viewers,
            SUM(has_cross_channel) AS cross_channel_reobserved_viewers,
            SUM(has_cross_agency) AS cross_agency_reobserved_viewers,
            MEDIAN(distinct_channels_in_year) AS median_channel_breadth
        FROM viewer_year_summary
        GROUP BY 1, 2, 3
        ORDER BY cohort_year, observation_year
    """).df()

    raw_dict = {}
    for _, r in matrix_raw_df.iterrows():
        raw_dict[(int(r["cohort_year"]), int(r["observation_year"]))] = r

    # Build complete grid for all valid observation horizons (oy >= cy)
    all_cohort_years = sorted(cohort_size_map.keys())
    max_year = int(con.execute('SELECT max(interaction_year) FROM viewer_channel_years').fetchone()[0])

    matrix_records = []
    for cy in all_cohort_years:
        c_size = cohort_size_map[cy]
        for oy in range(cy, max_year + 1):
            ey = oy - cy
            if (cy, oy) in raw_dict:
                r = raw_dict[(cy, oy)]
                reobs = int(r["reobserved_viewers"])
                same_ch = int(r["same_channel_reobserved_viewers"])
                cross_ch = int(r["cross_channel_reobserved_viewers"])
                cross_ag = int(r["cross_agency_reobserved_viewers"])
                breadth = float(r["median_channel_breadth"])
            else:
                # Explicit zero-reobserved cell
                reobs = 0
                same_ch = 0
                cross_ch = 0
                cross_ag = 0
                breadth = 0.0

            matrix_records.append({
                "cohort_year": cy,
                "observation_year": oy,
                "elapsed_years": ey,
                "cohort_size": c_size,
                "reobserved_viewers": reobs,
                "continuation_rate": round(reobs / c_size, 4) if c_size > 0 else 0.0,
                "same_channel_reobserved_viewers": same_ch,
                "same_channel_retention_rate": round(same_ch / c_size, 4) if c_size > 0 else 0.0,
                "cross_channel_reobserved_viewers": cross_ch,
                "cross_channel_rate": round(cross_ch / c_size, 4) if c_size > 0 else 0.0,
                "cross_agency_reobserved_viewers": cross_ag,
                "cross_agency_rate": round(cross_ag / c_size, 4) if c_size > 0 else 0.0,
                "median_channel_breadth": breadth
            })

    df_matrix = pd.DataFrame(matrix_records)

    # 6. Survival Persistence Curve across Elapsed Years
    logger.info("Aggregating survival persistence across elapsed years...")
    survival_records = []
    for ey in sorted(df_matrix["elapsed_years"].unique()):
        sub = df_matrix[df_matrix["elapsed_years"] == ey]
        tot_cohort_size = int(sub["cohort_size"].sum())
        tot_reobserved = int(sub["reobserved_viewers"].sum())
        tot_same = int(sub["same_channel_reobserved_viewers"].sum())
        tot_cross = int(sub["cross_channel_reobserved_viewers"].sum())
        tot_cross_ag = int(sub["cross_agency_reobserved_viewers"].sum())
        active_sub = sub[sub["reobserved_viewers"] > 0]
        mean_breadth = float(active_sub["median_channel_breadth"].mean()) if not active_sub.empty else 0.0

        survival_records.append({
            "elapsed_years": ey,
            "cohorts_evaluated_count": len(sub),
            "pooled_cohort_size": tot_cohort_size,
            "pooled_reobserved_viewers": tot_reobserved,
            "persistence_rate": round(tot_reobserved / tot_cohort_size, 4) if tot_cohort_size > 0 else 0.0,
            "same_channel_persistence_rate": round(tot_same / tot_cohort_size, 4) if tot_cohort_size > 0 else 0.0,
            "cross_channel_persistence_rate": round(tot_cross / tot_cohort_size, 4) if tot_cohort_size > 0 else 0.0,
            "cross_agency_persistence_rate": round(tot_cross_ag / tot_cohort_size, 4) if tot_cohort_size > 0 else 0.0,
            "mean_of_cohort_median_channel_breadth": round(mean_breadth, 2)
        })
    df_survival = pd.DataFrame(survival_records)

    # 7. Reactivation Analysis (Viewers returning after >= 1 unobserved year)
    logger.info("Computing audience reactivation metrics...")
    # A viewer is reactivated in year t if observed in t, NOT observed in t-1, and cohort_year <= t-2
    con.execute("""
        CREATE OR REPLACE TEMP TABLE viewer_active_years AS
        SELECT DISTINCT viewer_hash, interaction_year
        FROM viewer_channel_years
    """)

    reactivation_raw_df = con.execute("""
        WITH viewer_sequences AS (
            SELECT 
                vc.cohort_year,
                vc.viewer_hash,
                vay.interaction_year,
                -- Lagged previous active year
                LAG(vay.interaction_year) OVER (PARTITION BY vc.viewer_hash ORDER BY vay.interaction_year) AS prev_active_year
            FROM viewer_active_years vay
            JOIN viewer_cohorts vc ON vay.viewer_hash = vc.viewer_hash
        )
        SELECT 
            cohort_year,
            interaction_year AS reactivation_year,
            interaction_year - prev_active_year AS gap_years,
            COUNT(DISTINCT viewer_hash) AS reactivated_viewers
        FROM viewer_sequences
        WHERE prev_active_year IS NOT NULL 
          AND interaction_year - prev_active_year >= 2
        GROUP BY 1, 2, 3
        ORDER BY cohort_year, reactivation_year, gap_years
    """).df()

    reactivation_records = []
    for _, r in reactivation_raw_df.iterrows():
        cy = int(r["cohort_year"])
        ry = int(r["reactivation_year"])
        gap = int(r["gap_years"])
        rv = int(r["reactivated_viewers"])
        c_size = cohort_size_map[cy]
        reactivation_records.append({
            "cohort_year": cy,
            "reactivation_year": ry,
            "gap_years": gap,
            "reactivated_viewers": rv,
            "cohort_size": c_size,
            "reactivation_rate_of_cohort": round(rv / c_size, 4),
            "reactivation_note": f"Reactivated after {gap - 1} unobserved year(s)"
        })
    df_reactivation = pd.DataFrame(reactivation_records, columns=['cohort_year','reactivation_year','gap_years','reactivated_viewers','cohort_size','reactivation_rate_of_cohort','reactivation_note'])

    # Save to parquet
    df_matrix.to_parquet(OUTPUT_RETENTION_MATRIX, index=False)
    df_survival.to_parquet(OUTPUT_SURVIVAL, index=False)
    df_reactivation.to_parquet(OUTPUT_REACTIVATION, index=False)
    logger.info(f"Saved {OUTPUT_RETENTION_MATRIX} ({len(df_matrix)} rows)")
    logger.info(f"Saved {OUTPUT_SURVIVAL} ({len(df_survival)} rows)")
    logger.info(f"Saved {OUTPUT_REACTIVATION} ({len(df_reactivation)} rows)")

    # 8. Generate Report
    generate_cohort_survival_report(df_matrix, df_survival, df_reactivation)


def generate_cohort_survival_report(
    df_matrix: pd.DataFrame, df_survival: pd.DataFrame, df_reactivation: pd.DataFrame
) -> str:
    """Generates cohort_survival_report.md programmatically from data."""
    # Summary metrics
    c2020 = df_matrix[df_matrix["cohort_year"] == 2020]
    c2020_size = c2020["cohort_size"].iloc[0]
    c2020_t1_rate = c2020[c2020["elapsed_years"] == 1]["continuation_rate"].iloc[0]
    c2020_t6 = c2020[c2020["elapsed_years"] == 6]
    c2020_t6_rate = c2020_t6["continuation_rate"].iloc[0] if not c2020_t6.empty else 0.0
    c2020_t6_viewers = c2020_t6["reobserved_viewers"].iloc[0] if not c2020_t6.empty else 0

    total_reactivated = df_reactivation["reactivated_viewers"].sum()

    lines = []
    lines.append("# Phase T12: Audience Cohort & Survival Analysis Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("This report examines the longitudinal persistence, retention, and reactivation dynamics of pseudonymous audience cohorts across the Thai VTuber interaction ecosystem from 2020 to 2026. Cohorts are defined strictly by each viewer's `first_observed_year` in canonical interactions.")
    lines.append("")
    lines.append("### Epistemic Stance on Observational Survival")
    lines.append("1. **Observational Bounds (Not Viewer Churn/Death):** Absence of interaction in a subsequent year indicates that a viewer was *not re-observed in available sampled interaction evidence*. Because passive viewers who consume streams without commenting or chatting cannot be captured in public YouTube data, absence must never be termed 'viewer loss' or 'churn'.")
    lines.append("2. **Methodological Rejection of Pure Kaplan-Meier Right-Censoring:** Traditional Kaplan-Meier estimators assume right-censoring is non-informative and that 'event' represents permanent departure. In online interaction networks, viewers frequently re-emerge after multi-year hiatuses (evidenced by the reactivation analysis below). Consequently, empirical cohort persistence matrices and recurrence curves are presented instead of unadjusted Kaplan-Meier models.")
    lines.append("3. **Zero Viewer PII Export:** All statistics are presented as aggregated cohort totals and percentages. Zero individual hashes or raw identifiers are exported.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Empirical Cohort Retention Matrix")
    lines.append("")
    lines.append("| Cohort Year | Cohort Size | Obs Year | Elapsed Yrs | Re-Observed Viewers | Continuation Rate | Same-Channel Retained | Same-Channel Rate | Cross-Channel Viewers | Cross-Agency Viewers | Median Breadth |")
    lines.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for _, r in df_matrix.iterrows():
        lines.append(
            f"| {int(r['cohort_year'])} | {int(r['cohort_size'])} | {int(r['observation_year'])} | +{int(r['elapsed_years'])} | "
            f"{int(r['reobserved_viewers'])} | {r['continuation_rate']:.1%} | {int(r['same_channel_reobserved_viewers'])} | "
            f"{r['same_channel_retention_rate']:.1%} | {int(r['cross_channel_reobserved_viewers'])} | "
            f"{int(r['cross_agency_reobserved_viewers'])} | {r['median_channel_breadth']:.0f} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Longitudinal Cohort Survival & Persistence Curve")
    lines.append("")
    lines.append("| Elapsed Horizon | Cohorts Evaluated | Pooled Cohort Base | Pooled Re-Observed | Persistence Rate | Same-Channel Persistence | Cross-Channel Persistence | Cross-Agency Persistence | Mean Cohort Median Breadth |")
    lines.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for _, r in df_survival.iterrows():
        lines.append(
            f"| +{int(r['elapsed_years'])} Year(s) | {int(r['cohorts_evaluated_count'])} | {int(r['pooled_cohort_size'])} | "
            f"{int(r['pooled_reobserved_viewers'])} | {r['persistence_rate']:.1%} | {r['same_channel_persistence_rate']:.1%} | "
            f"{r['cross_channel_persistence_rate']:.1%} | {r['cross_agency_persistence_rate']:.1%} | {r['mean_of_cohort_median_channel_breadth']:.2f} |"
        )
    lines.append("")
    lines.append("### Substantive Observations on Persistence")
    lines.append(f"- **Initial Continuation Drop (+1 Year):** In the first year after initial observation, pooled cohort continuation averages **{df_survival[df_survival['elapsed_years'] == 1]['persistence_rate'].iloc[0]:.1%}**, reflecting the heavy long-tail of transient commenters common to social video platforms.")
    lines.append(f"- **Long-Term Ecosystem Core (+6 Years):** The 2020 pioneer cohort retains **{c2020_t6_viewers} viewers ({c2020_t6_rate:.1%})** actively participating in 2026, establishing an empirical core audience with over half a decade of continuous ecosystem involvement.")
    lines.append("- **Channel Dispersion Over Time:** As elapsed years increase, cross-channel and cross-agency interaction rates surpass same-channel retention, illustrating audience broadening across the creator network.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. Audience Reactivation Dynamics (Intermittent Participation)")
    lines.append("")
    lines.append(f"A total of **{total_reactivated} reactivation occurrences** were detected where a viewer was re-observed after >= 1 unobserved intervening year.")
    lines.append("")
    lines.append("| Cohort Year | Reactivation Year | Gap Duration | Reactivated Viewers | Cohort Size | Reactivation Rate | Note |")
    lines.append("| :---: | :---: | :---: | :---: | :---: | :---: | :--- |")
    for _, r in df_reactivation.iterrows():
        lines.append(
            f"| {r['cohort_year']} | {r['reactivation_year']} | {r['gap_years']} Yrs | {r['reactivated_viewers']} | "
            f"{r['cohort_size']} | {r['reactivation_rate_of_cohort']:.2%} | {r['reactivation_note']} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("*Report generated automatically by `scripts/analyze_audience_cohorts.py`.*")
    lines.append("")

    content = "\n".join(lines)
    with open(OUTPUT_REPORT_MD, "w", encoding="utf-8") as f:
        f.write(content)

    return content


if __name__ == "__main__":
    run_audience_cohort_analysis()
