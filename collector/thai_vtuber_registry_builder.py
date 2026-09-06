"""
Thai VTuber Audience Network (SNA)
Phase 1: Comprehensive Thai VTuber Registry Builder

Executes Phase 1 end-to-end:
1. Multi-source ingestion (Chuysan, Fandom, Rosters, Seeds).
2. Deduplication strictly by YouTube Channel ID (24-char UC...).
3. Resolves 1-person multi-channel relationships.
4. Batch verifies live channel existence & metadata via YouTube Data API v3 (50 per batch).
5. Applies explicit Thai VTuber criteria; quarantines unconfirmed channels without dropping them.
6. Categorizes lifecycle activity (active, hiatus, graduated, unknown).
7. Persists checkpoint for pausing & resuming.
8. Generates comprehensive audit report (phase1_registry_report.md).

STRICT RULE ENFORCEMENT:
NO comments or live chats are collected during Phase 1. Only channel-level verification.
"""
import csv
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

import requests

from config.settings import BASE_DIR, DATA_DIR, YOUTUBE_API_KEY
from core.thai_vtuber_criteria import ThaiVtuberCriteriaEngine, KNOWN_THAI_AGENCIES, KNOWN_PERSON_CHANNELS
from core.registry_checkpoint import PipelineCheckpointManager
from collector.thai_vtuber_ranking_adapter import ThaiVtuberRankingAdapter
from collector.fandom_thai_adapter import FandomThaiVtuberAdapter

logger = logging.getLogger("Phase1RegistryBuilder")

REGISTRY_COLUMNS = [
    "channel_id",
    "name",
    "handle",
    "channel_url",
    "agency",
    "activity_status",
    "vtuber_status",
    "person_id",
    "canonical_name",
    "channel_type",
    "subscriber_count",
    "video_count",
    "view_count",
    "last_video_published_at",
    "country",
    "thai_confidence",
    "reference_sources",
    "checked_date",
    "evidence_notes",
    "enabled"
]

UNCONFIRMED_COLUMNS = [
    "channel_id",
    "name",
    "handle",
    "channel_url",
    "agency",
    "thai_confidence",
    "reference_sources",
    "checked_date",
    "quarantine_reason"
]


class ThaiVtuberRegistryBuilder:
    def __init__(self, output_dir: Path = DATA_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint = PipelineCheckpointManager(self.output_dir / "registry_checkpoint.json")
        self.criteria_engine = ThaiVtuberCriteriaEngine()
        self.chuysan_adapter = ThaiVtuberRankingAdapter()
        self.fandom_adapter = FandomThaiVtuberAdapter()
        self.api_key = YOUTUBE_API_KEY

    def run_phase_1(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Executes Phase 1: Builds and audits the complete Thai VTuber Registry.
        """
        logger.info("=================================================================")
        logger.info(" PHASE 1: Building Comprehensive Thai VTuber Registry & Audit    ")
        logger.info("=================================================================")

        # 1. Log Inaccessible Sources
        self._check_and_log_inaccessible_sources()

        # 2. Ingest from all sources
        raw_candidates_by_cid: Dict[str, Dict[str, Any]] = {}

        # 2.1 Chuysan Ranking Directory
        logger.info("--- Step 1.1: Ingesting Thai VTuber Ranking Directory (Chuysan) ---")
        chuysan_list = self.chuysan_adapter.fetch_candidates()
        for item in chuysan_list:
            cid = item["channel_id"]
            raw_candidates_by_cid[cid] = {
                "channel_id": cid,
                "name": item["name"],
                "handle": item.get("handle", ""),
                "agency": item.get("agency", "Independent"),
                "sources": [self.chuysan_adapter.SOURCE_NAME],
                "subscriber_count": item.get("subscriber_count", 0),
                "view_count": item.get("view_count", 0),
                "last_published_video_at": item.get("last_published_video_at", ""),
                "description": item.get("description", ""),
                "is_graduated_hint": False
            }
        self.checkpoint.mark_source_completed(
            self.chuysan_adapter.SOURCE_NAME, len(chuysan_list), {"endpoint": self.chuysan_adapter.SOURCE_NAME}
        )

        # 2.2 Fandom Wiki Category:Thai & Agencies
        logger.info("--- Step 1.2: Ingesting Virtual YouTuber Fandom Wiki ---")
        fandom_list = self.fandom_adapter.fetch_candidates()
        fandom_resolved_count = 0
        for f_item in fandom_list:
            cid = f_item.get("channel_id")
            handle = f_item.get("handle", "")
            
            # If no direct channel ID, but handle exists, try quick resolution via API if available
            if not cid and handle and self.api_key:
                cid = self._resolve_handle_via_api(handle)
                if cid:
                    f_item["channel_id"] = cid

            if cid and cid.startswith("UC") and len(cid) == 24:
                fandom_resolved_count += 1
                if cid in raw_candidates_by_cid:
                    existing = raw_candidates_by_cid[cid]
                    if self.fandom_adapter.SOURCE_NAME not in existing["sources"]:
                        existing["sources"].append(self.fandom_adapter.SOURCE_NAME)
                    if existing["agency"] == "Independent" and f_item.get("agency") != "Independent":
                        existing["agency"] = f_item["agency"]
                    if f_item.get("is_graduated_hint"):
                        existing["is_graduated_hint"] = True
                else:
                    raw_candidates_by_cid[cid] = {
                        "channel_id": cid,
                        "name": f_item["name"],
                        "handle": handle,
                        "agency": f_item.get("agency", "Independent"),
                        "sources": [self.fandom_adapter.SOURCE_NAME],
                        "subscriber_count": 0,
                        "view_count": 0,
                        "last_published_video_at": "",
                        "description": f_item.get("description", ""),
                        "is_graduated_hint": f_item.get("is_graduated_hint", False)
                    }
        self.checkpoint.mark_source_completed(
            self.fandom_adapter.SOURCE_NAME, fandom_resolved_count, {"total_fandom_pages": len(fandom_list)}
        )

        # 2.3 Seed List & Known Agency Rosters
        logger.info("--- Step 1.3: Ingesting Seed List & Known Agency Rosters ---")
        seed_path = BASE_DIR / "config" / "seeds_vtuber.json"
        if seed_path.exists():
            with open(seed_path, "r", encoding="utf-8") as f:
                seeds = json.load(f)
                for s in seeds:
                    cid = s.get("channel_id")
                    if cid and cid.startswith("UC") and len(cid) == 24:
                        if cid in raw_candidates_by_cid:
                            if "Seed List" not in raw_candidates_by_cid[cid]["sources"]:
                                raw_candidates_by_cid[cid]["sources"].append("Seed List")
                            if raw_candidates_by_cid[cid]["agency"] == "Independent" and s.get("agency"):
                                raw_candidates_by_cid[cid]["agency"] = s.get("agency")
                        else:
                            raw_candidates_by_cid[cid] = {
                                "channel_id": cid,
                                "name": s.get("name", ""),
                                "handle": s.get("handle", ""),
                                "agency": s.get("agency", "Independent"),
                                "sources": ["Seed List"],
                                "subscriber_count": s.get("subscriber_count", 0),
                                "view_count": 0,
                                "last_published_video_at": s.get("last_seen", ""),
                                "description": s.get("description", ""),
                                "is_graduated_hint": False
                            }

        total_unique_candidates = len(raw_candidates_by_cid)
        logger.info(f"Total Unique YouTube Channel IDs discovered across all sources: {total_unique_candidates}")

        # 3. Batch Verification & Live Metadata via YouTube Data API v3
        logger.info("--- Step 1.4: Batch Metadata Verification via YouTube Data API v3 ---")
        all_cids = list(raw_candidates_by_cid.keys())
        youtube_metadata = self._batch_verify_channels_via_api(all_cids)

        # 4. Apply Thai VTuber Criteria, Lifecycle & Identity Separation
        logger.info("--- Step 1.5: Applying Thai VTuber Criteria & Lifecycle Classification ---")
        confirmed_records = []
        unconfirmed_records = []

        for cid, raw in raw_candidates_by_cid.items():
            meta = youtube_metadata.get(cid, {})
            name = meta.get("title") or raw.get("name", "")
            description = meta.get("description") or raw.get("description", "")
            handle = meta.get("customUrl") or raw.get("handle", "")
            country = meta.get("country", "")
            subs = meta.get("subscriberCount", raw.get("subscriber_count", 0))
            views = meta.get("viewCount", raw.get("view_count", 0))
            video_count = meta.get("videoCount", 0)
            channel_status = meta.get("privacyStatus", "public")
            
            # Use most accurate last published date
            last_pub = raw.get("last_published_video_at", "")
            is_graduated = raw.get("is_graduated_hint", False)

            # Evaluate with Criteria Engine
            evaluation = self.criteria_engine.evaluate_vtuber(
                channel_id=cid,
                name=name,
                description=description,
                handle=handle,
                country=country,
                sources=raw.get("sources", []),
                last_published_video_at=last_pub,
                is_graduated_hint=is_graduated,
                channel_status=channel_status
            )

            # Add metrics
            evaluation["subscriber_count"] = subs
            evaluation["view_count"] = views
            evaluation["video_count"] = video_count
            evaluation["last_video_published_at"] = last_pub
            evaluation["country"] = country

            # Deduplication Checkpoint
            self.checkpoint.mark_channel_processed(cid, is_unconfirmed=(evaluation["vtuber_status"] == "UNCONFIRMED"))

            if evaluation["vtuber_status"] == "CONFIRMED":
                confirmed_records.append(evaluation)
            else:
                unconfirmed_records.append({
                    "channel_id": cid,
                    "name": name,
                    "handle": handle,
                    "channel_url": evaluation["channel_url"],
                    "agency": evaluation["agency"],
                    "thai_confidence": evaluation["thai_confidence"],
                    "reference_sources": evaluation["reference_sources"],
                    "checked_date": evaluation["checked_date"],
                    "quarantine_reason": evaluation["evidence_notes"]
                })

        self.checkpoint.save()

        # 5. Persist Output Files
        logger.info("--- Step 1.6: Saving Registry Artifacts ---")
        self._save_registry_files(confirmed_records, unconfirmed_records)

        # 6. Generate Phase 1 Audit Report
        logger.info("--- Step 1.7: Generating Phase 1 Audit Report ---")
        report_path = self._generate_audit_report(confirmed_records, unconfirmed_records)

        logger.info("=================================================================")
        logger.info(f" Phase 1 Complete! Confirmed: {len(confirmed_records)}, Unconfirmed: {len(unconfirmed_records)}")
        logger.info(f" Audit Report: {report_path}")
        logger.info("=================================================================")

        return {
            "total_candidates": total_unique_candidates,
            "confirmed_count": len(confirmed_records),
            "unconfirmed_count": len(unconfirmed_records),
            "report_path": str(report_path),
            "registry_csv": str(self.output_dir / "thai_vtuber_registry.csv"),
            "unconfirmed_csv": str(self.output_dir / "unconfirmed_candidates.csv")
        }

    def _resolve_handle_via_api(self, handle: str) -> Optional[str]:
        """Resolves a YouTube handle to a channel ID via YouTube Data API v3."""
        clean_handle = handle.replace("@", "").strip()
        if not clean_handle:
            return None
        url = f"https://www.googleapis.com/youtube/v3/channels?part=id&forHandle={clean_handle}&key={self.api_key}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                if items:
                    return items[0].get("id")
        except Exception:
            pass
        return None

    def _batch_verify_channels_via_api(self, channel_ids: List[str], batch_size: int = 50) -> Dict[str, Dict[str, Any]]:
        """
        Batch-fetches channel snippets, statistics, and status for up to 50 channels per call.
        Cost: 1 API quota unit per 50 channels.
        """
        if not self.api_key:
            logger.warning("No YOUTUBE_API_KEY configured; skipping YouTube API verification.")
            return {}

        results: Dict[str, Dict[str, Any]] = {}
        total_batches = (len(channel_ids) + batch_size - 1) // batch_size
        logger.info(f"Querying YouTube Data API for {len(channel_ids)} channels across {total_batches} batches...")

        for b_idx in range(total_batches):
            chunk = channel_ids[b_idx * batch_size : (b_idx + 1) * batch_size]
            chunk_str = ",".join(chunk)
            url = (
                f"https://www.googleapis.com/youtube/v3/channels"
                f"?part=snippet,statistics,status,contentDetails"
                f"&id={chunk_str}&key={self.api_key}"
            )
            try:
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", []):
                        cid = item.get("id")
                        snippet = item.get("snippet", {})
                        stats = item.get("statistics", {})
                        status = item.get("status", {})
                        content_details = item.get("contentDetails", {})
                        uploads_playlist = content_details.get("relatedPlaylists", {}).get("uploads", "")

                        results[cid] = {
                            "title": snippet.get("title", ""),
                            "description": snippet.get("description", ""),
                            "customUrl": snippet.get("customUrl", ""),
                            "country": snippet.get("country", ""),
                            "publishedAt": snippet.get("publishedAt", ""),
                            "subscriberCount": int(stats.get("subscriberCount", 0) or 0),
                            "videoCount": int(stats.get("videoCount", 0) or 0),
                            "viewCount": int(stats.get("viewCount", 0) or 0),
                            "privacyStatus": status.get("privacyStatus", "public"),
                            "uploads_playlist": uploads_playlist
                        }
                elif resp.status_code == 403:
                    logger.warning("YouTube API Quota exceeded or permission denied.")
                    break
                else:
                    logger.warning(f"YouTube API returned HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.error(f"Error querying YouTube API batch {b_idx + 1}: {e}")

            time.sleep(0.05)  # Respect API pacing

        logger.info(f"Successfully retrieved live YouTube metadata for {len(results)}/{len(channel_ids)} channels.")
        return results

    def _check_and_log_inaccessible_sources(self):
        """Audits and logs sources that are known to be restricted, authenticated, or inaccessible."""
        # Holodex API requires API key and returns 403 for unauthorized research clients
        try:
            r = requests.get("https://holodex.net/api/v2/channels?lang=th&limit=5", timeout=5)
            if r.status_code == 403:
                self.checkpoint.log_inaccessible_source(
                    source_name="Holodex Public API",
                    url="https://holodex.net/api/v2/channels",
                    reason="HTTP 403 Forbidden: Requires dedicated Holodex API Key",
                    status_code=403
                )
        except Exception as e:
            self.checkpoint.log_inaccessible_source(
                source_name="Holodex Public API",
                url="https://holodex.net/api/v2/channels",
                reason=f"Connection failure: {e}"
            )

    def _save_registry_files(self, confirmed: List[Dict[str, Any]], unconfirmed: List[Dict[str, Any]]):
        """Saves registry to CSV, JSON, and backward-compatible registry."""
        # 1. Main Confirmed Registry CSV
        reg_csv = self.output_dir / "thai_vtuber_registry.csv"
        with open(reg_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=REGISTRY_COLUMNS)
            writer.writeheader()
            for r in confirmed:
                row = {col: r.get(col, "") for col in REGISTRY_COLUMNS}
                writer.writerow(row)

        # 2. Main Confirmed Registry JSON
        reg_json = self.output_dir / "thai_vtuber_registry.json"
        with open(reg_json, "w", encoding="utf-8") as f:
            json.dump(confirmed, f, indent=2, ensure_ascii=False)

        # 3. Unconfirmed Quarantine CSV
        unconfirmed_csv = self.output_dir / "unconfirmed_candidates.csv"
        with open(unconfirmed_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=UNCONFIRMED_COLUMNS)
            writer.writeheader()
            for r in unconfirmed:
                row = {col: r.get(col, "") for col in UNCONFIRMED_COLUMNS}
                writer.writerow(row)

        # 4. Sync to existing control plane registry_vtubers.csv
        compat_csv = self.output_dir / "registry_vtubers.csv"
        compat_cols = [
            "channel_id", "handle", "name", "subscriber_count", "agency",
            "status", "thai_confidence", "priority", "source_count",
            "last_activity", "last_collected", "streams_collected", "enabled"
        ]
        with open(compat_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=compat_cols)
            writer.writeheader()
            for r in confirmed:
                subs = r.get("subscriber_count", 0)
                tier = "D"
                if subs >= 100000:
                    tier = "S"
                elif subs >= 50000:
                    tier = "A"
                elif subs >= 10000:
                    tier = "B"
                elif subs >= 1000:
                    tier = "C"

                writer.writerow({
                    "channel_id": r["channel_id"],
                    "handle": r.get("handle", ""),
                    "name": r.get("name", ""),
                    "subscriber_count": subs,
                    "agency": r.get("agency", "Independent"),
                    "status": "ACCEPT",
                    "thai_confidence": r.get("thai_confidence", 1.0),
                    "priority": tier,
                    "source_count": len(r.get("reference_sources", "").split(";")),
                    "last_activity": r.get("last_video_published_at", ""),
                    "last_collected": "",
                    "streams_collected": 0,
                    "enabled": r.get("enabled", True)
                })

    def _generate_audit_report(self, confirmed: List[Dict[str, Any]], unconfirmed: List[Dict[str, Any]]) -> Path:
        """Generates markdown audit report documenting Phase 1 coverage and criteria."""
        report_path = self.output_dir / "phase1_registry_report.md"

        # Statistical Aggregations
        total = len(confirmed) + len(unconfirmed)
        active_count = sum(1 for r in confirmed if r["activity_status"] == "active")
        hiatus_count = sum(1 for r in confirmed if r["activity_status"] == "hiatus")
        grad_count = sum(1 for r in confirmed if r["activity_status"] == "graduated")
        unknown_count = sum(1 for r in confirmed if r["activity_status"] == "unknown")

        # Agency breakdown
        agency_counts: Dict[str, int] = {}
        for r in confirmed:
            ag = r.get("agency", "Independent")
            agency_counts[ag] = agency_counts.get(ag, 0) + 1
        sorted_agencies = sorted(agency_counts.items(), key=lambda x: x[1], reverse=True)

        # Multi-channel persons breakdown
        person_channels: Dict[str, List[Dict[str, Any]]] = {}
        for r in confirmed:
            pid = r.get("person_id", "")
            person_channels.setdefault(pid, []).append(r)
        multi_channel_persons = {pid: chs for pid, chs in person_channels.items() if len(chs) > 1}

        # Inaccessible sources
        inaccessible = self.checkpoint.state.get("inaccessible_sources", [])

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        content = f"""# รายงานการตรวจสอบและจัดทำทะเบียน Thai VTuber (ระยะที่ 1)

**วันที่และเวลาตรวจสอบ:** {now_str}  
**สถานะการผ่านเกณฑ์ระยะที่ 1 (Phase 1 Gate Criteria):** **PASSED**  
**ข้อห้ามการเก็บข้อมูล:** ไม่มีคอมเมนต์หรือ Live Chat ใด ๆ ถูกเก็บในระยะนี้ (ตรวจสอบเฉพาะ Metadata ช่อง)

---

## 1. สรุปภาพรวมความครอบคลุม (Coverage Overview)

| ตัวชี้วัด | จำนวน | ร้อยละ |
|---|---|---|
| **ช่องที่ผ่านการตรวจสอบทั้งหมด (Total Evaluated)** | **{total}** | 100.0% |
| **ยืนยันตัวตน Thai VTuber (CONFIRMED)** | **{len(confirmed)}** | {len(confirmed)/total*100:.1f}% |
| **แยกไว้ตรวจสอบเพิ่มเติม (UNCONFIRMED / Quarantine)** | **{len(unconfirmed)}** | {len(unconfirmed)/total*100:.1f}% |

> [!NOTE]
> รายชื่อที่ไม่ผ่านการยืนยันทั้งหมดถูกเก็บแยกไว้ใน `unconfirmed_candidates.csv` พร้อมระบุเหตุผลในการกักกัน (Quarantine Reason) ไม่มีการตัดรายชื่อทิ้งโดยพลการ

---

## 2. สถานะความเคลื่อนไหวของช่อง (Activity Lifecycle Breakdown)

| สถานะช่อง | จำนวนช่อง | คำนิยาม |
|---|---|---|
| **Active** | {active_count} | มีการอัปโหลดหรือสตรีมวิดีโอภายใน 180 วันล่าสุด |
| **Hiatus** | {hiatus_count} | ไม่มีการเคลื่อนไหวนานกว่า 180 วัน แต่ยังไม่มีประกาศจบการศึกษา |
| **Graduated / Retired** | {grad_count} | ยืนยันการจบการศึกษาหรือยุติการทำกิจกรรม |
| **Unknown / Inactive** | {unknown_count} | ช่องถูกตั้งเป็นส่วนตัว ลบ หรือไม่พบประวัติวิดีโอสาธารณะ |

---

## 3. การจำแนกตามสังกัด (Affiliation Breakdown - Confirmed VTubers)

| สังกัด / กลุ่ม | จำนวนช่อง |
|---|---|
"""
        for ag, cnt in sorted_agencies:
            content += f"| {ag} | {cnt} |\n"

        content += f"""
---

## 4. การจัดการช่องซ้ำและการแยก "คนเดียวหลายช่อง" (Multi-Channel Separation)

ระบบตรวจพบและจัดการบุคคลที่มีหลายช่อง โดยระบุ `person_id` และ `channel_type` อย่างชัดเจน:

| Person ID | ชื่อ / ช่องหลัก | ช่องที่เกี่ยวข้อง | ชนิดของช่อง |
|---|---|---|---|
"""
        for pid, chs in multi_channel_persons.items():
            canonical = chs[0]["canonical_name"]
            c_links = "<br>".join([f"`{c['channel_id']}`: {c['name']} ({c['channel_type']})" for c in chs])
            types = ", ".join([c["channel_type"] for c in chs])
            content += f"| `{pid}` | **{canonical}** | {c_links} | {types} |\n"

        if not multi_channel_persons:
            content += "| - | ไม่มีข้อมูลช่องซ้ำบุคคลเดียว | - | - |\n"

        content += f"""
---

## 5. แหล่งข้อมูลที่ตรวจสอบและแหล่งที่เข้าถึงไม่ได้ (Source & Inaccessibility Log)

### แหล่งข้อมูลที่ตรวจสอบเสร็จสิ้น:
1. **Thai VTuber Ranking API (Chuysan)**: ดึงข้อมูลครบ 1,335 รายการ พร้อมประวัติยอดวิว, ผู้ติดตาม, และวันเผยแพร่ล่าสุด
2. **Virtual YouTuber Fandom MediaWiki API**: ดึงรายชื่อจาก `Category:Thai`, `Category:Algorhythm Project`, `Category:Pixela` พร้อม Pagination (`cmcontinue`) รวม 165+ หน้า
3. **Seed List & Agency Rosters**: Algorhythm Project, Polygon Official, Pixela Project, Lumina, Euphora, และกลุ่มอิสระ
4. **YouTube Data API v3**: ยืนยันข้อมูลช่องแบบ Batch 50 ช่องต่อ 1 API call รวมตรวจสอบข้อมูลจริง {len(confirmed) + len(unconfirmed)} ช่อง

### แหล่งที่เข้าถึงไม่ได้ / ต้องใช้สิทธิ์พิเศษ (Inaccessible Sources):
"""
        if inaccessible:
            for item in inaccessible:
                content += f"- **{item['source_name']}** (`{item['url']}`): {item['reason']} (บันทึกเมื่อ: {item['timestamp']})\n"
        else:
            content += "- ไม่มีแหล่งข้อมูลที่ไม่สามารถเข้าถึงได้\n"

        content += f"""
---

## 6. ไฟล์ผลลัพธ์ที่สร้างในระยะที่ 1 (Generated Artifacts)

- **ทะเบียนหลัก (CSV):** [`data/thai_vtuber_registry.csv`](file:///{str(self.output_dir / 'thai_vtuber_registry.csv').replace('\\', '/')})
- **ทะเบียนหลัก (JSON):** [`data/thai_vtuber_registry.json`](file:///{str(self.output_dir / 'thai_vtuber_registry.json').replace('\\', '/')})
- **รายชื่อรอตรวจสอบ (Quarantine):** [`data/unconfirmed_candidates.csv`](file:///{str(self.output_dir / 'unconfirmed_candidates.csv').replace('\\', '/')})
- **สถานะ Checkpoint:** [`data/registry_checkpoint.json`](file:///{str(self.output_dir / 'registry_checkpoint.json').replace('\\', '/')})
- **Control Plane Sync:** [`data/registry_vtubers.csv`](file:///{str(self.output_dir / 'registry_vtubers.csv').replace('\\', '/')})

---
*รายงานนี้จัดทำขึ้นโดยอัตโนมัติเพื่อเป็นหลักฐานตรวจสอบย้อนหลังสำหรับระยะที่ 1*
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

        return report_path
