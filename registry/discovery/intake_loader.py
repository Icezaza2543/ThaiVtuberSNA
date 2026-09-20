"""Load un-ingested historical discovery queues from intake/ into DiscoveryBatch objects."""

import json
from pathlib import Path
import re
from typing import Dict, List, Optional, Set

from ..store import ROOT
from .models import DiscoveryBatch, DiscoveryLead
from .normalize import extract_handle_from_url, infer_platform, normalize_url


def load_intake_batches(
    intake_dir: Path = ROOT / "intake",
    max_records: int = 1500,
    platforms: Optional[List[str]] = None,
) -> List[DiscoveryBatch]:
    """
    Parse historical directory, crosslink, and hub files from intake/ directory.
    Emits DiscoveryBatches with method='official_crosslink' or 'crosslink_crawl',
    retaining exact source_url, observed_at, and metadata.
    """
    batches: List[DiscoveryBatch] = []
    seen_urls: Set[str] = set()
    target_plats = set(platforms) if platforms else None

    # 1. Extra Directory Links (HoloList, Bācharu, Thai directory listings)
    if not target_plats or "twitch" in target_plats:
        extra_dir_file = intake_dir / "2026-09-13-extra-directory-links.jsonl"
        if extra_dir_file.exists():
            leads = []
            with open(extra_dir_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        raw_source = data.get("source_url", "")
                        observed_at = data.get("observed_at") or "2026-09-13T08:55:00+00:00"
                        creator_name = data.get("name") or ""
                        for raw_tw in data.get("twitch_urls", []):
                            platform = infer_platform(raw_tw)
                            if platform != "twitch":
                                continue
                            normalized = normalize_url("twitch", raw_tw)
                            if normalized in seen_urls:
                                continue
                            seen_urls.add(normalized)
                            handle = extract_handle_from_url("twitch", normalized)
                            if not handle:
                                continue
                            source_url = raw_source if (raw_source and raw_source.startswith("https://")) else normalized
                            leads.append(
                                DiscoveryLead(
                                    platform="twitch",
                                    name=creator_name or handle or "",
                                    url=normalized,
                                    handle=handle,
                                    source_url=source_url,
                                    query="directory_intake",
                                    method="crosslink_crawl",
                                    observed_at=observed_at,
                                    source_kind="secondary_source",
                                    metadata={"origin": "intake_extra_directories", "directory_name": creator_name},
                                )
                            )
                            if len(leads) >= max_records:
                                break
                    except Exception:
                        continue
                    if len(leads) >= max_records:
                        break

            if leads:
                batches.append(
                    DiscoveryBatch(
                        platform="twitch",
                        query="directory_intake",
                        method="crosslink_crawl",
                        source_url=leads[0].source_url if leads else "",
                        status="completed",
                        leads=leads,
                        pages_seen=1,
                        records_seen=len(leads),
                    )
                )

    # 2. YouTube Owner Crosslinks (TikTok and creator links)
    for yt_file_name in ("2026-09-13-youtube-owner-crosslinks.jsonl", "2026-09-13-youtube-owner-crosslinks-02.jsonl"):
        yt_owner_file = intake_dir / yt_file_name
        if not yt_owner_file.exists():
            continue
        leads_by_plat: Dict[str, List[DiscoveryLead]] = {}
        with open(yt_owner_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    raw_source = data.get("source_url", "")
                    observed_at = data.get("observed_at") or "2026-09-13T06:20:00+00:00"
                    creator_name = data.get("name") or data.get("current_name") or ""

                    all_raw = list(data.get("tiktok_urls", [])) + list(data.get("creator_links", []))
                    for raw_u in all_raw:
                        platform = infer_platform(raw_u)
                        if not platform or platform == "website":
                            continue
                        if target_plats and platform not in target_plats:
                            continue
                        try:
                            normalized = normalize_url(platform, raw_u)
                        except Exception:
                            continue
                        if normalized in seen_urls:
                            continue
                        seen_urls.add(normalized)
                        handle = extract_handle_from_url(platform, normalized)
                        if platform != "youtube" and not handle:
                            continue
                        source_url = raw_source if (raw_source and raw_source.startswith("https://")) else normalized
                        lead = DiscoveryLead(
                            platform=platform,
                            name=creator_name or handle or "",
                            url=normalized,
                            handle=handle,
                            source_url=source_url,
                            query="owner_crosslinks_intake",
                            method="official_crosslink",
                            observed_at=observed_at,
                            source_kind="secondary_source",
                            metadata={"origin": yt_file_name, "parent_creator_name": creator_name},
                        )
                        if platform not in leads_by_plat:
                            leads_by_plat[platform] = []
                        leads_by_plat[platform].append(lead)
                        if sum(len(v) for v in leads_by_plat.values()) >= max_records:
                            break
                except Exception:
                    continue
                if sum(len(v) for v in leads_by_plat.values()) >= max_records:
                    break

        for plat, p_leads in leads_by_plat.items():
            batches.append(
                DiscoveryBatch(
                    platform=plat,
                    query="owner_crosslinks_intake",
                    method="official_crosslink",
                    source_url=p_leads[0].source_url if p_leads else "",
                    status="completed",
                    leads=p_leads,
                    pages_seen=1,
                    records_seen=len(p_leads),
                )
            )

    # 3. Consolidated X Profile Links (Official outbound platform links on Thai VTuber X accounts)
    x_profile_file = intake_dir / "consolidated" / "x-profile-links-2026-09-16.jsonl"
    if x_profile_file.exists():
        x_leads_by_plat: Dict[str, List[DiscoveryLead]] = {}
        with open(x_profile_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    raw_source = data.get("x_url") or data.get("youtube_url") or ""
                    observed_at = data.get("observed_at") or "2026-09-16T08:53:00+00:00"
                    creator_name = data.get("youtube_name") or ""
                    for item in data.get("platform_links", []):
                        u = item.get("url")
                        platform = item.get("platform") or infer_platform(u)
                        if not platform or platform in ("website", "linktree", "litlink", "carrd"):
                            continue
                        if target_plats and platform not in target_plats:
                            continue
                        if platform == "youtube" and ("/watch?" in u or "/live/" in u):
                            continue
                        try:
                            normalized = normalize_url(platform, u)
                        except Exception:
                            continue
                        if normalized in seen_urls:
                            continue
                        seen_urls.add(normalized)
                        handle = extract_handle_from_url(platform, normalized)
                        platform_id = None
                        id_namespace = None
                        if platform == "youtube":
                            m_cid = re.search(r'/channel/(UC[A-Za-z0-9_-]{22})', normalized)
                            if m_cid:
                                platform_id = m_cid.group(1)
                                id_namespace = "channel_id"
                        elif not handle:
                            continue
                        source_url = raw_source if (raw_source and raw_source.startswith("https://")) else normalized
                        lead = DiscoveryLead(
                            platform=platform,
                            name=item.get("handle") or creator_name or handle or "",
                            url=normalized,
                            handle=handle,
                            platform_id=platform_id,
                            id_namespace=id_namespace,
                            source_url=source_url,
                            query="x_profile_outbound_intake",
                            method="official_crosslink",
                            observed_at=observed_at,
                            source_kind="official_profile",
                            metadata={"origin": "x-profile-links-2026-09-16.jsonl", "x_handle": data.get("x_handle")},
                        )
                        if platform not in x_leads_by_plat:
                            x_leads_by_plat[platform] = []
                        x_leads_by_plat[platform].append(lead)
                        if sum(len(v) for v in x_leads_by_plat.values()) >= max_records:
                            break
                except Exception:
                    continue
                if sum(len(v) for v in x_leads_by_plat.values()) >= max_records:
                    break

        for plat, p_leads in x_leads_by_plat.items():
            batches.append(
                DiscoveryBatch(
                    platform=plat,
                    query="x_profile_outbound_intake",
                    method="official_crosslink",
                    source_url=p_leads[0].source_url if p_leads else "",
                    status="completed",
                    leads=p_leads,
                    pages_seen=1,
                    records_seen=len(p_leads),
                )
            )

    # 4. Consolidated Creator Hub Links (Hub crosslinks from Linktree, Carrd, lit.link)
    hub_file = intake_dir / "consolidated" / "creator-platform-links-2026-09-16.jsonl"
    if hub_file.exists():
        hub_leads_by_plat: Dict[str, List[DiscoveryLead]] = {}
        with open(hub_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    raw_source = data.get("hub_url") or data.get("source_url") or data.get("youtube_url") or ""
                    observed_at = data.get("observed_at") or "2026-09-16T08:53:00+00:00"
                    creator_name = data.get("youtube_name") or ""
                    for item in data.get("platform_links", []):
                        u = item.get("url")
                        platform = item.get("platform") or infer_platform(u)
                        if not platform or platform in ("website", "linktree", "litlink", "carrd"):
                            continue
                        if target_plats and platform not in target_plats:
                            continue
                        if platform == "youtube" and ("/watch?" in u or "/live/" in u):
                            continue
                        try:
                            normalized = normalize_url(platform, u)
                        except Exception:
                            continue
                        if normalized in seen_urls:
                            continue
                        seen_urls.add(normalized)
                        handle = extract_handle_from_url(platform, normalized)
                        if platform != "youtube" and not handle:
                            continue
                        source_url = raw_source if (raw_source and raw_source.startswith("https://")) else normalized
                        lead = DiscoveryLead(
                            platform=platform,
                            name=item.get("handle") or creator_name or handle or "",
                            url=normalized,
                            handle=handle,
                            source_url=source_url,
                            query="creator_hub_outbound_intake",
                            method="crosslink_crawl",
                            observed_at=observed_at,
                            source_kind="secondary_source",
                            metadata={"origin": "creator-platform-links-2026-09-16.jsonl", "hub_url": source_url},
                        )
                        if platform not in hub_leads_by_plat:
                            hub_leads_by_plat[platform] = []
                        hub_leads_by_plat[platform].append(lead)
                        if sum(len(v) for v in hub_leads_by_plat.values()) >= max_records:
                            break
                except Exception:
                    continue
                if sum(len(v) for v in hub_leads_by_plat.values()) >= max_records:
                    break

        for plat, p_leads in hub_leads_by_plat.items():
            batches.append(
                DiscoveryBatch(
                    platform=plat,
                    query="creator_hub_outbound_intake",
                    method="crosslink_crawl",
                    source_url=p_leads[0].source_url if p_leads else "",
                    status="completed",
                    leads=p_leads,
                    pages_seen=1,
                    records_seen=len(p_leads),
                )
            )

    # 5. TikTok Public Profiles
    if not target_plats or "tiktok" in target_plats:
        tk_files = sorted(intake_dir.glob("2026-09-13-tiktok-public-profiles*.jsonl"))
        tk_leads: List[DiscoveryLead] = []
        for tk_file in tk_files:
            with open(tk_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        u = data.get("url")
                        if not u:
                            continue
                        try:
                            normalized = normalize_url("tiktok", u)
                        except Exception:
                            continue
                        if normalized in seen_urls:
                            continue
                        seen_urls.add(normalized)
                        handle = extract_handle_from_url("tiktok", normalized)
                        if not handle:
                            continue
                        pid = str(data.get("platform_id")) if (data.get("status") == "resolved" and data.get("platform_id")) else None
                        ns = "web_user_id" if pid else None
                        raw_src = data.get("source_url") or normalized
                        src = raw_src if (raw_src and raw_src.startswith("https://")) else normalized
                        obs = data.get("observed_at") or "2026-09-13T06:15:00+00:00"
                        lead = DiscoveryLead(
                            platform="tiktok",
                            name=data.get("name") or handle,
                            url=normalized,
                            handle=handle,
                            platform_id=pid,
                            id_namespace=ns,
                            source_url=src,
                            query="tiktok_public_profiles_intake",
                            method="crosslink_crawl",
                            observed_at=obs,
                            source_kind="official_profile" if data.get("public_profile") else "secondary_source",
                            metadata={"origin": tk_file.name, "bio": data.get("bio")},
                        )
                        tk_leads.append(lead)
                        if len(tk_leads) >= max_records:
                            break
                    except Exception:
                        continue
            if len(tk_leads) >= max_records:
                break
        if tk_leads:
            batches.append(
                DiscoveryBatch(
                    platform="tiktok",
                    query="tiktok_public_profiles_intake",
                    method="crosslink_crawl",
                    source_url=tk_leads[0].source_url if tk_leads else "",
                    status="completed",
                    leads=tk_leads,
                    pages_seen=1,
                    records_seen=len(tk_leads),
                )
            )

    # 6. Twitch Public Profiles
    if not target_plats or "twitch" in target_plats:
        tw_files = sorted(intake_dir.glob("2026-09-13-twitch-public-profiles*.jsonl"))
        tw_leads: List[DiscoveryLead] = []
        for tw_file in tw_files:
            with open(tw_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        u = data.get("url")
                        if not u:
                            continue
                        try:
                            normalized = normalize_url("twitch", u)
                        except Exception:
                            continue
                        if normalized in seen_urls:
                            continue
                        seen_urls.add(normalized)
                        handle = extract_handle_from_url("twitch", normalized)
                        if not handle:
                            continue
                        pid = str(data.get("platform_id")) if (data.get("status") == "resolved" and data.get("platform_id")) else None
                        ns = "user_id" if pid else None
                        raw_src = data.get("source_url") or normalized
                        src = raw_src if (raw_src and raw_src.startswith("https://")) else normalized
                        obs = data.get("observed_at") or "2026-09-13T08:51:00+00:00"
                        lead = DiscoveryLead(
                            platform="twitch",
                            name=data.get("name") or handle,
                            url=normalized,
                            handle=handle,
                            platform_id=pid,
                            id_namespace=ns,
                            source_url=src,
                            query="twitch_public_profiles_intake",
                            method="crosslink_crawl",
                            observed_at=obs,
                            source_kind="official_profile",
                            metadata={"origin": tw_file.name, "bio": data.get("bio")},
                        )
                        tw_leads.append(lead)
                        if len(tw_leads) >= max_records:
                            break
                    except Exception:
                        continue
            if len(tw_leads) >= max_records:
                break
        if tw_leads:
            batches.append(
                DiscoveryBatch(
                    platform="twitch",
                    query="twitch_public_profiles_intake",
                    method="crosslink_crawl",
                    source_url=tw_leads[0].source_url if tw_leads else "",
                    status="completed",
                    leads=tw_leads,
                    pages_seen=1,
                    records_seen=len(tw_leads),
                )
            )

    # 7. Creator Hub Crosslinks (beacons.ai, easydonate, etc.)
    ch_file = intake_dir / "2026-09-13-creator-hub-crosslinks.jsonl"
    if ch_file.exists():
        ch_leads_by_plat: Dict[str, List[DiscoveryLead]] = {}
        with open(ch_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    raw_source = data.get("source_url") or ""
                    observed_at = data.get("observed_at") or "2026-09-13T06:20:00+00:00"
                    yt_sources = data.get("youtube_sources") or []
                    creator_name = yt_sources[0].get("name") if yt_sources else ""
                    for raw_u in data.get("tiktok_urls", []):
                        platform = infer_platform(raw_u)
                        if not platform or platform != "tiktok":
                            continue
                        if target_plats and platform not in target_plats:
                            continue
                        try:
                            normalized = normalize_url(platform, raw_u)
                        except Exception:
                            continue
                        if normalized in seen_urls:
                            continue
                        seen_urls.add(normalized)
                        handle = extract_handle_from_url(platform, normalized)
                        if not handle:
                            continue
                        src = raw_source if (raw_source and raw_source.startswith("https://")) else normalized
                        lead = DiscoveryLead(
                            platform=platform,
                            name=creator_name or handle,
                            url=normalized,
                            handle=handle,
                            source_url=src,
                            query="creator_hub_crosslinks_intake",
                            method="crosslink_crawl",
                            observed_at=observed_at,
                            source_kind="secondary_source",
                            metadata={"origin": "2026-09-13-creator-hub-crosslinks.jsonl", "hub_url": raw_source},
                        )
                        if platform not in ch_leads_by_plat:
                            ch_leads_by_plat[platform] = []
                        ch_leads_by_plat[platform].append(lead)
                        if sum(len(v) for v in ch_leads_by_plat.values()) >= max_records:
                            break
                except Exception:
                    continue
                if sum(len(v) for v in ch_leads_by_plat.values()) >= max_records:
                    break

        for plat, p_leads in ch_leads_by_plat.items():
            batches.append(
                DiscoveryBatch(
                    platform=plat,
                    query="creator_hub_crosslinks_intake",
                    method="crosslink_crawl",
                    source_url=p_leads[0].source_url if p_leads else "",
                    status="completed",
                    leads=p_leads,
                    pages_seen=1,
                    records_seen=len(p_leads),
                )
            )


    # 8. Hub VTuber Thai full-directory first-seen observations
    raw_dir = intake_dir / "raw"
    vtuberthai_files = (
        sorted(raw_dir.glob("*-vtuberthai-directory-new.jsonl"))
        if raw_dir.is_dir()
        else []
    )
    vtuberthai_by_plat: Dict[str, List[DiscoveryLead]] = {}
    vtuberthai_total = 0
    for source_file in vtuberthai_files:
        with open(source_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    platform = data.get("platform")
                    raw_url = data.get("url")
                    if not platform or not raw_url:
                        continue
                    if target_plats and platform not in target_plats:
                        continue
                    try:
                        normalized = normalize_url(platform, raw_url)
                    except Exception:
                        continue
                    if normalized in seen_urls:
                        continue
                    seen_urls.add(normalized)
                    handle = data.get("handle") or extract_handle_from_url(platform, normalized)
                    platform_id = data.get("platform_id")
                    id_namespace = data.get("id_namespace")
                    if platform != "youtube" and not handle and not platform_id:
                        continue
                    raw_source = data.get("source_url") or normalized
                    source_url = (
                        raw_source
                        if isinstance(raw_source, str) and raw_source.startswith("https://")
                        else normalized
                    )
                    lead = DiscoveryLead(
                        platform=platform,
                        name=data.get("name") or handle or normalized,
                        url=normalized,
                        handle=handle,
                        platform_id=str(platform_id) if platform_id else None,
                        id_namespace=id_namespace,
                        source_url=source_url,
                        query=data.get("query") or "vtuberthai_directory_intake",
                        method=data.get("method") or "directory_crawl",
                        observed_at=data.get("observed_at") or "",
                        source_kind=data.get("source_kind") or "secondary_source",
                        metadata={
                            "origin": source_file.name,
                            "directory": "Hub VTuber Thai",
                        },
                    )
                    vtuberthai_by_plat.setdefault(platform, []).append(lead)
                    vtuberthai_total += 1
                    if vtuberthai_total >= max_records:
                        break
                except Exception:
                    continue
        if vtuberthai_total >= max_records:
            break

    for plat, p_leads in vtuberthai_by_plat.items():
        batches.append(
            DiscoveryBatch(
                platform=plat,
                query="vtuberthai_directory_intake",
                method="directory_crawl",
                source_url=p_leads[0].source_url if p_leads else "",
                status="completed",
                leads=p_leads,
                pages_seen=1,
                records_seen=len(p_leads),
            )
        )

    return batches
