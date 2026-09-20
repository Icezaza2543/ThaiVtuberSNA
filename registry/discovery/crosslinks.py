"""Extract outbound cross-links from public creator profile pages and link hubs."""

from html.parser import HTMLParser
from typing import List, Optional, Set
from urllib.parse import parse_qs, unquote, urlparse

from .models import DiscoveryLead
from .normalize import extract_handle_from_url, infer_platform, normalize_url


def _unwrap_redirect_url(url: str) -> str:
    """Unwrap known platform outbound redirect links (e.g. YouTube redirect?q=, Facebook l.php?u=)."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host in ("youtube.com", "www.youtube.com", "m.youtube.com") and parsed.path == "/redirect":
            qs = parse_qs(parsed.query)
            target = qs.get("q", [None])[0]
            if target and (target.startswith("http://") or target.startswith("https://")):
                return unquote(target)
        elif "facebook.com" in host and "/l.php" in parsed.path:
            qs = parse_qs(parsed.query)
            target = qs.get("u", [None])[0]
            if target and (target.startswith("http://") or target.startswith("https://")):
                return unquote(target)
    except Exception:
        pass
    return url


class _LinkExtractor(HTMLParser):
    def __init__(self, max_links: int = 50):
        super().__init__()
        self.links: List[str] = []
        self.max_links = max_links

    def handle_starttag(self, tag, attrs):
        if len(self.links) >= self.max_links:
            return
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    val = value.strip()
                    if val.startswith("http://") or val.startswith("https://"):
                        unwrapped = _unwrap_redirect_url(val)
                        self.links.append(unwrapped)


def extract_urls_from_html(html: str, max_links: int = 50) -> List[str]:
    """Parse HTML and return outbound HTTP/HTTPS links up to max_links."""
    parser = _LinkExtractor(max_links=max_links)
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser.links


EXCLUDED_WEBSITE_DOMAINS = {
    "google.com",
    "www.google.com",
    "apple.com",
    "www.apple.com",
    "apps.apple.com",
    "play.google.com",
    "cloudflare.com",
    "support.google.com",
    "policies.google.com",
}


def _clean_host(h: Optional[str]) -> str:
    h = (h or "").lower().strip()
    return h[4:] if h.startswith("www.") else h


def extract_crosslinks(
    html: str,
    parent_url: str,
    observed_at: str,
    max_links: int = 30,
    allow_websites: bool = False,
    allow_same_host: bool = False,
) -> List[DiscoveryLead]:
    """
    Extract outbound crosslinks from a discovered page's HTML to known platforms.
    Generates DiscoveryLeads with source_url pointing back to parent_url.
    Does not recurse beyond 1 hop.
    Skips same-host internal navigation links by default.
    """
    raw_urls = extract_urls_from_html(html, max_links=max_links * 2)
    parent_host = urlparse(parent_url).hostname.lower() if parent_url else ""

    leads: List[DiscoveryLead] = []
    seen_urls: Set[str] = set()

    for raw_url in raw_urls:
        if len(leads) >= max_links:
            break
        platform = infer_platform(raw_url)
        if not platform:
            continue
        if platform == "website":
            if not allow_websites:
                continue
            parsed_raw = urlparse(raw_url)
            host = (parsed_raw.hostname or "").lower()
            if not host or host in EXCLUDED_WEBSITE_DOMAINS or host.endswith(".google.com") or host.endswith(".apple.com"):
                continue

        try:
            normalized = normalize_url(platform, raw_url)
            target_host = urlparse(normalized).hostname

            # Skip same-host internal navigation links (outbound discovery only)
            if not allow_same_host and _clean_host(target_host) == _clean_host(parent_host):
                continue
            if normalized in seen_urls:
                continue

            seen_urls.add(normalized)
            extracted_handle = extract_handle_from_url(platform, normalized)
            leads.append(
                DiscoveryLead(
                    platform=platform,
                    name=extracted_handle or "",
                    url=normalized,
                    handle=extracted_handle,
                    source_url=parent_url,
                    observed_at=observed_at,
                    source_kind="secondary_source" if platform == "website" else "platform_observation",
                    metadata={"origin": "crosslink_crawl"},
                )
            )
        except (ValueError, Exception):
            continue

    return leads
