"""
Thai VTuber Audience Network (SNA)
Worker Scheduler & Particle Swarm Optimization (PSO)

Manages worker allocation for concurrent live streams.
Provides both:
1. Baseline Priority Queue (Greedy)
2. Particle Swarm Optimization (PSO) for multi-worker constrained assignment
"""
import random
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from config.settings import SCHEDULER_WEIGHTS, DEFAULT_WORKERS
from core.priority import compute_priority_score


class CollectionJob:
    def __init__(
        self,
        vtuber_channel_id: str,
        video_id: str,
        priority_score: float = 0.0,
        status: str = "PENDING",
        metadata: Dict[str, Any] = None
    ):
        self.job_id = f"job_{uuid.uuid4().hex[:8]}"
        self.vtuber_channel_id = vtuber_channel_id
        self.video_id = video_id
        self.priority_score = priority_score
        self.status = status
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "vtuber_channel_id": self.vtuber_channel_id,
            "video_id": self.video_id,
            "priority_score": self.priority_score,
            "status": self.status,
            "created_at": self.created_at,
            "metadata": self.metadata
        }


class BaselinePriorityQueueScheduler:
    """
    Greedy Priority Queue Baseline:
    Selects top-k jobs with highest priority score.
    """
    def __init__(self, num_workers: int = DEFAULT_WORKERS, weights: Dict[str, float] = None):
        self.num_workers = num_workers
        self.weights = weights or SCHEDULER_WEIGHTS

    def schedule(self, candidate_streams: List[Dict[str, Any]]) -> List[CollectionJob]:
        """
        Takes candidate live streams, calculates priority scores,
        and assigns the top N streams to available workers.
        """
        scored_jobs: List[CollectionJob] = []
        for stream in candidate_streams:
            vtuber_info = stream.get("vtuber", {})
            score = compute_priority_score(
                vtuber_data=vtuber_info,
                is_live=stream.get("is_live", True),
                weights=self.weights
            )
            job = CollectionJob(
                vtuber_channel_id=stream["vtuber_channel_id"],
                video_id=stream["video_id"],
                priority_score=score,
                metadata=stream
            )
            scored_jobs.append(job)

        # Sort descending by priority score
        scored_jobs.sort(key=lambda j: j.priority_score, reverse=True)
        
        # Take up to num_workers
        selected = scored_jobs[:self.num_workers]
        for job in selected:
            job.status = "ASSIGNED"
        return selected


class PSOScheduler:
    """
    Particle Swarm Optimization (PSO) for Worker Assignment.
    Optimizes selection of streams from a larger candidate pool
    to balance subscriber reach, stream diversity, and data freshness.
    """
    def __init__(
        self,
        num_workers: int = DEFAULT_WORKERS,
        weights: Dict[str, float] = None,
        swarm_size: int = 20,
        max_iter: int = 30
    ):
        self.num_workers = num_workers
        self.weights = weights or SCHEDULER_WEIGHTS
        self.swarm_size = swarm_size
        self.max_iter = max_iter

    def schedule(self, candidate_streams: List[Dict[str, Any]]) -> List[CollectionJob]:
        num_candidates = len(candidate_streams)
        if num_candidates <= self.num_workers:
            # When candidates <= workers, collect all available
            jobs = []
            for s in candidate_streams:
                score = compute_priority_score(s.get("vtuber", {}), s.get("is_live", True), self.weights)
                job = CollectionJob(s["vtuber_channel_id"], s["video_id"], score, "ASSIGNED", s)
                jobs.append(job)
            return jobs

        # Calculate scores for all candidates
        candidate_scores = []
        for s in candidate_streams:
            score = compute_priority_score(s.get("vtuber", {}), s.get("is_live", True), self.weights)
            candidate_scores.append(score)

        # PSO Initialization:
        # Each particle is a continuous vector of length num_candidates.
        # Top num_workers indices represent the selected streams.
        particles = [
            [random.random() for _ in range(num_candidates)]
            for _ in range(self.swarm_size)
        ]
        velocities = [
            [random.uniform(-0.1, 0.1) for _ in range(num_candidates)]
            for _ in range(self.swarm_size)
        ]

        def evaluate_fitness(position: List[float]) -> float:
            # Select top num_workers indices
            indexed = sorted(enumerate(position), key=lambda x: x[1], reverse=True)
            chosen_indices = [idx for idx, _ in indexed[:self.num_workers]]
            
            # Primary Fitness: Total priority score
            total_score = sum(candidate_scores[i] for i in chosen_indices)
            
            # Agency diversity bonus (encourage covering multiple communities)
            agencies = set()
            for i in chosen_indices:
                agency = candidate_streams[i].get("vtuber", {}).get("agency", "indie")
                agencies.add(agency)
            diversity_bonus = len(agencies) * 0.05
            
            return total_score + diversity_bonus

        p_best = [list(p) for p in particles]
        p_best_scores = [evaluate_fitness(p) for p in particles]
        g_best = list(p_best[p_best_scores.index(max(p_best_scores))])
        g_best_score = max(p_best_scores)

        w, c1, c2 = 0.5, 1.5, 1.5
        for _ in range(self.max_iter):
            for i in range(self.swarm_size):
                for d in range(num_candidates):
                    r1, r2 = random.random(), random.random()
                    velocities[i][d] = (
                        w * velocities[i][d]
                        + c1 * r1 * (p_best[i][d] - particles[i][d])
                        + c2 * r2 * (g_best[d] - particles[i][d])
                    )
                    particles[i][d] += velocities[i][d]

                fit = evaluate_fitness(particles[i])
                if fit > p_best_scores[i]:
                    p_best[i] = list(particles[i])
                    p_best_scores[i] = fit
                    if fit > g_best_score:
                        g_best = list(particles[i])
                        g_best_score = fit

        # Extract optimal stream selection from g_best
        indexed_g = sorted(enumerate(g_best), key=lambda x: x[1], reverse=True)
        chosen_indices = [idx for idx, _ in indexed_g[:self.num_workers]]

        selected_jobs = []
        for idx in chosen_indices:
            s = candidate_streams[idx]
            job = CollectionJob(
                vtuber_channel_id=s["vtuber_channel_id"],
                video_id=s["video_id"],
                priority_score=candidate_scores[idx],
                status="ASSIGNED",
                metadata=s
            )
            selected_jobs.append(job)

        selected_jobs.sort(key=lambda j: j.priority_score, reverse=True)
        return selected_jobs
