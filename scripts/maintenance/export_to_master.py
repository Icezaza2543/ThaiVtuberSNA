"""Export canonical registry, SNA network results, and platform accounts

Exports datasets formatted for ThaiVtuberMaster (https://github.com/Icezaza2543/ThaiVtuberMaster):
- VTUBERS.csv (YouTube registry)
- NETWORK_RESULT.csv (SNA audience overlap network)
- TIKTOK_VERIFIED.csv (Verified TikTok accounts)
- TWITCH_VERIFIED.csv (Verified Twitch accounts)
- ANALYTICS_METRICS.csv (Account level metrics)
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]


def export_vtubers(creators_path: Path, web_data_path: Path, output_file: Path) -> int:
    """Export VTUBERS.csv for ThaiVtuberMaster registry view."""
    fieldnames = [
        "channel_id", "handle", "name", "subscriber_count",
        "agency", "status", "last_activity", "last_collected", "persona_id"
    ]
    
    rows: Dict[str, Dict[str, Any]] = {}
    
    # 1. Read from web/data.json nodes if available
    if web_data_path.exists():
        try:
            web_data = json.loads(web_data_path.read_text(encoding="utf-8"))
            for node in web_data.get("nodes", []):
                cid = node.get("id")
                if not cid:
                    continue
                rows[cid] = {
                    "channel_id": cid,
                    "handle": node.get("handle", ""),
                    "name": node.get("label", ""),
                    "subscriber_count": node.get("subscribers", 0),
                    "agency": node.get("agency", "Independent"),
                    "status": "ACCEPT",
                    "last_activity": node.get("status", "active"),
                    "last_collected": "",
                    "persona_id": ""
                }
        except Exception:
            pass

    # 2. Enrich from data/registry/creators.json
    if creators_path.exists():
        try:
            creators_data = json.loads(creators_path.read_text(encoding="utf-8"))
            accounts = creators_data.get("accounts", [])
            for acct in accounts:
                if acct.get("platform") != "youtube":
                    continue
                cid = acct.get("platform_id") or acct.get("account_id")
                if not cid or not cid.startswith("UC"):
                    continue
                meta = acct.get("metadata", {})
                existing = rows.get(cid, {})
                rows[cid] = {
                    "channel_id": cid,
                    "handle": acct.get("handle") or existing.get("handle", ""),
                    "name": acct.get("display_name") or existing.get("name", cid),
                    "subscriber_count": meta.get("subscriber_count") or existing.get("subscriber_count", 0),
                    "agency": meta.get("agency") or existing.get("agency", "Independent"),
                    "status": "ACCEPT",
                    "last_activity": meta.get("last_video_published_at") or meta.get("activity_status") or existing.get("last_activity", "active"),
                    "last_collected": meta.get("checked_date", ""),
                    "persona_id": acct.get("persona_id") or existing.get("persona_id", "")
                }
        except Exception:
            pass

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(rows.values(), key=lambda r: str(r["name"]).casefold()):
            writer.writerow(row)
            
    return len(rows)


def export_network(web_data_path: Path, output_file: Path) -> int:
    """Export NETWORK_RESULT.csv for ThaiVtuberMaster SNA view."""
    fieldnames = [
        "Channel A", "Agency A", "Channel B", "Agency B",
        "Shared Viewers", "Strong Shared", "Calculated At"
    ]
    
    if not web_data_path.exists():
        return 0
        
    web_data = json.loads(web_data_path.read_text(encoding="utf-8"))
    nodes = {n.get("id"): n for n in web_data.get("nodes", [])}
    edges = web_data.get("edges", [])
    updated_at = web_data.get("metadata", {}).get("updated_at", "2026-09-07")

    rows = []
    for edge in edges:
        s_id = edge.get("source")
        t_id = edge.get("target")
        s_node = nodes.get(s_id, {})
        t_node = nodes.get(t_id, {})

        channel_a = s_node.get("label", s_id)
        agency_a = s_node.get("agency", "Independent")
        channel_b = t_node.get("label", t_id)
        agency_b = t_node.get("agency", "Independent")

        shared = edge.get("shared_viewers", 0)
        strong = edge.get("strong_shared", 0)

        rows.append({
            "Channel A": channel_a,
            "Agency A": agency_a,
            "Channel B": channel_b,
            "Agency B": agency_b,
            "Shared Viewers": shared,
            "Strong Shared": strong,
            "Calculated At": updated_at
        })

    rows.sort(key=lambda x: int(x["Shared Viewers"]), reverse=True)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def export_platform_verified(registry_path: Path, platform: str, output_file: Path) -> int:
    """Export TIKTOK_VERIFIED.csv or TWITCH_VERIFIED.csv from registry.json."""
    fieldnames = [
        "handle", "name", "platform_id", "url",
        "persona_name", "persona_id", "observed_at"
    ]
    
    if not registry_path.exists():
        return 0

    data = json.loads(registry_path.read_text(encoding="utf-8"))
    tables = data.get("tables", {})
    personas = {p["id"]: p for p in tables.get("personas", [])}
    accounts = tables.get("accounts", [])
    links = tables.get("account_links", [])

    account_persona_map: Dict[str, str] = {}
    for link in links:
        if link.get("review_status") == "verified":
            account_persona_map[link["account_id"]] = link["persona_id"]

    rows = []
    for acct in accounts:
        if acct.get("platform") != platform:
            continue
        acct_id = acct.get("id")
        persona_id = account_persona_map.get(acct_id, "")
        persona = personas.get(persona_id, {})

        handle = acct.get("handle", "")
        name = persona.get("canonical_name", handle)
        platform_id = acct.get("platform_id", "")
        url = acct.get("url", "")
        persona_name = persona.get("canonical_name", "")

        rows.append({
            "handle": handle,
            "name": name,
            "platform_id": platform_id,
            "url": url,
            "persona_name": persona_name,
            "persona_id": persona_id,
            "observed_at": persona.get("reviewed_at", "")
        })

    rows.sort(key=lambda x: str(x["handle"]).casefold())

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def export_metrics(web_data_path: Path, output_file: Path) -> int:
    """Export ANALYTICS_METRICS.csv."""
    fieldnames = [
        "platform", "platform_id", "name", "scope",
        "followers_or_subscribers", "views", "likes_received",
        "metric_time", "time_basis", "observed_at",
        "source", "source_url", "account_url"
    ]
    
    if not web_data_path.exists():
        return 0

    web_data = json.loads(web_data_path.read_text(encoding="utf-8"))
    nodes = web_data.get("nodes", [])

    rows = []
    for node in nodes:
        cid = node.get("id", "")
        rows.append({
            "platform": "youtube",
            "platform_id": cid,
            "name": node.get("label", ""),
            "scope": "reviewed_persona_link",
            "followers_or_subscribers": node.get("subscribers", 0),
            "views": node.get("views", 0),
            "likes_received": "",
            "metric_time": "2026-09-07",
            "time_basis": "retrieved_from_platform",
            "observed_at": "2026-09-07T00:00:00Z",
            "source": "YouTube API / ThaiVTuberSNA",
            "source_url": f"https://www.youtube.com/channel/{cid}",
            "account_url": f"https://www.youtube.com/channel/{cid}"
        })

    rows.sort(key=lambda x: str(x["name"]).casefold())

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="Export datasets for ThaiVtuberMaster")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory to write CSV files (e.g. ../ThaiVtuberMaster/local/sheet-exports)"
    )
    args = parser.parse_args()

    out_dir: Path = args.output
    out_dir.mkdir(parents=True, exist_ok=True)

    creators_path = ROOT / "data" / "registry" / "creators.json"
    web_data_path = ROOT / "web" / "data.json"
    registry_path = ROOT / "data" / "registry.json"

    print(f"Exporting datasets for ThaiVtuberMaster to: {out_dir}")
    
    n_vtubers = export_vtubers(creators_path, web_data_path, out_dir / "VTUBERS.csv")
    print(f"  [+] VTUBERS.csv: {n_vtubers} records")

    n_network = export_network(web_data_path, out_dir / "NETWORK_RESULT.csv")
    print(f"  [+] NETWORK_RESULT.csv: {n_network} overlap pairs")

    n_tiktok = export_platform_verified(registry_path, "tiktok", out_dir / "TIKTOK_VERIFIED.csv")
    print(f"  [+] TIKTOK_VERIFIED.csv: {n_tiktok} accounts")

    n_twitch = export_platform_verified(registry_path, "twitch", out_dir / "TWITCH_VERIFIED.csv")
    print(f"  [+] TWITCH_VERIFIED.csv: {n_twitch} accounts")

    n_metrics = export_metrics(web_data_path, out_dir / "ANALYTICS_METRICS.csv")
    print(f"  [+] ANALYTICS_METRICS.csv: {n_metrics} metric rows")

    print(f"\nDone. You can now sync ThaiVtuberMaster using:")
    print(f"  python scripts/manage.py sync --from-csv {out_dir}")


if __name__ == "__main__":
    main()
