"""Reconcile the 884-account screening file into ThaiVtuber_DATA.

Source of the 884 is outputs/new-account-review-2026-09-19/all_884_screening_results.json
(rows drawn from data/master_creators.json#unresolved_discovery_accounts at revision
4a1db621). Human decisions are human_review_decisions.json (196 of the unresolved rows).

Does not read bootstrap into canonical tables and does not clear sheets.
New personas are created only for a human "vtuber" decision whose URL is an
account URL and does not already match a canonical account. Screening label
VTUBER without that human decision goes to FINDER_INBOX.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from migrate_canonical_sheet import HEADERS, SHEET_ID, Sheet, pad, token, upsert  # noqa: E402

SCREEN = ROOT / "outputs" / "new-account-review-2026-09-19" / "all_884_screening_results.json"
HUMAN = ROOT / "outputs" / "new-account-review-2026-09-19" / "human_review_decisions.json"
MARKER = "reconcile_884_screening"

VIDEO_PARTS = {"shorts", "watch", "live", "video", "videos", "status", "clip", "clips"}


def sha(text: str, n: int = 20) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:n]


def norm_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    p = urlparse(raw)
    host = (p.hostname or "").lower().removeprefix("www.")
    path = (p.path or "").rstrip("/")
    if host in {"youtube.com", "m.youtube.com", "youtu.be"}:
        host = "youtube.com"
    if host == "twitter.com":
        host = "x.com"
    return host + path.lower()


def parse_account(url: str, screening_platform: str) -> dict | None:
    raw = (url or "").strip()
    if "://" not in raw:
        raw = "https://" + raw
    p = urlparse(raw)
    host = (p.hostname or "").lower().removeprefix("www.")
    parts = [x for x in (p.path or "").split("/") if x]
    if host.endswith("carrd.co"):
        return {"platform": "website", "platform_id": "", "handle": host, "url": f"https://{host}/"}
    if not host or not parts:
        return None
    if host in {"youtube.com", "m.youtube.com"}:
        if parts[0].lower() in VIDEO_PARTS or parts[0].lower() in {"playlist", "post", "feed", "results"}:
            return None
        if parts[0].startswith("@") and len(parts) == 1:
            handle = parts[0][1:]
            return {"platform": "youtube", "platform_id": "", "handle": handle, "url": f"https://www.youtube.com/@{handle}"}
        if parts[0] == "channel" and len(parts) >= 2 and parts[1].startswith("UC"):
            return {"platform": "youtube", "platform_id": parts[1], "handle": "", "url": f"https://www.youtube.com/channel/{parts[1]}"}
        return None
    if host in {"twitch.tv"} and parts[0].lower() not in VIDEO_PARTS:
        login = parts[0]
        return {"platform": "twitch", "platform_id": "", "handle": login, "url": f"https://www.twitch.tv/{login}"}
    if host in {"tiktok.com"} and parts[0].startswith("@") and len(parts) == 1:
        handle = parts[0][1:]
        return {"platform": "tiktok", "platform_id": "", "handle": handle, "url": f"https://www.tiktok.com/@{handle}"}
    if host in {"x.com", "twitter.com"} and parts[0].lower() not in {"i", "intent", "share", "search"} and len(parts) == 1:
        handle = parts[0]
        return {"platform": "x", "platform_id": "", "handle": handle, "url": f"https://x.com/{handle}"}
    if host == "bsky.app" and len(parts) >= 2 and parts[0] == "profile":
        handle = parts[1]
        return {"platform": "bluesky", "platform_id": "", "handle": handle, "url": f"https://bsky.app/profile/{handle}"}
    if host in {"instagram.com"} and parts[0].lower() not in {"p", "reel", "reels", "stories"} and len(parts) == 1:
        handle = parts[0]
        return {"platform": "instagram", "platform_id": "", "handle": handle, "url": f"https://www.instagram.com/{handle}"}
    if host in {"facebook.com"} and parts[0].lower() not in {"watch", "share", "reel", "posts"} and len(parts) == 1:
        handle = parts[0]
        return {"platform": "facebook", "platform_id": "", "handle": handle, "url": f"https://www.facebook.com/{handle}"}
    return None


def note_rejects_url(note: str) -> bool:
    text = note or ""
    return "ไม่เกี่ยวข้อง" in text


class Index:
    def __init__(self, sheet: Sheet):
        self.personas = {r[0] for r in sheet.get("'PERSONAS'!A2:A") if r and r[0]}
        acc = sheet.get("'ACCOUNTS'!A2:F")
        self.accounts = {}
        self.by_platform_id = defaultdict(list)
        self.by_url = defaultdict(list)
        self.by_handle = defaultdict(list)
        for raw in acc:
            r = pad(raw, 6)
            if not r[0]:
                continue
            self.accounts[r[0]] = r
            if r[2]:
                self.by_platform_id[(r[1], r[2])].append(r[0])
            nu = norm_url(r[5])
            if nu:
                self.by_url[nu].append(r[0])
            if r[3]:
                self.by_handle[(r[1], r[3].casefold().lstrip("@"))].append(r[0])
        self.links = sheet.get("'ACCOUNT_LINKS'!A2:F")
        self.link_by_account = defaultdict(set)
        for raw in self.links:
            r = pad(raw, 6)
            if r[2]:
                self.link_by_account[r[2]].add(r[1])
        self.inbox = {}
        for i, raw in enumerate(sheet.get("'FINDER_INBOX'!A2:T"), start=2):
            r = pad(raw, 20)
            if r[0]:
                self.inbox[r[0]] = (i, r)
                self.inbox[inbox_key(r)] = (i, r)
        self.reviews = {r[0] for r in sheet.get("'REVIEW_QUEUE'!A2:A") if r and r[0]}

    def match_account(self, row: dict, parsed: dict | None) -> list[str]:
        hits = []
        ch = row.get("channel_id") or ""
        if ch:
            hits.extend(self.by_platform_id.get(("youtube", ch), []))
            hits.extend(self.by_url.get(norm_url(f"https://www.youtube.com/channel/{ch}"), []))
        if parsed:
            hits.extend(self.by_url.get(norm_url(parsed["url"]), []))
            if parsed["platform_id"]:
                hits.extend(self.by_platform_id.get((parsed["platform"], parsed["platform_id"]), []))
            if parsed["handle"] and parsed["platform"] != "youtube":
                hits.extend(self.by_handle.get((parsed["platform"], parsed["handle"].casefold()), []))
        hits.extend(self.by_url.get(norm_url(row.get("url") or ""), []))
        # unique, stable
        out = []
        for h in hits:
            if h not in out:
                out.append(h)
        return out


def youtube_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("YOUTUBE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    return ""


def resolve_youtube_handles(rows, humans) -> int:
    import urllib.parse
    import urllib.request
    key = youtube_key()
    if not key:
        return 0
    filled = 0
    for row in rows:
        human = humans.get(row["discovery_id"])
        if not human or human.get("decision") != "vtuber":
            continue
        if row.get("channel_id"):
            continue
        parsed = parse_account(row.get("url") or "", row.get("platform") or "")
        if not parsed or parsed["platform"] != "youtube" or not parsed["handle"]:
            continue
        q = urllib.parse.urlencode({"part": "id", "forHandle": parsed["handle"], "key": key})
        try:
            with urllib.request.urlopen("https://www.googleapis.com/youtube/v3/channels?" + q, timeout=30) as resp:
                body = json.loads(resp.read().decode())
        except Exception:
            continue
        items = body.get("items") or []
        if items and items[0].get("id"):
            row["channel_id"] = items[0]["id"]
            filled += 1
    return filled


def classify(rows, humans, idx: Index):
    buckets = defaultdict(list)
    for row in rows:
        human = humans.get(row["discovery_id"])
        parsed = parse_account(row.get("url") or "", row.get("platform") or "")
        matches = idx.match_account(row, parsed)
        decision = row.get("decision")
        if human and human.get("decision") == "vtuber":
            if note_rejects_url(human.get("note") or "") or parsed is None:
                buckets["CONFLICT"].append((row, "human_vtuber_url_not_an_account", matches))
            elif len(matches) > 1:
                buckets["CONFLICT"].append((row, "human_vtuber_matches_multiple_accounts", matches))
            elif len(matches) == 1:
                buckets["EXISTS_ALREADY"].append((row, matches[0]))
            else:
                buckets["NEW_CONFIRMED_PERSONA"].append((row, parsed, human))
            continue
        if human and human.get("decision") in {"unrelated", "non_persona"}:
            buckets["HUMAN_NEGATIVE"].append((row, human))
            continue
        if len(matches) > 1:
            buckets["CONFLICT"].append((row, "multiple_account_matches", matches))
            continue
        if len(matches) == 1:
            buckets["EXISTS_ALREADY"].append((row, matches[0]))
            continue
        if decision in {"NON_PERSONA_ACCOUNT", "NON_VTUBER", "VIRTUAL_GROUP", "INVALID_ACCOUNT_URL", "VTUBER_ASSOCIATED_ACCOUNT"}:
            buckets["SCREENED_NON_CANONICAL"].append((row, decision))
            continue
        # TRUSTED_BASELINE or VTUBER or UNRESOLVED (including human unavailable) with no account match
        if decision == "TRUSTED_BASELINE":
            buckets["CONFLICT"].append((row, "trusted_baseline_missing_from_sheet", matches))
        else:
            buckets["UNRESOLVED_CANDIDATE"].append((row, parsed, human))
    return buckets


def build_writes(buckets, idx: Index):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    personas, accounts, links, inbox, reviews = [], [], [], [], []
    for row, parsed, human in buckets["NEW_CONFIRMED_PERSONA"]:
        ch = row.get("channel_id") or ""
        if ch.startswith("UC"):
            parsed = dict(parsed)
            parsed["platform_id"] = ch
            parsed["url"] = f"https://www.youtube.com/channel/{ch}"
        persona_id = "persona_" + sha("884-human-vtuber:" + row["discovery_id"])
        stable = parsed["platform_id"] or parsed["url"].casefold()
        account_id = "acct_" + sha(f"884-account:{parsed['platform']}:{stable}")
        link_id = "link_" + sha(f"884-link:{account_id}:{persona_id}")
        if persona_id in idx.personas or account_id in idx.accounts:
            reviews.append(review_row(row, "deterministic_id_collision", "P1", "open", now, f"persona={persona_id}; account={account_id}"))
            continue
        reviewed = human.get("reviewed_at") or now
        personas.append([
            persona_id, row.get("name") or parsed["handle"], "unknown", "unknown", "", "", "",
            "uncertain", "verified", reviewed, reviewed,
            f"{MARKER}; human_reviewer=human; discovery_id={row['discovery_id']}; no_name_match",
        ])
        accounts.append([
            account_id, parsed["platform"], parsed["platform_id"], parsed["handle"], row.get("name") or "",
            parsed["url"], "persona", "", "unknown", reviewed, reviewed, "verified", reviewed, reviewed,
        ])
        links.append([
            link_id, persona_id, account_id, "official", "", "", parsed["url"],
            "verified", "human", reviewed,
            f"{MARKER}; discovery_id={row['discovery_id']}",
        ])
    for row, parsed, human in buckets["UNRESOLVED_CANDIDATE"]:
        inbox.append(inbox_row(row, parsed, "VTUBER_SIGNAL" if row.get("decision") == "VTUBER" else "UNRESOLVED", now))
    for row, human in buckets["HUMAN_NEGATIVE"]:
        reviews.append(review_row(row, "human_" + human.get("decision"), "P3", "rejected", now, human.get("note") or ""))
    for row, reason in buckets["SCREENED_NON_CANONICAL"]:
        reviews.append(review_row(row, "screened_" + reason.lower(), "P3", "closed", now, row.get("reason") or ""))
    for item in buckets["CONFLICT"]:
        row, reason, matches = item
        reviews.append(review_row(row, reason, "P1", "open", now, "matches=" + ",".join(matches)))
    # drop ids already present
    personas = [r for r in personas if r[0] not in idx.personas]
    accounts = [r for r in accounts if r[0] not in idx.accounts]
    existing_links = {pad(r, 1)[0] for r in idx.links}
    links = [r for r in links if r[0] not in existing_links]
    inbox = [r for r in inbox if r[0] not in idx.inbox and inbox_key(r) not in idx.inbox]
    reviews = [r for r in reviews if r[0] not in idx.reviews]
    return personas, accounts, links, inbox, reviews


def review_row(row, reason, priority, status, now, note):
    return [
        "rq_884_" + sha(row["discovery_id"] + ":" + reason, 24),
        "account", row["discovery_id"], reason, "needs_research", priority, status, "",
        now, now if status in {"rejected", "closed"} else "", row.get("url") or "",
        f"{MARKER}; name={row.get('name') or ''}; screening={row.get('decision')}; {note}",
    ]


def inbox_key(r) -> str:
    """Account identity across Finder/SNA candidate_id schemes: stable ID, else case-folded handle."""
    ident = r[2] or r[3].lstrip("@").lower()
    return f"{r[1]}:{ident}"


def inbox_row(row, parsed, classification, now):
    platform = parsed["platform"] if parsed else (row.get("platform") or "other")
    if platform not in {"youtube", "x", "twitch", "tiktok", "facebook", "instagram", "bluesky", "website", "ganknow", "other"}:
        platform = "other"
    platform_id = ""
    handle = ""
    url = row.get("url") or ""
    if parsed:
        platform_id = parsed["platform_id"]
        handle = parsed["handle"]
        url = parsed["url"]
    ch = row.get("channel_id") or ""
    if ch.startswith("UC"):
        platform = "youtube"
        platform_id = ch
        url = f"https://www.youtube.com/channel/{ch}"
    state = "pending_review" if platform_id or (parsed and url) else "unresolved_platform_id"
    return [
        row["discovery_id"], platform, platform_id, handle, row.get("name") or "", url,
        classification, "uncertain", (row.get("evidence_urls") or [""])[0] if row.get("evidence_urls") else url,
        now, now, "pending", "", "", row.get("name") or "", "unknown", "", "", f"{MARKER}; screening={row.get('decision')}", state,
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    payload = json.loads(SCREEN.read_text(encoding="utf-8"))
    humans = json.loads(HUMAN.read_text(encoding="utf-8"))["decisions"]
    rows = payload["rows"]
    assert len(rows) == 884
    print("youtube handles resolved", resolve_youtube_handles(rows, humans))
    sh = Sheet(token())
    idx = Index(sh)
    buckets = classify(rows, humans, idx)
    summary = {k: len(v) for k, v in buckets.items()}
    print(json.dumps({"rows": len(rows), "human": len(humans), "buckets": summary, "status_counts": payload["status_counts"]}, ensure_ascii=False, indent=2))
    personas, accounts, links, inbox, reviews = build_writes(buckets, idx)
    print(json.dumps({"personas": len(personas), "accounts": len(accounts), "links": len(links), "inbox": len(inbox), "reviews": len(reviews)}, indent=2))
    out = ROOT / "outputs" / "reconcile_884"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps({
        "source": str(SCREEN),
        "source_revision": payload["source_revision"],
        "buckets": summary,
        "writes": {"personas": len(personas), "accounts": len(accounts), "links": len(links), "inbox": len(inbox), "reviews": len(reviews)},
        "new_persona_ids": [r[0] for r in personas],
    }, indent=2), encoding="utf-8")
    if not args.write:
        print("dry-run")
        return 0
    for tab, body in (
        ("PERSONAS", personas),
        ("ACCOUNTS", accounts),
        ("ACCOUNT_LINKS", links),
        ("REVIEW_QUEUE", reviews),
    ):
        if not body:
            print(tab, "skip")
            continue
        header = sh.get(f"'{tab}'!A1:{chr(ord('A') + len(HEADERS[tab]) - 1)}1")
        if pad(header[0], len(HEADERS[tab])) != HEADERS[tab]:
            raise SystemExit(f"header mismatch {tab}")
        existing = sh.get(f"'{tab}'!A2:{chr(ord('A') + len(HEADERS[tab]) - 1)}")
        print(upsert(sh, tab, body, existing))
    if inbox:
        header = sh.get("'FINDER_INBOX'!A1:T1")
        expect = ["candidate_id", "platform", "platform_id", "handle", "display_name", "canonical_url", "classification", "thai_relevance", "source_url", "first_seen", "last_checked_at", "review_status", "action", "target_persona_id", "persona_name", "account_type", "reviewer", "reviewed_at", "notes", "sync_state"]
        if pad(header[0], 20) != expect:
            raise SystemExit(f"inbox header {header}")
        existing = sh.get("'FINDER_INBOX'!A2:T")
        # local upsert by candidate id without using HEADERS width helper
        have = {}
        for i, raw in enumerate(existing, start=2):
            r = pad(raw, 20)
            if r[0]:
                have[r[0]] = (i, r)
                have[inbox_key(r)] = (i, r)
        appends = [r for r in inbox if r[0] not in have and inbox_key(r) not in have]
        if appends:
            start = max((i for i, _ in have.values()), default=1) + 1
            data = []
            step = 200
            for off in range(0, len(appends), step):
                part = appends[off:off + step]
                a = start + off
                b = a + len(part) - 1
                data.append({"range": f"'FINDER_INBOX'!A{a}:T{b}", "values": part})
            sh.batch_update(data)
        print({"inbox_appended": len(appends), "inbox_skipped": len(inbox) - len(appends)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
