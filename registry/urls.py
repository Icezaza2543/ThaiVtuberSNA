"""URL and handle normalization utilities.

Generic, self-contained module with no dependency on registry/discovery/.
Used by registry/pipeline/ and any other new code.

These functions are distilled from registry/discovery/normalize.py
and extended to cover the creator-link pipeline needs.
"""

import re
from html.parser import HTMLParser
from typing import List, Optional, Set
from urllib.parse import parse_qs, parse_qsl, unquote, urlencode, urlparse, urlunparse

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRACKING_PARAMS: Set[str] = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "si", "ref", "ref_src", "t", "s", "feature", "lang",
    "is_from_webapp", "sender_device", "embedFrom",
}

HOST_ALIASES = {
    "twitter.com": "x.com",
    "www.twitter.com": "x.com",
    "mobile.twitter.com": "x.com",
    "m.facebook.com": "facebook.com",
    "web.facebook.com": "facebook.com",
    "m.youtube.com": "youtube.com",
    "m.twitch.tv": "twitch.tv",
    "sp.nicovideo.jp": "nicovideo.jp",
    "user.nicovideo.jp": "nicovideo.jp",
}

# Ordered: most specific patterns first
PLATFORM_HOST_PATTERNS = [
    ("youtube",   r"^(www\.|m\.)?youtube\.com$|^youtu\.be$"),
    ("twitch",    r"^(www\.|m\.)?twitch\.tv$"),
    ("tiktok",    r"^(www\.|m\.)?tiktok\.com$"),
    ("facebook",  r"^(www\.|m\.|web\.)?facebook\.com$"),
    ("instagram", r"^(www\.)?instagram\.com$"),
    ("x",         r"^(www\.|mobile\.)?(x|twitter)\.com$"),
    ("kick",      r"^(www\.)?kick\.com$"),
    ("ganknow",   r"^(www\.)?ganknow\.com$"),
    ("bilibili",  r"^(www\.|space\.)?bilibili\.com$"),
    ("niconico",  r"^(www\.|sp\.|user\.)?nicovideo\.jp$"),
    ("carrd",     r"^([a-zA-Z0-9_-]+\.)?carrd\.co$"),
    ("linktree",  r"^(www\.)?linktr\.ee$"),
    ("litlink",   r"^(www\.)?lit\.link$"),
    ("kofi",      r"^(www\.)?ko-fi\.com$"),
    ("patreon",   r"^(www\.)?patreon\.com$"),
    ("vgen",      r"^(www\.)?vgen\.co$"),
    # Link hubs without their own platform slot
    ("website",   r"^(www\.)?beacons\.ai$"),
    ("website",   r"^(www\.)?bio\.link$"),
    ("website",   r"^(www\.)?solo\.to$"),
    ("website",   r"^(www\.)?potofu\.me$"),
]

RESERVED_PATH_SEGMENTS = {
    "home", "explore", "search", "notifications", "messages", "settings",
    "directory", "downloads", "jobs", "turbo", "help", "terms", "privacy",
    "login", "signup", "about", "feed", "shop", "creators", "admin", "p",
    "reel", "reels", "stories", "categories", "i", "intent", "hashtag",
    "watch", "groups", "events", "gaming", "pages", "profile.php", "channel",
    "status", "share", "tag", "tags", "blog", "press", "pricing",
}

# Hub platforms — destinations we crawl for outbound creator links
HUB_PLATFORMS = {"carrd", "linktree", "litlink"}

HUB_DOMAINS = {
    "carrd.co",
    "linktr.ee",
    "linktree.com",
    "lit.link",
    "beacons.ai",
    "bio.link",
    "taplink.cc",
    "tipme.in.th",
    "tipjai.com",
    "easydonate.app",
    "ko-fi.com",
    "vgen.co",
    "fanbox.cc",
    "patreon.com",
    "solo.to",
    "potofu.me",
    "bio.site",
    "linkbio.co",
    "uwu.ai",
}

# Domains to skip when extracting outbound links
EXCLUDED_LINK_DOMAINS = {
    "google.com", "www.google.com", "apple.com", "www.apple.com",
    "apps.apple.com", "play.google.com", "cloudflare.com",
    "support.google.com", "policies.google.com",
    "support.x.com", "help.x.com", "business.x.com", "developer.x.com",
    "ads.x.com", "about.x.com", "careers.x.com", "status.x.com",
    "support.twitter.com", "help.twitter.com",
    "t.co", "discord.gg", "discord.com", "forms.gle", "docs.google.com",
}


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def infer_platform(url: str) -> Optional[str]:
    """Return which platform a URL belongs to based on hostname, or None."""
    try:
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return None
        for platform, pattern in PLATFORM_HOST_PATTERNS:
            if re.match(pattern, host):
                return platform
        return "website"
    except Exception:
        return None


def is_hub(url: str) -> bool:
    """Return True if the URL points to a known creator link-hub."""
    try:
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return False
        return any(host == d or host.endswith("." + d) for d in HUB_DOMAINS)
    except Exception:
        return False


def normalize_handle(handle: Optional[str]) -> Optional[str]:
    """Strip leading @, whitespace, and return None for empty strings."""
    if handle is None:
        return None
    cleaned = handle.strip().lstrip("@").strip()
    return cleaned if cleaned else None


def extract_handle_from_url(platform: str, url: str) -> Optional[str]:
    """Extract creator handle from a canonical platform URL."""
    if not url or not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return None

    path = parsed.path.strip("/")
    parts = [p for p in path.split("/") if p]

    if platform == "carrd":
        host = (parsed.hostname or "").lower()
        if host.endswith(".carrd.co"):
            sub = host.split(".carrd.co")[0]
            if sub and sub != "www" and sub.lower() not in RESERVED_PATH_SEGMENTS:
                return sub
        return None

    if not parts:
        return None

    first = parts[0].strip()

    if platform in ("tiktok", "youtube"):
        if first.startswith("@"):
            h = first.lstrip("@").strip()
            return h if h else None
        elif platform == "tiktok":
            if first.lower() not in RESERVED_PATH_SEGMENTS:
                return first
        return None

    if platform == "litlink":
        if first in ("en", "th", "ja") and len(parts) > 1:
            first = parts[1].strip()
        if first and first.lower() not in RESERVED_PATH_SEGMENTS:
            return first
        return None

    if platform in ("twitch", "x", "instagram", "facebook", "kick",
                    "ganknow", "linktree", "kofi", "patreon", "vgen"):
        clean = first.lstrip("@").strip()
        if clean and clean.lower() not in RESERVED_PATH_SEGMENTS and not clean.startswith("?"):
            return clean

    return None


def _strip_tracking_params(parsed_url) -> str:
    items = parse_qsl(parsed_url.query, keep_blank_values=False)
    filtered = [(k, v) for k, v in items if k.lower() not in TRACKING_PARAMS]
    return urlencode(filtered)


def normalize_url(platform: str, raw_url: str, validate: bool = True) -> str:
    """
    Canonicalize a URL:
    - Force HTTPS
    - Strip tracking query params
    - Normalize host aliases (twitter.com → x.com)
    - Strip trailing slashes on profile paths
    - Optionally validate against store platform rules
    """
    if not raw_url or not isinstance(raw_url, str):
        raise ValueError("URL must be a non-empty string")

    parsed = urlparse(raw_url.strip())
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError(f"Invalid URL (missing host): {raw_url}")

    host = HOST_ALIASES.get(host, host)
    cleaned_query = _strip_tracking_params(parsed)

    path = parsed.path
    if path and path != "/":
        path = path.rstrip("/")
    elif not path:
        path = ""

    normalized = urlunparse(("https", host, path, "", cleaned_query, ""))

    if validate:
        from .store import account_url
        account_url(platform, normalized)

    return normalized


# ---------------------------------------------------------------------------
# Redirect unwrapping
# ---------------------------------------------------------------------------

def unwrap_redirect(url: str) -> str:
    """Unwrap known platform outbound redirect links."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host in ("youtube.com", "www.youtube.com", "m.youtube.com") and parsed.path == "/redirect":
            target = parse_qs(parsed.query).get("q", [None])[0]
            if target and target.startswith(("http://", "https://")):
                return unquote(target)
        elif "facebook.com" in host and "/l.php" in parsed.path:
            target = parse_qs(parsed.query).get("u", [None])[0]
            if target and target.startswith(("http://", "https://")):
                return unquote(target)
    except Exception:
        pass
    return url


# ---------------------------------------------------------------------------
# HTML link extraction
# ---------------------------------------------------------------------------

class _LinkExtractor(HTMLParser):
    def __init__(self, max_links: int = 100):
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
                    if val.startswith(("http://", "https://")):
                        self.links.append(unwrap_redirect(val))


def extract_links_from_html(html: str, max_links: int = 100) -> List[str]:
    """Parse HTML and return outbound HTTP/HTTPS links (redirects unwrapped)."""
    parser = _LinkExtractor(max_links=max_links)
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser.links


def extract_platform_links(
    html: str,
    source_url: str,
    *,
    include_hubs: bool = True,
    max_links: int = 50,
) -> List[dict]:
    """
    Extract platform account links from HTML, classified by platform.

    Returns list of dicts:
      {platform, url, handle, is_hub, source_url}
    """
    raw_urls = extract_links_from_html(html, max_links=max_links * 2)
    parent_host = (urlparse(source_url).hostname or "").lower()
    if parent_host.startswith("www."):
        parent_host = parent_host[4:]

    results: List[dict] = []
    seen: Set[str] = set()

    for raw_url in raw_urls:
        if len(results) >= max_links:
            break
        platform = infer_platform(raw_url)
        if not platform:
            continue
        if platform == "website":
            parsed_raw = urlparse(raw_url)
            host = (parsed_raw.hostname or "").lower()
            clean_host = host[4:] if host.startswith("www.") else host
            if not host or clean_host in EXCLUDED_LINK_DOMAINS or clean_host == parent_host:
                continue
        try:
            norm = normalize_url(platform, raw_url, validate=False)
        except ValueError:
            continue

        # Skip same-host links
        norm_host = (urlparse(norm).hostname or "").lower()
        clean_norm = norm_host[4:] if norm_host.startswith("www.") else norm_host
        if clean_norm == parent_host:
            continue

        if norm in seen:
            continue
        seen.add(norm)

        hub = is_hub(norm)
        if not include_hubs and hub:
            continue

        handle = extract_handle_from_url(platform, norm)
        results.append({
            "platform": platform,
            "url": norm,
            "handle": handle,
            "is_hub": hub,
            "source_url": source_url,
        })

    return results
