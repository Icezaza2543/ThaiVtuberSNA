"""Default discovery query terms and resolution helpers."""

from typing import Any, List, Optional

DEFAULT_DISCOVERY_QUERIES = [
    "VTuberTH",
    "ThaiVTuber",
    "VTuber Thailand",
    "Thai VStreamer",
    "VStreamerTH",
    "PNGTuberTH",
    "VSingerTH",
    "วีทูบเบอร์ไทย",
    "วีทูปเบอร์ไทย",
    "วีสตรีมเมอร์",
    "วีไทย",
    "virtual creator thailand",
    "virtual streamer thai",
    "Virtual Idol Thailand",
    "เดบิวต์ VTuber",
    "เปิดตัวโมเดล",
]

PLATFORM_SPECIFIC_QUERIES = {
    "twitch": [
        "VTuberTH", "ThaiVTuber", "VTuber", "Vtuberไทย", "VTuber Thailand",
        "Thai VStreamer", "VStreamerTH", "PNGTuberTH", "วีสตรีมเมอร์"
    ],
    "youtube": [
        "VTuberTH", "ThaiVTuber", "VTuber Thailand", "Thai VStreamer", "VStreamerTH",
        "วีทูบเบอร์ไทย", "วีทูปเบอร์ไทย", "วีทูปเบอร์", "PNGTuberTH", "VSingerTH",
        "virtual creator thailand", "วีสตรีมเมอร์"
    ],
    "ganknow": ["VTuber", "VTuberTH", "ThaiVTuber", "Virtual Creator", "วีทูปเบอร์", "วีทูปเบอร์ไทย"],
    "kick": ["VTuberTH", "ThaiVTuber", "VTuber Thailand", "VTuber", "Thai VStreamer"],
    "facebook": ["VTuberTH", "ThaiVTuber", "VTuber Thailand", "วีทูบเบอร์ไทย", "วีทูปเบอร์ไทย"],
    "tiktok": ["VTuberTH", "ThaiVTuber", "VTuber Thailand", "วีทูปเบอร์ไทย", "วีทูบเบอร์ไทย", "VStreamerTH"],
}

GENERIC_NOISE_TERMS = {
    "channel", "official", "studio", "production", "thailand", "vtuber", "music",
    "live", "gaming", "stream", "video", "anime", "project", "crew", "team",
    "network", "records", "entertainment", "club", "house", "family", "ch",
}


def clean_seed_string(s: Optional[str]) -> Optional[str]:
    """Clean and validate creator identifier for search expansion."""
    if not s or not isinstance(s, str):
        return None
    cleaned = s.strip()
    # Strip leading @ or trailing common channel suffixes
    if cleaned.startswith("@"):
        cleaned = cleaned[1:].strip()
    for suffix in (" Ch.", " Ch", " Official", " TH", " VTuber", "【ARP】", "【ECR】", "【21PM】"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-len(suffix)].strip()
    if len(cleaned) < 3 or len(cleaned) > 40:
        return None
    if cleaned.isdigit():
        return None
    if cleaned.lower() in GENERIC_NOISE_TERMS:
        return None
    return cleaned


def resolve_queries(
    custom_queries: Optional[List[str]] = None,
    additional_queries: Optional[List[str]] = None,
    platform: Optional[str] = None,
) -> List[str]:
    """Return custom queries if provided, or platform-appropriate default query terms, plus any additional seeds."""
    if custom_queries:
        cleaned = [q.strip() for q in custom_queries if q and q.strip()]
        base = cleaned if cleaned else list(DEFAULT_DISCOVERY_QUERIES)
    elif platform and platform in PLATFORM_SPECIFIC_QUERIES:
        base = list(PLATFORM_SPECIFIC_QUERIES[platform])
    else:
        base = list(DEFAULT_DISCOVERY_QUERIES)

    if additional_queries:
        seen = set(base)
        for q in additional_queries:
            q_clean = q.strip()
            if q_clean and q_clean not in seen:
                seen.add(q_clean)
                base.append(q_clean)

    return base


def get_registry_expansion_seeds(db: Any, max_seeds: int = 250) -> List[str]:
    """
    Extract search seeds from existing registry accounts and personas with strict prioritization:
    1. Handles of verified persona accounts (Priority 1)
    2. Handles of YouTube accounts (Priority 2)
    3. Other account handles (Priority 3)
    4. Persona display names (Priority 4)
    5. Account display names (Priority 5)
    Filters out noise, short terms, and generic words.
    """
    seeds = []
    seen = set()

    def _add_seed(val: Optional[str]):
        if not val or not isinstance(val, str):
            return
        raw = val.strip()
        if raw.startswith("@"):
            raw = raw[1:].strip()
        if len(raw) >= 3 and len(raw) <= 40 and not raw.isdigit() and raw.lower() not in GENERIC_NOISE_TERMS:
            if raw.lower() not in seen:
                seen.add(raw.lower())
                seeds.append(raw)
        cleaned = clean_seed_string(val)
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            seeds.append(cleaned)

    try:
        # Priority 1: Handles of verified persona accounts
        for row in db.execute("""
            SELECT a.handle
            FROM accounts a
            JOIN account_links al ON a.id = al.account_id
            WHERE al.review_status = 'verified' AND a.handle IS NOT NULL
            ORDER BY length(a.handle) DESC
        """).fetchall():
            _add_seed(row[0])
            if len(seeds) >= max_seeds:
                return seeds

        # Priority 2: Handles of YouTube accounts
        for row in db.execute("""
            SELECT handle FROM accounts
            WHERE platform = 'youtube' AND handle IS NOT NULL
            ORDER BY length(handle) DESC
        """).fetchall():
            _add_seed(row[0])
            if len(seeds) >= max_seeds:
                return seeds

        # Priority 3: Other unique account handles
        for row in db.execute("SELECT handle FROM accounts WHERE handle IS NOT NULL").fetchall():
            _add_seed(row[0])
            if len(seeds) >= max_seeds:
                return seeds

        # Priority 4: Verified Persona display names
        for row in db.execute("SELECT name FROM personas ORDER BY length(name) DESC").fetchall():
            _add_seed(row[0])
            if len(seeds) >= max_seeds:
                return seeds

        # Priority 5: Account names
        for row in db.execute("SELECT name FROM accounts WHERE name IS NOT NULL").fetchall():
            _add_seed(row[0])
            if len(seeds) >= max_seeds:
                return seeds

    except Exception:
        pass

    return seeds[:max_seeds]

