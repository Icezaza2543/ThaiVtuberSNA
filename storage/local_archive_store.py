"""Read-only access to private tabs archived from the ThaiVtuber_SNA sheet.

scripts/archive_sna_sheet.py snapshots each sheet tab into a local DuckDB file
(outside the repo). Once a private tab is removed from the sheet, readers use
this store with the same `read_records(title, headers)` interface as
PrivateSheetStore.
"""
import os
import re
from pathlib import Path

import duckdb


def archive_path() -> Path:
    base = Path(os.getenv("LOCALAPPDATA") or Path.home() / ".local" / "share")
    return Path(os.getenv("SNA_ARCHIVE_DB") or base / "ThaiVtuberSNA" / "sna_archive.duckdb")


def _column(header: str) -> str:
    return re.sub(r"\W+", "_", header.strip()).strip("_").lower()


class LocalArchiveStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else archive_path()

    def has_tab(self, title) -> bool:
        if not self.path.exists():
            return False
        con = duckdb.connect(str(self.path), read_only=True)
        try:
            return bool(con.execute("SELECT 1 FROM _archive_meta WHERE tab = ?", [title]).fetchone())
        finally:
            con.close()

    def read_records(self, title, headers, *, batch_size=5000):
        con = duckdb.connect(str(self.path), read_only=True)
        try:
            table = '"' + title.replace('"', "") + '"'
            available = {r[0] for r in con.execute(f"DESCRIBE {table}").fetchall()}
            cols = [_column(h) for h in headers]
            if not set(cols) <= available:
                raise RuntimeError("Private archive schema mismatch")
            cur = con.execute("SELECT " + ", ".join(f'"{c}"' for c in cols) + f" FROM {table}")
            while batch := cur.fetchmany(batch_size):
                for row in batch:
                    yield {h: ("" if v is None else v) for h, v in zip(headers, row)}
        finally:
            con.close()


def default_private_store(tab: str):
    """Local archive when it holds `tab`, else the live sheet (legacy)."""
    local = LocalArchiveStore()
    if local.has_tab(tab):
        return local
    from storage.private_sheet_store import PrivateSheetStore
    return PrivateSheetStore()
