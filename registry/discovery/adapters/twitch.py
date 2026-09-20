"""Twitch public search discovery adapter."""

import re
from typing import Any, List
from urllib.parse import quote_plus

from ..models import DiscoveryBatch, DiscoveryLead, DiscoveryLimits
from .base import PlatformAdapter, now_iso

RESERVED_TWITCH_PATHS = {
    "directory",
    "downloads",
    "jobs",
    "turbo",
    "p",
    "login",
    "signup",
    "search",
    "settings",
    "videos",
    "moderator",
    "popout",
}


class TwitchAdapter(PlatformAdapter):
    platform = "twitch"

    def detect_empty_state(self, html: str) -> bool:
        lower = html.lower()
        return (
            "could not find" in lower
            or "no channels found" in lower
            or "no results found" in lower
            or "try searching for something else" in lower
            or "ไม่พบผลลัพธ์" in lower
        )

    async def discover(self, page: Any, query: str, limits: DiscoveryLimits) -> DiscoveryBatch:
        search_url = f"https://www.twitch.tv/search?term={quote_plus(query)}&type=channels"
        observed_at = now_iso()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=int(limits.timeout * 1000))
            if hasattr(page, "wait_for_selector"):
                try:
                    await page.wait_for_selector(
                        'div[data-a-target*="search-result"], div[class*="search-result-card"], div[class*="search-results"]',
                        timeout=min(int(limits.timeout * 1000), 8000),
                    )
                except Exception:
                    pass
            if hasattr(page, "wait_for_timeout"):
                await page.wait_for_timeout(1000)
        except Exception as exc:
            return self.create_batch(
                query=query,
                source_url=search_url,
                status="timeout" if "timeout" in str(exc).lower() else "partial",
                error_message=str(exc),
            )

        def extract_leads(content: str) -> List[DiscoveryLead]:
            res: List[DiscoveryLead] = []
            seen = set()

            # Target search result cards in Twitch SPA DOM
            card_matches = re.finditer(
                r'<div[^>]+(?:search-result|search-result-card)[^>]*>[\s\S]*?href=["\'](?:https?://(?:www\.)?twitch\.tv)?/([A-Za-z0-9_]{3,25})["\']',
                content,
            )
            found_card = False
            for m in card_matches:
                found_card = True
                login = m.group(1).lower()
                if login in RESERVED_TWITCH_PATHS:
                    continue
                url = f"https://www.twitch.tv/{login}"
                if url in seen:
                    continue
                seen.add(url)
                res.append(
                    DiscoveryLead(
                        platform=self.platform,
                        name=login,
                        url=url,
                        handle=login,
                        source_url=search_url,
                        query=query,
                        observed_at=observed_at,
                        source_kind="platform_observation",
                    )
                )

            if not found_card:
                # Fallback to main content or mock HTML
                main_match = re.search(r'<main[^>]*>([\s\S]*?)</main>', content)
                search_area = main_match.group(1) if main_match else content
                matches = re.finditer(
                    r'href=["\'](?:https?://(?:www\.)?twitch\.tv)?/([A-Za-z0-9_]{3,25})["\']',
                    search_area,
                )
                for m in matches:
                    login = m.group(1).lower()
                    if login in RESERVED_TWITCH_PATHS:
                        continue
                    url = f"https://www.twitch.tv/{login}"
                    if url in seen:
                        continue
                    seen.add(url)
                    res.append(
                        DiscoveryLead(
                            platform=self.platform,
                            name=login,
                            url=url,
                            handle=login,
                            source_url=search_url,
                            query=query,
                            observed_at=observed_at,
                            source_kind="platform_observation",
                        )
                    )
            return res

        leads, pages_seen, records_seen = await self.scroll_page_until_stabilized(page, extract_leads, limits)
        initial_html = await page.content() if hasattr(page, "content") else ""
        has_results = len(leads) > 0
        has_empty_state = self.detect_empty_state(initial_html)
        status = self.check_page_status(initial_html, has_results=has_results, has_empty_state=has_empty_state)

        return self.create_batch(
            query=query,
            method="playwright_search",
            source_url=search_url,
            status=status,
            leads=leads,
            pages_seen=pages_seen,
            records_seen=records_seen,
        )
