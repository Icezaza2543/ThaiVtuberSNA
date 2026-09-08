"""Script to generate data/temporal/research_integrity/t8_t10_integrity_report.md programmatically.

Reads committed/generated artifacts directly and outputs a rigorous summary markdown report.
"""
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "data" / "temporal" / "research_integrity"
OUTPUT_FILE = OUTPUT_DIR / "t8_t10_integrity_report.md"

def generate_integrity_report() -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load T8 Lifecycle artifacts
    events_path = REPO_ROOT / "data" / "temporal" / "lifecycle" / "lifecycle_events.parquet"
    intervals_path = REPO_ROOT / "data" / "temporal" / "lifecycle" / "channel_lifecycle_intervals.parquet"
    
    events_df = pd.read_parquet(events_path)
    intervals_df = pd.read_parquet(intervals_path)

    verified_events = int((events_df["verification_status"] == "VERIFIED").sum())
    proxy_events = int((events_df["verification_status"] == "INFERRED_PROXY").sum())
    unknown_events = int((events_df["verification_status"] == "UNKNOWN").sum())

    verified_intervals = int((intervals_df["verification_status"] == "VERIFIED").sum())
    proxy_intervals = int((intervals_df["verification_status"] == "INFERRED_PROXY").sum())
    unknown_intervals = int((intervals_df["verification_status"] == "UNKNOWN").sum())

    # 2. Load T9 Event Impact artifacts
    t9_metrics_path = REPO_ROOT / "data" / "temporal" / "event_analysis" / "event_impact_metrics.parquet"
    t9_metrics_df = pd.read_parquet(t9_metrics_path)

    # Distinct events by tier
    distinct_events = t9_metrics_df[["event_id", "channel_id", "channel_name", "event_type", "event_date", "analysis_tier", "verification_status"]].drop_duplicates()
    primary_verified_count = int((distinct_events["analysis_tier"] == "PRIMARY_VERIFIED").sum())
    exploratory_proxy_count = int((distinct_events["analysis_tier"] == "EXPLORATORY_PROXY").sum())
    # Excluded channels with zero video history from target manifest
    target_manifest = pd.read_csv(REPO_ROOT / "data" / "temporal" / "catalog" / "target_manifest.csv")
    unknown_t9_count = int(len(target_manifest) - len(distinct_events["channel_id"].unique()))

    # 3. Load T10 Robustness artifacts
    sensitivity_path = REPO_ROOT / "data" / "temporal" / "robustness" / "sensitivity_results.parquet"
    robustness_summary_path = REPO_ROOT / "data" / "temporal" / "robustness" / "robustness_summary.parquet"

    sens_df = pd.read_parquet(sensitivity_path)
    rob_summary_df = pd.read_parquet(robustness_summary_path)

    # T5 vs T6 cross-depth evaluation
    t5_rows = sens_df[sens_df["dataset_depth"] == "t5_stratified_baseline"].sort_values("slice_start")
    
    # Filter for res=1.0 yearly comparisons
    t5_yearly_res1 = t5_rows[(t5_rows["louvain_resolution"] == 1.0) & (t5_rows["slice_type"] == "yearly")]
    
    # Modality comparison (2026 yearly at res=1.0, threshold=1, t6_canonical)
    ev_2026 = sens_df[
        (sens_df["slice_label"] == "yearly_2026") &
        (sens_df["edge_threshold"] == 1) &
        (sens_df["louvain_resolution"] == 1.0) &
        (sens_df["dataset_depth"] == "t6_canonical")
    ].sort_values("evidence_mode")
    comm_row = ev_2026[ev_2026["evidence_mode"] == "comment_only"]
    uni_row = ev_2026[ev_2026["evidence_mode"] == "unified"]

    comm_nodes = int(comm_row["active_nodes"].iloc[0]) if not comm_row.empty else 0
    comm_edges = int(comm_row["active_edges"].iloc[0]) if not comm_row.empty else 0
    comm_q = float(comm_row["modularity_q"].iloc[0]) if not comm_row.empty else 0.0
    comm_nmi = float(comm_row["nmi_to_baseline"].iloc[0]) if not comm_row.empty else 0.0
    comm_ari = float(comm_row["ari_to_baseline"].iloc[0]) if not comm_row.empty else 0.0

    uni_nodes = int(uni_row["active_nodes"].iloc[0]) if not uni_row.empty else 0
    uni_edges = int(uni_row["active_edges"].iloc[0]) if not uni_row.empty else 0
    uni_q = float(uni_row["modularity_q"].iloc[0]) if not uni_row.empty else 0.0
    uni_nmi = float(uni_row["nmi_to_baseline"].iloc[0]) if not uni_row.empty else 0.0
    uni_ari = float(uni_row["ari_to_baseline"].iloc[0]) if not uni_row.empty else 0.0

    # Build report content
    lines = []
    lines.append("# Research Integrity Verification Report: T8–T10")
    lines.append("")
    lines.append("This report is programmatically generated from committed analytical artifacts to verify evidence traceability and analytical consistency across Phases T8, T9, and T10.")
    lines.append("")
    lines.append("## 1. T8 Lifecycle Evidence Tier Breakdown")
    lines.append("")
    lines.append("### Historical Events Breakdown")
    lines.append(f"- **VERIFIED Events**: {verified_events}")
    lines.append(f"- **INFERRED_PROXY Events**: {proxy_events}")
    lines.append(f"- **UNKNOWN Events**: {unknown_events}")
    lines.append(f"- **Total Lifecycle Events**: {len(events_df)}")
    lines.append("")
    lines.append("### Channel Historical Intervals Breakdown")
    lines.append(f"- **VERIFIED Intervals**: {verified_intervals}")
    lines.append(f"- **INFERRED_PROXY Intervals**: {proxy_intervals}")
    lines.append(f"- **UNKNOWN Intervals**: {unknown_intervals}")
    lines.append(f"- **Total Historical Intervals**: {len(intervals_df)}")
    lines.append("")
    lines.append("## 2. T9 Event Impact Cohort Separation")
    lines.append("")
    lines.append(f"- **PRIMARY_VERIFIED Anchors**: {primary_verified_count}")
    lines.append(f"- **EXPLORATORY_PROXY Events**: {exploratory_proxy_count}")
    lines.append(f"- **UNKNOWN Events**: {unknown_t9_count}")
    lines.append(f"- **Total Evaluated Event Cohorts**: {len(distinct_events)}")
    lines.append("")
    lines.append("### Primary Verified Impact Details (+/- 90-Day Window)")
    lines.append("| Event ID | Channel Name | Event Type | Event Date | Pre Viewers | Post Viewers | Focal Retention Rate | Evidence Status |")
    lines.append("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |")
    pv_rows = t9_metrics_df[(t9_metrics_df["analysis_tier"] == "PRIMARY_VERIFIED") & (t9_metrics_df["window_days"] == 90)]
    for _, r in pv_rows.iterrows():
        lines.append(
            f"| `{r['event_id']}` | {r['channel_name']} | {r['event_type']} | {r['event_date']} | "
            f"{r['pre_focal_viewers']} | {r['post_focal_viewers']} | {r['focal_retention_rate']:.1%} | `{r['evidence_status']}` |"
        )
    lines.append("")
    lines.append("## 3. T10 Cross-Depth Partition Metrics (T5 Stratified Baseline vs T6 Deepened)")
    lines.append("")
    lines.append("| Year | T6 Nodes | T5 Nodes | Common Nodes | T6 Edges | T5 Edges | T6 Modularity ($Q$) | T5 Modularity ($Q$) | Real NMI | Real ARI |")
    lines.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for _, r in t5_yearly_res1.iterrows():
        t6_n = int(r["t6_nodes"])
        t5_n = int(r["t5_nodes"])
        c_n = int(r["common_nodes"])
        t6_e = int(r["t6_edges"])
        t5_e = int(r["t5_edges"])
        lines.append(
            f"| {r['slice_start'][:4]} | {t6_n} | {t5_n} | {c_n} | {t6_e} | {t5_e} | "
            f"{r['t6_modularity']:.4f} | {r['t5_modularity']:.4f} | {r['real_nmi']:.4f} | {r['real_ari']:.4f} |"
        )
    lines.append("")
    lines.append("## 4. T10 Modality Invariance Metrics (Year 2026)")
    lines.append("")
    lines.append("| Modality | Active Nodes | Active Edges | Modularity ($Q$) | NMI to Unified Baseline | ARI to Unified Baseline |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    lines.append(f"| `comment_only` | {comm_nodes} | {comm_edges} | {comm_q:.4f} | {comm_nmi:.4f} | {comm_ari:.4f} |")
    lines.append(f"| `unified` | {uni_nodes} | {uni_edges} | {uni_q:.4f} | {uni_nmi:.4f} | {uni_ari:.4f} |")
    lines.append("")
    lines.append("## 5. T10 Rule-Derived Robustness Classifications")
    lines.append("")
    lines.append("| Finding ID | Domain | Metric | Measured Value | Classification | Rule Basis |")
    lines.append("| :--- | :--- | :--- | :---: | :--- | :--- |")
    for _, r in rob_summary_df.iterrows():
        lines.append(
            f"| `{r['finding_id']}` | {r['research_domain']} | {r['measured_metric_name']} | "
            f"{r['measured_metric_value']:.4f} | `{r['classification']}` | {r['deterministic_rule_basis']} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("*Report generated automatically by `scripts/generate_integrity_report.py`.*")
    lines.append("")

    content = "\n".join(lines)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    
    return content

if __name__ == "__main__":
    content = generate_integrity_report()
    print(f"Generated integrity report at {OUTPUT_FILE}")
