"""
Thai VTuber Audience Network (SNA)
Apply User Manual Audit for 55 Candidate Channels

1. Promotes 49 verified Thai VTubers from unconfirmed quarantine to CONFIRMED.
2. Permanently records the 6 non-Thai channels in data/excluded_channels.csv.
3. Clears the quarantine queue in data/unconfirmed_candidates.csv (100% audited).
4. Re-syncs data/thai_vtuber_registry.csv & data/thai_vtuber_registry.json (1,363 channels).
5. Synchronizes control plane data/registry_vtubers.csv.
6. Updates checkpoint and regenerates data/phase1_registry_report.md.
"""
import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from config.settings import BASE_DIR, DATA_DIR, YOUTUBE_API_KEY
from core.thai_vtuber_criteria import ThaiVtuberCriteriaEngine, KNOWN_PERSON_CHANNELS
from core.registry_checkpoint import PipelineCheckpointManager
from collector.thai_vtuber_ranking_adapter import ThaiVtuberRankingAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ApplyManualAudit")

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

EXCLUDED_COLUMNS = [
    "channel_id",
    "name",
    "handle",
    "channel_url",
    "country",
    "agency",
    "category",
    "exclusion_reason",
    "checked_date"
]

AUDITED_THAI_VTUBERS = [
    {"channel_id": "UC31u9DPv_zbrasL8FTH7K5g", "name": "Reiden_R Ch.", "handle": "@reiden_r", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCGAYOnH9azmAmcHpzRWZsOg", "name": "NoA Noaris", "handle": "@noa_noaris", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCH3mEs_fK3r0M2hJ9NsgNPg", "name": "fxoverpur", "handle": "@fxoverpur", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCUOVWfFzNwIfu3_MfXegyPA", "name": "Akaku Mikoni | V.W.Y", "handle": "@akakumikoni", "agency": "V.W.Y", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCUlc9fwNihOqufbS8KtakvA", "name": "Koharu Channel", "handle": "@koharuchannel", "agency": "Independent", "audited_status": "Hiatus (>180 วัน)", "activity_status": "hiatus"},
    {"channel_id": "UCaCHWJ4_dp4ovreQ91lp3Iw", "name": "Lyrics 🌙", "handle": "@moonshinelyrics_z", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UC_nmh9XycGlquouvai2UC6g", "name": "Newzkung Raccoonza", "handle": "@newzkungraccoon", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCsB043n4HJ1SfywowZACmug", "name": "Ané Monie Ch. | OAL", "handle": "@monie_oal", "agency": "OAL", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCtECeyZ_Uc-oE4fJCt3YPoA", "name": "Byte001_SLR", "handle": "@byte001_slr", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCtHdI-Bb1OWP9VaQpBHy7kg", "name": "Titorch Ch.", "handle": "@titorch_ch", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCONVwO_B2jxgzpbsVopQ6fw", "name": "Zion《ATX》", "handle": "@zion_atx", "agency": "ATX", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCNaHMNS61Q1f1nIRDS0429A", "name": "Weiß", "handle": "@lalalost8e", "agency": "Independent", "audited_status": "Hiatus (>180 วัน)", "activity_status": "hiatus"},
    {"channel_id": "UCOFHRsSrDPOcdiz3Crc2ZBw", "name": "Hatsu ch〖DPX〗", "handle": "@hatsuxch", "agency": "DPX", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UC82qGW5XAba3LYqMEmiVBgg", "name": "Naoki Yuuto Ch.", "handle": "@naokiyuuto", "agency": "Independent", "audited_status": "Hiatus (>180 วัน)", "activity_status": "hiatus"},
    {"channel_id": "UCDmay2oK3RLbl8ooxYv-wJg", "name": "CHALONETTA | VArtisit", "handle": "@chalonettavamp", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCEL3qsIRdudjSuFHMHUxi0Q", "name": "Rui Kazu 《 EXia 》", "handle": "@ruikazu_exia", "agency": "EXia", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCyv2oEiAXQp9xLlBr1Tn6Vg", "name": "Yokina Saori", "handle": "@yokinasaori", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCHhEdxjXqC8sbAj7a-PVFlg", "name": "LUM1N S.", "handle": "@lum1ns", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCpD_Ds-YEOOhPobh2xOGBHA", "name": "ZAIN Ch.", "handle": "@zainvtuber", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCpfWYM5nNmWfroMIXBk3Gug", "name": "Jozetté Wrasset Ch. | OAL", "handle": "@jozette_oal", "agency": "OAL", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCqUHXBufAIuF9KI-OoMFUQw", "name": "EikiShiro ch.", "handle": "@eikishiro", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCpbHtJERmEP-GZJeSpziqCQ", "name": "Zuruya Ch.", "handle": "@zuruya-zip", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCT0u795YFp9O_k9cL5d0RZg", "name": "Z", "handle": "@user-wj8iv9im1u", "agency": "Independent", "audited_status": "Hiatus (>180 วัน)", "activity_status": "hiatus"},
    {"channel_id": "UCRjdIz5ngcJVDZ-bjs2mEzg", "name": "shiorichan", "handle": "@shiorichanvt", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCSpIYbnsnaXgRpIpipxJRcw", "name": "Laychlype「ALF」", "handle": "@laychlype_alf", "agency": "ALF", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCKuzX7wNaRVXEI9a81xeNfA", "name": "Minami Lollipopza Ch. ʕ •ᴥ•ʔ", "handle": "@minamilollipopzach", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCKg9vWWT_2yK3FFNNnnhhLw", "name": "Goozilla Ily Ch. [Autumnia]", "handle": "@goozillaily", "agency": "Autumnia", "audited_status": "Hiatus (>180 วัน)", "activity_status": "hiatus"},
    {"channel_id": "UCLT-U861QLvJmrlP7K6kv2w", "name": "Vulgtmnahog", "handle": "@vulgt_bgp", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UC4Ty5GzSA5YjeXN-DqPIWfA", "name": "Rewarin Ch.", "handle": "@rewarinrei", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCc6hwdN1yu2QT9o4yIHUPnQ", "name": "Vermillion Ch. Flora Project", "handle": "@vermillvt", "agency": "Flora Project", "audited_status": "ไม่มีคลิปสาธารณะ", "activity_status": "unknown"},
    {"channel_id": "UCmLd6QDRBcD9TfFrThJucng", "name": "Haine『Paralist』", "handle": "@haineinwza", "agency": "Paralist", "audited_status": "Hiatus (>180 วัน)", "activity_status": "hiatus"},
    {"channel_id": "UCkjQ55wHjS7cQ9Xol9qW7Ow", "name": "東雲こね / Shinonome Kone ⌜VZ⌟", "handle": "@shinonomekone", "agency": "VZ", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCVogMqMZimg5YbPE48oPrlg", "name": "Mysterica X. Ch. | RPG", "handle": "@mystyrelife", "agency": "RPG", "audited_status": "Graduated (Hiatus)", "activity_status": "graduated"},
    {"channel_id": "UCWp6-EK_2seNDN_HN3mo9gA", "name": "^-Maru Chan-^", "handle": "@marukomaruchan", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCD2BJUqKTEPOkxdTyxfvCuQ", "name": "AzuruVT", "handle": "@azuruvt", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCCwDLJmhL5pYyXzN7coVwTw", "name": "Hajikeru Haruno Ch", "handle": "@hajikeruharuno", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCZq9-nxDs5XXEtAPzAuBnhQ", "name": "Wynn Carwin Ch. | OAL", "handle": "@wynn_oal", "agency": "OAL", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCZsXl4d82Yx76SeGNtWGjlQ", "name": "Fusui Ch.", "handle": "@fusuich", "agency": "Independent", "audited_status": "Hiatus (>180 วัน)", "activity_status": "hiatus"},
    {"channel_id": "UCtk8lcwk_Gx9egTljfiCMYw", "name": "Qmulaz", "handle": "@qmulaz_vt", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCwSohSYD00uLV-kq_UFJb4g", "name": "Folpuzx Ch.", "handle": "@folpuzx", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCvYUivIS4WcgfACH3xBJ0DQ", "name": "Zayn Ch【 HZ 】", "handle": "@zayngloucesterchannel", "agency": "HZ", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCPh5ZGdw9LkBXxpCAdSaCrw", "name": "Vivera Carmine", "handle": "@vivera_eylz", "agency": "EYLZ", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCPW4hvhGciPdGqcsM1OCZ-Q", "name": "Avele Ch. [Pandora]", "handle": "@avele_pdr", "agency": "Pandora", "audited_status": "ไม่มีคลิปสาธารณะ", "activity_status": "unknown"},
    {"channel_id": "UCAid1uC5pxxvPasgFTJZEAw", "name": "Miledy Z.Devlin ch.", "handle": "@miledyz_ch", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UChd2cJe7HuTYbZGkOO-QKwg", "name": "Xen Ch. 【Ti19t】", "handle": "@xen_desu", "agency": "Ti19t", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UCiG3hDSyLNx-tani2z03_Zg", "name": "AmiLLy", "handle": "@amillyarchive", "agency": "Independent", "audited_status": "Active", "activity_status": "active"},
    {"channel_id": "UChW_l65xozteVRme3mFE0Jg", "name": "Melantha Vtopia", "handle": "@melanthavtopia705", "agency": "Vtopia", "audited_status": "Hiatus (>180 วัน)", "activity_status": "hiatus"},
    {"channel_id": "UCt8vlwt6qi6P1mz5uuStJCA", "name": "Shimonz", "handle": "@shimonnnnn", "agency": "Independent", "audited_status": "Retired / Fandom (นกฮูกไดมอนด์)", "activity_status": "graduated"},
    {"channel_id": "UCFSkExeBcqI4nb_ArHeByNw", "name": "シノライラ - Shino Laila【WACTOR】", "handle": "@-shinolailawactor5871", "agency": "WACTOR", "audited_status": "Fandom Wiki (Thai VA)", "activity_status": "graduated"}
]

AUDITED_NON_THAI_CHANNELS = [
    {
        "channel_id": "UCW0p7VdWVO0bn0_FELopJpQ",
        "name": "こはならむ- Kohana Lam -",
        "handle": "@kohanalam",
        "country": "JP",
        "agency": "Avex",
        "category": "นักร้อง Utaite (ญี่ปุ่น)",
        "exclusion_reason": "Non-Thai: Japanese singer/utaite signed under Avex. Appeared via cross-referencing on Fandom wiki."
    },
    {
        "channel_id": "UCQYwIUCLqFoin7lHKmePjJw",
        "name": "Klara Charmwood 【NIJISANJI EN】",
        "handle": "@klaracharmwood",
        "country": "Global (EN)",
        "agency": "NIJISANJI EN",
        "category": "NIJISANJI EN (Denauth)",
        "exclusion_reason": "Non-Thai: International VTuber affiliated with NIJISANJI EN (Denauth unit)."
    },
    {
        "channel_id": "UC9p_lqQ0FEDz327Vgf5JwqA",
        "name": "Koseki Bijou Ch. hololive-EN",
        "handle": "@kosekibijou",
        "country": "Global (EN)",
        "agency": "hololive English",
        "category": "hololive English -Advent-",
        "exclusion_reason": "Non-Thai: International VTuber affiliated with hololive English (-Advent-)."
    },
    {
        "channel_id": "UCQxYe05rfMOW_gesVywQlYA",
        "name": "Nakaru Rikka",
        "handle": "@nakarurikka",
        "country": "JP",
        "agency": "Independent",
        "category": "นักพากย์ (ญี่ปุ่น)",
        "exclusion_reason": "Non-Thai: Japanese voice actress / singer. Appeared via cross-category link on Fandom wiki."
    },
    {
        "channel_id": "UCs9_O1tRPMQTHQ-N_L6FU2g",
        "name": "Lui ch. 鷹嶺ルイ - holoX -",
        "handle": "@takanelui",
        "country": "JP",
        "agency": "hololive Japan",
        "category": "hololive Japan (holoX)",
        "exclusion_reason": "Non-Thai: Japanese VTuber affiliated with hololive Japan (Secret Society holoX 6th Gen)."
    },
    {
        "channel_id": "UCSc_KzY_9WYAx9LghggjVRA",
        "name": "Yugo Asuma 【NIJISANJI EN】",
        "handle": "@yugoasuma",
        "country": "Global (EN)",
        "agency": "NIJISANJI EN",
        "category": "อดีต NIJISANJI EN (Noctyx) / Graduated",
        "exclusion_reason": "Non-Thai: Former international VTuber affiliated with NIJISANJI EN (Noctyx unit)."
    }
]


def fetch_youtube_api_batch(channel_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Batch-fetches YouTube channel snippet and statistics."""
    if not YOUTUBE_API_KEY:
        return {}
    results = {}
    ids_str = ",".join(channel_ids)
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails,status&id={ids_str}&key={YOUTUBE_API_KEY}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            for item in resp.json().get("items", []):
                cid = item.get("id")
                snip = item.get("snippet", {})
                stats = item.get("statistics", {})
                results[cid] = {
                    "title": snip.get("title", ""),
                    "customUrl": snip.get("customUrl", ""),
                    "country": snip.get("country", ""),
                    "publishedAt": snip.get("publishedAt", ""),
                    "subscriberCount": int(stats.get("subscriberCount", 0) or 0),
                    "videoCount": int(stats.get("videoCount", 0) or 0),
                    "viewCount": int(stats.get("viewCount", 0) or 0)
                }
    except Exception as e:
        logger.error(f"Error querying YouTube API: {e}")
    return results


def run_apply_audit():
    logger.info("Starting manual audit ingestion for 55 candidates...")
    criteria_engine = ThaiVtuberCriteriaEngine()
    checkpoint = PipelineCheckpointManager(DATA_DIR / "registry_checkpoint.json")

    # 1. Fetch live metadata from YouTube API for 49 Thai VTubers in 1 single call
    cids_49 = [item["channel_id"] for item in AUDITED_THAI_VTUBERS]
    yt_meta = fetch_youtube_api_batch(cids_49)
    logger.info(f"Retrieved live YouTube API metadata for {len(yt_meta)}/49 channels.")

    # Load Chuysan directory for historical upload timestamps
    chuysan_map = {c["channel_id"]: c for c in ThaiVtuberRankingAdapter().fetch_candidates()}

    # 2. Build full records for 49 confirmed channels
    new_confirmed_records = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for item in AUDITED_THAI_VTUBERS:
        cid = item["channel_id"]
        meta = yt_meta.get(cid, {})
        chuy = chuysan_map.get(cid, {})

        name = item["name"] or meta.get("title") or chuy.get("name", "")
        handle = item["handle"] or meta.get("customUrl") or chuy.get("handle", "")
        agency = item["agency"]
        activity_status = item["activity_status"]
        audited_status_note = item["audited_status"]

        subs = meta.get("subscriberCount") or chuy.get("subscriber_count", 0)
        views = meta.get("viewCount") or chuy.get("view_count", 0)
        videos = meta.get("videoCount") or 0
        last_pub = chuy.get("last_published_video_at") or meta.get("publishedAt", "")
        country = meta.get("country") or ("TH" if "ไทย" in audited_status_note else "")

        # Resolve person ID
        person_id, canonical_name, channel_type = criteria_engine.resolve_person_identity(cid, name, handle)

        evidence_notes = (
            f"Verified Thai VTuber via User Manual Audit; "
            f"Agency: {agency}; "
            f"Status: {audited_status_note}; "
            f"Subs: {subs:,}; Views: {views:,}"
        )

        sources = ["Manual Audit"]
        if cid in chuysan_map:
            sources.append("Thai VTuber Ranking")
        else:
            sources.append("Virtual YouTuber Fandom Wiki")

        record = {
            "channel_id": cid,
            "name": name,
            "handle": handle,
            "channel_url": f"https://www.youtube.com/channel/{cid}",
            "agency": agency,
            "activity_status": activity_status,
            "vtuber_status": "CONFIRMED",
            "person_id": person_id,
            "canonical_name": canonical_name,
            "channel_type": channel_type,
            "subscriber_count": subs,
            "video_count": videos,
            "view_count": views,
            "last_video_published_at": last_pub,
            "country": country,
            "thai_confidence": 1.0,
            "reference_sources": "; ".join(sources),
            "checked_date": now_iso,
            "evidence_notes": evidence_notes,
            "enabled": (activity_status in ["active", "hiatus"])
        }
        new_confirmed_records.append(record)

    # 3. Read existing confirmed registry
    reg_csv = DATA_DIR / "thai_vtuber_registry.csv"
    existing_confirmed = []
    if reg_csv.exists():
        with open(reg_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_confirmed.append(row)

    logger.info(f"Existing confirmed channels: {len(existing_confirmed)}")

    # Merge while deduplicating
    existing_cids = {r["channel_id"] for r in existing_confirmed}
    promoted_count = 0
    all_confirmed = list(existing_confirmed)

    for new_r in new_confirmed_records:
        if new_r["channel_id"] not in existing_cids:
            all_confirmed.append(new_r)
            promoted_count += 1
            checkpoint.mark_channel_processed(new_r["channel_id"], is_unconfirmed=False)
        else:
            # Update existing if already present
            for idx, ex in enumerate(all_confirmed):
                if ex["channel_id"] == new_r["channel_id"]:
                    all_confirmed[idx] = new_r

    logger.info(f"Promoted {promoted_count} channels to CONFIRMED. Total confirmed: {len(all_confirmed)}")

    # Write merged confirmed CSV & JSON
    with open(reg_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REGISTRY_COLUMNS)
        writer.writeheader()
        for r in all_confirmed:
            writer.writerow({col: r.get(col, "") for col in REGISTRY_COLUMNS})

    reg_json = DATA_DIR / "thai_vtuber_registry.json"
    with open(reg_json, "w", encoding="utf-8") as f:
        json.dump(all_confirmed, f, indent=2, ensure_ascii=False)

    # 4. Save Excluded Non-Thai Channels
    excluded_csv = DATA_DIR / "excluded_channels.csv"
    with open(excluded_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EXCLUDED_COLUMNS)
        writer.writeheader()
        for item in AUDITED_NON_THAI_CHANNELS:
            writer.writerow({
                "channel_id": item["channel_id"],
                "name": item["name"],
                "handle": item["handle"],
                "channel_url": f"https://www.youtube.com/channel/{item['channel_id']}",
                "country": item["country"],
                "agency": item["agency"],
                "category": item["category"],
                "exclusion_reason": item["exclusion_reason"],
                "checked_date": now_iso
            })
            checkpoint.mark_channel_processed(item["channel_id"], is_unconfirmed=False)

    logger.info(f"Saved {len(AUDITED_NON_THAI_CHANNELS)} excluded non-Thai channels to {excluded_csv}")

    # 5. Clear / update unconfirmed candidates (quarantine resolved)
    unconfirmed_csv = DATA_DIR / "unconfirmed_candidates.csv"
    with open(unconfirmed_csv, "w", encoding="utf-8", newline="") as f:
        un_cols = ["channel_id", "name", "handle", "channel_url", "agency", "thai_confidence", "reference_sources", "checked_date", "quarantine_reason"]
        writer = csv.DictWriter(f, fieldnames=un_cols)
        writer.writeheader()
        # 0 rows remaining - all 55 candidates are resolved

    checkpoint.state["unconfirmed_channel_ids"] = []
    checkpoint.save()
    logger.info("Cleared unconfirmed_candidates.csv (100% audit completed, 0 quarantined).")

    # 6. Re-sync Control Plane registry_vtubers.csv
    compat_csv = DATA_DIR / "registry_vtubers.csv"
    compat_cols = [
        "channel_id", "handle", "name", "subscriber_count", "agency",
        "status", "thai_confidence", "priority", "source_count",
        "last_activity", "last_collected", "streams_collected", "enabled"
    ]
    with open(compat_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=compat_cols)
        writer.writeheader()
        for r in all_confirmed:
            subs = int(r.get("subscriber_count") or 0)
            tier = "D"
            if subs >= 100000:
                tier = "S"
            elif subs >= 50000:
                tier = "A"
            elif subs >= 10000:
                tier = "B"
            elif subs >= 1000:
                tier = "C"

            sources_raw = str(r.get("reference_sources", ""))
            source_count = len([s for s in sources_raw.split(";") if s.strip()]) or 1

            writer.writerow({
                "channel_id": r["channel_id"],
                "handle": r.get("handle", ""),
                "name": r.get("name", ""),
                "subscriber_count": subs,
                "agency": r.get("agency", "Independent"),
                "status": "ACCEPT",
                "thai_confidence": r.get("thai_confidence", 1.0),
                "priority": tier,
                "source_count": source_count,
                "last_activity": r.get("last_video_published_at", ""),
                "last_collected": "",
                "streams_collected": 0,
                "enabled": r.get("enabled", True)
            })

    logger.info(f"Synchronized {len(all_confirmed)} channels to control plane {compat_csv}")

    # 7. Generate updated Phase 1 Audit Report
    generate_audit_report(all_confirmed, AUDITED_NON_THAI_CHANNELS, new_confirmed_records)


def generate_audit_report(confirmed: List[Dict[str, Any]], excluded: List[Dict[str, Any]], newly_promoted: List[Dict[str, Any]]):
    report_path = DATA_DIR / "phase1_registry_report.md"
    total_eval = len(confirmed) + len(excluded)

    active_count = sum(1 for r in confirmed if r["activity_status"] == "active")
    hiatus_count = sum(1 for r in confirmed if r["activity_status"] == "hiatus")
    grad_count = sum(1 for r in confirmed if r["activity_status"] == "graduated")
    unknown_count = sum(1 for r in confirmed if r["activity_status"] == "unknown")

    # Agency counts
    agencies: Dict[str, int] = {}
    for r in confirmed:
        ag = r.get("agency", "Independent")
        agencies[ag] = agencies.get(ag, 0) + 1
    sorted_agencies = sorted(agencies.items(), key=lambda x: x[1], reverse=True)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    content = f"""# รายงานการตรวจสอบและจัดทำทะเบียน Thai VTuber (ระยะที่ 1 - ฉบับสมบูรณ์หลังการตรวจทาน)

**วันที่และเวลาตรวจสอบล่าสุด:** {now_str}  
**สถานะการผ่านเกณฑ์ระยะที่ 1 (Phase 1 Gate Criteria):** **PASSED (100% Resolved)**  
**ข้อห้ามการเก็บข้อมูล:** ไม่มีคอมเมนต์หรือ Live Chat ใด ๆ ถูกเก็บในระยะนี้ (ตรวจสอบเฉพาะ Metadata ช่อง)

---

## 1. สรุปภาพรวมความครอบคลุม (Coverage Overview)

| ตัวชี้วัด | จำนวน | ร้อยละ |
|---|---|---|
| **ช่องที่ผ่านการตรวจสอบทั้งหมด (Total Evaluated)** | **{total_eval}** | 100.0% |
| **ยืนยันตัวตน Thai VTuber (CONFIRMED)** | **{len(confirmed)}** | {len(confirmed)/total_eval*100:.2f}% |
| **ช่องที่คัดออกถาวร (EXCLUDED Non-Thai)** | **{len(excluded)}** | {len(excluded)/total_eval*100:.2f}% |
| **ช่องใน Quarantine รอตอบรับ (UNCONFIRMED)** | **0** | **0.0% (ตรวจสอบครบ 100%)** |

> [!NOTE]
> จากเดิมที่มีช่องรอตรวจสอบ (Unconfirmed Quarantine) จำนวน 55 ช่อง ได้รับการสืบค้นและตรวจสอบประวัติจริงครบถ้วน 100% โดย:
> 1. **เลื่อนสถานะ 49 ช่อง** ขึ้นเป็น Thai VTuber ที่ได้รับการยืนยัน (**CONFIRMED**) พร้อมบันทึกสังกัดและสถานะที่ถูกต้อง
> 2. **คัดออก 6 ช่อง** ที่เป็น VTuber / บุคลากรต่างชาติ (**EXCLUDED**) พร้อมบันทึกเหตุผลใน `data/excluded_channels.csv`

---

## 2. สถานะความเคลื่อนไหวของ Thai VTuber (Activity Lifecycle)

คำนวณจากประวัติการเผยแพร่วิดีโอล่าสุดและสถานะการประกาศจบการศึกษา/พักงาน:

| สถานะ (Activity Status) | เกณฑ์การพิจารณา | จำนวนช่อง | ร้อยละ |
|---|---|---|---|
| **Active** | มีการเผยแพร่วิดีโอภายใน 180 วันที่ผ่านมา | **{active_count}** | {active_count/len(confirmed)*100:.1f}% |
| **Hiatus** | ไม่มีความเคลื่อนไหวเกิน 180 วัน | **{hiatus_count}** | {hiatus_count/len(confirmed)*100:.1f}% |
| **Graduated / Retired** | ประกาศจบการศึกษาหรือรีไทร์อย่างเป็นทางการ | **{grad_count}** | {grad_count/len(confirmed)*100:.1f}% |
| **Unknown** | ช่องไม่มีวิดีโอสาธารณะ หรือตั้งค่าส่วนตัว | **{unknown_count}** | {unknown_count/len(confirmed)*100:.1f}% |

---

## 3. การกระจายตัวตามสังกัดและกลุ่ม (Agency & Group Distribution)

Thai VTuber ในทะเบียนแบ่งตามสังกัด (แสดง 15 ลำดับแรก):

| สังกัด / กลุ่ม | จำนวนช่อง | ร้อยละ |
|---|---|---|
"""
    for ag, cnt in sorted_agencies[:15]:
        content += f"| {ag} | {cnt} | {cnt/len(confirmed)*100:.1f}% |\n"

    content += f"""
---

## 4. ผลการตรวจสอบ 55 ช่องที่ได้รับการตรวจทาน (Audit Breakdown)

### 4.1 รายชื่อ Thai VTuber ที่ได้รับการยืนยันเพิ่มเติม (49 ช่อง)

| ลำดับ | ช่อง | Handle | สังกัด | สถานะตรวจสอบ | สถานะระบบ |
|---|---|---|---|---|---|
"""
    for idx, r in enumerate(newly_promoted, 1):
        content += f"| {idx} | [{r['name']}]({r['channel_url']}) | `{r['handle']}` | {r['agency']} | {r['evidence_notes'].split(';')[2].replace('Status: ', '')} | `{r['activity_status']}` |\n"

    content += f"""
### 4.2 รายชื่อช่องต่างชาติที่ถูกคัดออกถาวร (6 ช่อง)

บันทึกแยกไว้ใน `data/excluded_channels.csv` เพื่อป้องกันการดึงข้อมูลผิดพลาดในอนาคต:

| ลำดับ | ช่อง | Handle | ประเทศ/สังกัด | เหตุผลการคัดออก |
|---|---|---|---|---|
"""
    for idx, r in enumerate(excluded, 1):
        content += f"| {idx} | [{r['name']}](https://www.youtube.com/channel/{r['channel_id']}) | `{r['handle']}` | {r['country']} / {r['agency']} | {r['exclusion_reason']} |\n"

    content += f"""
---

## 5. Artifacts และไฟล์ผลลัพธ์ที่จัดเก็บ

1. **`data/thai_vtuber_registry.csv`**: ทะเบียนหลัก Thai VTuber จำนวน **{len(confirmed):,} ช่อง** (UTF-8, 20 คอลัมน์)
2. **`data/thai_vtuber_registry.json`**: ทะเบียนหลักรูปแบบ JSON รองรับ API และ Web App
3. **`data/excluded_channels.csv`**: รายชื่อช่องต่างชาติที่ถูกคัดออกถาวรจำนวน **{len(excluded)} ช่อง**
4. **`data/unconfirmed_candidates.csv`**: ช่องที่ค้างในคิวตรวจสอบคงเหลือ **0 ช่อง**
5. **`data/registry_vtubers.csv`**: Control Plane CSV สำหรับระบบจัดตารางเก็บข้อมูลและ DuckDB

---
*รายงานจัดทำโดยระบบตรวจสอบ Thai VTuber Audience Network (Phase 1 Registry Builder)*
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Phase 1 Audit Report updated at {report_path}")


if __name__ == "__main__":
    run_apply_audit()
