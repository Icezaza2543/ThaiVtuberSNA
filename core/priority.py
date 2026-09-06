"""
Thai VTuber Audience Network (SNA)
Priority System

Assigns Subscriber Tiers (S, A, B, C, D) and computes dynamic priority scores
where Subscriber count has the highest weight.
"""
import math
from datetime import datetime, timezone
from typing import Dict, Any
from config.settings import SUBSCRIBER_TIERS, SCHEDULER_WEIGHTS


def get_subscriber_tier(subscriber_count: int) -> str:
    """
    Returns subscriber tier:
    S >= 100,000
    A >= 50,000
    B >= 10,000
    C >= 1,000
    D < 1,000
    """
    for tier, threshold in sorted(SUBSCRIBER_TIERS.items(), key=lambda x: x[1], reverse=True):
        if subscriber_count >= threshold:
            return tier
    return "D"


def calculate_subscriber_score(subscriber_count: int) -> float:
    """
    Normalizes subscriber count into a 0.0 to 1.0 log scale.
    Min scale ~ 100 subs (0.0), Max scale ~ 500,000 subs (1.0).
    """
    if subscriber_count <= 0:
        return 0.0
    # log10(100) = 2, log10(500,000) = 5.7
    log_val = math.log10(max(10, subscriber_count))
    score = (log_val - 2.0) / (5.7 - 2.0)
    return max(0.0, min(1.0, score))


def calculate_data_gap_score(last_collected: Any) -> float:
    """
    Normalizes time since last collection into 0.0 to 1.0.
    Channels not collected in a long time get higher priority.
    """
    if not last_collected:
        return 1.0  # Never collected -> maximum gap
    
    try:
        if isinstance(last_collected, str):
            last_dt = datetime.fromisoformat(last_collected.replace("Z", "+00:00"))
        else:
            last_dt = last_collected
        
        hours_gap = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600.0
        # 0 hours = 0.0, 72+ hours = 1.0
        return max(0.0, min(1.0, hours_gap / 72.0))
    except Exception:
        return 0.5


def calculate_collection_recency_score(streams_collected: int) -> float:
    """
    Channels with fewer streams collected get a boost to build balanced network sample.
    """
    if streams_collected <= 0:
        return 1.0
    return max(0.0, 1.0 - min(1.0, streams_collected / 10.0))


def compute_priority_score(
    vtuber_data: Dict[str, Any],
    is_live: bool = False,
    weights: Dict[str, float] = None
) -> float:
    """
    Calculates composite priority score:
    fitness = 0.60 * subscriber_priority
            + 0.20 * data_gap
            + 0.10 * live_urgency
            + 0.10 * collection_recency
    Subscriber count strictly maintains primary weight.
    """
    w = weights or SCHEDULER_WEIGHTS
    
    sub_count = vtuber_data.get("subscriber_count", 0)
    sub_score = calculate_subscriber_score(sub_count)
    
    gap_score = calculate_data_gap_score(vtuber_data.get("last_collected"))
    live_score = 1.0 if is_live else 0.0
    recency_score = calculate_collection_recency_score(vtuber_data.get("streams_collected", 0))

    score = (
        w["subscriber_priority"] * sub_score +
        w["data_gap"] * gap_score +
        w["live_urgency"] * live_score +
        w["collection_recency"] * recency_score
    )
    return round(score, 4)
