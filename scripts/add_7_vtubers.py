import csv
import json
from datetime import datetime, timezone
from pathlib import Path

NEW_VTUBERS = [
    {
        "channel_id": "UCkvce0jZJYBWJLTuKoLIvLA",
        "name": "Noeluc",
        "handle": "@noeluc_",
        "channel_url": "https://www.youtube.com/channel/UCkvce0jZJYBWJLTuKoLIvLA",
        "agency": "Independent",
        "activity_status": "active",
        "vtuber_status": "CONFIRMED",
        "person_id": "vtuber_noeluc_",
        "canonical_name": "Noeluc",
        "channel_type": "main",
        "subscriber_count": 498,
        "video_count": 89,
        "view_count": 0,
        "last_video_published_at": "2026-09-01T00:00:00+00:00",
        "country": "TH",
        "thai_confidence": 1.0,
        "reference_sources": "User Verification; YouTube Channel",
        "evidence_notes": "VTuber ปีศาจแมว (Bakeneko) สายร้องเพลง/พูดคุยภาษาไทย; Thai VTuber confirmed",
        "enabled": True,
        "priority": "D"
    },
    {
        "channel_id": "UCtJXU7YRwS-Cc8pu8U8bicg",
        "name": "Chiziz R Fa",
        "handle": "@ChizizFa",
        "channel_url": "https://www.youtube.com/channel/UCtJXU7YRwS-Cc8pu8U8bicg",
        "agency": "Independent",
        "activity_status": "active",
        "vtuber_status": "CONFIRMED",
        "person_id": "vtuber_ChizizFa",
        "canonical_name": "Chiziz R Fa",
        "channel_type": "main",
        "subscriber_count": 1360,
        "video_count": 64,
        "view_count": 0,
        "last_video_published_at": "2026-09-01T00:00:00+00:00",
        "country": "TH",
        "thai_confidence": 1.0,
        "reference_sources": "User Verification; YouTube Channel",
        "evidence_notes": "VTuber เอลฟ์แห่งทะเลทราย ผู้ถือครองพลัง Anubis & Ra; Thai VTuber confirmed",
        "enabled": True,
        "priority": "C"
    },
    {
        "channel_id": "UCP8tsYT8efX32P4WUlNrFOA",
        "name": "Aozora Sukai Ch.",
        "handle": "@SukaiVtuber",
        "channel_url": "https://www.youtube.com/channel/UCP8tsYT8efX32P4WUlNrFOA",
        "agency": "Independent",
        "activity_status": "active",
        "vtuber_status": "CONFIRMED",
        "person_id": "vtuber_SukaiVtuber",
        "canonical_name": "Aozora Sukai Ch.",
        "channel_type": "main",
        "subscriber_count": 1260,
        "video_count": 82,
        "view_count": 4981,
        "last_video_published_at": "2026-09-01T00:00:00+00:00",
        "country": "TH",
        "thai_confidence": 1.0,
        "reference_sources": "User Verification; YouTube Channel",
        "evidence_notes": "VTuber ชายไทย (โอโซระ สุไค) สายเล่นเกม/ร้องเพลง; Thai VTuber confirmed",
        "enabled": True,
        "priority": "C"
    },
    {
        "channel_id": "UC2q-fPPrsyKOjRpmm--vzPQ",
        "name": "Kuroyoru Yami",
        "handle": "@kuroyoruyami",
        "channel_url": "https://www.youtube.com/channel/UC2q-fPPrsyKOjRpmm--vzPQ",
        "agency": "Independent",
        "activity_status": "active",
        "vtuber_status": "CONFIRMED",
        "person_id": "vtuber_kuroyoruyami",
        "canonical_name": "Kuroyoru Yami",
        "channel_type": "main",
        "subscriber_count": 1240,
        "video_count": 35,
        "view_count": 10728,
        "last_video_published_at": "2026-09-01T00:00:00+00:00",
        "country": "TH",
        "thai_confidence": 1.0,
        "reference_sources": "User Verification; YouTube Channel",
        "evidence_notes": "VTuber ชายไทย (คุโรโยรุ ยามิ) นินจาแห่งความมืด; Thai VTuber confirmed",
        "enabled": True,
        "priority": "C"
    },
    {
        "channel_id": "UCfIXIjmCUKMBdmB2EspTygw",
        "name": "crazyghsot",
        "handle": "@crazyghsot",
        "channel_url": "https://www.youtube.com/channel/UCfIXIjmCUKMBdmB2EspTygw",
        "agency": "Independent",
        "activity_status": "active",
        "vtuber_status": "CONFIRMED",
        "person_id": "vtuber_crazyghsot",
        "canonical_name": "crazyghsot",
        "channel_type": "main",
        "subscriber_count": 2240,
        "video_count": 113,
        "view_count": 0,
        "last_video_published_at": "2026-09-01T00:00:00+00:00",
        "country": "TH",
        "thai_confidence": 1.0,
        "reference_sources": "User Verification; YouTube Channel",
        "evidence_notes": "VTuber & สายวาด/กราฟิกไทย (เคยร่วมงานอีเวนต์ไทยอย่าง Maruya); Thai VTuber confirmed",
        "enabled": True,
        "priority": "C"
    },
    {
        "channel_id": "UCOv6QnpFZfsVsOfh581sFrA",
        "name": "KitadesuS",
        "handle": "@KitadesuS_MDZ",
        "channel_url": "https://www.youtube.com/channel/UCOv6QnpFZfsVsOfh581sFrA",
        "agency": "Independent",
        "activity_status": "active",
        "vtuber_status": "CONFIRMED",
        "person_id": "vtuber_KitadesuS_MDZ",
        "canonical_name": "KitadesuS",
        "channel_type": "main",
        "subscriber_count": 102,
        "video_count": 256,
        "view_count": 239,
        "last_video_published_at": "2026-09-01T00:00:00+00:00",
        "country": "TH",
        "thai_confidence": 1.0,
        "reference_sources": "User Verification; YouTube Channel",
        "evidence_notes": "VTuber ชายไทย (คิตะเดสสึ / หมาพุดดิ้ง) สายเกม FPS/ร้องเพลง; Thai VTuber confirmed",
        "enabled": True,
        "priority": "D"
    },
    {
        "channel_id": "UCobiRetMOLHDrdLfLQzGiAw",
        "name": "Elsenia Volentia",
        "handle": "@ElseniaVolentia",
        "channel_url": "https://www.youtube.com/channel/UCobiRetMOLHDrdLfLQzGiAw",
        "agency": "Independent",
        "activity_status": "active",
        "vtuber_status": "CONFIRMED",
        "person_id": "vtuber_ElseniaVolentia",
        "canonical_name": "Elsenia Volentia",
        "channel_type": "main",
        "subscriber_count": 411,
        "video_count": 55,
        "view_count": 0,
        "last_video_published_at": "2026-09-01T00:00:00+00:00",
        "country": "TH",
        "thai_confidence": 1.0,
        "reference_sources": "User Verification; YouTube Channel",
        "evidence_notes": "VTuber ชายไทย; Thai VTuber confirmed",
        "enabled": True,
        "priority": "D"
    }
]

now_iso = datetime.now(timezone.utc).isoformat()

# 1. Update data/thai_vtuber_registry.csv
reg_csv = Path("data/thai_vtuber_registry.csv")
existing_rows = []
if reg_csv.exists():
    with open(reg_csv, "r", encoding="utf-8") as f:
        existing_rows = list(csv.DictReader(f))

existing_ids = {r["channel_id"] for r in existing_rows}
fieldnames = list(existing_rows[0].keys())

added_count = 0
for v in NEW_VTUBERS:
    if v["channel_id"] not in existing_ids:
        row = {
            "channel_id": v["channel_id"],
            "name": v["name"],
            "handle": v["handle"],
            "channel_url": v["channel_url"],
            "agency": v["agency"],
            "activity_status": v["activity_status"],
            "vtuber_status": v["vtuber_status"],
            "person_id": v["person_id"],
            "canonical_name": v["canonical_name"],
            "channel_type": v["channel_type"],
            "subscriber_count": str(v["subscriber_count"]),
            "video_count": str(v["video_count"]),
            "view_count": str(v["view_count"]),
            "last_video_published_at": v["last_video_published_at"],
            "country": v["country"],
            "thai_confidence": str(v["thai_confidence"]),
            "reference_sources": v["reference_sources"],
            "checked_date": now_iso,
            "evidence_notes": v["evidence_notes"],
            "enabled": str(v["enabled"])
        }
        existing_rows.append(row)
        existing_ids.add(v["channel_id"])
        added_count += 1

with open(reg_csv, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(existing_rows)

print(f"Updated {reg_csv}: total {len(existing_rows)} rows (+{added_count} new)")

# 2. Update data/thai_vtuber_registry.json
reg_json = Path("data/thai_vtuber_registry.json")
with open(reg_json, "w", encoding="utf-8") as f:
    json.dump(existing_rows, f, ensure_ascii=False, indent=2)
print(f"Updated {reg_json}: total {len(existing_rows)} records")

# 3. Update data/registry_vtubers.csv
vt_csv = Path("data/registry_vtubers.csv")
vt_rows = []
if vt_csv.exists():
    with open(vt_csv, "r", encoding="utf-8") as f:
        vt_rows = list(csv.DictReader(f))

vt_ids = {r["channel_id"] for r in vt_rows}
vt_fields = list(vt_rows[0].keys())

for v in NEW_VTUBERS:
    if v["channel_id"] not in vt_ids:
        row = {
            "channel_id": v["channel_id"],
            "handle": v["handle"],
            "name": v["name"],
            "subscriber_count": str(v["subscriber_count"]),
            "agency": v["agency"],
            "status": "ACCEPT",
            "thai_confidence": str(v["thai_confidence"]),
            "priority": v["priority"],
            "source_count": "1",
            "last_activity": v["last_video_published_at"],
            "last_collected": "",
            "streams_collected": "0",
            "enabled": "True"
        }
        vt_rows.append(row)
        vt_ids.add(v["channel_id"])

with open(vt_csv, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=vt_fields)
    writer.writeheader()
    writer.writerows(vt_rows)
print(f"Updated {vt_csv}: total {len(vt_rows)} rows")

# 4. Update web/data.json
web_json_path = Path("web/data.json")
with open(web_json_path, "r", encoding="utf-8") as f:
    web_data = json.load(f)

web_nodes = web_data.get("nodes", [])
web_node_ids = {n["id"] for n in web_nodes}

web_added = 0
for v in NEW_VTUBERS:
    if v["channel_id"] not in web_node_ids:
        new_node = {
            "id": v["channel_id"],
            "label": v["name"],
            "handle": v["handle"],
            "subscribers": v["subscriber_count"],
            "views": v["view_count"],
            "agency": v["agency"],
            "priority": v["priority"],
            "status": v["activity_status"],
            "degree": 0.0,
            "betweenness": 0.0,
            "pagerank": 0.0
        }
        web_nodes.append(new_node)
        web_node_ids.add(v["channel_id"])
        web_added += 1

web_data["nodes"] = web_nodes
web_data["metadata"]["total_vtubers"] = len(web_nodes)
# Update Independent member count in agencies array
for ag in web_data.get("agencies", []):
    if ag["name"] == "Independent":
        ag["member_count"] += web_added

with open(web_json_path, "w", encoding="utf-8") as f:
    json.dump(web_data, f, ensure_ascii=False, indent=2)

print(f"Updated {web_json_path}: total {len(web_nodes)} nodes (+{web_added} new), Independent count: {ag['member_count']}")
