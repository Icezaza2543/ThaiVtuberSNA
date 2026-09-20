"""Data structures for multi-platform discovery leads, batches, and limits."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DiscoveryLead:
    platform: str
    name: str
    url: str
    handle: Optional[str] = None
    platform_id: Optional[str] = None
    id_namespace: Optional[str] = None
    source_url: str = ""
    query: str = ""
    method: str = "playwright_search"
    observed_at: str = ""
    source_kind: str = "platform_observation"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryLimits:
    max_results: int = 20
    max_pages: int = 3
    timeout: float = 30.0


@dataclass
class DiscoveryBatch:
    platform: str
    query: str = ""
    method: str = "playwright_search"
    source_url: str = ""
    status: str = "completed"
    leads: List[DiscoveryLead] = field(default_factory=list)
    pages_seen: int = 0
    records_seen: int = 0
    error_message: Optional[str] = None
    sub_batches: List["DiscoveryBatch"] = field(default_factory=list)
