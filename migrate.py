"""
migrate.py — Migration / Bootstrap → runtime/thaivtubersna.duckdb

Usage:
    python migrate.py --dry-run     # show expected counts, do not write
    python migrate.py               # run migration from bootstrap.json or registry.json
    python migrate.py --verify      # compare DuckDB to baseline after migration
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from thaivtubersna.store import (
    DB_PATH,
    BASELINE_COUNTS,
    connect,
    migrate_from_registry_json,
    migrate_network_edges,
    bootstrap_from_json,
    verify_parity,
)

BOOTSTRAP_JSON = ROOT / "data" / "bootstrap.json"
REGISTRY_JSON = ROOT / "data" / "registry.json"
WEB_DATA_JSON = ROOT / "web" / "data.json"


def cmd_dry_run():
    print("=== DRY RUN ===")
    source = BOOTSTRAP_JSON if BOOTSTRAP_JSON.exists() else REGISTRY_JSON
    print(f"Source : {source}")
    print(f"Target : {DB_PATH}\n")

    payload = json.loads(source.read_text(encoding="utf-8"))
    tables = payload.get("tables", {})

    all_ok = True
    print(f"{'Metric / Table':<28} {'Source':>14} {'Baseline':>14} {'Match':>6}")
    print("-" * 65)
    for item, baseline in BASELINE_COUNTS.items():
        if item == "verified_personas":
            personas = tables.get("personas", [])
            src = sum(1 for p in personas if p.get("review_status") == "verified")
        else:
            src = len(tables.get(item, []))
        ok = src == baseline
        if not ok:
            all_ok = False
        mark = "✓" if ok else "✗"
        print(f"  {item:<26} {src:>14,} {baseline:>14,} {mark:>6}")

    if all_ok:
        print("\n✓ Source counts match baseline — safe to migrate.")
    else:
        print("\n✗ Source/baseline mismatch — review before migrating.")
    return 0 if all_ok else 1


def cmd_migrate():
    if BOOTSTRAP_JSON.exists():
        print(f"Bootstrapping {BOOTSTRAP_JSON} → {DB_PATH}")
        with connect(DB_PATH) as con:
            counts = bootstrap_from_json(con, BOOTSTRAP_JSON)
            con.commit()
    elif REGISTRY_JSON.exists():
        print(f"Migrating {REGISTRY_JSON} → {DB_PATH}")
        with connect(DB_PATH) as con:
            counts = migrate_from_registry_json(con, REGISTRY_JSON)
            edges = migrate_network_edges(con, WEB_DATA_JSON)
            counts["network_edges"] = edges
            con.commit()
    else:
        print("✗ Neither data/bootstrap.json nor data/registry.json found!")
        return 1

    print(f"\n{'Table':<28} {'inserted':>10}")
    print("-" * 40)
    for table, n in counts.items():
        print(f"  {table:<26} {n:>10,}")
    print(f"\nDatabase: {DB_PATH}")
    return 0


def cmd_verify():
    print(f"Verifying {DB_PATH} against baseline …\n")
    with connect(DB_PATH) as con:
        result = verify_parity(con)

    print(f"{'Metric / Table':<28} {'Expected':>12} {'Actual':>12} {'Match':>6}")
    print("-" * 60)
    for item, info in result["tables"].items():
        mark = "✓" if info["ok"] else "✗"
        print(f"  {item:<26} {info['expected']:>12,} {info['actual']:>12,} {mark:>6}")

    if result["ok"]:
        print("\n✓ Parity verified — all registry tables match baseline.")
    else:
        print("\n✗ Parity mismatch — investigate before deleting legacy data.")
    return 0 if result["ok"] else 1


def main():
    parser = argparse.ArgumentParser(description="Migrate / Bootstrap → DuckDB")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="Show expected counts without writing")
    group.add_argument("--verify", action="store_true", help="Verify DuckDB parity after migration")
    args = parser.parse_args()

    if args.dry_run:
        sys.exit(cmd_dry_run())
    elif args.verify:
        sys.exit(cmd_verify())
    else:
        sys.exit(cmd_migrate())


if __name__ == "__main__":
    main()
