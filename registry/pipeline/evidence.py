"""evidence.py — Evidence chain builder and review proposal generator.

Responsibilities:
  1. Build a traceable evidence chain from any public source account to a target
  2. Resolve stable IDs for new platform accounts (Twitch user_id, TikTok web_user_id)
  3. Match against existing registry accounts (deduplication)
  4. Detect agency/shared accounts (reject)
  5. Emit review proposals in the format expected by `python -m registry apply`

Evidence chain schema:
  {
    "youtube_account_id": str,
    "evidence_chain": [
      {"step": "youtube_account", "url": str, "platform_id": str},
      {"step": "x_profile",      "url": str, "source": "grok_x_search"|"existing_evidence"},
      {"step": "hub",            "url": str, "hub_platform": str},
      {"step": "target_account", "url": str, "platform": str, "handle": str}
    ]
  }

Review proposal format:
  {
    "version": 1,
    "changes": [
      {
        "action": "add_account" | "add_candidate" | "add_account_link",
        "platform": str,
        "url": str,
        "platform_id": str | null,
        "id_namespace": str | null,
        "evidence_chain": [...],
        "confidence": "high"|"medium"|"low",
        "reviewer": null,    # Must be filled in by human reviewer
        "reviewed_at": null  # Must be filled in by human reviewer
      }
    ]
  }
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from ..store import ROOT, load, rows
from ..identity import verified_account_personas
from ..urls import extract_handle_from_url, infer_platform, normalize_url

# Platforms we emit proposals for
TARGET_PLATFORMS = {
    "youtube", "twitch", "tiktok", "instagram", "facebook",
    "x", "kick", "ganknow", "bilibili", "niconico",
    "carrd", "linktree", "litlink", "kofi", "patreon", "vgen",
}

# Known agency/shared account patterns (conservative — handle similarity only triggers review, not rejection)
_AGENCY_NAME_PATTERNS = [
    "upd8", "nijisanji", "hololive", "vspo", "react", "dotlive",
    "animare", "honeystrap", "vivid army", "kamitsubaki", "v.dere",
    "v4mirai", "prism project", "idol corp", "phase connect", "neoporte",
]


# ---------------------------------------------------------------------------
# Stable ID resolution (reuses existing resolvers from discovery/)
# ---------------------------------------------------------------------------

def _resolve_stable_id(platform: str, handle: str) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve (platform_id, id_namespace) for a given platform + handle.
    Returns (None, None) if resolution fails or platform not supported.
    Wraps existing discovery/enrich.py resolvers.
    """
    if not handle:
        return None, None
    try:
        if platform == "twitch":
            from ..discovery.enrich import resolve_tiktok_web_user_id
            from ..twitch_public import resolve_public_twitch_user_id, get_public_twitch_client_id
            cid = get_public_twitch_client_id(handle)
            uid = resolve_public_twitch_user_id(handle, client_id=cid)
            if uid:
                return uid, "user_id"
        elif platform == "tiktok":
            from ..discovery.enrich import resolve_tiktok_web_user_id
            uid = resolve_tiktok_web_user_id(handle)
            if uid:
                return uid, "web_user_id"
    except Exception:
        pass
    return None, None


# ---------------------------------------------------------------------------
# Registry lookup helpers
# ---------------------------------------------------------------------------

def _load_existing_accounts(data_path: Path) -> dict[str, dict]:
    """
    Load all existing registry accounts keyed by (platform, url).
    Returns dict: (platform, url) → account dict.
    """
    db = load(data_path)
    try:
        result = {}
        for row in db.execute("SELECT * FROM accounts").fetchall():
            key = (row["platform"], row["url"])
            result[key] = dict(row)
        return result
    finally:
        db.close()


def _load_existing_account_links(data_path: Path) -> set[tuple[str, str]]:
    """Return set of (persona_id, account_id) pairs that are already linked."""
    db = load(data_path)
    try:
        return {
            (r["persona_id"], r["account_id"])
            for r in db.execute(
                "SELECT persona_id, account_id FROM account_links WHERE review_status='verified'"
            ).fetchall()
        }
    finally:
        db.close()


def _lookup_source_persona(source_account_id: str, data_path: Path) -> Optional[str]:
    """Resolve one reviewed source persona on any platform; shared is ambiguous."""
    db = load(data_path)
    try:
        pids = verified_account_personas(rows(db, 'personas'), rows(db, 'account_links')).get(source_account_id, [])
        return pids[0] if len(pids) == 1 else None
    finally:
        db.close()


def _lookup_youtube_persona(youtube_account_id: str, data_path: Path) -> Optional[str]:
    """Compatibility wrapper for historical YouTube-seeded input files."""
    return _lookup_source_persona(youtube_account_id, data_path)


# ---------------------------------------------------------------------------
# Agency detection
# ---------------------------------------------------------------------------

_FIRST_PARTY_SOURCES = {
    "youtube_about_or_intake",
    "youtube_about_x_urls",
    "existing_evidence",
    "remaining_discovered",
    "remaining-discovered",
    "youtube_about_or_description",
    "owner_profile", "official_profile", "official_crosslink",
    "twitch_profile", "tiktok_profile",
}


def _confidence_for_link(
    *,
    platform: str,
    x_url: Optional[str],
    hub_url: Optional[str],
    source: str,
    is_agency: bool,
) -> str:
    """Score a discovered platform link.

    high  = explicit owner cross-link, on any platform (review priority only)
    medium = X profile only, or a hub without X
    low   = name-only / agency / leftover
    """
    if is_agency:
        return "low"
    first_party = source in _FIRST_PARTY_SOURCES
    if x_url and hub_url:
        return "high"
    if first_party:
        return "high"
    if x_url:
        return "medium"
    if hub_url:
        return "medium"
    return "low"


def _looks_like_agency(name: str, url: str) -> bool:
    """Heuristic check for agency/group accounts. False positives prefer human review."""
    name_lower = (name or "").lower()
    url_lower = (url or "").lower()
    return any(pattern in name_lower or pattern in url_lower for pattern in _AGENCY_NAME_PATTERNS)


# ---------------------------------------------------------------------------
# Evidence chain builder
# ---------------------------------------------------------------------------

def build_evidence_chain(
    youtube_account_id: str,
    youtube_url: str,
    youtube_platform_id: str,
    x_url: Optional[str],
    x_source: str,
    hub_url: Optional[str],
    target_platform_link: dict,
    *,
    source_account: Optional[dict] = None,
) -> list[dict]:
    """Build source → optional X/hub → target, retaining legacy input support."""
    chain = [
        {
            "step": "youtube_account",
            "url": youtube_url,
            "platform": "youtube",
            "platform_id": youtube_platform_id,
            "account_id": youtube_account_id,
        }
    ]
    if source_account is not None:
        chain = [{"step": "source_account", **source_account}]
    if x_url:
        chain.append({
            "step": "x_profile",
            "url": x_url,
            "platform": "x",
            "source": x_source,
        })
    if hub_url:
        chain.append({
            "step": "hub",
            "url": hub_url,
            "platform": infer_platform(hub_url) or "website",
        })
    chain.append({
        "step": "target_account",
        "url": target_platform_link.get("url", ""),
        "platform": target_platform_link.get("platform", ""),
        "handle": target_platform_link.get("handle"),
    })
    return chain


# ---------------------------------------------------------------------------
# Per-record proposal builder
# ---------------------------------------------------------------------------

def build_proposals_for_record(
    record: dict,
    existing_accounts: dict,
    existing_links: set,
    *,
    resolve_ids: bool = True,
) -> list[dict]:
    """
    For one creator-platform-links record, build review proposals.

    Skip:
    - Links that already exist as verified accounts in the registry
    - Agency/shared accounts (flagged, stored as low-confidence candidate)
    - Platforms not in TARGET_PLATFORMS
    """
    proposals = []
    acct_id = record.get("source_account_id") or record.get("youtube_account_id", "")
    source_url = record.get("source_url") or record.get("youtube_url", "")
    source_platform = record.get("source_platform") or ("youtube" if record.get("youtube_account_id") else infer_platform(source_url))
    source_platform_id = record.get("source_platform_id") or record.get("youtube_platform_id", record.get("platform_id", ""))
    source_account = {"account_id": acct_id, "platform": source_platform,
                      "url": source_url, "platform_id": source_platform_id}
    x_url = record.get("x_url")
    x_source = record.get("source", "grok_x_search")
    hub_url = record.get("hub_url")

    observed_at = record.get("observed_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    for link in record.get("platform_links", []):
        platform = link.get("platform", "")
        url = link.get("url", "")
        handle = link.get("handle")
        name = link.get("name", handle or "")

        if not url or not platform or platform not in TARGET_PLATFORMS:
            continue

        # Skip only this source account, not an entire platform. Twitch-first
        # records can discover YouTube, and a creator may have two same-site accounts.
        if platform == source_platform and source_url:
            try:
                if normalize_url(platform, url) == normalize_url(source_platform, source_url):
                    continue
            except ValueError:
                pass

        # Check if already in registry
        existing = existing_accounts.get((platform, url))
        if existing and existing.get("review_status") == "verified":
            continue  # Already verified — no proposal needed

        # Agency check
        is_agency = _looks_like_agency(name, url)

        # Resolve stable ID
        platform_id, id_namespace = None, None
        if resolve_ids and handle and not is_agency:
            platform_id, id_namespace = _resolve_stable_id(platform, handle)

        # Build evidence chain
        chain = build_evidence_chain(
            youtube_account_id=acct_id,
            youtube_url=source_url,
            youtube_platform_id=source_platform_id,
            x_url=x_url,
            x_source=x_source,
            hub_url=hub_url,
            target_platform_link=link,
            source_account=source_account if record.get("source_account_id") else None,
        )

        # Confidence: YouTube About / owner crosslinks are first-party even
        # without an X+hub chain. Agency stays low.
        source = record.get("source") or x_source or ""
        confidence = _confidence_for_link(
            platform=platform,
            x_url=x_url,
            hub_url=hub_url,
            source=source,
            is_agency=is_agency,
        )

        action = "add_candidate" if is_agency else ("add_account" if platform_id else "add_candidate")

        proposal = {
            "action": action,
            "source_account_id": acct_id,
            "source_platform": source_platform,
            "source_url": source_url,
            "platform": platform,
            "url": url,
            "name": name or handle or "",
            "handle": handle,
            "platform_id": platform_id,
            "id_namespace": id_namespace,
            "confidence": confidence,
            "evidence_chain": chain,
            "observed_at": observed_at,
            "source": source,
            "needs_human_review": True,  # confidence never certifies persona scope/ownership
            "reviewer": None,      # Human fills in
            "reviewed_at": None,   # Human fills in
        }

        if is_agency:
            proposal["flag"] = "possible_agency_or_group_account"

        proposals.append(proposal)

    return proposals


# ---------------------------------------------------------------------------
# Batch review proposal builder
# ---------------------------------------------------------------------------

def build_review_batch(
    records: list[dict],
    data_path: Optional[Path] = None,
    *,
    resolve_ids: bool = True,
) -> dict:
    """
    Process all creator-platform-links records and produce a consolidated review batch.

    Returns classifier proposals, NOT a directly applicable registry change file:
    {
        "version": 1,
        "generated_at": str,
        "source_pipeline": "creator-link-pipeline",
        "changes": [...]
    }
    """
    if data_path is None:
        data_path = ROOT / "data/registry.json"

    print("Loading existing accounts from registry...")
    existing_accounts = _load_existing_accounts(data_path)
    existing_links = _load_existing_account_links(data_path)
    print(f"  {len(existing_accounts)} existing accounts loaded")

    all_proposals = []
    seen_observations: set[str] = set()  # Preserve distinct source/evidence chains

    for rec in records:
        proposals = build_proposals_for_record(
            rec,
            existing_accounts,
            existing_links,
            resolve_ids=resolve_ids,
        )
        for prop in proposals:
            observation_key = json.dumps(
                [prop['source_account_id'], prop['platform'], prop['url'],
                 prop['evidence_chain'], prop['observed_at'], prop['source']], sort_keys=True)
            if observation_key not in seen_observations:
                seen_observations.add(observation_key)
                all_proposals.append(prop)

    # Sort: high confidence first, then by platform, then by url
    _conf_rank = {"high": 0, "medium": 1, "low": 2}
    all_proposals.sort(key=lambda p: (_conf_rank.get(p["confidence"], 3), p["platform"], p["url"]))

    return {
        "version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_pipeline": "creator-link-pipeline",
        "stats": {
            "total_changes": len(all_proposals),
            "high_confidence": sum(1 for p in all_proposals if p["confidence"] == "high"),
            "medium_confidence": sum(1 for p in all_proposals if p["confidence"] == "medium"),
            "low_confidence": sum(1 for p in all_proposals if p["confidence"] == "low"),
            "needs_human_review": sum(1 for p in all_proposals if p.get("needs_human_review")),
            "agency_flagged": sum(1 for p in all_proposals if "flag" in p),
        },
        "changes": all_proposals,
    }
