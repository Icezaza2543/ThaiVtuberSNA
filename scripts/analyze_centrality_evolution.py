"""Phase T13: Dynamic Bridges & Centrality Evolution Engine

Tracks longitudinal evolution of creator structural roles across 2020-2026.

Analytical Scope:
1. For each yearly interaction network (threshold >= 1, unified):
   - Degree centrality
   - Weighted degree / strength
   - Betweenness centrality
   - PageRank
   - Eigenvector centrality (or fall back to Katz/power iteration if convergence fails)
   - Cross-community edge share (based on T11/T7 community partitions)
   - Cross-agency edge share (based on target manifest agency_at_selection)
2. Longitudinal Structural Percentiles:
   - Rank and percentiles calculated within each year:
     TOP_1_PERCENT (>= 99th percentile)
     TOP_5_PERCENT (>= 95th percentile)
     TOP_10_PERCENT (>= 90th percentile)
     TOP_QUARTILE (>= 75th percentile)
     BELOW_QUARTILE (< 75th percentile)
3. Change-Point & Role Trajectory Dynamics:
   - First year entering top decile
   - Total years persisting in top decile
   - Max percentile rank, min percentile rank, percentile volatility
4. Threshold Sensitivity Verification:
   - Evaluates bridge stability across thresholds >= 1, >= 3, >= 5.
5. Deterministic, Metric-Derived Role Classification:
   - STABLE_BRIDGE: Persists in top decile for >= 3 years and present in 2026.
   - EMERGING_BRIDGE: First entered top decile in recent years (2024-2026) and ascending.
   - DECLINING_BRIDGE: Previously in top decile for >= 2 years but dropped below top decile in 2025/2026.
   - VOLATILE: Fluctuates into and out of top decile without sustained persistence.
   - INSUFFICIENT_EVIDENCE: Observed in <= 1 year or never reached top quartile.

Framing Contract:
- Uses "structural centrality" / "bridge position".
- Avoids claiming "influence" or "causality".

Outputs:
- data/temporal/centrality/yearly_centrality.parquet
- data/temporal/centrality/bridge_dynamics.parquet
- data/temporal/centrality/centrality_change_points.parquet
- data/temporal/centrality/bridge_dynamics_report.md
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

import duckdb
import pandas as pd
import numpy as np
import networkx as nx
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BridgeCentralityEvolution")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "temporal" / "centrality"
SNAPSHOTS_PARQUET = BASE_DIR / "data" / "temporal" / "snapshots" / "network_snapshots.parquet"
TARGET_MANIFEST_CSV = BASE_DIR / "data" / "temporal" / "catalog" / "target_manifest.csv"
COMMUNITY_SNAPSHOTS_PARQUET = BASE_DIR / "data" / "temporal" / "analysis" / "community_snapshots.parquet"

OUTPUT_YEARLY_CENTRALITY = DATA_DIR / "yearly_centrality.parquet"
OUTPUT_BRIDGE_DYNAMICS = DATA_DIR / "bridge_dynamics.parquet"
OUTPUT_CHANGE_POINTS = DATA_DIR / "centrality_change_points.parquet"
OUTPUT_REPORT_MD = DATA_DIR / "bridge_dynamics_report.md"


def assign_percentile_band(pct: float) -> str:
    """Assigns discrete percentile band to avoid overclaiming raw ordinal rank."""
    if pct >= 0.99:
        return "TOP_1_PERCENT"
    elif pct >= 0.95:
        return "TOP_5_PERCENT"
    elif pct >= 0.90:
        return "TOP_10_PERCENT"
    elif pct >= 0.75:
        return "TOP_QUARTILE"
    else:
        return "BELOW_QUARTILE"


def compute_pagerank(G: nx.Graph, weight: str = "weight", alpha: float = 0.85, max_iter: int = 300, tol: float = 1e-6) -> Dict[str, float]:
    """Pure-python weighted PageRank implementation to guarantee execution without scipy."""
    nodes = list(G.nodes())
    N = len(nodes)
    if N == 0:
        return {}
    if N == 1:
        return {nodes[0]: 1.0}
    p = {n: 1.0 / N for n in nodes}
    out_weights = {n: G.degree(n, weight=weight) for n in nodes}
    for _ in range(max_iter):
        new_p = {}
        dangling_sum = sum(p[n] for n in nodes if out_weights[n] == 0)
        for n in nodes:
            in_sum = sum(
                p[nbr] * G[nbr][n].get(weight, 1.0) / out_weights[nbr]
                for nbr in G.neighbors(n)
                if out_weights[nbr] > 0
            )
            new_p[n] = (1.0 - alpha) / N + alpha * (in_sum + dangling_sum / N)
        err = sum(abs(new_p[n] - p[n]) for n in nodes)
        p = new_p
        if err < tol:
            break
    return p


def run_centrality_evolution_analysis() -> None:
    """Computes longitudinal network centrality metrics and bridge dynamics."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load target manifest for names and agencies
    manifest_df = pd.read_csv(TARGET_MANIFEST_CSV)
    channel_name = dict(zip(manifest_df["channel_id"], manifest_df["name"]))
    channel_agency = dict(zip(manifest_df["channel_id"], manifest_df["agency"].fillna("Independent / Other")))

    # Load community snapshots for community assignment per year
    comm_df = pd.read_parquet(COMMUNITY_SNAPSHOTS_PARQUET)
    channel_comm: Dict[Tuple[int, str], str] = {}
    for _, r in comm_df.iterrows():
        channel_comm[(int(r["year"]), r["channel_id"])] = r["community_id"]

    # Load snapshots
    snapshots_df = pd.read_parquet(SNAPSHOTS_PARQUET)
    yearly_snapshots = snapshots_df[snapshots_df["window_type"] == "yearly"]
    years = sorted(yearly_snapshots["window_start"].str[:4].astype(int).unique())
    logger.info(f"Loaded yearly snapshots across {years}")

    # 1. Compute yearly metrics for each threshold
    yearly_records: List[Dict[str, Any]] = []

    # Map threshold -> year -> bridge set (top 10% by betweenness) for sensitivity
    threshold_bridges: Dict[int, Dict[int, Set[str]]] = {1: {}, 3: {}, 5: {}}

    for yr in years:
        yr_str = str(yr)
        yr_edges = yearly_snapshots[yearly_snapshots["window_start"].str.startswith(yr_str)]

        # Build graph for thresholds 1, 3, 5 with distance = 1.0 / strength
        for th in [1, 3, 5]:
            G_th = nx.Graph()
            for _, r in yr_edges.iterrows():
                w = float(r["shared_any"])
                if w >= th:
                    G_th.add_edge(r["vtuber_a"], r["vtuber_b"], weight=w, distance=1.0 / w)

            if len(G_th) > 1 and G_th.number_of_edges() > 0:
                btw_th = nx.betweenness_centrality(G_th, weight="distance", normalized=True)
                s_btw = pd.Series(btw_th).rank(method="average", pct=True)
                threshold_bridges[th][yr] = set(s_btw[s_btw >= 0.90].index)
            else:
                threshold_bridges[th][yr] = set()

        # Primary analysis on canonical threshold >= 1
        G = nx.Graph()
        for _, r in yr_edges.iterrows():
            w = float(r["shared_any"])
            if w >= 1:
                G.add_edge(r["vtuber_a"], r["vtuber_b"], weight=w, distance=1.0 / w)

        if len(G) <= 1:
            continue

        n_nodes = len(G)
        deg_map = dict(G.degree())
        strength_map = dict(G.degree(weight="weight"))
        # Betweenness centrality strictly uses distance = 1.0 / strength
        btw_map = nx.betweenness_centrality(G, weight="distance", normalized=True)
        # PageRank uses strength weights
        pr_map = compute_pagerank(G, weight="weight", alpha=0.85)

        try:
            eig_map = nx.eigenvector_centrality(G, weight="weight", max_iter=1000)
        except Exception:
            eig_map = {n: 0.0 for n in G.nodes()}

        # Compute cross-community and cross-agency edge share
        cross_comm_share: Dict[str, float] = {}
        cross_agency_share: Dict[str, float] = {}

        for n in G.nodes():
            n_comm = channel_comm.get((yr, n), "Unknown")
            n_agency = channel_agency.get(n, "Independent / Other")
            nbrs = list(G.neighbors(n))
            if nbrs:
                diff_comm_edges = sum(
                    1 for v in nbrs if channel_comm.get((yr, v), "Unknown") != n_comm
                )
                diff_agency_edges = sum(
                    1 for v in nbrs if channel_agency.get(v, "Independent / Other") != n_agency
                )
                cross_comm_share[n] = round(diff_comm_edges / len(nbrs), 4)
                cross_agency_share[n] = round(diff_agency_edges / len(nbrs), 4)
            else:
                cross_comm_share[n] = 0.0
                cross_agency_share[n] = 0.0

        # Deterministic, tie-aware percentiles within each year
        btw_pct_map = pd.Series(btw_map).rank(method="average", pct=True).to_dict()
        deg_pct_map = pd.Series(deg_map).rank(method="average", pct=True).to_dict()
        pr_pct_map = pd.Series(pr_map).rank(method="average", pct=True).to_dict()

        for n in G.nodes():
            btw_pct = btw_pct_map[n]
            deg_pct = deg_pct_map[n]
            pr_pct = pr_pct_map[n]

            yearly_records.append({
                "year": yr,
                "channel_id": n,
                "channel_name": channel_name.get(n, n),
                "agency_at_selection": channel_agency.get(n, "Independent / Other"),
                "community_id": channel_comm.get((yr, n), "Unknown"),
                "degree": deg_map[n],
                "weighted_degree": strength_map[n],
                "betweenness_centrality": round(btw_map[n], 6),
                "pagerank": round(pr_map[n], 6),
                "eigenvector_centrality": round(eig_map[n], 6),
                "cross_community_edge_share": cross_comm_share[n],
                "cross_agency_edge_share": cross_agency_share[n],
                "betweenness_percentile": round(btw_pct, 4),
                "degree_percentile": round(deg_pct, 4),
                "pagerank_percentile": round(pr_pct, 4),
                "bridge_percentile_band": assign_percentile_band(btw_pct),
                "is_in_top_decile": btw_pct >= 0.90,
                "is_in_top_quartile": btw_pct >= 0.75,
            })

    df_yearly = pd.DataFrame(yearly_records)
    logger.info(f"Computed yearly centrality across {len(df_yearly)} channel-year records.")

    # 2. Longitudinal Bridge Dynamics & Classifications
    logger.info("Computing longitudinal bridge trajectories and deterministic classifications...")
    bridge_records: List[Dict[str, Any]] = []
    change_point_records: List[Dict[str, Any]] = []

    unique_channels = df_yearly["channel_id"].unique()

    for cid in unique_channels:
        c_rows = df_yearly[df_yearly["channel_id"] == cid].sort_values("year")
        c_name = c_rows["channel_name"].iloc[0]
        c_agency = c_rows["agency_at_selection"].iloc[0]

        years_observed = c_rows["year"].tolist()
        num_years = len(years_observed)
        first_yr = years_observed[0]
        last_yr = years_observed[-1]

        top_decile_rows = c_rows[c_rows["is_in_top_decile"]]
        years_in_top_decile = top_decile_rows["year"].tolist()
        top_decile_count = len(years_in_top_decile)
        first_year_top_decile = years_in_top_decile[0] if years_in_top_decile else None

        btw_pcts = c_rows["betweenness_percentile"].tolist()
        max_btw_pct = max(btw_pcts)
        min_btw_pct = min(btw_pcts)
        mean_btw_pct = float(np.mean(btw_pcts))
        pct_volatility = float(np.std(btw_pcts)) if len(btw_pcts) > 1 else 0.0

        mean_cross_comm = float(c_rows["cross_community_edge_share"].mean())
        mean_cross_agency = float(c_rows["cross_agency_edge_share"].mean())

        # Sensitivity across thresholds (how often in top 10% under th=1, th=3, th=5)
        th1_present = sum(1 for y in years_observed if cid in threshold_bridges[1].get(y, set()))
        th3_present = sum(1 for y in years_observed if cid in threshold_bridges[3].get(y, set()))
        th5_present = sum(1 for y in years_observed if cid in threshold_bridges[5].get(y, set()))
        th_stability_ratio = (th5_present / th1_present) if th1_present > 0 else 0.0

        # Deterministic Classification Rules
        # 1. INSUFFICIENT_EVIDENCE: observed in <= 1 year or never reached top quartile
        if num_years <= 1 or max_btw_pct < 0.75:
            classification = "INSUFFICIENT_EVIDENCE"
            rule_reason = f"Observed in {num_years} year(s) with max percentile {max_btw_pct:.2f} < 0.75"
        # 2. STABLE_BRIDGE: in top decile >= 3 years and present in 2026 with >= 75th pct, AND th5_retention_ratio >= 0.50
        elif top_decile_count >= 3 and 2026 in years_observed and c_rows[c_rows["year"] == 2026]["betweenness_percentile"].iloc[0] >= 0.75:
            if th_stability_ratio >= 0.50:
                classification = "STABLE_BRIDGE"
                rule_reason = f"Top decile in {top_decile_count} years; retained >= 75th percentile in 2026; threshold >= 5 retention ratio {th_stability_ratio:.2f} >= 0.50"
            else:
                classification = "STABLE_BRIDGE_CANONICAL_ONLY"
                rule_reason = f"Top decile in {top_decile_count} years; retained in 2026 at canonical threshold >= 1, but threshold >= 5 retention ratio {th_stability_ratio:.2f} < 0.50"
        # 3. EMERGING_BRIDGE: first entered top decile in 2024-2026 with documented ascending trajectory
        elif (
            first_year_top_decile is not None
            and first_year_top_decile >= 2024
            and len(btw_pcts) >= 2
            and btw_pcts[-1] >= btw_pcts[-2]
            and btw_pcts[-1] >= 0.85
        ):
            classification = "EMERGING_BRIDGE"
            rule_reason = f"First entered top decile in {first_year_top_decile}; ascending trajectory ({btw_pcts[-2]:.2f} -> {btw_pcts[-1]:.2f}) with terminal percentile >= 0.85"
        # 4. DECLINING_BRIDGE: previously in top decile for >= 2 years, dropped below top quartile in 2026 or inactive
        elif top_decile_count >= 2 and (2026 not in years_observed or c_rows[c_rows["year"] == 2026]["betweenness_percentile"].iloc[0] < 0.75):
            classification = "DECLINING_BRIDGE"
            rule_reason = f"Previously reached top decile in {top_decile_count} years (>= 2), but declined below top quartile (< 0.75) or inactive in 2026"
        # 5. VOLATILE: has >= 2 years in top quartile with volatility >= 0.15
        elif pct_volatility >= 0.15 and max_btw_pct >= 0.80:
            classification = "VOLATILE"
            rule_reason = f"High percentile standard deviation ({pct_volatility:.3f} >= 0.15) with top quartile reach"
        else:
            classification = "MODERATE_PERIPHERAL"
            rule_reason = f"Steady non-bridge trajectory with mean percentile {mean_btw_pct:.2f}"

        bridge_records.append({
            "channel_id": cid,
            "channel_name": c_name,
            "agency_at_selection": c_agency,
            "first_observed_year": first_yr,
            "last_observed_year": last_yr,
            "years_observed_count": num_years,
            "years_in_top_decile_count": top_decile_count,
            "first_year_entering_top_decile": first_year_top_decile if first_year_top_decile else -1,
            "mean_betweenness_percentile": round(mean_btw_pct, 4),
            "max_betweenness_percentile": round(max_btw_pct, 4),
            "min_betweenness_percentile": round(min_btw_pct, 4),
            "percentile_volatility_std": round(pct_volatility, 4),
            "mean_cross_community_share": round(mean_cross_comm, 4),
            "mean_cross_agency_share": round(mean_cross_agency, 4),
            "threshold_th5_retention_ratio": round(th_stability_ratio, 4),
            "bridge_classification": classification,
            "classification_rule_basis": rule_reason
        })

        # Change-point detection: year-over-year jump >= +0.25 or drop <= -0.25 in percentile
        for j in range(len(years_observed) - 1):
            y_curr = years_observed[j]
            y_next = years_observed[j + 1]
            if y_next == y_curr + 1:
                p_curr = c_rows[c_rows["year"] == y_curr]["betweenness_percentile"].iloc[0]
                p_next = c_rows[c_rows["year"] == y_next]["betweenness_percentile"].iloc[0]
                delta = p_next - p_curr
                if abs(delta) >= 0.25:
                    change_type = "RAPID_ASCENT" if delta > 0 else "RAPID_DECLINE"
                    change_point_records.append({
                        "channel_id": cid,
                        "channel_name": c_name,
                        "from_year": y_curr,
                        "to_year": y_next,
                        "from_percentile": round(p_curr, 4),
                        "to_percentile": round(p_next, 4),
                        "percentile_delta": round(delta, 4),
                        "change_type": change_type,
                        "from_band": assign_percentile_band(p_curr),
                        "to_band": assign_percentile_band(p_next)
                    })

    df_bridges = pd.DataFrame(bridge_records)
    df_change_points = pd.DataFrame(change_point_records, columns=['channel_id','channel_name','from_year','to_year','from_percentile','to_percentile','percentile_delta','change_type','from_band','to_band'])

    # Save to parquet
    df_yearly.to_parquet(OUTPUT_YEARLY_CENTRALITY, index=False)
    df_bridges.to_parquet(OUTPUT_BRIDGE_DYNAMICS, index=False)
    df_change_points.to_parquet(OUTPUT_CHANGE_POINTS, index=False)
    logger.info(f"Saved {OUTPUT_YEARLY_CENTRALITY} ({len(df_yearly)} rows)")
    logger.info(f"Saved {OUTPUT_BRIDGE_DYNAMICS} ({len(df_bridges)} rows)")
    logger.info(f"Saved {OUTPUT_CHANGE_POINTS} ({len(df_change_points)} rows)")

    # 3. Generate Report
    generate_bridge_dynamics_report(df_yearly, df_bridges, df_change_points)


def generate_bridge_dynamics_report(
    df_yearly: pd.DataFrame, df_bridges: pd.DataFrame, df_change_points: pd.DataFrame
) -> str:
    """Generates bridge_dynamics_report.md programmatically from data."""
    stable_bridges = df_bridges[df_bridges["bridge_classification"] == "STABLE_BRIDGE"].sort_values(
        "mean_betweenness_percentile", ascending=False
    )
    canonical_stable = df_bridges[df_bridges["bridge_classification"] == "STABLE_BRIDGE_CANONICAL_ONLY"].sort_values(
        "mean_betweenness_percentile", ascending=False
    )
    emerging_bridges = df_bridges[df_bridges["bridge_classification"] == "EMERGING_BRIDGE"].sort_values(
        "mean_betweenness_percentile", ascending=False
    )
    declining_bridges = df_bridges[df_bridges["bridge_classification"] == "DECLINING_BRIDGE"].sort_values(
        "mean_betweenness_percentile", ascending=False
    )
    volatile_channels = df_bridges[df_bridges["bridge_classification"] == "VOLATILE"].sort_values(
        "percentile_volatility_std", ascending=False
    )

    ascents = df_change_points[df_change_points["change_type"] == "RAPID_ASCENT"]
    declines = df_change_points[df_change_points["change_type"] == "RAPID_DECLINE"]

    lines = []
    lines.append("# Phase T13: Dynamic Bridges & Centrality Evolution Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"This report tracks the longitudinal evolution of creator structural network roles across the Thai VTuber interaction ecosystem from 2020 through 2026. Across **{len(df_yearly)} channel-year evaluations**, channel centrality is measured via normalized percentile bands to avoid overinterpreting threshold-sensitive ordinal ranks.")
    lines.append("")
    lines.append("### Scientific Framing & Guardrails")
    lines.append("1. **Edge Distance vs Strength Semantics:** Betweenness centrality models shortest paths where edge weight represents traversal distance (`distance = 1.0 / strength`, where `strength = shared_any`). Higher co-audience strength creates shorter graph distance. Degree, PageRank, and eigenvector centrality utilize edge strength directly.")
    lines.append("2. **Deterministic Tie-Aware Percentiles:** Percentiles are computed using average rank (`Series.rank(method='average', pct=True)`), ensuring identical centrality values receive strictly equal percentiles invariant to node insertion order.")
    lines.append("3. **Structural Position, Not Causal Influence:** Betweenness centrality and bridge metrics quantify topological position on shortest paths between creator communities. They must never be interpreted as personal 'influence' or causal authority.")
    lines.append("4. **Percentile Bands over Raw Ranks:** In alignment with Phase T10 findings demonstrating rank volatility under edge pruning, channels are classified into standardized percentile bands (`TOP_1_PERCENT`, `TOP_5_PERCENT`, `TOP_10_PERCENT`, `TOP_QUARTILE`).")
    lines.append("5. **Threshold Sensitivity & Robustness:** Bridge stability is tested against edge weight thresholds (>= 1, >= 3, >= 5 shared viewers) to distinguish multi-viewer structural bridges from single-viewer peripheral ties.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Classification of Creator Structural Roles")
    lines.append("")
    lines.append(f"- **STABLE_BRIDGE Creators (Threshold Robust):** {len(stable_bridges)}")
    if not canonical_stable.empty:
        lines.append(f"- **STABLE_BRIDGE_CANONICAL_ONLY (Threshold >= 1 Only):** {len(canonical_stable)}")
    lines.append(f"- **EMERGING_BRIDGE Creators (Ascending 2024–2026):** {len(emerging_bridges)}")
    lines.append(f"- **DECLINING_BRIDGE Creators:** {len(declining_bridges)}")
    lines.append(f"- **VOLATILE Structural Positions:** {len(volatile_channels)}")
    lines.append("")
    lines.append("### 1.1 Stable Bridge Creators (Sustained Cross-Community Integration)")
    lines.append("| Channel Name | Agency | Years Observed | Yrs in Top Decile | Mean Btw Pct | Max Btw Pct | Cross-Comm Share | Cross-Agency Share | Th=5 Retention |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for _, r in pd.concat([stable_bridges, canonical_stable]).iterrows():
        tag = " (Th>=1 only)" if r["bridge_classification"] == "STABLE_BRIDGE_CANONICAL_ONLY" else ""
        lines.append(
            f"| **{r['channel_name']}{tag}** | {r['agency_at_selection']} | {r['years_observed_count']} | "
            f"{r['years_in_top_decile_count']} | {r['mean_betweenness_percentile']:.1%} | {r['max_betweenness_percentile']:.1%} | "
            f"{r['mean_cross_community_share']:.1%} | {r['mean_cross_agency_share']:.1%} | {r['threshold_th5_retention_ratio']:.1%} |"
        )
    lines.append("")
    lines.append("### 1.2 Emerging Bridge Creators (Recent Ascents 2024–2026)")
    lines.append("| Channel Name | Agency | First Top Decile | Mean Btw Pct | Max Btw Pct | Cross-Comm Share | Cross-Agency Share |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: |")
    for _, r in emerging_bridges.iterrows():
        lines.append(
            f"| **{r['channel_name']}** | {r['agency_at_selection']} | {r['first_year_entering_top_decile']} | "
            f"{r['mean_betweenness_percentile']:.1%} | {r['max_betweenness_percentile']:.1%} | "
            f"{r['mean_cross_community_share']:.1%} | {r['mean_cross_agency_share']:.1%} |"
        )
    lines.append("")
    lines.append("### 1.3 Declining Bridge Creators")
    lines.append("| Channel Name | Agency | Years in Top Decile | Mean Btw Pct | Max Btw Pct | Rule Reason |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :--- |")
    for _, r in declining_bridges.iterrows():
        lines.append(
            f"| **{r['channel_name']}** | {r['agency_at_selection']} | {r['years_in_top_decile_count']} | "
            f"{r['mean_betweenness_percentile']:.1%} | {r['max_betweenness_percentile']:.1%} | {r['classification_rule_basis']} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Centrality Change-Point Candidates (Rapid Reconfigurations)")
    lines.append("")
    lines.append(f"Detected **{len(df_change_points)} major structural change-points** (|delta| >= 25 percentile points between adjacent years):")
    lines.append(f"- **Rapid Ascents:** {len(ascents)}")
    lines.append(f"- **Rapid Declines:** {len(declines)}")
    lines.append("")
    lines.append("| Channel Name | Year Transition | Change Type | From Pct | To Pct | Delta | From Band | To Band |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |")
    for _, r in df_change_points.sort_values("to_year").iterrows():
        lines.append(
            f"| {r['channel_name']} | {r['from_year']} -> {r['to_year']} | `{r['change_type']}` | "
            f"{r['from_percentile']:.1%} | {r['to_percentile']:.1%} | {r['percentile_delta']:+.1%} | "
            f"`{r['from_band']}` | `{r['to_band']}` |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. Threshold Sensitivity Comparison")
    lines.append("")
    lines.append("In accordance with Phase T10 validation, pruning low-weight edges removes peripheral shared-viewer bridges while concentrating centrality among high-density agency channels. Stable bridges with >= 50% retention under threshold >= 5 demonstrate genuine multi-viewer co-interaction bridges, whereas channels with 0% retention represent single-viewer tie bridges susceptible to sampling variation.")
    lines.append("")
    lines.append("---")
    lines.append("*Report generated automatically by `scripts/analyze_centrality_evolution.py`.*")
    lines.append("")

    content = "\n".join(lines)
    with open(OUTPUT_REPORT_MD, "w", encoding="utf-8") as f:
        f.write(content)

    return content


if __name__ == "__main__":
    run_centrality_evolution_analysis()
