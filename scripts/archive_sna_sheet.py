"""Snapshot every tab of the ThaiVtuber_SNA sheet into a local DuckDB file (read-only on the sheet).

Default target: %LOCALAPPDATA%/ThaiVtuberSNA/sna_archive.duckdb (outside the repo; it holds
viewer IDs/names). Each tab becomes a table `<tab>` (all VARCHAR, header row as column
names) plus a row in `_archive_meta` with row count and a SHA-256 over the rows.
`--verify` re-reads the sheet and checks counts and hashes against the archive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from migrate_canonical_sheet import token  # noqa: E402

SNA_SHEET = "1H876HyqxkOEYJGczctP5G-ZNAZv22jzViw787h441fE"
BASE = f"https://sheets.googleapis.com/v4/spreadsheets/{SNA_SHEET}"
CHUNK = 50000


def archive_path() -> Path:
    base = Path(os.getenv("LOCALAPPDATA") or Path.home() / ".local" / "share")
    return Path(os.getenv("SNA_ARCHIVE_DB") or base / "ThaiVtuberSNA" / "sna_archive.duckdb")


def col_letter(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def read_tab(http: requests.Session, title: str, rows: int, cols: int) -> list[list[str]]:
    out = []
    last = col_letter(max(cols, 1))
    for start in range(1, rows + 1, CHUNK):
        end = min(rows, start + CHUNK - 1)
        a1 = requests.utils.quote(f"'{title}'!A{start}:{last}{end}", safe="")
        r = http.get(f"{BASE}/values/{a1}", params={"valueRenderOption": "UNFORMATTED_VALUE"}, timeout=300)
        r.raise_for_status()
        out.extend(r.json().get("values", []))
    return out


def digest(rows: list[list]) -> str:
    h = hashlib.sha256()
    for r in rows:
        h.update(json.dumps([str(x) for x in r], ensure_ascii=False).encode())
        h.update(b"\n")
    return h.hexdigest()


def columns(header: list, width: int) -> list[str]:
    names, seen = [], set()
    for i in range(width):
        raw = str(header[i]) if i < len(header) and str(header[i]).strip() else f"col_{i + 1}"
        name = re.sub(r"\W+", "_", raw.strip()).strip("_").lower() or f"col_{i + 1}"
        while name in seen:
            name += "_"
        seen.add(name)
        names.append(name)
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    http = requests.Session()
    http.headers["Authorization"] = f"Bearer {token()}"
    meta = http.get(BASE, params={"fields": "sheets.properties(title,gridProperties)"}, timeout=120).json()
    path = archive_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE IF NOT EXISTS _archive_meta (tab VARCHAR PRIMARY KEY, rows INTEGER, "
                "sha256 VARCHAR, archived_at VARCHAR)")
    ok = True
    for s in meta["sheets"]:
        p = s["properties"]
        title, g = p["title"], p["gridProperties"]
        values = read_tab(http, title, g.get("rowCount", 0), g.get("columnCount", 0))
        header, body = (values[0] if values else []), values[1:]
        width = max([len(header)] + [len(r) for r in body]) if values else 0
        rows = [[None if i >= len(r) else str(r[i]) for i in range(width)] for r in body]
        h = digest(body)
        if args.verify:
            got = con.execute("SELECT rows, sha256 FROM _archive_meta WHERE tab = ?", [title]).fetchone()
            match = got == (len(body), h)
            ok &= match
            print(f"{'OK ' if match else 'BAD'} {title}: sheet {len(body)} rows, archive {got and got[0]}")
            continue
        cols = columns(header, width)
        table = '"' + title.replace('"', "") + '"'
        con.execute(f"DROP TABLE IF EXISTS {table}")
        if width:
            con.execute(f"CREATE TABLE {table} (" + ", ".join(f'"{c}" VARCHAR' for c in cols) + ")")
            if rows:
                con.executemany(f"INSERT INTO {table} VALUES (" + ", ".join("?" * width) + ")", rows)
        con.execute("INSERT OR REPLACE INTO _archive_meta VALUES (?, ?, ?, ?)",
                    [title, len(body), h, datetime.now(timezone.utc).isoformat()])
        print(f"archived {title}: {len(body)} rows")
    con.close()
    print(f"archive: {path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
