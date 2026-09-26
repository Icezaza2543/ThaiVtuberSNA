"""Append newly verified canonical accounts from ThaiVtuber_DATA to the ThaiVtuber_SNA sheet
that ThaiVtuberMaster reads (VTUBERS, TWITCH_VERIFIED, TIKTOK_VERIFIED).

Append-only: existing rows (and SNA collection state such as priority/enabled/
streams_collected) are never changed or removed. A row is added only for an
account linked (link verified) to a verified persona and not already present
by stable ID. New VTUBERS rows start with enabled=False so SNA collection
quota is not consumed until the owner enables them.

Dry-run unless --write.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from migrate_canonical_sheet import Sheet, pad, token  # noqa: E402

SNA_SHEET = "1H876HyqxkOEYJGczctP5G-ZNAZv22jzViw787h441fE"
VTUBERS_COLUMNS = ["channel_id", "handle", "name", "subscriber_count", "agency", "status", "thai_confidence",
                   "priority", "source_count", "last_activity", "last_collected", "streams_collected", "enabled"]
PLATFORM_COLUMNS = ["handle", "name", "platform_id", "url", "persona_name", "thai_relation", "format", "observed_at",
                    "as_of", "persona_id", "account_id", "id_namespace", "account_evidence_url",
                    "persona_evidence_url", "link_evidence_url", "reviewed_at"]
NAMESPACE = {"twitch": "user_id", "tiktok": "web_user_id"}


class SnaSheet:
    def __init__(self, tok: str):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {tok}"
        self.base = f"https://sheets.googleapis.com/v4/spreadsheets/{SNA_SHEET}/values/"

    def get(self, a1: str) -> list[list[str]]:
        r = self.s.get(self.base + requests.utils.quote(a1, safe=""), timeout=180)
        r.raise_for_status()
        return r.json().get("values", [])

    def append(self, tab: str, rows: list[list[str]]):
        for off in range(0, len(rows), 500):
            r = self.s.post(self.base + requests.utils.quote(f"'{tab}'!A1", safe="") + ":append",
                            params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                            json={"values": rows[off:off + 500]}, timeout=180)
            r.raise_for_status()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    tok = token()
    data, sna = Sheet(tok), SnaSheet(tok)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    personas = {pad(r, 12)[0]: pad(r, 12) for r in data.get("'PERSONAS'!A2:L") if r}
    accounts = {pad(r, 14)[0]: pad(r, 14) for r in data.get("'ACCOUNTS'!A2:N") if r}
    persona_of = defaultdict(list)
    for r in data.get("'ACCOUNT_LINKS'!A2:K"):
        r = pad(r, 11)
        if r[7] == "verified" and personas.get(r[1], [""] * 12)[8] == "verified":
            persona_of[r[2]].append((r[1], r[6], r[9]))

    plan = {}
    # VTUBERS (YouTube)
    header = sna.get("'VTUBERS'!A1:M1")[0]
    if header != VTUBERS_COLUMNS:
        raise SystemExit(f"VTUBERS header changed: {header}")
    have = {pad(r, 1)[0] for r in sna.get("'VTUBERS'!A2:A")}
    rows = []
    for aid, a in accounts.items():
        if a[1] != "youtube" or not a[2].startswith("UC") or a[2] in have or not persona_of.get(aid):
            continue
        pid = persona_of[aid][0][0]
        rows.append([a[2], a[3], personas[pid][1] or a[4], "", "", "ACCEPT", "", "C", "1", "", "", "0", "False"])
        have.add(a[2])
    plan["VTUBERS"] = rows

    # TWITCH_VERIFIED / TIKTOK_VERIFIED
    for platform, tab in (("twitch", "TWITCH_VERIFIED"), ("tiktok", "TIKTOK_VERIFIED")):
        header = sna.get(f"'{tab}'!A1:P1")[0]
        if header != PLATFORM_COLUMNS:
            raise SystemExit(f"{tab} header changed: {header}")
        have = {pad(r, 3)[2] for r in sna.get(f"'{tab}'!A2:C")}
        rows = []
        for aid, a in accounts.items():
            if a[1] != platform or not a[2].isdigit() or a[2] in have or not persona_of.get(aid):
                continue
            pid, src, reviewed = persona_of[aid][0]
            p = personas[pid]
            rows.append([a[3], a[4], a[2], a[5], p[1], p[7], p[2], now, today, pid, aid, NAMESPACE[platform],
                         src, src, src, reviewed])
            have.add(a[2])
        plan[tab] = rows

    print(json.dumps({tab: len(rows) for tab, rows in plan.items()}))
    if not args.write:
        print("dry-run")
        return 0
    for tab, rows in plan.items():
        if rows:
            sna.append(tab, rows)
            print(tab, "appended", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
