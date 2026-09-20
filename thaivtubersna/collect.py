"""
Step 1 — COLLECT
================
Discovers new Thai VTubers and collects platform profiles.

Entry points used by the worker:
    collect.discover()           — crawl directories / hubs for new leads
    collect.collect_accounts()   — fetch profile data for known accounts

All writes go to the DuckDB store via store.upsert().
No private data (viewer hashes, login tokens, etc.) is stored here.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from uuid import uuid4

from .store import PLATFORMS, connect, count, fetch_all, uid, upsert, utc_now

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]

# ── Helpers ─────────────────────────────────────────────────────────────────

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http_get(url: str, *, timeout: int = 20, headers: dict | None = None) -> bytes:
    opener = build_opener(_NoRedirect())
    req = Request(url, headers=headers or {})
    with opener.open(req, timeout=timeout) as resp:
        return resp.read()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# ── Discovery sources ────────────────────────────────────────────────────────

def discover_from_vtuberthai(con, *, max_pages: int = 10, delay: float = 1.0) -> dict:
    """
    Crawl vtuberthai.com directory for new creator leads.
    Returns a summary of candidates added.
    """
    from urllib.request import urlopen
    import html

    base = "https://vtuberthai.com"
    added = 0
    pages = 0
    timestamp = _now()
    run_id = "run_" + uuid4().hex
    upsert(con, "discovery_runs", {
        "id": run_id,
        "platform": "youtube",
        "method": "playwright_search",
        "query": "vtuberthai.com directory",
        "observed_at": timestamp,
        "stop_reason": "page_limit",
        "pages": 0,
        "records_seen": 0,
    })

    # Simple HTTP fetch; Playwright not required for the basic listing
    try:
        raw = _http_get(base + "/creators", timeout=30)
        text = raw.decode("utf-8", errors="replace")
        # Extract YouTube channel URLs from the directory
        yt_pattern = re.compile(r'youtube\.com/channel/(UC[A-Za-z0-9_-]{22})', re.I)
        found = set(yt_pattern.findall(text))
        for channel_id in found:
            url = f"https://www.youtube.com/channel/{channel_id}"
            # Skip if already in accounts
            existing = con.execute(
                "SELECT 1 FROM accounts WHERE platform='youtube' AND platform_id=?",
                [channel_id]
            ).fetchone()
            if existing:
                continue
            ev_id = uid("ev", run_id + url)
            upsert(con, "evidence", {
                "id": ev_id,
                "url": base + "/creators",
                "kind": "secondary_source",
                "observed_at": timestamp,
                "published_on": None,
                "sha256": None,
                "summary": "Found in vtuberthai.com creator directory.",
            })
            cid = uid("candidate", "youtube:" + channel_id)
            existing_c = con.execute("SELECT 1 FROM candidates WHERE id=?", [cid]).fetchone()
            if not existing_c:
                upsert(con, "candidates", {
                    "id": cid,
                    "platform": "youtube",
                    "platform_id": channel_id,
                    "id_namespace": "channel_id",
                    "name": channel_id,
                    "url": url,
                    "review_status": "needs_evidence",
                    "account_id": None,
                    "evidence_id": ev_id,
                    "reviewer": None,
                    "reviewed_at": None,
                })
                added += 1
        pages = 1
        upsert(con, "discovery_runs", {
            "id": run_id,
            "platform": "youtube",
            "method": "playwright_search",
            "query": "vtuberthai.com directory",
            "observed_at": timestamp,
            "stop_reason": "end_of_results",
            "pages": pages,
            "records_seen": len(found),
        })
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        logger.warning("vtuberthai.com fetch failed: %s", exc)
        upsert(con, "discovery_runs", {
            "id": run_id,
            "platform": "youtube",
            "method": "playwright_search",
            "query": "vtuberthai.com directory",
            "observed_at": timestamp,
            "stop_reason": "http_error",
            "pages": 0,
            "records_seen": 0,
        })

    return {"run_id": run_id, "candidates_added": added}


def discover_from_twitch(con, *, max_pages: int = 5, language: str = "th") -> dict:
    """
    Use Twitch Helix API to discover Thai-language streamers.
    Requires TWITCH_CLIENT_ID and TWITCH_ACCESS_TOKEN env vars.
    """
    import os

    client_id = os.getenv("TWITCH_CLIENT_ID")
    token = os.getenv("TWITCH_ACCESS_TOKEN")
    if not client_id or not token:
        logger.info("Twitch credentials not set; skipping Twitch discovery")
        return {"skipped": True, "reason": "no_credentials"}

    if not re.fullmatch(r"[a-z]{2}|other", language):
        raise ValueError("Use a supported language code")

    headers = {"Client-Id": client_id, "Authorization": f"Bearer {token}"}
    timestamp = _now()
    run_id = "run_" + uuid4().hex
    upsert(con, "discovery_runs", {
        "id": run_id,
        "platform": "twitch",
        "method": "twitch_helix",
        "query": f"language={language}",
        "observed_at": timestamp,
        "stop_reason": "page_limit",
        "pages": 0,
        "records_seen": 0,
    })

    cursor = ""
    seen: set[str] = set()
    added = 0

    for _ in range(max_pages):
        params: dict[str, Any] = {"language": language, "first": 100}
        if cursor:
            params["after"] = cursor
        try:
            raw = _http_get(
                "https://api.twitch.tv/helix/streams?" + urlencode(params),
                headers=headers,
            )
            page = json.loads(raw)
        except (HTTPError, URLError, TimeoutError):
            upsert(con, "discovery_runs", {
                "id": run_id, "platform": "twitch", "method": "twitch_helix",
                "query": f"language={language}", "observed_at": timestamp,
                "stop_reason": "http_error",
                "pages": len(seen) // 100, "records_seen": len(seen),
            })
            break

        for stream in page.get("data", []):
            broadcaster_id = stream["user_id"]
            if broadcaster_id in seen:
                continue
            seen.add(broadcaster_id)
            url = "https://www.twitch.tv/" + stream["user_login"]
            existing = con.execute(
                "SELECT 1 FROM accounts WHERE platform='twitch' AND platform_id=?",
                [broadcaster_id]
            ).fetchone()
            if existing:
                continue
            ev_id = uid("ev", run_id + url)
            upsert(con, "evidence", {
                "id": ev_id, "url": url, "kind": "platform_observation",
                "observed_at": timestamp, "published_on": None, "sha256": None,
                "summary": "Live Thai-language Twitch stream observed via Helix API.",
            })
            cid = uid("candidate", "twitch:user_id:" + broadcaster_id)
            if not con.execute("SELECT 1 FROM candidates WHERE id=?", [cid]).fetchone():
                upsert(con, "candidates", {
                    "id": cid, "platform": "twitch",
                    "platform_id": broadcaster_id, "id_namespace": "user_id",
                    "name": stream["user_name"], "url": url,
                    "review_status": "needs_evidence",
                    "account_id": None, "evidence_id": ev_id,
                    "reviewer": None, "reviewed_at": None,
                })
                added += 1

        cursor = page.get("pagination", {}).get("cursor", "")
        if not cursor:
            break

    upsert(con, "discovery_runs", {
        "id": run_id, "platform": "twitch", "method": "twitch_helix",
        "query": f"language={language}", "observed_at": timestamp,
        "stop_reason": "end_of_results" if not cursor else "page_limit",
        "pages": len(seen) // 100 + 1, "records_seen": len(seen),
    })

    return {"run_id": run_id, "seen": len(seen), "candidates_added": added}


# ── Public entry points ──────────────────────────────────────────────────────

def discover(db_path=None) -> dict:
    """
    Step 1a: Discover new VTuber leads from directories.
    Writes candidate rows into DuckDB.
    Returns a summary dict.
    """
    from .store import DB_PATH, connect
    path = db_path or DB_PATH

    results: dict[str, Any] = {}
    with connect(path) as con:
        try:
            results["vtuberthai"] = discover_from_vtuberthai(con)
        except Exception as exc:
            logger.warning("vtuberthai discovery error: %s", exc)
            results["vtuberthai"] = {"error": str(exc)}
        try:
            results["twitch"] = discover_from_twitch(con)
        except Exception as exc:
            logger.warning("twitch discovery error: %s", exc)
            results["twitch"] = {"error": str(exc)}
        from .store import set_state
        set_state(con, "last_discover_at", utc_now())
    return results


def collect_accounts(db_path=None) -> dict:
    """
    Step 1b: Fetch public profile data for accounts already in the registry.
    Currently a stub — to be extended with YouTube Data API / Twitch Helix calls
    that update account metadata (subscriber_count, last_activity, etc.).
    """
    from .store import DB_PATH, connect, set_state
    path = db_path or DB_PATH

    with connect(path) as con:
        n_accounts = con.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        set_state(con, "last_collect_at", utc_now())

    logger.info("collect_accounts: %d accounts in registry (metadata refresh stub)", n_accounts)
    return {"accounts_in_registry": n_accounts, "refreshed": 0}


def run(db_path=None) -> dict:
    """Run both discover and collect_accounts in sequence."""
    d = discover(db_path)
    c = collect_accounts(db_path)
    return {"discover": d, "collect": c}
