"""Instagram public discovery adapter."""

import re
from typing import Any, List
from urllib.parse import quote_plus

from ..models import DiscoveryBatch, DiscoveryLead, DiscoveryLimits
from .base import PlatformAdapter, now_iso

RESERVED_IG_PATHS = {
    "explore",
    "accounts",
    "legal",
    "direct",
    "reels",
    "stories",
    "about",
    "developer",
    "privacy",
    "terms",
}


class InstagramAdapter(PlatformAdapter):
    platform = "instagram"

    def detect_empty_state(self, html: str) -> bool:
        lower = html.lower()
        return (
            "no results found" in lower
            or "no users found" in lower
            or "no posts yet" in lower
            or "ไม่พบผลการค้นหา" in lower
            or "ไม่พบผลลัพธ์" in lower
        )

    async def discover(self, page: Any, query: str, limits: DiscoveryLimits) -> DiscoveryBatch:
        clean_tag = re.sub(r'[^A-Za-z0-9_]', '', query) or "vtuber"
        search_url = f"https://www.instagram.com/explore/tags/{quote_plus(clean_tag)}/"
        observed_at = now_iso()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=int(limits.timeout * 1000))
            if hasattr(page, "wait_for_selector"):
                try:
                    await page.wait_for_selector(
                        'a[href^="/"], article',
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

        if (
            "loginform" in initial_html.lower()
            or "log in to see photos" in initial_html.lower()
            or self.detect_login_required(initial_html)
        ):
            return self.create_batch(query=query, source_url=search_url, status="login_required")

        def extract_leads(content: str) -> List[DiscoveryLead]:
            res: List[DiscoveryLead] = []
            seen = set()
            matches = re.finditer(
                r'href=["\'](?:https?://(?:www\.)?instagram\.com)?/([A-Za-z0-9_.]{3,30})/?["\']([^>]*>([^<]+))?',
                content,
            )
            for m in matches:
                username = m.group(1).rstrip("/")
                if username.lower() in RESERVED_IG_PATHS:
                    continue
                name = (m.group(3) or username).strip()
                url = f"https://www.instagram.com/{username}"
                if url in seen:
                    continue
                seen.add(url)
                res.append(
                    DiscoveryLead(
                        platform=self.platform,
                        name=name,
                        url=url,
                        handle=username,
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
