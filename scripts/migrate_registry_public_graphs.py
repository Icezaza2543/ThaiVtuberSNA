"""Migrate registry-derived public graph identities without inventing network observations.

Existing edges and centrality values are retained.  Canonical YouTube accounts
missing from the older graph are added as isolated nodes with zero centrality.
The original network freshness metadata is preserved; registry migration
provenance is recorded separately.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import CREATOR_REGISTRY_PATH
from core.creator_catalog import CreatorCatalog

GRAPH_PATHS = [
    ROOT / "web" / "data.json",
    ROOT / "data" / "real" / "analytics" / "network_graph.json",
]
MIGRATED_ON = "2026-09-19"


def tier(subscriber_count):
    value = int(subscriber_count or 0)
    if value >= 100_000:
        return "S"
    if value >= 50_000:
        return "A"
    if value >= 10_000:
        return "B"
    if value >= 1_000:
        return "C"
    return "D"


def migrate_graph(path: Path, catalog: CreatorCatalog) -> bool:
    if not path.exists():
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("nodes"), list):
        raise ValueError(f"unsupported registry-derived graph payload: {path}")

    rows = {row["channel_id"]: row for row in catalog.youtube_rows()}
    existing_nodes = {
        str(node.get("id")): node
        for node in payload["nodes"]
        if isinstance(node, dict) and node.get("id")
    }

    nodes = []
    for channel_id in sorted(rows):
        row = rows[channel_id]
        node = dict(existing_nodes.get(channel_id, {}))
        node.update(
            {
                "id": channel_id,
                "label": row.get("name") or row.get("canonical_name") or channel_id,
                "handle": row.get("handle") or "",
                "subscribers": int(row.get("subscriber_count") or 0),
                "views": int(row.get("view_count") or 0),
                "agency": row.get("agency") or "Independent",
                "priority": tier(row.get("subscriber_count")),
                "status": row.get("activity_status") or "unknown",
            }
        )
        node.setdefault("degree", 0.0)
        node.setdefault("betweenness", 0.0)
        node.setdefault("pagerank", 0.0)
        nodes.append(node)

    allowed = set(rows)
    edges = [
        edge
        for edge in payload.get("edges", [])
        if isinstance(edge, dict)
        and edge.get("source") in allowed
        and edge.get("target") in allowed
    ]

    old_colors = {
        row.get("name"): row.get("color")
        for row in payload.get("agencies", [])
        if isinstance(row, dict) and row.get("name")
    }
    counts = {}
    for node in nodes:
        agency = node["agency"]
        counts[agency] = counts.get(agency, 0) + 1
    agencies = [
        {
            "name": agency,
            "color": old_colors.get(agency) or "#38bdf8",
            "member_count": count,
        }
        for agency, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    metadata = dict(payload.get("metadata") or {})
    metadata.update(
        {
            "total_vtubers": len(nodes),
            "total_connections": len(edges),
            "agencies_count": len(agencies),
            "creator_registry_sha256": catalog.source_fingerprint(),
            "creator_registry_migrated_on": MIGRATED_ON,
        }
    )
    payload.update({"metadata": metadata, "agencies": agencies, "nodes": nodes, "edges": edges})
    raw = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path.read_text(encoding="utf-8") == raw:
        return False
    path.write_text(raw, encoding="utf-8")
    return True


def main() -> int:
    catalog = CreatorCatalog.from_path(CREATOR_REGISTRY_PATH)
    changed = [str(path.relative_to(ROOT)) for path in GRAPH_PATHS if migrate_graph(path, catalog)]
    print(json.dumps({"changed": changed, "creator_registry_sha256": catalog.source_fingerprint()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
