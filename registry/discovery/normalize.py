"""URL, handle, and platform identity normalization."""

import re
from typing import Optional, Set
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ..store import PLATFORMS, account_url, public_url

TRACKING_PARAMS: Set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "si",
    "ref",
    "ref_src",
    "t",
    "s",
    "feature",
    "lang",
    "sub_confirmation",
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

PLATFORM_HOST_PATTERNS = [
    ("youtube", r"^(www\.|m\.)?youtube\.com$|^youtu\.be$"),
    ("twitch", r"^(www\.|m\.)?twitch\.tv$"),
    ("tiktok", r"^(www\.|m\.)?tiktok\.com$"),
    ("facebook", r"^(www\.|m\.|web\.)?facebook\.com$"),
    ("instagram", r"^(www\.)?instagram\.com$"),
    ("x", r"^(www\.|mobile\.)?(x|twitter)\.com$"),
    ("kick", r"^(www\.)?kick\.com$"),
    ("ganknow", r"^(www\.)?ganknow\.com$"),
    ("bilibili", r"^(www\.|space\.)?bilibili\.com$"),
    ("niconico", r"^(www\.|sp\.|user\.)?nicovideo\.jp$"),
    ("carrd", r"^([a-zA-Z0-9_-]+\.)?carrd\.co$"),
    ("linktree", r"^(www\.)?linktr\.ee$"),
    ("litlink", r"^(www\.)?lit\.link$"),
    ("kofi", r"^(www\.)?ko-fi\.com$"),
    ("patreon", r"^(www\.)?patreon\.com$"),
    ("vgen", r"^(www\.)?vgen\.co$"),
]


RESERVED_PATH_SEGMENTS = {
    "home", "explore", "search", "notifications", "messages", "settings",
    "directory", "downloads", "jobs", "turbo", "help", "terms", "privacy",
    "login", "signup", "about", "feed", "shop", "creators", "admin", "p",
    "reel", "reels", "stories", "categories", "i", "intent", "hashtag",
    "watch", "groups", "events", "gaming", "pages", "profile.php", "channel",
    "status", "share", "tag", "tags", "blog", "press", "pricing",
    "videos", "video", "clip", "clips", "post", "posts", "broadcast",
}


def normalize_handle(handle: Optional[str]) -> Optional[str]:
    """Strip leading @, whitespace, and empty strings."""
    if handle is None:
        return None
    cleaned = handle.strip()
    if cleaned.startswith("@"):
        cleaned = cleaned[1:].strip()
    return cleaned if cleaned else None


def extract_handle_from_url(platform: str, url: str) -> Optional[str]:
    """Extract creator handle from canonical platform URL where applicable."""
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

    if platform in ("twitch", "x", "instagram", "facebook", "kick", "ganknow", "linktree", "kofi", "patreon", "vgen"):
        clean = first.lstrip("@").strip()
        if clean and clean.lower() not in RESERVED_PATH_SEGMENTS and not clean.startswith("?"):
            return clean

    return None


def strip_tracking_params(parsed_url) -> str:
    """Filter out known tracking query parameters."""
    query_items = parse_qsl(parsed_url.query, keep_blank_values=False)
    filtered = [(k, v) for k, v in query_items if k.lower() not in TRACKING_PARAMS]
    new_query = urlencode(filtered)
    return new_query


def infer_platform(url: str) -> Optional[str]:
    """Identify which platform a URL belongs to based on hostname."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not host:
            return None
        for platform, pattern in PLATFORM_HOST_PATTERNS:
            if re.match(pattern, host):
                return platform
        return "website"
    except Exception:
        return None


def normalize_url(platform: str, raw_url: str) -> str:
    """
    Canonicalize a URL:
    - Force HTTPS
    - Strip tracking query params
    - Normalize known host aliases (e.g. twitter.com -> x.com)
    - Normalize trailing slashes on profile paths
    - Enforce platform validation rules
    """
    if not raw_url or not isinstance(raw_url, str):
        raise ValueError("URL must be a non-empty string")

    parsed = urlparse(raw_url.strip())
    # Force scheme to https if missing or http
    scheme = "https"
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError(f"Invalid URL (missing host): {raw_url}")

    # Canonicalize host aliases
    if host in HOST_ALIASES:
        host = HOST_ALIASES[host]

    # Clean query parameters
    cleaned_query = strip_tracking_params(parsed)

    # Normalize path
    path = parsed.path
    if path and path != "/":
        path = path.rstrip("/")
    elif not path:
        path = ""

    if platform == "youtube" and path:
        for tab in ("/videos", "/featured", "/about", "/community", "/streams", "/shorts"):
            if path.lower().endswith(tab):
                path = path[:-len(tab)]
                break

    # Reconstruct normalized URL
    normalized = urlunparse((
        scheme,
        host,
        path,
        "",  # params
        cleaned_query,
        "",  # fragment stripped
    ))

    # Validate against store rules
    account_url(platform, normalized)
    return normalized
