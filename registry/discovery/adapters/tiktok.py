"""TikTok public discovery adapter."""

import re
from typing import Any, List
from urllib.parse import quote_plus

from ..models import DiscoveryBatch, DiscoveryLead, DiscoveryLimits
from .base import PlatformAdapter, now_iso


class TikTokAdapter(PlatformAdapter):
    platform = "tiktok"

    def detect_empty_state(self, html: str) -> bool:
        lower = html.lower()
        return (
            "no results" in lower
            or "couldn't find" in lower
            or "try searching" in lower
            or "ไม่พบผลลัพธ์" in lower
        )

    async def discover(self, page: Any, query: str, limits: DiscoveryLimits) -> DiscoveryBatch:
        search_url = f"https://www.tiktok.com/search/user?q={quote_plus(query)}"
        observed_at = now_iso()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=int(limits.timeout * 1000))
            if hasattr(page, "wait_for_selector"):
                try:
                    await page.wait_for_selector(
                        '[data-e2e="search-user-container"], a[href*="/@"]',
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

        if self.detect_captcha(initial_html):
            return self.create_batch(query=query, source_url=search_url, status="captcha")

        if self.detect_login_required(initial_html):
            return self.create_batch(query=query, source_url=search_url, status="login_required")

        def extract_leads(content: str) -> List[DiscoveryLead]:
            res: List[DiscoveryLead] = []
            seen = set()
            matches = re.finditer(
                r'href=["\'](?:https?://(?:www\.)?tiktok\.com)?/(@([A-Za-z0-9_.-]+))["\']([^>]*>([^<]+))?',
                content,
            )
            for m in matches:
                handle = m.group(2)
                name = (m.group(4) or handle).strip()
                url = f"https://www.tiktok.com/@{handle}"
                if url in seen:
                    continue
                seen.add(url)
                res.append(
                    DiscoveryLead(
                        platform=self.platform,
                        name=name,
                        url=url,
                        handle=handle,
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
