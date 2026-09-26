"""Replace slug-like display names on EasyDonate-created personas with the linked
YouTube channel title (public channel page og:title).

Only personas whose notes contain `slug=<s>` and whose display_name equals that
slug are touched. A persona without exactly one linked YouTube channel keeps its
name. Dry-run unless --write.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from import_vtuberthaiinfo_base import Index  # noqa: E402
from migrate_canonical_sheet import Sheet, pad, token, upsert  # noqa: E402


def channel_title(cid: str) -> str:
    r = requests.get(f"https://www.youtube.com/channel/{cid}", timeout=20,
                     headers={"Accept-Language": "en", "User-Agent": "Mozilla/5.0"}, cookies={"CONSENT": "YES+1"})
    m = re.search(r'<meta property="og:title" content="([^"]*)"', r.text)
    return html.unescape(m.group(1)).strip() if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sh = Sheet(token())
    idx = Index(sh)
    yt = {pad(r, 14)[0]: pad(r, 14)[2] for r in idx.raw["ACCOUNTS"] if pad(r, 14)[1] == "youtube"}
    accts_of = {}
    for r in idx.raw["ACCOUNT_LINKS"]:
        r = pad(r, 11)
        if r[7] != "rejected" and r[2] in yt:
            accts_of.setdefault(r[1], set()).add(yt[r[2]])
    updates, log = [], []
    for raw in idx.raw["PERSONAS"]:
        p = list(pad(raw, 12))
        m = re.search(r"\bslug=([^;\s]+)", p[11])
        if not m or p[1] != m.group(1) or p[8] != "verified":
            continue
        chans = accts_of.get(p[0], set())
        if len(chans) != 1:
            log.append(f"keep {p[1]}: {len(chans)} YouTube channels")
            continue
        title = channel_title(next(iter(chans)))
        time.sleep(1)
        if not title or title == p[1]:
            log.append(f"keep {p[1]}: no title")
            continue
        log.append(f"{p[1]} -> {title}")
        p[11] += f"; renamed_from_slug={p[1]}"
        p[1], p[10] = title, now
        updates.append(p)
    print("\n".join(log))
    print(json.dumps({"rename": len(updates)}))
    if args.write and updates:
        print(upsert(sh, "PERSONAS", updates, idx.raw["PERSONAS"]))
    elif not args.write:
        print("dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
