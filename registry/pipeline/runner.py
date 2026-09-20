"""runner.py — Pipeline stage orchestrator.

Entry point: python -m registry map-creators

Loads all YouTube accounts from registry, dispatches each stage,
writes JSONL output with checkpoint/resume support.

Stages:
  youtube-to-x      : YT accounts → Grok X Search → X candidates + local verify
  x-to-hub          : Verified/medium X accounts → X profile fetch → hub URLs
  hub-to-platforms  : Hub URLs → platform link extraction
  build-review      : Platform links → stable IDs → review proposals
  all               : Run all stages in sequence
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from ..store import ROOT, load


# ---------------------------------------------------------------------------
# Seed loader: ALL YouTube accounts from registry
# ---------------------------------------------------------------------------

def load_youtube_seeds(data_path: Optional[Path] = None) -> list[dict]:
    """
    Return all YouTube accounts from registry.json as seed records.

    Includes every account (verified persona OR unlinked) to maximise coverage.
    Each record:
    {
        youtube_account_id: str,
        name: str,
        handle: str | None,
        url: str,
        platform_id: str,       # channel_id (UC...)
        linked_persona_id: str | None,
        is_verified_persona: bool,
    }
    """
    if data_path is None:
        data_path = ROOT / "data/registry.json"

    db = load(data_path)

    try:
        # All verified account_links by persona
        verified_pairs = {
            row["account_id"]: row["persona_id"]
            for row in db.execute(
                "SELECT account_id, persona_id FROM account_links WHERE review_status='verified'"
            ).fetchall()
        }

        # All verified personas
        verified_personas = {
            row["id"]
            for row in db.execute("SELECT id FROM personas WHERE review_status='verified'").fetchall()
        }

        # All YouTube accounts
        accounts = db.execute(
            "SELECT * FROM accounts WHERE platform='youtube' ORDER BY id"
        ).fetchall()

        seeds = []
        for acct in accounts:
            acct_id = acct["id"]
            linked_persona = verified_pairs.get(acct_id)
            seeds.append({
                "youtube_account_id": acct_id,
                "name": acct["name"] or "",
                "handle": _extract_yt_handle(acct["url"]),
                "url": acct["url"],
                "platform_id": acct["platform_id"],  # UC...
                "linked_persona_id": linked_persona,
                "is_verified_persona": bool(linked_persona and linked_persona in verified_personas),
            })
        return seeds
    finally:
        db.close()


def _extract_yt_handle(url: str) -> str:
    """Extract @handle or channel ID from YouTube URL."""
    from urllib.parse import urlparse
    path = urlparse(url).path.rstrip("/")
    parts = [p for p in path.split("/") if p]
    for part in parts:
        if part.startswith("@"):
            return part
    # Return last path segment as fallback (e.g. channel/UCxxx → UCxxx)
    return parts[-1] if parts else ""


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def _load_processed_ids(jsonl_path: Path) -> set[str]:
    """Return set of youtube_account_ids already in a JSONL output file."""
    ids: set[str] = set()
    if not jsonl_path.exists():
        return ids
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line)["youtube_account_id"])
            except Exception:
                continue
    return ids


def _load_resolved_x_ids(jsonl_path: Path) -> set[str]:
    """IDs that already have at least one X candidate URL (hub-only rows do not count)."""
    ids: set[str] = set()
    if not jsonl_path.exists():
        return ids
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            acct_id = rec.get("youtube_account_id")
            if not acct_id:
                continue
            if rec.get("x_url"):
                ids.add(acct_id)
                continue
            for cand in rec.get("candidates") or []:
                if cand.get("x_url"):
                    ids.add(acct_id)
                    break
    return ids


# ---------------------------------------------------------------------------
# Stage 1: YouTube → X  (via Grok X Search or existing evidence)
# ---------------------------------------------------------------------------

def run_youtube_to_x(
    seeds: list[dict],
    output_path: Path,
    *,
    api_key: Optional[str] = None,
    model: str = "grok-4.3",
    use_existing_evidence: bool = True,
    limit: Optional[int] = None,
    offset: int = 0,
    delay: float = 0.5,
) -> dict:
    """
    Stage 1: Resolve YouTube accounts → official X accounts.

    Priority:
      1. Existing intake JSONL evidence (zero cost)
      2. Grok X Search API

    Returns stats dict.
    """
    from .grok_x import batch_resolve

    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed = _load_resolved_x_ids(output_path)

    # Apply offset/limit
    batch = seeds[offset:]
    if limit:
        batch = batch[:limit]

    # Skip only accounts that already have an X URL (hub-only pre-enrich must still go to Grok)
    batch = [s for s in batch if s["youtube_account_id"] not in processed]

    # Pass 1: fill from existing evidence (free)
    if use_existing_evidence:
        filled, batch = _fill_from_existing_evidence(batch, output_path)
    else:
        filled = 0

    print(f"Stage 1: {filled} accounts resolved from existing evidence, {len(batch)} sent to Grok")

    if not batch:
        return {"from_evidence": filled, "from_grok": 0, "total": filled}

    # Pass 2: Grok X Search for the rest
    grok_stats = batch_resolve(
        batch,
        output_path,
        api_key=api_key,
        model=model,
        delay_between_calls=delay,
        skip_existing=True,
    )
    return {"from_evidence": filled, "from_grok": grok_stats["total"], **grok_stats}


def _fill_from_existing_evidence(seeds: list[dict], output_path: Path) -> tuple[int, list[dict]]:
    """
    Scan existing intake JSONL files and enrich seeds with:
    - hub_urls: Linktree, Carrd, tipme, easydonate, etc. from creator_links
    - tiktok_urls: direct TikTok links from tiktok_urls field

    Does NOT fill X links (intake files don't contain them directly).
    Seeds enriched here skip the expensive Grok call ONLY if X is already known.
    Otherwise they still go through Grok, but with hub_urls pre-populated.

    Intake format uses youtube_channel_id (UC...) as the key.
    Seeds use platform_id (UC...) — matched via that.

    Returns (count_with_hubs, all_seeds).
    All seeds are returned for Grok; hub-only rows are NOT written to output_path
    (writing empty candidates would make skip_existing skip the Grok pass).
    """
    # Build lookup: UC... → {hub_urls, tiktok_urls, observed_at}
    enrichment: dict[str, dict] = {}

    intake_dir = ROOT / "intake"
    for jsonl_file in sorted(intake_dir.glob("*-youtube-owner-crosslinks*.jsonl")):
        with jsonl_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    channel_id = rec.get("youtube_channel_id", "") or ""
                    if not channel_id or not channel_id.startswith("UC"):
                        continue

                    hub_urls = []
                    for link in rec.get("creator_links", []):
                        url = link if isinstance(link, str) else (link.get("url") or "")
                        if url and _is_hub_url(url):
                            hub_urls.append(url)

                    tiktok_urls = [
                        u for u in rec.get("tiktok_urls", []) if u
                    ]

                    if (hub_urls or tiktok_urls) and channel_id not in enrichment:
                        enrichment[channel_id] = {
                            "hub_urls": hub_urls,
                            "tiktok_urls": tiktok_urls,
                            "source_file": jsonl_file.name,
                            "observed_at": rec.get("observed_at", ""),
                        }
                except Exception:
                    continue

    enriched_count = 0
    enriched_seeds = []
    for seed in seeds:
        uc_id = seed.get("platform_id", "")
        if uc_id and uc_id in enrichment:
            e = enrichment[uc_id]
            seed = dict(seed)  # don't mutate original
            seed["hub_urls"] = e["hub_urls"]
            seed["tiktok_urls"] = e["tiktok_urls"]
            seed["intake_source_file"] = e["source_file"]
            seed["intake_observed_at"] = e["observed_at"]
            enriched_count += 1
        enriched_seeds.append(seed)

    # Hub/TikTok enrichment stays on the seed dict for Grok + later stages.
    # Do not write hub-only records here: empty candidates would skip Grok.
    return enriched_count, enriched_seeds


def _is_hub_url(url: str) -> bool:
    """Return True if the URL is a creator hub page (not X/TikTok/YT directly)."""
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or "").lower()
    HUB_HOSTS = {
        "linktr.ee", "linktree.com",
        "lit.link",
        "carrd.co",
        "bio.link",
        "beacons.ai",
        "taplink.cc",
        "tipme.in.th",
        "easydonate.app",
        "ko-fi.com",
        "vgen.co",
        "fanbox.cc",
        "patreon.com",
    }
    return any(host == h or host.endswith("." + h) for h in HUB_HOSTS)


def _extract_x_from_crosslink(rec: dict) -> Optional[str]:
    """
    Extract X/Twitter URL from a crosslink record.

    Handles actual intake format:
    - creator_links: list of URL strings (hub pages, platform links)
    - tiktok_urls: list (we skip these — not X)
    - Direct fields: x_url, twitter_url, x_handle, twitter_handle
    """
    # 1. Direct fields (future-proofing)
    for field in ("x_url", "twitter_url"):
        val = rec.get(field, "")
        if val and isinstance(val, str) and ("twitter.com" in val or "x.com/" in val):
            return val
    for field in ("x_handle", "twitter_handle"):
        val = rec.get(field, "")
        if val and isinstance(val, str):
            handle = val.lstrip("@")
            if handle:
                return f"https://x.com/{handle}"

    # 2. Scan creator_links list (list of URL strings or dicts)
    for link in rec.get("creator_links", []):
        url = link if isinstance(link, str) else (link.get("url") or "")
        if not url:
            continue
        from urllib.parse import urlparse
        host = (urlparse(url).hostname or "").lower()
        if host in ("x.com", "twitter.com", "www.x.com", "www.twitter.com"):
            path = urlparse(url).path.strip("/")
            # Reject non-handle paths (status, i/flow, etc.)
            if path and "/" not in path and not path.startswith(("i/", "intent/", "share", "home", "explore")):
                return f"https://x.com/{path}"

    return None


# ---------------------------------------------------------------------------
# Stage 2: X → Hub URLs  (Playwright fetch of X profile)
# ---------------------------------------------------------------------------

def run_x_to_hub(
    yt_to_x_path: Path,
    output_path: Path,
    *,
    profile_dir: Optional[Path] = None,
    headless: bool = True,
    min_confidence: str = "medium",
    limit: Optional[int] = None,
) -> dict:
    """
    Stage 2: For each resolved X account, fetch the X profile page and
    extract the website URL + bio links → hub candidates.

    Uses existing hub discovery: registry/pipeline/hubs.py
    Writes output JSONL with x_url, hub_urls, platform_links, status.
    """
    from .hubs import fetch_x_profile_links

    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed = _load_processed_ids(output_path)

    confidence_rank = {"high": 2, "medium": 1, "low": 0}
    min_rank = confidence_rank.get(min_confidence, 1)

    # Collect X accounts to fetch
    targets = []
    with yt_to_x_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                acct_id = rec["youtube_account_id"]
                if acct_id in processed:
                    continue
                for cand in rec.get("candidates", []):
                    rank = confidence_rank.get(cand.get("confidence", "low"), 0)
                    if rank >= min_rank and cand.get("x_url"):
                        targets.append({
                            "youtube_account_id": acct_id,
                            "youtube_name": rec.get("youtube_name", ""),
                            "youtube_url": rec.get("youtube_url", ""),
                            "x_url": cand["x_url"],
                            "x_handle": cand.get("x_handle", ""),
                            "confidence": cand["confidence"],
                        })
                        break  # Take highest-confidence candidate only
            except Exception:
                continue

    if limit:
        targets = targets[:limit]

    print(f"Stage 2: {len(targets)} X profiles to fetch")

    stats = {"total": len(targets), "hub_found": 0, "no_hub": 0, "errors": 0}

    with output_path.open("a", encoding="utf-8") as out:
        for idx, t in enumerate(targets, 1):
            try:
                result = fetch_x_profile_links(
                    t["x_url"],
                    profile_dir=profile_dir,
                    headless=headless,
                )
                if result.get("hub_urls") or result.get("platform_links"):
                    stats["hub_found"] += 1
                else:
                    stats["no_hub"] += 1
                record = {**t, **result, "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            except Exception as exc:
                stats["errors"] += 1
                record = {**t, "status": "error", "error": str(exc),
                          "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()

            if idx % 25 == 0 or idx == len(targets):
                print(f"Stage 2 progress: {idx}/{len(targets)} (found: {stats['hub_found']}, no_hub: {stats['no_hub']}, errors: {stats['errors']})")

    return stats


def _load_processed_targets(jsonl_path: Path) -> set[tuple[str, str]]:
    """Return set of (youtube_account_id, hub_url_or_direct) already in a JSONL file."""
    keys: set[tuple[str, str]] = set()
    if not jsonl_path.exists():
        return keys
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                keys.add((rec.get("youtube_account_id", ""), rec.get("hub_url") or "direct"))
            except Exception:
                continue
    return keys


def _latest_stage2_records(path: Path) -> list[dict]:
    """Last row per youtube_account_id (Stage 2 resume-appends)."""
    latest: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            acct_id = rec.get("youtube_account_id")
            if acct_id:
                latest[acct_id] = rec
    return list(latest.values())


def _canonical_hub_url(url: str) -> str:
    u = (url or "").strip()
    if u.startswith("http://"):
        u = "https://" + u[7:]
    return u.rstrip("/")


# ---------------------------------------------------------------------------
# Stage 3: Hub → All platform links
# ---------------------------------------------------------------------------

def run_hub_to_platforms(
    x_to_hub_path: Path,
    output_path: Path,
    *,
    limit: Optional[int] = None,
    delay: float = 0.25,
    require_x_url: bool = True,
) -> dict:
    """
    Stage 3: Fetch each hub URL and extract all platform account links.
    Also forwards direct platform links found on X profiles to the output.
    Uses latest-wins Stage 2 rows (resume appends do not duplicate crawls).
    """
    from .hubs import crawl_hub

    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed = _load_processed_targets(output_path)

    hub_targets = []
    direct_records = []
    seen_hubs: set[tuple[str, str]] = set()

    for rec in _latest_stage2_records(x_to_hub_path):
        acct_id = rec.get("youtube_account_id")
        if not acct_id:
            continue
        if require_x_url and not rec.get("x_url"):
            continue
        for hub_url in rec.get("hub_urls") or []:
            if not hub_url:
                continue
            canon = _canonical_hub_url(hub_url)
            if not canon:
                continue
            key = (acct_id, canon)
            if key in seen_hubs or (acct_id, canon) in processed or (acct_id, hub_url) in processed:
                continue
            seen_hubs.add(key)
            hub_targets.append({
                "youtube_account_id": acct_id,
                "youtube_name": rec.get("youtube_name", ""),
                "youtube_url": rec.get("youtube_url", ""),
                "x_url": rec.get("x_url", ""),
                "hub_url": canon,
                "source": "hub_crawl",
            })
        direct_links = rec.get("platform_links") or []
        if direct_links and (acct_id, "direct") not in processed:
            direct_records.append({
                "youtube_account_id": acct_id,
                "youtube_name": rec.get("youtube_name", ""),
                "youtube_url": rec.get("youtube_url", ""),
                "x_url": rec.get("x_url", ""),
                "hub_url": None,
                "source": "x_profile_direct",
                "platform_links": direct_links,
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

    direct_written = 0
    if direct_records:
        with output_path.open("a", encoding="utf-8") as out:
            for d in direct_records:
                out.write(json.dumps(d, ensure_ascii=False) + "\n")
                direct_written += 1

    if limit:
        hub_targets = hub_targets[:limit]

    print(f"Stage 3: {direct_written} direct records forwarded, {len(hub_targets)} hubs to crawl")
    stats = {
        "total_hubs": len(hub_targets),
        "direct_forwarded": direct_written,
        "links_found": 0,
        "empty": 0,
        "errors": 0,
    }

    with output_path.open("a", encoding="utf-8") as out:
        for idx, t in enumerate(hub_targets, 1):
            try:
                links = crawl_hub(t["hub_url"])
                stats["links_found"] += len(links)
                if not links:
                    stats["empty"] += 1
                record = {
                    **t,
                    "platform_links": links,
                    "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            except Exception as exc:
                stats["errors"] += 1
                record = {**t, "platform_links": [], "error": str(exc),
                          "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()

            if delay > 0:
                time.sleep(delay)

            if idx % 25 == 0 or idx == len(hub_targets):
                print(
                    f"Stage 3 progress: {idx}/{len(hub_targets)} hubs crawled "
                    f"({stats['links_found']} links found, {stats['empty']} empty, {stats['errors']} errors)"
                )

    return stats


# ---------------------------------------------------------------------------
# Stage 4: Build review proposals
# ---------------------------------------------------------------------------

def run_build_review(
    creator_platform_path: Path,
    output_path: Path,
    data_path: Optional[Path] = None,
) -> dict:
    """
    Stage 4: Load creator platform links, resolve stable IDs,
    match against existing registry accounts, build review proposals.
    """
    from .evidence import build_review_batch

    if data_path is None:
        data_path = ROOT / "data/registry.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with creator_platform_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue

    print(f"Stage 4: Building review proposals from {len(records)} records")
    proposals = build_review_batch(records, data_path)

    output_path.write_text(
        json.dumps(proposals, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "total_records": len(records),
        "proposals": len(proposals.get("changes", [])),
        "output": str(output_path),
    }
