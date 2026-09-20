"""Base class and common helpers for platform discovery adapters."""

from datetime import datetime, timezone
import re
from typing import Any, List, Optional
from urllib.parse import quote_plus

from ..models import DiscoveryBatch, DiscoveryLead, DiscoveryLimits
from ..normalize import normalize_url


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PlatformAdapter:
    """Base interface that every platform discovery adapter implements."""

    platform: str = ""

    async def discover(self, page_or_context: Any, query: str, limits: DiscoveryLimits) -> DiscoveryBatch:
        """
        Execute public search on the platform for the given query.
        Returns a DiscoveryBatch containing leads and status/stop-reason.
        """
        raise NotImplementedError

    def create_batch(
        self,
        query: str = "",
        method: str = "playwright_search",
        source_url: str = "",
        status: str = "completed",
        leads: Optional[List[DiscoveryLead]] = None,
        pages_seen: int = 0,
        records_seen: int = 0,
        error_message: Optional[str] = None,
    ) -> DiscoveryBatch:
        return DiscoveryBatch(
            platform=self.platform,
            query=query,
            method=method,
            source_url=source_url,
            status=status,
            leads=leads or [],
            pages_seen=pages_seen,
            records_seen=records_seen,
            error_message=error_message,
        )

    def check_page_status(
        self,
        html: str,
        has_results: bool,
        has_empty_state: bool,
    ) -> str:
        """
        Determine page state:
        - 'captcha' if captcha detected
        - 'login_required' if login wall detected
        - 'completed' if results found OR official empty state confirmed
        - 'selector_changed' if page loaded normally but neither results nor empty state found
        """
        if has_results:
            return "completed"
        if self.detect_captcha(html):
            return "captcha"
        if self.detect_login_required(html):
            return "login_required"
        if has_empty_state:
            return "completed"
        return "selector_changed"

    async def scroll_page_until_stabilized(
        self,
        page: Any,
        extract_fn: Any,
        limits: DiscoveryLimits,
    ) -> tuple[List[DiscoveryLead], int, int]:
        """
        Perform bounded scrolling / pagination up to limits.max_pages or limits.max_results.
        Returns (leads, pages_seen, records_seen).
        """
        pages_seen = 0
        all_leads: List[DiscoveryLead] = []
        seen_urls = set()

        for cycle in range(limits.max_pages):
            pages_seen += 1
            html = await page.content() if hasattr(page, "content") else ""
            batch_leads = extract_fn(html)
            for lead in batch_leads:
                if lead.url not in seen_urls:
                    seen_urls.add(lead.url)
                    all_leads.append(lead)

            if len(all_leads) >= limits.max_results:
                break

            if hasattr(page, "evaluate"):
                try:
                    prev_len = len(all_leads)
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    if hasattr(page, "wait_for_timeout"):
                        await page.wait_for_timeout(1000)
                    new_html = await page.content()
                    after_leads = extract_fn(new_html)
                    if len(after_leads) <= prev_len:
                        break
                except Exception:
                    break
            else:
                break

        return all_leads[:limits.max_results], pages_seen, len(all_leads)

    def detect_captcha(self, html: str) -> bool:
        """Common heuristic checks for active CAPTCHA and anti-bot challenge screens."""
        lower = html.lower()
        patterns = [
            "id=\"captcha-form\"",
            "g-recaptcha",
            "recaptcha-anchor",
            "cf-turnstile-wrapper",
            "hcaptcha-box",
            "verify-bar",
            "captcha-verify",
            "verify you are human",
            "verify that you are a human",
            "security check to continue",
            "verification required",
            "waf-challenge",
            "unusual traffic from your computer network",
            "geetest_radar",
        ]
        return any(p in lower for p in patterns)

    def detect_login_required(self, html: str) -> bool:
        """Common heuristic checks for login wall screens."""
        lower = html.lower()
        patterns = [
            "log in to continue",
            "sign in to continue",
            "please log in",
            "login required",
            "must log in",
            "login_popup_cta_element",
            "login-modal",
        ]
        return any(p in lower for p in patterns)

    def detect_empty_state(self, html: str) -> bool:
        """Platform-specific check for official empty search result message. Override in adapters."""
        return False

