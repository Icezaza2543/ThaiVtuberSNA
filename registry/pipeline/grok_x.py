"""YouTube → X/Twitter identity resolution via xAI Grok API with X Search.

Architecture:
  1. Free pass: scan existing intake JSONL evidence (zero cost)
  2. For remaining accounts: call Grok API with live X Search tool
     - targeted query per account (YouTube name + handle + channel URL)
     - Grok returns 1-3 candidates with evidence JSON (structured output)
  3. Our code verifies each candidate independently (no extra Grok call)

Cost note (effective 2026-09-21):
  - $10 / 1,000 user profiles fetched
  - $5  / 1,000 posts fetched
  Use `mode="user"` search + targeted query to minimise profile fetches.
  Estimated cost for ~1,400 uncovered accounts: ~$14 (1 profile each).

API endpoint: https://api.x.ai/v1/chat/completions  (OpenAI-compatible)
Auth: Bearer token from XAI_API_KEY environment variable.

Grok model used: grok-4.3  (low reasoning effort, function calling, structured output)
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XAI_API_BASE = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-4.3"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds (doubles on each retry)

# Search limits to control cost
MAX_PROFILES_PER_ACCOUNT = 1  # 1 targeted profile lookup per YouTube channel
MAX_SEARCH_RESULTS = 3        # Grok returns up to 3 candidates

# Confidence thresholds (Grok self-reported; verified independently)
AUTO_VERIFY_THRESHOLD = "high"   # high confidence → go straight to verification
MANUAL_REVIEW_THRESHOLD = "medium"  # medium → store as candidate


# ---------------------------------------------------------------------------
# Structured output schema for Grok's response
# ---------------------------------------------------------------------------

X_CANDIDATE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "x_candidate_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "candidates": {
                    "type": "array",
                    "description": "Up to 3 X/Twitter accounts that may be official accounts for this YouTube channel, ordered by confidence",
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "properties": {
                            "x_url": {
                                "type": "string",
                                "description": "Canonical X profile URL, e.g. https://x.com/handle"
                            },
                            "x_handle": {
                                "type": "string",
                                "description": "X handle without @ prefix"
                            },
                            "confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "high=explicit cross-link; medium=bio/name match; low=keyword only"
                            },
                            "evidence": {
                                "type": "array",
                                "description": "Specific, verifiable evidence statements linking this X to the YouTube channel",
                                "items": {"type": "string"},
                                "minItems": 1
                            }
                        },
                        "required": ["x_url", "x_handle", "confidence", "evidence"],
                        "additionalProperties": False
                    }
                },
                "search_exhausted": {
                    "type": "boolean",
                    "description": "True if no confident candidates found after thorough search"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes about ambiguity or why search was inconclusive"
                }
            },
            "required": ["candidates", "search_exhausted"],
            "additionalProperties": False
        }
    }
}


# ---------------------------------------------------------------------------
# System prompt (controls Grok behaviour)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a research assistant helping verify official cross-platform presence for Thai virtual creators (VTubers and virtual personas).

Your task:
1. Search X (formerly Twitter) for the official X account of a YouTube channel
2. Return ONLY accounts where there is verifiable evidence linking them to the YouTube channel
3. Evidence must be specific and checkable, e.g.:
   - "X bio contains a link to this YouTube channel URL"
   - "YouTube About page links to this X account"
   - "Pinned tweet announces the YouTube channel"
   - "Both accounts link to the same Linktree/Carrd page which contains both"
4. Do NOT infer identity from similar names, similar avatar, similar content style
5. A virtual persona's physical identity is NOT relevant and must NOT be inferred
6. Agency/group accounts (like talent agencies) must NOT be returned as individual creator accounts
7. Return at most 3 candidates ordered by confidence. Return 0 if not found.
8. Set search_exhausted=true only if you searched and found nothing credible.

IMPORTANT: "confidence=high" requires an explicit cross-link verifiable via URL. Do not use "high" for name similarity alone."""

# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def get_api_key() -> str:
    key = os.environ.get("XAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "XAI_API_KEY environment variable is not set. "
            "Set it with: $env:XAI_API_KEY='xai-...'"
        )
    return key


def _call_grok(payload: dict, api_key: str, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Send one request to xAI /v1/chat/completions and return parsed JSON response."""
    url = f"{XAI_API_BASE}/chat/completions"
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call_with_retry(payload: dict, api_key: str, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Call Grok API with exponential backoff on rate limit / server errors."""
    delay = RETRY_DELAY
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            return _call_grok(payload, api_key, timeout)
        except HTTPError as exc:
            last_exc = exc
            if exc.code == 429 or exc.code >= 500:
                time.sleep(delay)
                delay *= 2
                continue
            raise  # 4xx that are not 429: don't retry
        except Exception as exc:
            last_exc = exc
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"Grok API call failed after {MAX_RETRIES} retries") from last_exc


# ---------------------------------------------------------------------------
# Core resolution function
# ---------------------------------------------------------------------------

def resolve_x_for_youtube_account(
    youtube_name: str,
    youtube_handle: str,
    youtube_url: str,
    *,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """
    Ask Grok to find the official X account for a YouTube channel.

    Returns a dict matching X_CANDIDATE_SCHEMA['json_schema']['schema']:
    {
        "candidates": [
            {
                "x_url": "https://x.com/...",
                "x_handle": "...",
                "confidence": "high"|"medium"|"low",
                "evidence": ["...", ...]
            }
        ],
        "search_exhausted": bool,
        "notes": str | None
    }
    """
    if api_key is None:
        api_key = get_api_key()

    # Build targeted user query
    handle_clean = youtube_handle.lstrip("@")
    user_message = (
        f"Find the official X (Twitter) account for this YouTube channel:\n"
        f"- Channel name: {youtube_name}\n"
        f"- YouTube handle: @{handle_clean}\n"
        f"- YouTube URL: {youtube_url}\n\n"
        f"Search X for this creator and return their official X account if you can verify it. "
        f"Prioritise searching by handle '{handle_clean}' on X first, then by channel name."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "tools": [{"type": "x_search"}],  # xAI X Search tool
        "tool_choice": "auto",
        "response_format": X_CANDIDATE_SCHEMA,
        "max_tokens": 1024,
    }

    response = _call_with_retry(payload, api_key, timeout)

    # Extract content from first choice
    try:
        content = response["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unexpected Grok response format: {response}") from exc

    # Normalise x_url (ensure https://x.com/ prefix, not twitter.com)
    for candidate in result.get("candidates", []):
        url = candidate.get("x_url", "")
        if "twitter.com" in url:
            handle = candidate.get("x_handle", "")
            if handle:
                candidate["x_url"] = f"https://x.com/{handle.lstrip('@')}"

    return result


# ---------------------------------------------------------------------------
# Batch processing with JSONL output
# ---------------------------------------------------------------------------

def batch_resolve(
    accounts: list[dict],
    output_path,
    *,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    delay_between_calls: float = 0.5,
    skip_existing: bool = True,
) -> dict:
    """
    Process a list of YouTube accounts through Grok X Search.

    Each account dict must have: youtube_account_id, name, handle, url

    Appends one JSONL record per account to output_path.
    Returns summary stats: {total, resolved_high, resolved_medium, unresolved, errors}

    With skip_existing=True, skips accounts already in output_path (resume support).
    """
    import pathlib

    if api_key is None:
        api_key = get_api_key()

    output_path = pathlib.Path(output_path)

    # Build set of already-processed account IDs for resume
    processed_ids: set[str] = set()
    if skip_existing and output_path.exists():
        with output_path.open("r", encoding="utf-8") as f:
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
                if rec.get("x_url") or any(c.get("x_url") for c in rec.get("candidates") or []):
                    processed_ids.add(acct_id)

    stats = {"total": 0, "resolved_high": 0, "resolved_medium": 0, "unresolved": 0, "errors": 0}

    with output_path.open("a", encoding="utf-8") as out:
        for account in accounts:
            acct_id = account.get("youtube_account_id") or account.get("id", "")
            name = account.get("name", "")
            handle = account.get("handle", "") or account.get("url", "")
            url = account.get("url", "")

            if acct_id in processed_ids:
                continue

            stats["total"] += 1
            observed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            try:
                result = resolve_x_for_youtube_account(
                    youtube_name=name,
                    youtube_handle=handle,
                    youtube_url=url,
                    api_key=api_key,
                    model=model,
                )

                # Classify result
                high = [c for c in result.get("candidates", []) if c["confidence"] == "high"]
                medium = [c for c in result.get("candidates", []) if c["confidence"] == "medium"]
                if high:
                    stats["resolved_high"] += 1
                elif medium:
                    stats["resolved_medium"] += 1
                else:
                    stats["unresolved"] += 1

                record = {
                    "youtube_account_id": acct_id,
                    "youtube_name": name,
                    "youtube_handle": handle,
                    "youtube_url": url,
                    "observed_at": observed_at,
                    "source": "grok_x_search",
                    "model": model,
                    **result,
                }
                if account.get("hub_urls"):
                    record["hub_urls_from_intake"] = account["hub_urls"]
                if account.get("tiktok_urls"):
                    record["tiktok_urls_from_intake"] = account["tiktok_urls"]

            except Exception as exc:
                stats["errors"] += 1
                record = {
                    "youtube_account_id": acct_id,
                    "youtube_name": name,
                    "youtube_handle": handle,
                    "youtube_url": url,
                    "observed_at": observed_at,
                    "source": "grok_x_search",
                    "model": model,
                    "error": str(exc),
                    "candidates": [],
                    "search_exhausted": False,
                }

            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            processed_ids.add(acct_id)

            if delay_between_calls > 0:
                time.sleep(delay_between_calls)

    return stats


# ---------------------------------------------------------------------------
# Local verification (no Grok call — our code verifies the candidate)
# ---------------------------------------------------------------------------

def verify_x_candidate(candidate: dict, youtube_url: str, existing_html: Optional[str] = None) -> dict:
    """
    Verify an X candidate from Grok without making another Grok call.

    Checks:
    1. x_url is a valid X/Twitter profile URL
    2. If existing_html provided (from YouTube About page): check if x_url is linked there
    3. Returns verification_status: "verified" | "unverified" | "rejected"

    This is pure Python — no network call. Callers fetch HTML separately if needed.
    """
    from urllib.parse import urlparse
    from .urls import normalize_url

    x_url = candidate.get("x_url", "")
    status = "unverified"
    reasons = []

    # Basic URL validation
    try:
        parsed = urlparse(x_url)
        host = (parsed.hostname or "").lower()
        if host not in ("x.com", "twitter.com", "www.x.com", "www.twitter.com"):
            return {**candidate, "verification_status": "rejected", "rejection_reason": "Not an X/Twitter URL"}
        # Normalise to x.com
        x_url = normalize_url("x", x_url, validate=False)
        candidate = {**candidate, "x_url": x_url}
    except Exception:
        return {**candidate, "verification_status": "rejected", "rejection_reason": "Invalid URL"}

    # Check if YouTube About page links to this X
    if existing_html:
        x_handle = candidate.get("x_handle", "").lower()
        html_lower = existing_html.lower()
        if x_url.lower() in html_lower:
            status = "verified"
            reasons.append("YouTube About page contains exact X URL")
        elif x_handle and f"twitter.com/{x_handle}" in html_lower:
            status = "verified"
            reasons.append("YouTube About page links to twitter.com/{handle}")
        elif x_handle and f"x.com/{x_handle}" in html_lower:
            status = "verified"
            reasons.append("YouTube About page links to x.com/{handle}")

    # Check if YouTube URL appears in evidence (self-reporting)
    yt_url_clean = youtube_url.rstrip("/").lower()
    for ev in candidate.get("evidence", []):
        if yt_url_clean in ev.lower():
            reasons.append(f"Evidence mentions YouTube URL: {ev}")

    if not reasons and candidate.get("confidence") == "high":
        # High confidence from Grok but we couldn't verify locally → unverified (needs hub check)
        status = "unverified"

    return {
        **candidate,
        "x_url": x_url,
        "verification_status": status,
        "local_verification_reasons": reasons,
    }
