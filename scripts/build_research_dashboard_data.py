#!/usr/bin/env python3
"""T17 — Build Research Dashboard Data

Reads all parquet/markdown artifacts from T8–T16 and produces a single
privacy-safe JSON file that powers the static research dashboard.

Zero viewer hashes or PII are exported.
All data is macro-level aggregated metrics.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent.parent
TEMPORAL = BASE / "data" / "temporal"

# Input artifacts
ECOSYSTEM_METRICS = TEMPORAL / "ecosystem" / "yearly_ecosystem_metrics.parquet"
STRUCTURAL_BREAKS = TEMPORAL / "ecosystem" / "structural_breaks.parquet"
LINEAGE_V2 = TEMPORAL / "analysis" / "community_lineage_v2.parquet"
COMMUNITY_LIFECYCLES = TEMPORAL / "analysis" / "community_lifecycles.parquet"
COMMUNITY_SNAPSHOTS = TEMPORAL / "analysis" / "community_snapshots.parquet"
YEARLY_NETWORK = TEMPORAL / "analysis" / "yearly_network_metrics.parquet"
CENTRALITY = TEMPORAL / "centrality" / "yearly_centrality.parquet"
BRIDGE_DYNAMICS = TEMPORAL / "centrality" / "bridge_dynamics.parquet"
CHANGE_POINTS = TEMPORAL / "centrality" / "centrality_change_points.parquet"
COHORT_SURVIVAL = TEMPORAL / "cohorts" / "cohort_survival.parquet"
COHORT_RETENTION = TEMPORAL / "cohorts" / "cohort_retention_matrix.parquet"
COHORT_REACTIVATION = TEMPORAL / "cohorts" / "cohort_reactivation.parquet"
YEARLY_QUALITY = TEMPORAL / "quality" / "yearly_evidence_quality.parquet"
CHANNEL_QUALITY = TEMPORAL / "quality" / "channel_evidence_quality.parquet"
BIAS_SENSITIVITY = TEMPORAL / "quality" / "bias_sensitivity.parquet"
EVENT_IMPACT = TEMPORAL / "event_analysis" / "event_impact_metrics.parquet"
ROBUSTNESS = TEMPORAL / "robustness" / "robustness_summary.parquet"
SENSITIVITY = TEMPORAL / "robustness" / "sensitivity_results.parquet"
LIFECYCLE_EVENTS = TEMPORAL / "lifecycle" / "lifecycle_events.parquet"

# Output
OUTPUT_DIR = BASE / "web" / "research"
OUTPUT_JSON = OUTPUT_DIR / "dashboard_data.json"


def safe_read(path: Path) -> pd.DataFrame | None:
    """Read parquet, return None if missing."""
    if path.exists():
        return pd.read_parquet(path)
    print(f"  WARN: Missing {path.name}, skipping.")
    return None


def safe_val(v):
    """Convert numpy/pandas types to JSON-safe Python types."""
    if pd.isna(v):
        return None
    if hasattr(v, 'item'):
        return v.item()
    return v


def build_ecosystem_section():
    """Macro ecosystem metrics 2020-2026."""
    df = safe_read(ECOSYSTEM_METRICS)
    if df is None:
        return {}

    rows = []
    for _, r in df.iterrows():
        row = {}
        for col in df.columns:
            row[col] = safe_val(r[col])
        rows.append(row)

    breaks_df = safe_read(STRUCTURAL_BREAKS)
    breaks = []
    if breaks_df is not None:
        for _, r in breaks_df.iterrows():
            b = {}
            for col in breaks_df.columns:
                b[col] = safe_val(r[col])
            breaks.append(b)

    return {
        "yearly_metrics": rows,
        "structural_breaks": breaks,
    }


def build_lineage_section():
    """Community lineage genealogy."""
    lin_df = safe_read(LINEAGE_V2)
    lc_df = safe_read(COMMUNITY_LIFECYCLES)
    snap_df = safe_read(COMMUNITY_SNAPSHOTS)

    result = {}

    if lin_df is not None:
        transitions = []
        for _, r in lin_df.iterrows():
            t = {}
            for col in lin_df.columns:
                t[col] = safe_val(r[col])
            transitions.append(t)
        result["transitions"] = transitions

    if lc_df is not None:
        lifecycles = []
        for _, r in lc_df.iterrows():
            lc = {}
            for col in lc_df.columns:
                lc[col] = safe_val(r[col])
            lifecycles.append(lc)
        result["lifecycles"] = lifecycles

    if snap_df is not None:
        snapshots = []
        for _, r in snap_df.iterrows():
            s = {}
            for col in snap_df.columns:
                s[col] = safe_val(r[col])
            snapshots.append(s)
        result["snapshots"] = snapshots

    return result


def build_centrality_section():
    """Bridge dynamics and centrality evolution."""
    result = {}

    bridge_df = safe_read(BRIDGE_DYNAMICS)
    if bridge_df is not None:
        bridges = []
        for _, r in bridge_df.iterrows():
            b = {}
            for col in bridge_df.columns:
                b[col] = safe_val(r[col])
            bridges.append(b)
        result["bridge_dynamics"] = bridges

    cp_df = safe_read(CHANGE_POINTS)
    if cp_df is not None:
        cps = []
        for _, r in cp_df.iterrows():
            c = {}
            for col in cp_df.columns:
                c[col] = safe_val(r[col])
            cps.append(c)
        result["change_points"] = cps

    return result


def build_cohort_section():
    """Audience cohort survival and reactivation."""
    result = {}

    surv_df = safe_read(COHORT_SURVIVAL)
    if surv_df is not None:
        survival = []
        for _, r in surv_df.iterrows():
            s = {}
            for col in surv_df.columns:
                s[col] = safe_val(r[col])
            survival.append(s)
        result["survival_curve"] = survival

    ret_df = safe_read(COHORT_RETENTION)
    if ret_df is not None:
        retention = []
        for _, r in ret_df.iterrows():
            row = {}
            for col in ret_df.columns:
                row[col] = safe_val(r[col])
            retention.append(row)
        result["retention_matrix"] = retention

    react_df = safe_read(COHORT_REACTIVATION)
    if react_df is not None:
        reactivation = []
        for _, r in react_df.iterrows():
            row = {}
            for col in react_df.columns:
                row[col] = safe_val(r[col])
            reactivation.append(row)
        result["reactivation"] = reactivation

    return result


def build_quality_section():
    """Evidence quality and bias sensitivity."""
    result = {}

    yq_df = safe_read(YEARLY_QUALITY)
    if yq_df is not None:
        yearly = []
        for _, r in yq_df.iterrows():
            row = {}
            for col in yq_df.columns:
                row[col] = safe_val(r[col])
            yearly.append(row)
        result["yearly_quality"] = yearly

    cq_df = safe_read(CHANNEL_QUALITY)
    if cq_df is not None:
        # Only export tier distribution, not channel-level details (privacy)
        tier_counts = cq_df['evidence_support_tier'].value_counts().to_dict()
        result["channel_tier_distribution"] = {str(k): int(v) for k, v in tier_counts.items()}
        result["total_channels"] = int(len(cq_df))

    bs_df = safe_read(BIAS_SENSITIVITY)
    if bs_df is not None:
        sensitivity = []
        for _, r in bs_df.iterrows():
            row = {}
            for col in bs_df.columns:
                row[col] = safe_val(r[col])
            sensitivity.append(row)
        result["bias_sensitivity"] = sensitivity

    return result


def build_robustness_section():
    """T10 Robustness and sensitivity."""
    result = {}

    rob_df = safe_read(ROBUSTNESS)
    if rob_df is not None:
        rows = []
        for _, r in rob_df.iterrows():
            row = {}
            for col in rob_df.columns:
                row[col] = safe_val(r[col])
            rows.append(row)
        result["robustness_summary"] = rows

    sens_df = safe_read(SENSITIVITY)
    if sens_df is not None:
        rows = []
        for _, r in sens_df.iterrows():
            row = {}
            for col in sens_df.columns:
                row[col] = safe_val(r[col])
            rows.append(row)
        result["sensitivity_results"] = rows

    return result


def build_event_section():
    """T9 Lifecycle event impact analysis."""
    ev_df = safe_read(EVENT_IMPACT)
    if ev_df is None:
        return {}

    rows = []
    for _, r in ev_df.iterrows():
        row = {}
        for col in ev_df.columns:
            row[col] = safe_val(r[col])
        rows.append(row)
    return {"event_impacts": rows}


def main():
    print("=" * 60)
    print("T17: Building Research Dashboard Data")
    print("=" * 60)

    dashboard = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "phases_covered": "T8–T16",
            "privacy_level": "NO_VIEWER_LEVEL_DATA",
            "data_classification": {
                "public_channel_creator_metadata": "Exposed (channel names, IDs, agency affiliations as public creator data)",
                "aggregate_audience_metrics": "Exposed (pairwise shared audience counts, community sizes, graph metrics)",
                "viewer_level_rows": "ZERO (strictly excluded; no raw IDs, no viewer hashes, no individual interaction records)"
            },
            "note": "NO_VIEWER_LEVEL_DATA: Public creator metadata and aggregate audience metrics only. Zero viewer-level records or hashes.",
            "years": sorted(int(y) for y in pd.read_parquet(ECOSYSTEM_METRICS)['year'].unique()),
            "partial_year": 2026,
            "caveats": {
                "partial_window_2026_ytd": "2026 data reflects partial year-to-date (2026-01-01 to 2026-09-08) and is descriptive only (PARTIAL_WINDOW_DESCRIPTIVE_ONLY).",
                "evidence_quality": "Collection follows tiered empirical sampling (T6 deep exhaustive capture + T5 stratified backfill). Historical agency metrics represent selection-time metadata (agency_at_selection).",
                "non_causal_disclaimer": "Network structural metrics and bridge dynamics reflect observed audience co-attendance, not direct social causality or vtuber coordination."
            }
        },
        "ecosystem": build_ecosystem_section(),
        "lineage": build_lineage_section(),
        "centrality": build_centrality_section(),
        "cohorts": build_cohort_section(),
        "quality": build_quality_section(),
        "robustness": build_robustness_section(),
        "events": build_event_section(),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    size_kb = OUTPUT_JSON.stat().st_size / 1024
    print(f"\n✓ Dashboard data written to {OUTPUT_JSON}")
    print(f"  Size: {size_kb:.1f} KB")
    print(f"  Sections: {list(dashboard.keys())}")

    # Verify no viewer hashes leaked
    content = OUTPUT_JSON.read_text(encoding="utf-8")
    import re
    hex_matches = re.findall(r'\b[0-9a-f]{64}\b', content)
    if hex_matches:
        print(f"\n⚠ WARNING: Found {len(hex_matches)} potential 64-char hex strings!")
        for h in hex_matches[:5]:
            print(f"  {h}")
        return 1
    else:
        print("✓ Privacy check: zero 64-char hex strings in output.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
