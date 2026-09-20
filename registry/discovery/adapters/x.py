"""X (Twitter) public discovery adapter."""

import re
from typing import Any, List
from urllib.parse import quote_plus

from ..models import DiscoveryBatch, DiscoveryLead, DiscoveryLimits
from .base import PlatformAdapter, now_iso

RESERVED_X_PATHS = {
    "home",
    "explore",
    "notifications",
    "messages",
    "search",
    "settings",
    "tos",
    "privacy",
    "login",
    "signup",
    "i",
}


class XAdapter(PlatformAdapter):
    platform = "x"

    def detect_empty_state(self, html: str) -> bool:
        lower = html.lower()
        return (
            "no results for" in lower
            or "the term you entered did not bring up any results" in lower
            or "ไม่พบผลลัพธ์สำหรับ" in lower
        )

    async def discover(self, page: Any, query: str, limits: DiscoveryLimits) -> DiscoveryBatch:
        search_url = f"https://x.com/search?q={quote_plus(query)}&f=user"
        observed_at = now_iso()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=int(limits.timeout * 1000))
            if hasattr(page, "wait_for_selector"):
                try:
                    await page.wait_for_selector(
                        '[data-testid="UserCell"], [data-testid="emptyState"]',
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

        lower = initial_html.lower()
        if "rate limit exceeded" in lower or "too many requests" in lower:
            return self.create_batch(query=query, source_url=search_url, status="rate_limited")

        if (
            "sign in to x" in lower
            or "log in to x" in lower
            or "don't miss what's happening" in lower
            or self.detect_login_required(initial_html)
        ):
            return self.create_batch(query=query, source_url=search_url, status="login_required")

        def extract_leads(content: str) -> List[DiscoveryLead]:
            res: List[DiscoveryLead] = []
            seen = set()
            matches = re.finditer(
                r'href=["\'](?:https?://(?:www\.)?(?:x|twitter)\.com)?/([A-Za-z0-9_]{1,50})/?["\']([^>]*>([^<]+))?',
                content,
            )
            for m in matches:
                handle = m.group(1).rstrip("/")
                if handle.lower() in RESERVED_X_PATHS:
                    continue
                name = (m.group(3) or handle).strip()
                url = f"https://x.com/{handle}"
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
