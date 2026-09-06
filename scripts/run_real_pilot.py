"""
Thai VTuber Audience Network (SNA)
Real Pilot Pipeline Runner (Enhanced & Corrected)

Key Features:
1. Validates real YouTube viewer presence across 5-6 Thai VTuber channels.
2. Automatically replaces channels/videos if a target has no usable public comments/chat.
3. Implements EARLY AGGREGATION per video (viewer_hash, vtuber_channel_id, video_id, first_seen, last_seen, appearances, source_type).
4. Demonstrates cross-channel HMAC-SHA256 viewer identity matching.
5. Runs DuckDB OLAP and NetworkX SNA.
6. Exports real graph to data/real/analytics/network_graph.json tagged with is_demo: false.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Dict, Any, List

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import BASE_DIR
from core.hasher import hash_viewer
from core.filter_engine import FirstFilterEngine
from collector.youtube_collector import YouTubeCollector
from storage.parquet_manager import ParquetStorageManager
from storage.duckdb_engine import DuckDBAnalyticsEngine
from analytics.network_graph import VTuberNetworkAnalyzer
from analytics.exporter import NetworkExporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("RealPilotSNA")

# Target Pool of Real Thai VTuber Channels (with fallback options)
CANDIDATE_POOL = [
    {"channel_id": "UCqhhWjpw23dWhJ5rRwCCrMA", "name": "Aisha Channel", "agency": "Independent", "video_id": "G1LXXzZx48c"},
    {"channel_id": "UCuZ1ajvlGFUMCHZAPdetKHw", "name": "Dacapo Ch.【ARP】", "agency": "Algorhythm Project", "video_id": "5o4H5e3QLk0"},
    {"channel_id": "UCAr4U_HGMYXn1EZjdWiGSLQ", "name": "Baabel Ch.【ARP】", "agency": "Algorhythm Project", "video_id": "FASPZW15oSo"},
    {"channel_id": "UCNTEr2_96vJnXNazr5MwNLA", "name": "Schneider Ch.【ARP】", "agency": "Algorhythm Project", "video_id": "D3TxwjyV2I8"},
    {"channel_id": "UCEvyDOkcGkzCTo62d9BrhkA", "name": "Minami Cera Polygon", "agency": "Polygon Official", "video_id": "EAmImNNAQSQ"},
    {"channel_id": "UCfcNIwkAhHcDTP1rQg2n5nw", "name": "Tiara Rexa Polygon", "agency": "Polygon Official", "video_id": "0Txm89An9Io"},
    {"channel_id": "UCO6R8Pc5g2R7ObJQPBGppdg", "name": "Baku Ch.【ARP】", "agency": "Algorhythm Project", "video_id": "6iPQ-V8a3E8"}
]

# Dedicated Real Data Directory
REAL_DATA_DIR = BASE_DIR / "data" / "real"
REAL_EVENTS_DIR = REAL_DATA_DIR / "events"
REAL_ANALYTICS_DIR = REAL_DATA_DIR / "analytics"

for d in [REAL_DATA_DIR, REAL_EVENTS_DIR, REAL_ANALYTICS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def run_real_pilot(target_channel_count: int = 6, force_refresh: bool = False):
    logger.info("==================================================")
    logger.info("   Starting Thai VTuber SNA Real Pilot Pipeline   ")
    logger.info("==================================================")

    collector = YouTubeCollector()
    parquet_mgr = ParquetStorageManager(base_dir=REAL_EVENTS_DIR)
    filter_engine = FirstFilterEngine()

    active_vtubers = []
    channel_viewers_map: Dict[str, set] = {}
    total_aggregated_records = 0

    existing_parquet = list(REAL_EVENTS_DIR.glob("**/*.parquet"))
    use_existing = len(existing_parquet) >= target_channel_count and not force_refresh

    if use_existing:
        logger.info(f"Found {len(existing_parquet)} existing Parquet files. Loading existing pilot data...")
        import pyarrow.parquet as pq
        for p in existing_parquet:
            tab = pq.read_table(p)
            cid = tab["vtuber_channel_id"][0].as_py()
            hashes = set(tab["viewer_hash"].to_pylist())
            channel_viewers_map[cid] = hashes
            total_aggregated_records += len(tab)
            cand = next((c for c in CANDIDATE_POOL if c["channel_id"] == cid), {"name": cid, "agency": "Independent"})
            cname = cand["name"]
            status, conf, _ = filter_engine.evaluate_candidate(cand)
            active_vtubers.append({
                "channel_id": cid,
                "handle": f"@{cname.replace(' ', '')}",
                "name": cname,
                "agency": cand.get("agency", "Independent"),
                "subscriber_count": 0,
                "status": status,
                "priority": "S"
            })
    else:
        # Process candidates until target_channel_count usable channels are collected
        for cand in CANDIDATE_POOL:
            if len(active_vtubers) >= target_channel_count:
                break

            cid = cand["channel_id"]
            cname = cand["name"]
            vid = cand.get("video_id") or collector.fetch_latest_video_for_channel(cid)

            if not vid:
                logger.warning(f"No video found for {cname}. Trying next candidate...")
                continue

            logger.info(f"Collecting real presence for {cname} (Video: {vid})...")
            job = {"vtuber_channel_id": cid, "video_id": vid}
            
            # EARLY AGGREGATION: Collect per-video aggregated session schema
            agg_events = collector.collect_aggregated_events(job, max_comments=120)

            # Automatic replacement rule: If no usable events extracted, skip & replace
            if not agg_events or len(agg_events) == 0:
                logger.warning(f"No usable public comments/events on {cname} ({vid}). Automatically replacing...")
                continue

            # Save early aggregated presence to Parquet
            parquet_mgr.write_events(agg_events)
            total_aggregated_records += len(agg_events)
            
            unique_hashes = set(e["viewer_hash"] for e in agg_events)
            channel_viewers_map[cid] = unique_hashes

            status, conf, _ = filter_engine.evaluate_candidate(cand)
            active_vtubers.append({
                "channel_id": cid,
                "handle": f"@{cname.replace(' ', '')}",
                "name": cname,
                "agency": cand.get("agency", "Independent"),
                "subscriber_count": 0,
                "status": status,
                "priority": "S"
            })
            logger.info(f" -> Successfully recorded {len(agg_events)} early-aggregated viewer records for {cname}.")

    logger.info(f"Pilot data loaded: {len(active_vtubers)} channels with {total_aggregated_records} aggregated presence records.")

    # 3. Prove Cross-Channel HMAC-SHA256 Consistency
    logger.info("--- Demonstrating Cross-Channel HMAC-SHA256 Viewer Overlap ---")
    shared_occurrences = []
    cids = list(channel_viewers_map.keys())

    for i in range(len(cids)):
        for j in range(i + 1, len(cids)):
            ca, cb = cids[i], cids[j]
            na = next(v["name"] for v in active_vtubers if v["channel_id"] == ca)
            nb = next(v["name"] for v in active_vtubers if v["channel_id"] == cb)
            common = channel_viewers_map[ca].intersection(channel_viewers_map[cb])
            
            if common:
                shared_occurrences.append((na, nb, len(common), list(common)[0]))
                logger.info(f" [EVIDENCE] Overlap between {na} and {nb}: {len(common)} shared viewers!")
                logger.info(f"            Sample deterministic viewer_hash: {list(common)[0][:16]}... (Length: {len(list(common)[0])})")

    # 4. DuckDB OLAP Overlap Analysis with Source Separation & Strong Evidence
    duckdb_engine = DuckDBAnalyticsEngine(
        db_path=REAL_DATA_DIR / "real_analytics.duckdb",
        events_dir=REAL_EVENTS_DIR
    )
    overlap_matrix = duckdb_engine.compute_pairwise_overlap(min_shared_viewers=1, min_evidence_threshold=2)
    logger.info(f"DuckDB computed {len(overlap_matrix)} pairwise audience overlap links.")
    for p in overlap_matrix:
        logger.info(
            f" [PAIR] {p['vtuber_a'][:10]}.. - {p['vtuber_b'][:10]}.. | "
            f"shared_any: {p['shared_any']} | shared_comments: {p['shared_comments']} | "
            f"shared_live_chat: {p['shared_live_chat']} | strong_shared_any: {p['strong_shared_any']}"
        )

    # 5. NetworkX SNA Analysis
    analyzer = VTuberNetworkAnalyzer()
    graph = analyzer.build_graph(
        vtubers=active_vtubers,
        pairwise_overlap=overlap_matrix,
        weight_metric="shared_viewers",
        min_weight_threshold=1.0
    )

    centralities = analyzer.compute_centralities()
    communities = analyzer.detect_communities()
    top_bridges = analyzer.find_top_bridges(top_k=3)

    logger.info("--- Top Bridge VTubers in Real Pilot ---")
    for r, (bid, bname, score) in enumerate(top_bridges, 1):
        logger.info(f" #{r}: {bname} (Betweenness Centrality: {score:.4f})")

    # 6. Export Real Network Graph JSON (Goal 7: Tagged as is_demo: false)
    exporter = NetworkExporter(output_dir=REAL_ANALYTICS_DIR)
    real_graph_path = exporter.export_web_json(graph, filename="network_graph.json")

    # Inject explicit metadata tag: is_demo = false
    with open(real_graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)
    
    graph_data["metadata"]["is_demo"] = False
    graph_data["metadata"]["dataset_tag"] = "real_youtube_pilot_v1"
    graph_data["metadata"]["generated_at"] = datetime.now(timezone.utc).isoformat()
    graph_data["metadata"]["channels_monitored"] = len(active_vtubers)
    graph_data["metadata"]["total_shared_pairs"] = len(overlap_matrix)

    with open(real_graph_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)

    logger.info("==================================================")
    logger.info(" Real Pilot Successfully Completed!              ")
    logger.info(f" Channels Monitored:    {len(active_vtubers)}")
    logger.info(f" Real Events Directory: {REAL_EVENTS_DIR}")
    logger.info(f" Real Network Graph:    {real_graph_path}")
    logger.info("==================================================")

    return {
        "channels_count": len(active_vtubers),
        "total_aggregated_records": total_aggregated_records,
        "shared_occurrences": shared_occurrences,
        "overlap_matrix": overlap_matrix,
        "real_graph_path": real_graph_path
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Thai VTuber SNA Real Pilot Pipeline")
    parser.add_argument("--channels", type=int, default=6, help="Target number of channels to analyze")
    parser.add_argument("--refresh", action="store_true", help="Force re-extraction of video data from YouTube")
    args = parser.parse_args()

    run_real_pilot(target_channel_count=args.channels, force_refresh=args.refresh)
