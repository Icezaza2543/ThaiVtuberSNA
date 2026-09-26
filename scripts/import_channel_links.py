"""Reverse-direction discovery: owner-written links in YouTube About descriptions.

Input: %LOCALAPPDATA%/ThaiVtuberSNA/yt_channel_links.jsonl (exported daily by the
census worker; override with --file).

1. Report which domains verified VTuber channels link to (distinct channels per
   domain) — shows which donation/hub platforms the community actually uses.
2. Donation pages linked from a channel's own About are attached to that channel's
   persona (evidence: the owner's YouTube About). Social accounts (X, Twitch, ...)
   are only counted: official-account rules need a two-way cross-link.

Only slug/URL are stored for donation pages; payment details are never read.
Dry-run unless --write. Append only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from import_vtuberthaiinfo_base import Index, sha  # noqa: E402
from migrate_canonical_sheet import Sheet, pad, token, upsert  # noqa: E402

REVIEWER = "auto:youtube-about-crosslink"
MARKER = "youtube_about_links"
SLUG = re.compile(r"^[A-Za-z0-9_.-]{2,40}$")
RESERVED = {"discover", "explore", "login", "signup", "register", "dashboard", "api", "settings", "about",
            "terms", "privacy", "pricing", "help", "docs", "blog", "for", "link", "overlay", "auth"}
# host -> (platform, canonical URL template, path segment index of the slug)
DONATION = {
    "easydonate.app": ("easydonate", "https://easydonate.app/{}"),
    "ezdn.app": ("easydonate", "https://easydonate.app/{}"),
    "tipjai.com": ("tipjai", "https://tipjai.com/{}"),
    "tipnoi.app": ("tipnoi", "https://tipnoi.app/{}"),
    "ko-fi.com": ("kofi", "https://ko-fi.com/{}"),
    "buymeacoffee.com": ("buymeacoffee", "https://buymeacoffee.com/{}"),
    "streamlabs.com": ("streamlabs", "https://streamlabs.com/{}/tip"),
}


def default_file() -> Path:
    base = Path(os.getenv("LOCALAPPDATA") or Path.home() / ".local" / "share")
    return base / "ThaiVtuberSNA" / "yt_channel_links.jsonl"


def donation_account(url: str):
    parts = urlsplit(url)
    host = (parts.hostname or "").lower().removeprefix("www.")
    if host not in DONATION:
        return None
    platform, template = DONATION[host]
    segs = [s for s in parts.path.split("/") if s]
    if not segs:
        return None
    slug = segs[0].lstrip("@")
    if not SLUG.match(slug) or slug.lower() in RESERVED:
        return None
    if platform == "streamlabs" and (len(segs) < 2 or segs[1].lower() != "tip"):
        return None
    return platform, slug.lower(), template.format(slug.lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(default_file()))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(args.file, encoding="utf-8") if l.strip()]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sh = Sheet(token())
    idx = Index(sh)
    status = {pad(r, 12)[0]: pad(r, 12)[8] for r in idx.raw["PERSONAS"] if r}
    persona_of_channel = {}
    for r in idx.raw["ACCOUNTS"]:
        r = pad(r, 14)
        if r[1] == "youtube" and r[2]:
            ps = {p for p in idx.personas_of[r[0]] if status.get(p) == "verified"}
            if len(ps) == 1:
                persona_of_channel[r[2]] = ps.pop()

    domains = defaultdict(set)
    for r in rows:
        domains[r["domain"]].add(r["channel_id"])
    print(f"links {len(rows)} from {len({r['channel_id'] for r in rows})} channels; top domains (distinct channels):")
    for d, chans in sorted(domains.items(), key=lambda kv: -len(kv[1]))[:args.top]:
        tag = " [donation]" if d.removeprefix("www.") in DONATION else ""
        print(f"  {len(chans):5d}  {d}{tag}")

    accounts, links, stats = {}, {}, Counter()
    for r in rows:
        acc = donation_account(r["url"])
        if not acc:
            continue
        platform, slug, url = acc
        stats[f"found_{platform}"] += 1
        pid = persona_of_channel.get(r["channel_id"])
        if not pid:
            stats["no_verified_persona"] += 1
            continue
        a = {"platform": platform, "platform_id": "", "handle": slug}
        aid = idx.account(a)
        if aid:
            owners = {p for p in idx.personas_of[aid] if status.get(p) == "verified"}
            if owners and pid not in owners:
                stats["conflict_other_persona"] += 1
                print(f"  conflict: {url} already linked to {sorted(owners)}; channel {r['channel_id']} -> {pid}")
                continue
            if pid in owners:
                stats["already_linked"] += 1
                continue
        else:
            aid = "acct_" + sha(f"about-account:{platform}:{slug}")
            if aid not in accounts:
                accounts[aid] = [aid, platform, "", slug, slug, url, "persona", "", "unknown", now, now,
                                 "verified", now, now]
                stats[f"new_account_{platform}"] += 1
        lid = "link_" + sha(f"about-link:{aid}:{pid}")
        if (pid, aid) not in idx.links and lid not in links:
            links[lid] = [lid, pid, aid, "official", "", "", f"https://www.youtube.com/channel/{r['channel_id']}/about",
                          "verified", REVIEWER, now, f"{MARKER}; channel={r['channel_id']}; seen={r.get('last_seen')}"]
            stats["new_link"] += 1

    print(json.dumps(dict(stats), indent=1))
    if not args.write:
        print("dry-run")
        return 0
    if accounts:
        print(upsert(sh, "ACCOUNTS", list(accounts.values()), idx.raw["ACCOUNTS"]))
    if links:
        print(upsert(sh, "ACCOUNT_LINKS", list(links.values()), idx.raw["ACCOUNT_LINKS"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
