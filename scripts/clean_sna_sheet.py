"""Clean the ThaiVtuber_SNA sheet after archive_sna_sheet.py (owner decision 2026-09-26).

1. VTUBERS: rows whose channel is not linked (verified) to a verified persona in
   ThaiVtuber_DATA move to VTUBERS_RETIRED (with a reason column), so Master stops
   showing them. Nothing is lost.
2. ANALYTICS_SOURCES / ANALYTICS_NOTES rows are appended to DATA_DICTIONARY.
3. Private/raw and unused tabs are deleted from the sheet, but only when the local
   archive holds exactly the same row count and hash as the live tab.

Dry-run unless --write.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
from archive_sna_sheet import BASE, digest, read_tab  # noqa: E402
from migrate_canonical_sheet import Sheet, pad, token  # noqa: E402
from storage.local_archive_store import archive_path  # noqa: E402

DROP_TABS = ["PRIVATE_DATA_ARCHIVE", "VIEWER_INDEX", "VIEWER_CHANNEL_PRESENCE", "VIEWER_ACTIVITY_SUMMARY",
             "ALL_COMMENTERS", "MIGRATION_AUDIT", "RECOVERY_METADATA", "TIKTOK_ACCOUNTS", "TWITCH_ACCOUNTS",
             "ANALYTICS_SOURCES", "ANALYTICS_NOTES"]
MERGE_INTO_DICTIONARY = {"ANALYTICS_SOURCES": "analytics_source", "ANALYTICS_NOTES": "analytics_note"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    tok = token()
    http = requests.Session()
    http.headers["Authorization"] = f"Bearer {tok}"
    props = {s["properties"]["title"]: s["properties"] for s in
             http.get(BASE, params={"fields": "sheets.properties(sheetId,title,gridProperties)"}, timeout=120).json()["sheets"]}

    def values(a1):
        r = http.get(f"{BASE}/values/" + requests.utils.quote(a1, safe=""), timeout=300)
        r.raise_for_status()
        return r.json().get("values", [])

    # --- 1. VTUBERS retire plan -------------------------------------------------
    data = Sheet(tok)
    verified = {pad(r, 12)[0] for r in data.get("'PERSONAS'!A2:L") if r and pad(r, 12)[8] == "verified"}
    accounts = {pad(r, 14)[0]: pad(r, 14)[2] for r in data.get("'ACCOUNTS'!A2:N") if r and pad(r, 14)[1] == "youtube"}
    ok = set()
    for r in data.get("'ACCOUNT_LINKS'!A2:K"):
        r = pad(r, 11)
        if r[7] == "verified" and r[1] in verified and r[2] in accounts:
            ok.add(accounts[r[2]])
    vt = values("'VTUBERS'!A1:M")
    header, body = vt[0], vt[1:]
    retire = [(i + 2, pad(r, 13)) for i, r in enumerate(body) if pad(r, 13)[0] and pad(r, 13)[0] not in ok]

    # --- 2. dictionary merge plan ----------------------------------------------
    dict_rows = []
    for tab, category in MERGE_INTO_DICTIONARY.items():
        if tab not in props:
            continue
        rows = values(f"'{tab}'!A1:Z")
        if not rows:
            continue
        h = rows[0]
        for r in rows[1:]:
            rec = dict(zip(h, r))
            first = r[0] if r else ""
            dict_rows.append([category, tab, first, "", json.dumps(rec, ensure_ascii=False)] + [""] * 7)

    # --- 3. drop plan, gated on archive equality ----------------------------------
    con = duckdb.connect(str(archive_path()), read_only=True)
    drops, blocked = [], []
    for tab in DROP_TABS:
        if tab not in props:
            continue
        g = props[tab]["gridProperties"]
        live = read_tab(http, tab, g.get("rowCount", 0), g.get("columnCount", 0))[1:]
        arch = con.execute("SELECT rows, sha256 FROM _archive_meta WHERE tab = ?", [tab]).fetchone()
        (drops if arch == (len(live), digest(live)) else blocked).append(tab)
    con.close()

    print(json.dumps({"vtubers_total": len(body), "vtubers_retire": len(retire),
                      "dictionary_rows_added": len(dict_rows), "drop_tabs": drops,
                      "blocked_not_archived": blocked}, indent=1))
    if not args.write:
        print("dry-run")
        return 0

    def batch(requests_):
        r = http.post(f"{BASE}:batchUpdate", json={"requests": requests_}, timeout=300)
        r.raise_for_status()

    def append(tab, rows):
        r = http.post(f"{BASE}/values/" + requests.utils.quote(f"'{tab}'!A1", safe="") + ":append",
                      params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                      json={"values": rows}, timeout=300)
        r.raise_for_status()

    if retire:
        if "VTUBERS_RETIRED" not in props:
            batch([{"addSheet": {"properties": {"title": "VTUBERS_RETIRED"}}}])
            append("VTUBERS_RETIRED", [header + ["retired_reason", "retired_at"]])
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        append("VTUBERS_RETIRED", [r + ["not linked to a verified persona in ThaiVtuber_DATA", now] for _, r in retire])
        # Re-check rows are unchanged before deleting, then delete bottom-up.
        again = values("'VTUBERS'!A1:A")
        if any(pad(again[i - 1], 1)[0] != r[0] for i, r in retire):
            raise SystemExit("VTUBERS changed during cleanup; nothing deleted (retired copies already appended)")
        sid = props["VTUBERS"]["sheetId"]
        batch([{"deleteDimension": {"range": {"sheetId": sid, "dimension": "ROWS", "startIndex": i - 1, "endIndex": i}}}
               for i, _ in sorted(retire, reverse=True)])
        print("VTUBERS retired", len(retire))
    if dict_rows:
        append("DATA_DICTIONARY", dict_rows)
        print("DATA_DICTIONARY appended", len(dict_rows))
    if drops:
        batch([{"deleteSheet": {"sheetId": props[t]["sheetId"]}} for t in drops])
        print("deleted tabs", drops)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
