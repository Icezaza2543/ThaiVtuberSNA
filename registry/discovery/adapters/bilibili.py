"""Bilibili UP creator discovery adapter."""

import re
from typing import Any, List
from urllib.parse import quote_plus

from ..models import DiscoveryBatch, DiscoveryLead, DiscoveryLimits
from .base import PlatformAdapter, now_iso


class BilibiliAdapter(PlatformAdapter):
    platform = "bilibili"

    def detect_empty_state(self, html: str) -> bool:
        return (
            "没有找到相关结果" in html
            or "没有找到相关" in html
            or "no results" in html.lower()
        )

    async def discover(self, page: Any, query: str, limits: DiscoveryLimits) -> DiscoveryBatch:
        search_url = f"https://search.bilibili.com/upuser?keyword={quote_plus(query)}"
        observed_at = now_iso()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=int(limits.timeout * 1000))
            if hasattr(page, "wait_for_selector"):
                try:
                    await page.wait_for_selector(
                        'a[href*="space.bilibili.com/"], div.user-list',
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

        if "geetest" in initial_html or "bili-mini-mask" in initial_html or self.detect_captcha(initial_html):
            return self.create_batch(query=query, source_url=search_url, status="captcha")

        def extract_leads(content: str) -> List[DiscoveryLead]:
            res: List[DiscoveryLead] = []
            seen = set()
            matches = re.finditer(r'href=["\'](?:https?:)?//space\.bilibili\.com/(\d+)["\']([^>]*>([^<]+))?', content)
            for m in matches:
                uid = m.group(1)
                name = (m.group(3) or f"Bilibili UP {uid}").strip()
                url = f"https://space.bilibili.com/{uid}"
                if url in seen:
                    continue
                seen.add(url)
                res.append(
                    DiscoveryLead(
                        platform=self.platform,
                        name=name,
                        url=url,
                        platform_id=uid,
                        id_namespace="uid",
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
