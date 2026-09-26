"""Apply reviewed EasyDonate links (intake/consolidated/easydonate-links-*.jsonl) to ThaiVtuber_DATA.

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
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from import_vtuberthaiinfo_base import Index, sha  # noqa: E402
from migrate_canonical_sheet import Sheet, token, upsert  # noqa: E402

REVIEWER = "owner:easydonate-2026-09-26"
MARKER = "easydonate_links"
SKIP = {"hoshisaki_lyn"}  # current page conflicts with earlier owner cross-link; possible recycled slug
URLS = {"youtube": "https://www.youtube.com/channel/{}", "x": "https://x.com/{}",
        "twitch": "https://www.twitch.tv/{}", "easydonate": "https://easydonate.app/{}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default=str(ROOT / "intake/consolidated/easydonate-links-2026-09-26.jsonl"))
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = [json.loads(l) for l in open(args.file, encoding="utf-8") if l.strip()]
    sh = Sheet(token())
    idx = Index(sh)
    personas, accounts, links, log = {}, {}, {}, []

    def account(platform, pid, name):
        # Handle-only platforms follow the sheet convention: empty platform_id, handle in its own column.
        by_handle = platform in ("x", "easydonate")
        a = {"platform": platform, "platform_id": "" if by_handle else pid, "handle": pid.lower() if by_handle else ""}
        aid = idx.account(a)
        if not aid:
            aid = "acct_" + sha(f"ezdn-account:{platform}:{a['handle'] or pid}")
            accounts[aid] = [aid, platform, a["platform_id"], pid if by_handle else "", name,
                             URLS[platform].format(pid), "persona", "", "unknown", now, now, "verified", now, now]
        return aid

    def link(pid, aid, src, note):
        if (pid, aid) in idx.links:
            return
        lid = "link_" + sha(f"ezdn-link:{aid}:{pid}")
        links[lid] = [lid, pid, aid, "official", "", "", src, "verified", REVIEWER, now, f"{MARKER}; {note}"]

    for r in rows:
        slug, cls = r["slug"], r["match"]
        stable = [a for a in r["official_accounts"] if a.get("platform_id") and a["platform"] in URLS]
        if slug in SKIP or cls == "NO_EVIDENCE" or not stable:
            continue
        ed_url = URLS["easydonate"].format(slug)
        aids = [account(a["platform"], a["platform_id"], r.get("display_name") or slug) for a in stable]
        owners = set().union(*(idx.personas_of[a] for a in aids))
        if len(owners) > 1:
            log.append(f"SKIP {slug}: accounts map to {sorted(owners)}")
            continue
        if owners:
            pid = owners.pop()
            if cls == "MATCH_EXISTING" and r.get("persona_id") and r["persona_id"] != pid:
                log.append(f"SKIP {slug}: file says {r['persona_id']}, live says {pid}")
                continue
            log.append(f"ATTACH {slug} -> {pid}")
        else:
            pid = "persona_" + sha(f"ezdn-persona:{slug}")
            name = r.get("display_name") or slug
            personas[pid] = [pid, name, "vtuber", "unknown", "", "", "th", "thai", "verified", now, now,
                             f"{MARKER}; slug={slug}; vtuber_signal={(r.get('vtuber_signal') or '')[:80]}"]
            log.append(f"NEW {slug} -> {pid} ({name})")
        ed = account("easydonate", slug, r.get("display_name") or slug)
        for aid in dict.fromkeys(aids + [ed]):
            link(pid, aid, ed_url, f"slug={slug}")

    print("\n".join(log))
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
