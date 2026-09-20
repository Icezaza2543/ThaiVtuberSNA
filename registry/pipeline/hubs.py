"""hubs.py — X profile fetch + Creator hub link extraction.

Two responsibilities:
  1. fetch_x_profile_links(x_url) → hub URLs + direct platform links from X profile
  2. crawl_hub(hub_url)           → all platform links from a creator link hub

Uses:
  - registry/web.py  for HTTP/browser fetch (no discovery/ dependency)
  - registry/urls.py for link extraction and normalization
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from ..urls import (
    extract_handle_from_url,
    extract_platform_links,
    infer_platform,
    is_hub,
    normalize_url,
)
from ..web import fetch_html, fetch_with_browser_sync

# ---------------------------------------------------------------------------
# X profile: extract website field and bio links
# ---------------------------------------------------------------------------

# Patterns that indicate a login wall redirect on X
_X_LOGIN_PATTERNS = re.compile(
    r"(/login|/i/flow/login|accounts/login|/auth/)",
    re.IGNORECASE,
)

# X profile website field is in a <a> with data-testid="UserUrl" or class patterns
# We parse it from raw HTML since X is heavy JS, but the meta tags expose it too
_X_OG_URL_PATTERN = re.compile(
    r'<meta\s+(?:property|name)=["\']og:url["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_X_WEBSITE_PATTERNS = [
    # JSON-LD entities (sometimes present in SSR)
    re.compile(r'"url"\s*:\s*"(https?://(?!twitter\.com|x\.com)[^"]+)"'),
    # Anchor with expanded_url in JSON embedded in HTML
    re.compile(r'"expanded_url"\s*:\s*"(https?://(?!t\.co)[^"]+)"'),
    # t.co link in bio (expanded form)
    re.compile(r'href="(https://t\.co/[A-Za-z0-9]+)"'),
]

# Platforms we want to surface from X bios
_PLATFORM_TARGETS = {
    "youtube", "twitch", "tiktok", "instagram", "facebook",
    "kick", "ganknow", "carrd", "linktree", "litlink",
    "kofi", "patreon", "vgen", "website",
}


def fetch_x_profile_links(
    x_url: str,
    *,
    profile_dir: Optional[Path] = None,
    headless: bool = True,
    timeout: float = 20.0,
) -> dict:
    """
    Fetch an X profile page and extract:
    - hub_urls: Linktree, Carrd, lit.link, personal website URLs from profile
    - platform_links: direct platform account links (YT, TW, TT, etc.)
    - status: "ok" | "login_blocked" | "error" | "empty"

    Returns:
    {
        "status": str,
        "hub_urls": [str, ...],
        "platform_links": [{"platform", "url", "handle", "is_hub", "source_url"}, ...],
        "raw_tco_links": [str, ...],   # t.co URLs for external expansion if needed
    }
    """
    result = {
        "status": "ok",
        "hub_urls": [],
        "platform_links": [],
        "raw_tco_links": [],
    }

    # Try stdlib first (may work for some public profiles before JS hydration)
    html = fetch_html(x_url, timeout=10.0)

    # If no meaningful content, try browser
    if not html or len(html) < 500 or "application/json" in (html or ""):
        if profile_dir or not headless:
            # Has a logged-in profile or explicit non-headless: try browser
            html = fetch_with_browser_sync(
                x_url,
                headless=headless,
                profile_dir=profile_dir,
                timeout=timeout,
            )
        # Still no content → login-blocked or error
        if not html:
            result["status"] = "login_blocked"
            return result

    # Check for login wall
    if _X_LOGIN_PATTERNS.search(html):
        result["status"] = "login_blocked"
        return result

    # 1. Extract SSR embedded expanded_urls
    ssr_urls = re.findall(r'expanded_url\s*:\s*["\']([^"\']+)["\']', html)
    ssr_urls += re.findall(r'expandedUrl\s*:\s*["\']([^"\']+)["\']', html)

    # 2. Extract HTML anchor links
    anchor_links = extract_platform_links(
        html,
        source_url=x_url,
        include_hubs=True,
        max_links=50,
    )

    # 3. Collect t.co links
    tco_links = list(dict.fromkeys(re.findall(r'https://t\.co/[A-Za-z0-9]+', html)))
    result["raw_tco_links"] = tco_links

    # If no SSR expanded URLs were found, unwrap the first few t.co links directly
    candidate_urls = list(ssr_urls)
    if not ssr_urls and tco_links:
        for tco in tco_links[:3]:
            unwrapped = _unwrap_tco_link(tco)
            if unwrapped:
                candidate_urls.append(unwrapped)

    hubs = []
    direct = []
    seen = set()

    # Process anchor links
    for lnk in anchor_links:
        u = lnk.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        if lnk.get("is_hub"):
            hubs.append(u)
        elif lnk.get("platform") in _PLATFORM_TARGETS and lnk.get("platform") not in ("website", "x"):
            direct.append(lnk)

    # Process SSR/unwrapped candidate URLs
    for u in candidate_urls:
        if not u or u in seen:
            continue
        seen.add(u)
        if is_hub(u):
            hubs.append(u)
            continue
        plat = infer_platform(u)
        if plat in _PLATFORM_TARGETS and plat not in ("website", "x"):
            try:
                norm = normalize_url(plat, u, validate=False)
                handle = extract_handle_from_url(plat, norm)
                direct.append({
                    "platform": plat,
                    "url": norm,
                    "handle": handle,
                    "is_hub": False,
                    "source_url": x_url,
                })
            except Exception:
                continue

    # Deduplicate direct links by (platform, url)
    deduped_direct = []
    seen_plat_url = set()
    for d in direct:
        key = (d["platform"], d["url"])
        if key not in seen_plat_url:
            seen_plat_url.add(key)
            deduped_direct.append(d)

    result["hub_urls"] = list(dict.fromkeys(hubs))
    result["platform_links"] = deduped_direct

    if not result["hub_urls"] and not result["platform_links"]:
        result["status"] = "empty"

    return result


def _unwrap_tco_link(tco_url: str, timeout: float = 2.0) -> Optional[str]:
    """Unwrap a t.co redirect via HTTP HEAD."""
    import urllib.request
    try:
        req = urllib.request.Request(tco_url, headers={"User-Agent": "Mozilla/5.0"}, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.geturl()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Hub crawlers: Linktree / Carrd / lit.link / personal website / VGen / etc.
# ---------------------------------------------------------------------------

# Hub types that work with stdlib fetch (no JS needed)
_STDLIB_HUBS = {"linktree", "litlink", "carrd", "kofi", "patreon", "vgen"}


def crawl_hub(hub_url: str, *, timeout: float = 15.0) -> list[dict]:
    """
    Fetch a creator hub page and return all platform account links found.

    Returns list of:
    {
        "platform": str,
        "url": str,
        "handle": str | None,
        "is_hub": bool,
        "source_url": str,
    }

    Tries stdlib fetch first; falls back to browser for JS-heavy hubs.
    """
    platform = infer_platform(hub_url)

    # Stdlib is sufficient for most hub platforms
    if platform in _STDLIB_HUBS or platform == "website":
        html = fetch_html(hub_url, timeout=timeout)
    else:
        html = None

    if not html:
        # Try browser as fallback (beacons.ai, bio.link, etc. require JS)
        try:
            html = fetch_with_browser_sync(hub_url, headless=True, timeout=timeout)
        except Exception:
            html = None

    if not html:
        return []

    links = extract_platform_links(
        html,
        source_url=hub_url,
        include_hubs=False,  # Don't recurse into nested hubs
        max_links=60,
    )

    # Filter to meaningful platforms only
    return [l for l in links if l["platform"] in _PLATFORM_TARGETS]


# ---------------------------------------------------------------------------
# Batch hub crawl with JSONL output
# ---------------------------------------------------------------------------

def batch_crawl_hubs(
    hub_records: list[dict],
    output_path: Path,
    *,
    delay: float = 0.3,
    skip_existing: bool = True,
) -> dict:
    """
    Process a list of hub records and write results to JSONL.

    Each record must have: youtube_account_id, hub_url
    Optional: youtube_name, youtube_url, x_url

    Appends to output_path, supports resume.
    """
    import pathlib
    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    processed: set[str] = set()
    if skip_existing and output_path.exists():
        with output_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    processed.add(f"{rec['youtube_account_id']}|{rec['hub_url']}")
                except Exception:
                    continue

    stats = {"total": 0, "links_found": 0, "empty": 0, "errors": 0}

    with output_path.open("a", encoding="utf-8") as out:
        for rec in hub_records:
            key = f"{rec['youtube_account_id']}|{rec['hub_url']}"
            if key in processed:
                continue

            stats["total"] += 1
            observed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            try:
                links = crawl_hub(rec["hub_url"])
                stats["links_found"] += len(links)
                if not links:
                    stats["empty"] += 1
                record = {
                    "youtube_account_id": rec["youtube_account_id"],
                    "youtube_name": rec.get("youtube_name", ""),
                    "youtube_url": rec.get("youtube_url", ""),
                    "x_url": rec.get("x_url", ""),
                    "hub_url": rec["hub_url"],
                    "platform_links": links,
                    "observed_at": observed_at,
                }
            except Exception as exc:
                stats["errors"] += 1
                record = {
                    "youtube_account_id": rec["youtube_account_id"],
                    "hub_url": rec["hub_url"],
                    "platform_links": [],
                    "error": str(exc),
                    "observed_at": observed_at,
                }

            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            processed.add(key)

            if delay > 0:
                time.sleep(delay)

    return stats
