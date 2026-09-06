"""
Thai VTuber Audience Network (SNA)
Overlap Mathematical Metrics

Provides mathematical formulations for comparing viewer sets:
- Jaccard Similarity: |A ∩ B| / |A ∪ B|
- Simpson Overlap Coefficient: |A ∩ B| / min(|A|, |B|)
- Cosine Similarity: |A ∩ B| / sqrt(|A| * |B|)
- Sorensen-Dice Coefficient: 2 * |A ∩ B| / (|A| + |B|)
"""
import math
from typing import Set, Any


def jaccard_similarity(set_a: Set[Any], set_b: Set[Any]) -> float:
    """Calculates Jaccard index between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return round(intersection / union, 4) if union > 0 else 0.0


def overlap_coefficient(set_a: Set[Any], set_b: Set[Any]) -> float:
    """
    Calculates Szymkiewicz–Simpson Overlap Coefficient:
    |A ∩ B| / min(|A|, |B|)
    Crucial for identifying when a small channel's entire audience overlaps with a large channel.
    """
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    min_size = min(len(set_a), len(set_b))
    return round(intersection / min_size, 4) if min_size > 0 else 0.0


def cosine_similarity(set_a: Set[Any], set_b: Set[Any]) -> float:
    """Calculates Cosine similarity between two binary presence sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    denom = math.sqrt(len(set_a) * len(set_b))
    return round(intersection / denom, 4) if denom > 0 else 0.0


def dice_coefficient(set_a: Set[Any], set_b: Set[Any]) -> float:
    """Calculates Sorensen-Dice coefficient: 2 * |A ∩ B| / (|A| + |B|)"""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    total = len(set_a) + len(set_b)
    return round((2.0 * intersection) / total, 4) if total > 0 else 0.0
