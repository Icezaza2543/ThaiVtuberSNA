"""Generic HTTP fetch utilities for the creator-link pipeline.

No dependency on registry/discovery/. Uses stdlib urllib for simple fetches,
and wraps Playwright's BrowserSession for browser-driven fetches.

Usage:
    html = fetch_html("https://example.com")
    html = await fetch_with_browser("https://x.com/someone", profile_dir=Path("profiles/my"))
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 15.0
MAX_BYTES = 2_000_000  # 2 MB cap


# ---------------------------------------------------------------------------
# Simple HTTP (no JS)
# ---------------------------------------------------------------------------

def fetch_html(url: str, *, timeout: float = DEFAULT_TIMEOUT, user_agent: str = DEFAULT_UA) -> Optional[str]:
    """
    Fetch a URL with stdlib urllib and return decoded HTML, or None on error.

    Use for pages that do not require JavaScript execution (YouTube About,
    static Linktree pages, etc.).
    """
    try:
        req = Request(url, headers={"User-Agent": user_agent})
        with urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()
            body = resp.read(MAX_BYTES)
            return body.decode(charset, errors="replace")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Browser-driven fetch (Playwright)
# ---------------------------------------------------------------------------

class BrowserNotAvailableError(RuntimeError):
    """Raised when Playwright is required but not installed."""


def _check_playwright():
    try:
        from playwright.async_api import async_playwright
        return async_playwright
    except ImportError as exc:
        raise BrowserNotAvailableError(
            'Playwright not installed. Run: pip install -e ".[discovery]" && playwright install chromium'
        ) from exc


async def fetch_with_browser(
    url: str,
    *,
    headless: bool = True,
    profile_dir: Optional[Path] = None,
    timeout: float = 20.0,
    wait_until: str = "domcontentloaded",
) -> Optional[str]:
    """
    Fetch a URL using a Playwright Chromium browser and return page HTML.

    Supports persistent profile (for logged-in sessions) via profile_dir.
    Returns None on navigation error or login-wall detection.

    Login wall detection: if final URL contains /login, /i/flow/login, etc.,
    returns None and the caller should record status='login_blocked'.
    """
    async_playwright = _check_playwright()

    user_agent = DEFAULT_UA
    viewport = {"width": 1280, "height": 800}

    async with async_playwright() as p:
        if profile_dir:
            profile_dir.mkdir(parents=True, exist_ok=True)
            ctx = await p.chromium.launch_persistent_context(
                str(profile_dir),
                headless=headless,
                user_agent=user_agent,
                viewport=viewport,
            )
            page = await ctx.new_page()
        else:
            browser = await p.chromium.launch(headless=headless)
            ctx = await browser.new_context(user_agent=user_agent, viewport=viewport)
            page = await ctx.new_page()

        try:
            resp = await page.goto(url, timeout=int(timeout * 1000), wait_until=wait_until)
            if resp is None:
                return None

            final_url = page.url
            if _is_login_wall(final_url):
                return None  # caller records login_blocked

            return await page.content()
        except Exception:
            return None
        finally:
            await ctx.close()


def _is_login_wall(url: str) -> bool:
    """Detect common login/auth redirect patterns."""
    lower = url.lower()
    login_patterns = (
        "/login",
        "/i/flow/login",
        "/accounts/login",
        "/auth/",
        "?next=",
        "signup",
    )
    return any(p in lower for p in login_patterns)


# ---------------------------------------------------------------------------
# Sync wrapper (for non-async callers)
# ---------------------------------------------------------------------------

def fetch_with_browser_sync(
    url: str,
    *,
    headless: bool = True,
    profile_dir: Optional[Path] = None,
    timeout: float = 20.0,
) -> Optional[str]:
    """Synchronous wrapper around fetch_with_browser."""
    return asyncio.run(
        fetch_with_browser(url, headless=headless, profile_dir=profile_dir, timeout=timeout)
    )
