"""YouTube discovery adapter."""

import re
from typing import Any, List
from urllib.parse import quote_plus

from ..models import DiscoveryBatch, DiscoveryLead, DiscoveryLimits
from .base import PlatformAdapter, now_iso


class YouTubeAdapter(PlatformAdapter):
    platform = "youtube"

    def detect_empty_state(self, html: str) -> bool:
        lower = html.lower()
        return (
            "no results found" in lower
            or "ไม่พบผลลัพธ์" in lower
            or "try different keywords" in lower
            or "ytd-message-renderer" in lower
        )

    async def discover(self, page: Any, query: str, limits: DiscoveryLimits) -> DiscoveryBatch:
        search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        observed_at = now_iso()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=int(limits.timeout * 1000))
            if hasattr(page, "wait_for_selector"):
                try:
                    await page.wait_for_selector(
                        "ytd-video-renderer, ytd-channel-renderer, ytd-message-renderer",
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

        def extract_leads(content: str) -> List[DiscoveryLead]:
            res: List[DiscoveryLead] = []
            seen_urls = set()

            # Handle-based channels (e.g. /@CreatorName)
            handle_matches = re.finditer(r'href=["\'](/@([A-Za-z0-9_.-]+))["\']([^>]*>([^<]+))?', content)
            for m in handle_matches:
                raw_path = m.group(1)
                handle = m.group(2)
                name = (m.group(4) or handle).strip()
                url = f"https://www.youtube.com{raw_path}"
                if url in seen_urls:
                    continue
                seen_urls.add(url)
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

            # Channel_id-based channels (e.g. /channel/UC...)
            cid_matches = re.finditer(r'href=["\'](/channel/(UC[A-Za-z0-9_-]{22}))["\']([^>]*>([^<]+))?', content)
            for m in cid_matches:
                channel_id = m.group(2)
                name = (m.group(4) or channel_id).strip()
                url = f"https://www.youtube.com/channel/{channel_id}"
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                res.append(
                    DiscoveryLead(
                        platform=self.platform,
                        name=name,
                        url=url,
                        platform_id=channel_id,
                        id_namespace="channel_id",
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
