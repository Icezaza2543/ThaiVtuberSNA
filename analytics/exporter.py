"""
Thai VTuber Audience Network (SNA)
Graph & Results Exporter

Exports SNA results to:
1. Google Sheets / Local CSV (NETWORK_RESULT schema)
2. JSON for Interactive Web Visualizer (nodes, edges, communities, bridges)
3. GEXF / GraphML for Gephi
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any
import networkx as nx
from config.settings import ANALYTICS_DIR

logger = logging.getLogger(__name__)


class NetworkExporter:
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or ANALYTICS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_web_json(self, graph: nx.Graph, filename: str = "network_graph.json") -> Path:
        """
        Exports graph data into JSON optimized for modern web visualizers (D3, Vis, Canvas).
        """
        nodes = []
        for node_id, data in graph.nodes(data=True):
            nodes.append({
                "id": node_id,
                "label": data.get("name", node_id),
                "handle": data.get("handle", ""),
                "subscribers": data.get("subscriber_count", 0),
                "agency": data.get("agency", "Independent"),
                "priority": data.get("priority", "D"),
                "community": data.get("community_id", 0),
                "degree": data.get("degree_centrality", 0.0),
                "betweenness": data.get("betweenness_centrality", 0.0),
                "pagerank": data.get("pagerank", 0.0)
            })

        edges = []
        for u, v, data in graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "shared_viewers": data.get("shared_viewers", 1),
                "shared_any": data.get("shared_any", data.get("shared_viewers", 1)),
                "shared_live_chat": data.get("shared_live_chat", 0),
                "shared_comments": data.get("shared_comments", 0),
                "strong_shared_any": data.get("strong_shared_any", 0),
                "strong_shared_live_chat": data.get("strong_shared_live_chat", 0),
                "strong_shared_comments": data.get("strong_shared_comments", 0),
                "shared_strong": data.get("shared_strong", 0),
                "jaccard": data.get("jaccard", 0.0),
                "overlap_coefficient": data.get("overlap_coefficient", 0.0),
                "weight": data.get("weight", 1.0)
            })

        payload = {
            "metadata": {
                "total_vtubers": len(nodes),
                "total_connections": len(edges),
                "communities_count": len(set(n["community"] for n in nodes)) if nodes else 0
            },
            "nodes": nodes,
            "edges": edges
        }

        target_file = self.output_dir / filename
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported web graph JSON to {target_file}")
        return target_file

    def export_gexf(self, graph: nx.Graph, filename: str = "network_graph.gexf") -> Path:
        """Exports graph to Gephi GEXF format."""
        target_file = self.output_dir / filename
        try:
            nx.write_gexf(graph, str(target_file))
            logger.info(f"Exported GEXF to {target_file}")
        except Exception as e:
            logger.error(f"Failed to export GEXF: {e}")
        return target_file
