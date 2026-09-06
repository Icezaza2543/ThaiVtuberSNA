"""
Thai VTuber Audience Network (SNA)
Base Collector Interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseCollector(ABC):
    @abstractmethod
    def collect_events(self, job_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Collects viewer presence events for a given job.
        Returns list of event records:
        [
            {
                "viewer_hash": str,
                "vtuber_channel_id": str,
                "video_id": str,
                "timestamp": str,
                "source_type": "live_chat" | "comment"
            }, ...
        ]
        """
        pass
