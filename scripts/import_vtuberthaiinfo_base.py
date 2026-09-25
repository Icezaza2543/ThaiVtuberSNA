"""Import the VtuberThaiInfo archive as the trusted persona base into ThaiVtuber_DATA.

Owner decision 2026-09-26: each VtuberThaiInfo talent is a distinct, verified
Thai virtual-creator persona. Its youtubeMain/twitchMain are that persona's
official accounts (stable IDs come from the archive payload).

Per talent, matched by stable account ID only (never by name):
- a linked account already belongs to one persona -> reuse it, add missing accounts/links
- accounts exist but no persona                   -> new persona, link those accounts
- nothing exists                                  -> new persona + accounts + links
Talents whose accounts point at 2+ personas, or that share a channel with another
talent, are not written; they go to outputs/vtuberthaiinfo_base/owner_review.json.

Dry-run unless --write. Append/update only; never deletes rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from migrate_canonical_sheet import HEADERS, Sheet, pad, token, upsert  # noqa: E402

SOURCE = "https://vtuberthaiinfo-archive.pages.dev/talent"
MARKER = "vtuberthaiinfo_base"
REVIEWER = "owner:vtuberthaiinfo-base"


def sha(text: str, n: int = 20) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:n]


def fetch_talents() -> list[dict]:
    body = requests.get(SOURCE, timeout=60).text
    text = "".join(json.loads(m) for m in re.findall(r'self\.__next_f\.push\(\[1,(".*?")\]\)', body))
    i = text.find('{"talents":')
    if i < 0:
        raise SystemExit("vtuberthaiinfo schema changed: talents payload not found")
    doc, _ = json.JSONDecoder().raw_decode(text[i:])
    talents = doc.get("talents") or []
    if len(talents) < 1000:
        raise SystemExit(f"vtuberthaiinfo unexpectedly small: {len(talents)}")
    return talents


def persona_type(types: list[str]) -> str:
    t = set(types)
    if t == {"PNG"}:
        return "pngtuber"
    if "PNG" in t:
        return "mixed"
    return "vtuber" if t else "unknown"


def talent_accounts(t: dict) -> list[dict]:
    out = []
    y = t.get("youtubeMain")
    if y and str(y.get("channelId", "")).startswith("UC"):
        cid = y["channelId"]
        out.append({"platform": "youtube", "platform_id": cid, "handle": "",
                    "name": y.get("channelName") or t["name"], "url": f"https://www.youtube.com/channel/{cid}"})
    w = t.get("twitchMain")
    if w and str(w.get("channelId", "")).isdigit():
        login = (w.get("username") or "").lower()
        out.append({"platform": "twitch", "platform_id": w["channelId"], "handle": login,
                    "name": w.get("channelName") or t["name"], "url": f"https://www.twitch.tv/{login}"})
    return out


class Index:
    def __init__(self, sh: Sheet):
        self.raw = {tab: sh.get(f"'{tab}'!A2:{chr(ord('A') + len(HEADERS[tab]) - 1)}")
                    for tab in ("PERSONAS", "ACCOUNTS", "ACCOUNT_LINKS")}
        self.personas = {pad(r, 12)[0] for r in self.raw["PERSONAS"] if r}
        self.acc_by_id, self.acc_by_handle = {}, {}
        for r in self.raw["ACCOUNTS"]:
            r = pad(r, 14)
            if r[2]:
                self.acc_by_id[(r[1], r[2])] = r[0]
            if r[3]:
                self.acc_by_handle[(r[1], r[3].lower().lstrip("@"))] = r[0]
        self.personas_of = defaultdict(set)
        self.links = set()
        for r in self.raw["ACCOUNT_LINKS"]:
            r = pad(r, 11)
            self.links.add((r[1], r[2]))
            if r[7] != "rejected":
                self.personas_of[r[2]].add(r[1])

    def account(self, a: dict) -> str | None:
        return self.acc_by_id.get((a["platform"], a["platform_id"])) or (
            self.acc_by_handle.get((a["platform"], a["handle"])) if a["handle"] else None)


def plan(talents: list[dict], idx: Index):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    shared = Counter((a["platform"], a["platform_id"]) for t in talents for a in talent_accounts(t))
    personas, accounts, links, review = [], [], [], []
    counts = Counter()
    for t in talents:
        accs = talent_accounts(t)
        src = f"{SOURCE}/{t['slug']}"
        if not accs:
            counts["no_stable_account"] += 1
            continue
        if any(shared[(a["platform"], a["platform_id"])] > 1 for a in accs):
            counts["shared_channel"] += 1
            review.append({"reason": "channel listed under 2+ talents", "talent": t["name"], "slug": t["slug"], "accounts": accs})
            continue
        for a in accs:
            a["account_id"] = idx.account(a)
        existing = set().union(*(idx.personas_of[a["account_id"]] for a in accs if a["account_id"]))
        if len(existing) > 1:
            counts["conflict_multi_persona"] += 1
            review.append({"reason": "accounts already linked to different personas", "talent": t["name"], "slug": t["slug"],
                           "personas": sorted(existing), "accounts": accs})
            continue
        if existing:
            persona_id = existing.pop()
            counts["matched_existing"] += 1
        else:
            persona_id = "persona_" + sha(f"vti-talent:{t['id']}")
            counts["new_persona"] += 1
            status = "graduated" if t.get("statusType") == "RETIRED" else "unknown"
            personas.append([
                persona_id, t["name"], persona_type(t.get("type") or []), status, "", "", "th",
                "thai", "verified", now, now,
                f"{MARKER}; vti_id={t['id']}; slug={t['slug']}; vti_status={t.get('statusType')}",
            ])
        for a in accs:
            if not a["account_id"]:
                a["account_id"] = "acct_" + sha(f"vti-account:{a['platform']}:{a['platform_id']}")
                counts[f"new_account_{a['platform']}"] += 1
                accounts.append([
                    a["account_id"], a["platform"], a["platform_id"], a["handle"], a["name"], a["url"],
                    "persona", "", "unknown", now, now, "verified", now, now,
                ])
            if (persona_id, a["account_id"]) not in idx.links:
                counts["new_link"] += 1
                links.append([
                    "link_" + sha(f"vti-link:{a['account_id']}:{persona_id}"), persona_id, a["account_id"],
                    "official", "", "", src, "verified", REVIEWER, now, f"{MARKER}; vti_id={t['id']}",
                ])
    return personas, accounts, links, review, counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    talents = fetch_talents()
    sh = Sheet(token())
    idx = Index(sh)
    personas, accounts, links, review, counts = plan(talents, idx)
    summary = {"talents": len(talents), "outcomes": dict(counts),
               "writes": {"personas": len(personas), "accounts": len(accounts), "links": len(links)},
               "owner_review": len(review)}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    out = ROOT / "outputs" / "vtuberthaiinfo_base"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "owner_review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.write:
        print("dry-run")
        return 0
    for tab, body in (("PERSONAS", personas), ("ACCOUNTS", accounts), ("ACCOUNT_LINKS", links)):
        if body:
            print(tab, upsert(sh, tab, body, idx.raw[tab]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
