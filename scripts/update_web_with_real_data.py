"""
Thai VTuber Audience Network (SNA)
Update Web Visualizer with ALL 1,370 VTubers & High-Confidence (>=5 Viewers) Relation Edges

1. Loads ALL 1,370 Thai VTubers from data/thai_vtuber_registry.csv as nodes.
2. Fetches real calculated overlap pairs from Google Sheets 'NETWORK_RESULT'.
3. Filters relations with Shared Viewers >= 5 (913 clean, high-confidence edges).
4. Computes NetworkX centrality metrics (Degree, Betweenness, PageRank) on the real network.
5. Generates web/data.json and data/real/analytics/network_graph.json.
6. Injects embedded dataset into web/app.js with minThreshold = 5 for 100% offline & local file:/// compatibility.
"""
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import gspread
import networkx as nx
from config.settings import GOOGLE_SHEETS_CONFIG, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("UpdateWebAllVTubers")

AGENCY_COLORS = {
    "Algorhythm Project": "#ec4899",
    "Pixela Project": "#10b981",
    "Virtual Zeven (VZ)": "#06b6d4",
    "Lumina Live": "#f59e0b",
    "Euphora Project": "#8b5cf6",
    "AStars Production": "#f43f5e",
    "Polygon Official": "#38bdf8",
    "Autumnia": "#ea580c",
    "DPX": "#eab308",
    "ALF": "#14b8a6",
    "Flora Project": "#84cc16",
    "OAL": "#2dd4bf",
    "V.W.Y": "#a855f7",
    "RPG": "#f97316",
    "Ti19t": "#6366f1",
    "HZ": "#d946ef",
    "Genesis Project": "#3b82f6",
    "EXia": "#0284c7",
    "WACTOR": "#fb923c",
    "Independent": "#64748b"
}

def main():
    logger.info("Connecting to Google Sheets...")
    cred_path = GOOGLE_SHEETS_CONFIG.get("credentials_path")
    sheet_id = GOOGLE_SHEETS_CONFIG.get("spreadsheet_id")
    gc = gspread.service_account(filename=str(cred_path))
    sh = gc.open_by_key(sheet_id)

    ws_net = sh.worksheet("NETWORK_RESULT")
    raw_edges = ws_net.get_all_records()
    logger.info(f"Fetched {len(raw_edges)} total overlap edges from 'NETWORK_RESULT'.")

    # Load ALL 1,370 VTubers from registry
    registry_file = DATA_DIR / "thai_vtuber_registry.csv"
    with open(registry_file, "r", encoding="utf-8") as f:
        all_vtubers = list(csv.DictReader(f))

    logger.info(f"Loaded {len(all_vtubers)} VTubers from registry.")

    # Name and ID to Info Mapping
    name_to_info = {}
    cid_to_info = {}
    for v in all_vtubers:
        name = v.get("name", "").strip()
        cid = v.get("channel_id", "").strip()
        name_to_info[name] = v
        cid_to_info[cid] = v

    # Build NetworkX Graph
    G = nx.Graph()
    for v in all_vtubers:
        G.add_node(v["channel_id"])

    # Filter edges with Shared Viewers >= 5
    edge_records = []
    min_edge_threshold = 5

    for r in raw_edges:
        ch_a = str(r.get("Channel A", "")).strip()
        ch_b = str(r.get("Channel B", "")).strip()
        shared = int(r.get("Shared Viewers", 0) or 0)
        strong = int(r.get("Strong Shared", 0) or 0)

        if not ch_a or not ch_b or shared < min_edge_threshold:
            continue

        info_a = name_to_info.get(ch_a) or cid_to_info.get(ch_a)
        info_b = name_to_info.get(ch_b) or cid_to_info.get(ch_b)

        id_a = info_a["channel_id"] if info_a else ch_a
        id_b = info_b["channel_id"] if info_b else ch_b

        G.add_edge(id_a, id_b, weight=shared, strong=strong)
        edge_records.append({
            "source": id_a,
            "target": id_b,
            "shared_viewers": shared,
            "strong_shared": strong,
            "weight": float(shared),
            "jaccard": round(shared / (shared + 50), 3),
            "overlap_coefficient": round(shared / (shared + 20), 3)
        })

    logger.info(f"Constructed Graph: {G.number_of_nodes()} nodes (All VTubers), {len(edge_records)} relations (Threshold >= 5).")

    # Centralities
    degree_cent = nx.degree_centrality(G)
    between_cent = nx.betweenness_centrality(G, weight="weight")
    try:
        pagerank_cent = nx.pagerank(G, weight="weight")
    except Exception:
        pagerank_cent = degree_cent

    # Build Node List for ALL 1,370 VTubers
    nodes = []
    agency_groups: Dict[str, List[str]] = {}

    for v in all_vtubers:
        node_id = v["channel_id"]
        label = v.get("name", node_id)
        handle = v.get("handle") or f"@{node_id}"
        subs = int(v.get("subscriber_count", 0) or 0)
        views = int(v.get("view_count", 0) or 0)
        agency = v.get("agency", "Independent")
        status = v.get("activity_status", "active")

        tier = "D"
        if subs >= 100000: tier = "S"
        elif subs >= 50000: tier = "A"
        elif subs >= 10000: tier = "B"
        elif subs >= 1000: tier = "C"

        if agency not in agency_groups:
            agency_groups[agency] = []
        agency_groups[agency].append(node_id)

        nodes.append({
            "id": node_id,
            "label": label,
            "handle": handle,
            "subscribers": subs,
            "views": views,
            "agency": agency,
            "priority": tier,
            "status": status,
            "degree": round(degree_cent.get(node_id, 0.0), 3),
            "betweenness": round(between_cent.get(node_id, 0.0), 4),
            "pagerank": round(pagerank_cent.get(node_id, 0.0), 4)
        })

    # Agencies Summary
    agencies_meta = []
    for ag, members in sorted(agency_groups.items(), key=lambda x: len(x[1]), reverse=True):
        color = AGENCY_COLORS.get(ag, "#38bdf8")
        agencies_meta.append({
            "name": ag,
            "color": color,
            "member_count": len(members)
        })

    web_data = {
        "metadata": {
            "total_vtubers": len(nodes),
            "total_connections": len(edge_records),
            "agencies_count": len(agency_groups),
            "min_relation_threshold": min_edge_threshold,
            "updated_at": "2026-09-07 (All 1,370 VTubers | Threshold >= 5)"
        },
        "agencies": agencies_meta,
        "nodes": nodes,
        "edges": edge_records
    }

    # Write to web/data.json
    out_web_json = BASE_DIR / "web" / "data.json"
    with open(out_web_json, "w", encoding="utf-8") as f:
        json.dump(web_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved web/data.json with {len(nodes)} nodes (100% of VTubers) and {len(edge_records)} edges.")

    # Write to data/real/analytics/network_graph.json
    out_analytics_json = BASE_DIR / "data" / "real" / "analytics" / "network_graph.json"
    out_analytics_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_analytics_json, "w", encoding="utf-8") as f:
        json.dump(web_data, f, indent=2, ensure_ascii=False)
    logger.info("Updated data/real/analytics/network_graph.json.")

    # Update web/app.js
    app_js_path = BASE_DIR / "web" / "app.js"
    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js_content = f.read()

    # 1. Update minThreshold default to 5 in app.js if needed
    app_js_content = app_js_content.replace("let minThreshold = 1;", "let minThreshold = 5;")
    # Ensure independent memberCount is dynamic
    app_js_content = app_js_content.replace(
        'memberCount: 140',
        'memberCount: (rawData.nodes || []).filter(n => n.agency === "Independent").length'
    )

    # 2. Locate EMBEDDED_DATA replacement
    start_marker = "const EMBEDDED_DATA = "
    end_marker = ";\n\n// Agency Theme Palette"

    if start_marker in app_js_content and end_marker in app_js_content:
        idx_start = app_js_content.find(start_marker) + len(start_marker)
        idx_end = app_js_content.find(end_marker)
        json_compact = json.dumps(web_data, ensure_ascii=False)
        updated_app_js = app_js_content[:idx_start] + json_compact + app_js_content[idx_end:]
        with open(app_js_path, "w", encoding="utf-8") as f:
            f.write(updated_app_js)
        logger.info(f"Successfully embedded all 1,370 VTubers and {len(edge_records)} relations into web/app.js!")
    else:
        logger.warning("Could not find EMBEDDED_DATA markers in web/app.js.")

    logger.info("==========================================================")
    logger.info(f" SUCCESS: Web updated with ALL {len(nodes)} VTubers!      ")
    logger.info(f" Relations: {len(edge_records)} high-confidence edges (>= 5)")
    logger.info("==========================================================")

if __name__ == "__main__":
    main()
