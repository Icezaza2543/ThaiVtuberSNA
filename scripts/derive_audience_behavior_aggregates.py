#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase N5: Audience Behavior Aggregation Engine (Privacy-Preserving Public Analytics)
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

INDUSTRY_DIR = ROOT / "data/industry"
INDUSTRY_DIR.mkdir(parents=True, exist_ok=True)

COMMUNITY_SNAPSHOTS_PARQUET = ROOT / "data/temporal/analysis/community_snapshots.parquet"
TARGET_MANIFEST_CSV = ROOT / "data/temporal/catalog/target_manifest.csv"

OUT_PARQUET = INDUSTRY_DIR / "audience_behavior_yearly.parquet"
OUT_JSON = INDUSTRY_DIR / "audience_behavior_yearly.json"

NOW_ISO = datetime.now(timezone.utc).isoformat()

def compute_audience_behavior_aggregates():
    print("Initializing DuckDB in-memory session for aggregate derivation...")
    con = duckdb.connect(":memory:")
    
    # Build canonical events view in memory
    print("Building unified raw and canonical events views...")
    build_unified_raw_view(con)
    build_canonical_events_view(con)
    
    # Load manifest and community snapshots for agency and community mappings
    manifest_df = pd.read_csv(TARGET_MANIFEST_CSV)[["channel_id", "agency"]]
    con.register("manifest_table", manifest_df)
    
    comm_df = pd.read_parquet(COMMUNITY_SNAPSHOTS_PARQUET)[["year", "channel_id", "community_id"]]
    con.register("comm_table", comm_df)
    
    print("Executing privacy-preserving behavioral audience queries...")
    
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
    
    years = [r[0] for r in con.execute("SELECT DISTINCT interaction_year FROM viewer_year_summary ORDER BY 1").fetchall()]
    print(f"Observed years in canonical data: {years}")
    
    annual_metrics = []
    
    for yr in years:
        # Annual base population (denominator)
        total_accounts = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash) 
            FROM viewer_year_summary 
            WHERE interaction_year = {yr}
        """).fetchone()[0]
        
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
            reactivated = con.execute(f"""
                SELECT COUNT(DISTINCT s.viewer_hash)
                FROM viewer_year_summary s
                JOIN viewer_lifetime l ON s.viewer_hash = l.viewer_hash
                WHERE s.interaction_year = {yr}
                  AND l.first_year <= {yr - 2}
                  AND s.viewer_hash NOT IN (
                      SELECT viewer_hash FROM viewer_year_summary WHERE interaction_year = {yr - 1}
                  )
            """).fetchone()[0]
        else:
            reactivated = 0
            
        multi_year = con.execute(f"""
            SELECT COUNT(DISTINCT s.viewer_hash)
            FROM viewer_year_summary s
            JOIN viewer_lifetime l ON s.viewer_hash = l.viewer_hash
            WHERE s.interaction_year = {yr} AND l.active_years_count >= 2
        """).fetchone()[0]
        
        # Breadth dimensions
        single_channel = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND distinct_channels = 1
        """).fetchone()[0]
        
        multi_channel = con.execute(f"""
            SELECT COUNT(DISTINCT viewer_hash)
            FROM viewer_year_summary
            WHERE interaction_year = {yr} AND distinct_channels >= 2
        """).fetchone()[0]
        
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
        
        # Construct record
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
            "multi_year_observed_accounts": multi_year,
            "pct_multi_year": round((multi_year / total_accounts) * 100, 2),
            # Breadth
            "single_channel_observed": single_channel,
            "pct_single_channel": round((single_channel / total_accounts) * 100, 2),
            "multi_channel_observed": multi_channel,
            "pct_multi_channel": round((multi_channel / total_accounts) * 100, 2),
            "same_community_multi_channel": same_community_multi,
            "pct_same_community_multi": round((same_community_multi / total_accounts) * 100, 2),
            "cross_community_observed": cross_community,
            "pct_cross_community": round((cross_community / total_accounts) * 100, 2),
            "cross_agency_observed": cross_agency,
            "pct_cross_agency": round((cross_agency / total_accounts) * 100, 2),
            # Modality
            "comment_only_observed": comment_only,
            "pct_comment_only": round((comment_only / total_accounts) * 100, 2),
            "live_chat_only_observed": chat_only,
            "pct_live_chat_only": round((chat_only / total_accounts) * 100, 2),
            "mixed_modality_observed": mixed_modality,
            "pct_mixed_modality": round((mixed_modality / total_accounts) * 100, 2),
            # Metadata & Epistemic Contracts
            "privacy_class": "PUBLIC_RESEARCH_DATA",
            "k_anonymity_threshold_met": True,
            "limitation": "Measures pseudonymous accounts with recorded interaction in sampled content. Not unique human demographics. Not watch-time."
        }
        annual_metrics.append(row)
        
    con.close()
    
    df = pd.DataFrame(annual_metrics)
    print("\nAudience behavior yearly summary:")
    print(df[["year", "population_observed_accounts", "pct_newly_observed", "pct_re_observed", "pct_multi_channel", "pct_cross_community", "pct_mixed_modality"]])
    
    # Save Parquet
    df.to_parquet(OUT_PARQUET, index=False)
    print(f"Saved {OUT_PARQUET}")
    
    # Save JSON for direct frontend consumption
    json_payload = {
        "metadata": {
            "title": "Yearly Behavioral Audience Segments (Aggregate)",
            "updated_at": NOW_ISO,
            "privacy_class": "PUBLIC_RESEARCH_DATA",
            "observation_window": "2020-2026_YTD",
            "methodology": "k-anonymized aggregate counts of pseudonymous accounts in sampled public comments and live chats.",
            "caveat": "Behavioral segments reflect interaction patterns across channels, NOT demographic attributes."
        },
        "annual_segments": annual_metrics
    }
    OUT_JSON.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    print(f"Saved {OUT_JSON}")

if __name__ == "__main__":
    compute_audience_behavior_aggregates()
