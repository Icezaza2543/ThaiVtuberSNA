"""Platform coverage and persona missing-platform matrix reporting."""

from collections import defaultdict
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from ..store import PLATFORMS, rows

DEFAULT_TARGET_PLATFORMS = (
    "youtube", "twitch", "tiktok", "x", "instagram", "facebook", "ganknow", "kick"
)


def get_platform_coverage(db: sqlite3.Connection) -> Dict[str, Dict[str, int]]:
    """
    Calculate coverage statistics per platform:
    - total_accounts: rows in accounts table
    - verified_accounts: accounts linked to a persona with verified status
    - candidate_leads: candidates in needs_evidence status
    - stable_id_available: accounts or candidates with non-null platform_id
    """
    res = {}
    for p in PLATFORMS:
        res[p] = {
            "total_accounts": 0,
            "verified_accounts": 0,
            "candidate_leads": 0,
            "stable_id_available": 0,
        }

    # Query accounts
    accts = rows(db, "accounts")
    verified_acct_ids = {
        r["account_id"]
        for r in rows(db, "account_links")
        if r.get("review_status") == "verified"
    }

    for a in accts:
        p = a["platform"]
        if p in res:
            res[p]["total_accounts"] += 1
            if a["id"] in verified_acct_ids:
                res[p]["verified_accounts"] += 1
            if a.get("platform_id"):
                res[p]["stable_id_available"] += 1

    # Query candidates
    cands = rows(db, "candidates")
    for c in cands:
        p = c["platform"]
        if p in res:
            if c.get("review_status") == "needs_evidence":
                res[p]["candidate_leads"] += 1
            if c.get("platform_id"):
                res[p]["stable_id_available"] += 1

    return res


def format_coverage_table(coverage: Dict[str, Dict[str, int]]) -> str:
    """Format platform coverage dict into a clean ASCII table."""
    lines = []
    lines.append(f"{'Platform':<15} {'Total Accounts':<16} {'Verified':<12} {'Needs Evidence':<16} {'Stable IDs':<12}")
    lines.append("-" * 75)
    for p, stats in sorted(
        coverage.items(),
        key=lambda item: (item[1]["total_accounts"] + item[1]["candidate_leads"], item[1]["verified_accounts"]),
        reverse=True,
    ):
        if stats["total_accounts"] == 0 and stats["candidate_leads"] == 0:
            continue
        lines.append(
            f"{p:<15} {stats['total_accounts']:<16} {stats['verified_accounts']:<12} {stats['candidate_leads']:<16} {stats['stable_id_available']:<12}"
        )
    return "\n".join(lines)


def get_missing_platform_matrix(
    db: sqlite3.Connection,
    target_platforms: Tuple[str, ...] = DEFAULT_TARGET_PLATFORMS,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Build matrix for verified personas showing presence/absence on key platforms:
    - '✓' = verified account exists
    - '?' = candidate lead exists with matching name/handle or evidence
    - '-' = missing platform
    """
    persona_platforms = defaultdict(set)
    persona_names = {}
    for r in db.execute("""
        SELECT p.id, p.name, a.platform
        FROM personas p
        JOIN account_links al ON p.id = al.persona_id
        JOIN accounts a ON al.account_id = a.id
        WHERE al.review_status = 'verified'
    """).fetchall():
        pid, pname, plat = r[0], r[1], r[2]
        persona_names[pid] = pname
        persona_platforms[pid].add(plat)

    # Check candidates for candidate match
    cand_platforms = defaultdict(lambda: defaultdict(list))
    for c in rows(db, "candidates"):
        if c.get("name"):
            cand_platforms[c["name"].strip().lower()][c["platform"]].append(c["id"])

    matrix = []
    for pid, pname in sorted(persona_names.items(), key=lambda x: x[1].lower())[:limit]:
        entry = {"persona_id": pid, "name": pname, "platforms": {}}
        for plat in target_platforms:
            if plat in persona_platforms[pid]:
                entry["platforms"][plat] = "✓"
            elif plat in cand_platforms.get(pname.strip().lower(), {}):
                entry["platforms"][plat] = "?"
            else:
                entry["platforms"][plat] = "-"
        matrix.append(entry)
    return matrix


def format_matrix_table(matrix: List[Dict[str, Any]], target_platforms: Tuple[str, ...] = DEFAULT_TARGET_PLATFORMS) -> str:
    """Format missing-platform matrix into readable text table."""
    headers = ["Persona"] + [p.upper()[:4] for p in target_platforms]
    col_widths = [32] + [6] * len(target_platforms)
    header_str = "  ".join(f"{h:<{w}}" for h, w in zip(headers, col_widths))
    lines = [header_str, "-" * len(header_str)]
    for row in matrix:
        vals = [row["name"][:30]] + [row["platforms"].get(p, "-") for p in target_platforms]
        row_str = "  ".join(f"{v:<{w}}" for v, w in zip(vals, col_widths))
        lines.append(row_str)
    return "\n".join(lines)


def get_missing_platform_search_targets(
    db: sqlite3.Connection,
    target_platforms: Tuple[str, ...] = ("twitch", "tiktok", "ganknow", "x", "kick"),
    max_targets: int = 100,
) -> List[Tuple[str, str, str]]:
    """
    Find high-value search queries for verified personas missing specific platforms.
    Returns list of (target_platform, seed_query, persona_name).
    """
    targets = []
    seen = set()

    rows_data = db.execute("""
        SELECT p.id, p.name, a.handle, a.platform
        FROM personas p
        JOIN account_links al ON p.id = al.persona_id
        JOIN accounts a ON al.account_id = a.id
        WHERE al.review_status = 'verified'
    """).fetchall()

    persona_accts = defaultdict(dict)
    persona_names = {}
    for pid, pname, handle, plat in rows_data:
        persona_names[pid] = pname
        if handle:
            persona_accts[pid][plat] = handle

    for pid, plats in persona_accts.items():
        pname = persona_names.get(pid, "")
        # Get best seed handle (preferably YouTube handle)
        best_handle = plats.get("youtube") or next(iter(plats.values()), None)
        if not best_handle:
            continue
        clean_handle = best_handle.lstrip("@").strip()
        if len(clean_handle) < 3 or clean_handle.isdigit():
            continue

        for plat in target_platforms:
            if plat not in plats:
                key = (plat, clean_handle)
                if key not in seen:
                    seen.add(key)
                    targets.append((plat, clean_handle, pname))
                    if len(targets) >= max_targets:
                        return targets

    return targets
