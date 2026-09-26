"""Apply reviewed donation-page research files to ThaiVtuber_DATA.

Supports EasyDonate (intake/consolidated/easydonate-links-*.jsonl) and Tipjai
(tipjai-candidates-*.jsonl); the platform is detected from the file.
YouTube links without a channel ID (@handle, /c/, /user/) are resolved to the
stable UC… ID from the public channel page (no API quota) before matching.

Owner decision 2026-09-26: an EasyDonate page's own social button to a stable-ID
account is accepted evidence for attaching that EasyDonate page (and the linked
accounts) to the persona owning that account.

- MATCH_EXISTING: add easydonate account + link to the matched persona (re-checked live).
- NEW / NEED_REVIEW with stable-ID accounts and a VTuber self-description: create
  a persona, reuse existing accounts by stable ID, add missing ones, link all.
- NO_EVIDENCE and SKIP slugs are not written.
Only slug/URL are stored for EasyDonate; payment data is never read.
Dry-run unless --write. Append/update only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from import_vtuberthaiinfo_base import Index, sha  # noqa: E402
from migrate_canonical_sheet import Sheet, token, upsert  # noqa: E402

REVIEWER = "owner:easydonate-2026-09-26"
MARKER = "easydonate_links"
SKIP = {"hoshisaki_lyn"}  # current page conflicts with earlier owner cross-link; possible recycled slug
URLS = {"youtube": "https://www.youtube.com/channel/{}", "x": "https://x.com/{}",
        "twitch": "https://www.twitch.tv/{}", "easydonate": "https://easydonate.app/{}",
        "tipjai": "https://tipjai.com/{}",
        "facebook": "https://www.facebook.com/profile.php?id={}", "instagram": "https://www.instagram.com/{}"}


CANONICAL_UC = re.compile(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[A-Za-z0-9_-]{22})"')
_yt_cache: dict[str, str | None] = {}


def resolve_youtube(url: str) -> str | None:
    """@handle / custom URL -> UC channel ID via the public channel page (no API quota)."""
    m = re.search(r"/channel/(UC[A-Za-z0-9_-]{22})", url or "")
    if m:
        return m.group(1)
    if not re.search(r"youtube\.com/(@|c/|user/)", url or ""):
        return None
    base = url.split("?")[0].rstrip("/")
    base = re.sub(r"/(videos|streams|shorts|featured|about|live)$", "", base)
    if base not in _yt_cache:
        try:
            r = requests.get(base, timeout=20, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en"},
                             cookies={"CONSENT": "YES+1"})
            m = CANONICAL_UC.search(r.text) if r.status_code == 200 else None
            _yt_cache[base] = m.group(1) if m else None
        except requests.RequestException:
            _yt_cache[base] = None
        time.sleep(0.5)
    return _yt_cache[base]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default=str(ROOT / "intake/consolidated/easydonate-links-2026-09-26.jsonl"))
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--include-need-review", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = [json.loads(l) for l in open(args.file, encoding="utf-8") if l.strip()]
    platform = "tipjai" if any("tipjai_url" in r for r in rows) else "easydonate"
    marker = f"{platform}_links"
    reviewer = f"owner:{platform}-2026-09-26"
    resolved = 0
    for r in rows:
        for a in r.get("official_accounts", []):
            if a.get("platform") == "youtube" and not a.get("platform_id"):
                uc = resolve_youtube(a.get("url", ""))
                if uc:
                    a["platform_id"], resolved = uc, resolved + 1
    sh = Sheet(token())
    idx = Index(sh)
    personas, accounts, links, log = {}, {}, {}, []

    def account(platform, pid, name):
        # Handle-only platforms follow the sheet convention: empty platform_id, handle in its own column.
        # Facebook: numeric profile id -> platform_id; page name -> handle.
        by_handle = platform in ("x", "easydonate", "tipjai", "instagram") or (platform == "facebook" and not pid.isdigit())
        url = "https://www.facebook.com/" + pid if platform == "facebook" and by_handle else URLS[platform].format(pid)
        a = {"platform": platform, "platform_id": "" if by_handle else pid, "handle": pid.lower() if by_handle else ""}
        aid = idx.account(a)
        if not aid:
            aid = "acct_" + sha(f"ezdn-account:{platform}:{a['handle'] or pid}")
            accounts[aid] = [aid, platform, a["platform_id"], pid if by_handle else "", name,
                             url, "persona", "", "unknown", now, now, "verified", now, now]
        return aid

    def link(pid, aid, src, note):
        if (pid, aid) in idx.links:
            return
        lid = "link_" + sha(f"ezdn-link:{aid}:{pid}")
        links[lid] = [lid, pid, aid, "official", "", "", src, "verified", reviewer, now, f"{marker}; {note}"]

    for r in rows:
        slug, cls = r["slug"], r["match"]
        stable = [a for a in r["official_accounts"] if a.get("platform_id") and a["platform"] in URLS]
        if cls == "NEED_REVIEW" and not args.include_need_review:
            log.append(f"SKIP {slug}: NEED_REVIEW (pass --include-need-review after owner decision)")
            continue
        if slug in SKIP or not stable:
            continue
        # NO_EVIDENCE qualifies only when scope was established (virtual + Thai signals) and the
        # missing piece was a stable ID, now resolved from a YouTube handle.
        if cls == "NO_EVIDENCE" and not ((r.get("vtuber_signal") or r.get("virtual_signal")) and r.get("thai_signal")):
            continue
        ed_url = URLS[platform].format(slug)
        aids = [account(a["platform"], a["platform_id"], r.get("display_name") or slug) for a in stable]
        owners = set().union(*(idx.personas_of[a] for a in aids))
        if len(owners) > 1:
            log.append(f"SKIP {slug}: accounts map to {sorted(owners)}")
            continue
        if owners:
            pid = owners.pop()
            if r.get("persona_id") and r["persona_id"] != pid:
                log.append(f"SKIP {slug}: file says {r['persona_id']}, live says {pid}")
                continue
            log.append(f"ATTACH {slug} -> {pid}")
        else:
            pid = "persona_" + sha(f"ezdn-persona:{slug}" if platform == "easydonate" else f"{platform}-persona:{slug}")
            name = r.get("display_name") or slug
            personas[pid] = [pid, name, "vtuber", "unknown", "", "", "th", "thai", "verified", now, now,
                             f"{marker}; slug={slug}; vtuber_signal={(r.get('vtuber_signal') or r.get('virtual_signal') or '')[:80]}"]
            log.append(f"NEW {slug} -> {pid} ({name})")
        ed = account(platform, slug, r.get("display_name") or slug)
        for aid in dict.fromkeys(aids + [ed]):
            link(pid, aid, ed_url, f"slug={slug}")

    print("\n".join(log))
    print(f"platform {platform}; youtube handles resolved {resolved}")
    print(json.dumps({"personas": len(personas), "accounts": len(accounts), "links": len(links)}))
    if not args.write:
        print("dry-run")
        return 0
    for tab, body in (("PERSONAS", personas), ("ACCOUNTS", accounts), ("ACCOUNT_LINKS", links)):
        if body:
            print(tab, upsert(sh, tab, list(body.values()), idx.raw[tab]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
