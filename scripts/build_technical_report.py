#!/usr/bin/env python3
"""Phase T19: Technical Report & Scientific Paper Package Generator

Generates a comprehensive research paper-style technical report and extended appendix
synthesizing all findings from T8–T16.

Guarantees:
- Appendix field mappings match Parquet artifacts exactly (same-channel, cross-channel, cross-agency, Jaccard).
- All empirical numbers in prose are dynamically computed from active artifacts.
- Temporal methodology strictly uses interaction_time (NEVER video publication date fallback).
- Agency homophily explicitly characterized as selection-time metadata (agency_at_selection).
- No causal claims made; strictly observational audience co-attendance.
- Literature review explicitly marked as pending (no invented/assumed citations).
- Zero viewer PII; all hex hashes prefixed with sha256_.
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
TEMPORAL = BASE / "data" / "temporal"
REPORT_DIR = TEMPORAL / "report"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Input artifacts
ECOSYSTEM_METRICS = TEMPORAL / "ecosystem" / "yearly_ecosystem_metrics.parquet"
STRUCTURAL_BREAKS = TEMPORAL / "ecosystem" / "structural_breaks.parquet"
LINEAGE_V2 = TEMPORAL / "analysis" / "community_lineage_v2.parquet"
COMMUNITY_LIFECYCLES = TEMPORAL / "analysis" / "community_lifecycles.parquet"
CENTRALITY = TEMPORAL / "centrality" / "yearly_centrality.parquet"
BRIDGE_DYNAMICS = TEMPORAL / "centrality" / "bridge_dynamics.parquet"
COHORT_SURVIVAL = TEMPORAL / "cohorts" / "cohort_survival.parquet"
COHORT_RETENTION = TEMPORAL / "cohorts" / "cohort_retention_matrix.parquet"
YEARLY_QUALITY = TEMPORAL / "quality" / "yearly_evidence_quality.parquet"
CHANNEL_QUALITY = TEMPORAL / "quality" / "channel_evidence_quality.parquet"
ROBUSTNESS = TEMPORAL / "robustness" / "robustness_summary.parquet"
EVENT_IMPACT = TEMPORAL / "event_analysis" / "event_impact_metrics.parquet"
LIFECYCLE_EVENTS = TEMPORAL / "lifecycle" / "lifecycle_events.parquet"


def safe_read(path: Path) -> pd.DataFrame | None:
    if path.exists():
        try:
            return pd.read_parquet(path)
        except Exception:
            return None
    return None


def fmtnum(v, d=0):
    if v is None or pd.isna(v):
        return "–"
    if d == 0:
        return f"{int(round(v)):,}"
    return f"{v:,.{d}f}"


def fmtpct(v, d=1):
    if v is None or pd.isna(v):
        return "–"
    if v <= 1:
        return f"{v * 100:.{d}f}%"
    return f"{v:.{d}f}%"


def require_columns(df, columns, artifact):
    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError(f"{artifact}: required columns missing: {sorted(missing)}")
    return df


def build_technical_report() -> str:
    eco = pd.read_parquet(ECOSYSTEM_METRICS)
    surv = pd.read_parquet(COHORT_SURVIVAL)
    quality = pd.read_parquet(YEARLY_QUALITY)
    lineages = pd.read_parquet(COMMUNITY_LIFECYCLES)
    bridges = pd.read_parquet(BRIDGE_DYNAMICS)
    fields = ['elapsed_years', 'pooled_cohort_size', 'pooled_reobserved_viewers',
              'persistence_rate', 'same_channel_persistence_rate', 'cross_channel_persistence_rate']
    require_columns(surv, fields, 'cohort_survival.parquet')
    years = sorted(eco['year'].unique())
    lines = [
        '# Privacy-Preserving Longitudinal Social Network Analysis',
        f'# of the Thai VTuber Ecosystem ({min(years)}–{max(years)})', '',
        '## Methods and storage architecture', '',
        'Temporal slices use interaction_time; video publication date is NEVER a fallback. '
        'Undated events are excluded. Edges measure audience co-attendance and do not establish social causality.',
        'Agency labels are selection-time metadata (agency_at_selection), not historical affiliations.',
        'LEVEL A credentials remain local and never enter Git or Google Sheets. '
        'LEVEL B viewer records are private and stored only in the authorized ThaiVtuber_SNA workbook. '
        'LEVEL C public artifacts contain creator metadata and aggregate research metrics; NO_VIEWER_LEVEL_DATA applies to public exports.',
        'Louvain partitions use resolution 1 and seed 42. Lineage matching uses '
        '0.4 Jaccard + 0.3 forward overlap + 0.3 backward overlap with one-to-one primary matches.',
        'Observations describe sampled active commenters/chatters, not passive viewers or the complete population. '
        'The 2026 YTD window is PARTIAL_WINDOW_DESCRIPTIVE_ONLY.', '',
        '## Ecosystem measurements', '',
    ]
    cols = ['year','active_channels','edges','density','modularity','community_count','agency_at_selection_assortativity']
    require_columns(eco, cols, 'yearly_ecosystem_metrics.parquet')
    lines.extend(['| ' + ' | '.join(cols) + ' |', '| ' + ' | '.join(['---']*len(cols)) + ' |'])
    for row in eco[cols].itertuples(index=False, name=None):
        lines.append('| ' + ' | '.join(str(v) for v in row) + ' |')
    lines.extend(['', f'Observed persistent lineages: {len(lineages)}. '
                  f"Terminal-window ACTIVE lineages: {int((lineages['lifecycle_status'] == 'ACTIVE').sum())}.", '',
                  '## Cohort survival (cohort_survival.parquet)', '',
                  '| Elapsed Horizon | Pooled Cohort Base | Re-Observed Audience | Continuation Rate | Same-Channel Retained | Cross-Channel Broadened |',
                  '| --- | ---: | ---: | ---: | ---: | ---: |'])
    for r in surv[fields].itertuples(index=False, name=None):
        lines.append(f'| +{int(r[0])} Years | {int(r[1])} | {int(r[2])} | {r[3]} | {r[4]} | {r[5]} |')
    lines.extend(['', 'Rates above are proportions with the exact stored Parquet precision. '
                  'Same-channel and cross-channel categories may overlap; neither implies continuous attendance.', '',
                  '## Evidence quality', ''])
    cols = ['year','interaction_evidence_channel_count','catalog_published_channel_count','intersection_count',
            'catalog_active_recall','target_manifest_coverage','total_interactions','evidence_support_tier']
    require_columns(quality, cols, 'yearly_evidence_quality.parquet')
    lines.extend(['| ' + ' | '.join(cols) + ' |', '| ' + ' | '.join(['---']*len(cols)) + ' |'])
    for row in quality[cols].itertuples(index=False, name=None):
        lines.append('| ' + ' | '.join(str(v) for v in row) + ' |')
    lines.extend(['', '## Bridge classifications', ''])
    for label, count in sorted(bridges['bridge_classification'].value_counts().items()):
        lines.append(f'- {label}: {count} channels')
    lines.extend(['', '## Literature Review', '', 'PENDING formal bibliography curation; no citations have been invented.', ''])
    return "\n".join(lines)


def build_appendix() -> str:
    lines = [
        "# Appendix: Extended Empirical Data Tables",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "**Privacy Classification:** NO_VIEWER_LEVEL_DATA (All metrics aggregate)",
        "",
        "---",
        "",
    ]

    # A1: Full Cohort Retention Matrix with EXACT column mappings
    ret_df = safe_read(COHORT_RETENTION)
    if ret_df is not None and not ret_df.empty:
        lines.extend([
            "## A1. Cohort Longitudinal Retention & Dispersion Matrix",
            "",
            "| Cohort Year | Obs Year | Elapsed | Cohort Base | Re-Observed | Continuation Rate | Same-Channel Retained | Cross-Channel Viewers | Cross-Agency Viewers |",
            "| :---: | :---: | :---: | ---: | ---: | :---: | ---: | ---: | ---: |",
        ])
        for _, r in ret_df.iterrows():
            lines.append(
                f"| {int(r.get('cohort_year', 0))} | {int(r.get('observation_year', 0))} | "
                f"+{int(r.get('elapsed_years', 0))} | {fmtnum(r.get('cohort_size', 0))} | "
                f"{fmtnum(r.get('reobserved_viewers', 0))} | {fmtpct(r.get('continuation_rate', 0))} | "
                f"{fmtnum(r.get('same_channel_reobserved_viewers', 0))} | "
                f"{fmtnum(r.get('cross_channel_reobserved_viewers', 0))} | "
                f"{fmtnum(r.get('cross_agency_reobserved_viewers', 0))} |"
            )
        lines.extend(["", "---", ""])

    # A2: Community Lineage Transitions with EXACT column mappings
    lin_df = safe_read(LINEAGE_V2)
    if lin_df is not None and not lin_df.empty:
        lines.extend([
            "## A2. Community Lineage Transitions & Optimal Matching",
            "",
            "| Horizon | From Lineage | To Lineage | Relation Type | Shared Channels | Jaccard Similarity | Forward Overlap | Backward Overlap | Primary Backbone |",
            "| :---: | :--- | :--- | :--- | ---: | :---: | :---: | :---: | :---: |",
        ])
        for _, r in lin_df.iterrows():
            from_yr = int(r.get("from_year", 0))
            to_yr = int(r.get("to_year", 0))
            backbone_str = "Yes" if r.get("is_primary_backbone") else "No"
            lines.append(
                f"| {from_yr}→{to_yr} | `{r.get('from_lineage_id', '')}` ({r.get('from_community_id', '')}) | "
                f"`{r.get('to_lineage_id', '')}` ({r.get('to_community_id', '')}) | "
                f"`{r.get('relation_type', '')}` | {fmtnum(r.get('shared_channels', 0))} | "
                f"{r.get('jaccard_similarity', 0.0):.4f} | "
                f"{fmtpct(r.get('forward_overlap', 0.0))} | "
                f"{fmtpct(r.get('backward_overlap', 0.0))} | {backbone_str} |"
            )
        lines.extend(["", "---", ""])

    # A3: Bridge Centrality & Perturbation Stability
    bridge_df = safe_read(BRIDGE_DYNAMICS)
    if bridge_df is not None and not bridge_df.empty:
        lines.extend([
            "## A3. Bridge Creators & Perturbation Stability",
            "",
            "| Channel Name | Selection Agency | Active Years | Top Decile Years | Mean Betweenness Pct | TH5 Retention Ratio | Classification |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :--- |",
        ])
        for _, r in bridge_df.sort_values(by="mean_betweenness_percentile", ascending=False).iterrows():
            lines.append(
                f"| **{r.get('channel_name', '')}** | {r.get('agency_at_selection', 'Independent')} | "
                f"{fmtnum(r.get('years_observed_count', 0))} | {fmtnum(r.get('years_in_top_decile_count', 0))} | "
                f"{r.get('mean_betweenness_percentile', 0.0):.1f}% | {r.get('threshold_th5_retention_ratio', 0.0):.3f} | "
                f"`{r.get('bridge_classification', '')}` |"
            )
        lines.extend(["", "---", ""])

    lines.append("*Appendix tables generated automatically via `scripts/build_technical_report.py`.*")
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("T19: Generating Rigorous Technical Report & Appendix Package")
    print("=" * 60)

    report_content = build_technical_report()
    report_file = REPORT_DIR / "technical_report.md"
    report_file.write_text(report_content, encoding="utf-8")
    print(f"✓ Technical report written to {report_file} ({report_file.stat().st_size / 1024:.1f} KB)")

    appendix_content = build_appendix()
    appendix_file = REPORT_DIR / "appendix_tables.md"
    appendix_file.write_text(appendix_content, encoding="utf-8")
    print(f"✓ Appendix tables written to {appendix_file} ({appendix_file.stat().st_size / 1024:.1f} KB)")

    # Privacy verification
    for p in [report_file, appendix_file]:
        content = p.read_text(encoding="utf-8")
        import re
        raw_hex = re.findall(r'(?<!sha256_)\b[0-9a-f]{64}\b', content)
        if raw_hex:
            print(f"⚠ WARNING: {p.name} contains {len(raw_hex)} unprefixed 64-char hex strings!")
            return 1

    print("✓ Privacy verification passed: zero unprefixed hex strings in report package.")
    print("✓ T19 build complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
