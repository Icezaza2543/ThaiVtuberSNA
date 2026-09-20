"""
thaivtubersna — DuckDB-backed store for the 4-step worker pipeline.

Responsibilities:
  - Open / create the runtime DuckDB database
  - Migrate from data/registry.json (one-shot)
  - Provide typed query helpers used by collect, review, sna, export
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "runtime" / "thaivtubersna.duckdb"

TABLES = (
    "evidence",
    "personas",
    "accounts",
    "account_links",
    "lifecycle_events",
    "activity_observations",
    "affiliations",
    "continuity_links",
    "discovery_runs",
    "candidates",
    "discovery_hits",
    "legacy_claims",
    "review_queue",
    "network_edges",
    "interactions",
    "worker_state",
)

# Platforms supported by the registry
PLATFORMS = (
    "youtube", "twitch", "tiktok", "facebook", "instagram",
    "x", "kick", "ganknow", "bilibili", "niconico",
    "carrd", "linktree", "litlink", "kofi", "patreon", "vgen", "website",
)

# Tables imported from registry.json (the original 13 tables)
REGISTRY_TABLES = (
    "evidence", "personas", "accounts", "account_links",
    "lifecycle_events", "activity_observations", "affiliations",
    "continuity_links", "discovery_runs", "candidates",
    "discovery_hits", "legacy_claims", "review_queue",
)

# ── Schema ─────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY NOT NULL,
    url TEXT NOT NULL,
    kind TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    published_on TEXT,
    sha256 TEXT,
    summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    format TEXT NOT NULL,
    roles TEXT NOT NULL,
    thai_relation TEXT NOT NULL,
    review_status TEXT NOT NULL,
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    reviewer TEXT,
    reviewed_at TEXT,
    canonical_name TEXT
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY NOT NULL,
    platform TEXT NOT NULL,
    platform_id TEXT NOT NULL,
    id_namespace TEXT NOT NULL,
    handle TEXT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    first_discovered_at TEXT NOT NULL,
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    UNIQUE (platform, id_namespace, platform_id)
);

CREATE TABLE IF NOT EXISTS account_links (
    id TEXT PRIMARY KEY NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    persona_id TEXT NOT NULL REFERENCES personas(id),
    valid_from TEXT,
    valid_to TEXT,
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    review_status TEXT NOT NULL,
    reviewer TEXT,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS lifecycle_events (
    id TEXT PRIMARY KEY NOT NULL,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    event_type TEXT NOT NULL,
    event_date TEXT,
    date_precision TEXT NOT NULL,
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    review_status TEXT NOT NULL,
    reviewer TEXT,
    reviewed_at TEXT,
    note TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_observations (
    id TEXT PRIMARY KEY NOT NULL,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    account_id TEXT NOT NULL REFERENCES accounts(id),
    activity_date TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    review_status TEXT NOT NULL,
    reviewer TEXT,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS affiliations (
    id TEXT PRIMARY KEY NOT NULL,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    organization TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    review_status TEXT NOT NULL,
    reviewer TEXT,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS continuity_links (
    id TEXT PRIMARY KEY NOT NULL,
    from_persona_id TEXT NOT NULL REFERENCES personas(id),
    to_persona_id TEXT NOT NULL REFERENCES personas(id),
    relation TEXT NOT NULL,
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    review_status TEXT NOT NULL,
    reviewer TEXT,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS discovery_runs (
    id TEXT PRIMARY KEY NOT NULL,
    platform TEXT NOT NULL,
    method TEXT NOT NULL,
    query TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    stop_reason TEXT NOT NULL,
    pages INTEGER NOT NULL,
    records_seen INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY NOT NULL,
    platform TEXT NOT NULL,
    platform_id TEXT,
    id_namespace TEXT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    review_status TEXT NOT NULL,
    account_id TEXT REFERENCES accounts(id),
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    reviewer TEXT,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS discovery_hits (
    id TEXT PRIMARY KEY NOT NULL,
    run_id TEXT NOT NULL REFERENCES discovery_runs(id),
    account_id TEXT REFERENCES accounts(id),
    candidate_id TEXT REFERENCES candidates(id),
    evidence_id TEXT NOT NULL REFERENCES evidence(id)
);

CREATE TABLE IF NOT EXISTS legacy_claims (
    id TEXT PRIMARY KEY NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    source_status TEXT NOT NULL,
    source_activity TEXT NOT NULL,
    source_agency TEXT NOT NULL,
    source_names TEXT NOT NULL,
    source_checked_at TEXT NOT NULL,
    last_video_published_at TEXT,
    evidence_id TEXT NOT NULL REFERENCES evidence(id)
);

CREATE TABLE IF NOT EXISTS review_queue (
    id TEXT PRIMARY KEY NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    reason TEXT NOT NULL,
    status TEXT NOT NULL,
    note TEXT NOT NULL
);

-- SNA results table (not in original registry.json)
CREATE TABLE IF NOT EXISTS network_edges (
    id TEXT PRIMARY KEY NOT NULL,
    creator_a TEXT NOT NULL,
    creator_b TEXT NOT NULL,
    shared_any INTEGER NOT NULL DEFAULT 0,
    shared_live_chat INTEGER NOT NULL DEFAULT 0,
    shared_comments INTEGER NOT NULL DEFAULT 0,
    strong_shared_any INTEGER NOT NULL DEFAULT 0,
    strong_shared_live_chat INTEGER NOT NULL DEFAULT 0,
    strong_shared_comments INTEGER NOT NULL DEFAULT 0,
    jaccard REAL,
    simpson REAL,
    agency_a TEXT,
    agency_b TEXT,
    calculated_at TEXT NOT NULL,
    calculation_source TEXT NOT NULL DEFAULT 'legacy_seed',
    UNIQUE (creator_a, creator_b)
);

-- Interactions table (source events for SNA overlap computation)
CREATE TABLE IF NOT EXISTS interactions (
    creator_id TEXT,
    video_id TEXT,
    viewer_hash TEXT,
    source_type TEXT,   -- live_chat | comment
    observed_at TIMESTAMP,
    UNIQUE (creator_id, video_id, viewer_hash, source_type)
);

-- Worker checkpoint table
CREATE TABLE IF NOT EXISTS worker_state (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

# ── Helpers ────────────────────────────────────────────────────────────────

def uid(prefix: str, value: str) -> str:
    return prefix + "_" + hashlib.sha256(value.encode()).hexdigest()[:20]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def public_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"Evidence and account URLs must be public HTTPS URLs: {value!r}")


# ── Connection ──────────────────────────────────────────────────────────────

def open_db(path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (and initialise if new) the runtime DuckDB database."""
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(_DDL)
    if path == DB_PATH and count(con, "personas") == 0:
        bootstrap_file = ROOT / "data" / "bootstrap.json"
        registry_file = ROOT / "data" / "registry.json"
        if bootstrap_file.exists():
            bootstrap_from_json(con, bootstrap_file)
        elif registry_file.exists():
            migrate_from_registry_json(con, registry_file)
            migrate_network_edges(con, ROOT / "web" / "data.json")
    return con


@contextmanager
def connect(path: Path = DB_PATH) -> Iterator[duckdb.DuckDBPyConnection]:
    """Context-manager wrapper: commits on exit, rolls back on exception."""
    con = open_db(path)
    try:
        yield con
        con.commit()
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass  # DuckDB autocommit mode has no active transaction to roll back
        raise
    finally:
        con.close()


# ── Query helpers ───────────────────────────────────────────────────────────

def fetch_all(con: duckdb.DuckDBPyConnection, table: str, **where) -> list[dict]:
    """SELECT * FROM table [WHERE k=v ...] → list of dicts."""
    sql = f"SELECT * FROM {table}"
    params: list[Any] = []
    if where:
        clauses = " AND ".join(f"{k} = ?" for k in where)
        sql += f" WHERE {clauses}"
        params = list(where.values())
    rows = con.execute(sql, params).fetchall()
    cols = [d[0] for d in con.description]
    return [dict(zip(cols, r)) for r in rows]


# Tables whose primary key is not named 'id'
_PK_COLUMN: dict[str, str] = {
    "worker_state": "key",
}


def upsert(con: duckdb.DuckDBPyConnection, table: str, row: dict) -> None:
    """INSERT OR REPLACE equivalent for DuckDB using INSERT + ON CONFLICT DO UPDATE."""
    pk = _PK_COLUMN.get(table, "id")
    cols = list(row.keys())
    placeholders = ", ".join("?" for _ in cols)
    non_pk = [c for c in cols if c != pk]
    if non_pk:
        updates = ", ".join(f"{c} = excluded.{c}" for c in non_pk)
        on_conflict = f"DO UPDATE SET {updates}"
    else:
        on_conflict = "DO NOTHING"
    sql = (
        f"INSERT INTO {table} ({', '.join(cols)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT ({pk}) {on_conflict}"
    )
    con.execute(sql, list(row.values()))


def count(con: duckdb.DuckDBPyConnection, table: str, **where) -> int:
    sql = f"SELECT COUNT(*) FROM {table}"
    params: list[Any] = []
    if where:
        clauses = " AND ".join(f"{k} = ?" for k in where)
        sql += f" WHERE {clauses}"
        params = list(where.values())
    return con.execute(sql, params).fetchone()[0]


def record_interaction(
    con: duckdb.DuckDBPyConnection,
    creator_id: str,
    video_id: str,
    viewer_hash: str,
    source_type: str,
    observed_at: datetime | str | None = None,
) -> bool:
    """
    Record an audience interaction event.
    Idempotent: UNIQUE(creator_id, video_id, viewer_hash, source_type).
    """
    if observed_at is None:
        observed_at = utc_now()
    elif isinstance(observed_at, datetime):
        observed_at = observed_at.isoformat()
    if source_type not in {"live_chat", "comment"}:
        raise ValueError(f"Unsupported interaction source_type: {source_type!r}")
    inserted = con.execute(
        """
        INSERT INTO interactions (creator_id, video_id, viewer_hash, source_type, observed_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (creator_id, video_id, viewer_hash, source_type) DO NOTHING
        RETURNING 1
        """,
        [creator_id, video_id, viewer_hash, source_type, observed_at],
    ).fetchone()
    return inserted is not None


# ── Worker state ────────────────────────────────────────────────────────────

def get_state(con: duckdb.DuckDBPyConnection, key: str, default: Any = None) -> Any:
    row = con.execute("SELECT value FROM worker_state WHERE key = ?", [key]).fetchone()
    if row is None:
        return default
    return json.loads(row[0])


def set_state(con: duckdb.DuckDBPyConnection, key: str, value: Any) -> None:
    upsert(con, "worker_state", {"key": key, "value": json.dumps(value), "updated_at": utc_now()})


# ── Migration from registry.json ────────────────────────────────────────────

def migrate_from_registry_json(con: duckdb.DuckDBPyConnection, registry_path: Path) -> dict[str, int]:
    """
    One-shot migration: load data/registry.json rows into DuckDB.

    Tables are inserted in dependency order. Existing rows are skipped
    (idempotent). Returns counts of rows inserted per table.
    """
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported registry.json schema_version")

    counts: dict[str, int] = {}
    # Insert order respects FK dependencies
    insert_order = [
        "evidence", "personas", "accounts", "account_links",
        "lifecycle_events", "activity_observations", "affiliations",
        "continuity_links", "discovery_runs", "candidates",
        "discovery_hits", "legacy_claims", "review_queue",
    ]
    for table in insert_order:
        rows_data = payload["tables"].get(table, [])
        inserted = 0
        for row in rows_data:
            existing = con.execute(
                f"SELECT 1 FROM {table} WHERE id = ?", [row["id"]]
            ).fetchone()
            if not existing:
                upsert(con, table, row)
                inserted += 1
        counts[table] = inserted

    # Also patch personas.canonical_name from 'name' field if blank
    con.execute(
        "UPDATE personas SET canonical_name = name WHERE canonical_name IS NULL OR canonical_name = ''"
    )
    return counts


def migrate_network_edges(con: duckdb.DuckDBPyConnection, web_data_path: Path) -> int:
    """
    Seed network_edges from legacy web/data.json if the table is empty.
    Returns the number of edges inserted.
    """
    if not web_data_path.exists():
        return 0
    existing = con.execute("SELECT COUNT(*) FROM network_edges").fetchone()[0]
    if existing > 0:
        return 0  # already seeded

    web_data = json.loads(web_data_path.read_text(encoding="utf-8"))
    nodes = {n.get("id"): n for n in web_data.get("nodes", [])}
    edges = web_data.get("edges", [])
    updated_at = web_data.get("metadata", {}).get("updated_at", utc_now())

    inserted = 0
    for edge in edges:
        a_id = edge.get("source", "")
        b_id = edge.get("target", "")
        if not a_id or not b_id:
            continue
        # Canonical order: lexicographic so (A,B) and (B,A) don't duplicate
        if a_id > b_id:
            a_id, b_id = b_id, a_id
        a_node = nodes.get(a_id, {})
        b_node = nodes.get(b_id, {})
        edge_id = uid("edge", a_id + ":" + b_id)
        shared = int(edge.get("shared_viewers", 0) or 0)
        strong = int(edge.get("strong_shared", 0) or 0)
        upsert(con, "network_edges", {
            "id": edge_id,
            "creator_a": a_id,
            "creator_b": b_id,
            "shared_any": shared,
            "shared_live_chat": 0,
            "shared_comments": 0,
            "strong_shared_any": strong,
            "strong_shared_live_chat": 0,
            "strong_shared_comments": 0,
            "jaccard": None,
            "simpson": None,
            "agency_a": a_node.get("agency"),
            "agency_b": b_node.get("agency"),
            "calculated_at": updated_at,
            "calculation_source": "legacy_seed",
        })
        inserted += 1
    return inserted


# ── Bootstrap support (cold-start seed) ──────────────────────────────────────

def export_bootstrap_json(con: duckdb.DuckDBPyConnection, target_path: Path) -> int:
    """
    Export all verified baseline tables + network_edges to data/bootstrap.json.
    This serves as the lean seed snapshot for fresh clones.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    export_tables = [
        "evidence", "personas", "accounts", "account_links",
        "lifecycle_events", "activity_observations", "affiliations",
        "continuity_links", "discovery_runs", "candidates",
        "discovery_hits", "legacy_claims", "review_queue",
        "network_edges",
    ]
    data: dict[str, Any] = {
        "schema_version": 2,
        "generated_at": utc_now(),
        "tables": {},
    }
    total_rows = 0
    for t in export_tables:
        cols = [c[1] for c in con.execute(f"PRAGMA table_info({t})").fetchall()]
        rows = [dict(zip(cols, r)) for r in con.execute(f"SELECT * FROM {t}").fetchall()]
        data["tables"][t] = rows
        total_rows += len(rows)
    target_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return total_rows


def bootstrap_from_json(con: duckdb.DuckDBPyConnection, bootstrap_path: Path) -> dict[str, int]:
    """
    Seed DuckDB from data/bootstrap.json.
    Includes all 13 registry tables + network_edges.
    Idempotent: skips existing rows.
    """
    payload = json.loads(bootstrap_path.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    tables = payload.get("tables", {})
    insert_order = [
        "evidence", "personas", "accounts", "account_links",
        "lifecycle_events", "activity_observations", "affiliations",
        "continuity_links", "discovery_runs", "candidates",
        "discovery_hits", "legacy_claims", "review_queue",
        "network_edges",
    ]
    for table in insert_order:
        rows_data = tables.get(table, [])
        if not rows_data:
            counts[table] = 0
            continue

        if count(con, table) == 0:
            cols = list(rows_data[0].keys())
            placeholders = ", ".join("?" for _ in cols)
            sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
            params = [list(r.values()) for r in rows_data]
            con.executemany(sql, params)
            counts[table] = len(rows_data)
        else:
            inserted = 0
            for row in rows_data:
                existing = con.execute(
                    f"SELECT 1 FROM {table} WHERE id = ?", [row["id"]]
                ).fetchone()
                if not existing:
                    upsert(con, table, row)
                    inserted += 1
            counts[table] = inserted

    con.execute(
        "UPDATE personas SET canonical_name = name WHERE canonical_name IS NULL OR canonical_name = ''"
    )
    return counts


# ── Parity verification ─────────────────────────────────────────────────────

BASELINE_COUNTS = {
    "personas": 895,
    "verified_personas": 873,
    "accounts": 4721,
    "candidates": 1205,
    "evidence": 9411,
    "account_links": 2692,
    "lifecycle_events": 34,
    "affiliations": 14,
    "discovery_runs": 2035,
    "discovery_hits": 6362,
    "review_queue": 1402,
    "legacy_claims": 1370,
    "continuity_links": 0,
    "activity_observations": 0,
    "network_edges": 913,
}


def verify_parity(con: duckdb.DuckDBPyConnection) -> dict:
    """Compare DuckDB counts against the known baseline from registry.json."""
    results = {}
    all_ok = True
    for item, expected in BASELINE_COUNTS.items():
        if item == "verified_personas":
            actual = con.execute(
                "SELECT count(id) FROM personas WHERE review_status = 'verified'"
            ).fetchone()[0]
        else:
            actual = count(con, item)
        # After migration the 24/7 worker may legitimately add creators, accounts,
        # evidence, interactions and edges. Parity means the sealed baseline was not lost.
        ok = actual >= expected
        if not ok:
            all_ok = False
        results[item] = {"expected": expected, "actual": actual, "ok": ok}
    return {"ok": all_ok, "tables": results}
