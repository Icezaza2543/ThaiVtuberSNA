"""
Phase T7 Regression Suite: Temporal Community Evolution & Audience Migration Analytics
Tests:
1. Identical input -> identical communities (deterministic weighted Louvain with seed=42)
2. Synthetic lineage events: persistence, birth, disappearance, split, merge
3. Audience transition direction (strictly t -> t+1)
4. Self-retention separated from cross-channel transitions
5. Repeated interactions within a year do not inflate viewer counts
6. Interaction_at only; video_published_at fallback is never used
7. Zero viewer_hash exported in any public/aggregate parquet or report
8. Provenance precedence remains intact (T6 deep > T5 > T2 > legacy)
"""

import networkx as nx
import pyarrow.parquet as pq
import pytest
from datetime import datetime, timezone
import duckdb
from pathlib import Path

from scripts.analyze_temporal_communities import (
    detect_communities_for_year,
    compute_lineage_events,
)
from scripts.build_duckdb_temporal_snapshots import (
    build_canonical_events_view,
    build_unified_raw_view,
)


def test_deterministic_community_detection_identical_input():
    """Identical network graph input must produce identical communities and modularity across multiple runs."""
    G = nx.Graph()
    # Create a 2-cluster graph with a bridge
    for i in range(1, 6):
        for j in range(i + 1, 6):
            G.add_edge(f"node_a_{i}", f"node_a_{j}", weight=10)
    for i in range(1, 6):
        for j in range(i + 1, 6):
            G.add_edge(f"node_b_{i}", f"node_b_{j}", weight=10)
    # Bridge edge
    G.add_edge("node_a_5", "node_b_1", weight=1)

    comms_first, mod_first = detect_communities_for_year(2024, G, seed=42)

    for run_idx in range(5):
        comms, mod = detect_communities_for_year(2024, G, seed=42)
        assert len(comms) == len(comms_first), f"Run {run_idx}: community count mismatch"
        assert abs(mod - mod_first) < 1e-9, f"Run {run_idx}: modularity mismatch"
        for c1, c2 in zip(comms_first, comms):
            assert c1 == c2, f"Run {run_idx}: community membership mismatch"


def test_lineage_pure_persistence():
    """Stable community with identical membership across adjacent years must be classified as persistent."""
    yearly_comms = {
        2024: {"comm_2024_01": {"ch1", "ch2", "ch3", "ch4", "ch5"}},
        2025: {"comm_2025_01": {"ch1", "ch2", "ch3", "ch4", "ch5"}},
    }
    events = compute_lineage_events(yearly_comms)
    persistent = [e for e in events if e["event_type"] == "persistent"]
    assert len(persistent) == 1
    p = persistent[0]
    assert p["from_community_id"] == "comm_2024_01"
    assert p["to_community_id"] == "comm_2025_01"
    assert p["jaccard_similarity"] == 1.0
    assert p["forward_overlap_ratio"] == 1.0
    assert p["backward_overlap_ratio"] == 1.0


def test_lineage_community_birth():
    """Community in year t+1 consisting of brand new channels must be classified as a birth."""
    yearly_comms = {
        2024: {"comm_2024_01": {"ch1", "ch2", "ch3", "ch4"}},
        2025: {
            "comm_2025_01": {"ch1", "ch2", "ch3", "ch4"},
            "comm_2025_02": {"ch10", "ch11", "ch12", "ch13"},  # all new
        },
    }
    events = compute_lineage_events(yearly_comms)
    births = [e for e in events if e["event_type"] == "birth"]
    assert any(b["to_community_id"] == "comm_2025_02" for b in births)


def test_lineage_community_disappearance():
    """Community in year t whose members cease to exist in year t+1 must be classified as disappearance."""
    yearly_comms = {
        2024: {
            "comm_2024_01": {"ch1", "ch2", "ch3", "ch4"},
            "comm_2024_02": {"ch90", "ch91", "ch92", "ch93"},  # will vanish
        },
        2025: {"comm_2025_01": {"ch1", "ch2", "ch3", "ch4"}},
    }
    events = compute_lineage_events(yearly_comms)
    disappearances = [e for e in events if e["event_type"] == "disappearance"]
    assert any(d["from_community_id"] == "comm_2024_02" for d in disappearances)


def test_lineage_community_split():
    """Community in year t dividing substantially into >= 2 communities in year t+1 must be detected as split_branch."""
    yearly_comms = {
        2024: {"comm_2024_01": {"ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8"}},
        2025: {
            "comm_2025_01": {"ch1", "ch2", "ch3", "ch4"},  # 50%
            "comm_2025_02": {"ch5", "ch6", "ch7", "ch8"},  # 50%
        },
    }
    events = compute_lineage_events(yearly_comms)
    splits = [e for e in events if e["event_type"] == "split_branch"]
    assert len(splits) == 2
    targets = {s["to_community_id"] for s in splits}
    assert targets == {"comm_2025_01", "comm_2025_02"}


def test_lineage_community_merge():
    """Target community in year t+1 formed from >= 2 communities from year t must be detected as merge_tributary."""
    yearly_comms = {
        2024: {
            "comm_2024_01": {"ch1", "ch2", "ch3", "ch4"},
            "comm_2024_02": {"ch5", "ch6", "ch7", "ch8"},
        },
        2025: {"comm_2025_01": {"ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8"}},
    }
    events = compute_lineage_events(yearly_comms)
    merges = [e for e in events if e["event_type"] == "merge_tributary"]
    assert len(merges) == 2
    sources = {m["from_community_id"] for m in merges}
    assert sources == {"comm_2024_01", "comm_2024_02"}


def test_lineage_no_birth_when_significant_split_predecessor_exists():
    """A target community that is a branch of a split must NEVER be classified as a birth."""
    yearly_comms = {
        2024: {"comm_2024_01": {"ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8"}},
        2025: {
            "comm_2025_01": {"ch1", "ch2", "ch3", "ch4"},  # 50% split branch
            "comm_2025_02": {"ch5", "ch6", "ch7", "ch8"},  # 50% split branch
        },
    }
    events = compute_lineage_events(yearly_comms)
    births = [e for e in events if e["event_type"] == "birth"]
    assert len(births) == 0, f"Expected 0 births for split targets, got {births}"


def test_lineage_no_disappearance_when_significant_successor_exists():
    """A source community that splits or merges into target communities must NEVER be classified as a disappearance."""
    yearly_comms = {
        2024: {"comm_2024_01": {"ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8"}},
        2025: {
            "comm_2025_01": {"ch1", "ch2", "ch3", "ch4"},
            "comm_2025_02": {"ch5", "ch6", "ch7", "ch8"},
        },
    }
    events = compute_lineage_events(yearly_comms)
    disapps = [e for e in events if e["event_type"] == "disappearance"]
    assert len(disapps) == 0, f"Expected 0 disappearances for split source, got {disapps}"


def test_true_active_channel_count_distinct_union():
    """Active channel count must be the true distinct union of vtuber_a and vtuber_b, not double counting."""
    df_metrics = pq.read_table("data/temporal/analysis/yearly_network_metrics.parquet").to_pandas()
    df_snaps = pq.read_table("data/temporal/snapshots/network_snapshots.parquet").to_pandas()
    yearly_snaps = df_snaps[df_snaps["window_type"] == "yearly"]

    for _, row in df_metrics.iterrows():
        yr = int(row["year"])
        sub = yearly_snaps[yearly_snaps["window_start"].str.startswith(str(yr))]
        if sub.empty:
            continue
        true_unique = set(sub["vtuber_a"]).union(set(sub["vtuber_b"]))
        reported_active = int(row["active_channels"])
        assert reported_active == len(true_unique), f"Year {yr}: expected {len(true_unique)} channels, got {reported_active}"


def test_retention_rate_mathematical_invariants():
    """Retention rate formulas must hold mathematically without denominator conflation."""
    df_metrics = pq.read_table("data/temporal/analysis/yearly_network_metrics.parquet").to_pandas()
    for _, row in df_metrics.iterrows():
        yr = int(row["year"])
        if yr == 2026:  # Final year has no adjacent t+1 window
            continue
        act_t = int(row["active_viewers_t"])
        act_t1 = int(row["active_viewers_t1"])
        cont_any = int(row["continuing_viewers_any"])
        ret = int(row["same_channel_retained_viewers"])
        cont_rate = float(row["continuation_rate"])
        ret_rate = float(row["same_channel_retention_rate"])
        cond_rate = float(row["conditional_same_channel_rate"])

        assert act_t > 0
        assert act_t1 > 0
        assert cont_any <= act_t
        assert ret <= cont_any
        assert ret_rate <= cont_rate, "same_channel_retention_rate must be <= continuation_rate"
        assert abs(cont_rate - (cont_any / act_t)) < 0.001
        assert abs(ret_rate - (ret / act_t)) < 0.001
        assert abs(cond_rate - (ret / cont_any)) < 0.001


def test_no_duplicate_lineage_labels_in_actual_dataset():
    """In actual community_lineage.parquet, no community target can be both birth and target of relation."""
    df_lineage = pq.read_table("data/temporal/analysis/community_lineage.parquet").to_pandas()
    birth_targets = set(df_lineage[df_lineage["event_type"] == "birth"]["to_community_id"])
    relation_targets = set(df_lineage[df_lineage["event_category"] == "relation"]["to_community_id"])
    conflicts = birth_targets & relation_targets
    assert len(conflicts) == 0, f"Conflicting birth and relation targets: {conflicts}"

    disapp_sources = set(df_lineage[df_lineage["event_type"] == "disappearance"]["from_community_id"])
    relation_sources = set(df_lineage[df_lineage["event_category"] == "relation"]["from_community_id"])
    disapp_conflicts = disapp_sources & relation_sources
    assert len(disapp_conflicts) == 0, f"Conflicting disappearance and relation sources: {disapp_conflicts}"


def test_audience_transition_direction_and_separation():
    """
    Transition analytics must:
    - Flow strictly from year t to year t+1.
    - Strictly separate same_channel_retention from cross-channel migration.
    """
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE raw_test (
            viewer_hash VARCHAR,
            vtuber_channel_id VARCHAR,
            video_id VARCHAR,
            source_type VARCHAR,
            interaction_at VARCHAR,
            first_seen VARCHAR,
            timestamp VARCHAR,
            video_published_at VARCHAR,
            provenance VARCHAR,
            priority INT
        )
    """)

    # V1: Same channel retention in 2023 -> 2024
    con.execute("INSERT INTO raw_test VALUES ('v1', 'ch1', 'vid1', 'comment', '2023-05-01T00:00:00Z', NULL, NULL, NULL, 't5', 2)")
    con.execute("INSERT INTO raw_test VALUES ('v1', 'ch1', 'vid2', 'comment', '2024-05-01T00:00:00Z', NULL, NULL, NULL, 't5', 2)")

    # V2: Cross channel transition in 2023 -> 2024 (ch1 -> ch2)
    con.execute("INSERT INTO raw_test VALUES ('v2', 'ch1', 'vid1', 'comment', '2023-05-01T00:00:00Z', NULL, NULL, NULL, 't5', 2)")
    con.execute("INSERT INTO raw_test VALUES ('v2', 'ch2', 'vid3', 'comment', '2024-05-01T00:00:00Z', NULL, NULL, NULL, 't5', 2)")

    # V3: Active in 2024 only
    con.execute("INSERT INTO raw_test VALUES ('v3', 'ch1', 'vid2', 'comment', '2024-05-01T00:00:00Z', NULL, NULL, NULL, 't5', 2)")

    build_canonical_events_view(con, source_table_or_view="raw_test")

    # Ephemeral transitions
    con.execute("""
        CREATE TEMP TABLE viewer_years AS
        SELECT DISTINCT viewer_hash, CAST(extract(year FROM interaction_time) AS INT) AS yr, vtuber_channel_id
        FROM canonical_events
        WHERE interaction_time IS NOT NULL
    """)

    transitions = con.execute("""
        SELECT 
            v1.yr AS from_year,
            v2.yr AS to_year,
            v1.vtuber_channel_id AS from_ch,
            v2.vtuber_channel_id AS to_ch,
            CASE WHEN v1.vtuber_channel_id = v2.vtuber_channel_id THEN 'retention' ELSE 'cross' END AS t_type,
            COUNT(DISTINCT v1.viewer_hash) AS viewer_cnt
        FROM viewer_years v1
        JOIN viewer_years v2 ON v1.viewer_hash = v2.viewer_hash AND v2.yr = v1.yr + 1
        GROUP BY 1, 2, 3, 4, 5
        ORDER BY 1, 3, 4
    """).df()

    assert len(transitions) == 2
    # 2023 -> 2024 retention
    ret = transitions[(transitions["from_ch"] == "ch1") & (transitions["to_ch"] == "ch1")]
    assert len(ret) == 1
    assert ret["viewer_cnt"].iloc[0] == 1
    assert ret["t_type"].iloc[0] == "retention"

    # 2023 -> 2024 cross-channel
    cross = transitions[(transitions["from_ch"] == "ch1") & (transitions["to_ch"] == "ch2")]
    assert len(cross) == 1
    assert cross["viewer_cnt"].iloc[0] == 1
    assert cross["t_type"].iloc[0] == "cross"


def test_repeated_interactions_do_not_inflate_viewer_counts():
    """A viewer with 100 comments on the same channel in a year must count as exactly 1 in transitions."""
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE raw_test (
            viewer_hash VARCHAR,
            vtuber_channel_id VARCHAR,
            video_id VARCHAR,
            source_type VARCHAR,
            interaction_at VARCHAR,
            first_seen VARCHAR,
            timestamp VARCHAR,
            video_published_at VARCHAR,
            provenance VARCHAR,
            priority INT
        )
    """)

    # 50 interactions on ch1 in 2023
    for i in range(50):
        con.execute(f"INSERT INTO raw_test VALUES ('active_user', 'ch1', 'vid_{i}', 'comment', '2023-05-01T00:00:00Z', NULL, NULL, NULL, 't5', 2)")
    # 20 interactions on ch2 in 2024
    for i in range(20):
        con.execute(f"INSERT INTO raw_test VALUES ('active_user', 'ch2', 'vid_new_{i}', 'comment', '2024-05-01T00:00:00Z', NULL, NULL, NULL, 't5', 2)")

    build_canonical_events_view(con, source_table_or_view="raw_test")

    con.execute("""
        CREATE TEMP TABLE viewer_years AS
        SELECT DISTINCT viewer_hash, CAST(extract(year FROM interaction_time) AS INT) AS yr, vtuber_channel_id
        FROM canonical_events
        WHERE interaction_time IS NOT NULL
    """)

    res = con.execute("""
        SELECT COUNT(DISTINCT v1.viewer_hash) AS distinct_viewers, COUNT(*) AS transition_rows
        FROM viewer_years v1
        JOIN viewer_years v2 ON v1.viewer_hash = v2.viewer_hash AND v2.yr = v1.yr + 1
    """).fetchall()

    assert res[0][0] == 1, "Distinct viewer count must be exactly 1"
    assert res[0][1] == 1, "Transition rows must be exactly 1"


def test_interaction_timestamp_strictly_required_no_published_fallback():
    """Events with NULL interaction timestamps must not enter temporal analysis even if published_at exists."""
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE raw_test (
            viewer_hash VARCHAR,
            vtuber_channel_id VARCHAR,
            video_id VARCHAR,
            source_type VARCHAR,
            interaction_at VARCHAR,
            first_seen VARCHAR,
            timestamp VARCHAR,
            video_published_at VARCHAR,
            provenance VARCHAR,
            priority INT
        )
    """)

    # Only video_published_at, NO interaction_at
    con.execute("INSERT INTO raw_test VALUES ('v_missing', 'ch1', 'vid1', 'comment', NULL, NULL, NULL, '2023-01-01T00:00:00Z', 't5', 2)")

    build_canonical_events_view(con, source_table_or_view="raw_test")

    dated_events = con.execute("""
        SELECT * FROM canonical_events WHERE interaction_time IS NOT NULL
    """).fetchall()

    assert len(dated_events) == 0, "Event without interaction timestamp must not have interaction_time"


def test_no_pii_exported_in_analysis_artifacts():
    """All generated parquet files in data/temporal/analysis/ must contain ZERO viewer_hash columns."""
    analysis_dir = Path("data/temporal/analysis")
    parquet_files = list(analysis_dir.glob("*.parquet"))
    assert len(parquet_files) >= 4, "Expected at least 4 analysis parquet files"

    for pf in parquet_files:
        tbl = pq.read_table(pf)
        assert "viewer_hash" not in tbl.column_names, f"PII LEAK in {pf.name}: viewer_hash found"
        for col in tbl.column_names:
            assert "author" not in col.lower(), f"PII LEAK in {pf.name}: {col} found"
            assert "comment" not in col.lower() or "jaccard" in col.lower() or "shared" in col.lower() or "community" in col.lower(), f"Suspicious column {col} in {pf.name}"


def test_provenance_precedence_intact_in_canonical_events():
    """T6 deep comments must take priority over T5 stratified and T2 pilot for the same video."""
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE raw_test (
            viewer_hash VARCHAR,
            vtuber_channel_id VARCHAR,
            video_id VARCHAR,
            source_type VARCHAR,
            interaction_at VARCHAR,
            first_seen VARCHAR,
            timestamp VARCHAR,
            video_published_at VARCHAR,
            provenance VARCHAR,
            priority INT
        )
    """)

    # T6 observation for (ch1, vid1)
    con.execute("INSERT INTO raw_test VALUES ('v_t6', 'ch1', 'vid1', 'comment', '2024-06-01T00:00:00Z', NULL, NULL, NULL, 't6_deep', 1)")
    # T5 observation for same (ch1, vid1)
    con.execute("INSERT INTO raw_test VALUES ('v_t5', 'ch1', 'vid1', 'comment', '2024-06-01T00:00:00Z', NULL, NULL, NULL, 't5_stratified', 2)")
    # T2 observation for same (ch1, vid1)
    con.execute("INSERT INTO raw_test VALUES ('v_t2', 'ch1', 'vid1', 'comment', '2024-06-01T00:00:00Z', NULL, NULL, NULL, 't2_pilot', 3)")

    build_canonical_events_view(con, source_table_or_view="raw_test")

    rows = con.execute("SELECT viewer_hash, provenance FROM canonical_events WHERE vtuber_channel_id = 'ch1' AND video_id = 'vid1'").fetchall()
    assert len(rows) == 1, "Expected only T6 row to survive precedence filtering"
    assert rows[0][0] == "v_t6"
    assert rows[0][1] == "t6_deep"
