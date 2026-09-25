"""Apply owner decisions (2026-09-26) on the 26 VtuberThaiInfo base review items.

MERGE: talents whose YouTube/Twitch were split across two existing personas.
  Keeper = first persona id (sorted). Loser's links/affiliations/lifecycle rows are
  repointed to the keeper; the loser persona is marked rejected with merged_into.
SAME_CHANNEL_ONE: two talent entries on one channel that are the same creator
  (duplicate/typo listing) -> one persona.
SHARED_SEPARATE: two talents on one channel who are different personas
  (model change / re-debut) -> one persona each, both linked to the shared account.
A3/A8/A11/A13 stay as two separate personas: nothing to write.

Dry-run unless --write. Never deletes rows.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from import_vtuberthaiinfo_base import (  # noqa: E402
    MARKER, SOURCE, Index, fetch_talents, persona_type, sha, talent_accounts)
from migrate_canonical_sheet import HEADERS, Sheet, pad, token, upsert  # noqa: E402

REVIEWER = "owner:vtuberthaiinfo-review-2026-09-26"
MERGE = ["Alparu", "Lunatrix", "ApriRiru", "Akito Q Flame", "Kaylef Orion", "JamMyChan", "Biru",
         "Katsuyoshi Torakaze", "Milyni Tivona", "Ponpun"]
SAME_CHANNEL_ONE = [("DaLea", "DaLea DL"), ("Hosiko Earl", "Hoshiko Eral")]
SHARED_SEPARATE = [("Bonita", "Shinah"), ("บันลัย - banraii", "Quga"), ("Zoastelle", "Zachielle"),
                   ("Jie Mochizuki", "Geno Algos")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    talents = {t["name"]: t for t in fetch_talents()}
    sh = Sheet(token())
    idx = Index(sh)
    extra = {tab: sh.get(f"'{tab}'!A2:{chr(ord('A') + len(HEADERS[tab]) - 1)}") for tab in ("AFFILIATIONS", "LIFECYCLE_EVENTS")}
    personas = {pad(r, 12)[0]: pad(r, 12) for r in idx.raw["PERSONAS"] if r}
    out = {"PERSONAS": {}, "ACCOUNTS": {}, "ACCOUNT_LINKS": {}, "AFFILIATIONS": {}, "LIFECYCLE_EVENTS": {}}
    log = []

    def link_row(pid, aid, t, note=""):
        return ["link_" + sha(f"vti-link:{aid}:{pid}"), pid, aid, "official", "", "", f"{SOURCE}/{t['slug']}",
                "verified", REVIEWER, now, f"{MARKER}; vti_id={t['id']}{note}"]

    def ensure_accounts(t):
        ids = []
        for a in talent_accounts(t):
            aid = idx.account(a)
            if not aid:
                aid = "acct_" + sha(f"vti-account:{a['platform']}:{a['platform_id']}")
                out["ACCOUNTS"][aid] = [aid, a["platform"], a["platform_id"], a["handle"], a["name"], a["url"],
                                        "persona", "", "unknown", now, now, "verified", now, now]
            ids.append(aid)
        return ids

    def new_persona(t):
        pid = "persona_" + sha(f"vti-talent:{t['id']}")
        if pid not in personas:
            status = "graduated" if t.get("statusType") == "RETIRED" else "unknown"
            out["PERSONAS"][pid] = [pid, t["name"], persona_type(t.get("type") or []), status, "", "", "th", "thai",
                                    "verified", now, now, f"{MARKER}; vti_id={t['id']}; slug={t['slug']}; vti_status={t.get('statusType')}"]
        return pid

    # MERGE
    for name in MERGE:
        t = talents[name]
        aids = [idx.account(a) for a in talent_accounts(t)]
        ps = sorted(set().union(*(idx.personas_of[a] for a in aids if a)))
        if len(ps) != 2:
            raise SystemExit(f"{name}: expected 2 personas, found {ps}")
        keep, lose = ps
        k = list(personas[keep]); k[1] = t["name"]; k[10] = now
        k[11] = (k[11] + "; " if k[11] else "") + f"merged_from={lose}; vti_id={t['id']}"
        out["PERSONAS"][keep] = k
        lo = list(personas[lose]); lo[8] = "rejected"; lo[10] = now
        lo[11] = (lo[11] + "; " if lo[11] else "") + f"merged_into={keep} ({REVIEWER})"
        out["PERSONAS"][lose] = lo
        keep_accts = {pad(r, 11)[2] for r in idx.raw["ACCOUNT_LINKS"] if pad(r, 11)[1] == keep}
        for r in idx.raw["ACCOUNT_LINKS"]:
            r = list(pad(r, 11))
            if r[1] != lose:
                continue
            if r[2] in keep_accts:
                r[7] = "rejected"
                r[10] = (r[10] + "; " if r[10] else "") + f"duplicate after merge into {keep}"
            else:
                r[1] = keep
                r[10] = (r[10] + "; " if r[10] else "") + f"repointed from {lose} (merge)"
            r[8], r[9] = REVIEWER, now
            out["ACCOUNT_LINKS"][r[0]] = r
        for tab, w in (("AFFILIATIONS", 11), ("LIFECYCLE_EVENTS", 10)):
            for r in extra[tab]:
                r = list(pad(r, w))
                if r[1] == lose:
                    r[1] = keep
                    r[-1] = (r[-1] + "; " if r[-1] else "") + f"repointed from {lose} (merge)"
                    out[tab][r[0]] = r
        log.append(f"MERGE {name}: {personas[lose][1]} ({lose}) -> {personas[keep][1]} ({keep})")

    # SAME_CHANNEL_ONE
    for a_name, b_name in SAME_CHANNEL_ONE:
        t = talents[a_name]
        aids = ensure_accounts(t) + ensure_accounts(talents[b_name])
        existing = set().union(*(idx.personas_of[a] for a in aids))
        pid = existing.pop() if len(existing) == 1 else new_persona(t)
        for aid in dict.fromkeys(aids):
            if (pid, aid) not in idx.links:
                r = link_row(pid, aid, t, f"; also_listed_as={b_name}")
                out["ACCOUNT_LINKS"][r[0]] = r
        log.append(f"ONE {a_name} / {b_name} -> {pid}")

    # SHARED_SEPARATE
    for pair in SHARED_SEPARATE:
        for name in pair:
            t = talents[name]
            aids = ensure_accounts(t)
            existing = set().union(*(idx.personas_of[a] for a in aids))
            match = [p for p in existing if personas.get(p, [""] * 2)[1].casefold() == name.casefold()]
            if not match and len(existing) == 1 and t.get("statusType") != "RETIRED":
                match = list(existing)  # current owner of the channel keeps the existing persona
            pid = match[0] if match else new_persona(t)
            for aid in aids:
                if (pid, aid) not in idx.links:
                    r = link_row(pid, aid, t, f"; shared_channel_with={'/'.join(n for n in pair if n != name)}")
                    out["ACCOUNT_LINKS"][r[0]] = r
            log.append(f"SEPARATE {name} -> {pid}{' (existing)' if match else ''}; existing on channel: {[personas[p][1] for p in existing if p in personas]}")

    print("\n".join(log))
    print(json.dumps({tab: len(v) for tab, v in out.items()}, indent=2))
    if not args.write:
        print("dry-run")
        return 0
    for tab, rows in out.items():
        if rows:
            existing = idx.raw.get(tab) or extra.get(tab) or sh.get(f"'{tab}'!A2:{chr(ord('A') + len(HEADERS[tab]) - 1)}")
            print(tab, upsert(sh, tab, list(rows.values()), existing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
