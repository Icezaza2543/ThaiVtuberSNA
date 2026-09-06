"""
Thai VTuber Audience Network (SNA)
Network Graph Analytics Engine

Builds Social Network Analysis graph using NetworkX:
- Nodes: VTubers with metadata (subs, agency, tier)
- Edges: Audience overlap with multiple weight metrics
- Metrics: Degree Centrality, Betweenness Centrality (Bridges), PageRank
- Communities: Louvain Modularity Community Detection
"""
import logging
from typing import List, Dict, Any, Tuple
import networkx as nx
from networkx.algorithms.community import louvain_communities, greedy_modularity_communities

logger = logging.getLogger(__name__)


class VTuberNetworkAnalyzer:
    def __init__(self):
        self.graph = nx.Graph()

    def build_graph(
        self,
        vtubers: List[Dict[str, Any]],
        pairwise_overlap: List[Dict[str, Any]],
        weight_metric: str = "shared_viewers",
        min_weight_threshold: float = 1.0
    ) -> nx.Graph:
        """
        Constructs an undirected weighted graph.
        weight_metric options: 'shared_viewers', 'jaccard', 'overlap_coefficient'
        """
        self.graph.clear()
        vtuber_map = {v["channel_id"]: v for v in vtubers}

        # 1. Add Nodes
        for vid, vdata in vtuber_map.items():
            self.graph.add_node(
                vid,
                name=vdata.get("name", vid),
                handle=vdata.get("handle", ""),
                subscriber_count=int(vdata.get("subscriber_count", 0)),
                agency=vdata.get("agency", "Independent"),
                priority=vdata.get("priority", "D"),
                status=vdata.get("status", "ACCEPT")
            )

        # 2. Add Edges
        for pair in pairwise_overlap:
            u = pair["vtuber_a"]
            v = pair["vtuber_b"]

            # Ensure both nodes exist in graph
            if u not in self.graph or v not in self.graph:
                continue

            shared_any = int(pair.get("shared_any", pair.get("shared_viewers", 0)))
            shared_live_chat = int(pair.get("shared_live_chat", 0))
            shared_comments = int(pair.get("shared_comments", 0))
            strong_shared_any = int(pair.get("strong_shared_any", pair.get("shared_strong", 0)))
            strong_shared_live_chat = int(pair.get("strong_shared_live_chat", 0))
            strong_shared_comments = int(pair.get("strong_shared_comments", 0))
            shared_strong = strong_shared_any

            jaccard = float(pair.get("jaccard", 0.0))
            jaccard_live_chat = float(pair.get("jaccard_live_chat", 0.0))
            jaccard_comments = float(pair.get("jaccard_comments", 0.0))
            overlap_coeff = float(pair.get("overlap_coefficient", 0.0))

            # Selected weight for graph algorithms
            primary_weight = float(pair.get(weight_metric, shared_any))

            if primary_weight >= min_weight_threshold:
                self.graph.add_edge(
                    u,
                    v,
                    weight=primary_weight,
                    shared_viewers=shared_any,
                    shared_any=shared_any,
                    shared_live_chat=shared_live_chat,
                    shared_comments=shared_comments,
                    strong_shared_any=strong_shared_any,
                    strong_shared_live_chat=strong_shared_live_chat,
                    strong_shared_comments=strong_shared_comments,
                    shared_strong=shared_strong,
                    jaccard=jaccard,
                    jaccard_live_chat=jaccard_live_chat,
                    jaccard_comments=jaccard_comments,
                    overlap_coefficient=overlap_coeff
                )

        logger.info(f"Built graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")
        return self.graph

    def compute_centralities(self) -> Dict[str, Dict[str, float]]:
        """
        Computes Degree, Betweenness (Bridge indicator), and PageRank.
        """
        if self.graph.number_of_nodes() == 0:
            return {}

        degree_cent = nx.degree_centrality(self.graph)
        betweenness_cent = nx.betweenness_centrality(self.graph, weight="weight")
        
        try:
            pagerank_val = nx.pagerank(self.graph, weight="weight")
        except Exception:
            pagerank_val = {node: 0.0 for node in self.graph.nodes}

        metrics = {}
        for node in self.graph.nodes:
            metrics[node] = {
                "degree_centrality": round(degree_cent.get(node, 0.0), 4),
                "betweenness_centrality": round(betweenness_cent.get(node, 0.0), 4),
                "pagerank": round(pagerank_val.get(node, 0.0), 4)
            }
            # Attach to graph node attributes
            self.graph.nodes[node]["degree_centrality"] = metrics[node]["degree_centrality"]
            self.graph.nodes[node]["betweenness_centrality"] = metrics[node]["betweenness_centrality"]
            self.graph.nodes[node]["pagerank"] = metrics[node]["pagerank"]

        return metrics

    def detect_communities(self) -> Dict[str, int]:
        """
        Detects communities using Louvain modularity (or greedy fallback).
        Returns mapping: node_id -> community_id
        """
        if self.graph.number_of_nodes() == 0:
            return {}

        try:
            communities = list(louvain_communities(self.graph, weight="weight", seed=42))
        except Exception as e:
            logger.warning(f"Louvain failed: {e}. Using greedy modularity communities.")
            communities = list(greedy_modularity_communities(self.graph, weight="weight"))

        community_map = {}
        for comm_id, member_set in enumerate(communities):
            for member in member_set:
                community_map[member] = comm_id
                self.graph.nodes[member]["community_id"] = comm_id

        logger.info(f"Detected {len(communities)} communities.")
        return community_map

    def find_top_bridges(self, top_k: int = 5) -> List[Tuple[str, str, float]]:
        """
        Identifies top 'Bridge' VTubers who connect distinct communities based on Betweenness Centrality.
        Returns: [(channel_id, name, betweenness_score), ...]
        """
        bridges = []
        for node, data in self.graph.nodes(data=True):
            b_score = data.get("betweenness_centrality", 0.0)
            name = data.get("name", node)
            bridges.append((node, name, b_score))

        bridges.sort(key=lambda x: x[2], reverse=True)
        return bridges[:top_k]
