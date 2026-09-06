"""
Thai VTuber Audience Network (SNA)
Performance Benchmark & Scheduler Comparison Suite

Separates and measures:
1. YouTube Extraction Throughput (Network-bound extraction rate from YouTube)
2. Local Aggregation & Parquet Throughput (In-memory Early Aggregation + SHA-256 + Parquet write)
3. Parquet Storage Size & Efficiency per 1,000 events
4. DuckDB OLAP Aggregation Latency on Real Dataset
5. Multi-Worker Concurrency Scaling (1 / 3 / 5 workers)
6. Head-to-Head Comparison: Greedy Priority Queue vs Particle Swarm Optimization (PSO)
"""
import concurrent.futures
import json
import logging
import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.scheduler import BaselinePriorityQueueScheduler, PSOScheduler
from storage.duckdb_engine import DuckDBAnalyticsEngine
from storage.parquet_manager import ParquetStorageManager
from collector.mock_collector import MockCollector
from collector.youtube_collector import YouTubeCollector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BenchmarkSuite")

BENCHMARK_OUTPUT_DIR = BASE_DIR / "data" / "benchmarks"
BENCHMARK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def benchmark_youtube_extraction_rate() -> Dict[str, Any]:
    """
    Measures YouTube Extraction Rate:
    Network I/O throughput from real public YouTube video.
    """
    logger.info("--- 1. Benchmarking Real YouTube Extraction Throughput (Network I/O) ---")
    try:
        collector = YouTubeCollector()
    except RuntimeError:
        return {"status": "blocked", "reason": "Persistent key unavailable or continuity check failed",
                "youtube_extraction_events_per_minute": None, "elapsed_sec": None, "comments_extracted": None}
    job = {
        "vtuber_channel_id": "UCqhhWjpw23dWhJ5rRwCCrMA",
        "video_id": "G1LXXzZx48c"
    }

    t0 = time.perf_counter()
    # Extract up to 100 comments from real YouTube video
    events = collector.collect_events(job, max_comments=100)
    t1 = time.perf_counter()

    elapsed = t1 - t0
    events_count = len(events)
    events_per_sec = (events_count / elapsed) if elapsed > 0 else 0.0
    events_per_min = events_per_sec * 60.0

    return {
        "status": "measured" if events_count else "no_evidence",
        "source": "Real YouTube Video (G1LXXzZx48c)",
        "comments_extracted": events_count,
        "elapsed_sec": round(elapsed, 3),
        "youtube_extraction_events_per_sec": round(events_per_sec, 2),
        "youtube_extraction_events_per_minute": round(events_per_min, 1),
        "note": "Network-bound I/O governed by YouTube response times and rate-limits."
    }


def benchmark_local_processing_throughput(event_count: int = 1000) -> Dict[str, Any]:
    """
    Measures Local Processing Throughput:
    Pure CPU/RAM throughput for Early Aggregation + HMAC-SHA256 Hashing + Parquet Compression.
    """
    logger.info(f"--- 2. Benchmarking Local Processing & Parquet Storage ({event_count} events) ---")
    tracemalloc.start()
    start_cpu = time.process_time()
    start_wall = time.perf_counter()

    collector = MockCollector(seed=123)
    job = {
        "vtuber_channel_id": "UC_BENCH_TEST",
        "video_id": "vid_bench_001",
        "metadata": {"agency": "Algorhythm Project"}
    }
    
    events = []
    while len(events) < event_count:
        events.extend(collector.collect_events(job))
    events = events[:event_count]

    # Aggregate the sanitized events by viewer/channel/video/source.
    from collector.youtube_collector import YouTubeCollector
    from types import SimpleNamespace
    aggregated = YouTubeCollector.collect_aggregated_events(
        SimpleNamespace(collect_events=lambda *a, **k: events), job)

    # Local write to Parquet
    bench_dir = BENCHMARK_OUTPUT_DIR / "events"
    bench_dir.mkdir(parents=True, exist_ok=True)
    parquet_mgr = ParquetStorageManager(base_dir=bench_dir)
    parquet_path = parquet_mgr.write_events(aggregated)

    end_wall = time.perf_counter()
    end_cpu = time.process_time()
    current_ram, peak_ram = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    wall_duration = end_wall - start_wall
    cpu_duration = end_cpu - start_cpu
    events_per_min = (event_count / wall_duration) * 60.0
    file_size_bytes = os.path.getsize(parquet_path)
    file_size_kb = file_size_bytes / 1024.0

    return {
        "events_processed": event_count,
        "aggregated_records": len(aggregated),
        "local_wall_time_sec": round(wall_duration, 4),
        "local_cpu_time_sec": round(cpu_duration, 4),
        "local_processing_events_per_minute": round(events_per_min, 1),
        "local_peak_ram_mb": round(peak_ram / (1024 * 1024), 2),
        "parquet_size_kb": round(file_size_kb, 2),
        "parquet_kb_per_1000_events": round(file_size_kb / (event_count / 1000.0), 2),
        "note": "Synthetic generation, HMAC, source-separated aggregation and Parquet write; tracemalloc is Python allocations, not process RSS."
    }


def benchmark_duckdb_aggregation() -> Dict[str, Any]:
    """Measures DuckDB query and multi-source overlap aggregation latency."""
    logger.info("--- 3. Benchmarking DuckDB Multi-Source Overlap Latency ---")
    real_events = BASE_DIR / "data" / "real" / "events"
    events_dir = real_events if real_events.exists() and list(real_events.glob("**/*.parquet")) else (BENCHMARK_OUTPUT_DIR / "events")

    engine = DuckDBAnalyticsEngine(
        db_path=BENCHMARK_OUTPUT_DIR / "bench_analytics.duckdb",
        events_dir=events_dir
    )

    tracemalloc.start()
    t0 = time.perf_counter()
    overlap_results = engine.compute_pairwise_overlap(min_shared_viewers=1)
    t1 = time.perf_counter()
    _, peak_ram = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    engine.close()
    latency_ms = (t1 - t0) * 1000.0
    return {
        "pairwise_links_calculated": len(overlap_results),
        "query_latency_ms": round(latency_ms, 2),
        "duckdb_peak_ram_mb": round(peak_ram / (1024 * 1024), 2)
    }


def benchmark_concurrency(worker_counts: List[int] = [1, 3, 5]) -> Dict[str, Any]:
    """Tests worker scaling across 1, 3, and 5 concurrent streams."""
    logger.info("--- 4. Benchmarking Concurrent Worker Scaling (1 / 3 / 5 workers) ---")
    results = {}

    def worker_task(worker_id: int):
        collector = MockCollector(seed=worker_id)
        job = {
            "vtuber_channel_id": f"UC_CONCUR_{worker_id}",
            "video_id": f"vid_concur_{worker_id}",
            "metadata": {"agency": "Polygon"}
        }
        events = collector.collect_events(job)
        mgr = ParquetStorageManager(base_dir=BENCHMARK_OUTPUT_DIR / f"concur_{worker_id}")
        mgr.write_events(events)
        return len(events)

    for count in worker_counts:
        tracemalloc.start()
        t0 = time.perf_counter()

        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(worker_task, i) for i in range(count)]
            total_events = sum(f.result() for f in futures)

        t1 = time.perf_counter()
        _, peak_ram = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        elapsed = t1 - t0
        results[f"{count}_workers"] = {
            "total_events": total_events,
            "duration_sec": round(elapsed, 4),
            "peak_ram_mb": round(peak_ram / (1024 * 1024), 2),
            "events_per_sec": round(total_events / elapsed, 1)
        }
        logger.info(f" -> {count} workers: {elapsed:.3f}s, Peak RAM: {peak_ram / (1024*1024):.2f} MB")

    return results


def benchmark_scheduler_comparison() -> Dict[str, Any]:
    """
    Compares Greedy Priority Queue vs PSO using the exact same candidate pool.
    """
    logger.info("--- 5. Comparing Greedy Scheduler vs Particle Swarm Optimization (PSO) ---")
    candidate_streams = [
        {"vtuber_channel_id": "UC_01_AISHA", "video_id": "v01", "is_live": True, "vtuber": {"subscriber_count": 540000, "agency": "Independent", "last_collected": "", "streams_collected": 0}},
        {"vtuber_channel_id": "UC_02_DACAPO", "video_id": "v02", "is_live": True, "vtuber": {"subscriber_count": 450000, "agency": "Algorhythm Project", "last_collected": "", "streams_collected": 0}},
        {"vtuber_channel_id": "UC_03_BAABEL", "video_id": "v03", "is_live": True, "vtuber": {"subscriber_count": 280000, "agency": "Algorhythm Project", "last_collected": "", "streams_collected": 0}},
        {"vtuber_channel_id": "UC_04_SCHNEIDER", "video_id": "v04", "is_live": True, "vtuber": {"subscriber_count": 240000, "agency": "Algorhythm Project", "last_collected": "", "streams_collected": 0}},
        {"vtuber_channel_id": "UC_05_HOKU", "video_id": "v05", "is_live": True, "vtuber": {"subscriber_count": 119000, "agency": "Polygon Official", "last_collected": "", "streams_collected": 0}},
        {"vtuber_channel_id": "UC_06_BAKU", "video_id": "v06", "is_live": True, "vtuber": {"subscriber_count": 60000, "agency": "Algorhythm Project", "last_collected": "", "streams_collected": 0}},
        {"vtuber_channel_id": "UC_07_MINAMI", "video_id": "v07", "is_live": True, "vtuber": {"subscriber_count": 29000, "agency": "Polygon Official", "last_collected": "", "streams_collected": 0}},
        {"vtuber_channel_id": "UC_08_KORRA", "video_id": "v08", "is_live": True, "vtuber": {"subscriber_count": 18000, "agency": "Independent", "last_collected": "", "streams_collected": 0}},
        {"vtuber_channel_id": "UC_09_ZEPHYR", "video_id": "v09", "is_live": True, "vtuber": {"subscriber_count": 7500, "agency": "Independent", "last_collected": "", "streams_collected": 0}},
        {"vtuber_channel_id": "UC_10_INDIE", "video_id": "v10", "is_live": True, "vtuber": {"subscriber_count": 2000, "agency": "Independent", "last_collected": "", "streams_collected": 0}}
    ]

    num_workers = 4

    # 1. Greedy
    t0_greedy = time.perf_counter()
    greedy_scheduler = BaselinePriorityQueueScheduler(num_workers=num_workers)
    greedy_jobs = greedy_scheduler.schedule(candidate_streams)
    t1_greedy = time.perf_counter()

    greedy_score_sum = sum(j.priority_score for j in greedy_jobs)
    greedy_ids = [j.vtuber_channel_id for j in greedy_jobs]

    # 2. PSO
    t0_pso = time.perf_counter()
    pso_scheduler = PSOScheduler(num_workers=num_workers, swarm_size=20, max_iter=30)
    pso_jobs = pso_scheduler.schedule(candidate_streams)
    t1_pso = time.perf_counter()

    pso_score_sum = sum(j.priority_score for j in pso_jobs)
    pso_ids = [j.vtuber_channel_id for j in pso_jobs]

    selection_overlap = len(set(greedy_ids).intersection(set(pso_ids)))
    time_greedy_ms = (t1_greedy - t0_greedy) * 1000.0
    time_pso_ms = (t1_pso - t0_pso) * 1000.0

    recommendation = (
        "Greedy remains default; PSO optional. This single synthetic run is not a scaling study."
    )

    return {
        "num_candidates": len(candidate_streams),
        "num_workers": num_workers,
        "greedy": {
            "selected_channels": greedy_ids,
            "score_sum": round(greedy_score_sum, 4),
            "execution_time_ms": round(time_greedy_ms, 3)
        },
        "pso": {
            "selected_channels": pso_ids,
            "score_sum": round(pso_score_sum, 4),
            "execution_time_ms": round(time_pso_ms, 3)
        },
        "selection_agreement": f"{selection_overlap}/{num_workers} ({selection_overlap/num_workers*100:.0f}%)",
        "recommendation": recommendation
    }


def run_full_benchmark():
    report = {
        "youtube_extraction_rate": benchmark_youtube_extraction_rate(),
        "local_processing_throughput": benchmark_local_processing_throughput(),
        "duckdb_aggregation": benchmark_duckdb_aggregation(),
        "concurrency_scaling": benchmark_concurrency(),
        "scheduler_comparison": benchmark_scheduler_comparison()
    }

    out_file = BENCHMARK_OUTPUT_DIR / "benchmark_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print("           PERFORMANCE BENCHMARK REPORT SUMMARY          ")
    print("=" * 65)
    extraction = report['youtube_extraction_rate']
    if extraction.get('status') == 'blocked':
        print(f"1. YouTube Extraction Rate: BLOCKED ({extraction['reason']})")
    else:
        print(f"1. YouTube Extraction Rate: {extraction['youtube_extraction_events_per_minute']} comments/min")
        print(f"   Status: {extraction['status']}; elapsed: {extraction['elapsed_sec']}s")
    print(f"2. Local Processing Throughput: {report['local_processing_throughput']['local_processing_events_per_minute']} events/min")
    print(f"   Peak RAM: {report['local_processing_throughput']['local_peak_ram_mb']} MB")
    print(f"   Parquet Storage: {report['local_processing_throughput']['parquet_kb_per_1000_events']} KB / 1,000 events")
    print(f"3. DuckDB Multi-Source Query Latency: {report['duckdb_aggregation']['query_latency_ms']} ms")
    print(f"4. Worker Concurrency (1 vs 3 vs 5):")
    for k, v in report['concurrency_scaling'].items():
        print(f"   - {k}: {v['duration_sec']}s ({v['events_per_sec']} ev/s, {v['peak_ram_mb']} MB RAM)")
    print(f"5. Greedy vs PSO Comparison:")
    print(f"   - Greedy Time: {report['scheduler_comparison']['greedy']['execution_time_ms']} ms")
    print(f"   - PSO Time:    {report['scheduler_comparison']['pso']['execution_time_ms']} ms")
    print(f"   - Agreement:   {report['scheduler_comparison']['selection_agreement']}")
    print(f"   - Verdict:     {report['scheduler_comparison']['recommendation']}")
    print("=" * 65)
    print(f"Full Report Saved: {out_file}\n")


if __name__ == "__main__":
    run_full_benchmark()
