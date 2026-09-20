"""GankNow public creator discovery adapter."""

from collections import defaultdict
import re
from typing import Any, Dict, List
from urllib.parse import quote_plus

from ..crosslinks import extract_crosslinks, extract_urls_from_html
from ..models import DiscoveryBatch, DiscoveryLead, DiscoveryLimits
from ..network_safety import is_safe_public_http_url, safe_goto
from .base import PlatformAdapter, now_iso

RESERVED_GANKNOW_PATHS = {
    "search",
    "terms",
    "privacy",
    "explore",
    "about",
    "login",
    "signup",
    "creators",
    "blog",
    "feed",
    "membership",
    "shop",
}


class GankNowAdapter(PlatformAdapter):
    platform = "ganknow"

    def detect_empty_state(self, html: str) -> bool:
        lower = html.lower()
        return (
            "no creators found" in lower
            or "no results found" in lower
            or "0 creators" in lower
            or "try another search" in lower
            or "ไม่พบผลลัพธ์" in lower
        )

    async def discover(self, page: Any, query: str, limits: DiscoveryLimits) -> DiscoveryBatch:
        search_url = f"https://ganknow.com/search?q={quote_plus(query)}"
        observed_at = now_iso()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=int(limits.timeout * 1000))
            if hasattr(page, "wait_for_selector"):
                try:
                    await page.wait_for_selector(
                        'a[href^="/"], div.creator, div.search-result',
                        timeout=min(int(limits.timeout * 1000), 5000),
                    )
                except Exception:
                    pass
        except Exception as exc:
            return self.create_batch(
                query=query,
                source_url=search_url,
                status="timeout" if "timeout" in str(exc).lower() else "partial",
                error_message=str(exc),
            )

        initial_html = await page.content() if hasattr(page, "content") else ""

        def extract_creator_leads(content: str) -> List[DiscoveryLead]:
            res: List[DiscoveryLead] = []
            seen = set()
            matches = re.finditer(
                r'href=["\'](?:https?://(?:www\.)?ganknow\.com)?/([A-Za-z0-9_.-]{3,30})/?["\']([^>]*>([^<]+))?',
                content,
            )
            for m in matches:
                slug = m.group(1).rstrip("/")
                if slug.lower() in RESERVED_GANKNOW_PATHS:
                    continue
                name = (m.group(3) or slug).strip()
                url = f"https://ganknow.com/{slug}"
                if url in seen:
                    continue
                seen.add(url)
                res.append(
                    DiscoveryLead(
                        platform=self.platform,
                        name=name,
                        url=url,
                        handle=slug,
                        source_url=search_url,
                        query=query,
                        observed_at=observed_at,
                        source_kind="platform_observation",
                    )
                )
            return res

        creator_leads, pages_seen, creator_records_seen = await self.scroll_page_until_stabilized(
            page, extract_creator_leads, limits
        )

        has_results = len(creator_leads) > 0
        has_empty_state = self.detect_empty_state(initial_html)
        status = self.check_page_status(initial_html, has_results=has_results, has_empty_state=has_empty_state)

        # Primary search batch
        search_batch = self.create_batch(
            query=query,
            method="playwright_search",
            source_url=search_url,
            status=status,
            leads=creator_leads,
            pages_seen=pages_seen,
            records_seen=creator_records_seen,
        )

        sub_batches: List[DiscoveryBatch] = [search_batch]
        all_collected_leads: List[DiscoveryLead] = list(creator_leads)

        # Bounded 1-hop crosslink crawl from creator profiles (up to 5 profiles)
        max_profiles_to_crawl = min(len(creator_leads), 5)
        for creator in creator_leads[:max_profiles_to_crawl]:
            try:
                if not hasattr(page, "goto"):
                    continue
                await page.goto(
                    creator.url,
                    wait_until="domcontentloaded",
                    timeout=min(int(limits.timeout * 1000), 8000),
                )
                profile_html = await page.content() if hasattr(page, "content") else ""
                raw_profile_urls = extract_urls_from_html(profile_html, max_links=50)
                profile_records_seen = len(raw_profile_urls)

                # 1. Social crosslinks on known creator platforms
                outbound_leads = extract_crosslinks(
                    profile_html,
                    parent_url=creator.url,
                    observed_at=observed_at,
                    max_links=15,
                    allow_websites=False,
                )

                leads_by_plat: Dict[str, List[DiscoveryLead]] = defaultdict(list)
                for cl in outbound_leads:
                    cl.source_url = creator.url
                    cl.query = query
                    cl.method = "crosslink_crawl"
                    cl.source_kind = "secondary_source"
                    cl.metadata["origin"] = "crosslink_crawl"
                    cl.metadata["parent_creator_url"] = creator.url
                    leads_by_plat[cl.platform].append(cl)

                for plat, p_leads in leads_by_plat.items():
                    sub_batches.append(
                        DiscoveryBatch(
                            platform=plat,
                            query=query,
                            method="crosslink_crawl",
                            source_url=creator.url,
                            status="completed",
                            leads=p_leads,
                            pages_seen=1,
                            records_seen=profile_records_seen,
                        )
                    )
                    all_collected_leads.extend(p_leads)

                # 2. Link hubs (Carrd, Linktree, Litlink) -> Hop 2
                link_hubs = [cl for cl in outbound_leads if cl.platform in {"carrd", "linktree", "litlink"}][:2]
                for hub in link_hubs:
                    try:
                        await page.goto(
                            hub.url,
                            wait_until="domcontentloaded",
                            timeout=min(int(limits.timeout * 1000), 6000),
                        )
                        hub_html = await page.content() if hasattr(page, "content") else ""
                        hub_raw_urls = extract_urls_from_html(hub_html, max_links=40)
                        hub_leads = extract_crosslinks(
                            hub_html,
                            parent_url=hub.url,
                            observed_at=observed_at,
                            max_links=10,
                            allow_websites=False,
                        )
                        hub_leads_by_plat: Dict[str, List[DiscoveryLead]] = defaultdict(list)
                        for hl in hub_leads:
                            if hl.platform not in {"carrd", "linktree", "litlink", "website"}:
                                hl.source_url = hub.url
                                hl.query = query
                                hl.method = "crosslink_crawl"
                                hl.source_kind = "secondary_source"
                                hl.metadata["origin"] = "crosslink_crawl"
                                hl.metadata["parent_creator_url"] = creator.url
                                hub_leads_by_plat[hl.platform].append(hl)

                        for h_plat, hl_leads in hub_leads_by_plat.items():
                            sub_batches.append(
                                DiscoveryBatch(
                                    platform=h_plat,
                                    query=query,
                                    method="crosslink_crawl",
                                    source_url=hub.url,
                                    status="completed",
                                    leads=hl_leads,
                                    pages_seen=1,
                                    records_seen=len(hub_raw_urls),
                                )
                            )
                            all_collected_leads.extend(hl_leads)
                    except Exception:
                        pass

                # 3. Personal websites (Hop 2)
                website_candidates = [
                    cl
                    for cl in extract_crosslinks(
                        profile_html,
                        parent_url=creator.url,
                        observed_at=observed_at,
                        max_links=5,
                        allow_websites=True,
                    )
                    if cl.platform == "website"
                ][:2]

                for web_lead in website_candidates:
                    # Guard against SSRF / local network access before recording or navigating
                    if not is_safe_public_http_url(web_lead.url, resolve_dns=True):
                        continue

                    web_lead.source_url = creator.url
                    web_lead.query = query
                    web_lead.method = "crosslink_crawl"
                    web_lead.metadata["parent_creator_url"] = creator.url
                    sub_batches.append(
                        DiscoveryBatch(
                            platform="website",
                            query=query,
                            method="crosslink_crawl",
                            source_url=creator.url,
                            status="completed",
                            leads=[web_lead],
                            pages_seen=1,
                            records_seen=1,
                        )
                    )
                    all_collected_leads.append(web_lead)

                    try:
                        nav_ok = await safe_goto(
                            page,
                            web_lead.url,
                            timeout_ms=min(int(limits.timeout * 1000), 6000),
                        )
                        if not nav_ok:
                            continue

                        site_html = await page.content() if hasattr(page, "content") else ""
                        site_raw_urls = extract_urls_from_html(site_html, max_links=50)
                        site_leads = extract_crosslinks(
                            site_html,
                            parent_url=web_lead.url,
                            observed_at=observed_at,
                            max_links=10,
                            allow_websites=False,
                        )
                        site_leads_by_plat: Dict[str, List[DiscoveryLead]] = defaultdict(list)
                        for sl in site_leads:
                            if sl.platform != "website":
                                sl.source_url = web_lead.url
                                sl.query = query
                                sl.method = "crosslink_crawl"
                                sl.source_kind = "secondary_source"
                                sl.metadata["origin"] = "crosslink_crawl"
                                sl.metadata["parent_creator_url"] = creator.url
                                sl.metadata["intermediate_url"] = web_lead.url
                                site_leads_by_plat[sl.platform].append(sl)

                        for s_plat, sl_leads in site_leads_by_plat.items():
                            sub_batches.append(
                                DiscoveryBatch(
                                    platform=s_plat,
                                    query=query,
                                    method="crosslink_crawl",
                                    source_url=web_lead.url,
                                    status="completed",
                                    leads=sl_leads,
                                    pages_seen=1,
                                    records_seen=len(site_raw_urls),
                                )
                            )
                            all_collected_leads.extend(sl_leads)
                    except Exception:
                        pass
            except Exception:
                pass

        main_return_batch = self.create_batch(
            query=query,
            method="playwright_search",
            source_url=search_url,
            status=status,
            leads=all_collected_leads,
            pages_seen=pages_seen,
            records_seen=creator_records_seen,
        )
        main_return_batch.sub_batches = sub_batches
        return main_return_batch
