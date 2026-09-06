"""
Thai VTuber Audience Network (SNA)
Mock Collector

Generates realistic viewer presence events for testing, verification, and demo.
Strictly respects privacy: all viewer IDs are immediately HMAC-SHA256 hashed.
NO chat message or comment text is generated or stored.
"""
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from collector.base_collector import BaseCollector
from core.hasher import hash_viewer


class MockCollector(BaseCollector):
    def __init__(self, seed: int = 42):
        random.seed(seed)
        # Predefined pools of simulated viewer raw IDs
        # Agency core pools
        self.arp_core_viewers = [f"viewer_arp_{i:04d}" for i in range(1, 300)]
        self.polygon_core_viewers = [f"viewer_poly_{i:04d}" for i in range(1, 250)]
        self.pixela_core_viewers = [f"viewer_pix_{i:04d}" for i in range(1, 200)]
        # Bridge viewers (crossover community)
        self.bridge_viewers = [f"viewer_bridge_{i:04d}" for i in range(1, 150)]
        # General indie viewers
        self.indie_viewers = [f"viewer_indie_{i:04d}" for i in range(1, 250)]

    def generate_presence_pool(self, vtuber_id: str, agency: str = "") -> List[str]:
        """Creates a realistic set of viewer IDs active on this channel."""
        presence = []
        # Unique dedicated fans for this channel
        unique_fans = [f"viewer_dedicated_{vtuber_id}_{i:03d}" for i in range(random.randint(40, 90))]
        presence.extend(unique_fans)

        # Agency shared pool
        if "algorhythm" in agency.lower() or "arp" in agency.lower():
            presence.extend(random.sample(self.arp_core_viewers, k=random.randint(60, 140)))
        elif "polygon" in agency.lower():
            presence.extend(random.sample(self.polygon_core_viewers, k=random.randint(50, 120)))
        elif "pixela" in agency.lower():
            presence.extend(random.sample(self.pixela_core_viewers, k=random.randint(40, 100)))
        else:
            presence.extend(random.sample(self.indie_viewers, k=random.randint(30, 80)))

        # Bridge viewers (present across multiple communities)
        bridge_sample_size = random.randint(25, 70)
        presence.extend(random.sample(self.bridge_viewers, k=bridge_sample_size))

        return presence

    def collect_events(self, job_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Simulates gathering live chat/comment events.
        All raw IDs are hashed immediately. Zero message text stored.
        """
        vtuber_id = job_dict["vtuber_channel_id"]
        video_id = job_dict["video_id"]
        agency = job_dict.get("metadata", {}).get("agency", "")

        raw_viewers = self.generate_presence_pool(vtuber_id, agency)
        base_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48))

        events = []
        for raw_id in raw_viewers:
            # Privacy: Hasher transforms raw_id to HMAC-SHA256
            v_hash = hash_viewer(raw_id)
            source = "live_chat" if random.random() > 0.15 else "comment"
            event_time = base_time + timedelta(minutes=random.randint(1, 120))

            events.append({
                "viewer_hash": v_hash,
                "vtuber_channel_id": vtuber_id,
                "video_id": video_id,
                "timestamp": event_time.isoformat(),
                "source_type": source
            })

        return events

    def collect_aggregated_events(self, job_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Aggregated session schema alternative (Requirement 7):
        viewer_hash, vtuber_channel_id, video_id, first_seen, last_seen, appearances
        """
        raw_events = self.collect_events(job_dict)
        agg_map: Dict[str, Dict[str, Any]] = {}

        for ev in raw_events:
            vh = ev["viewer_hash"]
            if vh not in agg_map:
                agg_map[vh] = {
                    "viewer_hash": vh,
                    "vtuber_channel_id": ev["vtuber_channel_id"],
                    "video_id": ev["video_id"],
                    "first_seen": ev["timestamp"],
                    "last_seen": ev["timestamp"],
                    "appearances": 1
                }
            else:
                agg_map[vh]["appearances"] += 1
                if ev["timestamp"] > agg_map[vh]["last_seen"]:
                    agg_map[vh]["last_seen"] = ev["timestamp"]

        return list(agg_map.values())
