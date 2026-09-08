#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase N5 / Pass 2F: Deep Audience Behavior Aggregation Engine (Privacy-Preserving Public Analytics)
Builds:
- data/industry/audience_behavior_yearly.parquet
- data/industry/audience_behavior_yearly.json

Strict Governance Rules:
- Private viewer evidence is used ONLY as an internal in-memory computation source.
- NEVER export viewer-level rows or identifiers (viewer_hash, channel_id, display_name).
- All outputs are k-anonymized public population-level aggregates (LEVEL C).
- Do NOT call these demographics. Do NOT infer age, gender, income, or geography.
- Use explicit terminology: 'Behavioral Audience Segments'.
"""

import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_duckdb_temporal_snapshots import build_unified_raw_view, build_canonical_events_view

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AudienceBehaviorEngine")

INDUSTRY_DIR = ROOT / "data/industry"
INDUSTRY_DIR.mkdir(parents=True, exist_ok=True)

COMMUNITY_SNAPSHOTS_PARQUET = ROOT / "data/temporal/analysis/community_snapshots.parquet"
TARGET_MANIFEST_CSV = ROOT / "data/temporal/catalog/target_manifest.csv"

OUT_PARQUET = INDUSTRY_DIR / "audience_behavior_yearly.parquet"
OUT_JSON = INDUSTRY_DIR / "audience_behavior_yearly.json"

NOW_ISO = datetime.now(timezone.utc).isoformat()


def compute_audience_behavior_aggregates():
    logger.info("Initializing DuckDB in-memory session for aggregate derivation...")
    con = duckdb.connect(":memory:")
    
    # Build canonical events view in memory
    logger.info("Building unified raw and canonical events views...")
    build_unified_raw_view(con)
    build_canonical_events_view(con)
    
    # Load manifest and community snapshots for agency and community mappings
    manifest_df = pd.read_csv(TARGET_MANIFEST_CSV)[["channel_id", "agency"]]
    con.register("manifest_table", manifest_df)
    
    comm_df = pd.read_parquet(COMMUNITY_SNAPSHOTS_PARQUET)[["year", "channel_id", "community_id"]]
    con.register("comm_table", comm_df)
    
    logger.info("Executing privacy-preserving behavioral audience queries...")
    
    # 1. Ephemeral viewer-channel-year activity with agency and community mappings
    con.execute("""
        CREATE OR REPLACE TEMP TABLE viewer_channel_year_activity AS
        SELECT 
            ce.viewer_hash,
            EXTRACT(YEAR FROM ce.interaction_time)::INT AS interaction_year,
            ce.vtuber_channel_id,
            COALESCE(m.agency, 'Independent') AS agency,
            COALESCE(c.community_id, 'unclustered') AS community_id,
            BOOL_OR(ce.source_type = 'comment') AS has_comment,
            BOOL_OR(ce.source_type = 'live_chat') AS has_live_chat,
            COUNT(*) AS event_count
        FROM canonical_events ce
        LEFT JOIN manifest_table m ON ce.vtuber_channel_id = m.channel_id
        LEFT JOIN comm_table c ON ce.vtuber_channel_id = c.channel_id 
                               AND EXTRACT(YEAR FROM ce.interaction_time)::INT = c.year
        WHERE ce.interaction_time IS NOT NULL
        GROUP BY 1, 2, 3, 4, 5
    """)
    
    # 2. Ephemeral viewer-year summary
    con.execute("""
        CREATE OR REPLACE TEMP TABLE viewer_year_summary AS
        SELECT 
            viewer_hash,
            interaction_year,
            COUNT(DISTINCT vtuber_channel_id) AS distinct_channels,
            COUNT(DISTINCT agency) AS distinct_agencies,
            COUNT(DISTINCT community_id) AS distinct_communities,
            BOOL_OR(has_comment) AS any_comment,
            BOOL_OR(has_live_chat) AS any_chat,
            CASE 
                WHEN BOOL_OR(has_comment) AND BOOL_OR(has_live_chat) THEN 'mixed'
                WHEN BOOL_OR(has_comment) THEN 'comment_only'
                ELSE 'chat_only'
            END AS modality_state,
            SUM(event_count) AS total_events
        FROM viewer_channel_year_activity
        GROUP BY 1, 2
    """)
    
    # 3. Viewer lifetime cohort year and active years count
    con.execute("""
        CREATE OR REPLACE TEMP TABLE viewer_lifetime AS
        SELECT 
            viewer_hash,
            MIN(interaction_year) AS first_year,
            MAX(interaction_year) AS last_year,
            COUNT(DISTINCT interaction_year) AS active_years_count
        FROM viewer_year_summary
        GROUP BY 1
    """)

    # 4. Channel rank per year by event volume (for creator-size exposure)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE channel_yearly_rank AS
        WITH ch_events AS (
            SELECT 
                interaction_year,
                vtuber_channel_id,
                SUM(event_count) AS total_events
            FROM viewer_channel_year_activity
            GROUP BY 1, 2
        )
        SELECT 
            interaction_year,
            vtuber_channel_id,
            ROW_NUMBER() OVER (PARTITION BY interaction_year ORDER BY total_events DESC) AS channel_rank
        FROM ch_events
    """)
    
    years = [r[0] for r in con.execute("SELECT DISTINCT interaction_year FROM viewer_year_summary ORDER BY 1").fetchall()]
    logger.info(f"Observed years in canonical data: {years}")
    
    annual_metrics = []
    
    for yr in years:
        # Annual base population (denominator)
        total_accounts = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash) 
            FROM viewer_year_summary 
            WHERE interaction_year = {yr}
        """).fetchone()[0]
        
        # Quantiles for channels, communities, agencies
        quantiles_row = con.execute(f"""
            SELECT 
                ROUND(quantile_cont(distinct_channels, 0.25), 2),
                ROUND(quantile_cont(distinct_channels, 0.50), 2),
                ROUND(quantile_cont(distinct_channels, 0.75), 2),
                ROUND(quantile_cont(distinct_channels, 0.90), 2),
                ROUND(quantile_cont(distinct_channels, 0.95), 2),
                ROUND(quantile_cont(distinct_communities, 0.50), 2),
                ROUND(quantile_cont(distinct_communities, 0.75), 2),
                ROUND(quantile_cont(distinct_communities, 0.90), 2),
                ROUND(quantile_cont(distinct_communities, 0.95), 2),
                ROUND(quantile_cont(distinct_agencies, 0.50), 2),
                ROUND(quantile_cont(distinct_agencies, 0.75), 2),
                ROUND(quantile_cont(distinct_agencies, 0.90), 2),
                ROUND(quantile_cont(distinct_agencies, 0.95), 2),
                ROUND(quantile_cont(total_events, 0.50), 2),
                ROUND(quantile_cont(total_events, 0.75), 2),
                ROUND(quantile_cont(total_events, 0.90), 2),
                ROUND(quantile_cont(total_events, 0.95), 2),
                ROUND(quantile_cont(total_events, 0.99), 2)
            FROM viewer_year_summary
            WHERE interaction_year = {yr}
        """).fetchone()

        ch_p25, ch_p50, ch_p75, ch_p90, ch_p95 = quantiles_row[0:5]
        comm_p50, comm_p75, comm_p90, comm_p95 = quantiles_row[5:9]
        ag_p50, ag_p75, ag_p90, ag_p95 = quantiles_row[9:13]
        ev_p50, ev_p75, ev_p90, ev_p95, ev_p99 = quantiles_row[13:18]

        # Top 10% event concentration share
        ev_conc_row = con.execute(f"""
            WITH ranked AS (
                SELECT 
                    total_events,
                    PERCENT_RANK() OVER (ORDER BY total_events) AS p_rank
                FROM viewer_year_summary
                WHERE interaction_year = {yr}
            )
            SELECT 
                SUM(CASE WHEN p_rank >= 0.90 THEN total_events ELSE 0 END) * 100.0 / NULLIF(SUM(total_events), 0)
            FROM ranked
        """).fetchone()
        top_10pct_event_share = round(ev_conc_row[0], 2) if ev_conc_row and ev_conc_row[0] is not None else 0.0

        # Timing dimensions
        new_accounts = con.execute(f"""
            SELECT COUNT(DISTINCT s.viewer_hash)
            FROM viewer_year_summary s
            JOIN viewer_lifetime l ON s.viewer_hash = l.viewer_hash
            WHERE s.interaction_year = {yr} AND l.first_year = {yr}
        """).fetchone()[0]
        
        reobserved_accounts = total_accounts - new_accounts
        
        # Reactivated accounts: active in yr, active in <= yr-2, but NOT active in yr-1
        if yr >= 2022:
            react_res = con.execute(f"""
                WITH prev_act AS (
                    SELECT 
                        s.viewer_hash,
                        MAX(prev.interaction_year) AS prev_year
                    FROM viewer_year_summary s
                    JOIN viewer_year_summary prev 
                      ON s.viewer_hash = prev.viewer_hash 
                     AND prev.interaction_year <= {yr - 2}
                    WHERE s.interaction_year = {yr}
                      AND s.viewer_hash NOT IN (
                          SELECT viewer_hash FROM viewer_year_summary WHERE interaction_year = {yr - 1}
                      )
                    GROUP BY 1
                )
                SELECT COUNT(*), AVG({yr} - prev_year) FROM prev_act
            """).fetchone()
            reactivated = react_res[0]
            avg_reactivation_interval = round(react_res[1], 2) if react_res[1] is not None else 0.0
        else:
            reactivated = 0
            avg_reactivation_interval = 0.0
            
        multi_year = con.execute(f"""
            SELECT COUNT(DISTINCT s.viewer_hash)
            FROM viewer_year_summary s
            JOIN viewer_lifetime l ON s.viewer_hash = l.viewer_hash
            WHERE s.interaction_year = {yr} AND l.active_years_count >= 2
        """).fetchone()[0]
        
        # Detailed Breadth Buckets
        single_channel = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND distinct_channels = 1
        """).fetchone()[0]
        
        two_channels = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND distinct_channels = 2
        """).fetchone()[0]

        three_to_five_channels = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND distinct_channels BETWEEN 3 AND 5
        """).fetchone()[0]

        six_to_ten_channels = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND distinct_channels BETWEEN 6 AND 10
        """).fetchone()[0]

        gt_ten_channels = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND distinct_channels > 10
        """).fetchone()[0]

        multi_channel = total_accounts - single_channel
        
        same_community_multi = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND distinct_channels >= 2 AND distinct_communities = 1
        """).fetchone()[0]
        
        cross_community = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND distinct_communities >= 2
        """).fetchone()[0]
        
        cross_agency = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND distinct_agencies >= 2
        """).fetchone()[0]
        
        # Modality dimensions
        comment_only = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND any_comment = true AND any_chat = false
        """).fetchone()[0]
        
        chat_only = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND any_comment = false AND any_chat = true
        """).fetchone()[0]
        
        mixed_modality = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND any_comment = true AND any_chat = true
        """).fetchone()[0]

        # Modality transitions from yr-1 to yr
        modality_transitions = {
            "retained_from_prior_year": 0,
            "comment_to_comment": 0,
            "comment_to_chat": 0,
            "comment_to_mixed": 0,
            "chat_to_comment": 0,
            "chat_to_chat": 0,
            "chat_to_mixed": 0,
            "mixed_to_comment": 0,
            "mixed_to_chat": 0,
            "mixed_to_mixed": 0,
        }
        if yr > min(years):
            trans_rows = con.execute(f"""
                SELECT 
                    prev.modality_state AS prev_state,
                    curr.modality_state AS curr_state,
                    COUNT(*) AS count
                FROM viewer_year_summary curr
                JOIN viewer_year_summary prev 
                  ON curr.viewer_hash = prev.viewer_hash 
                 AND prev.interaction_year = {yr - 1}
                WHERE curr.interaction_year = {yr}
                GROUP BY 1, 2
            """).fetchall()
            retained_cnt = 0
            for r in trans_rows:
                p_st, c_st, c_num = r[0], r[1], r[2]
                key = f"{p_st.replace('_only','')}_to_{c_st.replace('_only','')}"
                if key in modality_transitions:
                    modality_transitions[key] = c_num
                retained_cnt += c_num
            modality_transitions["retained_from_prior_year"] = retained_cnt

        # Creator-size exposure (Top 5, Rank 6-20, Rank 21+)
        creator_exposure_row = con.execute(f"""
            WITH ranked_activity AS (
                SELECT 
                    act.viewer_hash,
                    BOOL_OR(rk.channel_rank <= 5) AS exp_top5,
                    BOOL_OR(rk.channel_rank BETWEEN 6 AND 20) AS exp_rank6_20,
                    BOOL_OR(rk.channel_rank > 20) AS exp_rank21plus
                FROM viewer_channel_year_activity act
                JOIN channel_yearly_rank rk 
                  ON act.vtuber_channel_id = rk.vtuber_channel_id 
                 AND act.interaction_year = rk.interaction_year
                WHERE act.interaction_year = {yr}
                GROUP BY 1
            )
            SELECT 
                COUNT(*) FILTER (WHERE exp_top5),
                COUNT(*) FILTER (WHERE exp_rank6_20),
                COUNT(*) FILTER (WHERE exp_rank21plus),
                COUNT(*) FILTER (WHERE exp_top5 AND NOT exp_rank6_20 AND NOT exp_rank21plus),
                COUNT(*) FILTER (WHERE exp_rank21plus AND NOT exp_top5 AND NOT exp_rank6_20)
            FROM ranked_activity
        """).fetchone()
        
        exp_top5_cnt, exp_rank6_20_cnt, exp_rank21p_cnt, excl_top5_cnt, excl_rank21p_cnt = creator_exposure_row

        # Construct comprehensive record
        time_window_label = f"{yr} (YTD / Partial)" if yr == 2026 else str(yr)
        
        row = {
            "year": yr,
            "time_window": time_window_label,
            "population_observed_accounts": total_accounts,
            # Timing
            "newly_observed_accounts": new_accounts,
            "pct_newly_observed": round((new_accounts / total_accounts) * 100, 2),
            "re_observed_accounts": reobserved_accounts,
            "pct_re_observed": round((reobserved_accounts / total_accounts) * 100, 2),
            "reactivated_accounts": reactivated,
            "pct_reactivated": round((reactivated / total_accounts) * 100, 2) if total_accounts > 0 else 0.0,
            "avg_reactivation_interval_years": avg_reactivation_interval,
            "multi_year_observed_accounts": multi_year,
            "pct_multi_year": round((multi_year / total_accounts) * 100, 2),
            # Breadth Percentiles
            "channels_per_account_p25": ch_p25,
            "channels_per_account_p50": ch_p50,
            "channels_per_account_p75": ch_p75,
            "channels_per_account_p90": ch_p90,
            "channels_per_account_p95": ch_p95,
            "communities_per_account_p50": comm_p50,
            "communities_per_account_p75": comm_p75,
            "communities_per_account_p90": comm_p90,
            "communities_per_account_p95": comm_p95,
            "agencies_per_account_p50": ag_p50,
            "agencies_per_account_p75": ag_p75,
            "agencies_per_account_p90": ag_p90,
            "agencies_per_account_p95": ag_p95,
            # Breadth Buckets
            "single_channel_observed": single_channel,
            "pct_single_channel": round((single_channel / total_accounts) * 100, 2),
            "two_channels_observed": two_channels,
            "pct_two_channels": round((two_channels / total_accounts) * 100, 2),
            "three_to_five_channels_observed": three_to_five_channels,
            "pct_three_to_five_channels": round((three_to_five_channels / total_accounts) * 100, 2),
            "six_to_ten_channels_observed": six_to_ten_channels,
            "pct_six_to_ten_channels": round((six_to_ten_channels / total_accounts) * 100, 2),
            "gt_ten_channels_observed": gt_ten_channels,
            "pct_gt_ten_channels": round((gt_ten_channels / total_accounts) * 100, 2),
            "multi_channel_observed": multi_channel,
            "pct_multi_channel": round((multi_channel / total_accounts) * 100, 2),
            "same_community_multi_channel": same_community_multi,
            "pct_same_community_multi": round((same_community_multi / total_accounts) * 100, 2),
            "cross_community_observed": cross_community,
            "pct_cross_community": round((cross_community / total_accounts) * 100, 2),
            "cross_agency_observed": cross_agency,
            "pct_cross_agency": round((cross_agency / total_accounts) * 100, 2),
            # Interaction Concentration
            "events_per_account_p50": ev_p50,
            "events_per_account_p75": ev_p75,
            "events_per_account_p90": ev_p90,
            "events_per_account_p95": ev_p95,
            "events_per_account_p99": ev_p99,
            "top_10pct_event_concentration_pct": top_10pct_event_share,
            # Modality
            "comment_only_observed": comment_only,
            "pct_comment_only": round((comment_only / total_accounts) * 100, 2),
            "live_chat_only_observed": chat_only,
            "pct_live_chat_only": round((chat_only / total_accounts) * 100, 2),
            "mixed_modality_observed": mixed_modality,
            "pct_mixed_modality": round((mixed_modality / total_accounts) * 100, 2),
            # Modality Transitions
            "prior_year_retention_count": modality_transitions["retained_from_prior_year"],
            "transition_comment_to_comment": modality_transitions["comment_to_comment"],
            "transition_comment_to_chat": modality_transitions["comment_to_chat"],
            "transition_comment_to_mixed": modality_transitions["comment_to_mixed"],
            "transition_chat_to_comment": modality_transitions["chat_to_comment"],
            "transition_chat_to_chat": modality_transitions["chat_to_chat"],
            "transition_chat_to_mixed": modality_transitions["chat_to_mixed"],
            "transition_mixed_to_comment": modality_transitions["mixed_to_comment"],
            "transition_mixed_to_chat": modality_transitions["mixed_to_chat"],
            "transition_mixed_to_mixed": modality_transitions["mixed_to_mixed"],
            # Creator-size exposure
            "accounts_exposed_top5_creators": exp_top5_cnt,
            "pct_accounts_exposed_top5": round((exp_top5_cnt / total_accounts) * 100, 2),
            "accounts_exposed_rank6_20_creators": exp_rank6_20_cnt,
            "pct_accounts_exposed_rank6_20": round((exp_rank6_20_cnt / total_accounts) * 100, 2),
            "accounts_exposed_rank21plus_creators": exp_rank21p_cnt,
            "pct_accounts_exposed_rank21plus": round((exp_rank21p_cnt / total_accounts) * 100, 2),
            "accounts_exclusive_top5_creators": excl_top5_cnt,
            "pct_accounts_exclusive_top5": round((excl_top5_cnt / total_accounts) * 100, 2),
            "accounts_exclusive_rank21plus_creators": excl_rank21p_cnt,
            "pct_accounts_exclusive_rank21plus": round((excl_rank21p_cnt / total_accounts) * 100, 2),
            # Metadata & Epistemic Contracts
            "privacy_class": "PUBLIC_RESEARCH_DATA",
            "k_anonymity_threshold_met": True,
            "limitation": "Measures pseudonymous accounts with recorded interaction in sampled content. Not unique human demographics. Not watch-time."
        }
        annual_metrics.append(row)
        
    con.close()
    
    df = pd.DataFrame(annual_metrics)
    logger.info("Audience behavior yearly summary derived:")
    logger.info(df[["year", "population_observed_accounts", "pct_newly_observed", "channels_per_account_p90", "top_10pct_event_concentration_pct", "pct_accounts_exposed_top5"]])
    
    # Save Parquet
    df.to_parquet(OUT_PARQUET, index=False)
    logger.info(f"Saved {OUT_PARQUET}")
    
    # Save JSON for direct consumption
    json_payload = {
        "metadata": {
            "title": "Yearly Behavioral Audience Segments (Aggregate)",
            "updated_at": NOW_ISO,
            "privacy_class": "PUBLIC_RESEARCH_DATA",
            "observation_window": "2020-2026_YTD",
            "methodology": "k-anonymized aggregate counts and distributions of pseudonymous accounts in sampled public comments and live chats.",
            "caveat": "Behavioral segments reflect interaction patterns across channels, NOT demographic attributes."
        },
        "annual_segments": annual_metrics
    }
    OUT_JSON.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    logger.info(f"Saved {OUT_JSON}")


if __name__ == "__main__":
    compute_audience_behavior_aggregates()
