"""
Thai VTuber Audience Network (SNA)
Main Orchestrator & CLI Runner

Provides end-to-end execution of the Thai VTuber SNA pipeline:
Discovery -> First Filter -> Registry -> Priority & PSO -> Collector -> Parquet -> DuckDB -> SNA -> Web Export
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

from config.settings import (
    BASE_DIR, DATA_DIR, ANALYTICS_DIR, DEFAULT_WORKERS,
    SCHEDULER_WEIGHTS, GOOGLE_SHEETS_CONFIG
)
from core.hasher import hash_viewer
from core.filter_engine import FirstFilterEngine
from core.priority import get_subscriber_tier, compute_priority_score
from core.registry import RegistryManager
from core.scheduler import BaselinePriorityQueueScheduler, PSOScheduler
from collector.discovery_adapter import DiscoveryAdapter
from collector.mock_collector import MockCollector
from collector.youtube_collector import YouTubeCollector
from storage.parquet_manager import ParquetStorageManager
from storage.duckdb_engine import DuckDBAnalyticsEngine
from analytics.network_graph import VTuberNetworkAnalyzer
from analytics.exporter import NetworkExporter

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("ThaiVtuberSNA")


class ThaiVtuberSNASystem:
    def __init__(self):
        self.registry = RegistryManager()
        self.filter_engine = FirstFilterEngine()
        self.discovery = DiscoveryAdapter()
        self.parquet_mgr = ParquetStorageManager()
        self.duckdb_engine = DuckDBAnalyticsEngine()
        self.network_analyzer = VTuberNetworkAnalyzer()
        self.exporter = NetworkExporter()

    def step_discovery(self, seed_path: Path = None) -> List[Dict[str, Any]]:
        """Step 1: Discovery from Directory Sources & Deduplication."""
        logger.info("=== STEP 1: VTuber Discovery & Ingestion ===")
        seed_file = seed_path or (BASE_DIR / "config" / "seeds_vtuber.json")
        raw_candidates = self.discovery.load_from_json(seed_file)
        
        # Deduplicate strictly by Channel ID
        deduped = self.discovery.discover_and_deduplicate([raw_candidates])
        logger.info(f"Discovered {len(deduped)} unique VTuber candidates.")
        
        self.registry.update_system_status({
            "last_discovery_count": len(deduped),
            "discovery_source": str(seed_file.name)
        })
        return deduped

    def step_filter_and_register(self, candidates: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Step 2 & 3: First Filter & Google Sheets Registry population."""
        logger.info("=== STEP 2 & 3: First Filter & Registry Management ===")
        if not candidates:
            candidates = self.step_discovery()

        processed_vtubers = []
        for c in candidates:
            status, thai_conf, reason = self.filter_engine.evaluate_candidate(c)
            subs = c.get("subscriber_count", 0)
            tier = get_subscriber_tier(subs)

            v_record = {
                "channel_id": c["channel_id"],
                "handle": c.get("handle", ""),
                "name": c.get("name", ""),
                "subscriber_count": subs,
                "status": status,
                "thai_confidence": thai_conf,
                "priority": tier,
                "source_count": c.get("source_count", 1),
                "last_activity": c.get("last_seen", ""),
                "last_collected": "",
                "streams_collected": 0,
                "enabled": (status == "ACCEPT"),
                "agency": c.get("agency", "Independent")
            }
            processed_vtubers.append(v_record)

        self.registry.save_vtubers(processed_vtubers)
        accepted_count = sum(1 for v in processed_vtubers if v["status"] == "ACCEPT")
        logger.info(f"Filtered {len(processed_vtubers)} candidates. ACCEPTED: {accepted_count}")
        return processed_vtubers

    def step_schedule_and_collect(
        self,
        use_pso: bool = True,
        use_mock: bool = True,
        num_workers: int = DEFAULT_WORKERS
    ) -> int:
        """Step 5, 6, 7 & 9: Stream Detection, Scheduling & Parquet Storage."""
        logger.info("=== STEP 4 & 5: Stream Detection & Worker Scheduling ===")
        enabled_vtubers = self.registry.get_enabled_vtubers()
        if not enabled_vtubers:
            logger.warning("No enabled VTubers found in registry! Run filter step first.")
            return 0

        # Simulate or Detect Live Streams
        candidate_streams = []
        for i, vtuber in enumerate(enabled_vtubers):
            # In mock mode, pretend multiple VTubers are live simultaneously
            vid = f"live_{vtuber['channel_id']}_{i:03d}"
            candidate_streams.append({
                "vtuber_channel_id": vtuber["channel_id"],
                "video_id": vid,
                "is_live": True,
                "vtuber": vtuber
            })

        logger.info(f"Detected {len(candidate_streams)} live streams. Available workers: {num_workers}")

        # Choose Scheduler
        if use_pso:
            logger.info("Running Particle Swarm Optimization (PSO) Worker Scheduler...")
            scheduler = PSOScheduler(num_workers=num_workers)
        else:
            logger.info("Running Baseline Priority Queue Scheduler...")
            scheduler = BaselinePriorityQueueScheduler(num_workers=num_workers)

        assigned_jobs = scheduler.schedule(candidate_streams)
        logger.info(f"Scheduled {len(assigned_jobs)} streams to workers.")
        for j in assigned_jobs:
            logger.info(f" -> Assigned Job: {j.video_id} (Priority: {j.priority_score:.4f})")

        # Ingestion
        collector = MockCollector() if use_mock else YouTubeCollector()
        total_events_written = 0

        for job in assigned_jobs:
            events = collector.collect_events(job.to_dict())
            if events:
                target_parquet = self.parquet_mgr.write_events(events)
                total_events_written += len(events)
                
                # Update stats in registry
                self.registry.update_vtuber(job.vtuber_channel_id, {
                    "last_collected": job.created_at,
                    "streams_collected": 1
                })

        logger.info(f"Collection complete: {total_events_written} viewer presence events recorded in Parquet.")
        return total_events_written

    def step_analytics_and_sna(self, min_shared: int = 2) -> Dict[str, Any]:
        """Step 10 & 11: DuckDB Aggregation, Audience Overlap & NetworkX SNA."""
        logger.info("=== STEP 6 & 7: DuckDB OLAP & Social Network Analysis (SNA) ===")
        
        # 1. DuckDB Pairwise Overlap Matrix
        overlap_results = self.duckdb_engine.compute_pairwise_overlap(min_shared_viewers=min_shared)
        logger.info(f"Calculated {len(overlap_results)} pairwise VTuber audience overlap links.")

        # Save to Registry control plane (NETWORK_RESULT sheet)
        self.registry.save_network_results(overlap_results)

        # 2. Build NetworkX SNA Graph
        all_vtubers = self.registry.load_vtubers()
        graph = self.network_analyzer.build_graph(
            vtubers=all_vtubers,
            pairwise_overlap=overlap_results,
            weight_metric="shared_viewers"
        )

        # Compute Centralities & Bridges
        centralities = self.network_analyzer.compute_centralities()
        communities = self.network_analyzer.detect_communities()
        top_bridges = self.network_analyzer.find_top_bridges(top_k=5)

        logger.info("--- Top Bridge VTubers (Connecting Distinct Communities) ---")
        for rank, (cid, name, b_score) in enumerate(top_bridges, 1):
            logger.info(f" #{rank}: {name} (Betweenness Centrality: {b_score:.4f})")

        # 3. Export Web JSON and Gephi GEXF
        web_json_path = self.exporter.export_web_json(graph)
        gexf_path = self.exporter.export_gexf(graph)

        # Also sync web json to web/data.json so static html can read it directly
        web_static_data = BASE_DIR / "web" / "data.json"
        web_static_data.parent.mkdir(parents=True, exist_ok=True)
        with open(web_json_path, "r", encoding="utf-8") as f_in, open(web_static_data, "w", encoding="utf-8") as f_out:
            f_out.write(f_in.read())

        return {
            "graph": graph,
            "centralities": centralities,
            "communities": communities,
            "top_bridges": top_bridges,
            "web_json_path": web_json_path,
            "gexf_path": gexf_path
        }

    def run_full_demo(self):
        """Runs the entire end-to-end pipeline."""
        logger.info("==================================================")
        logger.info(" Running Thai VTuber SNA Full End-to-End Pipeline ")
        logger.info("==================================================")
        
        # 1. Discovery
        candidates = self.step_discovery()
        
        # 2. First Filter & Registry
        registered = self.step_filter_and_register(candidates)
        
        # 3. Stream Scheduling (PSO) & Ingestion (Mock)
        events_count = self.step_schedule_and_collect(use_pso=True, use_mock=True, num_workers=6)
        
        # 4. DuckDB & SNA Analytics
        analytics_res = self.step_analytics_and_sna(min_shared=5)
        
        logger.info("==================================================")
        logger.info(" Pipeline Executed Successfully!                 ")
        logger.info(f" Web Network Graph: {analytics_res['web_json_path']}")
        logger.info(f" Gephi Graph File:  {analytics_res['gexf_path']}")
        logger.info(" Open web/index.html in your browser to view map.")
        logger.info("==================================================")


def main():
    parser = argparse.ArgumentParser(description="Thai VTuber Audience Network (SNA)")
    parser.add_argument("--demo", action="store_true", help="Run full end-to-end demo pipeline")
    parser.add_argument("--discovery", action="store_true", help="Run candidate discovery")
    parser.add_argument("--filter", action="store_true", help="Run first filter and populate registry")
    parser.add_argument("--collect", action="store_true", help="Schedule and collect viewer presence events")
    parser.add_argument("--analyze", action="store_true", help="Run DuckDB overlap and SNA analysis")
    parser.add_argument("--pso", action="store_true", default=True, help="Use PSO scheduler")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Number of collector workers")

    args = parser.parse_args()
    system = ThaiVtuberSNASystem()

    if args.demo or len(sys.argv) == 1:
        system.run_full_demo()
    else:
        if args.discovery:
            system.step_discovery()
        if args.filter:
            system.step_filter_and_register()
        if args.collect:
            system.step_schedule_and_collect(use_pso=args.pso, num_workers=args.workers)
        if args.analyze:
            system.step_analytics_and_sna()


if __name__ == "__main__":
    main()
