"""Classify Stage 3 links vs registry and emit Stage 4 review + first-party apply."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from registry.store import PRIMARY, ROOT, uid, utc_timestamp
from registry.identity import verified_account_personas
from registry.urls import extract_handle_from_url, normalize_url

S3 = ROOT / "intake/consolidated/creator-platform-links-2026-09-16.jsonl"
REGISTRY = ROOT / "data/registry.json"
REVIEW_OUT = ROOT / "reviews/pending/creator-link-map-2026-09-16.json"
APPLY_OUT = ROOT / "reviews/pending/creator-link-map-2026-09-16-apply-first-party.json"
STAMP = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

APPLY_PLATFORMS = {
    "youtube", "x", "twitch", "tiktok", "instagram", "facebook",
    "bilibili", "niconico",
    "kick", "ganknow", "linktree", "litlink", "carrd",
    "kofi", "patreon", "vgen",
}
STABLE_REQUIRED = {"youtube", "twitch", "tiktok", "bilibili", "niconico"}
HANDLE_NS = {
    "x": "handle",
    "instagram": "handle",
    "facebook": "handle",
    "kick": "handle",
    "ganknow": "handle",
    "linktree": "handle",
    "litlink": "handle",
    "carrd": "handle",
    "kofi": "handle",
    "patreon": "handle",
    "vgen": "handle",
}

AGENCY_PATTERNS = (
    "upd8", "nijisanji", "hololive", "vspo", "official",
)


def norm_key(platform: str, url: str) -> str | None:
    try:
        return normalize_url(platform, url, validate=False).rstrip("/").casefold()
    except Exception:
        return None


def skip_url(platform: str, url: str) -> str | None:
    path = (urlparse(url).path or "").lower()
    if platform == "website":
        return "website_not_apply"
    if "/watch" in path or "/live" in path or "youtu.be" in url.casefold():
        return "watch_or_live"
    if platform == "facebook" and any(p in path for p in ("/photos", "/posts", "/videos", "/reel")):
        return "fb_content_path"
    if platform == "ganknow" and path.startswith("/post"):
        return "ganknow_post"
    if not url.lower().startswith("https://"):
        if url.lower().startswith("http://"):
            return None
        return "not_http"
    return None


def fb_platform_id(url: str, handle: str | None) -> tuple[str, str] | None:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "id" in qs and qs["id"][0].isdigit():
        return qs["id"][0], "profile_id"
    if handle and handle != "profile.php":
        return handle, "handle"
    return None


def load_registry():
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    tables = payload["tables"]
    accounts = tables["accounts"]
    by_url = {}
    by_handle = {}
    by_id = {}
    for a in accounts:
        by_id[a["id"]] = a
        nk = norm_key(a["platform"], a["url"])
        if nk:
            by_url[(a["platform"], nk)] = a
        h = (a.get("handle") or "").lstrip("@").casefold()
        if h:
            by_handle[(a["platform"], h)] = a
        pid = (a.get("platform_id") or "").casefold()
        if pid:
            by_handle[(a["platform"], pid)] = a
    account_personas = verified_account_personas(tables["personas"], tables["account_links"])
    links = {}
    for link in tables["account_links"]:
        links[(link["persona_id"], link["account_id"])] = link
    verified_personas = {
        p["id"] for p in tables["personas"] if p.get("review_status") == "verified"
    }
    candidates = {}
    for c in tables["candidates"]:
        nk = norm_key(c["platform"], c["url"])
        if nk:
            candidates[(c["platform"], nk)] = c
    return {
        "by_url": by_url,
        "by_handle": by_handle,
        "by_id": by_id,
        "account_personas": account_personas,
        "evidence": {e["id"]: e for e in tables["evidence"]},
        "links": links,
        "verified_personas": verified_personas,
        "candidates": candidates,
    }


def find_account(reg, platform, url, handle):
    nk = norm_key(platform, url)
    if nk and (platform, nk) in reg["by_url"]:
        return reg["by_url"][(platform, nk)]
    h = (handle or extract_handle_from_url(platform, url) or "").lstrip("@").casefold()
    if h and (platform, h) in reg["by_handle"]:
        return reg["by_handle"][(platform, h)]
    return None


def iter_stage3():
    with S3.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def classify():
    reg = load_registry()
    stats = Counter()
    by_plat = defaultdict(Counter)
    high_rows = []  # first-party apply candidates
    review_changes = []
    seen_review = set()

    for rec in iter_stage3():
        source_id = rec.get("source_account_id") or rec.get("youtube_account_id") or ""
        source_account = reg["by_id"].get(source_id)
        source_url = rec.get("source_url") or rec.get("youtube_url") or (source_account or {}).get("url", "")
        source_platform = (source_account or {}).get("platform") or rec.get("source_platform")
        persona_ids = reg["account_personas"].get(source_id, [])
        persona_id = persona_ids[0] if len(persona_ids) == 1 else None
        identity_reason = ("reviewed_source_persona" if persona_id else
                           "ambiguous_source_persona" if persona_ids else "source_persona_needs_review")
        if rec.get("source_platform") and rec["source_platform"] != source_platform:
            persona_id, identity_reason = None, "source_platform_mismatch"
        source_evidence_id = rec.get("source_evidence_id")
        source_evidence = reg["evidence"].get(source_evidence_id)
        x_url = rec.get("x_url") or ""
        hub_url = rec.get("hub_url")
        source = rec.get("source") or ""
        first_party = bool(x_url) and source in {"hub_crawl", "x_profile_direct"}
        if rec.get("source_account_id"):
            # Generic account-first observations need recorded primary evidence.
            # A source label or a matching handle alone is not ownership proof.
            first_party = bool(source_account and source_evidence and
                               source_evidence["kind"] in PRIMARY)

        links = list(rec.get("platform_links") or [])
        # Also treat the Stage 2 official X URL as a target once per creator
        if x_url:
            links.append({
                "platform": "x",
                "url": x_url,
                "handle": extract_handle_from_url("x", x_url),
                "_from_x_field": True,
            })

        for link in links:
            platform = link.get("platform") or ""
            url = link.get("url") or ""
            handle = link.get("handle") or extract_handle_from_url(platform, url)
            if not url or not platform:
                stats["no_url"] += 1
                continue
            if source_platform == platform and source_url and norm_key(platform, url) == norm_key(platform, source_url):
                stats["source_account"] += 1
                continue
            reason = skip_url(platform, url)
            if reason:
                stats[reason] += 1
                by_plat[platform][reason] += 1
                continue
            if platform not in APPLY_PLATFORMS:
                stats["platform_out"] += 1
                continue
            try:
                canon = normalize_url(platform, url, validate=False)
            except Exception:
                stats["bad_url"] += 1
                continue
            existing = find_account(reg, platform, canon, handle)
            already_candidate = bool(reg["candidates"].get((platform, norm_key(platform, canon) or "")))
            already_linked = False
            if existing and persona_id:
                linkrow = reg["links"].get((persona_id, existing["id"]))
                if linkrow:
                    already_linked = linkrow.get("review_status")

            high = first_party and not any(p in (handle or "").lower() for p in ("official",))
            # Official X field is first-party even without hub
            if link.get("_from_x_field") and x_url and not rec.get("source_account_id"):
                high = True

            bucket = "new"
            if existing:
                if already_linked == "verified":
                    bucket = "existing_verified_link"
                elif already_linked:
                    bucket = "existing_unverified_link"
                else:
                    bucket = "existing_account_unlinked"
            elif already_candidate:
                bucket = "existing_candidate"
            elif platform in STABLE_REQUIRED:
                bucket = "needs_stable_id"
            else:
                bucket = "new_handle_account"

            stats[bucket] += 1
            by_plat[platform][bucket] += 1

            key = f"{source_id}|{platform}|{canon.casefold()}|{source_evidence_id or hub_url or x_url or source_url}"
            if key not in seen_review:
                seen_review.add(key)
                review_changes.append({
                    "action": "add_account" if bucket == "new_handle_account" else (
                        "add_candidate" if bucket in {"needs_stable_id", "existing_candidate", "new"} else "add_account_link"
                    ),
                    "platform": platform,
                    "url": canon,
                    "handle": handle,
                    "name": rec.get("source_name") or rec.get("youtube_name") or (source_account or {}).get("name") or handle or "",
                    "confidence": "high" if high else "medium",
                    "bucket": bucket,
                    "source_account_id": source_id,
                    "source_platform": source_platform,
                    "source_url": source_url,
                    "source_evidence_id": source_evidence_id,
                    "observed_at": rec.get("observed_at"),
                    "identity_reason": identity_reason,
                    "persona_id": persona_id,
                    "existing_account_id": existing["id"] if existing else None,
                    "x_url": x_url or None,
                    "hub_url": hub_url,
                    "source": source or ("x_field" if link.get("_from_x_field") else ""),
                    "first_party": high,
                    "needs_human_review": True,
                })

            if high and bucket != "existing_verified_link":
                high_rows.append({
                    "platform": platform,
                    "url": canon,
                    "handle": (handle or "").lstrip("@") or None,
                    "name": rec.get("source_name") or rec.get("youtube_name") or (source_account or {}).get("name") or handle or "",
                    "source_account_id": source_id,
                    "source_platform": source_platform,
                    "source_url": source_url,
                    "source_evidence_id": source_evidence_id,
                    "observed_at": rec.get("observed_at"),
                    "identity_reason": identity_reason,
                    "persona_id": persona_id,
                    "existing": existing,
                    "already_linked": already_linked,
                    "bucket": bucket,
                    "x_url": x_url,
                    "hub_url": hub_url,
                    "source": source or ("x_field" if link.get("_from_x_field") else ""),
                })

    return reg, stats, by_plat, review_changes, high_rows


def resolve_twitch(handle: str) -> str | None:
    try:
        from registry.twitch_public import get_public_twitch_client_id, resolve_public_twitch_user_id
        cid = get_public_twitch_client_id(handle)
        uid_val = resolve_public_twitch_user_id(handle, client_id=cid)
        return str(uid_val) if uid_val else None
    except Exception:
        return None


def resolve_tiktok(handle: str) -> str | None:
    try:
        from registry.discovery.enrich import resolve_tiktok_web_user_id
        uid_val = resolve_tiktok_web_user_id(handle)
        return str(uid_val) if uid_val else None
    except Exception:
        return None


def build_apply(reg, high_rows, *, reviewer=None, reviewed_at=None):
    """Prepare rows; only explicit reviewer decisions may produce verified links.

Without a supplied reviewer and timestamp, proposed links remain needs_evidence.
This function never writes the registry or certifies persona scope.
    """
    if bool(reviewer) != bool(reviewed_at):
        raise ValueError("reviewer and reviewed_at must be supplied together")
    if reviewed_at:
        utc_timestamp(reviewed_at)
    if reviewer is not None and not reviewer.strip():
        raise ValueError("reviewer must not be blank")
    link_status = "verified" if reviewer else "needs_evidence"

    evidence, accounts, links, candidates = [], [], [], []
    skipped = Counter()
    seen = set()
    existing_links = dict(reg["links"])
    existing_acct_keys = {
        (a["platform"], a["id_namespace"], a["platform_id"]): a["id"]
        for a in reg["by_id"].values()
    }

    # Dedupe high rows: prefer hub_crawl over x_profile_direct over x_field per (persona or yt, platform, url)
    best = {}
    rank = {"hub_crawl": 0, "x_profile_direct": 1, "x_field": 2, "": 3}
    for row in high_rows:
        key = (row["source_account_id"], row["platform"], row["url"].casefold())
        prev = best.get(key)
        if prev is None or rank.get(row["source"], 9) < rank.get(prev["source"], 9):
            best[key] = row
    rows = list(best.values())

    resolve_needed = [
        r for r in rows
        if r["existing"] is None and r["platform"] in {"twitch", "tiktok"} and r["handle"]
    ]
    print(f"resolving stable ids for {len(resolve_needed)} twitch/tiktok handles...")
    resolved = {}
    for i, row in enumerate(resolve_needed, 1):
        h = row["handle"]
        key = (row["platform"], h.casefold())
        if key in resolved:
            continue
        if row["platform"] == "twitch":
            resolved[key] = resolve_twitch(h)
        else:
            resolved[key] = resolve_tiktok(h)
        if i % 25 == 0 or i == len(resolve_needed):
            ok = sum(1 for v in resolved.values() if v)
            print(f"  resolve {i}/{len(resolve_needed)} ok={ok}")

    for row in rows:
        platform = row["platform"]
        url = row["url"]
        handle = row["handle"]
        persona_id = row["persona_id"]
        existing = row["existing"]
        source_evidence_id = row.get("source_evidence_id")
        retained_evidence = reg["evidence"].get(source_evidence_id)
        observation_time = (retained_evidence or {}).get("observed_at") or row.get("observed_at")
        if not observation_time:
            skipped["missing_observation_time"] += 1
            continue
        utc_timestamp(observation_time)
        if reviewed_at and utc_timestamp(reviewed_at) < utc_timestamp(observation_time):
            raise ValueError("Review predates its evidence observation")
        ev_url = ((retained_evidence or {}).get("url") or row["hub_url"] or
                  row["x_url"] or row["source_url"] or url)
        if not str(ev_url).startswith("https://"):
            ev_url = url
        if not url.startswith("https://"):
            skipped["url_not_https"] += 1
            continue

        platform_id = None
        id_namespace = None
        if existing:
            acct_id = existing["id"]
            platform_id = existing["platform_id"]
            id_namespace = existing["id_namespace"]
        elif platform in STABLE_REQUIRED:
            pid = resolved.get((platform, (handle or "").casefold()))
            namespace = {"twitch": "user_id", "tiktok": "web_user_id",
                         "youtube": "channel_id", "bilibili": "uid", "niconico": "user_id"}[platform]
            parsed = urlparse(url)
            pattern = {"youtube": r"/channel/(UC[A-Za-z0-9_-]{22})/?",
                       "bilibili": r"/(\d+)/?", "niconico": r"/user/(\d+)/?"}.get(platform)
            match = re.fullmatch(pattern, parsed.path) if pattern else None
            if match and (platform != "bilibili" or parsed.hostname == "space.bilibili.com"):
                pid = match[1]
            if not pid:
                skipped["unresolved_stable_id"] += 1
                # keep as candidate
                cid = uid("candidate", f"{platform}:{url.rstrip('/')}")
                if cid in seen:
                    continue
                seen.add(cid)
                ev_id = uid("ev", f"cand|{platform}|{url}")
                if ev_id not in seen:
                    seen.add(ev_id)
                    evidence.append({
                        "id": ev_id,
                        "url": ev_url,
                        "kind": "official_profile",
                        "observed_at": observation_time,
                        "published_on": None,
                        "sha256": None,
                        "summary": (
                            f"First-party {row['source']} from {row['source_url']} "
                            f"via {row['x_url']} to {platform} {url}; stable ID not resolved."
                        ),
                    })
                candidates.append({
                    "id": cid,
                    "platform": platform,
                    "platform_id": None,
                    "id_namespace": None,
                    "name": row["name"] or handle or url,
                    "url": url,
                    "review_status": "needs_evidence",
                    "account_id": None,
                    "evidence_id": source_evidence_id if retained_evidence else ev_id,
                    "reviewer": None,
                    "reviewed_at": None,
                })
                continue
            platform_id = pid
            id_namespace = namespace
        elif platform == "facebook":
            pair = fb_platform_id(url, handle)
            if not pair:
                skipped["fb_no_id"] += 1
                continue
            platform_id, id_namespace = pair
        else:
            if not handle:
                skipped["no_handle"] += 1
                continue
            platform_id = handle
            id_namespace = HANDLE_NS[platform]

        if not existing:
            key = (platform, id_namespace, platform_id)
            if key in existing_acct_keys:
                acct_id = existing_acct_keys[key]
                existing = {"id": acct_id}
            else:
                acct_id = uid("acct", f"{platform}:{id_namespace}:{platform_id}")
                ev_id = uid("ev", f"{row['source_account_id']}|{platform}|{platform_id}|{url}")
                if acct_id in seen:
                    skipped["dup_acct"] += 1
                    continue
                seen.add(acct_id)
                seen.add(ev_id)
                evidence.append({
                    "id": ev_id,
                    "url": ev_url,
                    "kind": "official_profile",
                    "observed_at": observation_time,
                    "published_on": None,
                    "sha256": None,
                    "summary": (
                        f"First-party {row['source'] or 'x_profile'} chain "
                        f"{row['source_url']} → {row['x_url']}"
                        + (f" → {row['hub_url']}" if row["hub_url"] else "")
                        + f" → {platform} {url}."
                    ),
                })
                accounts.append({
                    "id": acct_id,
                    "platform": platform,
                    "platform_id": platform_id,
                    "id_namespace": id_namespace,
                    "handle": handle,
                    "name": row["name"] or handle or platform_id,
                    "url": url,
                    "first_discovered_at": observation_time,
                    "evidence_id": source_evidence_id if retained_evidence else ev_id,
                })
                existing_acct_keys[key] = acct_id
        else:
            acct_id = existing["id"]
            ev_id = uid("ev", f"{row['source_account_id']}|link|{acct_id}|{url}")
            if ev_id not in seen:
                seen.add(ev_id)
                evidence.append({
                    "id": ev_id,
                    "url": ev_url,
                    "kind": "official_profile",
                    "observed_at": observation_time,
                    "published_on": None,
                    "sha256": None,
                    "summary": (
                        f"First-party {row['source'] or 'x_profile'} chain "
                        f"{row['source_url']} → {row['x_url']}"
                        + (f" → {row['hub_url']}" if row["hub_url"] else "")
                        + f" → existing {platform} account {url}."
                    ),
                })

        if not persona_id or persona_id not in reg["verified_personas"]:
            skipped[row.get("identity_reason") or "source_persona_needs_review"] += 1
            continue
        prev = existing_links.get((persona_id, acct_id))
        if prev and prev.get("review_status") == "verified":
            skipped["already_verified_link"] += 1
            continue
        link_id = prev["id"] if prev else uid("link", f"{persona_id}|{acct_id}")
        if (not prev) and link_id in seen:
            continue
        seen.add(link_id)
        links.append({
            "id": link_id,
            "account_id": acct_id,
            "persona_id": persona_id,
            "valid_from": None,
            "valid_to": None,
            "evidence_id": source_evidence_id if retained_evidence else ev_id,
            "review_status": link_status,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
        })
        existing_links[(persona_id, acct_id)] = {
            "id": link_id,
            "review_status": link_status,
        }

    # Reuse retained primary evidence. Never restamp a stored observation as a
    # fresh visit, and omit generated evidence rows that no proposal references.
    used_evidence = {row["evidence_id"] for row in accounts + links + candidates}
    evidence = [ev for ev in evidence if ev["id"] in used_evidence]
    payload = {
        "evidence": evidence,
        "accounts": accounts,
        "account_links": links,
        "candidates": candidates,
    }
    return payload, skipped


def main():
    print("classifying Stage 3 vs registry...")
    reg, stats, by_plat, review_changes, high_rows = classify()
    print("classify", dict(stats))
    print("by_platform")
    for plat, c in sorted(by_plat.items()):
        print(f"  {plat}: {dict(c)}")

    high_fp = [c for c in review_changes if c.get("first_party")]
    review = {
        "version": 1,
        "generated_at": STAMP.replace("+00:00", "Z"),
        "source_pipeline": "creator-link-pipeline",
        "source_file": str(S3.as_posix()),
        "stats": {
            "total_changes": len(review_changes),
            "high_confidence": sum(1 for c in review_changes if c["confidence"] == "high"),
            "medium_confidence": sum(1 for c in review_changes if c["confidence"] == "medium"),
            "first_party": len(high_fp),
            "buckets": dict(Counter(c["bucket"] for c in review_changes)),
            "platforms": dict(Counter(c["platform"] for c in review_changes)),
        },
        "changes": review_changes,
    }
    REVIEW_OUT.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", REVIEW_OUT, "changes", len(review_changes), "stats", review["stats"])

    payload, skipped = build_apply(reg, high_rows)
    APPLY_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", APPLY_OUT)
    print(
        "apply evidence", len(payload["evidence"]),
        "accounts", len(payload["accounts"]),
        "links", len(payload["account_links"]),
        "candidates", len(payload["candidates"]),
    )
    print("apply skipped", dict(skipped))
    print("apply accounts by platform", dict(Counter(a["platform"] for a in payload["accounts"])))
    print("apply links by... count", len(payload["account_links"]))


if __name__ == "__main__":
    main()
